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
from permission_policy import (load_project_mode, is_supervision_file,
    is_always_protected_path, is_allowed_for_codex_worker,
    extract_paths_from_command, extract_paths_from_patch,
    command_has_write_intent)
from codex_client import call_codex_default

# --- Denylist patterns ---
DENYLIST = [
    r"rm\s+-rf\b", r"\bsudo\b", r"git\s+reset\s+--hard\b",
    r"git\s+clean\s+-fd\b", r"chmod\s+-R\b", r"chown\s+-R\b",
    r"curl\s+.*\|\s*sh\b", r"wget\s+.*\|\s*sh\b",
]
DENY_PATTERNS = [re.compile(p) for p in DENYLIST]

# --- Protected file name patterns ---
PROTECTED_FILES = [
    r"\.env\b", r"\.env\.", r"\.pem\b", r"\.key\b",
    r"\bid_rsa\b", r"\bid_ed25519\b", r"secrets\.",
    r"credentials\.", r"docker-compose\.yml\b",
]
PROTECTED_FILE_PATTERNS = [re.compile(p) for p in PROTECTED_FILES]

# --- Protected directory/path fragments ---
PROTECTED_PATHS = ["deploy/", "deployment/", "migrations/", "migration/",
                      "schema/", ".ssh/", ".github/workflows/"]

# --- High-risk write/modify keywords ---
WRITE_OPS = [r"\brm\b", r"\bmv\b", r"\bcp\b", r">>", r">",
             r"\btee\b", r"\bsed\s+-i\b", r"\bperl\s+-pi\b",
             r"\bpython\s+-c\b", r"\bpython3\s+-c\b"]
WRITE_OP_PATTERNS = [re.compile(p) for p in WRITE_OPS]

REASON_TEMPLATE = "Blocked by Codex-WikiGuard: %s"

# Guard log path
WIKI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".project_wiki"
)
GUARD_LOG = os.path.join(WIKI_DIR, "guard_log.jsonl")
PROJECT_SPEC_PATH = os.path.join(WIKI_DIR, "PROJECT_SPEC.md")

# Recursive guard: skip if child Codex process
if os.environ.get("CODEX_WIKIGUARD_CHILD") == "1":
    print(json.dumps({}, indent=2, ensure_ascii=False))
    sys.exit(0)


def _log_deny(cmd, reason):
    """Append a deny entry to guard_log.jsonl."""
    os.makedirs(WIKI_DIR, exist_ok=True)
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(),
              "command": cmd, "reason": reason}
    with open(GUARD_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_project_spec():
    if os.path.isfile(PROJECT_SPEC_PATH):
        with open(PROJECT_SPEC_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _extract_targets(turn_payload):
    """Extract file paths and tool name from any tool payload."""
    tool_name = (turn_payload.get("tool", "")
                 or turn_payload.get("tool_name", "")
                 or turn_payload.get("name", ""))
    command = ""
    file_paths = []

    tool_input = turn_payload.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError:
            tool_input = {}

    if isinstance(tool_input, dict):
        # Bash command
        if "command" in tool_input:
            command = tool_input.get("command", "")
            if command:
                file_paths.extend(extract_paths_from_command(command))

        # Apply patch / Write / Edit: extract from common fields
        for key in ("target_file", "path", "file_path", "filename", "file"):
            if key in tool_input:
                val = tool_input[key]
                if isinstance(val, str) and val not in file_paths:
                    file_paths.append(val)

        # Also check patch/content/diff fields
        for key in ("patch", "content", "diff"):
            if key in tool_input:
                val = tool_input[key]
                if isinstance(val, str):
                    file_paths.extend(extract_paths_from_patch(val))

        # Fallback: check arguments field too
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
                        if isinstance(val, str) and val not in file_paths:
                            file_paths.append(val)
                for key in ("patch", "content", "diff"):
                    if key in arguments:
                        val = arguments[key]
                        if isinstance(val, str):
                            file_paths.extend(extract_paths_from_patch(val))

    return tool_name, command, file_paths


def _has_protected_target(command):
    """Check if command targets a protected file or dir with a risky write op."""
    if not command:
        return False
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
    if file_paths:
        seen = set()
        for fp in file_paths:
            if fp in seen:
                continue
            seen.add(fp)
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
    return (False, "")


def _soft_judge(tool_name, command, file_paths, project_spec):
    """Call codex exec for soft judgment.

    Returns "allow", "deny", "human_review", or "skip".
    If codex exec fails, returns "deny" (conservative: fail closed).
    """
    perm_summary = ("# Permission Summary\n"
                       "Codex Worker must follow permissions in PROJECT_SPEC.md.\n")
    if file_paths:
        perm_summary += "Target paths: " + ", ".join(file_paths) + "\n"

    prompt = (
        "You are Codex-WikiGuard PreToolUse soft judge.\n"
        "PROJECT_SPEC.md content:\n```\n%s\n```\n\n"
        "Permission summary:\n%s\n\n"
        "Tool: %s\n"
        "Command: %s\n"
        "Target paths: %s\n\n"
        "Output ONLY a JSON object with these fields:\n"
        "{\n"
        '     "decision": "allow | deny | human_review",\n'
        '     "reason": "brief reason"\n'
        "}\n"
        "Rules:\n"
        "- If safe and within scope, return allow.\n"
        "- If modifies supervision files or is risky, return deny.\n"
        "- If uncertain, return human_review.\n"
        "- Do NOT execute commands, only judge them.\n"
        % (project_spec[:3000] if project_spec else "(no PROJECT_SPEC.md)",
           perm_summary, tool_name,
           command if command else "(file tool: " + ", ".join(file_paths) + ")",
           ", ".join(file_paths) if file_paths else "(no paths extracted)")
    )

    result = call_codex_default(prompt, timeout=120)
    # Conservative: if codex exec fails, treat as deny
    if not result.get("ok"):
        return "deny"
    content = result.get("content", "")
    if not content:
        return "deny"

    # Try to parse JSON
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            dec = data.get("decision", "")
            if dec in ("allow", "deny", "human_review"):
                return dec
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: try to find JSON in markdown code blocks
    if "```" in content:
        for block in content.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                data = json.loads(block)
                if isinstance(data, dict):
                    return data.get("decision", "deny")
            except (json.JSONDecodeError, ValueError):
                continue

    # Unparseable -> conservative deny
    return "deny"


def pre_tool_use(turn_payload):
    """Called before every tool invocation."""
    tool_name, command, file_paths = _extract_targets(turn_payload)

    # 0. If file tool (apply_patch/Edit/Write) but no paths parsed, deny
    if tool_name in ("apply_patch", "Edit", "Write"):
        if not file_paths:
            reason = REASON_TEMPLATE % (
                "cannot determine target path for %s write tool" % tool_name
            )
            _log_deny(tool_name, reason)
            return {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }}

    # 1. Check denylist (command only)
    if command:
        for pattern in DENY_PATTERNS:
            if pattern.search(command):
                matched = pattern.pattern
                reason = REASON_TEMPLATE % (
                    "command matches denylist pattern %r" % matched
                )
                _log_deny(command, reason)
                return {"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }}
                # 2. Check protected files/dirs with write ops
                if _has_protected_target(command):
                    reason = REASON_TEMPLATE % (
                        "command targets protected file/dir with risky write operation"
                    )
                    _log_deny(command, reason)
                    return {"hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }}

    # 3. Permission policy check
    project_spec = _read_project_spec()
    blocked, reason = _check_permission(command, file_paths, tool_name, project_spec)
    if blocked:
        _log_deny(command or tool_name, reason)
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}

    # 4. LLM soft judgment (only after hard rules + permission pass)
    #    codex exec failure -> conservative deny
    soft_decision = _soft_judge(tool_name, command, file_paths, project_spec)
    if soft_decision == "deny":
        _log_deny(command or tool_name, "LLM soft judge: deny")
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "LLM soft judge: deny",
        }}
    if soft_decision == "human_review":
        _log_deny(command or tool_name, "LLM soft judge: human_review")
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "LLM soft judge: human_review required",
        }}
    # soft_decision is "allow" -> allow
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
