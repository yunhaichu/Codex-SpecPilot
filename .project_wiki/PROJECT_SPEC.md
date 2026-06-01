# Project Specification

## 0. Project Mode
当前项目模式：`specpilot_self_development`

This is the Codex SpecPilot project itself. Codex may modify Hook source,
tests, README, and selected wiki instruction files only when the user asks to
develop SpecPilot.

## 1. Project Goal
Codex SpecPilot 是一个轻量的任务书驱动自动开发闭环。

用户把需求整理成 `.project_wiki/PROJECT_SPEC.md` 后，只需要在 Codex 输入一次
`开始工作`。之后 Codex 根据任务书开发，Hook 持续调用 AI 判断是否继续、纠偏或
完成，并自动推动 Codex 工作，直到任务完成并生成完成报告。

当目标项目是空项目或老项目且没有完整任务书时，SpecPilot 应由 Hook 自动接管：
创建最小项目 Wiki、进入需求澄清，在信息足够后通过受控 Hook 流程写入正式
`PROJECT_SPEC.md`，然后再允许 Codex Worker 开始开发。

SpecPilot 还应在 onboarding 阶段支持可选的轻量 GitHub 同步策略确认。项目可以
保持本地-only；只有用户明确选择上传或同步时，Hook/onboarding 才收集必要的
GitHub 策略，并在后续开发节点按任务书策略决定是否提交、推送、打 tag、发布或
记录其他 GitHub 标记。

当当前完成流程认为项目已经完成时，SpecPilot 不应立刻视为最终结束，而应先启动
一个使用者视角体验测评 Hook。该 Hook 尽可能真实地使用项目成果，输出用户实际会
遇到的明显问题、阻碍、困惑、缺失和高价值改进，并将有效测评发现转入受控任务合同
更新流程。开发、测评、合同更新、继续开发可以反复循环，直到体验测评找不到明显问题
或值得继续开发的改进点后，再进入最终完成报告。

## 2. Background
Codex 默认是一轮一轮被用户推动的交互工具。SpecPilot 的目标是让 Codex 在明确
任务书约束下进入无人值守的连续工作模式，由 Hook 里的 AI 判断替代用户反复确认：

- 当前方向是否符合 PROJECT_SPEC；
- 当前任务是否完成；
- 下一步应该继续、纠偏还是结束；
- 完成前是否需要从使用者视角进行体验测评；
- 完成时是否可以生成 COMPLETION_REPORT。

对于还没有完整任务书的空项目或既有老项目，SpecPilot 还需要在开发前完成轻量
onboarding，避免 Codex Worker 在合同不完整时直接写业务代码。

在需要与 GitHub 同步的项目中，SpecPilot 只负责按用户确认的轻量策略在必要节点
进行或请求提交、推送、tag、release 等标记动作；它不是完整 GitHub 平台、CI 管理器、
发布平台或 issue tracker。

体验测评 Hook 的目标是补上“从真实使用者角度检查成果”的闭环。它不是新的多 Agent
平台、复杂流程编排器或无限打磨机制；它只在完成前识别与目标用户、项目目标和验收
价值直接相关的明显体验问题，并把这些问题通过受控 Spec Steward / Development Plan /
Worker 流程转成可执行后续开发任务。

## 3. User Requirements
- 用户只输入一次 `开始工作` 后，系统应尽量自动推进到完成。
- Hook 判断主要使用 AI，而不是大量硬编码规则或正则。
- Stop Hook 是核心控制器，负责决定 `continue | revise | done | human_review`。
- `continue` 或 `revise` 时，Stop Hook 应通过 `decision:block` 给出下一步动作，驱动 Codex 继续。
- Hook 调用 AI 时使用当前 Codex 默认模型：`codex exec`，不传 `-m`，不写死模型、profile 或 endpoint。
- Profile 只允许通过 `CODEX_SPECPILOT_PROFILE` 或 `CODEX_PROFILE` 继承。
- 必须防递归：子进程使用 `CODEX_SPECPILOT_CHILD=1`。
- 必须支持 macOS 和 Windows。
- 判断体系文件不能由 Codex Worker 修改，只能由对应 Hook 在职责范围内写入。
- 不要把项目扩展成复杂安全平台；保持 Hook 轻量。
- 用户可以在开发中途调整目标、范围、优先级或验收标准；此时应先进入任务合同更新流程，而不是让 Codex Worker 直接继续写业务代码。
- Stop Hook 应能识别 `spec_update_required` 状态，暂停自动继续，并要求受控更新 PROJECT_SPEC 与后续 Development Plan。
- 空项目或既有老项目缺少 `.project_wiki/PROJECT_SPEC.md` 时，用户不需要手动运行接管脚本；Hook 应自动创建最小项目 Wiki 和占位任务书，并注入 onboarding 规则。
- 如果用户直接说 `开始工作` 但任务书不完整，Hook 必须延期开发并继续需求澄清，而不是让普通 Codex Worker 直接写业务代码。
- 完整 `PROJECT_SPEC.md` 只能通过受控 Hook onboarding / Spec Steward 流程写入，不能由普通 Codex Worker 自行生成或改写。
- SpecPilot 应支持可选的开发期 GitHub 自动同步；该能力不是强制要求，项目默认可以保持 local-only。
- onboarding 在正式 `PROJECT_SPEC.md` 最终确定前，必须询问用户项目应保持本地-only，还是需要同步到 GitHub。
- 如果用户表示不需要上传或同步，GitHub 策略默认记录为 local-only，后续 Hook 不应尝试 GitHub 上传、推送、tag 或 release。
- 如果用户希望上传或同步到 GitHub，onboarding 必须继续询问并写入必要 GitHub 策略信息，至少包括：使用哪个 GitHub 账号、credential 或认证方式，但不得在 `PROJECT_SPEC.md` 中暴露或存储 secret；仓库 public/private；允许创建新仓库还是必须使用已有仓库；哪些开发节点需要 commit、tag、release 或其他 GitHub marker；自动 push/tag/release 是否允许，还是需要 human confirmation。
- Hook 应在必要开发节点根据用户确认的 `PROJECT_SPEC` GitHub 策略决定是否 commit、push、tag、release 或执行其他 GitHub marker 操作。
- 如果 GitHub 策略缺失、含糊或凭据不可用，Hook 必须 fail safe：保持 local-only 或进入 `human_review`，不得假装同步成功。
- 项目文件中不得存储 API key、token、private key、密码或其他 credential secret。
- Hook 升级后，应能在目标项目运行时自动补齐或刷新受管 Hook 文件、Hook 配置和静态 Wiki 模板，以适配新版 Hook。
- macOS 应提供一键安装入口；安装器不能依赖固定仓库路径，应自动识别自身所在目录和 Codex 配置目录，安装后用户只需在 Codex 中启用 Hook。
- 当 Stop Hook 或完成流程判断当前项目任务达到 `done` 时，必须先启动使用者视角体验测评 Hook，而不是立即进入最终完成报告。
- 体验测评 Hook 应尽可能真实地运行、打开、操作或检查项目成果，并输出详细体验测评，包括用户实际会遇到的明显问题、阻碍、困惑、缺失和高价值改进。
- 体验测评发现中只有与目标用户、项目目标、验收标准或真实使用路径直接相关，且具备明确价值的问题，才能被转换为新的项目需求或 Development Plan 任务。
- 体验测评 Hook 不得把纯主观偏好、低价值润色、无限打磨、非目标用户场景、与项目目标不相关的问题转成新需求。
- 有效体验测评发现必须进入受控 Spec Steward / Development Plan / Worker 流程，不能由普通 Codex Worker 绕过任务合同直接继续开发。
- 开发完成、体验测评、任务合同更新、继续开发的循环可以反复进行；只有最后一次体验测评找不到明显问题或值得继续开发的改进点时，才进入最终完成报告。

## 4. Non-Goals
- 不做完整 GH 平台。
- 不做 GitHub CI 管理器。
- 不做 release platform。
- 不做 issue tracker。
- 不做 n8n 式流程编排器。
- 不做多 Agent 平台。
- 不做 RAG。
- 不做图数据库。
- 不做复杂长期记忆系统。
- 不做外层调度器。
- 不做单独的用户研究平台或可用性实验平台。
- 不把体验测评扩展成无限打磨、审美偏好收集或脱离项目目标的改进清单。
- 不单独配置模型。
- 不写死 GPT、Qwen、API endpoint 或某个 profile。
- 不用大量硬编码 denylist 构建权限引擎。
- 不做复杂项目扫描或资产盘点系统。
- 不在项目文件中保存 GitHub token、API key、private key、密码或 credential secret。

## 5. Allowed Scope
开发 SpecPilot 自身时，允许修改：

- `hooks/*.py`
- `.codex/hooks.json`
- `tests/*`
- `README.md`
- `.project_wiki/INJECTION.md`
- `.project_wiki/PROJECT_SPEC.md`（用户明确要求时）
- `.project_wiki/PROJECT_SPEC_TEMPLATE.md`（用户明确要求时）

为实现轻量 GitHub 同步策略，允许在上述范围内增加 Hook/onboarding 逻辑、测试和文档；不得把 credential secret 写入项目文件。

为实现使用者视角体验测评闭环，允许在上述范围内增加完成前测评 Hook、测评状态、受控 Spec Steward 入口、Development Plan 更新逻辑、测试和文档；不得引入多 Agent 平台、RAG、图数据库、外层调度器或复杂流程编排。

## 6. Protected Scope
Codex Worker 不能修改判断体系和监督状态文件，除非用户明确要求开发 SpecPilot
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

普通受监督项目中，完整 `PROJECT_SPEC.md` 只能由受控 Hook onboarding / Spec Steward
流程在信息足够时写入；普通 Codex Worker 不得绕过该流程生成或改写任务合同。

GitHub 同步策略属于任务合同内容，只能通过受控 Hook onboarding / Spec Steward 流程写入或更新；普通 Codex Worker 不得绕过该流程修改 GitHub policy。

体验测评发现转换出的新需求或任务合同变化，也只能通过受控体验测评 Hook / Spec Steward
流程写入或更新；普通 Codex Worker 不得绕过该流程把测评建议直接变成开发范围。

## 7. Development Plan
- [ ] TASK-001: 重新校准项目说明和注入规则
  - Goal: 把 SpecPilot 的方向明确为任务书驱动的无人值守自动开发闭环。
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
  - Notes: 试跑前必须保证环境中的 `codex exec` 可用；引入 TASK-010 后，试跑的 done 前还必须经过体验测评 Hook。

- [ ] TASK-006: 支持开发中途目标变更治理
  - Goal: 当用户在开发过程中调整目标、范围、优先级或验收标准时，SpecPilot 暂停 Worker 开发，先进入任务合同更新流程。
  - Scope: `hooks/*.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`
  - Acceptance: Stop Hook 支持 `spec_update_required`；UserPromptSubmit 注入目标变更规则；提供轻量 Spec Steward 受控入口用于生成或写入 PROJECT_SPEC 更新；README 说明用户、需求解析、Spec Steward、Planner、Worker、Stop Hook 的分工；测试覆盖该状态不会 auto-continue，且 Spec Steward 默认不写入、显式 apply 才写入。
  - Notes: 不引入多 Agent 平台；只定义轻量分工和状态。

- [ ] TASK-007: 支持 Hook 自动接管空项目和老项目
  - Goal: 当目标项目没有完整任务书时，由 Hook 自动创建最小项目 Wiki、进入需求澄清，并在信息足够后写入正式 PROJECT_SPEC.md。
  - Scope: `hooks/project_paths.py`, `hooks/project_injector.py`, `hooks/user_prompt_submit.py`, `hooks/stop_judge.py`, `tests/*`, `README.md`
  - Acceptance: 用户不需要手动运行接管脚本；缺失 `.project_wiki/PROJECT_SPEC.md` 时 UserPromptSubmit 自动创建占位任务书并注入 onboarding 规则；如果用户直接说 `开始工作` 但任务书不完整，Hook 必须先延期开发并继续 onboarding；Stop Hook 可在 onboarding 信息足够时写入完整 PROJECT_SPEC；测试覆盖空项目、老项目、路径解析、spec_update_required 与 onboarding。
  - Notes: 保持轻量；不引入外层调度器、多 Agent、RAG 或复杂项目扫描。

- [ ] TASK-008: 支持轻量 GitHub 同步 onboarding 策略
  - Goal: 在 onboarding 中确认项目 local-only 或 GitHub sync 策略，并让 Hook 在必要开发节点按策略处理 commit、push、tag、release 或其他 GitHub marker。
  - Scope: `hooks/*.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`
  - Acceptance: onboarding 在正式 PROJECT_SPEC 确定前询问 local-only 或 GitHub sync；local-only 时不尝试 GitHub 操作；GitHub sync 时收集账号/认证方式描述但不保存 secret、public/private、新建或既有仓库、marker 节点、自动操作或人工确认策略；Hook 在策略缺失、含糊或凭据不可用时 fail safe 到 local-only 或 human_review；测试覆盖 local-only、策略完整、策略缺失、凭据不可用、禁止自动 push/tag/release 的场景。
  - Notes: 不引入完整 GitHub 平台、CI 管理、release platform、issue tracker、外层调度器或 credential 存储。

- [ ] TASK-009: 支持 Hook 运行时自更新和 macOS 一键安装
  - Goal: Hook 升级后，目标项目能自动补齐或刷新受管运行文件；macOS 用户能通过一键安装入口完成全局 Hook 安装。
  - Scope: `hooks/project_injector.py`, `hooks/user_prompt_submit.py`, `hooks/stop_judge.py`, `hooks/permission_policy.py`, `install/macos/*`, `tests/*`, `README.md`, `.project_wiki/PROJECT_SPEC.md`
  - Acceptance: Hook 运行时只刷新 `hooks/*.py`、`.codex/hooks.json` 和静态 `.project_wiki` 模板/说明文件；不覆盖 `PROJECT_SPEC.md`、JUDGE、latest_context、judge_latest、loop_state、guard_log、COMPLETION_REPORT；目标项目写入本地 manifest 用于后续升级；macOS 安装器自动识别仓库路径和 Codex 配置目录，写入用户级 `hooks.json`，不要求或保存 secret；测试覆盖运行时升级、PROJECT_SPEC 保留、安装器生成配置和幂等安装。
  - Notes: 保持轻量；不做复杂包管理器、后台服务、外层调度器或自动远程更新。

- [ ] TASK-010: 新增使用者视角体验测评 Hook
  - Goal: 在当前完成流程宣告完成后、最终完成报告前，加入真实使用者视角的体验测评闭环，并把有效发现转成受控任务合同更新。
  - Scope: `hooks/*.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`, `.project_wiki/COMPLETION_REPORT_TEMPLATE.md`
  - Acceptance: Stop Hook 的 `done` 不再直接等于最终结束，而是先触发体验测评 Hook；体验测评 Hook 能尽可能真实地使用项目成果并输出详细测评；测评结果按目标用户、项目目标、验收标准和价值过滤；有效发现进入 `spec_update_required` 或等价受控 Spec Steward 流程并更新 Development Plan；无明显问题或高价值改进时才允许生成最终完成报告；测试覆盖有问题继续开发、无问题最终完成、低价值/主观/非目标场景建议被过滤、循环次数或反复测评的 fail-safe。
  - Notes: 保持轻量；不引入多 Agent 平台、RAG、图数据库、外层调度器、复杂流程编排或无限打磨机制。

## 8. Acceptance Criteria
- 用户只输入一次 `开始工作` 后，Hook 能持续推动 Codex 继续开发或纠偏。
- Stop Hook 能基于 AI 输出可靠处理 `continue | revise | done | human_review`。
- Stop Hook 能在用户修改目标、范围、优先级或验收标准时处理 `spec_update_required`，并暂停自动继续。
- 空项目或既有老项目缺少完整任务书时，Hook 能自动创建最小项目 Wiki 和占位 `PROJECT_SPEC.md`，并进入 onboarding。
- 如果用户在任务书不完整时直接说 `开始工作`，Hook 必须延期开发并继续需求澄清。
- onboarding 信息足够后，完整 `PROJECT_SPEC.md` 只能由受控 Hook onboarding / Spec Steward 流程写入，不能由普通 Codex Worker 写入。
- onboarding 必须在正式 PROJECT_SPEC 确定前询问项目应保持 local-only 还是同步到 GitHub。
- 用户选择 local-only 或表示不需要上传/同步时，Hook 不应尝试 GitHub 上传、推送、tag 或 release。
- 用户选择 GitHub sync 时，PROJECT_SPEC 必须记录非 secret 的 GitHub 策略：账号/认证方式描述、仓库 public/private、新建或既有仓库、GitHub marker 节点、自动操作或人工确认策略。
- Hook 必须按 PROJECT_SPEC GitHub 策略在必要开发节点决定是否 commit、push、tag、release 或执行其他 GitHub marker 操作。
- GitHub 策略缺失、含糊或凭据不可用时，Hook 必须 fail safe 到 local-only 或 `human_review`，不得声称同步成功。
- 项目文件不得保存 API key、token、private key、密码或其他 credential secret。
- Hook 升级后，目标项目中受管 Hook 文件、Hook 配置和静态 Wiki 模板能自动补齐或刷新，但不得覆盖任务合同、判断状态、日志、循环状态或完成报告。
- macOS 一键安装器能自动定位自身仓库和 Codex 配置目录，安装用户级 Hook 配置，不依赖固定路径，不保存 secret。
- 当当前完成流程判断任务 `done` 时，必须先运行使用者视角体验测评 Hook，不能立即生成最终完成报告。
- 体验测评 Hook 必须尽可能真实地使用项目成果，并输出包含明显问题、阻碍、困惑、缺失和高价值改进的详细测评。
- 体验测评 Hook 必须过滤纯主观偏好、低价值润色、无限打磨、非目标用户场景和与项目目标不相关的问题，不得把它们转成新需求。
- 有效体验测评发现必须通过受控 Spec Steward / Development Plan / Worker 流程转成后续任务，普通 Codex Worker 不得绕过任务合同直接开发。
- 开发、体验测评、合同更新、继续开发可以循环；最后一次体验测评找不到明显问题或高价值改进时，才允许生成或更新 `.project_wiki/COMPLETION_REPORT.md`。
- 判断体系文件不能被普通 Codex Worker 修改。
- Hook 保持轻量，不引入复杂规则引擎、RAG、多 Agent、外层调度器、完整 GitHub 平台、CI 管理器、release platform、issue tracker、复杂流程编排或无限打磨机制。
- `codex exec` 使用当前默认模型，不写死模型、profile 或 endpoint。
- macOS 和 Windows 的路径与启动方式都有测试覆盖。

## 9. Stop Conditions
- AI 判断需求不清或需要用户决策时，进入 `human_review`。
- `codex exec` 不可用或输出无法解析时，不假装监督成功。
- 连续自动推进达到 loop 限制仍未完成时，进入 `human_review`。
- 下一步动作要求修改判断体系核心文件且当前不是 SpecPilot 自开发任务时，进入 `human_review`。
- 任务书缺失或不完整且 onboarding 信息不足时，延期开发并继续需求澄清。
- GitHub 同步策略缺失、含糊或与当前动作冲突时，保持 local-only 或进入 `human_review`。
- GitHub 凭据不可用、认证失败、远端不可访问或 GitHub 操作结果无法确认时，不得假装成功；应进入 `human_review` 或按策略降级为 local-only。
- 自动 push、tag、release 或仓库创建未被 PROJECT_SPEC 明确允许时，必须请求人工确认或进入 `human_review`。
- 体验测评 Hook 无法真实使用或验证项目成果时，不得声称最终完成；应标记为 environment-blocked、code-ready 或进入 `human_review`。
- 体验测评发现的问题是否应转为新需求存在歧义、与任务合同冲突或需要用户取舍时，进入 `spec_update_required` 或 `human_review`。
- 体验测评循环反复提出低价值、主观、非目标场景或无法收敛的建议时，应过滤这些建议，并在达到循环限制时进入 `human_review`，不得无限打磨。

## 10. Submission Requirements
- 每次开发提交必须说明属于 code-ready、environment-blocked 还是 real-world verified。
- 涉及 GitHub 同步的提交或完成报告必须说明实际 GitHub 状态：local-only、sync skipped by policy、sync pending human confirmation、sync environment-blocked，或 sync verified with direct evidence。
- 涉及体验测评的提交或完成报告必须说明体验测评状态：not run、evaluation environment-blocked、issues found and converted to spec update、issues filtered as low-value/out-of-scope，或 no obvious user-facing issues found。
- 完成真实试跑前，不得声称无人值守 LLM supervisor 已完全跑通。
- 最终完成报告只能在最后一次体验测评找不到明显问题或值得继续开发的改进点后生成或更新。
- 修改后至少运行不触发无关状态污染的基础验证。
