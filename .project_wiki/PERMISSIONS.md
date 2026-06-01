# Codex SpecPilot — PERMISSIONS

## 1. Core Rule

Codex Worker 可以开发业务代码，但不能修改监督它自己的任务书、规则、Hook 配置、Hook 程序、判断记录和审计日志。

换句话说：
- PROJECT_SPEC.md 是任务合同，Codex Worker 不能改。
- RULES.md 是制度，Codex Worker 不能改。
- hooks/*.py 是监督程序，Codex Worker 不能关掉或改写。
- .codex/hooks.json 是监督配置，Codex Worker 不能改。
- JUDGE.md / judge_latest.json / latest_context.md / loop_state.json 是监督记录，Codex Worker 不能直接改。
- guard_log.jsonl 是拦截日志，Codex Worker 不能直接改或清空。
- WORKFLOW.md 是工作流说明，Codex Worker 不能改。
- COMPLETION_REPORT_TEMPLATE.md 是报告模板，Codex Worker 不能改。

## 2. Project Mode

PROJECT_SPEC.md 必须声明项目模式：
- `specpilot_self_development` — 开发 Codex SpecPilot 自身
- `supervised_project_development` — 被 SpecPilot 监督的普通项目

### specpilot_self_development

用于开发 Codex SpecPilot 本身。
允许 Codex 修改：
- hooks/*.py
- .codex/hooks.json
- tests/*
- README.md
- .project_wiki/INJECTION.md
- .project_wiki/PROJECT_SPEC.md（前提是用户明确要求本轮修改任务书）

### supervised_project_development

用于被 Codex SpecPilot 监督的普通项目。
禁止 Codex 修改：
- .codex/hooks.json
- hooks/*.py
- .project_wiki/PROJECT_SPEC.md
- .project_wiki/PROJECT_SPEC_TEMPLATE.md
- .project_wiki/RULES.md
- .project_wiki/DECISIONS.md
- .project_wiki/REJECTED.md
- .project_wiki/PERMISSIONS.md
- .project_wiki/JUDGE.md
- .project_wiki/latest_context.md
- .project_wiki/judge_latest.json
- .project_wiki/loop_state.json
- .project_wiki/guard_log.jsonl
- .project_wiki/WORKFLOW.md
- .project_wiki/COMPLETION_REPORT_TEMPLATE.md

## 3. Hook Write Permissions

### UserPromptSubmit Hook
默认只读。
可读：
- .project_wiki/PROJECT_SPEC.md
- .project_wiki/INJECTION.md
- .project_wiki/latest_context.md
- .project_wiki/PERMISSIONS.md
默认不可写任何文件。

### PreToolUse Hook
可写：
- .project_wiki/guard_log.jsonl
不可写：
- 其他所有项目 Wiki 文件
- hooks/*.py
- .codex/hooks.json
- 业务代码

### Stop Hook
可写：
- .project_wiki/JUDGE.md
- .project_wiki/latest_context.md
- .project_wiki/judge_latest.json
- .project_wiki/loop_state.json
- .project_wiki/PROGRESS.md
- .project_wiki/COMPLETION_REPORT.md（仅在 verdict=done 时）
不可写：
- .project_wiki/PROJECT_SPEC.md
- .project_wiki/RULES.md
- .project_wiki/DECISIONS.md
- .project_wiki/REJECTED.md
- .project_wiki/PERMISSIONS.md
- .project_wiki/WORKFLOW.md
- .project_wiki/COMPLETION_REPORT_TEMPLATE.md
- hooks/*.py
- .codex/hooks.json
- 业务代码

## 4. Always Protected Files

默认禁止 Codex Worker 修改：
- .env
- .env.*
- *.pem
- *.key
- id_rsa
- id_ed25519
- secrets.*
- credentials.*
- .ssh/
- deploy/
- deployment/
- schema/
- migration/
- migrations/
- .github/workflows/

除非 PROJECT_SPEC.md 明确写出具体文件、具体原因、具体允许动作，否则必须 deny。

## 5. Permission Priority

权限优先级：
1. 绝对危险命令：直接 deny
2. 受保护文件和目录：直接 deny
3. 监督系统文件：直接 deny
4. 超出 PROJECT_SPEC Allowed Scope：deny 或 human_review
5. 只有以上都通过，才允许 LLM 软判断
6. LLM 不能覆盖硬规则 deny
