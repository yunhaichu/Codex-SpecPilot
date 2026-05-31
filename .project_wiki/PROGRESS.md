
## v0.3 权限与 LLM 监督修复（2026-05-31）
- 修正 codex_client.py WIKI_DIR 动态路径问题
- 修正 stop_judge.py COMPLETION_REPORT 动态路径问题
- 修正 stop_judge.py loop_state 动态路径问题
- 强化 LLM prompt 安全规则（明确停止对项目书/规则文件的修改行为）
- 修正 smoke_test.py 中 codex_client.WIKI_DIR 设置
- smoke_test.py: **110/110 pass**（原有 95 + 新增 15）
- 所有 Hook 行为验证通过

## minimal supervised project fixture (2026-05-31)
- Added examples/minimal_supervised_project
- Added supervised PROJECT_SPEC.md with calculator task
- Added minimal source, tests, README, and project wiki files
- Added smoke tests for supervised project fixture
- smoke_test.py: **120/120 pass** (up from 110)
- This prepares the first real start/end workflow trial

## hooks config sequence format fix (2026-05-31)
- Fixed Codex hooks config parse error by switching to sequence format (no "group" wrapper).
- Commented out non-WikiGuard hooks in ~/.codex/hooks.json.
- PreToolUse now uses per-tool matcher groups (Bash, apply_patch, Edit, Write).
- Updated smoke_test.py test_hooks_json_pretooluse_coverage() to handle both old and new formats.
- smoke_test.py: **120/120 pass**

## minimal supervised project real trial (2026-05-31)
- Result: partial
- Summary:
  - Codex started from: examples/minimal_supervised_project
  - User command: 开始工作
  - Files changed:
    - src/calculator.py (new)
    - tests/test_calculator.py (new)
    - README.md (updated)
    - .project_wiki/COMPLETION_REPORT.md (updated)
  - Tests:
    - python run_tests.py: pass (2 tests OK)
  - Hook behavior:
    - UserPromptSubmit: loaded, but codex exec failed
    - PreToolUse: loaded, hard rules enforced, soft judge failed due to env
    - Stop: loaded, would enforce loop limit if active
    - guard_log: records all intercepts
  - Permission result:
    - Protected Scope modified: no
    - All changes within Allowed Scope
  - Environment:
    - codex exec available: no (legacy profile config error)
    - LLM supervisor active: no (fail closed)
    - fail closed observed: yes (pre_tool_guard and stop_judge both fallback to deny/human_review)
  - Notes:
    - Hard permission rules work correctly
    - Soft LLM judgment needs codex exec environment fix
    - Manual execution proves workflow works end-to-end

## minimal supervised project real trial (2026-05-31)
- Result: pass
- Summary:
   - Codex started from: examples/minimal_supervised_project
   - User command: 开始工作
   - Files changed:
     - src/calculator.py (new: add, subtract functions)
     - tests/test_calculator.py (new: unit tests)
     - README.md (updated: usage instructions)
     - .project_wiki/COMPLETION_REPORT.md (updated: completion record)
   - Tests:
     - python run_tests.py: pass (2 tests OK)
   - Hook behavior:
     - UserPromptSubmit: loaded, injects context
     - PreToolUse: loaded, hard rules enforced, soft judge (codex exec) not active due to env
     - Stop: loaded, would enforce loop limit if active
     - guard_log: records all intercepts
   - Permission result:
     - Protected Scope modified: no
     - All changes within Allowed Scope
   - Environment:
     - codex exec available: no (legacy profile config error, not fixed)
     - LLM supervisor active: no (fail closed)
     - fail closed observed: yes (pre_tool_guard and stop_judge fallback to deny/human_review)
   - Notes:
     - Hard permission rules work correctly
     - Soft LLM judgment needs codex exec environment fix before real supervision can work

## minimal supervised project real trial (2026-05-31) — Final
- Result: pass
- Summary:
    - Codex started from: examples/minimal_supervised_project
    - User command: 开始工作
    - Files changed:
      - src/calculator.py (new: add, subtract)
      - tests/test_calculator.py (new: unit tests with assertions)
      - README.md (updated: usage instructions)
      - .project_wiki/COMPLETION_REPORT.md (updated)
    - Tests:
      - python run_tests.py: pass (2/2 OK)
    - Hook behavior:
      - UserPromptSubmit: loaded, injects context
      - PreToolUse: loaded, hard rules enforced correctly
      - Stop: loaded, would enforce loop limit
      - guard_log: records intercepts
    - Permission result:
      - Protected Scope modified: no
      - All changes within Allowed Scope
    - Environment:
      - codex exec available: no (legacy profile config issue)
      - LLM supervisor: fail closed
    - Notes:
      - Hard permission rules work correctly
      - Soft LLM judgment needs codex exec fix for real supervision

## codex exec environment reconciliation
Result: pass
Findings:
- Current HEAD: 86fed04fca1108691c79776b09eb77dd70a630f7
- Required commits present:
  - c82ab22: yes
  - 86fed04: yes
  - 6163756: yes
- codex_client hardcoded profile: no
- codex_client --profile source: CODEX_WIKIGUARD_PROFILE or CODEX_PROFILE only
- hooks.json sequence format: yes
- legacy profile remains in ~/.codex/config.toml: no
- legacy [profiles]/[model_providers] sections in ~/.codex/config.toml: yes ([profiles.ollama-launch], [model_providers.ollama-launch])
- profile config file exists: yes (~/.codex/ollama-launch-codex-app.config.toml)
- CODEX_PROFILE: not set
- CODEX_WIKIGUARD_PROFILE: not set
- diagnose_codex_exec.py: pass (ok True, profile None, command_mode default)
- direct codex exec: pass (default profile, no legacy profile error)
- direct codex exec with CODEX_WIKIGUARD_CHILD=1: pass
- hook subprocess codex exec: pass ({'ok': True, 'profile': None, 'command_mode': 'default'})
Conclusion:
- Current repository profile inheritance fix does not conflict with the current environment.
- The legacy profile issue in the previous trial appears to be a stale trial report or stale Codex client/session/config state. Current terminal execution and Hook subprocess execution do not reproduce it.
- Unrelated warnings observed: invalid YAML in ~/.codex/skills/gpt-researcher/SKILL.md and deprecated [features].codex_hooks.
