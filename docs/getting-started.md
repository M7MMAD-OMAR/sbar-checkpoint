# Getting started

Language: [English](getting-started.md) | [العربية](getting-started.ar.md)

Sbar Checkpoint has two entry points: invoke the skill through your agent host, or run its local engine directly. The host does implementation, independent review, and any browser or image work. The engine records evidence and validates transitions.

## Install for your host

The Skills CLI can install user-level copies for all three hosts:

```sh
npx skills add M7MMAD-OMAR/sbar-checkpoint --skill sbar-checkpoint -a codex claude-code hermes-agent -g
```

The bundled installer lets you select one host and respects configured root paths:

```sh
git clone https://github.com/M7MMAD-OMAR/sbar-checkpoint.git
cd sbar-checkpoint
python3 skills/sbar-checkpoint/scripts/hosts.py paths --host all
python3 skills/sbar-checkpoint/scripts/install.py --host codex
```

Choose `--host claude` or `--host hermes` instead for those hosts. The installer refuses existing directories and symlinks. If a copy exists, inspect it and preserve local changes before choosing an update method. It does not configure models, credentials, permissions, or global hooks.

| Host | Default user destination | Root override | Invocation |
| --- | --- | --- | --- |
| Codex | `~/.codex/skills/sbar-checkpoint` | `CODEX_HOME` | `$sbar-checkpoint` |
| Claude Code | `~/.claude/skills/sbar-checkpoint` | `CLAUDE_CONFIG_DIR` | `/sbar-checkpoint` |
| Hermes Agent | `~/.hermes/skills/sbar-checkpoint` | `HERMES_HOME` | `/sbar-checkpoint` |

Root overrides must be absolute paths. For a custom Hermes profile, set `HERMES_HOME` to the active profile's resolved home before invoking the installer from an external shell.

Project installation uses `.agents/skills` for Codex, `.claude/skills` for Claude Code, and `.hermes/skills` for Hermes:

```sh
python3 skills/sbar-checkpoint/scripts/install.py \
  --host codex --scope project --project /absolute/path/to/project
```

Hermes project discovery requires a trusted Git root. Host discovery policies can change; consult the [host reference](../skills/sbar-checkpoint/references/hosts.md) and the matching adapter for your installed version. Cloud surfaces need their own distribution and execution setup.

After installation, use the skill path supplied by the host to run its doctor:

```text
python3 SKILL/scripts/doctor.py --host codex
```

Replace `SKILL` with the actual directory and select the correct host. Doctor checks observable Python, platform, executable, and file prerequisites. It does not verify authentication, skill discovery, or independent agent availability.

## Ask for an outcome

In Codex, start with `$sbar-checkpoint`. In Claude Code and interactive Hermes, start with `/sbar-checkpoint`. The remaining prompt can describe the task naturally. Hermes also supports explicit noninteractive preloading:

```sh
hermes chat --oneshot --skills sbar-checkpoint --query-file prompt.txt
```

Keep the outcome, constraints, environment, and authorization in the prompt. The examples below are task templates to adapt to your repository, not claims that a project or host integration has been tested.

### Repair

```text
Use sbar-checkpoint to repair duplicate request handling in this repository.
Preserve the public API and existing uncommitted work. Inspect the current
tests and reproduce the failure first. Use a local isolated test environment.
Cover retry behavior, concurrent requests, and tenant boundaries. Obtain a
fresh independent specification review. You are authorized to make the source
and test changes needed for this repair. Do not deploy. Deliver the implemented
behavior, fresh evidence, and any unresolved environment gaps.
```

### Read-only audit

```text
Use sbar-checkpoint in audit mode to assess authorization checks in this
repository. Do not modify source, configuration, or data. Run only reviewed
read-only checks in a local environment, with restricted permissions where
available. Save the plan and findings outside the source tree. Trace each
finding to a requirement and source evidence. Obtain an independent review
of the findings and report missing evidence without inventing a pass.
```

The read-only rule is part of the host contract. The engine is not a sandbox: a planned executable can still write files unless external permissions prevent it. Use `plan` mode when you want only a plan; that mode refuses execution and acceptance commands.

### Multi-stage migration

```text
Use sbar-checkpoint to plan and implement a local migration from the legacy
record format to the new versioned format. Define separate checkpoints for
compatibility readers, a repeatable backfill, writer cutover, and removal of
legacy reads. Make dependencies explicit. Test partially migrated records,
reruns, interruption recovery, and rollback constraints in isolated fixtures.
Include schemas, migration code, tests, and configuration in source scopes.
Use independent specification and standards reviewers for risky checkpoints.
Prepare a reviewable cutover decision under milestone approval. Do not run a
production migration or publish changes. Record any provider behavior that
cannot be demonstrated locally.
```

A dependent checkpoint includes ancestor scopes in its digest. Editing the compatibility reader after accepting it can invalidate both that checkpoint and later migration evidence.

### UI change with matched evidence

```text
Use sbar-checkpoint to repair the mobile form layout against the approved
reference. Include the affected styles, components, fixtures, and interaction
tests in scope. Compare the same saved fixture, role, language, state, and
390 by 844 viewport. Capture the current UI and reference, inspect both with
actual image tools, and test keyboard focus, validation errors, and submission.
Require independent source review and a UI gate. If the host cannot inspect
images or run the required interactions, leave that evidence unproven.
Do not deploy.
```

The UI report must exactly match the planned identity and include both capture and reference artifacts. The engine checks metadata and artifact hashes; the reviewer performs the visual judgment. See the [UI schema](../skills/sbar-checkpoint/references/cli.md#ui-report).

### Pause and resume

```text
Pause this sbar-checkpoint run now. Stop the checks and background work owned
by this task. Preserve the project, plan, journal, and completed evidence.
Export the current state and next safe action. Do not start more work.
```

Later, explicitly authorize continuation:

```text
Resume the existing sbar-checkpoint run. Read fresh status, reconcile pending
commands and any ambiguous external effects, then continue ready checkpoints
under the original scope and approval policy. Refresh stale checks and reviews.
```

A host switch or another follow-up message does not override an explicit pause. Keep the same project and run paths and one coordinator at a time.

## Local engine walkthrough

This small repair demonstrates the commands mechanically. A change this size normally needs direct verification. Run it from the cloned repository in a POSIX shell with Python 3.10+. It uses a temporary workspace and creates no production services. These commands illustrate a local fixture, not a host acceptance test.

First select the bundled engine and create sibling project, plan, and run locations:

```sh
SKILL="$PWD/skills/sbar-checkpoint"
ENGINE="$SKILL/scripts/workflow.py"
WORK="$(mktemp -d)"
PROJECT="$WORK/project"
RUN="$WORK/run"
mkdir -p "$PROJECT/tests"
python3 "$SKILL/scripts/doctor.py" --host codex
```

The run must be outside the project tree. Keep plans, reviewer inputs, and reports outside source scopes too. Do not put secrets in commands, plans, or logs.

Create the broken implementation and two acceptance tests:

```sh
cat > "$PROJECT/total.py" <<'PY'
def total_cents(subtotal, fee):
    return subtotal - fee
PY
cat > "$PROJECT/tests/test_total.py" <<'PY'
import unittest
from total import total_cents

class TotalTests(unittest.TestCase):
    def test_adds_fee(self):
        self.assertEqual(total_cents(1200, 75), 1275)

    def test_zero_fee(self):
        self.assertEqual(total_cents(1200, 0), 1200)
PY
```

Create a plan before implementing. The command uses an argv array rather than a shell string. The `unittest` parser requires actual executed tests; an exit-only check cannot satisfy a test count.

```sh
cat > "$WORK/plan.json" <<'JSON'
{
  "schema_version": 1,
  "mode": "repair",
  "approval": "delegated",
  "environment": "local-isolated",
  "requirements": [
    {"id": "R1", "text": "Add the fee to the subtotal in integer cents"},
    {"id": "R2", "text": "Preserve the subtotal when the fee is zero"}
  ],
  "checkpoints": [{
    "id": "core",
    "title": "Repair fee calculation",
    "covers": ["R1", "R2"],
    "depends_on": [],
    "scope": ["total.py", "tests/test_total.py"],
    "gates": {
      "behavior": {
        "kind": "command",
        "checks": [{
          "id": "unit",
          "argv": ["python3", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
          "parser": "unittest", "min_tests": 2,
          "timeout_seconds": 60, "max_attempts": 3
        }]
      },
      "review": {"kind": "review", "reviewers": 1, "axes": ["specification"]},
      "ui": {"kind": "not_applicable", "reason": "No visible interface change"}
    }
  }]
}
JSON
python3 "$ENGINE" init --run "$RUN" --project "$PROJECT" --plan "$WORK/plan.json"
python3 "$ENGINE" start --run "$RUN" --checkpoint core --actor implementer
python3 "$ENGINE" check --run "$RUN" --checkpoint core --check unit --token baseline
```

The baseline check should return 1 and record a failed test. Read its output, then make the repair and run a fresh invocation:

```sh
cat > "$PROJECT/total.py" <<'PY'
def total_cents(subtotal, fee):
    return subtotal + fee
PY
python3 "$ENGINE" check --run "$RUN" --checkpoint core --check unit --token repaired
python3 "$ENGINE" status --run "$RUN"
```

Checks run from the project directory. A completed token is bound to its source, plan, and check. Repeating `repaired` on the same source returns the saved result without execution. Changing source rejects that token; use a new token for the new source. This mechanism does not reconcile payment or migration side effects.

Prepare a fresh independent reviewer input outside the project and run:

```sh
python3 "$SKILL/scripts/hosts.py" review-packet \
  --run "$RUN" --checkpoint core --reviewer independent-reviewer \
  --axis specification --output "$WORK/review-input.json"
```

Give a fresh subagent or authorized fresh host process that packet, the project rules, scoped source, and [review report contract](../skills/sbar-checkpoint/references/roles.md). Ask it to inspect the implementation and tests and save its actual report to `$WORK/review.json`. It must verify the current hashes using `hosts.py review-state` before returning and avoid previous verdicts. A new actor label alone does not create an independent reviewer.

The report contains the current `source_hash` and `plan_hash`, the reviewer and axis, its actual verdict, and findings. Do not create a passing report yourself to finish the example. If independent review is unavailable, the checkpoint remains unproven.

Once a real passing report exists and any findings have been resolved with fresh evidence:

```sh
python3 "$ENGINE" review --run "$RUN" --checkpoint core --report "$WORK/review.json"
python3 "$ENGINE" prove --run "$RUN" --checkpoint core
python3 "$ENGINE" accept --run "$RUN" --checkpoint core
python3 "$ENGINE" export --run "$RUN"
python3 "$SKILL/scripts/viewer.py" --run "$RUN" --output "$WORK/report.html"
```

`delegated` acceptance uses the existing authorization. For `milestone` or `checkpoint` policy, `accept` also requires `--approval-note` recording the actual authorization and its source. The command does not authenticate that note or deploy anything.

The export writes `status.json` and `resume.md` in the run. The viewer creates a local HTML report. A source edit after acceptance makes the earlier evidence stale; inspect fresh status and rerun the affected gates.

For an active run, pause and resume use:

```sh
python3 "$ENGINE" pause --run "$RUN" --reason 'User requested a pause'
python3 "$ENGINE" export --run "$RUN"
# Run only after the user explicitly resumes the work:
python3 "$ENGINE" resume --run "$RUN"
python3 "$ENGINE" status --run "$RUN"
```

Pause and cancellation preserve files and terminate owned check process groups. After a crash, inspect pending commands and external effects before resuming. Do not replay an ambiguous external operation blindly. The [CLI reference](../skills/sbar-checkpoint/references/cli.md) covers pending tokens, journal recovery, expected revisions, plan changes, parser contracts, and exact schemas.
