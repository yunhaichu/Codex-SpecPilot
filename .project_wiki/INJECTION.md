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

## Latest Judge
- VERDICT: human_review
- NEXT_ACTION: wait for user confirmation
- AUTO_CONTINUE: disabled

## Local Model Mode
- Backend model: qwen3.6:35b-a3b-coding-mxfp8
- Use short, explicit instructions.
- Prefer deterministic rules over model judgment.
- Do not rely on hidden reasoning or implicit context.
