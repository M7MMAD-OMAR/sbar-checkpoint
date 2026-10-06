# Engine CLI

English | [العربية](cli.ar.md)

The engine requires Python 3.10 or newer and POSIX process groups and advisory file locks. It uses only the standard library. Commands run from the project directory using the exact planned argv. No shell is inserted by the engine. The plan itself is trusted executable input: an argv can explicitly invoke a shell or a network tool. This is not an operating system sandbox.

## Commands

```sh
python3 scripts/workflow.py init --run /absolute/run --project /absolute/project --plan plan.json
python3 scripts/workflow.py status --run /absolute/run
python3 scripts/workflow.py start --run /absolute/run --checkpoint cp1 --actor implementer
python3 scripts/workflow.py check --run /absolute/run --checkpoint cp1 --check tests --token stable-invocation-key
python3 scripts/workflow.py review --run /absolute/run --checkpoint cp1 --report review.json
python3 scripts/workflow.py ui --run /absolute/run --checkpoint cp1 --report ui.json
python3 scripts/workflow.py prove --run /absolute/run --checkpoint cp1
python3 scripts/workflow.py accept --run /absolute/run --checkpoint cp1
python3 scripts/workflow.py pause --run /absolute/run --reason 'Owner pause'
python3 scripts/workflow.py resume --run /absolute/run
python3 scripts/workflow.py cancel --run /absolute/run --reason 'Owner cancellation'
python3 scripts/workflow.py revise --run /absolute/run --plan revised-plan.json
python3 scripts/workflow.py export --run /absolute/run
python3 scripts/workflow.py recover --run /absolute/run --truncate-final-line
```

All mutation commands except init accept `--expected-revision N`. A mismatch fails before the mutation. `status` returns the revision to use. Successful commands emit a JSON object on stdout. Validation failures emit `{"error":"reason"}` on stderr and return 2. A failed or invalid check emits its recorded evidence on stdout and returns 1. Status and export do not change journal revision. Plan revisions reset checkpoint projections and preserve prior snapshots in the event journal. Run directory must be outside the project tree.

`accept` requires a currently proven checkpoint. For `milestone` and `checkpoint` approval, pass `--approval-note 'User authorization and its source'`. The note records the operator's assertion of authorization, rather than authenticating a human. Delegated policy does not require a note. This API does not deploy, publish, merge, or extend authority.

## Plan format

```json
{
  "schema_version": 1,
  "mode": "feature",
  "approval": "delegated",
  "environment": "local-isolated",
  "requirements": [{"id": "R1", "text": "Round the total correctly"}],
  "checkpoints": [{
    "id": "cp1",
    "title": "Correct calculation",
    "covers": ["R1"],
    "depends_on": [],
    "scope": ["src.py", "test_src.py"],
    "gates": {
      "behavior": {
        "kind": "command",
        "checks": [{"id": "tests", "argv": ["python3", "-m", "unittest", "-v"],
                    "parser": "unittest", "min_tests": 1,
                    "timeout_seconds": 60, "max_attempts": 3}]
      },
      "review": {"kind": "review", "reviewers": 1, "axes": ["specification"]},
      "ui": {"kind": "not_applicable", "reason": "No visible interface change"}
    }
  }]
}
```

Modes: `feature`, `migration`, `repair`, `audit`, `plan`. Plan mode cannot start, check, prove, or accept. Audit and read-only modes describe a contract for the calling agent; the engine detects changes during a check but cannot prevent arbitrary source writes by an executable. Choose reviewed read-only commands and external restricted permissions when needed.

Approval policies: `delegated`, `milestone`, `checkpoint`. Environments: `local-isolated`, `read-only`, `staging`, `production`. Production requires `production_authorization: {"allowed": true, "reason": "specific existing authorization"}`. That field documents authorization and does not verify it. The environment is bound into the plan hash and evidence metadata, not an automatic network or secret boundary.

Requirements must be covered by at least one checkpoint or have `exclusions: [{"id":"R2","reason":"Explicitly outside this delivery"}]`. Dependencies must name known checkpoints without cycles. Scope values are safe relative file paths or file globs. New files can be listed before they exist. A glob matching directories is rejected; use `src/**/*.py`, rather than `src/**`. Parent traversal, absolute paths, and escaped symlinks are rejected. Common generated dependency directories are excluded. Scope must include acceptance tests, contract files, and other influential files. Dependency scopes are included transitively in descendants' source hashes. The engine cannot infer omitted dependencies or protect evidence against unlisted influential files.

The source hash covers project path/device/inode/git-root identity, scope patterns, matched filenames, file bytes, and file permission bits. It covers dirty and untracked files when matched by scope. It is intentionally not a claim that every file on the machine has been captured.

## Behavior gate

Supported parsers:

- `unittest`: requires a single `Ran N tests in ...` summary and final `OK` or `FAILED` result. It records failure/error/skipped counts and requires at least `min_tests` unskipped tests.
- `json`: command emits exactly one JSON object with nonnegative integer fields `total`, `failed`, `skipped`. Failed plus skipped cannot exceed total. Unskipped total must meet `min_tests`.
- `exit`: for lint, build, or similar tooling without test counts. It requires `min_tests: 0` and records no actual tests. Do not use it to claim acceptance tests ran.

Every gate command has explicit timeout and retry limit. Output is bounded to 4 MiB. Timeout, interruption, source changes while running, output overflow, or execution failure invalidate evidence. The command process group is terminated when the command ends. A descendant that deliberately creates another session can escape that group; use an external supervisor for commands requiring stronger isolation. Do not plan commands whose intent is to leave servers running.

An invocation token permanently identifies one source, plan, and check. Repeating a completed token returns its original evidence without running the command again. A changed source or plan rejects the token. A failed check can be retried with a new token, up to `max_attempts` for the same source/check/plan. An interrupted token cannot be replayed. A missing token creates a new UUID and is safe only for checks the operator intends to run again.

## Review report

Obtain `source_hash` and `plan_hash` from current status immediately before giving a reviewer its read-only task. Import a report shaped like this:

```json
{
  "source_hash": "current source hash",
  "plan_hash": "current plan hash",
  "reviewer": "independent-agent-1",
  "axis": "specification",
  "verdict": "pass",
  "findings": [],
  "artifacts": []
}
```

Verdict is `pass`, `fail`, or `invalid`. Reviewer must differ from the implementer. Reviewer identity is an asserted label, not a cryptographic identity. A two-reviewer gate requires two distinct labels and the planned distinct axes. Default axes are `specification` and `standards`; a one-reviewer gate defaults to `specification`.

Each finding requires `id`, `severity` (`blocker`, `major`, `minor`), and nonempty `evidence`. An optional `resolution` is `fixed`, `dismissed`, or `deferred`; any resolution requires a nonempty `reason`. Passing reports cannot contain unresolved findings. Minor findings can be deferred only when the plan explicitly includes a nonempty `minor_deferral_policy`; the report must mark them deferred and explain why. Deferring blockers or major findings never permits passing. A reviewer remains responsible for verifying that an asserted fix or dismissal is supported, rather than accepting implementer claims.

Optional artifact paths are relative to the report's parent directory, cannot contain traversal, and must remain inside that directory after resolving symlinks. The engine copies them into its artifact directory and hashes them. Reports with stale hashes are rejected before import.

## UI report

A required UI gate has `kind: "ui"` and an `identity` containing `fixture`, `language`, `reference`, `role`, `state`, and `viewport: [width,height]`. Add extra identity fields such as scale, network state, or fixture digest when the comparison requires them. The report identity must equal the full planned object exactly.

```json
{
  "source_hash": "current source hash",
  "plan_hash": "current plan hash",
  "reviewer": "visual-reviewer",
  "verdict": "pass",
  "identity": {
    "fixture": "invoice-1",
    "language": "ar",
    "reference": "approved prototype v1",
    "role": "manager",
    "state": "saved",
    "viewport": [390, 844]
  },
  "artifacts": {"capture": "capture.png", "reference": "reference.png"}
}
```

Both artifacts are required. Metadata mismatch is recorded as `invalid`, which prevents proof. Hashes detect later artifact modification. The engine validates artifact presence and bytes, rather than decoding images or judging appearance. The reviewer must actually inspect the images and perform required interaction checks; a successful import alone is not proof of visual quality.

## Journal, stop, and resume

`events.jsonl` is the authoritative checksum-linked journal. `state.json` is a convenience projection and is never trusted as the source of truth. `status` computes evidence freshness from current source hashes and copied artifact hashes. Stale accepted/proven checkpoints appear as verifying, and dependent checkpoints cannot progress until their dependencies are currently accepted again.

Pause and cancellation preserve files. A running check polls the run state every 100 milliseconds and terminates its process group when paused or cancelled. Keyboard interrupt pauses the run. A crashed engine leaves a pending command; explicitly pause, inspect the project and services, then resume to mark orphaned invocation tokens interrupted. Resume is refused while a pending command's engine process is still alive, preventing a pause/resume race. Do not assume a machine crash proves all external descendants stopped.

An incomplete final journal line causes all ordinary commands to fail. `recover --truncate-final-line` backs up the incomplete bytes, retains complete records, and pauses the run for inspection. It does not repair a corrupt complete record or accept edited state. Checksums are corruption detection, not authenticated anti-tamper protection. An actor who can edit the engine or recompute the journal chain can fabricate a history. Use an external verifier and restricted permissions for a stronger trust boundary.

`export` writes `status.json` and `resume.md`, describing current gates and the next safe action. It never restarts a service or reruns a command.
