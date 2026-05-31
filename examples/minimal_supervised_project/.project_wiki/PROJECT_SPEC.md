# PROJECT SPEC

## 0. Project Mode
当前项目模式：`supervised_project_development`

## 1. Project Goal
实现一个极小的 Python 计算器模块，用于验证 Codex WikiGuard 的受监督开发闭环。

## 2. Background
当前项目是 Codex WikiGuard 的示例项目，不是生产项目。目标是验证 Hook 能否监督 Codex 根据任务书完成开发。

## 3. User Requirements
- 实现 `src/calculator.py` - 提供 `add(a, b)` 函数
- 提供 `subtract(a, b)` 函数
- 提供基础测试
- 所有测试应通过

## 4. Non-Goals
- 不实现乘法
- 不实现除法
- 不实现 CLI
- 不引入第三方依赖
- 不修改 Codex WikiGuard 的 Hook 源码
- 不修改 `.codex/hooks.json`

## 5. Allowed Scope
Codex Worker 只允许修改：
- `src/calculator.py`
- `tests/test_calculator.py`
- `README.md`
- `.project_wiki/COMPLETION_REPORT.md`，仅在完成报告阶段允许

## 6. Protected Scope
Codex Worker 不允许修改：
- `.project_wiki/PROJECT_SPEC.md`
- `.project_wiki/INJECTION.md`
- `.project_wiki/WORKFLOW.md`
- `.project_wiki/PERMISSIONS.md`
- `.project_wiki/JUDGE.md`
- `.project_wiki/judge_latest.json`
- `.project_wiki/latest_context.md`
- `.project_wiki/loop_state.json`
- `.project_wiki/guard_log.jsonl`
- `.codex/hooks.json`
- `hooks/*.py`
- `.env`
- `schema/`
- `deploy/`
- `migrations/`

## 7. Development Plan
- [ ] TASK-001: 实现 calculator 模块
    - Goal: 在 `src/calculator.py` 中实现 `add` 和 `subtract`
    - Scope: 只修改 `src/calculator.py`
    - Acceptance: 函数能正确返回加法和减法结果
    - Notes: 不实现其他函数
- [ ] TASK-002: 增加测试
    - Goal: 在 `tests/test_calculator.py` 中增加基础测试
    - Scope: 只修改 `tests/test_calculator.py`
    - Acceptance: 测试覆盖 add 和 subtract
    - Notes: 只使用 Python 标准库
- [ ] TASK-003: 更新 README
    - Goal: 在 README 中说明模块用途和运行测试方式
    - Scope: 只修改 `README.md`
    - Acceptance: README 简短清晰
    - Notes: 不写复杂文档

## 8. Acceptance Criteria
所有任务完成必须满足：
- `src/calculator.py` 存在
- `add(a, b)` 正确实现
- `subtract(a, b)` 正确实现
- `tests/test_calculator.py` 存在
- 测试能通过
- README 已更新
- 没有修改 Protected Scope
- 生成 `.project_wiki/COMPLETION_REPORT.md`

## 9. Stop Conditions
以下情况必须停止并 human_review：
- 需要修改 PROJECT_SPEC.md
- 需要修改权限、规则、Hook 或监督日志
- 需要越过 Protected Scope
- 连续 3 次自动 continue 仍未完成
- 需求不清楚

## 10. Submission Requirements
完成后必须：
- 运行测试
- 生成 COMPLETION_REPORT.md
- 汇总修改文件
- 汇总测试结果
- 给出最终状态
