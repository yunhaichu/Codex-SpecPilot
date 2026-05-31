# Project Specification Template

## 0. Project Mode
必须选择一个：
- `wikiguard_self_development`
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
- 必须生成 COMPLETION_REPORT.md。

## 9. Stop Conditions
以下情况必须停止并 human_review：
- 需求不清楚。
- 需要修改 PROJECT_SPEC.md。
- 需要修改规则、权限、Hook 或监督日志。
- 需要越过 Protected Scope。
- 连续 3 次自动 continue 仍未完成。

## 10. Submission Requirements
写清楚完成后要提交什么结果、运行什么测试、写什么报告。
