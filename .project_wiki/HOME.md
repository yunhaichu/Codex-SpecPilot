# Codex SpecPilot — HOME

This is the SpecPilot project root.

## Scope

- Minimal hook-based guard for Codex.
- No harness, no multi-agent, no graph DB, no RAG, no scheduler.

## Directory layout

```
.project_wiki/   — Wiki files read/written by hooks
hooks/           — Hook implementations (Python, stdlib only)
.codex/          — Codex hook config
README.md        — This project
```

## First release goals

1. `UserPromptSubmit` — inject HOME, RULES, CURRENT_TASK, JUDGE into prompts
2. `PreToolUse` — intercept dangerous commands
3. `StopJudge` — write verdict to Wiki, default to `human_review`
