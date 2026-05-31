# Codex WikiGuard

Codex WikiGuard is a lightweight AI-controlled development loop for Codex.

The intended user flow is simple:

1. The user and AI turn requirements into `.project_wiki/PROJECT_SPEC.md`.
2. The user opens Codex in the project directory.
3. The user says `开始工作` once.
4. Codex develops from the task book.
5. Hooks use AI judgment to decide whether Codex should continue, revise, finish, or stop for human review.
6. When done, WikiGuard records completion in `.project_wiki/COMPLETION_REPORT.md`.

The goal is unattended progress from a written task book. WikiGuard is not a full security platform, workflow engine, RAG system, graph memory, or multi-agent framework.

## Core Idea

WikiGuard has three Hooks:

| Hook | Role |
| --- | --- |
| `UserPromptSubmit` | Injects a short task and status context before Codex starts or continues work. |
| `PreToolUse` | Keeps the judge system from being modified by the Codex worker and can ask AI to judge tool intent. |
| `Stop` | The main controller. It asks AI whether to `continue`, `revise`, `done`, or `human_review`, then drives the next turn when appropriate. |

Most project direction decisions should be made by AI:

- Is Codex still following `PROJECT_SPEC.md`?
- Is the current task complete?
- Should Codex continue?
- Should Codex revise direction?
- Is the whole project done?

Deterministic code should stay small and mechanical:

- prevent recursive Hook calls with `CODEX_WIKIGUARD_CHILD=1`;
- call `codex exec` with the current default model;
- parse JSON responses;
- track loop count;
- prevent the Codex worker from editing the judge system;
- fail closed when AI judgment is unavailable.

## Judge System Boundary

Codex may edit project code. It must not edit the files that control or record the judgment system unless the user is explicitly developing WikiGuard itself.

Judge system files include:

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

The corresponding Hooks may update their own state files.

## Model Rule

Hooks call the current Codex environment:

```bash
codex exec
```

They do not pass `-m`, do not configure a separate model, and do not hardcode a provider, endpoint, profile, GPT model, or local model.

Profile inheritance is allowed only through:

1. `CODEX_WIKIGUARD_PROFILE`
2. `CODEX_PROFILE`
3. default Codex configuration

## Current Status

Implemented foundations:

- Hook registration for `UserPromptSubmit`, `PreToolUse`, and `Stop`.
- `codex exec` wrapper using the current default model.
- Profile inheritance through environment variables.
- Recursive guard through `CODEX_WIKIGUARD_CHILD=1`.
- Stop Hook state files and loop counter.
- Minimal supervised example project.

Direction now being corrected:

- Keep Hooks light.
- Make `Stop` the main automatic development controller.
- Move project direction decisions to AI judgment.
- Avoid expanding `PreToolUse` into a large hardcoded permission engine.
- Add macOS and Windows compatibility checks.

## Local Checks

Basic syntax check:

```bash
python -m py_compile hooks/*.py tests/*.py
```

Codex execution diagnostic:

```bash
python tests/diagnose_codex_exec.py
```

The full smoke test may invoke Hooks that write state files, so run it only when intentionally testing the Hook loop.
