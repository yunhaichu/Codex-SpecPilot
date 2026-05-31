"""PreToolUse hook -- blocks dangerous commands and protected file operations.

Hard rules (denylist + protected files) have highest priority.
Permission policy checks run before LLM soft judgment.
LLM cannot override hard permission denies.

Hooks also cover: Bash, apply_patch, Edit, Write tool calls.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from permission_policy import (
    load_project_mode,
    is_supervision_file,
    is_hook_state_file,
    is_always_protected_path,
    is_allowed_for_codex_worker,
    extract_paths_from_command,
    command_has_write_intent,
)

DENYLIST = [
    r"rm\s+-rf\b",
    r"\bsudo\b",
    r"git\s+reset\s+--hard\b",
    r"git\s+clean\s+-fd\b",
    r"chmod\s+-R\b",
    r"chown\s+-R\b",
    r"curl\s+.*\|\s*sh\b",
    r"wget\s+.*\|\s*sh\b",
]
DENY_PATTERNS = [re.compile(p) for p in DENYLIST]

PROTECTED_FILES = [
    r"\.env\b",
    r"\.env\.",
    r"\.pem\b",
    r"\.key\b",
    r"\bid_rsa\b",
    r"\bid_ed25519\b",
    r"secrets\.",
    r"credentials\.",
    r"docker-compose\.yml\b",
]
PROTECTED_FILE_PATTERNS = [re.compile(p) for p in PROTECTED_FILES]

PROTECTED_PATHS = [
    "deploy/",
    "deployment/",
    "migrations/",
    "migration/",
    "schema/",
    ".ssh/",
    ".github/workflows/",
]

WRITE_OPS = [
    r"\brm\b",
    r"\bmv\b",
    r"\bcp\b",
    r">>",
    r">",
    r"\btee\b",
    r"\bsed\s+-i\b",
    r"\bperl\s+-pi\b",
    r"\bpython\s+-c\b",
    r"\bpython3\s+-c\b",
]
WRITE_OP_PATTERNS = [re.compile(p) for p in WRITE_OPS]

REASON_TEMPLATE = "Blocked by Codex-WikiGuard: %s"

WIKI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".project_wiki"
)
GUARD_LOG = os.path.join(WIKI_DIR, "guard_log.jsonl")
PROJECT_SPEC_PATH = os.path.join(WIKI_DIR, "PROJECT_SPEC.md")

if os.environ.get("CODEX_WIKIGUARD_CHILD") == "1":
    print(json.dumps({}, indent=2, ensure_ascii=False))
    sys.exit(0)


def _log_deny(command, reason):
    """Append a deny entry to guard_log.jsonl."""
    os.makedirs(WIKI_DIR, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "reason": reason,
    }
    with open(GUARD_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_project_spec():
    if os.path.isfile(PROJECT_SPEC_PATH):
        with open(PROJECT_SPEC_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _extract_targets_from_payload(turn_payload):
    """Extract file paths and tool name from any tool payload."""
    tool_name = (
        turn_payload.get("tool", "")
        or turn_payload.get("tool_name", "")
        or turn_payload.get("name", "")
    )
    command = ""
    file_paths = []

    tool_input = turn_payload.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            tool_input = {}

    if isinstance(tool_input, dict):
        if "command" in tool_input:
            command = tool_input.get("command", "")
            if command:
                file_paths.extend(extract_paths_from_command(command))

        for key in ("target_file", "path", "file_path", "filename", "file"):
            if key in tool_input:
                val = tool_input[key]
                if isinstance(val, str):
                    file_paths.append(val)

        if not command:
            arguments = turn_payload.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            if isinstance(arguments, dict):
                for key in ("target_file", "path", "file_path", "filename"):
                    if key in arguments:
                        val = arguments[key]
                        if isinstance(val, str):
                            file_paths.append(val)

    return tool_name, command, file_paths


def _has_protected_target(command):
    """Check if command targets a protected file or dir with a risky write op."""
    has_write = any(p.search(command) for p in WRITE_OP_PATTERNS)
    if not has_write:
        return False
    for pat in PROTECTED_FILE_PATTERNS:
        if pat.search(command):
            return True
    for protected in PROTECTED_PATHS:
        if protected in command:
            return True
    return False


def _check_permission(command, file_paths, tool_name, project_spec):
    """Check permission policy. Returns (blocked, reason) or (False, "")."""
    has_write = command_has_write_intent(command) if command else False

    if file_paths and has_write:
        for fp in file_paths:
            if is_always_protected_path(fp):
                return (True, "always protected file/dir: %s" % fp)
            if is_supervision_file(fp):
                return (True, "Codex Worker cannot modify supervision file: %s" % fp)
            mode = load_project_mode(project_spec)
            allowed, reason = is_allowed_for_codex_worker(fp, project_spec)
            if not allowed:
                return (True, "permission policy: %s" % reason)
            if mode == "supervised_project_development":
                if fp.startswith("hooks/") or fp.startswith(".codex/"):
                    return (True, "Codex Worker cannot modify hooks/.codex in supervised mode")

    if file_paths and not has_write:
        for fp in file_paths:
            if is_always_protected_path(fp):
                return (True, "always protected file/dir: %s" % fp)
            if is_supervision_file(fp):
                return (True, "Codex Worker cannot modify supervision file: %s" % fp)
            mode = load_project_mode(project_spec)
            allowed, reason = is_allowed_for_codex_worker(fp, project_spec)
            if not allowed:
                return (True, "permission policy: %s" % reason)

    return (False, "")


def pre_tool_use(turn_payload):
    """Called before every tool invocation."""
    tool_name, command, file_paths = _extract_targets_from_payload(turn_payload)

    # 1. Check denylist (command only)
    if command:
        for pattern in DENY_PATTERNS:
            if pattern.search(command):
                matched = pattern.pattern
                reason = REASON_TEMPLATE % (
                    "command matches denylist pattern '%s'" % matched
                )
                _log_deny(command, reason)
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }

        # 2. Check protected files/dirs with write ops
        if _has_protected_target(command):
            reason = REASON_TEMPLATE % (
                "command targets protected file/dir with risky write operation"
            )
            _log_deny(command, reason)
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }

    # 3. Permission policy check
    project_spec = _read_project_spec()
    blocked, reason = _check_permission(command, file_paths, tool_name, project_spec)
    if blocked:
        _log_deny(command or tool_name, reason)
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }

    # No match -- allow
    return {}


if __name__ == "__main__":
    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        try:
            payload = json.loads(stdin_data)
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = {}

    result = pre_tool_use(payload)
    print(json.dumps(result, indent=2, ensure_ascii=False))
