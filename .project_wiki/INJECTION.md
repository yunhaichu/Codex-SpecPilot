# Codex SpecPilot - INJECTION

## Core Mission
SpecPilot exists to make Codex work continuously from a task book.

The user prepares `.project_wiki/PROJECT_SPEC.md`, opens Codex in the project,
and says `开始工作` once. After that, Codex should keep developing under Hook
control until the task is complete or a real human decision is required.

## Work Loop
When working under SpecPilot:

1. Read `.project_wiki/PROJECT_SPEC.md`.
2. Read Active Mission Snapshot as the current-goal anchor before historical summaries.
3. Find the first incomplete `TASK-*` in the current Development Plan range.
4. Work only on the current task.
5. At the end of the turn, report:
   - current task id;
   - files changed;
   - validation performed;
   - whether the task is done;
   - what should happen next.
6. Let the Stop Hook judge whether to continue, revise, finish, or request human review.

## Active Mission Snapshot Rule
Long task books must keep an Active Mission Snapshot near the front of
`PROJECT_SPEC.md`. Treat it as the current-goal anchor for:

- current goal and current phase;
- current `TASK-*` range;
- current acceptance focus;
- current non-goals;
- release or GitHub sync target;
- context priority.

If historical summaries, completed phases, old task reports, or previous
completion claims conflict with the Active Mission Snapshot, use the snapshot
first. The correct response is a concrete revise step, evidence reconciliation,
or controlled `spec_update_required` when the task contract itself needs to
change.

## Blocker Self-Recovery Rule
When development hits an implementation, test, dependency, planning, or stage
progress problem, do not default to handing the problem to the user.

Use the existing `.project_wiki` facts, PROJECT_SPEC, latest context, current
goal, stage goal, validation output, and changed files to choose the next
recovery step. Prefer one of these outcomes:

- continue with a concrete investigation, fix, or validation step;
- revise the implementation approach;
- re-check whether the current stage goal or Development Plan assumption is
  wrong, then propose a controlled `spec_update_required` change if the task
  contract needs to move.

Use `human_review` only when the blocker truly needs user judgment, secrets or
credentials, external environment action, protected-scope authorization, a
scope choice, or an ambiguity Codex cannot resolve from the task book and wiki
facts.

Classify blockers narrowly:

- `engineering_recovery`: investigate, fix, rerun validation;
- `evidence_reconciliation`: compare reports, tests, completion claims, and task status;
- `status_reconciliation`: normalize status aliases and repair inconsistent state;
- `contract_update`: use controlled Spec Steward;
- `user_decision`: stop for the user;
- `external_environment`: stop for environment or credential action;
- `unsafe/protected_scope`: stop unless explicitly authorized.

Only `user_decision`, `external_environment`, and `unsafe/protected_scope`
normally justify `human_review`.

## Protected Maintenance Authorization Rule
If Hook runtime maintenance is needed for protected files, do not ask the user to
manually disable PreToolUse or manually edit the protected files.

Instead:

1. State the exact maintenance target files.
2. Ask for a one-shot protected maintenance authorization.
3. If the user replies `同意`, `允许`, `可以`, `yes`, `ok`, or equivalent approval,
   UserPromptSubmit creates a short-lived lease.
4. PreToolUse may consume the lease once, only for the listed maintenance files.
5. After consumption or expiry, protection returns automatically.

The lease must not cover `.project_wiki/PROJECT_SPEC.md`, judge logs, loop
state, secrets, or a patch that mixes maintenance files with unrelated business
files. Task-contract changes still go through the controlled Spec Steward flow.

## Goal Change Rule
Users may change project goals during development. When the current user prompt
changes the project goal, scope, priority, acceptance criteria, or Development
Plan:

1. Do not continue ordinary business-code development in that turn.
2. Do not edit `.project_wiki/PROJECT_SPEC.md` as Codex Worker.
3. Summarize the requested contract change.
4. List the affected PROJECT_SPEC sections.
5. Make the change request clear enough for the controlled Spec Steward flow.
6. Do not ask the user to manually edit `PROJECT_SPEC.md` or task-book files.

The Stop Hook should treat this as `spec_update_required`, not as normal
`continue`. If information is sufficient, the controlled Spec Steward /
onboarding / spec update flow should write the updated task contract directly.
If information is insufficient after a complete PROJECT_SPEC already exists,
Codex must first use wiki facts, latest context, evidence, and current goal to
resolve the gap or narrow the plan automatically. Repeated user confirmation is
allowed only during initial project creation/onboarding before the task contract
is complete.
After the task contract is updated by the controlled spec-update flow, Codex
Worker resumes from the new Development Plan.

The controlled writer is the Spec Steward flow. It may update
`.project_wiki/PROJECT_SPEC.md` only for a user-confirmed contract change.
When latest context is already `spec_update_required` and the user replies
`同意`, `yes`, `ok`, `apply`, or an equivalent confirmation, treat that as
permission for Spec Steward to apply the previously summarized change.
If the user rejects the summarized change or uses ambiguous confirmation
wording, do not apply the task contract update; ask only the minimum
confirmation or replacement-change question.

## Automatic Phase Transition Rule
When a phase, TASK range, completion report, experience evaluation, evidence
reconciliation, or Development Plan segment is complete, do not ask the user to
confirm the next phase. The Stop Hook should route the transition through
controlled Spec Steward automatically, update the task contract or plan from
available project facts, and then continue Worker development.

Only initial task-contract creation may repeatedly ask the user to confirm
requirements and goals. After PROJECT_SPEC is complete, user prompts and
confirmed goals are the highest instruction source, but phase planning,
status reconciliation, and next-task activation are automatic unless they need
secrets, external environment actions, or unsafe/protected-scope authorization.

For normal conversation prompts, the Hook must still record a lightweight pass
judgment and avoid starting the full task loop.

## GitHub Sync Rule
SpecPilot defaults to local-only development unless PROJECT_SPEC explicitly
enables GitHub sync.

During onboarding, ask whether the user wants GitHub upload/sync. If not,
record local-only. If yes, ask for GitHub account, auth method, credential
availability, repository owner/name, public or private visibility, whether a
new repository may be created or an existing repository must be used, marker
nodes, and allowed automatic operations versus human confirmation. Do not ask
the user to paste API keys, tokens, or secrets into the project.

During development, the Stop Hook may decide that a development node needs a
local checkpoint, GitHub sync, tag, or other mark, but only within the GitHub
policy recorded in PROJECT_SPEC. If the policy is missing or local-only, do not
request remote push, remote tag, repository creation, or remote changes.
Remote GitHub actions require a complete non-secret policy with auth method
description, GitHub account, repository target, existing-vs-new repository
policy, visibility, marker nodes, allowed automatic operations, and available
credentials. If credentials are unavailable or a push/tag/release/repository
creation requires human confirmation, fail safe to `human_review` instead of
pretending the sync succeeded.

If the Active Mission Snapshot or Submission Requirements already records a
current GitHub sync/release authorization but the formal GitHub Sync Policy is
still local-only or incomplete, route to controlled `spec_update_required`
policy reconciliation before any remote operation.

## Long Task Book Rule
`PROJECT_SPEC.md` may be long. Do not ask the user to manually shorten,
split, or rewrite the task book to fit a Hook prompt.

Hooks should use compact key-section context or section head/tail preservation
so Active Mission Snapshot, Project Goal, User Requirements, Non-Goals, Allowed
Scope, Protected Scope, Development Plan, Acceptance Criteria, Stop Conditions,
GitHub policy, and Submission Requirements remain visible, including late
Development Plan tasks.

Do not perform full task-book rewrites when a section-level update is enough.
Use the controlled Spec Steward / section patch flow so long contracts keep
their current snapshot, late tasks, GitHub policy, and submission requirements.

## Start Work Rule
When the user says `开始工作`:

1. Treat PROJECT_SPEC as the task contract.
2. Start the first incomplete Development Plan item.
3. Do not wait for the user between normal development steps.
4. Make progress in small, verifiable steps.
5. If blocked, first investigate, revise, validate, or re-check the stage plan
   using task-book and wiki facts.
6. Stop only when the task is done, blocked by environment, or needs real user judgment.

## End Work Rule
When all Acceptance Criteria are satisfied:

1. Stop ordinary development.
2. Run the user-perspective experience evaluation before final completion.
3. If the evaluation finds obvious high-value user-facing issues, convert them
   into a controlled Spec Steward update before worker development continues.
4. Generate or update `.project_wiki/COMPLETION_REPORT.md` only after the
   evaluation finds no obvious issue or only low-value/out-of-scope suggestions.
5. Summarize changed files, validation results, and experience evaluation status.
6. Do not request another auto-continue.

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

- recursive guard with `CODEX_SPECPILOT_CHILD=1`;
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

1. `CODEX_SPECPILOT_PROFILE`
2. `CODEX_PROFILE`
3. default Codex environment

## Current Priority
Keep SpecPilot light.

Do not expand into a security platform, RAG system, graph memory, multi-agent
framework, or external scheduler.
