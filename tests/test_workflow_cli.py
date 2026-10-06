"""Black-box integration checks of the published workflow CLI.

Every project and run is disposable. Tests exercise observable commands and
artifacts rather than importing engine functions or duplicating its rules.
"""

import copy
import base64
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


ENGINE = Path(__file__).resolve().parents[1] / "skills" / "sbar-checkpoint" / "scripts" / "workflow.py"


class WorkflowCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="checkpoint-cli-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.run = self.root / "run"
        self.plan_file = self.root / "plan.json"
        (self.project / "src.py").write_text("def add(a, b):\n    return a + b\n")
        (self.project / "test_src.py").write_text(
            "import unittest\nfrom src import add\n"
            "class Addition(unittest.TestCase):\n"
            "    def test_real_result(self):\n        self.assertEqual(add(2, 3), 5)\n"
        )
        self.plan = {
            "schema_version": 1,
            "mode": "feature",
            "approval": "delegated",
            "environment": "local-isolated",
            "requirements": [{"id": "R1", "text": "Addition yields correct result"}],
            "checkpoints": [self.checkpoint("cp1", ["R1"])],
        }

    def checkpoint(self, checkpoint_id, covers, dependencies=None):
        return {
            "id": checkpoint_id,
            "title": "Verify addition",
            "covers": covers,
            "depends_on": dependencies or [],
            "scope": ["src.py", "test_src.py"],
            "gates": {
                "behavior": {
                    "kind": "command",
                    "checks": [{
                        "id": "unit",
                        "argv": [sys.executable, "-m", "unittest", "-v", "test_src"],
                        "parser": "unittest",
                        "min_tests": 1,
                        "timeout_seconds": 5,
                    }],
                },
                "review": {"kind": "review", "reviewers": 1, "axes": ["spec"]},
                "ui": {"kind": "not_applicable", "reason": "No visible surface changes"},
            },
        }

    def cli(self, command, *args, success=True, expected=None, revision=True):
        argv = [sys.executable, str(ENGINE), command, "--run", str(self.run)]
        if revision and command not in {"init", "status", "export", "recover"}:
            if expected is None:
                expected = self.status()["revision"]
            argv += ["--expected-revision", str(expected)]
        argv.extend(str(x) for x in args)
        result = subprocess.run(argv, text=True, capture_output=True, timeout=20)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        text = result.stdout if result.returncode == 0 else result.stderr
        try:
            payload = json.loads(text)
        except ValueError:
            payload = {"output": result.stdout, "error": result.stderr}
        return result, payload

    def initialize(self, success=True):
        self.plan_file.write_text(json.dumps(self.plan))
        return self.cli("init", "--project", self.project, "--plan", self.plan_file,
                        success=success)

    def status(self):
        return self.cli("status", revision=False)[1]

    def start(self, checkpoint="cp1", actor="builder", success=True):
        return self.cli("start", "--checkpoint", checkpoint, "--actor", actor,
                        success=success)

    def check(self, checkpoint="cp1", success=True, token=None):
        args = ["--checkpoint", checkpoint, "--check", "unit"]
        if token:
            args += ["--token", token]
        return self.cli("check", *args, success=success)

    def review(self, checkpoint="cp1", reviewer="independent-reviewer", success=True,
               axis="spec", verdict="pass", findings=None, overrides=None):
        status = self.status()
        report = {
            "source_hash": status["checkpoints"][checkpoint]["source_hash"],
            "plan_hash": status["plan_hash"],
            "reviewer": reviewer,
            "axis": axis,
            "verdict": verdict,
            "findings": findings or [],
        }
        if overrides:
            report.update(overrides)
        path = self.root / ("review-" + reviewer + ".json")
        path.write_text(json.dumps(report))
        return self.cli("review", "--checkpoint", checkpoint, "--report", path,
                        success=success)

    def prove(self, checkpoint="cp1", success=True):
        return self.cli("prove", "--checkpoint", checkpoint, success=success)

    def complete(self, checkpoint="cp1"):
        self.start(checkpoint)
        self.check(checkpoint)
        self.review(checkpoint)
        self.prove(checkpoint)
        self.cli("accept", "--checkpoint", checkpoint)

    def change_check(self, argv, parser="json", minimum=1, timeout=5):
        check = self.plan["checkpoints"][0]["gates"]["behavior"]["checks"][0]
        check.update(argv=argv, parser=parser, min_tests=minimum,
                     timeout_seconds=timeout)

    def test_real_unittest_positive_to_acceptance(self):
        self.initialize()
        self.complete()
        self.assertEqual(self.status()["checkpoints"]["cp1"]["status"], "accepted")

    def test_prove_rejects_missing_required_evidence(self):
        self.initialize()
        self.start()
        self.prove(success=False)

    def test_accept_rejects_unproven_checkpoint(self):
        self.initialize()
        self.start()
        self.cli("accept", "--checkpoint", "cp1", success=False)

    def test_missing_requirement_coverage_rejects_plan(self):
        self.plan["requirements"].append({"id": "R2", "text": "Uncovered output"})
        self.initialize(success=False)

    def test_unknown_covered_requirement_rejects_plan(self):
        self.plan["checkpoints"][0]["covers"].append("unknown")
        self.initialize(success=False)

    def test_dependency_cycle_rejects_plan(self):
        self.plan["checkpoints"][0]["depends_on"] = ["cp2"]
        self.plan["requirements"].append({"id": "R2", "text": "Second cycle contract"})
        self.plan["checkpoints"].append(self.checkpoint("cp2", ["R2"], ["cp1"]))
        result, _ = self.initialize(success=False)
        self.assertIn("dependency cycle", result.stderr)

    def test_unknown_dependency_rejects_plan(self):
        self.plan["checkpoints"][0]["depends_on"] = ["missing"]
        self.initialize(success=False)

    def test_dependency_requires_acceptance_and_becomes_available(self):
        self.plan["requirements"].append({"id": "R2", "text": "Second contract"})
        self.plan["checkpoints"].append(self.checkpoint("cp2", ["R2"], ["cp1"]))
        self.initialize()
        self.start("cp2", success=False)
        self.complete()
        self.start("cp2")

    def test_real_assertion_failure_is_failed_evidence(self):
        (self.project / "src.py").write_text("def add(a, b):\n    return a - b\n")
        self.initialize()
        self.start()
        self.check(success=False)
        self.review()
        self.prove(success=False)

    def test_success_exit_with_zero_tests_does_not_pass(self):
        self.change_check([sys.executable, "-c", 'print(\'{"total":0,"failed":0,"skipped":0}\')'])
        self.initialize()
        self.start()
        self.check(success=False)
        self.prove(success=False)

    def test_all_skipped_json_does_not_pass(self):
        self.change_check([sys.executable, "-c", 'print(\'{"total":2,"failed":0,"skipped":2}\')'])
        self.initialize()
        self.start()
        self.check(success=False)

    def test_all_skipped_unittest_does_not_pass(self):
        (self.project / "test_src.py").write_text(
            "import unittest\nclass Skipped(unittest.TestCase):\n"
            "    @unittest.skip('environment unavailable')\n"
            "    def test_not_run(self): pass\n")
        self.initialize()
        self.start()
        self.check(success=False)

    def test_missing_executable_is_not_proven(self):
        self.change_check([str(self.root / "absent-runner")])
        self.initialize()
        self.start()
        self.check(success=False)
        self.prove(success=False)

    def test_malformed_json_result_does_not_pass(self):
        self.change_check([sys.executable, "-c", "print('not a result')"])
        self.initialize()
        self.start()
        self.check(success=False)

    def test_json_counts_reject_boolean_as_integer(self):
        self.change_check([sys.executable, "-c", 'print(\'{"total":true,"failed":0,"skipped":0}\')'])
        self.initialize()
        self.start()
        self.check(success=False)

    def test_json_counts_reject_impossible_skipped_total(self):
        self.change_check([sys.executable, "-c", 'print(\'{"total":1,"failed":0,"skipped":2}\')'])
        self.initialize()
        self.start()
        self.check(success=False)

    def test_tooling_exit_parser_is_separate_from_actual_tests(self):
        self.change_check([sys.executable, "-c", "print('lint ok')"], parser="exit", minimum=0)
        self.initialize()
        self.start()
        self.check()

    def test_exit_parser_cannot_claim_required_tests(self):
        self.change_check([sys.executable, "-c", "pass"], parser="exit", minimum=1)
        self.initialize(success=False)

    def test_implementer_cannot_review_own_work(self):
        self.initialize()
        self.start()
        self.check()
        self.review(reviewer="builder", success=False)
        self.prove(success=False)

    def test_two_reviewers_require_distinct_identities(self):
        self.plan["checkpoints"][0]["gates"]["review"]["reviewers"] = 2
        self.plan["checkpoints"][0]["gates"]["review"]["axes"] = ["spec", "standards"]
        self.initialize()
        self.start()
        self.check()
        self.review()
        self.review()
        self.prove(success=False)
        self.review(reviewer="reviewer-two", axis="standards")
        self.prove()

    def test_unresolved_major_finding_blocks_proof(self):
        self.initialize()
        self.start()
        self.check()
        finding = {"id": "F1", "severity": "major", "evidence": "Wrong result for refund"}
        self.review(verdict="fail", findings=[finding])
        self.prove(success=False)

    def test_pass_verdict_cannot_hide_unresolved_finding(self):
        self.initialize()
        self.start()
        self.check()
        self.review(findings=[{"id": "F1", "severity": "major", "evidence": "Incorrect persisted output"}],
                    success=False)

    def test_minor_deferral_requires_explicit_policy(self):
        self.initialize()
        self.start()
        self.check()
        self.review(findings=[{"id": "F1", "severity": "minor", "evidence": "Spacing issue",
                               "resolution": "deferred", "reason": "Scheduled follow-up"}], success=False)

    def test_explicit_minor_deferral_is_visible_and_allowed(self):
        self.plan["minor_deferral_policy"] = "Defer cosmetic issues with documented reason only"
        self.initialize()
        self.start()
        self.check()
        self.review(findings=[{"id": "F1", "severity": "minor", "evidence": "Spacing issue",
                               "resolution": "deferred", "reason": "No acceptance contract affected"}])
        self.prove()

    def test_resolved_finding_requires_explanation(self):
        self.initialize()
        self.start()
        self.check()
        self.review(findings=[{"id": "F1", "severity": "major", "evidence": "Wrong arithmetic",
                               "resolution": "fixed"}], success=False)

    def test_changed_engine_owned_log_invalidates_proof(self):
        self.initialize()
        self.start()
        self.check()
        self.review()
        logs = list((self.run / "artifacts").glob("check-*.log"))
        self.assertEqual(len(logs), 1)
        logs[0].write_text("Forged all tests pass\n")
        self.prove(success=False)

    def test_imported_review_is_copied_before_original_changes(self):
        self.initialize()
        self.start()
        self.check()
        self.review()
        (self.root / "review-independent-reviewer.json").write_text("Removed original report\n")
        self.prove()

    def test_stale_review_plan_hash_rejected(self):
        self.initialize()
        self.start()
        self.check()
        self.review(overrides={"plan_hash": "0" * 64}, success=False)

    def test_stale_review_source_hash_rejected(self):
        self.initialize()
        self.start()
        self.check()
        self.review(overrides={"source_hash": "0" * 64}, success=False)

    def test_source_edit_invalidates_previous_checks_and_review(self):
        self.initialize()
        self.start()
        self.check()
        self.review()
        (self.project / "src.py").write_text("def add(a, b):\n    return a + b + 1\n")
        self.prove(success=False)

    def test_acceptance_test_edit_invalidates_evidence(self):
        self.initialize()
        self.start()
        self.check()
        self.review()
        with (self.project / "test_src.py").open("a") as handle:
            handle.write("\n# Acceptance contract changed\n")
        self.prove(success=False)

    def test_unrelated_file_outside_scope_preserves_evidence(self):
        self.initialize()
        self.start()
        self.check()
        self.review()
        (self.project / "notes.txt").write_text("Unrelated scratch document\n")
        self.prove()

    def test_paused_run_blocks_commands_and_resume_restores_operation(self):
        self.initialize()
        self.start()
        self.cli("pause", "--reason", "Owner requested pause")
        self.check(success=False)
        self.cli("resume")
        self.check()

    def test_cancelled_run_cannot_resume_or_run(self):
        self.initialize()
        self.start()
        self.cli("cancel", "--reason", "Owner cancelled")
        self.check(success=False)
        self.cli("resume", success=False)

    def test_plan_mode_cannot_start_execution(self):
        self.plan["mode"] = "plan"
        self.initialize()
        self.start(success=False)

    def test_checkpoint_acceptance_requires_owner_note(self):
        self.plan["approval"] = "checkpoint"
        self.initialize()
        self.start()
        self.check()
        self.review()
        self.prove()
        self.cli("accept", "--checkpoint", "cp1", success=False)
        self.cli("accept", "--checkpoint", "cp1", "--approval-note", "Owner accepted this checkpoint")

    def test_forged_display_state_cannot_create_approval(self):
        self.initialize()
        self.start()
        projection = self.run / "state.json"
        forged = self.status()
        forged["checkpoints"]["cp1"]["status"] = "accepted"
        forged["checkpoints"]["cp1"]["gates"] = {"behavior": "passed", "review": "passed"}
        projection.write_text(json.dumps(forged))
        self.prove(success=False)
        self.assertNotEqual(self.status()["checkpoints"]["cp1"]["status"], "accepted")

    def test_stale_revision_rejects_late_actor_mutation(self):
        self.initialize()
        old = self.status()["revision"]
        self.start()
        self.cli("pause", "--reason", "Late actor", expected=old, success=False)

    def test_concurrent_mutations_accept_exactly_one_expected_revision(self):
        self.initialize()
        revision = self.status()["revision"]
        processes = []
        for reason in ("actor one", "actor two"):
            processes.append(subprocess.Popen([
                sys.executable, str(ENGINE), "pause", "--run", str(self.run),
                "--reason", reason, "--expected-revision", str(revision),
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
        outcomes = []
        for process in processes:
            output, error = process.communicate(timeout=10)
            outcomes.append((process.returncode, output, error))
        self.assertEqual(sum(code == 0 for code, _, _ in outcomes), 1, outcomes)

    def test_journal_corruption_is_not_silently_accepted(self):
        self.initialize()
        self.start()
        journals = list(self.run.glob("*.jsonl"))
        self.assertEqual(len(journals), 1, "Expected one canonical event journal")
        data = journals[0].read_bytes()
        journals[0].write_bytes(b"!" + data[1:])
        self.cli("status", success=False, revision=False)

    def test_truncated_last_journal_line_requires_explicit_recovery(self):
        self.initialize()
        self.start()
        journals = list(self.run.glob("*.jsonl"))
        self.assertEqual(len(journals), 1)
        with journals[0].open("ab") as handle:
            handle.write(b'{"partial":')
        self.cli("status", success=False, revision=False)
        self.cli("recover", "--truncate-final-line", revision=False)
        self.assertEqual(self.status()["checkpoints"]["cp1"]["implementer"], "builder")

    def test_dependency_scope_edit_invalidates_dependent_proof(self):
        (self.project / "consumer.py").write_text("from src import add\n")
        self.plan["requirements"].append({"id": "R2", "text": "Consumer contract"})
        dependent = self.checkpoint("cp2", ["R2"], ["cp1"])
        dependent["scope"] = ["consumer.py"]
        self.plan["checkpoints"].append(dependent)
        self.initialize()
        self.complete()
        self.start("cp2")
        self.check("cp2")
        self.review("cp2")
        (self.project / "src.py").write_text("def add(a, b):\n    return a - b\n")
        self.prove("cp2", success=False)

    def configure_ui(self):
        identity = {
            "fixture": "invoice-1", "language": "ar", "viewport": [390, 844],
            "reference": "approved-screen", "role": "academy-admin", "state": "loaded",
        }
        self.plan["checkpoints"][0]["gates"]["ui"] = {"kind": "ui", "identity": identity}
        # These fixture images test identity and artifact integrity, not visual quality.
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jVZkAAAAASUVORK5CYII=")
        reports = self.root / "reports"
        reports.mkdir(exist_ok=True)
        (reports / "capture.png").write_bytes(png)
        (reports / "reference.png").write_bytes(png)
        return identity

    def ui(self, identity, success=True, reviewer="visual-reviewer", artifacts=None):
        status = self.status()
        report = {
            "source_hash": status["checkpoints"]["cp1"]["source_hash"],
            "plan_hash": status["plan_hash"],
            "reviewer": reviewer, "verdict": "pass", "identity": identity,
            "artifacts": artifacts or {"capture": "capture.png", "reference": "reference.png"},
        }
        path = self.root / "reports" / "ui-report.json"
        path.write_text(json.dumps(report))
        return self.cli("ui", "--checkpoint", "cp1", "--report", path, success=success)

    def test_ui_matching_condition_metadata_can_pass(self):
        identity = self.configure_ui()
        self.initialize()
        self.start()
        self.check()
        self.review()
        self.ui(identity)
        self.prove()

    def test_ui_language_mismatch_is_invalid_before_judgment(self):
        identity = self.configure_ui()
        self.initialize()
        self.start()
        self.check()
        self.review()
        identity = dict(identity, language="en")
        _, imported = self.ui(identity)
        self.assertEqual(imported["evidence"]["verdict"], "invalid")
        self.prove(success=False)

    def test_ui_artifact_escape_cannot_be_imported(self):
        identity = self.configure_ui()
        (self.root / "outside.png").write_bytes((self.root / "reports" / "capture.png").read_bytes())
        self.initialize()
        self.start()
        self.ui(identity, artifacts={"capture": "../outside.png", "reference": "reference.png"}, success=False)

    def test_plan_revise_invalidates_previous_proof(self):
        self.initialize()
        self.start()
        self.check()
        self.review()
        self.prove()
        self.plan["requirements"][0]["text"] = "Addition plus new acceptance wording"
        self.plan_file.write_text(json.dumps(self.plan))
        self.cli("revise", "--plan", self.plan_file)
        self.cli("accept", "--checkpoint", "cp1", success=False)

    def test_idempotent_check_token_does_not_repeat_side_effect(self):
        self.change_check([sys.executable, "-c",
            "from pathlib import Path; p=Path('count.txt'); n=int(p.read_text()) if p.exists() else 0; "
            "p.write_text(str(n+1)); print('{\"total\":1,\"failed\":0,\"skipped\":0}')"])
        self.initialize()
        self.start()
        self.check(token="once")
        self.check(token="once")
        self.assertEqual((self.project / "count.txt").read_text(), "1")

    def test_failed_command_retry_bound_stops_real_execution(self):
        self.change_check([sys.executable, "-c",
            "from pathlib import Path; p=Path('count.txt'); n=int(p.read_text()) if p.exists() else 0; "
            "p.write_text(str(n+1)); print('{\"total\":1,\"failed\":1,\"skipped\":0}'); raise SystemExit(1)"])
        self.plan["checkpoints"][0]["gates"]["behavior"]["checks"][0]["max_attempts"] = 2
        self.initialize()
        self.start()
        self.check(success=False)
        self.check(success=False)
        self.check(success=False)
        self.assertEqual((self.project / "count.txt").read_text(), "2")

    def test_timeout_stops_spawned_child_process(self):
        heartbeat = self.root / "heartbeat.txt"
        child = self.root / "child.py"
        child.write_text("import time\nfrom pathlib import Path\np=Path(" + repr(str(heartbeat)) + ")\n"
                         "while True:\n    p.write_text(str(time.time_ns()))\n    time.sleep(.05)\n")
        self.change_check([sys.executable, "-c",
            "import subprocess,time,sys; subprocess.Popen([sys.executable," + repr(str(child)) + "]); time.sleep(20)"],
            timeout=0.5)
        self.initialize()
        self.start()
        self.check(success=False)
        self.assertTrue(heartbeat.exists(), "Child did not actually start")
        first = heartbeat.read_text()
        time.sleep(0.3)
        self.assertEqual(heartbeat.read_text(), first, "Timed out child continued executing")

    def test_owner_cancel_stops_an_active_command(self):
        marker = self.root / "active-heartbeat.txt"
        self.change_check([sys.executable, "-c",
            "import time; from pathlib import Path; p=Path(" + repr(str(marker)) + "); "
            "exec('for _ in range(60):\\n p.write_text(str(time.time_ns()))\\n time.sleep(.05)')"], timeout=10)
        self.initialize()
        self.start()
        revision = self.status()["revision"]
        process = subprocess.Popen([
            sys.executable, str(ENGINE), "check", "--run", str(self.run),
            "--checkpoint", "cp1", "--check", "unit", "--expected-revision", str(revision),
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.025)
        self.assertTrue(marker.exists(), "Command did not actually start")
        self.cli("cancel", "--reason", "Owner stops running command")
        process.communicate(timeout=1)
        first = marker.read_text()
        time.sleep(.2)
        self.assertEqual(marker.read_text(), first)
        self.assertEqual(self.status()["run_status"], "cancelled")

    def test_source_modified_during_check_cannot_create_current_evidence(self):
        self.change_check([sys.executable, "-c",
            "from pathlib import Path; Path('src.py').write_text('def add(a,b): return a-b\\n'); "
            "print('{\"total\":1,\"failed\":0,\"skipped\":0}')"])
        self.initialize()
        self.start()
        self.check(success=False)
        self.prove(success=False)

    def test_replaced_project_directory_cannot_resume_silently(self):
        self.initialize()
        self.start()
        prior_project = self.root / "original-project"
        self.project.rename(prior_project)
        self.project.mkdir()
        for source in prior_project.iterdir():
            if source.is_file():
                (self.project / source.name).write_bytes(source.read_bytes())
        self.cli("status", revision=False, success=False)

    def test_scope_parent_escape_is_rejected(self):
        self.plan["checkpoints"][0]["scope"] = ["../outside.py"]
        self.initialize(success=False)

    def test_symlink_scope_escape_is_rejected(self):
        outside = self.root / "outside.py"
        outside.write_text("private file\n")
        (self.project / "outside-link.py").symlink_to(outside)
        self.plan["checkpoints"][0]["scope"].append("outside-link.py")
        self.initialize(success=False)

    def test_run_directory_inside_project_is_rejected(self):
        self.run = self.project / "run"
        self.initialize(success=False)

    def test_negative_timeout_is_rejected(self):
        self.plan["checkpoints"][0]["gates"]["behavior"]["checks"][0]["timeout_seconds"] = -1
        self.initialize(success=False)

    def test_boolean_minimum_is_rejected(self):
        self.plan["checkpoints"][0]["gates"]["behavior"]["checks"][0]["min_tests"] = True
        self.initialize(success=False)

    def test_non_string_argv_is_rejected(self):
        self.plan["checkpoints"][0]["gates"]["behavior"]["checks"][0]["argv"] = [sys.executable, 1]
        self.initialize(success=False)

    def test_duplicate_checkpoint_ids_are_rejected(self):
        self.plan["checkpoints"].append(copy.deepcopy(self.plan["checkpoints"][0]))
        self.initialize(success=False)


if __name__ == "__main__":
    report_path = os.environ.get("CHECKPOINT_TEST_REPORT")
    engine_before = hashlib.sha256(ENGINE.read_bytes()).hexdigest()
    suite_before = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(WorkflowCLI)
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if report_path:
        report = {
            "command": [sys.executable, str(Path(__file__).resolve())],
            "engine": str(ENGINE),
            "engine_sha256_before": engine_before,
            "engine_sha256_after": hashlib.sha256(ENGINE.read_bytes()).hexdigest(),
            "suite_sha256_before": suite_before,
            "suite_sha256_after": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "tests_run": result.testsRun,
            "failures": [{"test": str(test), "traceback": tb} for test, tb in result.failures],
            "errors": [{"test": str(test), "traceback": tb} for test, tb in result.errors],
            "skipped": [{"test": str(test), "reason": reason} for test, reason in result.skipped],
            "duration_seconds": round(time.monotonic() - started, 3),
            "passed": result.wasSuccessful(),
            "scope": "Disposable project fixtures via subprocess CLI only",
        }
        Path(report_path).write_text(json.dumps(report, indent=2) + "\n")
    sys.exit(0 if result.wasSuccessful() else 1)
