# Codex adapter

## Load and execute

Invoke `$sbar-checkpoint`. Resolve the absolute directory from the available skill catalog. Use the current terminal execution tool to run its Python scripts. In Codex desktop this may be `exec_command` exposed through `functions.exec`; other versions expose it directly. Follow the actual tool schema instead of copying wrapper syntax from another session.

Install into the active CODEX_HOME/skills or the supported workstation default ~/.codex/skills with `install.py --host codex`. Project install uses .agents/skills. `agents/openai.yaml` supplies display metadata only. The workflow never depends on a Codex Stop hook or automatic task recreation.

## Independent reviewer

When permitted and available, create a fresh subagent with `fork_turns="none"`. Supply the review packet, actual project path, rules, relevant skill references and report destination. Give reviewers unique actor IDs and no earlier verdicts. Read the final report, verify hashes, and import it. For repair reviews create a new context, not a message to an old reviewer.

If the host exposes no agent capability, use an authorized fresh `codex exec` process with no resume or continue, a scoped prompt, and the user's existing provider configuration. Do not change the configured model to invent compatibility. If CLI tooling or credentials fail, leave the required review unproven. Source pasted into a tool-less reviewer is a source review, not a runtime test.

## Cancel and UI

Use engine pause/cancel plus the actual host interrupt control for owned work. Collaboration interrupt tools, command SIGINT and desktop Stop have different ownership; inspect IDs before stopping. Browser and image tools are optional capabilities. Without real captures and interaction evidence leave a required UI gate pending. Engine tests do not certify a browser workflow.
