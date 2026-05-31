# Codex-WikiGuard — PROGRESS

## v0.3 权限分层与 LLM 监督修复（2026-05-31）
- self-development 权限顺序: pass — hooks/、.codex/hooks.json 在 self-dev 模式下允许
- supervised-project 权限保护: pass — supervised 模式下 hooks/、.codex/ 禁止
- PreToolUse Bash coverage: pass — denylist、protected file/dir 均拦截
- PreToolUse apply_patch/Edit/Write coverage: pass — 监督文件路径均被 deny
- PreToolUse LLM soft judge: pass — codex exec 可用时执行，不可用时保守 skip（不阻断）
- Stop prompt includes PROJECT_SPEC/latest_context/assistant_msg: pass — 真实上下文已注入
- Stop safe auto-continue returns decision:block: implemented
- Stop dangerous auto-continue blocked: pass — 权限门控 + loop limit 均生效
- loop_state updated_at: pass — 格式正确
- smoke_test.py: **69/69 pass**
- 原有 v0.2 行为: 保留
- 外部依赖: 无
- LLM 覆盖硬 deny: 不允许

### 修复内容
1. **permission_policy.py**: 修正权限顺序 — self-dev 模式下允许 hooks/、.codex/hooks.json、tests/、README.md、INJECTION.md；supervised 模式下禁止 hooks/、.codex/
2. **.codex/hooks.json**: PreToolUse 覆盖范围从 `^Bash$` 改为 `^(Bash|apply_patch|Edit|Write)$`
3. **pre_tool_guard.py**: 新增 codex exec 软判断；apply_patch/Edit/Write 路径提取；软判断失败时保守 skip（不阻断已通过的硬规则）
4. **stop_judge.py**: LLM prompt 包含 PROJECT_SPEC.md、latest_context.md、last_assistant_message 实际内容；safe continue/revise 时返回 decision:block；权限门控 + loop limit 机制
5. **codex_client.py**: loop_state 增加 last_verdict、updated_at 字段；兼容旧格式
6. **smoke_test.py**: 69 项测试全部通过，覆盖 self-dev/supervised 权限差异、apply_patch/Edit/Write 拦截、软判断 skip 行为

### 真实 Hook 触发验证
- PreToolUse: pass — 拦截 PROJECT_SPEC.md、JUDGE.md、.env
- PreToolUse safe command: pass — ls -la 放行
- UserPromptSubmit: pass — additionalContext 包含权限摘要
- Stop: pass — 输出 systemMessage，judge_latest.json 合法
- codex exec 调用: 因本地 ollama config 问题当前返回 human_review fallback，功能正确

## Codex Hook 真实触发验证（2026-05-31）
- PreToolUse real trigger: pass
- PreToolUse safe command: pass
- PreToolUse protected file deny: pass
- guard_log.jsonl: pass
- UserPromptSubmit real trigger: pass
- Stop real trigger: pass
- hooks.state empty: does not block hook execution
- hooks.json group format: works
- 自动 continue: 未启用
