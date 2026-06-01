"""Permission policy module for Codex SpecPilot.

Determines whether Codex Worker or a Hook may write to a given file path.
Uses Python standard library only. No LLM calls.
"""
import re
import os
import json
try:
    from project_paths import wiki_dir
except ModuleNotFoundError:
    from hooks.project_paths import wiki_dir


def _normalize_path(path):
    """Normalize paths from macOS, Linux, or Windows payloads to slash form."""
    return os.path.normpath(str(path)).replace("\\", "/").replace(os.sep, "/")


def _basename(path):
    return _normalize_path(path).rstrip("/").rsplit("/", 1)[-1]


# Supervision files that Codex Worker must not modify
_SUPERVISION_FILES = [
     "JUDGE.md",
     "latest_context.md",
     "judge_latest.json",
     "loop_state.json",
     "guard_log.jsonl",
     "specpilot_manifest.json",
     "WORKFLOW.md",
     "COMPLETION_REPORT_TEMPLATE.md",
     "PROJECT_SPEC.md",
     "RULES.md",
     "DECISIONS.md",
     "REJECTED.md",
     "PERMISSIONS.md",
]

# Always protected paths (credentials, infra, etc.)
_ALWAYS_PROTECTED_PATTERNS = [
    r"\.env($|\b|\.)",
    r"\.pem$",
    r"\.key$",
    r"id_rsa",
    r"id_ed25519",
    r"secrets\.",
    r"credentials\.",
    r"\.ssh/",
    r"deploy/",
    r"deployment/",
    r"schema/",
    r"migration/",
    r"migrations/",
    r"\.github/workflows/",
]

# Dangerous auto-continue actions that must always be blocked
_DANGEROUS_AUTO_ACTIONS = [
     "修改 PROJECT_SPEC",
     "修改 RULES",
     "修改 DECISIONS",
     "修改 REJECTED",
     "修改 PERMISSIONS",
     "修改 JUDGE",
     "修改 judge_latest",
     "修改 latest_context",
     "修改 loop_state",
     "修改 guard_log",
     "修改 .codex/hooks",
     "修改 hooks/",
     "修改 .env",
     "修改 secrets",
     "修改 keys",
     "删除文件",
     "reset",
     "大规模重构",
     "修改 deploy",
     "修改 schema",
     "修改 migration",
     "修改 migrations",
     "修改 hooks.json",
     "修改 hooks/*.py",
     "删除 .env",
     "删除 secrets",
     "删除 keys",
     "reset 仓库",
     "大规模重构",
]


SELF_DEV_MODE = "specpilot_self_development"
SUPERVISED_MODE = "supervised_project_development"


def load_project_mode(project_spec_text):
    """Return specpilot_self_development / supervised_project_development / unknown."""
    if not project_spec_text:
        return "unknown"
    if SELF_DEV_MODE in project_spec_text:
        return SELF_DEV_MODE
    if SUPERVISED_MODE in project_spec_text:
        return SUPERVISED_MODE
    return "unknown"


def is_supervision_file(path):
    """Check if path is a supervision file (task book, rules, hook config/log/state)."""
    normalized = _normalize_path(path)
    basename = _basename(path)
    for sf in _SUPERVISION_FILES:
        if basename == sf or normalized.endswith("/" + sf):
            return True
     # Also check for .codex/hooks.json
    if "hooks.json" in normalized and ".codex" in normalized:
        return True
     # Check for hooks/*.py
    if normalized.startswith("hooks/") and normalized.endswith(".py"):
        return True
    return False


def is_hook_state_file(path):
    """Check if path is a Stop Hook state file (JUDGE, latest_context, etc.)."""
    normalized = _normalize_path(path)
    basename = _basename(path)
    hook_state_names = [
         "JUDGE.md",
         "latest_context.md",
         "judge_latest.json",
         "loop_state.json",
         "guard_log.jsonl",
     ]
    for name in hook_state_names:
        if basename == name or normalized.endswith("/" + name):
            return True
    return False


def is_always_protected_path(path):
    """Check if path matches always-protected patterns (.env, keys, deploy, etc.)."""
    normalized = _normalize_path(path)
    for pat in _ALWAYS_PROTECTED_PATTERNS:
        if re.search(pat, normalized):
            return True
    return False


def _get_project_spec_path():
    """Return the path to PROJECT_SPEC.md if it exists."""
    path = os.path.join(wiki_dir(), "PROJECT_SPEC.md")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _is_allowed_in_self_dev(normalized, basename):
    """Check if path is allowed in specpilot_self_development mode."""
     # hooks/*.py, .codex/hooks.json, tests/*, README.md, INJECTION.md are allowed
    if normalized.startswith("hooks/") and normalized.endswith(".py"):
        return True
    if "hooks.json" in normalized and ".codex" in normalized:
        return True
    if normalized.startswith("tests/") or normalized == "tests.py":
        return True
    if basename == "README.md":
        return True
    if "INJECTION.md" in normalized:
        return True
    return False


def is_allowed_for_codex_worker(path, project_spec_text=None):
    """Determine if Codex Worker may write to this path.

    Returns (allowed: bool, reason: str).
    """
    if project_spec_text is None:
        project_spec_text = _get_project_spec_path()

    normalized = _normalize_path(path)
    basename = _basename(path)

     # Check supervision files first
    if is_supervision_file(path):
         # But allow self-dev exceptions
        if load_project_mode(project_spec_text) == SELF_DEV_MODE:
            if _is_allowed_in_self_dev(normalized, basename):
                return (True, "allowed in specpilot_self_development mode")
        return (False, "Codex Worker cannot modify supervision file: %s" % path)

     # Check always protected paths
    if is_always_protected_path(normalized):
        return (False, "Codex Worker cannot modify protected file/dir: %s" % path)

     # Check allowed scope in PROJECT_SPEC.md
    if "Allowed Scope" in project_spec_text:
        allowed_section = project_spec_text.split("Allowed Scope")[1].split("## ")[0]
        allowed_section_lower = allowed_section.lower()
         # If the path appears in allowed scope
        if basename.lower() in allowed_section_lower or normalized.lower() in allowed_section_lower:
            return (True, "explicitly allowed in PROJECT_SPEC.md Allowed Scope")
        # If directory path is in allowed scope
        for line in allowed_section.split("\n"):
            line = line.strip().strip("-*").strip()
            if line and (normalized.startswith(line.replace(".md", "").replace("/", "")) or
                         basename in line):
                return (True, "path found in PROJECT_SPEC.md Allowed Scope")

     # Check self-dev mode exceptions
    if load_project_mode(project_spec_text) == SELF_DEV_MODE:
        if _is_allowed_in_self_dev(normalized, basename):
            return (True, "allowed in specpilot_self_development mode")

     # Default: deny (conservative)
    return (False, "file not in Allowed Scope and not explicitly permitted")


def is_allowed_for_hook_writer(hook_name, path):
    """Determine if a Hook may write to this path.

    hook_name: UserPromptSubmit, PreToolUse, Stop
    """
    normalized = _normalize_path(path)
    basename = _basename(path)

    if hook_name == "UserPromptSubmit":
         # Read-only hook
        return (False, "UserPromptSubmit is read-only and cannot write any file")

    if hook_name == "PreToolUse":
         # Only guard_log.jsonl is writable
        if basename == "guard_log.jsonl" or normalized.endswith("/guard_log.jsonl"):
            return (True, "guard_log.jsonl is the only file PreToolUse may write")
        return (False, "PreToolUse may only write guard_log.jsonl, not %s" % path)

    if hook_name == "Stop":
        allowed_stop_files = [
             "JUDGE.md",
             "latest_context.md",
             "judge_latest.json",
             "loop_state.json",
             "PROGRESS.md",
             "COMPLETION_REPORT.md",
        ]
        for allowed in allowed_stop_files:
            if basename == allowed or normalized.endswith("/" + allowed):
                return (True, "%s is allowed for Stop hook" % allowed)
        return (False, "Stop hook cannot write %s" % path)

    return (False, "unknown hook name: %s" % hook_name)



def extract_paths_from_patch(patch_content):
    """Extract file paths from a patch/diff content."""
    paths = []
    # Match *** Update File: path
    for m in re.finditer(r"\*\*\*\s*Update\s+File:\s*(\S+)", patch_content):
        paths.append(m.group(1))
    # Match *** Add File: path
    for m in re.finditer(r"\*\*\*\s*Add\s+File:\s*(\S+)", patch_content):
        paths.append(m.group(1))
    # Match *** Delete File: path
    for m in re.finditer(r"\*\*\*\s*Delete\s+File:\s*(\S+)", patch_content):
        paths.append(m.group(1))
    # Match --- a/path
    for m in re.finditer(r"^---\s+a/(.+)$", patch_content, re.MULTILINE):
        paths.append(m.group(1))
    # Match +++ b/path
    for m in re.finditer(r"^\+\+\+\s+b/(.+)$", patch_content, re.MULTILINE):
        paths.append(m.group(1))
    return paths


def extract_paths_from_command(command):
    """Extract file paths from a Bash command using conservative heuristics."""
    paths = []
     # Match > path, >> path, 2> path
    for m in re.finditer(r'[>]{1,2}\s*(\S+)', command):
        p = m.group(1)
        if not p.startswith("http") and not p.startswith("pty"):
            paths.append(p)
     # Match cp/mv source/dest
    for m in re.finditer(r"\b(cp|mv|ln)\s+(?:-\w+\s+)*(.+)", command):
        parts = m.group(2).split()
        for p in parts:
            if not p.startswith("http") and not p.startswith("-"):
                paths.append(p)
     # Match -i '' 's/x/y/' pattern (sed -i)
    for m in re.finditer(r"sed\s+-i\s+['\"]?\s*['\"]?\s*(?:.\s*)?['\"]?([^'\s]+)", command):
        paths.append(m.group(1))
    return paths


def command_has_write_intent(command):
    """Check if command has write/delete/move/overwrite intent."""
    write_patterns = [
        r"\brm\s",
        r"\brm\s+-rf\b",
        r"\bmv\b",
        r"\bcp\b",
        r">\s*/",
        r">>\s",
        r"\btee\b",
        r"\bsed\s+-i\b",
        r"\bperl\s+-pi\b",
        r"\bpython\s+-c\b",
        r"\bpython3\s+-c\b",
        r"\btruncate\b",
     ]
    for pat in write_patterns:
        if re.search(pat, command):
            return True
    return False


def get_permission_summary():
    """Return a short permission summary for injection into Codex prompts."""
    return (
         "# Permission Summary (Codex SpecPilot)\n"
         "Codex Worker MUST NOT modify:\n"
         "- .project_wiki/PROJECT_SPEC.md, RULES.md, DECISIONS.md, REJECTED.md, PERMISSIONS.md\n"
         "- .project_wiki/JUDGE.md, latest_context.md, judge_latest.json,\n"
         "  loop_state.json, guard_log.jsonl, WORKFLOW.md, COMPLETION_REPORT_TEMPLATE.md\n"
         "- .codex/hooks.json, hooks/*.py (unless specpilot_self_development)\n"
         "- .env, secrets, keys, deploy/, schema/, migration/, migrations/\n"
         "Only modify files within Allowed Scope in PROJECT_SPEC.md."
     )
