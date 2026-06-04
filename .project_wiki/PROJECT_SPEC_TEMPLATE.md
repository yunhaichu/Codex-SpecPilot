# Project Specification Template

## Active Mission Snapshot
写清楚当前开发阶段的目标锚点。长任务书必须优先保留本节。
- Current Goal:
- Current Phase:
- Current TASK Range:
- Current Acceptance Focus:
- Current Non-Goals:
- Current Release / GitHub Target:
- Context Priority: Active Mission Snapshot -> current phase -> current TASK -> acceptance criteria -> historical summaries/evidence.

## 0. Project Mode
必须选择一个：
- `specpilot_self_development`
- `supervised_project_development`
当前项目模式：

## 1. Project Goal
写清楚这个项目最终要实现什么。

## 2. Background
写清楚为什么要做这个项目、当前已有基础是什么。

## 3. User Requirements
逐条列出用户确认过的需求。

## 4. Non-Goals
写清楚明确不做什么。

## 5. Allowed Scope
写清楚 Codex Worker 允许修改哪些目录和文件。
如果没有明确写入 Allowed Scope，默认不允许修改。

## 6. Protected Scope
写清楚 Codex Worker 不允许修改哪些目录和文件。

## 7. Development Plan
每个任务必须使用以下格式：
- [ ] TASK-001: 任务标题
   - Goal:
   - Scope:
   - Acceptance:
   - Notes:
- [ ] TASK-002: 任务标题
   - Goal:
   - Scope:
   - Acceptance:
   - Notes:

## 8. Acceptance Criteria
所有任务完成必须满足：
- Development Plan 中所有任务均完成。
- 每项 User Requirement 都有对应实现或明确说明。
- 没有违反 Non-Goals。
- 没有修改 Protected Scope。
- 用户提出需求、范围、优先级、验收标准或 Development Plan 修改建议时，系统通过受控 Spec Steward / onboarding / spec update 流程更新任务书，不要求用户手动编辑。
- 如果用户对已总结的任务合同变化回复 `同意` 或等价确认，Spec Steward 可以直接应用该已确认更新。
- 如果用户拒绝已总结的任务合同变化，或确认语义含糊，Spec Steward 不得写入；完整任务书已存在时应优先从任务书、Wiki 事实、证据和当前目标自动收敛，只有项目创建初期需求/目标尚未确认时才反复向用户提问。
- 阶段过渡、下一阶段计划、任务状态对账、体验测评后续任务和 Development Plan 衔接必须自动进入受控 Spec Steward / spec update / Worker 流程，不得要求用户人工确认。
- Hook 必须对普通对话写入轻量反馈状态，且不得把普通问答误当成 Development Plan 任务启动。
- 开发遇到普通实现、测试、依赖或规划卡点时，必须先基于任务书和项目 Wiki 自行调查、修复、验证或重审阶段目标，不得默认把问题丢给用户。
- 如果没有直接解法，必须先判断当前阶段目标或 Development Plan 是否需要调整；需要改任务合同时，进入受控 `spec_update_required`。
- 长任务书必须优先保留 Active Mission Snapshot，并通过关键章节紧凑导入或头尾保真方式进入 Hook 判断，后段 Development Plan、GitHub 策略、停止条件、验收标准和提交要求不得因简单截断丢失。
- 历史摘要、已完成阶段或旧报告与 Active Mission Snapshot 冲突时，以当前目标锚点为准，并触发纠偏、证据对账或受控任务合同更新。
- 用户确认受保护维护时，系统必须创建短时一次性、目标文件限定的维护租约；不得要求用户手动关闭保护或手动编辑受保护文件。
- 维护租约不得覆盖 `PROJECT_SPEC.md`、判断日志、循环状态、secret，或夹带无关业务文件的 patch。
- 报告证据显示任务完成但 Development Plan 仍显示 pending 时，必须做任务证据对账或受控任务合同修复。
- 状态枚举必须归一化处理，等价状态不得导致任务完成证据和任务书状态冲突。
- 完成前必须经过使用者视角体验测评。
- 最后一次体验测评找不到明显问题或高价值改进后，才生成 COMPLETION_REPORT.md。

## 9. Stop Conditions
以下情况必须停止并 human_review：
- 项目创建初期需求、目标、范围或验收标准尚未确认，无法生成完整任务书。
- 普通卡点已基于任务书、Wiki 事实和阶段目标尝试自解或重审计划后，仍确实需要用户取舍。
- 需要修改规则、权限、Hook 或监督日志。
- 需要越过 Protected Scope。
- 需要受保护维护且用户尚未确认一次性维护租约。
- 连续 3 次自动 continue 仍未完成。

## GitHub Sync Policy
必须二选一：
- Mode: local-only.
  - No push, tag, release, repository creation, or remote GitHub operation.
- Mode: github-sync.
  - GitHub account: 说明使用哪个账号或 owner，不写入 secret。
  - Auth method: 说明使用的本地认证方式，不写入 token、key 或 secret 原文。
  - Credentials: 只记录可用/不可用状态或认证方式描述，不记录 secret。
  - Repository: owner/name，或说明允许创建的新仓库目标。
  - Repository creation policy: 必须使用已有仓库，或允许创建新仓库。
  - Visibility: public 或 private。
  - Marker nodes: 明确哪些开发节点需要 commit、push、tag、release 或其他 GitHub marker。
  - Allowed automatic operations: 明确哪些操作可自动执行，例如 commit、push、tag、release；未列出的操作必须 human confirmation。
  - 如果 Active Mission Snapshot 或提交要求已明确当前 GitHub 发布/同步授权，但本策略仍是 local-only 或不完整，必须先进入受控 `spec_update_required` 策略对齐。

## 10. Submission Requirements
写清楚完成后要提交什么结果、运行什么测试、写什么报告，以及体验测评状态：
- 任务合同更新必须说明是由受控 Spec Steward / onboarding / spec update 流程写入，还是因信息不足进入澄清。
- 不得要求用户手动编辑 `PROJECT_SPEC.md` 或任务书相关文件。
- 受保护维护必须说明授权来源、目标文件、租约消费状态、验证结果和是否自动失效。
- 长任务书相关项目必须说明关键章节、后段任务和提交要求是否被 Hook 判断保留。
- not run
- evaluation environment-blocked
- issues found and converted to spec update
- issues filtered as low-value/out-of-scope
- no obvious user-facing issues found
