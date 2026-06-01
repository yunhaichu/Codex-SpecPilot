# Project Specification Template

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
- 如果用户拒绝已总结的任务合同变化，或确认语义含糊，Spec Steward 不得写入，只能请求最少确认或新的修改建议。
- 完成前必须经过使用者视角体验测评。
- 最后一次体验测评找不到明显问题或高价值改进后，才生成 COMPLETION_REPORT.md。

## 9. Stop Conditions
以下情况必须停止并 human_review：
- 需求不清楚。
- 任务合同修改建议不清楚，且受控 Spec Steward / onboarding / spec update 流程无法用最少问题澄清。
- 用户确认是否等价于 `同意` 无法判断。
- 需要修改规则、权限、Hook 或监督日志。
- 需要越过 Protected Scope。
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

## 10. Submission Requirements
写清楚完成后要提交什么结果、运行什么测试、写什么报告，以及体验测评状态：
- 任务合同更新必须说明是由受控 Spec Steward / onboarding / spec update 流程写入，还是因信息不足进入澄清。
- 不得要求用户手动编辑 `PROJECT_SPEC.md` 或任务书相关文件。
- not run
- evaluation environment-blocked
- issues found and converted to spec update
- issues filtered as low-value/out-of-scope
- no obvious user-facing issues found
