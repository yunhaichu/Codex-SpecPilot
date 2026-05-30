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

## Codex Hook 启用
- 修改文件：`~/.codex/hooks.json`（追加 WikiGuard 钩子）
- 未修改：项目级 `.codex/hooks.json`（保持原样）
- hooks.state：已重置（Codex 下次 session 会重新验证）
- Hook 已启用：是
  - UserPromptSubmit: wiki-guard-user-prompt (cwd=项目根目录)
  - PreToolUse: 仅匹配 Bash 工具
  - Stop: 追加到现有 Stop 钩子列表

## 下一步验证（需在 Codex 客户端操作）
1. 在 Codex 客户端中打开 Codex-WikiGuard 项目
2. 发送：`只回复：wiki guard injection test`
   → 观察状态栏是否显示 "Codex-WikiGuard: injecting wiki context"
3. 要求执行：`echo x > .env`
   → 观察是否被 PreToolUse 拦截，查看 .project_wiki/guard_log.jsonl
4. 发送：`只回复：stop hook test complete，不改文件`
   → 回合结束后检查 JUDGE.md、latest_context.md、judge_latest.json

## 未修改 hooks.json 原因
- hooks.json 已正确配置到全局配置文件
- hooks.state 已重置，Codex 下次启动时会重新信任
- 不需要额外修改格式

## Hook 格式修复（2026-05-31）
- 问题：Codex 报错 "invalid type: map, expected a string"（matcher 不能是 map）
- 问题：Codex 报错 "invalid type: map, expected a sequence"（事件名下不能是 group map）
- 修复：
     * `~/.codex/hooks.json`：所有 matcher 从 {} 改为 ""
     * `.codex/hooks.json`：移除 group 包装，事件名直接指向数组
- 验证：两个 hooks.json 均通过格式校验
- 状态：等待 Codex 重新加载后验证触发
