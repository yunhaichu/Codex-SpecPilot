# Codex WikiGuard

**最小 Hook Guard** — 一个极简的 Codex Hook 守卫系统。

## 定位

- 只做规则读取、文件写入、简单 JSON 输出和危险命令匹配。
- **不是**完整 Guardrails Harness。
- 不引入任何外部依赖，仅用 Python 标准库。
- 第一版不调用 LLM。
- Hook 输出遵循 Codex 官方 wire format（`hookSpecificOutput`、`systemMessage`）。

**不做的**：多 Agent、图数据库、RAG、外层调度平台、Subagent、PostToolUse、PreCompact。

## Hook 清单

| Hook | Codex 事件名 | 触发时机 | 功能 |
|------|-------------|----------|------|
| **UserPromptSubmit** | `UserPromptSubmit` | 每次用户 Prompt 发送前 | 注入 INJECTION.md；存在时追加 latest_context.md |
| **PreToolUse** | `PreToolUse` | Bash 工具调用前 | 拦截危险命令和受保护文件操作；deny 时追加 guard_log.jsonl |
| **StopJudge** | `Stop` | Codex Turn 结束时 | 写入 JUDGE.md / latest_context.md / judge_latest.json |

## 目录结构

```
.project_wiki/
    HOME.md              — 项目主页
    RULES.md             — 规则和 Hook 契约
    CURRENT_TASK.md      — 当前任务
    DECISIONS.md         — 决策记录
    REJECTED.md          — 被拒绝的方案
    PROGRESS.md          — 进度跟踪
    ISSUES.md            — 问题追踪
    HOOKS.md             — Hook 文档
    JUDGE.md             — StopJudge 完整审计记录（含完整 assistant message）
    latest_context.md    — StopJudge 生成的短状态摘要
    judge_latest.json   — JSON 格式最新判断
    INJECTION.md         — 优先注入给 Codex 的短上下文文件
    guard_log.jsonl     — PreToolUse deny 时的追加日志

hooks/
      __init__.py
    user_prompt_submit.py     — UserPromptSubmit 事件钩子
    pre_tool_guard.py         — PreToolUse 事件钩子（仅匹配 Bash）
    stop_judge.py             — Stop 事件钩子

.codex/
    hooks.json                — Codex Hook 配置

README.md
```

## Local Model Mode

使用 qwen3.6:35b-a3b-coding-mxfp8 等本地模型时，Hook 行为做了专门优化：

- **UserPromptSubmit** 优先注入 INJECTION.md（短文本），存在时追加 latest_context.md；不注入完整 JUDGE.md。
- **JUDGE.md** 是人类审计文件，默认不注入到模型上下文。
- **StopJudge** 生成 latest_context.md 作为短状态摘要，不回流完整 assistant message。
- **PreToolUse** 采用确定性规则（denylist + 受保护文件/目录检查），deny 时追加 guard_log.jsonl；不依赖模型判断。
- 第一版仍然不自动 continue。

## 配置 Codex

将 `.codex/hooks.json` 放在项目根目录，Codex 会自动加载。

```bash
# 确保 hooks 目录在 Python path 中
export PYTHONPATH="${PYTHONPATH}:$(pwd)/hooks"
```

> **注意**：hooks.json 中的 `group` 包裹层在部分本地 Codex 版本中可能不被识别。
> 如果 Hook 不触发，可尝试去掉 `group`，直接将 `matcher` + `hooks` 放在事件名下：
> ```json
> "UserPromptSubmit": [
>    {
>      "matcher": {},
>      "hooks": [{ "type": "command", "command": "python -m hooks.user_prompt_submit" }]
>    }
> ]
> ```

## 本地测试 Hook

```bash
cd /path/to/Codex-WikiGuard

# UserPromptSubmit（空输入）
echo '{}' | python -m hooks.user_prompt_submit

# PreToolUse — 拦截：危险命令
echo '{"tool_input": {"command": "rm -rf /tmp/x"}}' | python -m hooks.pre_tool_guard

# PreToolUse — 拦截：受保护文件
echo '{"tool_input": {"command": "echo x > .env"}}' | python -m hooks.pre_tool_guard

# PreToolUse — 放行：安全命令
echo '{"tool_input": {"command": "ls -la"}}' | python -m hooks.pre_tool_guard

# StopJudge
echo '{"last_assistant_message": "changed hooks only"}' | python -m hooks.stop_judge
```

不传 stdin 时所有 Hook 也正常工作（回退为 `{}`）。

## PreToolUse 拦截规则

**命令 denylist**：
- `rm -rf` / `sudo` / `git reset --hard` / `git clean -fd` / `chmod -R` / `chown -R` / `curl | sh` / `wget | sh`

**受保护文件**（匹配文件名模式 + 写操作关键词时拦截）：
- `.env` / `.env.*` / `.pem` / `.key` / `id_rsa` / `id_ed25519` / `secrets.*` / `credentials.*` / `docker-compose.yml`

**受保护目录**：
- `deploy/` / `deployment/` / `migrations/` / `migration/` / `schema/` / `.ssh/` / `.github/workflows/`

**写操作关键词**：`rm` / `mv` / `cp` / `>` / `>>` / `tee` / `sed -i` / `perl -pi` / `python -c` / `python3 -c`

## Wire Format 约定

- **UserPromptSubmit** 返回：`{ "hookSpecificOutput": { "hookEventName": "UserPromptSubmit", "additionalContext": "..." } }`
- **PreToolUse** 命中拦截规则返回：`{ "hookSpecificOutput": { "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..." } }`；未命中返回 `{}`；deny 时追加 guard_log.jsonl
- **Stop** 返回：`{ "systemMessage": "Codex-WikiGuard wrote human_review judgment." }`

## 设计约束

1. **最小可用**：不做复杂 Harness、不做多 Agent。
2. **标准库**：Python 内置模块即可，零外部依赖。
3. **保守判断**：Stop 事件默认 `systemMessage`，不返回 `decision: block`，不自动 continue。
4. **不实现**：Subagent、PostToolUse、PreCompact、run_task.py。
5. **无 LLM**：第一版纯规则引擎，不调用大模型。
6. **本地模型友好**：注入上下文短、硬规则优先、JUDGE.md 不回流污染。

## 后续方向

- 稳定后开启 `continue` verdict 自动循环
- 扩展 denylist / 受保护文件列表
- 增加 Hook 日志和审计功能
