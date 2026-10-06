# Role contracts

## Planner

Read user requirements and repository rules. Produce checkpoints, requirement coverage, scopes, exact checks and required reviewer/UI gates. Record exclusions and unresolved business choices. Do not invent permission, credentials or prior user decisions.

## Implementer

Implement one started checkpoint, preserve existing work, run planned checks and disclose limitations. Keep a stable actor ID in engine start. Do not write independent reviewer reports. Fixers count as implementers for the source they change.

## Independent reviewer

Start with a fresh context. Receive the requirement contract, applicable repository rules, project path, checkpoint source/plan hashes and artifact output destination. Inspect actual source and tests, run a small discriminating reproduction if useful, and write a structured report. Do not edit implementation. Before submitting, verify hashes remain current. Do not see other review verdicts until your report is saved.

For two reviewers, use separate contexts and axes such as requirement correctness and operational correctness. Both inspect the actual source. A second name on the same report is not two independent reviews.

Use scripts/hosts.py review-packet to capture the current contract and hashes without prior verdicts. It is an input packet, not evidence. Refresh hashes with hosts.py review-state instead of workflow.py status/export or journal reads, which expose earlier verdicts. Follow the matching host adapter for a fresh Codex subagent, Claude Agent or Hermes delegate_task. Do not copy its placeholder verdict into the real report. Retain the reviewer's actual artifact and inspect it before engine import.

Report example, consult cli.md for exact required fields:

```json
{
  "reviewer": "independent-reviewer-1",
  "axis": "specification",
  "source_hash": "CURRENT_CHECKPOINT_HASH",
  "plan_hash": "CURRENT_PLAN_HASH",
  "verdict": "pass",
  "findings": []
}
```

On failure, report findings with ID, severity, file/location, reproduction, evidence and status. This is a template, not evidence. Never copy `pass` without doing the work.

## UI reviewer

Inspect reference and actual images in matching conditions, then evaluate relevant interactions with the browser or supplied recording. Report pass/fail/invalid, conditions, artifact paths, source/plan hashes, reviewer and findings. Different conditions yield invalid. Keyboard, RTL, validation, busy/error/success and persistence checks depend on the task, not a universal checklist.

## Owner or delegated coordinator

Resolve product choices, preserve prior authorization and accept proven outcomes under the selected policy. Record which choices were delegated and which require an actual owner decision. Full-write coordinator capability is an explicit trust limitation, not an excuse to fabricate another role's evidence.
