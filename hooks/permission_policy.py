"""Small boundary helpers for Codex SpecPilot hooks.

PreToolUse is intentionally not a full permission engine. It uses this module
only to recognize judge-system files, extract likely target paths, and skip AI
judgment for obvious read-only commands.
"""
import re
import os


def _normalize_path(path):
    """Normalize paths from macOS, Linux, or Windows payloads to slash form."""
    return os.path.normpath(str(path)).replace("\\", "/").replace(os.sep, "/")


def _basename(path):
    return _normalize_path(path).rstrip("/").rsplit("/", 1)[-1]


def _clean_path_token(token):
    return str(token).strip().strip("'\"")


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
    if (
        normalized.startswith("hooks/") or "/hooks/" in normalized
    ) and normalized.endswith(".py"):
        return True
    return False


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
        p = _clean_path_token(m.group(1))
        if not p.startswith("http") and not p.startswith("pty"):
            paths.append(p)
    # Match cp/mv source/dest
    for m in re.finditer(r"\b(cp|mv|ln)\s+(?:-\w+\s+)*(.+)", command, re.IGNORECASE):
        parts = m.group(2).split()
        for p in parts:
            p = _clean_path_token(p)
            if not p.startswith("http") and not p.startswith("-"):
                paths.append(p)
    # Match common Windows PowerShell/CMD write commands.
    for m in re.finditer(
        r"\b(?:Set-Content|Add-Content|Out-File|New-Item|Remove-Item|del|erase)\b"
        r"(?:\s+-\w+)*\s+(\S+)",
        command,
        re.IGNORECASE,
    ):
        p = _clean_path_token(m.group(1))
        if not p.startswith("http") and not p.startswith("-"):
            paths.append(p)
    for m in re.finditer(
        r"\b(?:Move-Item|Copy-Item|copy|move)\b(?:\s+-\w+)*\s+(.+)",
        command,
        re.IGNORECASE,
    ):
        for p in m.group(1).split():
            p = _clean_path_token(p)
            if not p.startswith("http") and not p.startswith("-"):
                paths.append(p)
    # Match -i '' 's/x/y/' pattern (sed -i)
    for m in re.finditer(r"sed\s+-i\s+['\"]?\s*['\"]?\s*(?:.\s*)?['\"]?([^'\s]+)", command):
        paths.append(_clean_path_token(m.group(1)))
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
        r"\bdel\b",
        r"\berase\b",
        r"\bcopy\b",
        r"\bmove\b",
        r"\bset-content\b",
        r"\badd-content\b",
        r"\bout-file\b",
        r"\bnew-item\b",
        r"\bremove-item\b",
        r"\bmove-item\b",
        r"\bcopy-item\b",
    ]
    for pat in write_patterns:
        if re.search(pat, command, re.IGNORECASE):
            return True
    return False
