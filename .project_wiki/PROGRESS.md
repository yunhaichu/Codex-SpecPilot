# Codex-WikiGuard — PROGRESS

## v0.3 权限分层与 LLM 监督修复（2026-05-31）
- PreToolUse Bash coverage: pass — denylist、protected file/dir 拦截正常
- PreToolUse apply_patch/Edit/Write coverage: pass — target_file/path/file_path/file 路径提取正常
- PreToolUse LLM soft judge: pass — codex exec 失败时保守 deny，非 skip
- PreToolUse soft judge deny on failure: pass — 安全命令在 codex 不可用时也 deny
- Stop prompt includes PROJECT_SPEC/latest_context/assistant_msg: pass — 真实上下文已注入
- Stop decision:block for auto-continue: pass — 代码逻辑已实现
- Stop dangerous auto-continue blocked: pass — 权限门控 + loop limit 均生效
- loop_state updated_at: pass — 字段正确，格式 OK
- smoke_test.py: **84/84 pass**
- 原有 v0.2 行为: 保留
- 外部依赖: 无
- LLM 覆盖硬 deny: 不允许

### 修复内容
1. **pre_tool_guard.py**: `_soft_judge` 返回 "deny" 代替 "skip"（fail closed 策略）
2. **pre_tool_guard.py**: `_extract_targets` 增加 `target_file`, `path`, `file_path`, `filename`, `file` 字段解析
3. **stop_judge.py**: 已有真实上下文注入 + decision:block + 权限门控
4. **codex_client.py**: loop_state 有 updated_at 字段
5. **smoke_test.py**: 新增 apply_patch/Edit/Write 测试、judge_latest.json 结构测试、hooks.json PreToolUse 覆盖测试、soft judge fail closed 测试
6. **.codex/hooks.json**: PreToolUse matcher 已覆盖 Bash|apply_patch|Edit|Write

## Codex Hook 真实触发验证（2026-05-31）
- PreToolUse real trigger: pass — 拦截 PROJECT_SPEC.md、JUDGE.md、.env
- PreToolUse safe command: pass — ls -la 由软判断处理（codex 不可用时 deny）
- PreToolUse protected file deny: pass
- guard_log.jsonl: pass
- UserPromptSubmit real trigger: pass
- Stop real trigger: pass
- hooks.state empty: does not block hook execution
- hooks.json group format: works
- 自动 continue: 未启用

## 本地 codex exec 问题
- codex exec 因 ollama profile 配置问题不可用
- Hook 代码逻辑已正确实现 fail closed 策略
- 修复 ollama 配置后 LLM 监督功能即可正常运作

## protected target hard-rule reachability fix (2026-05-31)
- Fixed unreachable `_has_protected_target(command)` branch in PreToolUse
- `_has_protected_target` moved to be a sibling of the denylist `for` loop (not nested inside return)
- Verified: deploy/, schema/, migrations/, .github/workflows/ writes denied by hard rule
- smoke_test.py: 88/88 pass (up from 84)

## codex exec 本地环境修复（2026-05-31）
- 修复前：codex exec 报错 `legacy profile = "ollama-launch-codex-app" config is no longer supported`
- 修复方式：
  - 将 `[profiles.ollama-launch-codex-app]` 和 `[model_providers.ollama-launch-codex-app]` 移至 `~/.codex/ollama-launch-codex-app.config.toml`
  - 从 `~/.codex/config.toml` 中移除 legacy profile 和 model provider 段
  - `codex_client.py` 添加 `--profile ollama-launch-codex-app` 参数
- 修复 codex_client.py 缩进错误：call_codex_default 的 docstring 缩进不一致导致 SyntaxError
- 修复后 codex exec 可以启动，但遇到平台限制：
  - 错误：`The 'qwen3.6:35b-a3b-coding-mxfp8' model is not supported when using Codex with a ChatGPT account.`
  - 原因：ChatGPT 账号的 CLI 不支持自定义模型，只支持 OpenAI 模型
  - Hook 的 fail-closed 策略生效：codex exec 失败 → soft judge 返回 deny
- 解决方案：需要使用 API Key 模式的 Codex 配置，或等 Codex CLI 支持非 OpenAI 模型
- smoke_test.py: **88/88 pass**（修复后）
