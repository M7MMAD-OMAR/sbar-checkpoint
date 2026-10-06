# Verification and host trials

English | [العربية](validation.ar.md)

[README](../README.md) | [Getting started](getting-started.md)

## Repeat the deterministic checks

Run from the repository root with Python 3.10+ on POSIX:

```sh
python3 -B -m unittest discover -s tests -v
python3 tools/check_public.py
python3 tools/demo.py
python3 tools/package.py --output dist
```

The regression suite exercises transitions, requirement coverage, source and artifact freshness, command counts, retries, tokens, interruption, review contracts, host paths and installation. GitHub Actions runs it on Linux with Python 3.10, 3.12 and 3.14, and on macOS with Python 3.12. The linked [workflow](https://github.com/M7MMAD-OMAR/sbar-checkpoint/actions/workflows/verify.yml) shows current results.

The disposable demo deliberately reproduces a failing calculation, repairs it and executes two tests. It sets review to not applicable for an engine mechanics demonstration and explicitly reports `independent_review_performed: false`. The [full walkthrough](getting-started.md#local-engine-walkthrough) instead requires a real fresh reviewer before acceptance.

Arabic and English guides preserve the same executable command and JSON blocks. Task prompts are translated. Their language links and local anchors can be checked without invoking a model provider.

## Repeat native agent smoke trials

Use a disposable Python project, keep plan/run/report files outside its source tree, and preserve its initial file hashes. Configure the agent normally before beginning; the skill never configures authentication or chooses a provider for you.

| Surface | Invocation | Meaningful trial |
| --- | --- | --- |
| Codex | `$sbar-checkpoint` in a fresh native context | Arabic plan-only and English read-only audit |
| Claude Code | `/sbar-checkpoint` in a fresh session | Arabic plan-only and English read-only audit |
| Hermes Agent | `--skills sbar-checkpoint` in a new one-shot session | English plan-only and Arabic read-only audit |

These flows have been exercised using their actual installed skill and engine. An independent check compared scoped fixture bytes, journal transitions and recorded test counts. This verifies the observed local flows; it does not certify every provider, host extension or cloud environment. Scoped source preservation does not imply an unchanged full project tree: host extensions can generate indexes or cache files.

For plan-only trials, ask the agent to create two dependent checkpoints in `plan` mode, call doctor plus `init` and `status`, and stop. Require no `start`, `check`, `prove` or `accept`. The journal should contain only initialization and the evidence counts should remain zero.

For audit trials, use this deliberately incorrect function:

```python
def visible_rows(rows, tenant):
    return [row for row in rows if row["active"]]
```

Add two unittest checks: one active row belonging to the requested tenant should be returned, and an active row from another tenant should be excluded. Pre-review the test command as read-only, then ask the agent to run it through an `audit` checkpoint with the `unittest` parser and `min_tests: 2`. A useful result is two executed tests and one expected failure demonstrating the leak. The behavior gate must remain failed and required review pending. Do not repair, prove or accept in this trial.

Run native headless prompts through the documented entry points, using a prompt file so its text cannot be interpreted by a shell:

```sh
codex exec --sandbox workspace-write --ephemeral - < prompt.txt
claude -p --output-format json --no-session-persistence < prompt.txt
hermes chat --oneshot --skills sbar-checkpoint --query-file prompt.txt
```

For Claude, the file begins with `/sbar-checkpoint`; for Codex it begins with `$sbar-checkpoint`. Codex CLI and desktop contexts are separate observations. If a configured CLI model or authentication is unavailable, record that invocation as blocked rather than treating an engine test as a successful CLI test. Do not bypass permissions, edit provider settings or fabricate review evidence to finish a smoke trial.

## Check downloaded bundles

Each release includes a portable ZIP, an identical `.skill` archive and SHA256 checksums. Verify the download, extract into an owned temporary directory, install into an empty host directory, and execute its `scripts/workflow.py --version`. The skill release version and engine version are separate; documentation releases can retain the same engine version.

Follow the [installation guide](getting-started.md) and [contributor checks](../CONTRIBUTING.md). Keep raw model traces, account details, local paths and run artifacts out of public issues and commits.
