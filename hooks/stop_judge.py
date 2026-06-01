"""StopJudge hook -- AI controller for unattended task-book development."""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codex_client import call_codex_default
from project_paths import wiki_dir

WIKI_DIR = wiki_dir()

# Recursive guard: child codex exec processes must not judge or write state.
if os.environ.get("CODEX_WIKIGUARD_CHILD") == "1":
    print(json.dumps({}, indent=2, ensure_ascii=False))
    sys.exit(0)

JUDGE_MD = os.path.join(WIKI_DIR, "JUDGE.md")
LATEST_CTX_MD = os.path.join(WIKI_DIR, "latest_context.md")
JUDGE_JSON = os.path.join(WIKI_DIR, "judge_latest.json")
LOOP_STATE_PATH = os.path.join(WIKI_DIR, "loop_state.json")


def _wiki_path(filename):
    return os.path.join(WIKI_DIR, filename)


def _completion_report_path():
    return _wiki_path("COMPLETION_REPORT.md")


def _completion_report_template_path():
    return _wiki_path("COMPLETION_REPORT_TEMPLATE.md")

DEFAULT_VERDICT = "human_review"
DEFAULT_REASON = "Default conservative judgment in v2."
NEXT_ACTION = "manual review required before continuing"


def _read_loop_state():
    try:
        with open(_wiki_path("loop_state.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("loop_count", 0))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return 0


def _write_loop_state(count, auto_continue, verdict="human_review"):
    data = {
        "loop_count": count,
        "auto_continue": auto_continue,
        "last_verdict": verdict,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(_wiki_path("loop_state.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "[file missing]"


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
    with open(_wiki_path("JUDGE.md"), "w", encoding="utf-8") as f:
        f.write(md)


def _write_context_md(verdict, reason, next_action_text="", auto_continue=False):
    md = "# Latest Judge Context\n\n"
    md += "VERDICT: %s\n" % verdict
    md += "AUTO_CONTINUE: %s\n" % ("enabled" if auto_continue else "disabled")
    md += "NEXT_ACTION: %s\n" % (next_action_text if next_action_text else NEXT_ACTION)
    md += "REASON: %s\n" % reason
    with open(_wiki_path("latest_context.md"), "w", encoding="utf-8") as f:
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
    with open(_wiki_path("judge_latest.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _write_completion_report(verdict, reason):
    """Write a done record into COMPLETION_REPORT.md if verdict is done."""
    if verdict != "done":
        return
    ts = datetime.now(timezone.utc).isoformat()
    report_path = _completion_report_path()
    if not os.path.exists(report_path):
        template_path = _completion_report_template_path()
        if os.path.exists(template_path):
            initial_content = _read_file(template_path)
        else:
            initial_content = "# Completion Report\n\n_No completion report yet._\n"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(initial_content)
    # Append done record
    record = (
        "\n## Stop Hook Done Record\n"
        "- Timestamp: %s\n"
        "- Verdict: done\n"
        "- Reason: %s\n"
        "- Next action: None (task complete)\n"
    ) % (ts, reason)
    with open(report_path, "a", encoding="utf-8") as f:
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


def _slice_section(text, start_term, end_terms):
    lower = text.lower()
    start = lower.find(start_term.lower())
    if start < 0:
        return ""
    end = len(text)
    for term in end_terms:
        idx = lower.find(term.lower(), start + len(start_term))
        if idx >= 0 and idx < end:
            end = idx
    return text[start:end].strip()


def _compact_project_spec_for_stop(project_spec, limit=6000):
    """Keep Stop context focused on the task contract, not the whole document."""
    if not project_spec:
        return "(no PROJECT_SPEC.md)"

    pieces = []
    for title, start, ends in (
        ("Project Mode", "0. Project Mode", ("1. Project Goal",)),
        ("Project Goal", "1. Project Goal", ("2. Background",)),
        ("Development Plan", "7. Development Plan", ("8. Acceptance Criteria",)),
        ("Acceptance Criteria", "8. Acceptance Criteria", ("9. Stop Conditions",)),
        ("Stop Conditions", "9. Stop Conditions", ("10. Submission Requirements",)),
    ):
        section = _slice_section(project_spec, start, ends)
        if section:
            pieces.append("## %s\n%s" % (title, section))

    if not pieces:
        return project_spec[:limit]

    compact = "\n\n".join(pieces)
    if len(compact) > limit:
        return compact[:limit] + "\n[PROJECT_SPEC compact context truncated]"
    return compact


def _is_permission_block(verdict, next_action, project_spec):
    """Keep the auto-continue gate mechanical.

    Direction and risk judgment belongs to the AI judge. This gate only ensures
    there is an actionable next step to send back to the main Codex loop.
    """
    return not bool(next_action and next_action.strip())


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
    judge_md = _read_file(_wiki_path("JUDGE.md"))
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
    project_spec = _read_file(_wiki_path("PROJECT_SPEC.md"))
    latest_ctx = _read_file(_wiki_path("latest_context.md"))
    compact_project_spec = _compact_project_spec_for_stop(project_spec)

    # LLM judgment with compact real context. Keep this prompt light because
    # Stop hooks must finish inside Codex hook timeouts.
    llm_prompt = (
        "You are Codex-WikiGuard Stop Judge. Return ONLY JSON.\n"
        "Schema: {\"verdict\":\"pass|continue|revise|done|human_review\","
        "\"reason\":\"brief\",\"next_action\":\"action or empty\","
        "\"auto_continue\":true}\n"
        "Rules: done only when the whole PROJECT_SPEC is complete, including every "
        "Development Plan task and final acceptance criteria. If the last assistant "
        "message says one TASK is done and names another TASK as next step, verdict "
        "must be continue with that next task as next_action and auto_continue true. "
        "pass is only for a no-op reply; continue/revise when work should proceed; "
        "human_review if unsafe or unclear. "
        "Worker must not edit judge-system files: PROJECT_SPEC, RULES, PERMISSIONS, "
        "JUDGE, latest_context, judge_latest, loop_state, guard_log, .codex/hooks.json, hooks/*.py.\n"
        "PROJECT_SPEC:\n```\n%s\n```\n"
        "LATEST_CONTEXT:\n```\n%s\n```\n"
        "LAST_ASSISTANT_MESSAGE:\n```\n%s\n```\n"
        % (
            compact_project_spec,
            latest_ctx[:300] if latest_ctx else "(no latest_context.md)",
            assistant_msg[:1200],
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
        _write_context_md(verdict, reason, next_action, auto_continue=True)
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
    _write_context_md(verdict, reason, next_action, auto_continue=False)

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
