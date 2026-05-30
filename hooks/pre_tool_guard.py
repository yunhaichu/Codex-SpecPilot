"""PreToolUse hook — blocks dangerous commands.

Intercepts tool invocations and checks the command string against
a fixed denylist. Returns approved=false for dangerous patterns.
"""
import json
import os
import re

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

# Precompile for performance
DENY_PATTERNS = [re.compile(p) for p in DENYLIST]

REASON_TEMPLATE = "Blocked by Codex-WikiGuard: command matches denylist pattern '{}'"


def pre_tool_use(turn_payload):
    """Called before every tool invocation.
    
    Args:
        turn_payload: dict from Codex containing the tool call info.
                      Expected key: 'arguments' with a 'command' field,
                      or 'tool' indicating the tool name.
    
    Returns:
        dict with 'approved' (bool) and optional 'reason'.
    """
    # Extract command string from the payload
    arguments = turn_payload.get("arguments", {})
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {}
    
    command = arguments.get("command", "") or ""
    tool_name = turn_payload.get("tool", "") or turn_payload.get("tool_name", "")

    # Check against denylist
    for pattern in DENY_PATTERNS:
        if pattern.search(command):
            matched = pattern.pattern
            return {
                "approved": False,
                "reason": REASON_TEMPLATE.format(matched)
            }

    return {"approved": True}


if __name__ == "__main__":
    # Allow standalone test
    test_commands = [
        "rm -rf /tmp/test",
        "ls -la",
        "sudo apt install",
        "git reset --hard HEAD",
        "echo hello",
    ]
    for cmd in test_commands:
        result = pre_tool_use({"arguments": {"command": cmd}})
        print(f"  {cmd!s:40s} -> {result}")
