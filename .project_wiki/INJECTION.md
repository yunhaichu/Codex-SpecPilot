# Codex WikiGuard — INJECTION

## Current Task
- 暂无。

## Hard Rules
- 禁止扩大任务范围。
- 禁止无授权重构核心架构。
- 禁止修改 .env、secrets、credentials、密钥、部署脚本、数据库 schema、migration，除非用户明确要求。
- 禁止删除文件、清空目录、reset 仓库。
- 禁止只写说明不改代码后声称完成。
- 每轮必须说明实际修改了哪些文件、做了什么验证。

## Start Work Rule
当用户输入"开始工作"时，Codex 必须：
1. 读取 PROJECT_SPEC.md。
2. 按 Development Plan 找到第一个未完成任务（[ ] 标记）。
3. 只执行当前任务，不跳跃执行后续任务。
4. 每轮结束时说明：
    - 本轮处理了哪个 TASK
    - 修改了哪些文件
    - 做了什么验证
    - 下一步是什么
5. 不允许修改 PROJECT_SPEC.md、RULES.md、DECISIONS.md、REJECTED.md、PERMISSIONS.md。
6. 不允许修改 JUDGE.md、latest_context.md、judge_latest.json、loop_state.json、guard_log.jsonl。
7. 不允许修改 WORKFLOW.md、COMPLETION_REPORT_TEMPLATE.md。
8. 不允许修改 .codex/hooks.json 或 hooks/*.py，除非项目模式是 wikiguard_self_development。

## End Work Rule
当所有任务完成且 Acceptance Criteria 满足时，Codex 必须：
1. 停止继续开发。
2. 更新或生成 COMPLETION_REPORT.md。
3. 输出最终完成摘要。
4. 不再请求自动 continue。
当用户输入"结束工作"时，Codex 应整理本轮完成结果并输出摘要，不继续自动 continue。

## Permission Summary (Codex WikiGuard)
Codex Worker **MUST NOT** modify:
- .project_wiki/PROJECT_SPEC.md, RULES.md, DECISIONS.md, REJECTED.md, PERMISSIONS.md
- .project_wiki/JUDGE.md, latest_context.md, judge_latest.json, loop_state.json, guard_log.jsonl
- .project_wiki/WORKFLOW.md, COMPLETION_REPORT_TEMPLATE.md
- .codex/hooks.json, hooks/*.py (除非 project mode 是 wikiguard_self_development 且用户明确要求)
- .env, secrets, keys, deploy/, schema/, migration/, migrations/
Only modify files within Allowed Scope in PROJECT_SPEC.md.

## Latest Judge
- VERDICT: human_review
- NEXT_ACTION: wait for user confirmation
- AUTO_CONTINUE: disabled

## Local Model Mode
- Backend model: 使用 Codex 默认模型（codex exec，不传 -m）。
- Use short, explicit instructions.
- Prefer deterministic rules over model judgment.
- Do not rely on hidden reasoning or implicit context.

## Real Workflow
1. 用户先通过与 AI 对话确认项目需求。
2. AI 按模板整理成 PROJECT_SPEC.md。
3. 用户打开 Codex，在项目目录输入"开始工作"。
4. Codex 根据 PROJECT_SPEC.md 自动开发。
5. Hook 使用当前 Codex 默认模型监督 Codex。
6. 开发期间用户原则上不介入。
7. 如果没完成，Stop Hook 可以要求 Codex 继续。
8. 如果方向偏了，Stop Hook 可以要求 Codex 纠偏。
9. 如果全部完成，Codex 结束工作并提交结果。
