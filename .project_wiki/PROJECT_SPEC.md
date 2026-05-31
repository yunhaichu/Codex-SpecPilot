# Project Specification

## 0. Project Mode
当前项目模式：`wikiguard_self_development`

> This is the Codex WikiGuard project itself. Codex is permitted to modify
> hooks/*.py, .codex/hooks.json, tests/*, README.md, and this file
> (when explicitly requested).

## 1. Project Goal
Codex WikiGuard 是一个最小 Hook Guard 系统，用于在 Codex 自动开发项目时提供监督。

## 2. Background
Codex 在开发项目时可能偏离需求或修改不该改的文件。需要一套 Hook 机制在 Codex 执行操作前进行拦截和判断。

## 3. User Requirements
- Hook 不修改 LLM 调用方式，使用 codex exec 默认模型
- Hook 通过 CODEX_WIKIGUARD_CHILD 递归保护避免无限循环
- 权限分层：Codex 可以改业务代码，不能改监督系统
- 所有测试必须通过

## 4. Non-Goals
- 不做复杂 Harness
- 不做多 Agent
- 不做图数据库、RAG
- 不新增外部依赖

## 5. Allowed Scope
- hooks/*.py
- .codex/hooks.json
- tests/*
- README.md
- .project_wiki/INJECTION.md
- .project_wiki/PROJECT_SPEC.md（需用户明确要求）

## 6. Protected Scope
- .project_wiki/JUDGE.md
- .project_wiki/latest_context.md
- .project_wiki/judge_latest.json
- .project_wiki/loop_state.json
- .project_wiki/guard_log.jsonl
- .project_wiki/PROJECT_SPEC.md（非明确要求时）
- .project_wiki/RULES.md
- .project_wiki/DECISIONS.md
- .project_wiki/REJECTED.md
- .project_wiki/PERMISSIONS.md
- .project_wiki/PROGRESS.md

## 7. Development Plan
待定。

## 8. Acceptance Criteria
- 所有 smoke test 通过
- 权限策略生效
- Codex Worker 无法修改监督文件

## 9. Stop Conditions
待定。

## 10. Submission Requirements
待定。
