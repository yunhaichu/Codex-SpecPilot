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
| **PreToolUse** | `PreToolUse` | Bash/apply_patch/Edit/Write 工具调用前 | 硬规则（denylist + 受保护文件 + 权限策略）优先；未命中则调用 codex exec 软判断 |
| **StopJudge** | `Stop` | Codex Turn 结束时 | 调用 codex exec 做判断，写入 JUDGE.md / latest_context.md / judge_latest.json |

## 目录结构

```
.project_wiki/
    HOME.md                  — 项目主页
    RULES.md                 — 规则和 Hook 契约
    CURRENT_TASK.md          — 当前任务
    DECISIONS.md             — 决策记录
    REJECTED.md              — 被拒绝的方案
    PROGRESS.md              — 进度跟踪
    ISSUES.md                — 问题追踪
    HOOKS.md                 — Hook 文档
    PROJECT_SPEC_TEMPLATE.md — PROJECT_SPEC 模板
    PROJECT_SPEC.md          — 项目需求规格（由 AI 生成）
    JUDGE.md                 — StopJudge 完整审计记录（含完整 assistant message）
    latest_context.md        — StopJudge 生成的短状态摘要
    judge_latest.json       — JSON 格式最新判断
    loop_state.json         — 自动继续循环计数
    INJECTION.md             — 优先注入给 Codex 的短上下文文件
    guard_log.jsonl         — PreToolUse deny 时的追加日志
    PERMISSIONS.md          — 权限分层策略说明

hooks/
         __init__.py
    codex_client.py          — codex exec 调用封装（默认模型）
    user_prompt_submit.py    — UserPromptSubmit 事件钩子
    pre_tool_guard.py        — PreToolUse 事件钩子（Bash + apply_patch + Edit + Write）
    stop_judge.py            — Stop 事件钩子
    permission_policy.py     — 权限策略模块

tests/
    smoke_test.py            — 冒烟测试

.codex/
    hooks.json               — Codex Hook 配置

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

## v0.3 变化 — 权限分层

v0.3 引入权限分层策略，防止 Codex Worker 修改监督它自己的文件。

### 权限模型

1. **Codex Worker 只能改业务代码**。
2. **Codex Worker 不能改任务书、规则、Hook、监督日志和状态文件**：
   - `PROJECT_SPEC.md`、`RULES.md`、`DECISIONS.md`、`REJECTED.md`、`PERMISSIONS.md`
   - `JUDGE.md`、`latest_context.md`、`judge_latest.json`、`loop_state.json`、`guard_log.jsonl`
   - `.codex/hooks.json`、`hooks/*.py`（除非 project mode 是 `wikiguard_self_development`）
3. **PreToolUse Hook** 只能写 `guard_log.jsonl`。
4. **Stop Hook** 只能写 `JUDGE.md`、`latest_context.md`、`judge_latest.json`、`loop_state.json`、`PROGRESS.md`。
5. **UserPromptSubmit Hook** 默认只读。
6. **普通项目模式**（`supervised_project_development`）下，Codex 不能改 `.codex/hooks.json` 和 `hooks/*.py`。
7. **开发 WikiGuard 自身**时，`PROJECT_SPEC.md` 需声明 `wikiguard_self_development`。
8. **LLM 软判断不能覆盖硬权限 deny**。

### 权限优先级

1. 绝对危险命令 → deny
2. 受保护文件和目录 → deny
3. 监督系统文件 → deny
4. 超出 PROJECT_SPEC Allowed Scope → deny 或 human_review
5. 以上通过 → 才允许 LLM 软判断

### 项目模式

- `wikiguard_self_development` — 开发 Codex WikiGuard 自身，允许修改 hooks/*.py、.codex/hooks.json
- `supervised_project_development` — 被 WikiGuard 监督的普通项目，禁止修改上述监督文件

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
>       {
>         "matcher": {},
>         "hooks": [{ "type": "command", "command": "python -m hooks.user_prompt_submit" }]
>       }
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

# PreToolUse — 拦截：监督文件
echo '{"tool_input": {"command": "echo x > .project_wiki/JUDGE.md"}}' | python -m hooks.pre_tool_guard

# PreToolUse — 放行：安全命令
echo '{"tool_input": {"command": "ls -la"}}' | python -m hooks.pre_tool_guard

# PreToolUse — apply_patch 拦截监督文件
echo '{"tool": "apply_patch", "tool_input": {"target_file": ".project_wiki/PROJECT_SPEC.md", "original_text": "a", "new_text": "b"}}' | python -m hooks.pre_tool_guard

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

**监督系统文件**（Codex Worker 不能修改）：
- `PROJECT_SPEC.md` / `RULES.md` / `DECISIONS.md` / `REJECTED.md` / `PERMISSIONS.md`
- `JUDGE.md` / `latest_context.md` / `judge_latest.json` / `loop_state.json` / `guard_log.jsonl`
- `.codex/hooks.json` / `hooks/*.py`

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
7. **权限分层**：Codex Worker 不能修改监督系统文件，LLM 软判断不能覆盖硬权限 deny。
8. **自动 continue 权限门控**：Stop 判断的 next_action 如涉及监督文件修改，强制 human_review。

## 后续方向

- 扩展 denylist / 受保护文件列表
- 增加 Hook 日志和审计功能
- 优化 codex exec prompt 以提高判断质量

## Codex profile inheritance

1. WikiGuard 不写死模型。
2. WikiGuard 不写死 profile。
3. 默认调用：

```bash
codex exec <prompt>
```

4. 如果当前 Codex 需要 profile 才能使用本地模型，应由启动环境提供：

```bash
export CODEX_PROFILE=ollama-launch-codex-app
```

或：

```bash
export CODEX_WIKIGUARD_PROFILE=ollama-launch-codex-app
```

5. `CODEX_WIKIGUARD_PROFILE` 优先级高于 `CODEX_PROFILE`。
6. 这只是继承启动环境，不是 WikiGuard 独立配置模型。
7. 如果使用 ChatGPT 账号模式运行 Codex，而该模式不支持自定义本地模型，则 Hook LLM supervision 会 fail closed。
8. 这种情况下需要修复 Codex 运行环境，而不是修改 WikiGuard 代码。
