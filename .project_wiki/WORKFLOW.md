# Codex WikiGuard — WORKFLOW

## User Flow

1. 用户先通过与 AI 对话确认项目需求。
2. AI 按模板整理成 `.project_wiki/PROJECT_SPEC.md`。
3. 用户打开 Codex，在项目目录新建会话。
4. 用户只输入：**开始工作**。
5. Codex 读取 PROJECT_SPEC.md，按 Development Plan 执行。
6. Hook 监督 Codex：
   - UserPromptSubmit 注入任务书、最新状态、权限摘要。
   - PreToolUse 拦截危险动作和越权修改。
   - Stop 判断本轮是否通过、继续、纠偏、完成或需要人工确认。
7. 如果任务没完成，Stop 可以要求 Codex 继续。
8. 如果方向偏了，Stop 可以要求 Codex 纠偏。
9. 如果任务全部完成，Stop 记录 done，并要求 Codex 输出完成报告。
10. 用户最终查看完成报告和提交结果。

## Start Command

用户输入：

> 开始工作

Codex 必须：

- 读取 PROJECT_SPEC.md
- 读取 Development Plan
- 找到第一个未完成任务
- 只执行当前任务，不跳跃执行后续任务
- 遵守 Allowed Scope 和 Protected Scope
- 不修改监督系统文件

## End Condition

当 Acceptance Criteria 全部满足时，Codex 应：

- 停止继续开发
- 写出完成报告（COMPLETION_REPORT.md）
- 汇总修改文件
- 汇总测试结果
- 给出提交建议

## End Command

用户输入：

> 结束工作

Codex 应整理本轮完成结果，输出摘要，不继续自动 continue。
