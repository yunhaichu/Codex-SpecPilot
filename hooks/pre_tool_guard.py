"""PreToolUse hook — blocks dangerous commands.

Intercepts Bash tool invocations and checks the command string against
a fixed denylist. Returns permissionDecision=deny for dangerous patterns.
"""
import json
import os
import re
import sys

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

REASON_TEMPLATE = "Blocked by Codex-WikiGuard: command matches denylist pattern '{}'"


def pre_tool_use(turn_payload):
    """Called before every tool invocation.

    Returns the Codex wire-format response.
    On denylist match: permissionDecision="deny" with reason.
    On no match: empty dict (allow through).
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

    for pattern in DENY_PATTERNS:
        if pattern.search(command):
            matched = pattern.pattern
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": REASON_TEMPLATE.format(matched),
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
