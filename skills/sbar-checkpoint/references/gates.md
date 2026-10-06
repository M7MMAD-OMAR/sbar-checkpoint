# Evidence gates

## Behavior

Planned command arguments are arrays, not shell strings. The engine captures exit status and logs. `unittest` parses real unittest totals. `json` expects a terminal structured test summary as documented in cli.md. `exit` is for builds or lint, and does not certify test count. Require meaningful non-skipped tests when the acceptance contract needs tests.

Test absence, failure and success. For replayable financial commands test a duplicate operation, concurrent call where relevant, changed amount under the same key, incorrect tenant and persisted state after a rejected operation. A memory-only fixture does not prove database isolation, RLS or production concurrency.

Keep contract tests independent from assertions describing the implementation. If all tests are skipped or none execute, the test gate remains unproven. Error import or missing environment is not valid TDD proof of absent behavior.

## Review

Read roles.md for report format. The engine requires current source and plan hashes, an independent actor ID, a verdict, a documented axis and findings. A passing sentence without a review of actual source is insufficient, even if structurally accepted.

Reports are bound to artifact content and source identity. Changing a copied evidence artifact or a scoped source file makes the evidence stale. Original external reports are inputs; their immutable copied bytes are the evidence. Actors are recorded assertions. A separate process or subagent with a fresh context supplies practical independence; cryptographic authentication is outside this local engine.

Do not suppress minor findings without explicit policy. The shipped engine treats unresolved reported findings conservatively. Use a new evidence-backed reviewer report after a fix, rather than editing a stored report.

## UI

Match language, role, fixture, viewport and capture state to the planned identity. Supply reference and actual capture artifacts. Their hashes are evidence of exact inputs, not evidence of visual quality by themselves. A qualified image reviewer must inspect them; interaction needs browser/application execution evidence as well.

Declare a UI gate only when it applies. Absence of a required browser or reference is a blocker. A metadata mismatch is invalid, not pass/fail on appearance. Do not compare a logged-in Arabic screen to an English anonymous reference.

The engine checks report identity and artifact consistency. It does not implement a vision model, accessibility scanner or pixel threshold and cannot determine if a reviewer actually saw the images. Record tools and tested actions in findings/evidence and avoid overstating automation.

## Limits

Local evidence is not certification of hosted providers, production load or inaccessible devices. State which environment ran. Plan/source/artifact hashes and a checksum journal protect consistency; the full-write owner can alter all of them. Put critical verification outside that owner's write boundary when required.
