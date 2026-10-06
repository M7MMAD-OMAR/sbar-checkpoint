# Claude Code adapter

## Load and execute

Invoke `/sbar-checkpoint` in Claude Code. Personal installation is ~/.claude/skills/sbar-checkpoint, honoring CLAUDE_CONFIG_DIR when set. Project installation is .claude/skills/sbar-checkpoint. Use the skill directory supplied by Claude. `${CLAUDE_SKILL_DIR}` in skill content resolves to that installed directory; it is not a shell variable shared with Codex.

Read files with Read, change authorized source with Write/Edit, and run the engine through Bash. Tool availability and permission rules come from the session. Do not add broad allowed-tools, bypass permissions or overwrite settings. The skill's audit and plan modes remain separate from Claude's permission mode; neither grants write authority.

## Independent reviewer

Use Agent with a fresh, non-fork general-purpose or custom reviewer context. Include the review packet, applicable rules, actual source/test paths, roles.md and cli.md. A fork or SendMessage continuation retains history and cannot serve as a fresh repair review. A custom reviewer can restrict tools; still supply all required rules because built-in agent types differ in injected project context.

Read actual available Agent schema. Do not hard-code deprecated Task or TaskOutput names. Wait for asynchronous completion; inspect returned output with Read when the host supplies a file. The reviewer writes only its report artifact outside source, completes owned checks before returning, and does not alter implementation. Import the JSON through the engine only after verifying its hashes.

Fallback: use a new `claude -p` session without --resume/--continue, --output-format json and --no-session-persistence. For headless prompts beginning with a slash use `/sbar-checkpoint TASK`. Keep existing authentication and model selection. Do not use --bare for an ordinary subscription discovery test; it changes authentication/loading behavior. Do not use --safe-mode or --disable-slash-commands when testing this skill.

## Cancel, cloud and UI

For owned background agent or Bash tasks, use the session's TaskStop control with the returned task ID, plus engine pause/cancel. Honor user interrupts even if a hook would continue. No hooks are installed. Browser capabilities require a real configured browser tool; Read can inspect supplied local images but does not exercise interactions.

Local personal skills do not automatically become Cowork or cloud skills. Enable an account skill or distribute the repository skill on those surfaces, then separately verify Python, filesystem access and reviewer capabilities. Validate those environments separately before relying on their gates.

Official references: [skills](https://code.claude.com/docs/en/skills), [subagents](https://code.claude.com/docs/en/sub-agents), [tools](https://code.claude.com/docs/en/tools-reference).
