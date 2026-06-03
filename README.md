# Codex SpecPilot

Codex SpecPilot is a public, MIT-licensed project for running Codex from a clear project specification.

It helps a user turn a rough idea into a structured task contract, then lets Codex keep working under Hook supervision until the work is done, blocked, or needs a real human decision.

## What It Can Do

- Create the minimal `.project_wiki` files when a project has no task contract yet.
- Guide onboarding for empty projects and existing projects.
- Resolve onboarding to the real repository or project root when Codex is opened inside a nested subdirectory.
- Ask for the project goal, allowed scope, protected scope, validation method, and GitHub sync preference before development starts.
- Default to local-only development when GitHub upload or sync is not needed.
- Record a GitHub sync policy when the user enables it, including account, auth method, credential availability, public/private visibility, repository target, existing-vs-new repository policy, marker nodes, and allowed push/tag/release behavior without storing secrets.
- Write or update `.project_wiki/PROJECT_SPEC.md` through a controlled Hook flow instead of letting the ordinary Codex worker edit the task contract directly.
- Apply clear task-contract change suggestions through Spec Steward without asking the user to edit project files by hand.
- Treat a simple approval such as `同意`, `yes`, `ok`, or `apply` as confirmation of the previously summarized contract update.
- Refuse to apply rejected or ambiguous contract confirmations until the user gives a clear approval or replacement change.
- Keep an Active Mission Snapshot at the front of long task contracts so the current goal, task range, acceptance focus, non-goals, and release target do not get blurred by old history.
- Inject the current task contract and project state into Codex before each user prompt.
- Refresh managed Hook runtime files and static wiki templates when a project opens with an older local copy.
- Block ordinary worker edits to judge-system files such as `PROJECT_SPEC.md`, Hook source, Hook config, and supervision state.
- Ask the current Codex default model to judge whether work should continue, revise, finish, or stop for human review.
- Automatically continue the Codex loop when the Stop Hook decides the next step is clear and allowed.
- Treat ordinary implementation, test, dependency, or planning blockers as work to investigate and recover from before asking the user.
- Re-check the current stage goal or Development Plan when there is no direct recovery path, then route real contract changes through Spec Steward.
- Preserve key task-book sections when `.project_wiki/PROJECT_SPEC.md` is long, including the Active Mission Snapshot, late Development Plan items, GitHub policy, stop conditions, and submission requirements.
- Reconcile task evidence when reports say a task is complete but the Development Plan still shows it as pending.
- Pause development when the user changes project goals, scope, priorities, or acceptance criteria, then invoke the controlled task-contract update flow directly.
- Run a user-perspective experience evaluation before final completion reporting.
- Convert obvious high-value user-facing evaluation findings into controlled task-contract updates before development continues.
- Generate or update a completion report only after experience evaluation finds no obvious remaining user-facing issue.

Codex SpecPilot stays intentionally small. It is not a full GitHub platform, CI system, release system, RAG system, graph database, long-term memory system, workflow orchestrator, or multi-agent platform.

## Basic Flow

1. Open Codex in the target project directory.
2. If no task contract exists, Codex SpecPilot creates the minimal project Wiki files and starts onboarding.
3. The user answers the onboarding questions.
4. The controlled Hook flow writes `.project_wiki/PROJECT_SPEC.md`.
5. The user says `开始工作`.
6. Codex works through the Development Plan.
7. Hooks judge progress, direction, permissions, completion, and whether the loop should continue.
8. If development hits an ordinary blocker, SpecPilot asks Codex to investigate, recover, validate, or revise the stage plan before asking the user.
9. If the user changes requirements, SpecPilot routes the suggestion or confirmation through Spec Steward; the user does not manually edit the task contract.
10. When all acceptance criteria are met, Codex SpecPilot runs a user-perspective experience evaluation.
11. If the evaluation finds obvious high-value user-facing issues, SpecPilot pauses for a controlled task-contract update.
12. If no obvious issue remains, SpecPilot records the final completion result.

## Role Boundaries

- User: provides goals, scope, priorities, acceptance criteria, and mid-development change suggestions or approvals.
- Requirement parsing: turns confirmed user intent into task-contract changes; ambiguous changes stay in minimum necessary questions instead of code edits.
- Spec Steward: the controlled writer for `.project_wiki/PROJECT_SPEC.md`; it applies clear suggestions or explicit approvals such as `同意`, supports section-level updates, and asks only when information is insufficient.
- Planner: the Development Plan inside `PROJECT_SPEC.md`; it converts the confirmed contract into ordered `TASK-*` work.
- Codex Worker: implements the current Development Plan task and must not rewrite the task contract or judge-system files.
- Stop Hook: judges each turn and may return `continue`, `revise`, `done`, `human_review`, or `spec_update_required`; ordinary blockers should become concrete recovery or stage-replan actions, while goal changes pause Worker development so Spec Steward can update the contract.

## Long Task Books

SpecPilot does not require the user to shorten a long `.project_wiki/PROJECT_SPEC.md`. Hooks first preserve the Active Mission Snapshot, then build compact prompt context from the key sections and keep both the beginning and end of long sections, so late Development Plan tasks, GitHub policy, stop conditions, and submission requirements remain visible.

If old summaries, completed phases, or stale reports conflict with the Active Mission Snapshot, the current snapshot wins. The Stop Hook should revise the next action, run evidence reconciliation, or route a real contract change through Spec Steward instead of continuing from the stale target.

## macOS Install

Double-click `install/macos/install.command`.

The installer detects the repository location from the script itself, finds the Codex config directory from `CODEX_HOME` or `~/.codex`, writes `hooks.json`, and keeps a timestamped backup when an older file exists. After that, enable Codex hooks in Codex settings if they are not already enabled.

No token, API key, password, or private key is requested or stored.

## GitHub Sync Policy

Projects are local-only unless `.project_wiki/PROJECT_SPEC.md` explicitly enables GitHub sync. Remote operations such as push, tag, release, repository creation, pull requests, or GitHub checkpoints require a complete non-secret policy: GitHub account, auth method description, credential availability, repository target, existing-vs-new repository policy, public/private visibility, marker nodes, and the exact automatic operations allowed.

If the policy is missing, local-only, incomplete, says credentials are unavailable, or requires human confirmation for the requested remote operation, SpecPilot stops for human review instead of attempting the operation.

## Runtime Updates

When a Hook runs in a target project, SpecPilot checks the managed local runtime:

- `hooks/*.py`
- `.codex/hooks.json`
- static `.project_wiki` instruction and template files

Missing or stale managed files are created or refreshed from the installed SpecPilot source. Project contracts, judge state, logs, loop state, and completion reports are not overwritten by this updater.

## License

MIT

---

# Codex SpecPilot

Codex SpecPilot 是一个公开的 MIT 许可证项目，用来让 Codex 按清晰的项目任务书持续开发。

它帮助用户把粗略需求整理成结构化任务合同，然后让 Codex 在 Hook 监督下持续工作，直到任务完成、环境阻塞，或确实需要人工判断。

## 它能做什么

- 当项目还没有任务合同时，自动创建最小 `.project_wiki` 文件。
- 支持空项目和老项目接管。
- 在仓库或项目子目录中打开 Codex 时，自动把 onboarding 定位到真正的仓库或项目根目录。
- 在开发前询问项目目标、允许范围、保护范围、验证方式和 GitHub 同步策略。
- 如果用户不需要 GitHub 上传或同步，默认使用本地模式。
- 如果用户启用 GitHub 同步，记录 GitHub 账号、认证方式、凭据可用状态、公开/私有、仓库目标、已有或新建仓库策略、marker 节点、允许的 push/tag/release 行为，但不保存密钥。
- 通过受控 Hook 流程写入或更新 `.project_wiki/PROJECT_SPEC.md`，避免普通 Codex Worker 直接修改任务合同。
- 用户提出清晰任务合同修改建议时，直接通过 Spec Steward 更新，不要求用户手动编辑项目文件。
- 用户回复 `同意`、`yes`、`ok`、`apply` 等确认时，视为确认前一次已总结的合同更新。
- 用户拒绝或含糊确认前一次合同更新时，不写入任务书，只请求最少确认或新的修改建议。
- 在长任务书前部维护 Active Mission Snapshot，固定当前目标、任务范围、验收重点、非目标和发布目标，避免旧历史模糊当前开发方向。
- 每轮用户输入前，把当前任务合同和项目状态注入给 Codex。
- 当目标项目里的本地 Hook 副本或静态 Wiki 模板过旧时，自动补齐或刷新受管文件。
- 阻止普通 Worker 修改判断体系文件，例如 `PROJECT_SPEC.md`、Hook 源码、Hook 配置和监督状态。
- 使用当前 Codex 默认模型判断是否继续、纠偏、完成或进入人工确认。
- 当 Stop Hook 判断下一步明确且允许时，自动推动 Codex 继续工作。
- 遇到普通实现、测试、依赖或规划卡点时，先推动 Codex 调查、修复、验证或调整阶段计划，而不是直接把问题交给用户。
- 如果没有直接解法，先重审当前阶段目标或 Development Plan；确实需要改任务合同时，再走 Spec Steward。
- 长任务书会优先保留 Active Mission Snapshot，并以关键章节和头尾保真的方式导入 Hook 判断，避免后段任务、GitHub 策略、停止条件或提交要求被截断。
- 当报告证据显示任务已完成但 Development Plan 仍显示 pending 时，进入任务证据对账或受控合同修复。
- 当用户在开发中修改目标、范围、优先级或验收标准时，暂停开发并直接调用受控任务合同更新流程。
- 最终完成报告前，先执行使用者视角体验测评。
- 将明显且高价值的用户体验问题转成受控任务合同更新，再继续开发。
- 只有体验测评找不到明显剩余用户问题时，才生成或更新完成报告。

Codex SpecPilot 保持轻量。它不是完整 GitHub 平台、CI 系统、发布系统、RAG 系统、图数据库、长期记忆系统、流程编排器或多 Agent 平台。

## 基本流程

1. 在目标项目目录打开 Codex。
2. 如果还没有任务合同，Codex SpecPilot 自动创建最小项目 Wiki 文件并进入 onboarding。
3. 用户回答 onboarding 问题。
4. 受控 Hook 流程写入 `.project_wiki/PROJECT_SPEC.md`。
5. 用户输入 `开始工作`。
6. Codex 按 Development Plan 开发。
7. Hook 判断进度、方向、权限、完成状态，以及是否继续循环。
8. 如果开发遇到普通卡点，SpecPilot 先要求 Codex 调查、自解、验证或重审阶段计划。
9. 如果用户调整需求，SpecPilot 将修改建议或确认交给 Spec Steward；用户不需要手动编辑任务书。
10. 所有验收条件满足后，Codex SpecPilot 先执行使用者视角体验测评。
11. 如果测评发现明显且高价值的用户问题，SpecPilot 暂停并进入受控任务合同更新。
12. 如果没有明显剩余问题，SpecPilot 记录最终完成结果。

## 角色分工

- 用户：提出项目目标、范围、优先级、验收标准，以及开发中途的任务合同修改建议或确认。
- 需求解析：把用户已确认的意图转成任务合同变更；不清楚的变更只问最少必要问题，不直接写代码。
- Spec Steward：`.project_wiki/PROJECT_SPEC.md` 的受控写入者；对清晰建议或 `同意` 这类明确确认可直接应用，支持章节级更新，信息不足时才提问。
- Planner：`PROJECT_SPEC.md` 里的 Development Plan；把已确认合同拆成有顺序的 `TASK-*`。
- Codex Worker：只实现当前 Development Plan 任务，不改写任务合同或判断体系文件。
- Stop Hook：每轮判断 `continue`、`revise`、`done`、`human_review` 或 `spec_update_required`；普通卡点应转成明确恢复或阶段重规划动作，用户改目标时才暂停 Worker 并让 Spec Steward 更新合同。

## 长任务书

SpecPilot 不要求用户手动缩短 `.project_wiki/PROJECT_SPEC.md`。Hook 会先保留 Active Mission Snapshot，再从关键章节构造紧凑上下文，并保留长章节的开头和结尾，确保后段 Development Plan、GitHub 策略、停止条件和提交要求仍能进入判断。

如果旧摘要、已完成阶段或过期报告与 Active Mission Snapshot 冲突，应以当前目标锚点为准。Stop Hook 应纠偏下一步、运行证据对账，或把真实合同变化交给 Spec Steward，而不是沿着旧目标继续开发。

## macOS 安装

双击 `install/macos/install.command`。

安装器会根据脚本所在位置识别当前仓库，自动查找 `CODEX_HOME` 或 `~/.codex`，写入 `hooks.json`，如果旧文件存在会先生成带时间戳的备份。完成后，只需要在 Codex 设置里启用 Hook。

安装过程不会要求或保存 token、API key、密码、private key。

## GitHub 同步策略

除非 `.project_wiki/PROJECT_SPEC.md` 明确启用 GitHub sync，项目默认是 local-only。push、tag、release、创建仓库、创建 PR、GitHub checkpoint 等远端操作必须有完整的非密钥策略：GitHub 账号、认证方式描述、凭据可用状态、仓库目标、已有或新建仓库策略、public/private、marker 节点，以及允许自动执行的具体操作。

如果策略缺失、local-only、不完整、凭据不可用，或请求的远端操作需要人工确认，SpecPilot 会进入 human_review，而不是尝试执行该操作。

## 运行时更新

Hook 在目标项目运行时，会检查本地受管运行文件：

- `hooks/*.py`
- `.codex/hooks.json`
- 静态 `.project_wiki` 说明和模板文件

缺失或过旧的受管文件会从已安装的 SpecPilot 源码中自动创建或刷新。任务合同、判断状态、日志、循环状态和完成报告不会被这个更新器覆盖。

## 许可证

MIT
