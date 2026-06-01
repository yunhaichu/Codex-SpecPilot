# SpecPilot Project Onboarding

This project is not ready for `开始工作` yet.
Codex must first interview the user and produce a complete PROJECT_SPEC candidate.
The controlled SpecPilot Hook flow writes `.project_wiki/PROJECT_SPEC.md`.

## Project Snapshot

- Kind: `existing`
- Signals: `readme`
- Top-level entries: `.gitignore, README.md, examples, tests`

## Rules

1. Do not write business code during onboarding.
2. Ask at most 5 high-signal questions per round.
3. Do not invent requirements the user did not confirm.
4. When enough information is known, output a complete PROJECT_SPEC candidate.
5. Ask for GitHub sync preference during onboarding; default to local-only if upload is not needed.
6. If GitHub sync is requested, ask for auth method, public/private visibility, repo target, and allowed checkpoint/tag behavior.
7. Never ask the user to paste API keys, tokens, or secrets into project files.
8. Keep Allowed Scope concrete; do not use vague phrases like related files.

## First Questions

- 这个老项目当前的主要用途和现阶段目标是什么？
- 这次接管后第一阶段要完成哪些具体改动？哪些旧功能不能碰？
- Codex 允许修改哪些具体目录或文件？
- 哪些目录、配置、数据、部署、schema、migration 或密钥必须保护？
- 当前项目如何构建、测试、启动或人工验收？是否需要同步或上传到 GitHub？如果不需要，默认 local-only；如果需要，请说明认证方式（不要提供 token/密钥原文）、仓库 owner/name、公开或私有，以及允许 Hook 在哪些节点 push、tag 或 checkpoint。
