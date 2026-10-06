# Hosts, portability and ownership

## Shared engine

The local engine uses Python 3.10+ and the standard library on POSIX. Linux is tested. macOS uses the same APIs but requires testing on a Mac before claiming certification. Windows requires a POSIX environment such as WSL, with the host and Python operating on the same filesystem; native Windows is unsupported. Agent host compatibility is separate from OS support.

Use the common SKILL.md, plans and report schemas in all three hosts. Read only [Codex](host-codex.md), [Claude Code](host-claude.md) or [Hermes](host-hermes.md). No global hooks, auto-continuation loop, credentials or provider-specific model is installed. `doctor.py` observes paths and executable presence, not authentication, model quality, tool permission or successful discovery.

## Native installation

`scripts/hosts.py paths --host all` prints user destinations. `scripts/install.py --host codex|claude|hermes --receipt RECEIPT` installs a new native copy. It refuses existing directories and symlinks. Use `--scope project --project PROJECT` for project installation. Do not blindly replace owner-modified skills. The source and engine are identical; `agents/openai.yaml` is additional Codex metadata and is not required by the other hosts.

| Host | User root | Root override | Project location | Invoke |
| --- | --- | --- | --- | --- |
| Codex | ~/.codex/skills | CODEX_HOME | .agents/skills | $sbar-checkpoint |
| Claude Code | ~/.claude/skills | CLAUDE_CONFIG_DIR | .claude/skills | /sbar-checkpoint |
| Hermes | ~/.hermes/skills | HERMES_HOME | .hermes/skills | /sbar-checkpoint |

The installer uses a supported Codex user skill directory. Hosts can support additional directories; the table is the installer's policy, not an exhaustive discovery specification. Hermes profiles must supply their active home with HERMES_HOME when installing from an external shell; do not assume the default profile is active. Project Hermes skills require a trusted Git root. Claude Cowork/cloud does not read a workstation's user folder; configure account skills or repository distribution separately. Uploading a bundle does not prove local engine execution or native agent tools on those surfaces.

## Independent review

Use `hosts.py review-packet --run RUN --checkpoint ID --reviewer ACTOR --axis AXIS --output NEW_PACKET`. Place the packet outside the project and run trees. It contains the contract and current hashes without previous verdicts. This input is not review evidence. The reviewer refreshes hashes with `hosts.py review-state --run RUN --checkpoint ID`; it never reads status/export or the journal because those reveal earlier verdicts. Read project rules and source independently; return actual report JSON from roles.md, then import it through `workflow.py review`. Refuse a stale result. A new actor string or a resumed conversation does not establish independence.

## Move between hosts

Stop or finish owned commands before switching coordinators. Keep the same absolute project and run paths, original plan and journal. Read fresh engine status from the new host's identical engine, including accepted checkpoints, dependency invalidation and pending commands. Preserve approval policy and user stop intent. Never reinitialize an existing run or reuse a stale snapshot to bypass a failed gate. A pending command after a crash requires reconciliation; do not claim it finished or replay a side effect blindly. Skill installation alone does not move files to another computer or cloud environment.

## Resource ownership

Set check timeouts in the plan. The runner bounds retained output and kills its process group on timeout or SIGINT. Checks are foreground bounded commands, not launchers for shared services. Host-native background processes belong to their spawning session and must finish or be explicitly stopped before delivery. Stop the correct owned task; never kill shared services or another session's workers.

The journal lock serializes mutations. A running check polls pause/cancel every 100 milliseconds. A full-write agent can still edit executable code or journal contents. Memory quotas and independent process sessions need OS/container controls. Pi and other hosts have no dedicated adapter in this version.

## Primary sources

Official references: [Claude skills](https://code.claude.com/docs/en/skills), [Claude subagents](https://code.claude.com/docs/en/sub-agents), [Claude tools](https://code.claude.com/docs/en/tools-reference), [Hermes skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/), [Hermes delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation/), [Hermes authoring](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills). Recheck current tool schemas before using version-specific controls.
