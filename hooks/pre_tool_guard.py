"""PreToolUse hook -- light tool gate for the SpecPilot judge system.

The goal is not to build a large hardcoded security engine. This hook keeps
Codex Worker away from the judge system and lets AI judge ordinary write intent.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from permission_policy import (load_project_mode, is_supervision_file,
    extract_paths_from_command, extract_paths_from_patch,
    command_has_write_intent)
from codex_client import call_codex_default
from project_paths import wiki_dir

REASON_TEMPLATE = "Blocked by Codex SpecPilot: %s"

# Guard log path
WIKI_DIR = wiki_dir()
GUARD_LOG = os.path.join(WIKI_DIR, "guard_log.jsonl")
PROJECT_SPEC_PATH = os.path.join(WIKI_DIR, "PROJECT_SPEC.md")

# Recursive guard: skip if child Codex process
if os.environ.get("CODEX_SPECPILOT_CHILD") == "1":
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

    def collect_from_mapping(data):
        paths = []
        patch_texts = []

        for key in ("target_file", "path", "file_path", "filename", "file"):
            val = data.get(key)
            if isinstance(val, str):
                paths.append(val)

        for key in ("patch", "content", "diff", "input", "text"):
            val = data.get(key)
            if isinstance(val, str):
                patch_texts.append(val)

        return paths, patch_texts

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
                if tool_name == "apply_patch":
                    file_paths.extend(extract_paths_from_patch(command))

        # Apply patch / Write / Edit: extract from common fields
        paths, patch_texts = collect_from_mapping(tool_input)
        file_paths.extend(paths)
        for text in patch_texts:
            file_paths.extend(extract_paths_from_patch(text))

        # Fallback: check arguments field too
        if not command:
            arguments = turn_payload.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            if isinstance(arguments, dict):
                paths, patch_texts = collect_from_mapping(arguments)
                file_paths.extend(paths)
                for text in patch_texts:
                    file_paths.extend(extract_paths_from_patch(text))

    deduped = []
    for path in file_paths:
        if path not in deduped:
            deduped.append(path)
    return tool_name, command, deduped


def _is_self_dev_allowed_supervision_target(path, project_spec):
    """Allow explicit SpecPilot self-development files in self-dev mode."""
    if load_project_mode(project_spec) != "specpilot_self_development":
        return False
    normalized = os.path.normpath(str(path)).replace("\\", "/").replace(os.sep, "/")
    basename = normalized.rstrip("/").rsplit("/", 1)[-1]
    if basename == "PROJECT_SPEC.md":
        return False
    if (normalized.startswith("hooks/") or "/hooks/" in normalized) and normalized.endswith(".py"):
        return True
    if normalized == ".codex/hooks.json" or normalized.endswith("/.codex/hooks.json"):
        return True
    return basename in {
        "PROJECT_SPEC_TEMPLATE.md",
        "COMPLETION_REPORT_TEMPLATE.md",
        "INJECTION.md",
    }


def _is_spec_steward_apply_command(command):
    normalized = (command or "").replace("\\", "/")
    return (
        "--apply" in normalized
        and (
            "hooks/spec_steward.py" in normalized
            or "-m hooks.spec_steward" in normalized
        )
    )


def _is_controlled_spec_steward_command(command):
    return (
        _is_spec_steward_apply_command(command)
        and "CODEX_SPECPILOT_STEWARD=1" in (command or "")
    )


def _check_judge_system_boundary(file_paths, project_spec):
    """Block Codex Worker from editing the judge system itself."""
    if file_paths:
        seen = set()
        for fp in file_paths:
            if fp in seen:
                continue
            seen.add(fp)
            if is_supervision_file(fp):
                if _is_self_dev_allowed_supervision_target(fp, project_spec):
                    continue
                return (True, "Codex Worker cannot modify judge system file: %s" % fp)
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
        "You are Codex SpecPilot PreToolUse soft judge.\n"
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

    # 1. Judge system boundary check. This is the minimal non-AI boundary.
    project_spec = _read_project_spec()
    if command and _is_spec_steward_apply_command(command):
        if _is_controlled_spec_steward_command(command):
            return {}
        reason = "PROJECT_SPEC updates must use the controlled Spec Steward write channel."
        _log_deny(command or tool_name, reason)
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}

    blocked, reason = _check_judge_system_boundary(file_paths, project_spec)
    if blocked:
        _log_deny(command or tool_name, reason)
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}
    if file_paths and all(
        is_supervision_file(fp) and _is_self_dev_allowed_supervision_target(fp, project_spec)
        for fp in file_paths
    ):
        return {}

    # 2. Read-only commands should not pay for an AI judgment.
    if command and not file_paths and not command_has_write_intent(command):
        return {}

    # 3. Ordinary write intent is judged by AI against PROJECT_SPEC.
    #    codex exec failure -> conservative deny.
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
