# Codex-WikiGuard — RULES

## General

1. Hooks run inside Codex; they are **not** a replacement for the LLM.
2. Keep everything simple — rules-based, file I/O, JSON output only.
3. Do NOT implement Subagent, PostToolUse, PreCompact, or `run_task.py` in v1.

## Hook contracts

### UserPromptSubmit

- **Trigger**: Before every user prompt is sent to Codex.
- **Read**: HOME.md, RULES.md, CURRENT_TASK.md, JUDGE.md.
- **Output**: `additionalContext` field in the hook response.
- **No compression** — raw file contents only.

### PreToolUse

- **Trigger**: Before every tool invocation from Codex.
- **Check**: Command string against a fixed denylist.
- **Action**: If matched, return `approved: false` with a reason.
- **Denylist** (first version):
   - `rm -rf`
   - `sudo`
   - `git reset --hard`
   - `git clean -fd`
   - `chmod -R`
   - `chown -R`
   - `curl | sh`
   - `wget | sh`

### StopJudge

- **Trigger**: On Codex `stop` signal (turn ends).
- **Read**: `last_assistant_message` from the turn payload.
- **Write**: `JUDGE.md` (human-readable) and `judge_latest.json` (machine-readable).
- **Default verdict**: `human_review` — no auto-loop yet.

## Versioning

- v1 is a minimal guard. Do not add LLM calls or complex logic.
- When hooks are stable, consider enabling `continue` verdicts later.
