# Hermes Agent adapter

## Load and execute

Use `/sbar-checkpoint` interactively or preload with `hermes chat --oneshot --skills sbar-checkpoint --query-file PROMPT_FILE`. A query passed with -q is literal text and is not necessarily parsed as a slash command. Do not use --ignore-rules or --safe-mode when testing skill preloading.

Install into the active profile's HERMES_HOME/skills/sbar-checkpoint, default ~/.hermes/skills/sbar-checkpoint. A custom profile needs its resolved home set when installing from an external shell. Project install uses .hermes/skills within a trusted Git root. Use skills_list/skill_view for discovery. skill_view returns skill_dir; `${HERMES_SKILL_DIR}` in loaded skill content resolves to it. Keep the actual directory, since external skills can live elsewhere.

Use terminal for bounded foreground engine/check commands, and available file read/write tools for authorized source. Inspect the session's toolset. Terminal can run scripts even when a dedicated file tool is absent. Do not configure a new provider, add API keys or grant permission to satisfy a gate. The core engine needs no model or network connection; Hermes's own runtime may need its normal dependencies.

## Independent reviewer

Use delegate_task with a new task: tasks=[{goal, context}]. Supply the review packet, paths, applicable rules, roles.md, cli.md and a new report output path. Consult the installed schema before adding options. Native child contexts are fresh, but source directories are shared by default. Tell reviewers to leave implementation unchanged and finish owned checks before returning.

Top-level delegations can return a background handle rather than a completed report. Wait for the actual completion notice and saved JSON. Use action=list to inspect owned workers and action=stop with subagent_id to interrupt. Steering a child does not create a new review context; spawn a new child after repairs. Do not supply earlier verdicts or assume a second role name creates independence. A per-task output_schema can help formatting, but schema_valid=false or truncated/interrupted output is not a passed review.

If delegation is unavailable, use an authorized new hermes chat --oneshot process with no resume/continue and the user's provider configuration. Keep source and reports on a filesystem the new process can access. Report actual failure when it cannot inspect source or authenticate; do not fabricate a report.

## Cancel and UI

Use engine pause/cancel and the native owned delegate stop control. User /stop interrupts session-owned work; ordinary follow-up messages may not cancel background children. terminal background work returns a process handle; use the available process_manage poll/wait/kill controls for that handle. Do not leave checks running when a child exits. Child process cleanup and explicit process handoff depend on the installed version. A restarted host cannot prove an interrupted command completed.

Use configured browser tools for interactions and vision_analyze or actual multimodal tools for image comparisons. If pixels or required browser controls are unavailable, leave the UI gate unproven. Do not substitute text commentary for visual review.

Official references: [skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/), [delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation/), [toolsets](https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference).
