# Codex SpecPilot

Codex SpecPilot is a public, MIT-licensed project for running Codex from a clear project specification.

It helps a user turn a rough idea into a structured task contract, then lets Codex keep working under Hook supervision until the work is done, blocked, or needs a real human decision.

## What It Can Do

- Create the minimal `.project_wiki` files when a project has no task contract yet.
- Guide onboarding for empty projects and existing projects.
- Ask for the project goal, allowed scope, protected scope, validation method, and GitHub sync preference before development starts.
- Default to local-only development when GitHub upload or sync is not needed.
- Record a GitHub sync policy when the user enables it, including auth method, public/private visibility, repository target, and allowed push/tag/checkpoint behavior without storing secrets.
- Write or update `.project_wiki/PROJECT_SPEC.md` through a controlled Hook flow instead of letting the ordinary Codex worker edit the task contract directly.
- Inject the current task contract and project state into Codex before each user prompt.
- Refresh managed Hook runtime files and static wiki templates when a project opens with an older local copy.
- Block ordinary worker edits to judge-system files such as `PROJECT_SPEC.md`, Hook source, Hook config, and supervision state.
- Ask the current Codex default model to judge whether work should continue, revise, finish, or stop for human review.
- Automatically continue the Codex loop when the Stop Hook decides the next step is clear and allowed.
- Pause development when the user changes project goals, scope, priorities, or acceptance criteria, then require a controlled task-contract update.
- Generate or update a completion report when the task contract is satisfied.

Codex SpecPilot stays intentionally small. It is not a full GitHub platform, CI system, release system, RAG system, graph database, long-term memory system, workflow orchestrator, or multi-agent platform.

## Basic Flow

1. Open Codex in the target project directory.
2. If no task contract exists, Codex SpecPilot creates the minimal project Wiki files and starts onboarding.
3. The user answers the onboarding questions.
4. The controlled Hook flow writes `.project_wiki/PROJECT_SPEC.md`.
5. The user says `开始工作`.
6. Codex works through the Development Plan.
7. Hooks judge progress, direction, permissions, completion, and whether the loop should continue.
8. When all acceptance criteria are met, Codex SpecPilot records the completion result.

## macOS Install

Double-click `install/macos/install.command`.

The installer detects the repository location from the script itself, finds the Codex config directory from `CODEX_HOME` or `~/.codex`, writes `hooks.json`, and keeps a timestamped backup when an older file exists. After that, enable Codex hooks in Codex settings if they are not already enabled.

No token, API key, password, or private key is requested or stored.

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
- 在开发前询问项目目标、允许范围、保护范围、验证方式和 GitHub 同步策略。
- 如果用户不需要 GitHub 上传或同步，默认使用本地模式。
- 如果用户启用 GitHub 同步，记录认证方式、公开/私有、仓库目标、允许的 push/tag/checkpoint 行为，但不保存密钥。
- 通过受控 Hook 流程写入或更新 `.project_wiki/PROJECT_SPEC.md`，避免普通 Codex Worker 直接修改任务合同。
- 每轮用户输入前，把当前任务合同和项目状态注入给 Codex。
- 当目标项目里的本地 Hook 副本或静态 Wiki 模板过旧时，自动补齐或刷新受管文件。
- 阻止普通 Worker 修改判断体系文件，例如 `PROJECT_SPEC.md`、Hook 源码、Hook 配置和监督状态。
- 使用当前 Codex 默认模型判断是否继续、纠偏、完成或进入人工确认。
- 当 Stop Hook 判断下一步明确且允许时，自动推动 Codex 继续工作。
- 当用户在开发中修改目标、范围、优先级或验收标准时，暂停开发并要求先更新任务合同。
- 当任务合同满足后，生成或更新完成报告。

Codex SpecPilot 保持轻量。它不是完整 GitHub 平台、CI 系统、发布系统、RAG 系统、图数据库、长期记忆系统、流程编排器或多 Agent 平台。

## 基本流程

1. 在目标项目目录打开 Codex。
2. 如果还没有任务合同，Codex SpecPilot 自动创建最小项目 Wiki 文件并进入 onboarding。
3. 用户回答 onboarding 问题。
4. 受控 Hook 流程写入 `.project_wiki/PROJECT_SPEC.md`。
5. 用户输入 `开始工作`。
6. Codex 按 Development Plan 开发。
7. Hook 判断进度、方向、权限、完成状态，以及是否继续循环。
8. 所有验收条件满足后，Codex SpecPilot 记录完成结果。

## macOS 安装

双击 `install/macos/install.command`。

安装器会根据脚本所在位置识别当前仓库，自动查找 `CODEX_HOME` 或 `~/.codex`，写入 `hooks.json`，如果旧文件存在会先生成带时间戳的备份。完成后，只需要在 Codex 设置里启用 Hook。

安装过程不会要求或保存 token、API key、密码、private key。

## 运行时更新

Hook 在目标项目运行时，会检查本地受管运行文件：

- `hooks/*.py`
- `.codex/hooks.json`
- 静态 `.project_wiki` 说明和模板文件

缺失或过旧的受管文件会从已安装的 SpecPilot 源码中自动创建或刷新。任务合同、判断状态、日志、循环状态和完成报告不会被这个更新器覆盖。

## 许可证

MIT
