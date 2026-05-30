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

## Codex Hook 启用验证
- hooks.json 位置：已添加到全局 ~/.codex/hooks.json
- UserPromptSubmit：已添加到全局 hooks 配置，需要 Codex 重新加载后触发
- PreToolUse：已添加到全局 hooks 配置（仅匹配 Bash 工具），需要 Codex 重新加载后触发
- Stop：已添加到全局 hooks 配置，需要 Codex 重新加载后触发
- hooks.state 已重置，Codex 下次启动时会重新验证和信任 hooks
- hooks.json 修改方式：追加到全局配置，非项目级配置
- 需要手动验证：在 Codex 客户端中新建 Codex-WikiGuard 项目的 session，观察 hooks 是否触发
