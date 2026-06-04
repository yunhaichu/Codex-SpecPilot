# Project Specification

## Active Mission Snapshot
- Current overall goal: Codex SpecPilot must remain a lightweight task-book-driven unattended development loop.
- Current phase: v3.0 automatic phase-transition governance has completed local implementation and validation through TASK-029.
- Current phase goal: Complete the current-turn explicitly authorized v3.0 GitHub release after validation, using the already-authenticated local GitHub CLI account `yunhaichu` for repository `yunhaichu/Codex-SpecPilot`.
- Current task range: TASK-029 is complete and locally validated. The only currently authorized remaining work is release execution for v3.0: verify local state, commit validated v3.0 changes, push `origin/main`, create annotated tag `v3.0`, and create GitHub release `v3.0`.
- Current non-goals: no RAG, no multi-agent platform, no graph database, no external scheduler, no cloud default, no credential storage, no complex workflow platform.
- Current safety boundary: ordinary Worker must not directly edit task contracts or judge-system files; controlled Spec Steward/onboarding/spec update flows may update PROJECT_SPEC only for confirmed contract changes. After a complete PROJECT_SPEC exists, controlled flows must not ask the user to reconfirm routine phase transitions, next-task activation, status reconciliation, experience-evaluation follow-up, or Development Plan carry-over.
- Current release target: current-turn explicit GitHub release authorization for `v3.0` only, after validation. Use local authenticated `gh` account `yunhaichu` with repository `yunhaichu/Codex-SpecPilot`; do not request, write, print, or store any API key, token, private key, password, or credential secret.
- Context priority: Active Mission Snapshot -> current phase -> current TASK -> acceptance criteria -> historical summaries/evidence.

## 0. Project Mode
当前项目模式：`specpilot_self_development`

当前下一阶段：`自主合同治理、证据闭环与目标锚定`

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

当用户在开发中途提出需求、范围、优先级、验收标准或任务合同相关修改建议时，
SpecPilot 不应要求用户手动编辑 `PROJECT_SPEC.md` 或任务书相关文件，而应自动进入
受控 Spec Steward / onboarding / spec update 流程。信息足够时，该受控流程直接写入
更新后的 `PROJECT_SPEC.md` 并同步更新 Development Plan；信息不足时，只提出最少量
澄清问题。当 Codex 已经总结过拟议合同变化且用户回复 `同意` 或等价确认时，
Spec Steward 可以立即应用该已确认更新，不再要求用户手动改文件。

SpecPilot 还应在 onboarding 阶段支持可选的轻量 GitHub 同步策略确认。项目可以
保持本地-only；只有用户明确选择上传或同步时，Hook/onboarding 才收集必要的
GitHub 策略，并在后续开发节点按任务书策略决定是否提交、推送、打 tag、发布或
记录其他 GitHub 标记。

当当前完成流程认为项目已经完成时，SpecPilot 不应立刻视为最终结束，而应先启动
一个使用者视角体验测评 Hook。该 Hook 尽可能真实地使用项目成果，输出用户实际会
遇到的明显问题、阻碍、困惑、缺失和高价值改进，并将有效测评发现转入受控任务合同
更新流程。开发、测评、合同更新、继续开发可以反复循环，直到体验测评找不到明显问题
或值得继续开发的改进点后，再进入最终完成报告。

当开发中途遇到实现、测试、规划或阶段推进问题时，SpecPilot 不应机械地把问题丢给
用户。只要任务书、项目 Wiki、当前目标和阶段目标中已有足够事实，Hook 应推动 Codex
先自行研究、修复、验证或调整执行计划。如果没有直接解法，应先判断当前阶段目标或
Development Plan 是否存在问题，再通过受控任务合同更新或计划调整继续推进；只有确实
需要用户取舍、凭据、外部环境动作、受保护范围授权或不可消除歧义时，才进入
`human_review`。

SpecPilot 还应支持长任务书。Hook、Spec Steward 和 onboarding 不应依赖把完整
`PROJECT_SPEC.md` 无脑塞进一次提示；遇到长任务、长背景或大量阶段计划时，应使用
紧凑摘要、关键章节抽取或分段保真方式，确保目标、范围、保护边界、Development Plan
后段任务、验收标准、停止条件、GitHub 策略和提交要求不会因为篇幅限制丢失。

长 `PROJECT_SPEC.md` 还必须保留当前目标锚点。SpecPilot 应在任务合同中维护
Active Mission Snapshot / current goal anchor，用于说明当前阶段、当前任务、当前
验收重点、当前阻塞和下一步允许动作。历史已完成阶段只能作为证据和背景，不能被 Hook、
Spec Steward 或 Stop Judge 误当作当前目标。

Hook、Spec Steward 和 Stop Judge 在读取长任务书或紧凑上下文时，判断优先级必须是：
Active Mission Snapshot -> current Phase -> current TASK -> acceptance criteria -> historical summaries。
如果历史总结、完成阶段或旧任务与当前 Active Mission Snapshot 冲突，应优先按当前目标锚点执行，并触发受控证据核对或合同修复。

如果用户在当前阶段再次明确要求发布，SpecPilot 应先通过受控 Spec Steward 对齐 GitHub Sync Policy 和发布目标，再执行验证、commit、push、tag 和 release；不得请求、保存或暴露任何 secret。历史上下文中的 `vv2.6` 仅作为 `v2.6` 笔误处理，不自动构成当前发布目标。

## 2. Background
Codex 默认是一轮一轮被用户推动的交互工具。SpecPilot 的目标是让 Codex 在明确
任务书约束下进入无人值守的连续工作模式，由 Hook 里的 AI 判断替代用户反复确认：

- 当前方向是否符合 PROJECT_SPEC；
- 当前任务是否完成；
- 下一步应该继续、纠偏还是结束；
- 用户提出变化或确认变化时，是否应进入受控任务合同更新流程；
- 完成前是否需要从使用者视角进行体验测评；
- 完成时是否可以生成 COMPLETION_REPORT。

对于还没有完整任务书的空项目或既有老项目，SpecPilot 还需要在开发前完成轻量
onboarding，避免 Codex Worker 在合同不完整时直接写业务代码。

对于开发中途的目标变化，SpecPilot 需要把“用户提修改建议”或“用户确认已总结的合同变化”
识别为任务合同更新事件，并由受控 Spec Steward / onboarding / spec update 流程处理，
而不是要求用户手工改任务书，也不是让普通 Codex Worker 绕过合同继续开发。

在需要与 GitHub 同步的项目中，SpecPilot 只负责按用户确认的轻量策略在必要节点
进行或请求提交、推送、tag、release 等标记动作；它不是完整 GitHub 平台、CI 管理器、
发布平台或 issue tracker。

体验测评 Hook 的目标是补上“从真实使用者角度检查成果”的闭环。它不是新的多 Agent
平台、复杂流程编排器或无限打磨机制；它只在完成前识别与目标用户、项目目标和验收
价值直接相关的明显体验问题，并把这些问题通过受控 Spec Steward / Development Plan /
Worker 流程转成可执行后续开发任务。

开发中途卡点治理的目标是让 Hook 更像真实项目负责人：能基于已有事实继续推动问题
解决，而不是把普通工程卡点升级成用户负担。只有当问题本质上需要用户决策、权限、
凭据、范围变更或合同澄清时，才暂停自动推进。

长任务书治理的目标是避免任务书一长就影响导入、判断或更新。SpecPilot 应优先保留
任务合同中会影响判断的结构性事实，而不是简单按字符数截断全文。

当前阶段进一步要求 SpecPilot 解决长任务书中的目标漂移与证据闭环问题：历史阶段、
完成报告、旧 Development Plan 和旧摘要可能很多，但它们只能证明过去做过什么，不能
替代当前任务目标。Hook 必须能从 Active Mission Snapshot 和当前阶段任务中恢复工作
坐标，并能在状态、证据、任务完成声明和当前目标不一致时触发核对、修复或受控合同更新。

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
- 用户不应被要求手动编辑 `PROJECT_SPEC.md` 或任务书相关文件来完成需求变化；SpecPilot 必须自动进入受控 Spec Steward / onboarding / spec update 流程处理。
- 当用户给出修改建议且信息足够时，受控 Spec Steward / onboarding / spec update 流程应直接写入更新后的 `PROJECT_SPEC.md` 并更新 Development Plan。
- 当用户给出修改建议但信息不足时，受控流程只应提出最少量澄清问题，不应要求用户手动改文件。
- 当 Codex 已经总结拟议合同变化且用户回复 `同意` 或等价确认时，Spec Steward 允许立即应用该已确认更新，不再追加手工编辑要求。
- 自动任务合同更新规则适用于 `PROJECT_SPEC.md` 这个任务合同，也适用于后续实现中需要保持一致的相关 SpecPilot instruction/template 文件。
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
- 开发中途遇到实现、测试、依赖、规划或阶段推进问题时，Hook 应优先基于 `.project_wiki` 事实、当前项目目标、阶段目标和 Development Plan 给出自解或研究路径，而不是默认进入 `human_review`。
- 如果没有直接解决思路，Hook 应先要求 Codex 重新审视当前阶段目标或 Development Plan 假设，必要时生成受控 `spec_update_required` / 计划更新请求，然后继续推动开发。
- 只有问题需要真实用户取舍、凭据/secret、外部环境动作、受保护范围授权、目标范围确认或不可消除歧义时，才把问题交给用户。
- Hook、Spec Steward 和 onboarding 必须支持长 `PROJECT_SPEC.md` / 长任务书导入，保留关键章节、后段 Development Plan 任务和提交要求，不得因为简单截断导致后续任务或验收标准丢失。
- 用户不应被要求手动缩短、拆分或重写任务书来绕过 Hook 篇幅限制；必要的紧凑化或分段读取应由 SpecPilot 处理。
- PROJECT_SPEC 顶部必须维护 Active Mission Snapshot / 当前目标锚点，记录当前总目标、当前阶段、当前任务范围、当前非目标、质量门槛、发布目标和上下文优先级。
- Hook、Spec Steward、Stop Judge、UserPromptSubmit 和体验测评必须优先使用 Active Mission Snapshot，再读取当前 Phase、当前 TASK、验收标准和历史摘要。
- 长任务书中的已完成阶段和历史证据不得继续占据当前判断主上下文，必须压缩为 Phase Summary 或历史证据输入。
- Spec Steward 必须支持受控 section patch / task patch / phase summary patch 更新，避免每次依赖完整 PROJECT_SPEC 全文重写。
- 本地 artifact、report、completion report、latest context 和 judge state 已能证明任务完成时，SpecPilot 应生成受控任务状态更新，而不是默认把状态对账交给用户。
- Spec Steward 的受控写入通道必须区别于普通 Worker 写入，避免受控任务合同更新被普通保护规则误拦。
- 同一产品主线内阶段完成并建议下一阶段时，SpecPilot 应能生成下一阶段合同草案并进入受控更新，不得把普通阶段衔接问题默认交给用户。
- human_review 必须按类型收窄，工程卡点、证据缺口、状态不同步和合同缺口优先自动修复或进入受控 spec_update_required，只有真实用户决策才问用户。
- 任务报告状态和 Hook/Spec Steward 状态必须归一化，避免类似 quality_fix_required 与 quality_risks 的口径不一致阻塞受控更新。
- novelcreatepilot 暴露出的长任务书、阶段推进、任务状态对账、Spec Steward patch、目标锚定和 human_review 收窄场景必须成为 SpecPilot 回归验证样例。
- 长 `PROJECT_SPEC.md` 必须维护 Active Mission Snapshot / current goal anchor，明确当前阶段、当前 TASK、当前验收重点、当前状态和下一步允许动作。
- 已完成历史阶段和历史摘要只能作为 evidence/background，不得覆盖 Active Mission Snapshot 或当前阶段目标。
- Hook、Spec Steward、Stop Judge 的任务书读取和判断优先级必须为：Active Mission Snapshot -> current Phase -> current TASK -> acceptance criteria -> historical summaries。
- 如果当前目标锚点、Development Plan、历史完成声明、完成报告、测试证据或状态文件存在冲突，Hook 必须触发 goal drift detection 或 task evidence reconciliation，而不是直接按旧结论继续。
- SpecPilot 必须能以 section patch 方式更新 `PROJECT_SPEC.md`，避免每次合同更新都重写整份长任务书导致历史、后段计划或提交要求丢失。
- Spec Steward 写入 `PROJECT_SPEC.md`、Active Mission Snapshot、Development Plan 和相关模板时必须走受控写入通道，保留 diff/evidence/decision summary，并防止普通 Worker 绕过写入。
- 阶段完成时，SpecPilot 应能生成 phase closure evidence，并起草下一阶段任务合同更新，但只有经受控 Spec Steward 流程确认后才写入。
- `human_review` 分类必须收窄：普通实现失败、测试失败、计划不顺、状态不一致优先由 Hook 自解、证据核对或合同修复处理；只有真实需要用户取舍、secret、外部动作、授权或不可消除歧义时才升级用户。
- Hook 和状态文件中的状态枚举必须规范化，避免 `done`、`complete`、`finished`、`code-ready`、`real-world verified` 等概念混用导致错误推进。
- SpecPilot 必须有上下文预算和阶段历史归档策略，确保长历史不会挤掉当前目标锚点、后段任务、验收标准、停止条件、GitHub 策略和提交要求。
- 本阶段必须用 novelcreatepilot 或等价真实受监督项目做回归验证，证明 Active Mission Snapshot、目标锚定、证据闭环和长任务书策略在真实项目中有效。
- 本阶段默认只要求本地验证；只有用户在当前回合明确要求发布时，才通过受控 Spec Steward 对齐 GitHub 发布策略、tag/release 目标和自动操作权限；`vv2.6` 仅在该发布流程中按 `v2.6` 笔误处理。
- 完整 `PROJECT_SPEC.md` 已形成后，SpecPilot 不得在不同阶段过渡、下一阶段计划、任务状态对账、体验测评后续任务或 Development Plan 衔接时反复要求用户确认；Stop Hook、Spec Steward 和 Worker 必须根据 `PROJECT_SPEC.md`、latest context、wiki evidence 和当前目标自动继续推进。
- 只有项目创建初期 / onboarding 尚未形成完整 `PROJECT_SPEC.md`，且需求或目标信息不足时，才允许反复向用户确认需求和目标。
- 普通对话、问答、说明、状态询问或非开发型交流不得被当成新任务启动；Hook 应为所有普通对话写入轻量反馈或轻量状态记录，避免沉默或误触发任务推进。
- 当 TASK 已完成且 Development Plan 中存在明确后续工作，或体验测评发现可转入受控任务合同更新的后续任务时，SpecPilot 应自动生成或应用窄范围 section patch，并继续推进下一项授权任务，除非存在真实用户取舍、secret、外部动作、受保护范围授权或不可消除歧义。
- Stop Hook 输出 `spec_update_required` 时，若所需变化可由现有 `PROJECT_SPEC.md`、latest context 和 wiki evidence 明确推出，Spec Steward 应直接应用受控 section patch；不得再把“是否进入下一阶段”作为确认问题交给用户。

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
- 不要求用户手动维护任务合同文件来完成需求变化。
- 不把普通工程卡点、测试失败、规划不顺或阶段目标疑似不合理默认升级给用户处理。
- 不要求用户手动压缩、拆分或重新导入长任务书。
- 不把历史完成阶段、历史摘要或旧完成报告当作当前目标来源。
- 不用全文重写作为长任务书更新的默认机制。
- 不做复杂文档管理平台或额外知识库。
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
- `.project_wiki/PROJECT_SPEC.md`（用户明确要求时，或由受控 Spec Steward / onboarding / spec update 流程处理已确认合同变化时）
- `.project_wiki/PROJECT_SPEC_TEMPLATE.md`（用户明确要求时，或为保持任务合同更新流程一致性时）

为实现轻量 GitHub 同步策略，允许在上述范围内增加 Hook/onboarding 逻辑、测试和文档；不得把 credential secret 写入项目文件。

为实现使用者视角体验测评闭环，允许在上述范围内增加完成前测评 Hook、测评状态、受控 Spec Steward 入口、Development Plan 更新逻辑、测试和文档；不得引入多 Agent 平台、RAG、图数据库、外层调度器或复杂流程编排。

为实现自动任务合同更新确认流，允许在上述范围内增加用户修改建议识别、确认语义处理、受控 Spec Steward / onboarding / spec update 写入、Development Plan 更新、README、INJECTION 和模板一致性维护逻辑；不得让普通 Codex Worker 绕过该受控流程直接改写任务合同。

为实现开发中途卡点自解和阶段目标重规划，允许在上述范围内调整 Stop Hook 提示词、
下一步动作生成、任务合同更新入口、README、INJECTION、模板和测试；不得引入外层
调度器、多 Agent 平台、RAG 或复杂流程编排。

为实现长任务书支持，允许在上述范围内增加任务书紧凑化、关键章节抽取、分段保真、
提示构造和测试；不得引入复杂文档平台或要求用户手动维护额外任务书分片。

为实现自主合同治理、证据闭环与目标锚定阶段，允许在上述范围内增加 Active Mission Snapshot、goal drift detection、section patch 更新、task evidence reconciliation、受控 Spec Steward 写入通道、phase closure / next phase draft、human_review taxonomy、status enum normalization、context budget / phase-history archive 策略和 novelcreatepilot 回归验证相关逻辑、测试和文档；不得引入 RAG、多 Agent 平台、图数据库、外层调度器、云默认或复杂流程编排。

如果用户明确要求发布，允许在受控 GitHub Sync Policy 对齐且验证完成后按任务书策略执行 git commit、push、tag 和 GitHub release；不得写入、请求或暴露任何 credential secret。

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

用户提出的修改建议、范围调整、验收标准变化，或对 Codex 已总结合同变化的 `同意` / 等价确认，只能通过受控 Spec Steward / onboarding / spec update 流程写入 `PROJECT_SPEC.md` 及相关 instruction/template 文件；普通 Codex Worker 不得要求用户手动改文件，也不得自行绕过受控流程改写任务合同。

Active Mission Snapshot、current goal anchor、Development Plan、GitHub policy、Submission Requirements、阶段关闭证据和下一阶段合同草案都属于任务合同治理内容，只能由受控 Hook / Spec Steward / spec update 流程写入或更新。普通 Codex Worker 不得绕过受控流程直接修改这些合同治理内容。

## 7. Current Phase Snapshot Evidence
- Current Phase: TASK-024 through TASK-027 已完成本地验证
- Current Release Target: local validation for protected-maintenance repair flow; no new release is required unless the user explicitly asks.
- Current Goal: 解决 019e8233 会话暴露的硬权限死锁：用户明确授权受保护 Hook 维护时，授权必须能通过受控租约传递给 PreToolUse；Spec Steward 自身故障时必须有有限维护修复通道；Active Snapshot 与正式 GitHub policy 冲突时必须进入受控策略修复，而不是只把问题交给用户。
- Current TASK Range: TASK-024 through TASK-027
- Current Acceptance Focus: 已验证用户确认可生成短时一次性租约，PreToolUse 只放行并消费租约指定维护文件，Spec Steward runtime blocked 会进入 `maintenance_authorization_required`，GitHub policy 与 Active Snapshot 冲突会进入受控 `spec_update_required` 策略修复。
- Current GitHub Policy: 本阶段不要求新发布；如 Active Snapshot、Submission Requirements 或用户命令要求 GitHub 远端动作但正式 GitHub policy 为 local-only，Stop Hook 必须触发受控 policy reconciliation，而不是把远端动作当作普通 auto-continue。
- Historical Phase Rule: TASK-001 through TASK-013 are completed historical evidence. They remain protected context and regression baseline, but they are not the current development goal.
- Next Allowed Action: TASK-028 已通过 `python3 tests/smoke_test.py`（155/155 passed）。当前没有新的开发任务；若用户要求发布新版本或新增下一阶段任务，先通过受控 Spec Steward 更新任务合同。

## 8. Development Plan
- [x] TASK-001: 重新校准项目说明和注入规则
  - Goal: 把 SpecPilot 的方向明确为任务书驱动的无人值守自动开发闭环。
  - Scope: `PROJECT_SPEC.md`, `INJECTION.md`, `README.md`
  - Acceptance: 文档不再把项目描述成复杂权限 Guard，明确 Stop Hook 自动推进目标。
  - Notes: 不修改 Hook 业务逻辑。

- [x] TASK-002: 收敛 Hook 为轻量 AI 控制管道
  - Goal: 保留最小确定性运行逻辑，把方向、继续、纠偏、完成判断交给 AI。
  - Scope: `hooks/*.py`, `tests/*`
  - Acceptance: PreToolUse 不再是复杂权限引擎；Stop Hook 成为主要自动推进控制器。
  - Notes: 保留防递归、超时、JSON 解析、AI 调用失败处理和判断体系自保护。

- [x] TASK-003: 修复自动继续闭环
  - Goal: 让 Stop Hook 在 `continue` / `revise` 时可靠驱动下一轮，在 `done` 时生成完成报告。
  - Scope: `hooks/stop_judge.py`, `hooks/codex_client.py`, `tests/*`
  - Acceptance: `decision:block` 携带明确 next_action；loop_state 正确计数和重置；latest_context 正确记录 auto_continue。
  - Notes: 不把 code-ready 说成 real-world verified；引入 TASK-010 后，`done` 进入最终报告前必须先经过体验测评 Hook。

- [x] TASK-004: 加入 macOS / Windows 兼容验证
  - Goal: Hook 路径、诊断脚本和测试不依赖单一 shell 或平台路径格式。
  - Scope: `hooks/*.py`, `tests/*`
  - Acceptance: 使用跨平台路径处理；测试覆盖 Windows 风格路径和当前 macOS 路径。
  - Notes: 不引入外部依赖。

- [x] TASK-005: 做真实无人值守闭环试跑
  - Goal: 验证用户只输入一次 `开始工作` 后，Codex 能在 Hook 控制下自动推进到 done。
  - Scope: `examples/minimal_supervised_project`, `.project_wiki/COMPLETION_REPORT.md`, `.project_wiki/PROGRESS.md`
  - Acceptance: 记录 direct evidence，明确区分 code-ready、environment-blocked、real-world verified。
  - Notes: 试跑前必须保证环境中的 `codex exec` 可用；引入 TASK-010 后，试跑的 done 前还必须经过体验测评 Hook。

- [x] TASK-006: 支持开发中途目标变更治理
  - Goal: 当用户在开发过程中调整目标、范围、优先级或验收标准时，SpecPilot 暂停 Worker 开发，先进入任务合同更新流程。
  - Scope: `hooks/*.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`
  - Acceptance: Stop Hook 支持 `spec_update_required`；UserPromptSubmit 注入目标变更规则；提供轻量 Spec Steward 受控入口用于生成或写入 PROJECT_SPEC 更新；README 说明用户、需求解析、Spec Steward、Planner、Worker、Stop Hook 的分工；测试覆盖该状态不会 auto-continue，且 Spec Steward 默认不写入、显式 apply 才写入。
  - Notes: 不引入多 Agent 平台；只定义轻量分工和状态。TASK-011 会进一步把用户修改建议和 `同意` 确认接入自动受控写入流程，避免要求用户手动编辑任务书。

- [x] TASK-007: 支持 Hook 自动接管空项目和老项目
  - Goal: 当目标项目没有完整任务书时，由 Hook 自动创建最小项目 Wiki、进入需求澄清，并在信息足够后写入正式 PROJECT_SPEC.md。
  - Scope: `hooks/project_paths.py`, `hooks/project_injector.py`, `hooks/user_prompt_submit.py`, `hooks/stop_judge.py`, `tests/*`, `README.md`
  - Acceptance: 用户不需要手动运行接管脚本；缺失 `.project_wiki/PROJECT_SPEC.md` 时 UserPromptSubmit 自动创建占位任务书并注入 onboarding 规则；如果用户直接说 `开始工作` 但任务书不完整，Hook 必须先延期开发并继续 onboarding；Stop Hook 可在 onboarding 信息足够时写入完整 PROJECT_SPEC；测试覆盖空项目、老项目、路径解析、spec_update_required 与 onboarding。
  - Notes: 保持轻量；不引入外层调度器、多 Agent、RAG 或复杂项目扫描。

- [x] TASK-008: 支持轻量 GitHub 同步 onboarding 策略
  - Goal: 在 onboarding 中确认项目 local-only 或 GitHub sync 策略，并让 Hook 在必要开发节点按策略处理 commit、push、tag、release 或其他 GitHub marker。
  - Scope: `hooks/*.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`
  - Acceptance: onboarding 在正式 PROJECT_SPEC 确定前询问 local-only 或 GitHub sync；local-only 时不尝试 GitHub 操作；GitHub sync 时收集账号/认证方式描述但不保存 secret、public/private、新建或既有仓库、marker 节点、自动操作或人工确认策略；Hook 在策略缺失、含糊或凭据不可用时 fail safe 到 local-only 或 human_review；测试覆盖 local-only、策略完整、策略缺失、凭据不可用、禁止自动 push/tag/release 的场景。
  - Notes: 不引入完整 GitHub 平台、CI 管理、release platform、issue tracker、外层调度器或 credential 存储。

- [x] TASK-009: 支持 Hook 运行时自更新和 macOS 一键安装
  - Goal: Hook 升级后，目标项目能自动补齐或刷新受管运行文件；macOS 用户能通过一键安装入口完成全局 Hook 安装。
  - Scope: `hooks/project_injector.py`, `hooks/user_prompt_submit.py`, `hooks/stop_judge.py`, `hooks/permission_policy.py`, `install/macos/*`, `tests/*`, `README.md`, `.project_wiki/PROJECT_SPEC.md`
  - Acceptance: Hook 运行时只刷新 `hooks/*.py`、`.codex/hooks.json` 和静态 `.project_wiki` 模板/说明文件；不覆盖 `PROJECT_SPEC.md`、JUDGE、latest_context、judge_latest、loop_state、guard_log、COMPLETION_REPORT；目标项目写入本地 manifest 用于后续升级；macOS 安装器自动识别仓库路径和 Codex 配置目录，写入用户级 `hooks.json`，不要求或保存 secret；测试覆盖运行时升级、PROJECT_SPEC 保留、安装器生成配置和幂等安装。
  - Notes: 保持轻量；不做复杂包管理器、后台服务、外层调度器或自动远程更新。

- [x] TASK-010: 新增使用者视角体验测评 Hook
  - Goal: 在当前完成流程宣告完成后、最终完成报告前，加入真实使用者视角的体验测评闭环，并把有效发现转成受控任务合同更新。
  - Scope: `hooks/*.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`, `.project_wiki/COMPLETION_REPORT_TEMPLATE.md`
  - Acceptance: Stop Hook 的 `done` 不再直接等于最终结束，而是先触发体验测评 Hook；体验测评 Hook 能尽可能真实地使用项目成果并输出详细测评；测评结果按目标用户、项目目标、验收标准和价值过滤；有效发现进入 `spec_update_required` 或等价受控 Spec Steward 流程并更新 Development Plan；无明显问题或高价值改进时才允许生成最终完成报告；测试覆盖有问题继续开发、无问题最终完成、低价值/主观/非目标场景建议被过滤、循环次数或反复测评的 fail-safe。
  - Notes: 保持轻量；不引入多 Agent 平台、RAG、图数据库、外层调度器、复杂流程编排或无限打磨机制。

- [x] TASK-011: 实现自动任务合同更新确认流
  - Goal: 当用户提出合同修改建议或确认 Codex 已总结的合同变化时，SpecPilot 自动进入受控 Spec Steward / onboarding / spec update 流程，避免要求用户手动编辑任务书文件。
  - Scope: `hooks/*.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`, `.project_wiki/PROJECT_SPEC.md`
  - Acceptance: 用户提出修改建议时，Hook/Spec Steward 能识别并启动受控任务合同更新；信息足够时直接写入完整更新后的 `PROJECT_SPEC.md` 并更新 Development Plan；信息不足时只问最少澄清问题；用户对已总结变化回复 `同意` 或等价确认时，Spec Steward 可立即 apply；相关 INJECTION、模板和 README 与该流程保持一致；测试覆盖直接建议、信息不足、`同意` 确认、拒绝/含糊确认、Development Plan 更新、普通 Worker 不得绕过受控流程、GitHub policy 默认 local-only 且不保存 secret。
  - Notes: 保持受控写入边界；不引入 RAG、多 Agent 平台、图数据库、外层调度器、云默认或 credential 存储。

- [x] TASK-012: 支持开发卡点自解和阶段目标重规划
  - Goal: 让 Hook 在开发中途遇到实现、测试、依赖、规划或阶段推进问题时，优先基于已有 Wiki 事实和任务合同推动 Codex 自行研究、修复、验证或调整计划，而不是默认把问题交给用户。
  - Scope: `hooks/stop_judge.py`, `hooks/spec_steward.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`, `.project_wiki/PROJECT_SPEC.md`
  - Acceptance: Stop Hook 提示和测试明确要求普通工程卡点优先走 `continue` / `revise` 并给出可执行 next_action；无直接解法时先重审阶段目标或 Development Plan 假设，必要时进入受控 `spec_update_required`；只有真实用户取舍、secret、外部环境、保护范围、目标范围确认或不可消除歧义才进入 `human_review`。
  - Notes: 保持轻量 AI 控制；不引入外层调度器、多 Agent、RAG、复杂流程编排或无限研究机制。

- [x] TASK-013: 支持长任务书紧凑导入和关键章节保真
  - Goal: 避免长 `PROJECT_SPEC.md` / 长任务书因为提示篇幅限制导致目标、范围、后段任务、验收标准或提交要求丢失。
  - Scope: `hooks/stop_judge.py`, `hooks/spec_steward.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`, `.project_wiki/PROJECT_SPEC.md`
  - Acceptance: Stop Hook 和 Spec Steward 构造提示时使用关键章节抽取与头尾保真，而不是简单全文截断；紧凑上下文必须保留 Project Goal、User Requirements、Non-Goals、Allowed Scope、Protected Scope、Development Plan、Acceptance Criteria、Stop Conditions、GitHub policy 和 Submission Requirements；测试覆盖长背景、长 Development Plan、后段任务和提交要求仍能进入判断提示。
  - Notes: 不要求用户手动缩短或拆分任务书；不引入复杂文档管理、RAG 或外层调度器。

- [x] TASK-014: Active Mission Snapshot / current goal anchor
  - Goal: 在 `PROJECT_SPEC.md` 和受控模板中建立当前目标锚点，让长任务书始终明确当前阶段、当前任务、当前验收重点和下一步允许动作。
  - Scope: `hooks/spec_steward.py`, `hooks/stop_judge.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`, `.project_wiki/PROJECT_SPEC.md`
  - Acceptance: 任务书包含 Active Mission Snapshot；Stop Hook / Spec Steward 提示优先读取该锚点；历史阶段不会覆盖当前目标；测试覆盖长历史下仍正确识别当前 TASK。
  - Notes: TASK-001 through TASK-013 保持历史证据，不作为当前目标。

- [x] TASK-015: Goal drift detection
  - Goal: 检测当前行动、Stop Judge 判断、Development Plan、完成声明或历史摘要是否偏离 Active Mission Snapshot。
  - Scope: `hooks/stop_judge.py`, `hooks/spec_steward.py`, `tests/*`, `README.md`
  - Acceptance: 当 Hook 发现当前 next_action 指向过时任务、已完成历史阶段或与 Active Mission Snapshot 冲突时，进入 `revise`、受控 `spec_update_required` 或证据核对流程；测试覆盖历史完成任务误当当前目标、release label 冲突和当前阶段不一致。
  - Notes: 不引入复杂规则引擎；以轻量结构检查和 AI 判断结合。

- [x] TASK-016: PROJECT_SPEC section patch update
  - Goal: 支持按章节 patch 更新长 `PROJECT_SPEC.md`，避免全文件重写丢失后段任务、提交要求或历史约束。
  - Scope: `hooks/spec_steward.py`, `tests/*`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`, `README.md`
  - Acceptance: Spec Steward 能只替换或更新指定 heading section；保留必需 heading、后段 Development Plan、GitHub policy、Stop Conditions 和 Submission Requirements；测试覆盖长任务书 section patch、缺失 heading、重复 heading 和保真失败。
  - Notes: 输出完整任务书仍可用于受控流程，但内部更新策略应支持 section patch。

- [x] TASK-017: Task evidence reconciliation
  - Goal: 建立任务完成声明与真实证据之间的核对机制，避免状态文件或总结声称完成但测试、文件或验证证据不支持。
  - Scope: `hooks/stop_judge.py`, `hooks/spec_steward.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`
  - Acceptance: Hook 在宣告 TASK 完成、阶段完成、体验测评通过或 release 前，必须核对相关 evidence；证据不足时不能进入最终完成或发布；测试覆盖 code-ready、environment-blocked、real-world verified 和证据缺失。
  - Notes: 不做复杂资产盘点；只核对任务书要求的直接证据。

- [x] TASK-018: Controlled Spec Steward write channel
  - Goal: 收敛所有任务合同写入入口，确保 `PROJECT_SPEC.md`、Active Mission Snapshot、Development Plan、GitHub policy 和相关模板只能通过受控 Spec Steward 通道更新。
  - Scope: `hooks/spec_steward.py`, `hooks/user_prompt_submit.py`, `hooks/stop_judge.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`
  - Acceptance: 受控写入必须记录 decision、reason、update summary、目标 sections 和 evidence；普通 Worker 和非受控路径不得改写任务合同；测试覆盖直接建议、确认 apply、拒绝、含糊确认、受保护 scope、secret 拒绝和 section patch 写入。
  - Notes: 不请求、不保存、不暴露 secrets。

- [x] TASK-019: Phase closure and next phase contract draft
  - Goal: 阶段完成时生成阶段关闭证据和下一阶段合同草案，把历史阶段归档为 evidence，而不是让历史摘要污染当前目标。
  - Scope: `hooks/stop_judge.py`, `hooks/spec_steward.py`, `tests/*`, `README.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`
  - Acceptance: 阶段关闭必须包含完成 TASK、验证证据、未解决事项、体验测评状态和 GitHub 状态；下一阶段草案必须进入受控 Spec Steward 流程，未经确认不得写入正式合同；测试覆盖阶段关闭、草案生成、用户确认和用户拒绝。
  - Notes: 不新增外层调度器或多 Agent 平台。

- [x] TASK-020: Narrowed human_review taxonomy
  - Goal: 收窄 `human_review` 触发条件，把普通工程失败、测试失败、计划不顺、状态不一致优先转为自解、revise、证据核对或合同修复。
  - Scope: `hooks/stop_judge.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`
  - Acceptance: Stop Hook 分类明确区分 self-fixable、spec-repair-needed、evidence-needed、external-action-needed、user-decision-needed、secret-needed、protected-scope-needed；测试覆盖普通卡点不直接升级用户，真实用户取舍和 secret 场景才进入 `human_review`。
  - Notes: 保持轻量 AI 控制，不做复杂权限平台。

- [x] TASK-021: Status enum normalization
  - Goal: 规范 Hook、状态文件、完成报告和发布流程中的状态枚举，避免 `done`、`complete`、`finished`、`code-ready`、`real-world verified`、`environment-blocked` 混用。
  - Scope: `hooks/*.py`, `tests/*`, `README.md`, `.project_wiki/COMPLETION_REPORT_TEMPLATE.md`, `.project_wiki/INJECTION.md`
  - Acceptance: 状态枚举有清晰定义和转换规则；Stop Judge 决策状态与验证状态分离；发布前必须达到任务书要求的验证状态；测试覆盖状态解析、旧状态兼容、非法状态 fail-safe。
  - Notes: 不因状态重命名破坏已有监督项目的兼容读取。

- [x] TASK-022: Context budget and phase-history archive strategy
  - Goal: 为长任务书、长历史和多阶段开发建立上下文预算与阶段历史归档策略，确保当前目标和后段要求不会被历史挤掉。
  - Scope: `hooks/stop_judge.py`, `hooks/spec_steward.py`, `tests/*`, `README.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`
  - Acceptance: 提示构造必须保留 Active Mission Snapshot、current Phase、current TASK、Acceptance Criteria、Stop Conditions、GitHub policy、Submission Requirements 和后段 Development Plan；历史阶段以压缩 evidence/archive 进入；测试覆盖超长历史、后段提交要求、发布策略和当前任务仍被保留。
  - Notes: 不要求用户手动拆分任务书，不引入 RAG 或复杂文档平台。

- [x] TASK-023: novelcreatepilot regression validation
  - Goal: 用 novelcreatepilot 或等价真实受监督项目验证本阶段能力在真实长任务书和历史状态中有效。
  - Scope: `tests/*`, `README.md`, `.project_wiki/PROGRESS.md` 或受控验证记录，必要时只读或临时测试目标项目
  - Acceptance: 验证 Active Mission Snapshot 优先级、目标漂移检测、证据核对、section patch、受控写入、状态枚举、上下文预算和 release 前证据要求；记录 direct evidence；明确 code-ready、environment-blocked 或 real-world verified。
  - Notes: 不污染目标项目任务合同；如需要修改外部受监督项目合同，必须走该项目受控 Spec Steward 流程。

- [x] TASK-024: Protected maintenance authorization lease
  - Goal: 解决用户明确授权维护受保护 Hook 文件时仍被 PreToolUse 死锁的问题。
  - Scope: `hooks/maintenance_authorization.py`, `hooks/user_prompt_submit.py`, `hooks/pre_tool_guard.py`, `hooks/permission_policy.py`, `tests/*`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`, `README.md`
  - Acceptance: 用户对精确受保护维护目标回复 `同意` / `允许` / `可以` 后，UserPromptSubmit 生成短时一次性维护租约；PreToolUse 只允许匹配租约的维护文件写入，消费后不可复用；混入业务文件、PROJECT_SPEC、判断日志、循环状态或 secret 时继续拒绝。
  - Notes: Evidence: `test_protected_maintenance_authorization_lease` covers lease creation, one-shot consumption, non-reuse, mixed-file denial, missing-target denial, protected PROJECT_SPEC denial, rejection and ambiguous authorization denial.

- [x] TASK-025: Spec Steward runtime blocked recovery path
  - Goal: 当 Spec Steward 自身运行时调用失败时，不要求用户手动关闭 Hook 或手动改保护文件，而是进入受控维护修复流。
  - Scope: `hooks/spec_steward.py`, `hooks/maintenance_authorization.py`, `hooks/stop_judge.py`, `tests/*`, docs/templates
  - Acceptance: Spec Steward runtime failure returns `maintenance_authorization_required` with exact maintenance targets; Stop Hook records a bounded protected-maintenance next action; maintenance authorization still requires explicit user approval and a short-lived lease.
  - Notes: Evidence: `test_spec_steward_controlled_update_flow` covers runtime failure returning protected maintenance authorization targets.

- [x] TASK-026: Active Snapshot / GitHub policy reconciliation
  - Goal: 当 Active Mission Snapshot 或 Submission Requirements 已明确 GitHub 发布/同步授权，但正式 GitHub Sync Policy 仍 local-only 或不完整时，进入受控 policy reconciliation，而不是普通 human_review 死停或直接远端操作。
  - Scope: `hooks/stop_judge.py`, `hooks/mission_snapshot.py`, `tests/*`, docs/templates
  - Acceptance: Stop Hook can detect snapshot/local-only conflict and invoke controlled Spec Steward apply; missing/incomplete policy, unavailable credentials, and human-confirmation policy remain fail-safe.
  - Notes: Evidence: `test_stop_github_sync_policy_gate` covers snapshot/local-only policy reconciliation, missing policy, incomplete policy, unavailable credentials, human-confirmation blocking, and allowed auto push.

- [x] TASK-027: Protected maintenance and policy repair validation
  - Goal: 验证 TASK-024 through TASK-026 的受控维护、PreToolUse 租约消费和 GitHub policy repair 行为在本地闭环中可用。
  - Scope: `tests/*`, `.project_wiki/PROJECT_SPEC.md`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`, `README.md`
  - Acceptance: 本地 smoke tests cover protected maintenance lease lifecycle, Spec Steward maintenance authorization, and GitHub policy reconciliation without storing secrets or enabling remote operations by default.
  - Notes: Status: local validation complete; no GitHub release required unless explicitly requested.

- [x] TASK-028: Hook context de-duplication
  - Goal: 去掉 UserPromptSubmit 注入内容里的重复规则块，避免动态上下文和基础 INJECTION 重复消耗上下文窗口。
  - Scope: `hooks/user_prompt_submit.py`, `tests/*`, `.project_wiki/PROJECT_SPEC.md`, `README.md` as needed
  - Acceptance: 当动态 Active Mission Snapshot 已注入时，基础 `Active Mission Snapshot Rule` 不再重复进入 additionalContext；动态 `Goal Change Rule` 已注入时，基础 `Goal Change Rule` 不再重复进入 additionalContext；PROJECT_SPEC 只保留一个 canonical Active Mission Snapshot heading 或将第二份改为非 canonical evidence heading；测试覆盖去重后仍保留当前目标锚点、Goal Change Rule、Latest Judge Context 和 start-work/onboarding 规则。
  - Notes: Evidence: `python3 tests/smoke_test.py` 155/155 passed; UserPromptSubmit output contains one dynamic `Goal Change Rule`, omits base `Active Mission Snapshot Rule` when a dynamic snapshot exists, and PROJECT_SPEC has one canonical `## Active Mission Snapshot` heading.

- [x] TASK-029: 自动阶段过渡治理与 Worker 连续推进闭环
  - Goal: 完成 v3.0 automatic phase-transition governance，使 Stop Hook、Spec Steward 和 Worker 在完整 PROJECT_SPEC 已存在时，能自动处理普通阶段过渡、下一任务激活、任务状态对账、体验测评后续任务和 Development Plan 衔接，不再反复要求用户确认。
  - Scope: `hooks/stop_judge.py`, `hooks/spec_steward.py`, `hooks/task_intent.py`, `hooks/user_prompt_submit.py`, `hooks/permission_policy.py`, `tests/*`, `README.md`, `.project_wiki/INJECTION.md`, `.project_wiki/PROJECT_SPEC_TEMPLATE.md`, `.project_wiki/PROJECT_SPEC.md`
  - Acceptance: Stop Hook 在 Spec Steward 成功应用受控合同更新后返回 `decision:block`、`VERDICT: continue`、`AUTO_CONTINUE: enabled`，Worker 会自动从更新后的 Active Mission Snapshot / Development Plan 继续；普通对话 conversation mode 会写入轻量 pass，避免沉默或误触发任务推进；Spec Steward `needs_user_confirmation` 或不可解析失败会转为自动 `revise`，要求 Worker 继续补齐证据或收窄 patch，而不是直接问用户；Spec Steward 现在拒绝会丢掉已有 TASK id 的 section patch；无新增 RAG、多 Agent 平台、图数据库、外层调度器、云默认或复杂流程编排。
  - Evidence: TASK-029 已完成本地实现和验证。验证通过：`python3 -m py_compile hooks/*.py tests/smoke_test.py` pass；`python3 tests/smoke_test.py` pass 167/167 after Worker-flow auto-continue and task-id preservation changes; PROJECT_SPEC task-id preservation check confirms TASK-001 through TASK-029 all present.
  - Notes: 当前无下一任务授权；release target 仍为 local validation only，除非用户在当前回合明确要求且 GitHub Sync Policy 已对齐，否则不执行 GitHub push/tag/release。
- [ ] TASK-030: Execute current-turn v3.0 GitHub release
  - Goal: Complete the user-authorized v3.0 publication after TASK-029 local validation.
  - Scope: local validation commands, git status/diff review, git commit, `origin/main` push, annotated tag `v3.0`, GitHub release `v3.0`, README or completion notes only if needed for release accuracy.
  - Acceptance: Confirm repository is `yunhaichu/Codex-SpecPilot`; confirm local GitHub CLI is already authenticated as `yunhaichu`; run required validation; commit validated v3.0 changes without reverting unrelated user changes; push `origin/main`; create annotated tag `v3.0`; create GitHub release `v3.0`; report commit, tag, release URL, and validation results.
  - Notes: This is a current-turn explicit release authorization only. Do not request, write, print, or store secrets. Do not introduce RAG, multi-agent platforms, graph memory, external schedulers, cloud defaults, or complex workflow platforms. Preserve all existing TASK-001 through TASK-029 history and do not truncate the Development Plan.

## 9. Acceptance Criteria
- 用户只输入一次 `开始工作` 后，Hook 能持续推动 Codex 继续开发或纠偏。
- Stop Hook 能基于 AI 输出可靠处理 `continue | revise | done | human_review`。
- Stop Hook 能在用户修改目标、范围、优先级或验收标准时处理 `spec_update_required`，并暂停自动继续。
- 用户提出任务合同修改建议时，SpecPilot 必须直接进入受控 Spec Steward / onboarding / spec update 流程，而不是要求用户手动编辑 `PROJECT_SPEC.md` 或任务书相关文件。
- 修改建议信息足够时，受控流程必须写入完整更新后的 `PROJECT_SPEC.md` 并更新 Development Plan。
- 修改建议信息不足时，受控流程只提出最少量澄清问题。
- Codex 已总结拟议合同变化且用户回复 `同意` 或等价确认时，Spec Steward 可以立即应用该已确认更新。
- 自动任务合同更新流程必须能使相关 INJECTION、PROJECT_SPEC_TEMPLATE、README 等 instruction/template 文件在后续实现中保持一致。
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
- 开发中途遇到普通实现、测试、依赖、规划或阶段推进问题时，Stop Hook 必须优先给出基于已有事实的自解、研究、修复或验证 next_action，而不是默认进入 `human_review`。
- 如果没有直接解决路径，Stop Hook 必须先推动 Codex 重审当前阶段目标或 Development Plan 假设，并在需要时进入受控 `spec_update_required` / 计划更新流程。
- 只有真实用户取舍、凭据/secret、外部环境动作、受保护范围授权、目标范围确认或不可消除歧义，才允许把开发卡点升级为 `human_review`。
- 长任务书必须能被 Stop Hook 和 Spec Steward 以紧凑或分段保真方式导入，且后段 Development Plan 任务、验收标准、停止条件、GitHub 策略和提交要求不能因为简单截断丢失。
- `PROJECT_SPEC.md` 必须包含 Active Mission Snapshot / current goal anchor，并在长任务书中作为当前目标的最高优先级来源。
- Hook、Spec Steward 和 Stop Judge 必须按 Active Mission Snapshot -> current Phase -> current TASK -> acceptance criteria -> historical summaries 的优先级读取和判断任务合同。
- 已完成历史阶段必须作为 evidence/background 处理，不能覆盖当前目标或导致 Hook 回到旧任务。
- Goal drift detection 必须能发现当前行动、判断、状态或完成声明与 Active Mission Snapshot 冲突，并触发 revise、证据核对或受控合同修复。
- `PROJECT_SPEC.md` 长文件更新必须支持 section patch 或等价章节保真策略，不能因为全文件重写丢失后段任务、GitHub 策略、停止条件或提交要求。
- 任务完成、阶段关闭、体验测评通过和 release 前必须核对直接 evidence；证据不足时不得声称 real-world verified 或发布完成。
- 任务合同写入必须通过受控 Spec Steward write channel，记录 decision、reason、update summary、目标 sections 和 evidence；普通 Worker 不得绕过。
- 阶段关闭必须生成 closure evidence 和下一阶段合同草案；草案未经确认不得写入正式任务合同。
- `human_review` taxonomy 必须收窄，普通工程卡点和状态不一致优先自解、revise、证据核对或合同修复。
- Hook、状态文件、完成报告和发布流程中的状态枚举必须规范化，并区分决策状态、验证状态和 GitHub sync 状态。
- 上下文预算和阶段历史归档策略必须保留当前目标、后段任务、验收标准、停止条件、GitHub 策略和提交要求。
- novelcreatepilot 或等价真实受监督项目回归验证必须覆盖本阶段目标锚定、证据闭环和长任务书策略。
- 本阶段验证通过后默认停留在本地验证完成状态；只有用户明确要求发布时，才 commit、push 到 GitHub、创建 tag 并 release，且 `vv2.6` 仅作为 `v2.6` 笔误处理。
- PROJECT_SPEC 必须包含 Active Mission Snapshot，且 Hook 判断上下文必须优先使用该当前目标锚点。
- 长任务书中的历史阶段、已完成任务和未来建议不得覆盖当前目标、当前阶段和当前任务。
- Spec Steward 必须支持受控 section patch / task patch / phase summary patch，并避免因完整任务书过长导致合同更新悬挂或截断。
- 本地报告、completion report、latest context 和 judge state 可作为任务状态对账证据；证据足够时应进入受控任务状态更新。
- 同一产品主线内的普通阶段推进应生成下一阶段合同草案并进入受控更新，不得默认交给用户决定技术任务顺序。
- human_review 必须按分类收窄，只有真实用户取舍、secret/credential、外部权限、受保护范围授权或不可消除歧义才能问用户。
- 任务、报告、Hook 和 Spec Steward 状态必须支持语义归一化；等价状态不能阻塞合同更新。
- novelcreatepilot 暴露出的长任务书和阶段推进问题必须有回归覆盖。
- 用户明确授权临时维护受保护 Hook 文件时，SpecPilot 必须能生成一次性短时维护租约，并由 PreToolUse 精确消费。
- PreToolUse 不得因为普通聊天授权而全局关闭；租约必须限定文件、次数、时效和原因。
- Spec Steward runtime blocked 时必须能提出受控维护修复流，而不是要求用户手动关闭 hook。
- Active Snapshot / Submission Requirements 与正式 GitHub policy 冲突时，Stop Hook 必须触发受控 policy reconciliation；只有凭据、外部环境或真实用户取舍缺失时才进入 human_review。
- 判断体系文件不能被普通 Codex Worker 修改。
- Hook 保持轻量，不引入复杂规则引擎、RAG、多 Agent、外层调度器、完整 GitHub 平台、CI 管理器、release platform、issue tracker、复杂流程编排或无限打磨机制。
- `codex exec` 使用当前默认模型，不写死模型、profile 或 endpoint。
- macOS 和 Windows 的路径与启动方式都有测试覆盖。
- v3.0 自动化阶段过渡治理必须证明：TASK 完成后，若 `PROJECT_SPEC.md` 和 Development Plan 已明确下一步，Stop Hook / Spec Steward 能自动对齐当前阶段、当前 TASK、Development Plan 和 latest context，并继续推进，不再询问用户是否授权普通下一阶段。
- 必须覆盖任务状态对账：当 Active Mission Snapshot、Development Plan、历史完成声明、完成报告、测试证据或 latest context 不一致时，Hook 优先执行证据核对和受控合同修复；只有真实不可消除歧义才进入 `human_review`。
- 必须覆盖体验测评后续任务：完成前体验测评若发现明确高价值改进，应进入受控 Spec Steward section patch 并继续开发；若无明显问题或值得继续开发的改进点，才允许进入最终完成报告。
- 必须覆盖普通对话轻量反馈：普通问答和非任务型交流应被记录为轻量反馈或轻量状态，不得误判为开发任务、合同变更或完成阻塞。
- 必须保留 onboarding 例外：只有尚未形成完整 `PROJECT_SPEC.md` 且需求信息不足时，才允许反复向用户确认目标、范围、验收标准或 GitHub 同步策略。
- v3.0 修改必须使用 section patch 或等价窄范围合同更新策略验证长任务书保真，确认 Active Mission Snapshot、Development Plan 后段任务、Submission Requirements、GitHub Sync Policy 和原始用户目标未被丢失。

## 10. Stop Conditions
- AI 判断需求不清或需要用户决策时，进入 `human_review`；但普通工程卡点必须先尝试基于任务书、项目 Wiki、阶段目标和已有验证结果自解或重审阶段目标，不能直接把问题丢给用户。
- 用户修改建议涉及任务合同但信息不足时，进入受控 Spec Steward / onboarding / spec update 澄清流程，只问最少必要问题。
- 用户对拟议合同变化的确认含糊、冲突或无法判断是否等价于 `同意` 时，不得直接写入，必须请求最少确认或进入 `human_review`。
- 任务合同更新请求与当前受保护范围、Non-Goals 或 GitHub/secret 安全政策冲突时，进入 `human_review` 或拒绝该变更，不得静默写入。
- Active Mission Snapshot 缺失、过时或与当前 Development Plan / user confirmation 冲突时，必须进入受控合同修复或 `human_review`，不得基于旧历史继续推进。
- 当前 next_action、Stop Judge 输出、完成声明或状态文件明显指向已完成历史阶段而非当前阶段时，必须触发 goal drift detection 并 revise 或进入受控修复。
- 任务完成、阶段完成、体验测评通过或 release 前缺少直接 evidence 时，不得声称完成或发布；必须继续验证、标记 environment-blocked 或进入 `human_review`。
- Section patch 更新无法保留必需 heading、后段 Development Plan、GitHub policy、Stop Conditions 或 Submission Requirements 时，不得写入；必须进入受控修复或 `human_review`。
- 状态枚举无法识别、互相冲突或可能导致错误推进时，必须 fail safe 到 `revise`、证据核对或 `human_review`。
- 上下文预算不足以保留 Active Mission Snapshot、current TASK、验收标准、停止条件、GitHub 策略和提交要求时，不能假装判断完整；必须使用紧凑/分段保真修复或进入 `human_review`。
- `codex exec` 不可用或输出无法解析时，不假装监督成功。
- 连续自动推进达到 loop 限制仍未完成时，进入 `human_review`。
- 下一步动作要求修改判断体系核心文件且当前不是 SpecPilot 自开发任务时，进入 `human_review`。
- 任务书缺失或不完整且 onboarding 信息不足时，延期开发并继续需求澄清。
- GitHub 同步策略缺失、含糊或与当前动作冲突时，保持 local-only 或进入 `human_review`。
- 如果用户或 Active Mission Snapshot 已明确要求 GitHub 发布，但正式 GitHub policy 仍为 local-only 或不完整，应进入 `spec_update_required` / policy reconciliation，而不是普通 auto-continue 或无解释 human_review。
- 维护租约缺失、过期、目标文件不匹配、次数耗尽或授权语义不明确时，PreToolUse 必须继续拦截受保护文件写入。
- GitHub 凭据不可用、认证失败、远端不可访问或 GitHub 操作结果无法确认时，不得假装成功；应进入 `human_review` 或按策略降级为 local-only / sync environment-blocked。
- 自动 push、tag、release 或仓库创建未被 PROJECT_SPEC 明确允许时，必须请求人工确认或进入 `human_review`。
- 如果进入发布流程，发布前若验证失败、证据不足、工作树状态不清、远端不可确认或 release 操作失败，不得声称发布完成。
- 任何流程要求在项目文件中写入 API key、token、private key、密码或 credential secret 时，拒绝该写入并进入 `human_review`。
- Hook 运行时升级检测到本地受管文件有无法安全合并的用户修改时，进入 `human_review`，不得覆盖用户内容。
- 体验测评 Hook 无法真实使用或验证项目成果时，不得声称最终完成；应标记为 environment-blocked、code-ready 或进入 `human_review`。
- 体验测评发现的问题是否应转为新需求存在歧义、与任务合同冲突或需要用户取舍时，进入 `spec_update_required` 或 `human_review`。
- 体验测评发现只包含低价值、纯主观、非目标用户场景或与项目目标无关的建议时，不得转成新需求，应允许最终完成报告继续。
- 体验测评循环反复提出低价值、主观、非目标场景或无法收敛的建议时，应过滤这些建议，并在达到循环限制时进入 `human_review`，不得无限打磨。
- 长任务书导入或紧凑化无法保留必需章节、后段任务或提交要求时，不能假装判断完整；应进入受控修复或 `human_review`，不得基于残缺任务书宣告完成。
- 不得因为 TASK 完成、阶段切换、下一任务选择、任务状态对账、体验测评后续任务或 Development Plan 衔接本身而停止等待用户确认；完整 `PROJECT_SPEC.md` 已存在且证据足够时，必须自动推进或进入受控合同修复。
- 只有以下情况允许停止并请求用户：尚未形成完整 `PROJECT_SPEC.md` 的 onboarding 需求澄清；真实需要用户取舍；需要 secret 或外部账号动作；需要受保护范围授权；GitHub 发布/远端同步未获当前明确授权；存在无法通过 PROJECT_SPEC、wiki evidence、latest context 和代码事实消除的目标歧义。
- 普通对话不得触发开发停止条件或新任务启动；Hook 应写入轻量反馈后保持当前任务合同不变，除非用户明确提出合同变更、开发请求、发布请求或受保护授权。

## GitHub Sync Policy
- Default policy remains local-only for ordinary work and future turns unless the user explicitly authorizes upload, sync, push, tag, or release again.
- For this current turn only, the user explicitly authorizes completing the v3.0 GitHub release after validation.
- Authorized GitHub account and repository: use the already-authenticated local GitHub CLI account `yunhaichu` for repository `yunhaichu/Codex-SpecPilot`.
- Authorized current-turn release actions: commit the validated v3.0 changes, push `origin/main`, create annotated tag `v3.0`, and create GitHub release `v3.0`.
- This authorization is not a general cloud default, not a standing permission for future releases, and not permission to store or expose credentials.
- Do not request, write, print, or store any API key, token, private key, password, or credential secret. Use only the existing local authenticated GitHub CLI/session state.
- If validation fails, repository identity does not match `yunhaichu/Codex-SpecPilot`, the authenticated account is not `yunhaichu`, the working tree contains unrelated or unsafe changes, or release/tag state conflicts cannot be resolved locally without user choice, stop and report the concrete blocker instead of publishing.

## 11. Submission Requirements
- 受控 Spec Steward / onboarding / spec update 流程输出更新后的 `PROJECT_SPEC.md` 时，必须保留本文件的必需 heading，包括 `Project Mode`、`Project Goal`、`User Requirements`、`Non-Goals`、`Allowed Scope`、`Protected Scope`、`Active Mission Snapshot`、`Development Plan`、`Acceptance Criteria`、`Stop Conditions`、GitHub 相关策略内容和 `Submission Requirements`。
- 如果用户未明确要求上传或同步，GitHub 策略必须保持 local-only/default safety，不得新增 GitHub 上传、推送、tag、release 或云默认。
- 本阶段当前提交要求是本地验证完成并保留发布前证据。若用户在当前回合明确要求发布，必须先通过受控 Spec Steward 对齐 GitHub Sync Policy、发布目标、tag/release 名称和自动操作权限；上下文中的 `vv2.6` 仅在该发布流程中视为 `v2.6`。
- 若进入发布流程，发布前必须运行基础验证和 TASK-023 要求的 novelcreatepilot 或等价真实受监督项目回归验证，并记录 direct evidence。
- 若进入发布流程，必须确认工作树状态、commit 内容、tag 名称、远端 push 状态和 release 状态；凭据不可用或远端不可确认时必须标记 sync environment-blocked 或进入 `human_review`，不得声称发布成功。
- 更新任务合同时，只能编码用户已确认的变化；含糊、冲突或越过受保护范围的变化必须进入澄清或拒绝。
- 更新 Development Plan 时，必须让剩余工作清晰可执行；过时工作应在 Notes 中标明，而不是删除重要历史约束。
- 每次开发提交必须说明属于 code-ready、environment-blocked 还是 real-world verified。
- 涉及 GitHub 同步的提交或完成报告必须说明实际 GitHub 状态：local-only、sync skipped by policy、sync pending human confirmation、sync environment-blocked，或 sync verified with direct evidence。
- 涉及体验测评的提交或完成报告必须说明体验测评状态：not run、evaluation environment-blocked、issues found and converted to spec update、issues filtered as low-value/out-of-scope，或 no obvious user-facing issues found。
- 涉及 Active Mission Snapshot、目标漂移检测、证据核对、状态枚举或上下文预算的修改必须说明当前目标锚点是否被保留、历史阶段是否仅作为 evidence、后段任务和提交要求是否被验证保留。
- Phase closure 必须说明完成任务、直接证据、未解决事项、体验测评状态、GitHub 状态和下一阶段合同草案状态。
- 完成真实试跑前，不得声称无人值守 LLM supervisor 已完全跑通。
- 最终完成报告只能在最后一次体验测评找不到明显问题或值得继续开发的改进点后生成或更新。
- 修改后至少运行不触发无关状态污染的基础验证。
- 长任务书相关修改必须说明是否使用了紧凑/分段保真或 section patch，以及 Active Mission Snapshot、后段任务和提交要求是否被验证保留。
- 不得请求、写入或暴露 API key、token、private key、密码或其他 credential secret。
- 不得新增 RAG、多 Agent 平台、图数据库、外层调度器、云默认或复杂流程编排。
- 普通 Codex Worker 不得绕过受控流程改写 `PROJECT_SPEC.md`、Active Mission Snapshot、Development Plan、GitHub policy 或相关 SpecPilot instruction/template 文件。
- Protected maintenance lease 必须在完成报告或验证记录中说明授权来源、目标文件、消费状态、验证结果和是否自动失效。
- GitHub policy reconciliation 必须说明冲突来源、最终 policy 状态和是否执行任何远端动作。
- TASK-014 至 TASK-023 完成后必须说明 Active Mission Snapshot、section patch、证据对账、阶段合同草案、human_review 收窄、状态归一化和 novelcreatepilot 回归验证状态。
- 若用户明确要求发布新版本，发布前必须运行基础验证、提交本地变更、推送 GitHub、创建指定 tag，并发布 GitHub release；发布说明必须包含验证结果和体验测评状态。
- 涉及长任务书目标锚定的提交必须说明历史阶段是否已压缩为摘要，以及当前目标是否仍清晰。
- For the current-turn v3.0 release, the final report must include: validation commands and results, confirmed GitHub account `yunhaichu`, confirmed repository `yunhaichu/Codex-SpecPilot`, commit hash, pushed branch `origin/main`, annotated tag `v3.0`, GitHub release `v3.0` URL or identifier, and confirmation that no secret was requested, written, printed, or stored.
- If the release cannot be completed, report the exact blocker and the last safe completed step; do not fabricate publication status.
