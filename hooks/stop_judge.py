"""StopJudge hook -- writes judgment on turn stop.

Calls codex exec (default model) for judgment.
Permission gate on auto-continue: checks next_action for dangerous ops.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from permission_policy import load_project_mode, _DANGEROUS_AUTO_ACTIONS
from codex_client import call_codex_default, check_auto_continue

WIKI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".project_wiki"
)

JUDGE_MD = os.path.join(WIKI_DIR, "JUDGE.md")
LATEST_CTX_MD = os.path.join(WIKI_DIR, "latest_context.md")
JUDGE_JSON = os.path.join(WIKI_DIR, "judge_latest.json")
LOOP_STATE_PATH = os.path.join(WIKI_DIR, "loop_state.json")

DEFAULT_VERDICT = "human_review"
DEFAULT_REASON = "Default conservative judgment in v2."
NEXT_ACTION = "manual review required before continuing"


def _read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "[file missing]"


def _is_dangerous_action(text):
    """Check if next_action involves dangerous operations."""
    if not text:
        return False
    text_lower = text.lower()
    for pat in _DANGEROUS_AUTO_ACTIONS:
        if pat.lower() in text_lower:
            return True
    return False


def _write_md(verdict, reason, assistant_msg, history, next_action_text):
    ts = datetime.now(timezone.utc).isoformat()
    na_display = next_action_text if next_action_text else "_none_"
    history_text = "\n".join(history)
    lines = [
        "# Codex-WikiGuard -- JUDGE",
        "",
        "## Latest Judgment",
        "",
        "**Timestamp**: %s" % ts,
        "",
        "**Verdict**: %s" % verdict,
        "",
        "**Reason**: %s" % reason,
        "",
        "## Assistant Message (last turn)",
        "",
        "```",
        assistant_msg,
        "```",
        "",
        "## Next Action",
        "",
        "| Note | Next action |",
        "|------|-------------|",
        "| _%s_ |" % na_display,
        "",
        "## History",
        "",
        history_text,
    ]
    with open(JUDGE_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_context_md(verdict, reason):
    md = "# Latest Judge Context\n\n"
    md += "VERDICT: %s\n" % verdict
    md += "AUTO_CONTINUE: disabled\n"
    md += "NEXT_ACTION: %s\n" % NEXT_ACTION
    md += "REASON: %s\n" % reason
    with open(LATEST_CTX_MD, "w", encoding="utf-8") as f:
        f.write(md)


def _write_json(verdict, reason, auto_continue, next_action, extra=None):
    data = {
        "last_verdict": verdict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "auto_continue": auto_continue,
        "next_action": next_action,
    }
    if extra:
        data.update(extra)
    with open(JUDGE_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _read_loop_state():
    try:
        with open(LOOP_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return int(data.get("loop_count", 0))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return 0


def _write_loop_state(count, auto_continue):
    data = {
        "loop_count": count,
        "auto_continue": auto_continue,
        "last_updated": None,
    }
    with open(LOOP_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _parse_llm_response(content):
    """Parse LLM JSON response."""
    if not content:
        return None
    content = content.strip()
    if "```" in content:
        for block in content.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                data = json.loads(block)
                return data
            except json.JSONDecodeError:
                continue
        return None
    try:
        data = json.loads(content)
        return data
    except json.JSONDecodeError:
        return None


def _is_permission_block(verdict, next_action, project_spec):
    """Check if auto-continue should be blocked by permission policy."""
    if not next_action:
        return True
    if _is_dangerous_action(next_action):
        return True
    mode = load_project_mode(project_spec)
    if mode == "supervised_project_development":
        lower_action = next_action.lower()
        if "hook" in lower_action or ".codex" in lower_action:
            return True
        if "修改 hooks" in next_action or "修改 .codex" in next_action:
            return True
    return False


def stop_judge(turn_payload):
    """Called when a Codex turn ends (Stop event)."""
    assistant_msg = turn_payload.get("last_assistant_message", "")
    if isinstance(assistant_msg, list):
        assistant_msg = "\n".join(
            m.get("content", "") if isinstance(m, dict) else str(m)
            for m in assistant_msg
        )

    # Read existing history from JUDGE.md
    history = []
    if os.path.isfile(JUDGE_MD):
        content = _read_file(JUDGE_MD)
        history_marker = "## History"
        if history_marker in content:
            history_text = content.split(history_marker, 1)[1]
            lines = [
                l.strip()
                for l in history_text.split("\n")
                if l.strip() and not l.strip().startswith("#")
            ]
            history = lines[:10]

    verdict = DEFAULT_VERDICT
    reason = DEFAULT_REASON
    next_action = ""
    auto_continue = False

    # Read project spec for permission checks
    project_spec_path = os.path.join(WIKI_DIR, "PROJECT_SPEC.md")
    project_spec = ""
    if os.path.isfile(project_spec_path):
        project_spec = _read_file(project_spec_path)

    # Try LLM judgment via codex exec
    llm_prompt = (
        "You are Codex-WikiGuard Stop Judge. Analyze the assistant message.\n"
        "Output ONLY JSON: {\n"
        '  "verdict": "pass | continue | revise | done | human_review",\n'
        '  "reason": "brief reason",\n'
        '  "next_action": "what to do next",\n'
        '  "auto_continue": true\n'
        "}\n"
        "Safety: if next_action modifies PROJECT_SPEC.md, RULES.md, DECISIONS.md,\n"
        "REJECTED.md, PERMISSIONS.md, JUDGE.md, judge_latest.json, latest_context.md,\n"
        "loop_state.json, guard_log.jsonl, .codex/hooks.json, hooks/*.py, .env, secrets,\n"
        "keys, deleting files, reset repository, deploy scripts, schema, or large refactor\n"
        "-> set verdict to human_review, auto_continue to false.\n"
        "Max 3 auto-continue loops.\n"
    )
    llm_result = call_codex_default(llm_prompt, timeout=120)
    parsed = None
    if llm_result.get("ok"):
        parsed = _parse_llm_response(llm_result.get("content", ""))

    if parsed and isinstance(parsed, dict):
        v = parsed.get("verdict", DEFAULT_VERDICT)
        if v in ("pass", "continue", "revise", "done", "human_review"):
            verdict = v
            reason = parsed.get("reason", DEFAULT_REASON)
            next_action = parsed.get("next_action", "")
        else:
            verdict = "human_review"
            reason = "LLM returned invalid verdict: %s" % v

    # Permission gate on auto-continue
    if verdict in ("continue", "revise"):
        if _is_permission_block(verdict, next_action, project_spec):
            auto_continue = False
            verdict = "human_review"
            reason = "permission policy blocked auto-continue: %s" % next_action
        else:
            lc_check = check_auto_continue(verdict)
            if lc_check.get("continue"):
                loop_count = _read_loop_state()
                _write_loop_state(loop_count + 1, True)
                auto_continue = True
            else:
                auto_continue = False
                verdict = "human_review"
                reason = "loop limit (3) reached, human_review required"
    else:
        _write_loop_state(0, False)

    _write_md(verdict, reason, assistant_msg, history, next_action)
    _write_context_md(verdict, reason)
    _write_json(verdict, reason, auto_continue, next_action)

    return {
        "systemMessage": "Codex-WikiGuard wrote %s judgment." % verdict,
    }


if __name__ == "__main__":
    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        try:
            payload = json.loads(stdin_data)
        except json.JSONDecodeError:
            payload = {}
    else:
        payload = {}

    result = stop_judge(payload)
    print(json.dumps(result, indent=2, ensure_ascii=False))
