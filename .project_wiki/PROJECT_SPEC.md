# Project Specification

## 0. Project Mode
当前项目模式：`wikiguard_self_development`

This is the Codex WikiGuard project itself. Codex may modify Hook source,
tests, README, and selected wiki instruction files only when the user asks to
develop WikiGuard.

## 1. Project Goal
Codex WikiGuard 是一个轻量的任务书驱动自动开发闭环。

用户把需求整理成 `.project_wiki/PROJECT_SPEC.md` 后，只需要在 Codex 输入一次
`开始工作`。之后 Codex 根据任务书开发，Hook 持续调用 AI 判断是否继续、纠偏或
完成，并自动推动 Codex 工作，直到任务完成并生成完成报告。

## 2. Background
Codex 默认是一轮一轮被用户推动的交互工具。WikiGuard 的目标是让 Codex 在明确
任务书约束下进入无人值守的连续工作模式，由 Hook 里的 AI 判断替代用户反复确认：

- 当前方向是否符合 PROJECT_SPEC；
- 当前任务是否完成；
- 下一步应该继续、纠偏还是结束；
- 完成时是否可以生成 COMPLETION_REPORT。

## 3. User Requirements
- 用户只输入一次 `开始工作` 后，系统应尽量自动推进到完成。
- Hook 判断主要使用 AI，而不是大量硬编码规则或正则。
- Stop Hook 是核心控制器，负责决定 `continue | revise | done | human_review`。
- `continue` 或 `revise` 时，Stop Hook 应通过 `decision:block` 给出下一步动作，驱动 Codex 继续。
- Hook 调用 AI 时使用当前 Codex 默认模型：`codex exec`，不传 `-m`，不写死模型、profile 或 endpoint。
- Profile 只允许通过 `CODEX_WIKIGUARD_PROFILE` 或 `CODEX_PROFILE` 继承。
- 必须防递归：子进程使用 `CODEX_WIKIGUARD_CHILD=1`。
- 必须支持 macOS 和 Windows。
- 判断体系文件不能由 Codex Worker 修改，只能由对应 Hook 在职责范围内写入。
- 不要把项目扩展成复杂安全平台；保持 Hook 轻量。

## 4. Non-Goals
- 不做完整 GH 平台。
- 不做 n8n 式流程编排器。
- 不做多 Agent 平台。
- 不做 RAG。
- 不做图数据库。
- 不做复杂长期记忆系统。
- 不做外层调度器。
- 不单独配置模型。
- 不写死 GPT、Qwen、API endpoint 或某个 profile。
- 不用大量硬编码 denylist 构建权限引擎。

## 5. Allowed Scope
开发 WikiGuard 自身时，允许修改：

- `hooks/*.py`
- `.codex/hooks.json`
- `tests/*`
- `README.md`
- `.project_wiki/INJECTION.md`
- `.project_wiki/PROJECT_SPEC.md`（用户明确要求时）
- `.project_wiki/PROJECT_SPEC_TEMPLATE.md`（用户明确要求时）

## 6. Protected Scope
Codex Worker 不能修改判断体系和监督状态文件，除非用户明确要求开发 WikiGuard
自身且修改属于当前任务：

- `.project_wiki/JUDGE.md`
- `.project_wiki/latest_context.md`
- `.project_wiki/judge_latest.json`
- `.project_wiki/loop_state.json`
- `.project_wiki/guard_log.jsonl`
- `.project_wiki/RULES.md`
- `.project_wiki/DECISIONS.md`
- `.project_wiki/REJECTED.md`
- `.project_wiki/PERMISSIONS.md`
- `.project_wiki/PROGRESS.md`

普通受监督项目中，Codex Worker 也不能修改：

- `.project_wiki/PROJECT_SPEC.md`
- `.project_wiki/PROJECT_SPEC_TEMPLATE.md`
- `.project_wiki/INJECTION.md`
- `.project_wiki/WORKFLOW.md`
- `.project_wiki/COMPLETION_REPORT_TEMPLATE.md`
- `.codex/hooks.json`
- `hooks/*.py`

## 7. Development Plan
- [ ] TASK-001: 重新校准项目说明和注入规则
  - Goal: 把 WikiGuard 的方向明确为任务书驱动的无人值守自动开发闭环。
  - Scope: `PROJECT_SPEC.md`, `INJECTION.md`, `README.md`
  - Acceptance: 文档不再把项目描述成复杂权限 Guard，明确 Stop Hook 自动推进目标。
  - Notes: 不修改 Hook 业务逻辑。

- [ ] TASK-002: 收敛 Hook 为轻量 AI 控制管道
  - Goal: 保留最小确定性运行逻辑，把方向、继续、纠偏、完成判断交给 AI。
  - Scope: `hooks/*.py`, `tests/*`
  - Acceptance: PreToolUse 不再是复杂权限引擎；Stop Hook 成为主要自动推进控制器。
  - Notes: 保留防递归、超时、JSON 解析、AI 调用失败处理和判断体系自保护。

- [ ] TASK-003: 修复自动继续闭环
  - Goal: 让 Stop Hook 在 `continue` / `revise` 时可靠驱动下一轮，在 `done` 时生成完成报告。
  - Scope: `hooks/stop_judge.py`, `hooks/codex_client.py`, `tests/*`
  - Acceptance: `decision:block` 携带明确 next_action；loop_state 正确计数和重置；latest_context 正确记录 auto_continue。
  - Notes: 不把 code-ready 说成 real-world verified。

- [ ] TASK-004: 加入 macOS / Windows 兼容验证
  - Goal: Hook 路径、诊断脚本和测试不依赖单一 shell 或平台路径格式。
  - Scope: `hooks/*.py`, `tests/*`
  - Acceptance: 使用跨平台路径处理；测试覆盖 Windows 风格路径和当前 macOS 路径。
  - Notes: 不引入外部依赖。

- [ ] TASK-005: 做真实无人值守闭环试跑
  - Goal: 验证用户只输入一次 `开始工作` 后，Codex 能在 Hook 控制下自动推进到 done。
  - Scope: `examples/minimal_supervised_project`, `.project_wiki/COMPLETION_REPORT.md`, `.project_wiki/PROGRESS.md`
  - Acceptance: 记录 direct evidence，明确区分 code-ready、environment-blocked、real-world verified。
  - Notes: 试跑前必须保证环境中的 `codex exec` 可用。

## 8. Acceptance Criteria
- 用户只输入一次 `开始工作` 后，Hook 能持续推动 Codex 继续开发或纠偏。
- Stop Hook 能基于 AI 输出可靠处理 `continue | revise | done | human_review`。
- `done` 时生成或更新 `.project_wiki/COMPLETION_REPORT.md`。
- 判断体系文件不能被普通 Codex Worker 修改。
- Hook 保持轻量，不引入复杂规则引擎、RAG、多 Agent 或外层调度器。
- `codex exec` 使用当前默认模型，不写死模型、profile 或 endpoint。
- macOS 和 Windows 的路径与启动方式都有测试覆盖。

## 9. Stop Conditions
- AI 判断需求不清或需要用户决策时，进入 `human_review`。
- `codex exec` 不可用或输出无法解析时，不假装监督成功。
- 连续自动推进达到 loop 限制仍未完成时，进入 `human_review`。
- 下一步动作要求修改判断体系核心文件且当前不是 WikiGuard 自开发任务时，进入 `human_review`。

## 10. Submission Requirements
- 每次开发提交必须说明属于 code-ready、environment-blocked 还是 real-world verified。
- 完成真实试跑前，不得声称无人值守 LLM supervisor 已完全跑通。
- 修改后至少运行不触发无关状态污染的基础验证。
