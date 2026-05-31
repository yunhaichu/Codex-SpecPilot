"""Permission policy module for Codex WikiGuard.

Provides unified permission checks to prevent Codex Worker from
modifying its own supervision files (task book, rules, hooks,
judgments, audit logs).
"""
import json
import os
import re

# --- Supervision system files (Codex Worker CANNOT modify) ---
_SUPERVISION_FILES = frozenset([
      "JUDGE.md",
      "latest_context.md",
      "judge_latest.json",
      "loop_state.json",
      "guard_log.jsonl",
      "PERMISSIONS.md",
      "PROJECT_SPEC_TEMPLATE.md",
      "RULES.md",
      "DECISIONS.md",
      "REJECTED.md",
      "PROGRESS.md",
])

_SUPERVISION_DIRS = frozenset([
      ".codex",
      "hooks",
      ".project_wiki",
])

# --- Always protected paths ---
_ALWAYS_PROTECTED_PATHS = [
      ".env",
      ".env.",
      ".pem",
      ".key",
      "id_rsa",
      "id_ed25519",
      "secrets.",
      "credentials.",
      "docker-compose.yml",
      "deploy/",
      "deployment/",
      "migrations/",
      "migration/",
      "schema/",
      ".ssh/",
      ".github/workflows/",
]

_ALWAYS_PROTECTED_PATTERNS = [re.compile(p) for p in _ALWAYS_PROTECTED_PATHS]

# --- Dangerous auto-continue actions ---
_DANGEROUS_AUTO_ACTIONS = [
      "PROJECT_SPEC.md",
      "RULES.md",
      "DECISIONS.md",
      "REJECTED.md",
      "PERMISSIONS.md",
      "JUDGE.md",
      "judge_latest.json",
      "latest_context.md",
      "loop_state.json",
      "guard_log.jsonl",
      ".codex/hooks.json",
      "delete",
      "删除",
      "rm ",
      "reset",
      "refactor",
      "重构",
      "deploy/",
      "deployment/",
      "schema/",
      "migration/",
      "migrations/",
      ".env",
      "secrets",
      "credentials",
      ".pem",
      ".key",
]


def load_project_mode(project_spec_text):
     """Return wikiguard_self_development / supervised_project_development / unknown."""
     if not project_spec_text:
         return "unknown"
     if "wikiguard_self_development" in project_spec_text:
         return "wikiguard_self_development"
     if "supervised_project_development" in project_spec_text:
         return "supervised_project_development"
     return "unknown"


def _normalize_path(path):
     """Normalize a path for matching."""
     if not path:
         return path
     p = path.strip()
     if p.startswith("./"):
         p = p[2:]
     return p


def is_supervision_file(path):
     """判断是否属于任务书、规则、Hook 状态、Hook 日志、Hook 配置、Hook 程序."""
     normalized = _normalize_path(path)
     if normalized in _SUPERVISION_FILES:
         return True
     for supervised_dir in _SUPERVISION_DIRS:
         if normalized.startswith(supervised_dir + "/") or normalized.startswith(supervised_dir + os.sep):
             return True
     return False


def is_hook_state_file(path):
     """判断是否属于 JUDGE.md / latest_context.md / judge_latest.json / loop_state.json / guard_log.jsonl."""
     normalized = _normalize_path(path)
     return normalized in {"JUDGE.md", "latest_context.md", "judge_latest.json",
                             "loop_state.json", "guard_log.jsonl"}


def is_always_protected_path(path):
     """判断是否属于 .env / keys / secrets / deploy / schema / migrations 等绝对保护范围."""
     normalized = _normalize_path(path)
     for pat in _ALWAYS_PROTECTED_PATTERNS:
         if pat.search(normalized):
             return True
     return False


def is_allowed_for_codex_worker(path, project_spec_text):
     """判断 Codex Worker 是否允许修改该路径.
     返回 (allowed, reason)

     Permission priority:
     1. Always protected paths (env, keys, deploy, schema...) -> deny
     2. Hook state files (JUDGE, guard_log, etc.) -> always deny
     3. Check project mode:
        - wikiguard_self_development: allow hooks/, .codex/hooks.json, tests/, README.md, .project_wiki/INJECTION.md
        - supervised_project_development: deny hooks/, .codex/, supervise files
        - unknown: deny hidden/internal files
     4. Check Allowed Scope patterns in PROJECT_SPEC.md
     """
     normalized = _normalize_path(path)

     # 1. Always protected
     if is_always_protected_path(normalized):
         return (False, "always protected file/dir")

     # 2. Hook state files — always deny even in self-dev mode
     if is_hook_state_file(normalized):
         return (False, "hook state file protected even in self-dev mode")

     # 3. Check project mode FIRST
     mode = load_project_mode(project_spec_text)

     if mode == "wikiguard_self_development":
         # Allow: hooks, .codex/hooks.json, tests, README, INJECTION, PROJECT_SPEC
         allowed_prefixes = [
               "hooks/",
               "hooks" + os.sep,
               ".codex/hooks.json",
               "tests/",
               "tests" + os.sep,
               "README.md",
               ".project_wiki/INJECTION.md",
         ]
         for prefix in allowed_prefixes:
             if normalized == prefix or normalized.startswith(prefix):
                 return (True, "wikiguard_self_development allows %s" % normalized)

         # In self-dev mode, PROJECT_SPEC.md is allowed only if user explicitly
         # mentions modifying it (checked by caller or by spec content).
         # Here we allow it but note it should be user-requested.
         if normalized == "PROJECT_SPEC.md" or normalized.endswith("/PROJECT_SPEC.md"):
             return (True, "wikiguard_self_development allows PROJECT_SPEC.md")

         # Still deny other supervision files
         if is_supervision_file(normalized):
             return (False, "supervision file protected in self-dev mode: %s" % normalized)

     if mode == "supervised_project_development":
         # In supervised mode, hooks and .codex are always protected
         if normalized.startswith("hooks/") or normalized.startswith("hooks" + os.sep):
             return (False, "Codex Worker cannot modify hooks in supervised mode")
         if normalized.startswith(".codex/") or normalized.startswith(".codex" + os.sep):
             return (False, "Codex Worker cannot modify .codex in supervised mode")

     # 4. For supervised or unknown mode: check supervision files
     if mode == "supervised_project_development" or mode == "unknown":
         if is_supervision_file(normalized):
             return (False, "Codex Worker cannot modify supervision file: %s" % normalized)

     if mode == "supervised_project_development":
         # If no project_spec text, deny by default
         if not project_spec_text:
             return (False, "no Allowed Scope defined, deny by default")

     # 5. Check ALLOWED scope patterns in project spec
     if project_spec_text:
         allowed_patterns = [
               r"allowed\s*scope",
               r"允许\s*修改",
               r"allowed\s*\w*\s*file",
         ]
         for pat in allowed_patterns:
             if re.search(pat, project_spec_text, re.IGNORECASE):
                 if not normalized.startswith(".") and not normalized.startswith("_"):
                     return (True, "no explicit deny, business file allowed")

     # Default: deny for hidden/internal files in unknown/supervised mode
     if normalized.startswith(".") or normalized.startswith("_"):
         return (False, "hidden/internal file, no explicit Allowed Scope")

     return (True, "no explicit deny, business file allowed by default")


def is_allowed_for_hook_writer(hook_name, path):
     """判断指定 Hook 是否允许写指定路径.
     hook_name: UserPromptSubmit, PreToolUse, Stop
     返回 (allowed, reason)
     """
     normalized = _normalize_path(path)

     if hook_name == "UserPromptSubmit":
         return (False, "UserPromptSubmit is read-only, cannot write any file")

     if hook_name == "PreToolUse":
         if normalized == "guard_log.jsonl":
             return (True, "PreToolUse allowed to write guard_log.jsonl")
         return (False, "PreToolUse can only write guard_log.jsonl, not %s" % normalized)

     if hook_name == "Stop":
         allowed_files = {
               "JUDGE.md", "latest_context.md", "judge_latest.json",
               "loop_state.json", "PROGRESS.md",
         }
         if normalized in allowed_files:
             return (True, "Stop hook allowed to write %s" % normalized)
         return (False, "Stop hook cannot write %s" % normalized)

     return (False, "unknown hook name: %s" % hook_name)


def extract_paths_from_command(command):
     """从简单 Bash 命令中提取可能的路径."""
     paths = []
     patterns = [
           r">\s*(\S+)",
           r">\s*>\s*(\S+)",
           r">>(\s*)(\S+)",
           r"\brm\s+(?:-\S+\s+)*(\S+)",
           r"\bmv\s+\S+\s+(\S+)",
           r"\bcp\s+\S+\s+(\S+)",
           r"\btee\s+(\S+)",
           r"\bsed\s+-i[^']*'\s*(\S+)",
           r"\bperl\s+-pi\s*[^']*\s*'(\S+)",
           r"(\.\/)?([\w./\-]+\.(?:py|js|ts|md|json|yml|yaml|txt|html|css|sh|env|pem|key|yml))",
     ]
     for pat in patterns:
         matches = re.findall(pat, command)
         for m in matches:
             if isinstance(m, tuple):
                 p = m[-1]
             else:
                 p = m
             if p and not p.startswith("-") and not p.startswith("#"):
                 paths.append(p)
     return paths


def extract_paths_from_patch(patch_content):
     """从 patch/diff 内容中提取目标路径."""
     paths = []
     if not patch_content:
         return paths
     for line in patch_content.split("\n"):
         line = line.strip()
         # git diff style: +++ b/path or --- a/path
         if line.startswith("+++ b/") or line.startswith("+++ "):
             p = line[6:].strip()
             if p and not p.startswith("/dev/null"):
                 paths.append(p)
         elif line.startswith("--- a/"):
             p = line[6:].strip()
             if p and not p.startswith("/dev/null"):
                 paths.append(p)
     return paths


def command_has_write_intent(command):
     """判断命令是否有写入、删除、移动、覆盖、修改倾向."""
     write_patterns = [
           r">\s", r">\s*$", r">>\s",
           r"\brm\b", r"\bmv\b", r"\bcp\b",
           r"\btee\b", r"\bsed\s+-i\b", r"\bperl\s+-pi\b",
           r"\bpython\s+-c\b", r"\bpython3\s+-c\b",
           r"\btruncate\b", r">\s*/",
     ]
     for pat in write_patterns:
         if re.search(pat, command):
             return True
     return False


def get_permission_summary():
     """返回给 Codex Worker 的权限摘要 (用于注入)."""
     return (
          "# Permission Summary (Codex WikiGuard)\n"
          "Codex Worker MUST NOT modify:\n"
          "- .project_wiki/PROJECT_SPEC.md, RULES.md, DECISIONS.md, REJECTED.md, PERMISSIONS.md\n"
          "- .project_wiki/JUDGE.md, latest_context.md, judge_latest.json,\n"
          "  loop_state.json, guard_log.jsonl\n"
          "- .codex/hooks.json, hooks/*.py (unless wikiguard_self_development)\n"
          "- .env, secrets, keys, deploy/, schema/, migration/\n"
          "Only modify files within Allowed Scope in PROJECT_SPEC.md."
     )
