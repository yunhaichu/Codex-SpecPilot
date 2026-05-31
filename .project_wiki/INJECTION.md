# Codex WikiGuard - INJECTION

## Core Mission
WikiGuard exists to make Codex work continuously from a task book.

The user prepares `.project_wiki/PROJECT_SPEC.md`, opens Codex in the project,
and says `开始工作` once. After that, Codex should keep developing under Hook
control until the task is complete or a real human decision is required.

## Work Loop
When working under WikiGuard:

1. Read `.project_wiki/PROJECT_SPEC.md`.
2. Find the first incomplete `TASK-*` in Development Plan.
3. Work only on the current task.
4. At the end of the turn, report:
   - current task id;
   - files changed;
   - validation performed;
   - whether the task is done;
   - what should happen next.
5. Let the Stop Hook judge whether to continue, revise, finish, or request human review.

## Start Work Rule
When the user says `开始工作`:

1. Treat PROJECT_SPEC as the task contract.
2. Start the first incomplete Development Plan item.
3. Do not wait for the user between normal development steps.
4. Make progress in small, verifiable steps.
5. Stop only when the task is done, blocked by environment, or needs real user judgment.

## End Work Rule
When all Acceptance Criteria are satisfied:

1. Stop further development.
2. Generate or update `.project_wiki/COMPLETION_REPORT.md`.
3. Summarize changed files and validation results.
4. Do not request another auto-continue.

When the user says `结束工作`, summarize current state and do not continue automatically.

## Judge System Boundary
Codex Worker may develop project code, but must not edit the judge system that
controls it.

Worker must not modify these judge system files unless the current user command
explicitly asks to develop WikiGuard itself:

- `.project_wiki/PROJECT_SPEC.md`
- `.project_wiki/PROJECT_SPEC_TEMPLATE.md`
- `.project_wiki/RULES.md`
- `.project_wiki/DECISIONS.md`
- `.project_wiki/REJECTED.md`
- `.project_wiki/PERMISSIONS.md`
- `.project_wiki/WORKFLOW.md`
- `.project_wiki/JUDGE.md`
- `.project_wiki/latest_context.md`
- `.project_wiki/judge_latest.json`
- `.project_wiki/loop_state.json`
- `.project_wiki/guard_log.jsonl`
- `.codex/hooks.json`
- `hooks/*.py`

Corresponding Hooks may update their own state files.

## AI Judge Preference
Project direction decisions belong to AI judgment, not hardcoded rule piles.

Use AI judgment for:

- whether Codex is following PROJECT_SPEC;
- whether the current task is complete;
- whether the next step should continue or revise;
- whether the whole project is done.

Keep deterministic logic minimal:

- recursive guard with `CODEX_WIKIGUARD_CHILD=1`;
- timeout handling;
- JSON parsing;
- loop count;
- judge system self-protection;
- fail closed when AI judgment is unavailable.

## Model Rule
Hooks call:

```text
codex exec
```

Do not pass `-m`.
Do not hardcode a model, profile, endpoint, API key, GPT, or Qwen.

Profile inheritance only:

1. `CODEX_WIKIGUARD_PROFILE`
2. `CODEX_PROFILE`
3. default Codex environment

## Current Priority
Keep WikiGuard light.

Do not expand into a security platform, RAG system, graph memory, multi-agent
framework, or external scheduler.
