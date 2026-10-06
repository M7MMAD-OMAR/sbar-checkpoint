# Contributing

Language: [English](CONTRIBUTING.md) | [العربية](CONTRIBUTING.ar.md)

Report a reproducible issue with the host, Python version, operating system,
expected behavior and actual command result. Remove credentials, project data
and private paths from logs before attaching them.

For changes, keep the engine dependency-free and retain the shared plan/report
schemas across hosts. Add a regression for a demonstrated bug or a meaningful
new contract. Use isolated fixtures instead of live services.

Run from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
python3 tools/check_public.py
python3 tools/demo.py
python3 tools/package.py --output dist
```

Keep the skill body concise. Put host differences in its references. Update the
getting-started guide when changing public commands. Diagrams must agree with
the actual transitions and trust boundary. Do not commit run logs, transcripts,
receipts, generated test reports or environment-specific examples.
