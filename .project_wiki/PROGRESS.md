# Codex-WikiGuard — PROGRESS

## Milestones

- [ ] v1: Three hooks implemented and tested
- [ ] v1: README complete
- [ ] v1: Wiki structure in place

## Notes

- Hooks use only Python standard library.
- PreToolUse denylist is fixed at import time.
- StopJudge default verdict is `human_review`.

## v0.1.0-local-guard 验证

- UserPromptSubmit：通过
- PreToolUse denylist：通过
- PreToolUse protected file：通过
- PreToolUse safe command：通过
- StopJudge：通过
- guard_log.jsonl：通过
- judge_latest.json：通过
- latest_context.md：通过
- 真实 Codex Hook 触发：待手动验证
- 自动 continue：未启用

## 验证日期
- 验证时间：2026-05-31
- hooks.json group 包装层：保留（待 Codex 真实环境验证，不触发时再调整）
