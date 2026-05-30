# Codex WikiGuard

**最小 Hook Guard** — 一个极简的 Codex Hook 守卫系统。

## 定位

- 只做规则读取、文件写入、简单 JSON 输出和危险命令匹配。
- **不是**完整 Guardrails Harness。
- 不引入任何外部依赖，仅用 Python 标准库。
- 第一版不调用 LLM。

**不做的**：多 Agent、图数据库、RAG、外层调度平台、Subagent、PostToolUse、PreCompact。

## Hook 清单

| Hook | 触发时机 | 功能 |
|------|----------|------|
| **UserPromptSubmit** | 每次用户 Prompt 发送前 | 读取 Wiki 文件，注入 `additionalContext` |
| **PreToolUse** | 每次 Codex 工具调用前 | 匹配危险命令 denylist，拦截高风险操作 |
| **StopJudge** | Codex Turn 结束时 | 读取 `last_assistant_message`，写入 `JUDGE.md` 和 `judge_latest.json`，默认 verdict = `human_review` |

## 快速开始

### 1. 目录结构

```
.project_wiki/
    HOME.md          — 项目主页
    RULES.md         — 规则和 Hook 契约
    CURRENT_TASK.md  — 当前任务
    DECISIONS.md     — 决策记录
    REJECTED.md      — 被拒绝的方案
    PROGRESS.md      — 进度跟踪
    ISSUES.md        — 问题追踪
    HOOKS.md         — Hook 文档
    JUDGE.md         — StopHook 的判���记录
    judge_latest.json — JSON 格式的最新判断

hooks/
    __init__.py
    user_prompt_submit.py   — UserPromptSubmit 实现
    pre_tool_guard.py       — PreToolUse 实现
    stop_judge.py           — StopJudge 实现

.codex/
    hooks.json              — Codex Hook 配置

README.md
```

### 2. 配置 Codex

在 Codex 的项目配置中引用 `.codex/hooks.json`：

```bash
# 确保 hooks 目录在 Python path 中
export PYTHONPATH="${PYTHONPATH}:$(pwd)/hooks"
```

或在 `.codex/hooks.json` 中将 `command` 改为绝对路径。

### 3. 运行 Hook 测试

```bash
cd /path/to/Codex-WikiGuard

# 测试 UserPromptSubmit
python -m hooks.user_prompt_submit

# 测试 PreToolUse
python -m hooks.pre_tool_guard

# 测试 StopJudge
python -m hooks.stop_judge
```

## PreToolUse Denylist

第一版拦截以下命令片段：

- `rm -rf`
- `sudo`
- `git reset --hard`
- `git clean -fd`
- `chmod -R`
- `chown -R`
- `curl | sh`
- `wget | sh`

## 设计约束

1. **最小可用**：不做复杂 Harness、不做多 Agent。
2. **标准库**：Python 内置模块即可，零外部依赖。
3. **保守判断**：StopJudge 默认 `human_review`，不自动 continue。
4. **不实现**：Subagent、PostToolUse、PreCompact、run_task.py。
5. **无 LLM**：第一版纯规则引擎，不调用大模型。

## 后续方向

- 稳定后开启 `continue` verdict 自动循环
- 扩展 denylist 规则
- 增加 Hook 日志和审计功能
