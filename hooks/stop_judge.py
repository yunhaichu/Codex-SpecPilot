"""StopJudge hook -- writes judgment on turn stop.

Calls codex exec (default model) for judgment.
Permission gate on auto-continue: checks next_action for dangerous ops.
Writes completion report when verdict is done.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from permission_policy import load_project_mode, _DANGEROUS_AUTO_ACTIONS
from codex_client import call_codex_default, _read_loop_state, _write_loop_state

WIKI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".project_wiki"
)

JUDGE_MD = os.path.join(WIKI_DIR, "JUDGE.md")
LATEST_CTX_MD = os.path.join(WIKI_DIR, "latest_context.md")
JUDGE_JSON = os.path.join(WIKI_DIR, "judge_latest.json")
LOOP_STATE_PATH = os.path.join(WIKI_DIR, "loop_state.json")
def _completion_report_path():
    return os.path.join(WIKI_DIR, "COMPLETION_REPORT.md")


def _completion_report_template_path():
    return os.path.join(WIKI_DIR, "COMPLETION_REPORT_TEMPLATE.md")

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
    md = "# Codex-WikiGuard -- JUDGE\n\n"
    md += "## Latest Judgment\n\n"
    md += "**Timestamp**: %s\n\n" % ts
    md += "**Verdict**: %s\n\n" % verdict
    md += "**Reason**: %s\n\n" % reason
    md += "## Assistant Message (last turn)\n\n"
    md += "```\n%s\n```\n\n" % (assistant_msg[:2000])
    md += "## Next Action\n\n"
    md += "| Note | Next action |\n"
    md += "|------|-------------|\n"
    md += "| _%s_ |\n\n" % na_display
    md += "## History\n\n"
    md += history_text + "\n"
    with open(JUDGE_MD, "w", encoding="utf-8") as f:
        f.write(md)


def _write_context_md(verdict, reason, next_action_text=""):
    md = "# Latest Judge Context\n\n"
    md += "VERDICT: %s\n" % verdict
    md += "AUTO_CONTINUE: disabled\n"
    md += "NEXT_ACTION: %s\n" % (next_action_text if next_action_text else NEXT_ACTION)
    md += "REASON: %s\n" % reason
    with open(LATEST_CTX_MD, "w", encoding="utf-8") as f:
        f.write(md)


def _write_json(verdict, reason, auto_continue, next_action, loop_count=0,
                llm_ok=False, llm_error=None, original_verdict=None, original_next_action=None):
    data = {
        "last_verdict": verdict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "auto_continue": auto_continue,
        "next_action": next_action,
        "loop_count": loop_count,
        "llm_ok": llm_ok,
    }
    if llm_error:
        data["raw_llm_error"] = llm_error[:500] if llm_error else None
    if original_verdict:
        data["original_verdict"] = original_verdict
    if original_next_action:
        data["original_next_action"] = original_next_action
    with open(JUDGE_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _write_completion_report(verdict, reason):
    """Write a done record into COMPLETION_REPORT.md if verdict is done."""
    if verdict != "done":
        return
    ts = datetime.now(timezone.utc).isoformat()
    if not _completion_report_path():
        if _completion_report_template_path():
            template = _read_file(COMPLETION_REPORT_TEMPLATE)
            with open(_completion_report_path(), "w", encoding="utf-8") as f:
                f.write(template)
        else:
            with open(_completion_report_path(), "w", encoding="utf-8") as f:
                f.write("# Completion Report\n\n_No completion report yet._\n")
    # Append done record
    record = (
        "\n## Stop Hook Done Record\n"
        "- Timestamp: %s\n"
        "- Verdict: done\n"
        "- Reason: %s\n"
        "- Next action: None (task complete)\n"
    ) % (ts, reason)
    with open(_completion_report_path(), "a", encoding="utf-8") as f:
        f.write(record)


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
    judge_md = _read_file(JUDGE_MD)
    for line in judge_md.split("\n"):
        if line.startswith("## History"):
            continue
        if line.startswith("- ") and len(history) > 0:
            history.append(line)
        elif not line.startswith("## ") and not line.startswith("# ") and history:
            if not line.strip():
                pass
            else:
                history.append(line)

    # Read PROJECT_SPEC and latest context for LLM prompt
    project_spec = _read_file(os.path.join(WIKI_DIR, "PROJECT_SPEC.md"))
    latest_ctx = _read_file(os.path.join(WIKI_DIR, "latest_context.md"))

    # LLM judgment with real context
    llm_prompt = (
        "You are Codex-WikiGuard Stop Judge. Analyze the assistant's last message\n"
        "and determine if the task is complete, needs revision, or should continue.\n\n"
        "PROJECT_SPEC.md:\n```\n%s\n```\n\n"
        "Latest judge context:\n```\n%s\n```\n\n"
        "Assistant's last message:\n```\n%s\n```\n\n"
        "Output ONLY a JSON object with these fields:\n"
        '{\n'
        '    "verdict": "pass | continue | revise | done | human_review",\n'
        '    "reason": "brief reason (one sentence)",\n'
        '    "next_action": "what the main Codex should do next, or empty if done/pass",\n'
        '    "auto_continue": true\n'
        "}\n"
           "- Safety rules (HIGH PRIORITY - override any other interpretation):\n"
           "- If the assistant's last message indicates it MODIFIED or WILL MODIFY\n"
           "  PROJECT_SPEC.md, RULES.md, DECISIONS.md, REJECTED.md, PERMISSIONS.md,\n"
           "  JUDGE.md, judge_latest.json, latest_context.md, loop_state.json,\n"
           "  guard_log.jsonl, .codex/hooks.json, hooks/*.py, .env, secrets, keys,\n"
           "  or mentions deleting files, resetting repository, modifying deploy scripts,\n"
           "  database schema, or large refactoring -> set verdict to human_review,\n"
           "  auto_continue to false. THIS RULE TAKES PRECEDENCE.\n"
           "- If next_action involves any of the above -> set verdict to human_review.\n"
           "- auto_continue is true ONLY if the action is safe business code development\n"
           "  within the Allowed Scope of PROJECT_SPEC.md.\n"
           "- Max 3 auto-continue loops. If loop limit reached, set human_review.\n"
           "- If the assistant's message indicates task is complete, set verdict to done.\n"
           "- If the assistant's message is just a reply with no actionable task, set verdict to pass.\n"
             "" % (
            project_spec[:3000] if project_spec else "(no PROJECT_SPEC.md)",
            latest_ctx[:1000] if latest_ctx else "(no latest_context.md)",
            assistant_msg[:3000],
        )
    )
    llm_result = call_codex_default(llm_prompt, timeout=120)
    llm_ok = False
    llm_error = None
    parsed = None
    if llm_result.get("ok"):
        llm_ok = True
        parsed = _parse_llm_response(llm_result.get("content", ""))
    else:
        llm_error = llm_result.get("error", "unknown error")

    if parsed and isinstance(parsed, dict):
        v = parsed.get("verdict", DEFAULT_VERDICT)
        if v in ("pass", "continue", "revise", "done", "human_review"):
            verdict = v
            reason = parsed.get("reason", DEFAULT_REASON)
            next_action = parsed.get("next_action", "")
            llm_auto_continue = parsed.get("auto_continue", False)
        else:
            verdict = "human_review"
            reason = "LLM returned invalid verdict: %s" % v
            next_action = ""
            llm_auto_continue = False
    else:
        verdict = "human_review"
        reason = "LLM call failed or returned unparseable: %s" % (llm_error or "no content")
        next_action = ""
        llm_auto_continue = False

    # Permission gate on auto-continue
    can_continue = False
    auto_continue = False
    if verdict in ("continue", "revise") and llm_auto_continue:
        if _is_permission_block(verdict, next_action, project_spec):
            can_continue = False
            verdict = "human_review"
            reason = "permission policy blocked auto-continue: %s" % next_action
        else:
            loop_count = _read_loop_state()
            if loop_count >= 3:
                can_continue = False
                verdict = "human_review"
                reason = "loop limit (3) reached, human_review required"
            else:
                can_continue = True

    # Write state files
    if can_continue:
        loop_count = _read_loop_state()
        _write_loop_state(loop_count + 1, True, verdict)
        auto_continue = True
        reason_max = next_action[:1200] if next_action else "safe continue loop"
        _write_json(verdict, reason, auto_continue, next_action,
                    loop_count=loop_count + 1, llm_ok=llm_ok, llm_error=llm_error)
        _write_md(verdict, reason, assistant_msg, history, next_action)
        _write_context_md(verdict, reason, next_action)
        return {
            "decision": "block",
            "reason": reason_max,
        }

    if verdict in ("done", "pass", "human_review"):
        _write_loop_state(0, False, verdict)

    _write_json(verdict, reason, auto_continue, next_action,
                loop_count=0 if verdict in ("done", "pass", "human_review") else _read_loop_state(),
                llm_ok=llm_ok, llm_error=llm_error)
    _write_md(verdict, reason, assistant_msg, history, next_action)
    _write_context_md(verdict, reason, next_action)

    # When verdict is done, write completion report
    _write_completion_report(verdict, reason)

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
