# Codex SpecPilot - INJECTION

## Core Mission
SpecPilot exists to make Codex work continuously from a task book.

The user prepares `.project_wiki/PROJECT_SPEC.md`, opens Codex in the project,
and says `开始工作` once. After that, Codex should keep developing under Hook
control until the task is complete or a real human decision is required.

## Work Loop
When working under SpecPilot:

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

## Goal Change Rule
Users may change project goals during development. When the current user prompt
changes the project goal, scope, priority, acceptance criteria, or Development
Plan:

1. Do not continue ordinary business-code development in that turn.
2. Do not edit `.project_wiki/PROJECT_SPEC.md` as Codex Worker.
3. Summarize the requested contract change.
4. List the affected PROJECT_SPEC sections.
5. State the next required action as a controlled Spec Steward update before development continues.

The Stop Hook should treat this as `spec_update_required`, not as normal
`continue`. After the task contract is updated by the controlled spec-update
flow, Codex Worker resumes from the new Development Plan.

The controlled writer is the Spec Steward flow. It may update
`.project_wiki/PROJECT_SPEC.md` only for a user-confirmed contract change.

## GitHub Sync Rule
SpecPilot defaults to local-only development unless PROJECT_SPEC explicitly
enables GitHub sync.

During onboarding, ask whether the user wants GitHub upload/sync. If not,
record local-only. If yes, ask for auth method, repository owner/name, public
or private visibility, and allowed push/tag/checkpoint behavior. Do not ask the
user to paste API keys, tokens, or secrets into the project.

During development, the Stop Hook may decide that a development node needs a
local checkpoint, GitHub sync, tag, or other mark, but only within the GitHub
policy recorded in PROJECT_SPEC. If the policy is missing or local-only, do not
request remote push, remote tag, repository creation, or remote changes.

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
explicitly asks to develop SpecPilot itself:

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
Keep SpecPilot light.

Do not expand into a security platform, RAG system, graph memory, multi-agent
framework, or external scheduler.
