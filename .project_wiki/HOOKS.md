# Codex SpecPilot — HOOKS

## Available Hooks

| Hook | File | Status |
|------|------|--------|
| UserPromptSubmit | `hooks/user_prompt_submit.py` | Implemented (v1) |
| PreToolUse | `hooks/pre_tool_guard.py` | Implemented (v1) |
| StopJudge | `hooks/stop_judge.py` | Implemented (v1) |

## Configuration

Hooks are configured in `.codex/hooks.json`. See README.md for setup instructions.

## Version Notes

- All hooks use only Python standard library.
- No external dependencies.
- No LLM calls in v1.
