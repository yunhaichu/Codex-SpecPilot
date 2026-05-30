"""PreToolUse hook — blocks dangerous commands and protected file operations.

Intercepts Bash tool invocations and checks:
1. Command denylist (rm -rf, sudo, git reset --hard, etc.)
2. Protected file names (env, pem, key, secrets, etc.)
3. Protected directories (deploy, migrations, .ssh, etc.)

Returns permissionDecision=deny on match, {} on pass.
On deny, appends a log line to .project_wiki/guard_log.jsonl.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

# --- Denylist patterns ---
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

# --- Protected file name patterns ---
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

# --- Protected directory/path fragments ---
PROTECTED_PATHS = [
    "deploy/",
    "deployment/",
    "migrations/",
    "migration/",
    "schema/",
    ".ssh/",
    ".github/workflows/",
]

# --- High-risk write/modify keywords ---
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

REASON_TEMPLATE = "Blocked by Codex-WikiGuard: {}"

# Guard log path
WIKI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".project_wiki"
)
GUARD_LOG = os.path.join(WIKI_DIR, "guard_log.jsonl")


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


def _has_protected_target(command):
    """Check if command targets a protected file or dir with a risky write op."""
    # Check for write operations
    has_write = any(p.search(command) for p in WRITE_OP_PATTERNS)
    if not has_write:
        return False

    # Check protected files
    for pat in PROTECTED_FILE_PATTERNS:
        if pat.search(command):
            return True

    # Check protected paths (substring match, case-sensitive)
    for protected in PROTECTED_PATHS:
        if protected in command:
            return True

    return False


def pre_tool_use(turn_payload):
    """Called before every tool invocation.

    Returns:
        Denylist hit: { "hookSpecificOutput": { ..., "permissionDecision": "deny", ... } }
        Protected file hit: same format
        Pass: {}
    """
    # Extract command from Codex wire format
    tool_input = turn_payload.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            tool_input = {}

    command = tool_input.get("command", "") or ""

    # Fallback: also check legacy arguments.command
    if not command:
        arguments = turn_payload.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {}
        command = arguments.get("command", "") or ""

    # 1. Check denylist
    for pattern in DENY_PATTERNS:
        if pattern.search(command):
            matched = pattern.pattern
            reason = REASON_TEMPLATE.format(
                f"command matches denylist pattern '{matched}'"
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
        reason = REASON_TEMPLATE.format(
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

    # No match — allow
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
