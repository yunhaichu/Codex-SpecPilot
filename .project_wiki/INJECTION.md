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

## Permission Summary (Codex WikiGuard)
Codex Worker **MUST NOT** modify:
- .project_wiki/PROJECT_SPEC.md, RULES.md, DECISIONS.md, REJECTED.md, PERMISSIONS.md
- .project_wiki/JUDGE.md, latest_context.md, judge_latest.json, loop_state.json, guard_log.jsonl
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
