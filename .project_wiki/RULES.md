# Codex-WikiGuard — RULES

## General

1. Hooks run inside Codex; they are **not** a replacement for the LLM.
2. Keep everything simple — rules-based, file I/O, JSON output only.
3. Do NOT implement Subagent, PostToolUse, PreCompact, or `run_task.py` in v1.
4. All hooks follow Codex official wire format (`hookSpecificOutput`, `systemMessage`).

## Hook contracts

### UserPromptSubmit

- **Codex Event**: `UserPromptSubmit`
- **Trigger**: Before every user prompt is sent to Codex.
- **Read**: HOME.md, RULES.md, CURRENT_TASK.md, JUDGE.md.
- **Output**: `{ "hookSpecificOutput": { "hookEventName": "UserPromptSubmit", "additionalContext": "..." } }`
- **No compression** — raw file contents only.

### PreToolUse

- **Codex Event**: `PreToolUse`
- **Matcher**: `{"tool": "^Bash$"}` (only triggers on Bash tool calls)
- **Trigger**: Before every Bash tool invocation from Codex.
- **Input**: `turn_payload["tool_input"]["command"]` (fallback to `arguments.command`)
- **Denylist match**: return `{ "hookSpecificOutput": { "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..." } }`
- **No match**: return `{}` (allow through)
- **Denylist** (first version):
    - `rm -rf`
    - `sudo`
    - `git reset --hard`
    - `git clean -fd`
    - `chmod -R`
    - `chown -R`
    - `curl | sh`
    - `wget | sh`

### Stop

- **Codex Event**: `Stop`
- **Trigger**: On Codex turn end (stop signal).
- **Read**: `last_assistant_message` from the turn payload.
- **Write**: `JUDGE.md` (human-readable) and `judge_latest.json` (machine-readable).
- **Return**: `{ "systemMessage": "Codex-WikiGuard wrote human_review judgment." }`
- **Default verdict**: `human_review` — no auto-loop, no `decision: block`.

## Versioning

- v1 is a minimal guard. Do not add LLM calls or complex logic.
- When hooks are stable, consider enabling `continue` verdicts later.
