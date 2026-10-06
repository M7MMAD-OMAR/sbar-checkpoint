# Project adapters

Keep machine-specific paths and secrets out of the portable skill. A project profile is a local source for plan construction, not automatic permission or a magic universal check command. Read the actual project's scripts and rules each time.

## Useful profile fields

Record project path, applicable rules, environment ownership, package manager, check argv arrays, source/test/config scopes, local fixture setup, UI reference and capture conditions, service cleanup and known provider gaps. Never save API keys or passwords. Environment variable names alone are fine; logs should still be reviewed for sensitive output.

## General use cases

- Financial services: duplicate operation IDs, tenant boundaries, conflicting amounts and persisted state after failure.
- Offline synchronization: replay order, restart behavior, durable acknowledgements and schema compatibility.
- Booking systems: concurrent reservation/cancellation, role boundaries and private media access.
- Database migrations: parity with the reference schema, disposable fixtures, rollback validation and provider limits.
- Design systems: keyboard/RTL behavior, consumer API compatibility and token verification.
- Document editors: revision-safe editing/export and recovery after interrupted writes.

These are plan inputs to investigate, not evidence that a product, provider or deployment passed.

## Example adaptation sequence

Read rules and current scripts, choose one small accepted outcome, create an isolated fixture if real infrastructure is unavailable, then declare the resulting evidence boundary. Use tests appropriate to the framework rather than replacing its suite with a custom fake runner. Include provider/device limitations in delivery.
