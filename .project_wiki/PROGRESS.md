
## v0.3 权限与 LLM 监督修复（2026-05-31）
- 修正 codex_client.py WIKI_DIR 动态路径问题
- 修正 stop_judge.py COMPLETION_REPORT 动态路径问题
- 修正 stop_judge.py loop_state 动态路径问题
- 强化 LLM prompt 安全规则（明确停止对项目书/规则文件的修改行为）
- 修正 smoke_test.py 中 codex_client.WIKI_DIR 设置
- smoke_test.py: **110/110 pass**（原有 95 + 新增 15）
- 所有 Hook 行为验证通过
