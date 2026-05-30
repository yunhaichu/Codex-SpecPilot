# Codex WikiGuard

**最小 Hook Guard** — 一个极简的 Codex Hook 守卫系统。

## 定位

- 只做规则读取、文件写入、简单 JSON 输出和危险命令匹配。
- **不是**完整 Guardrails Harness。
- 不引入任何外部依赖，仅用 Python 标准库。
- Hook 输出遵循 Codex 官方 wire format（`hookSpecificOutput`、`systemMessage`）。

**不做的**：多 Agent、图数据库、RAG、外层调度平台、Subagent、PostToolUse、PreCompact。

## Hook 清单

| Hook | Codex 事件名 | 触发时机 | 功能 |
|------|-------------|----------|------|
| **UserPromptSubmit** | `UserPromptSubmit` | 每次用户 Prompt 发送前 | 调用 codex exec（默认模型）生成短上下文；失败时回退到 INJECTION.md |
| **PreToolUse** | `PreToolUse` | Bash 工具调用前 | 硬规则（denylist + 受保护文件）优先；未命中则调用 codex exec 软判断 |
| **StopJudge** | `Stop` | Codex Turn 结束时 | 调用 codex exec 做判断，写入 JUDGE.md / latest_context.md / judge_latest.json |

## 目录结构

```
.project_wiki/
    HOME.md                 — 项目主页
    RULES.md                — 规则和 Hook 契约
    CURRENT_TASK.md         — 当前任务
    DECISIONS.md            — 决策记录
    REJECTED.md             — 被拒绝的方案
    PROGRESS.md             — 进度跟踪
    ISSUES.md               — 问题追踪
    HOOKS.md                — Hook 文档
    PROJECT_SPEC_TEMPLATE.md — PROJECT_SPEC 模板
    PROJECT_SPEC.md         — 项目需求规格（由 AI 生成）
    JUDGE.md                — StopJudge 完整审计记录（含完整 assistant message）
    latest_context.md       — StopJudge 生成的短状态摘要
    judge_latest.json      — JSON 格式最新判断
    loop_state.json        — 自动继续循环计数
    INJECTION.md            — 优先注入给 Codex 的短上下文文件
    guard_log.jsonl        — PreToolUse deny 时的追加日志

hooks/
        __init__.py
    codex_client.py         — codex exec 调用封装（默认模型）
    user_prompt_submit.py   — UserPromptSubmit 事件钩子
    pre_tool_guard.py       — PreToolUse 事件钩子（仅匹配 Bash）
    stop_judge.py           — Stop 事件钩子

tests/
    smoke_test.py           — 冒烟测试

.codex/
    hooks.json              — Codex Hook 配置

README.md
```

## v0.2 变化

- v0.1 是纯规则 smoke test。
- v0.2 开始，Hook 可以调用当前 Codex 默认模型（通过 `codex exec`，不传 `-m`）。
- 不需要单独设置模型或 LLM API endpoint。
- Hook 通过 `codex exec` 调用默认 Codex。
- 为避免递归，子进程设置 `CODEX_WIKIGUARD_CHILD=1`。
- 子 Codex 不会触发 WikiGuard 判断。
- PreToolUse：硬规则优先，软判断由默认 Codex 完成。
- Stop：默认 Codex 判断 pass / continue / revise / done / human_review。
- 自动 continue 最多 3 次，超过强制 human_review。

## 真实工作流

1. 用户先通过与 AI 对话确认项目需求。
2. AI 按模板（PROJECT_SPEC_TEMPLATE.md）整理成 PROJECT_SPEC.md。
3. 用户打开 Codex，在项目目录输入"开始工作"。
4. Codex 根据 PROJECT_SPEC.md 自动开发。
5. Hook 使用当前 Codex 默认模型监督 Codex。
6. 开发期间用户原则上不介入。
7. 如果没完成，Stop Hook 可以要求 Codex 继续（最多 3 次）。
8. 如果方向偏了，Stop Hook 可以要求 Codex 纠偏。
9. 如果全部完成，Codex 结束工作并提交结果。

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
>      {
>        "matcher": {},
>        "hooks": [{ "type": "command", "command": "python -m hooks.user_prompt_submit" }]
>      }
> ]
> ```

## 本地测试 Hook

```bash
cd /path/to/Codex-WikiGuard

# 运行冒烟测试
python3 tests/smoke_test.py

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
- **Stop** 返回：`{ "systemMessage": "Codex-WikiGuard wrote ... judgment." }`

## 设计约束

1. **最小可用**：不做复杂 Harness、不做多 Agent。
2. **标准库**：Python 内置模块即可，零外部依赖。
3. **保守判断**：Stop 事件不返回 `decision: block`，不自动 continue（除非 codex exec 明确允许且不超过 3 次）。
4. **不实现**：Subagent、PostToolUse、PreCompact、run_task.py。
5. **不写死模型名**：Hook 通过 `codex exec` 调用默认模型，不传 `-m`。
6. **递归保护**：子进程设置 `CODEX_WIKIGUARD_CHILD=1`，不触发 WikiGuard 判断。

## 后续方向

- 扩展 denylist / 受保护文件列表
- 增加 Hook 日志和审计功能
- 优化 codex exec prompt 以提高判断质量
