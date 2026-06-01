"""StopJudge hook -- AI controller for unattended task-book development."""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codex_client import call_codex_default
from project_paths import wiki_dir
from project_injector import bootstrap_wiki_files

WIKI_DIR = wiki_dir()

# Recursive guard: child codex exec processes must not judge or write state.
if os.environ.get("CODEX_SPECPILOT_CHILD") == "1":
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
VALID_VERDICTS = (
    "pass",
    "continue",
    "revise",
    "done",
    "human_review",
    "spec_update_required",
    "onboarding_required",
)
ONBOARDING_MARKER = "NEEDS_USER_CONFIRMATION"
ONBOARDING_DECISIONS = ("ask_user", "write_spec", "human_review")
REQUIRED_SPEC_TERMS = (
    "Project Mode",
    "Project Goal",
    "User Requirements",
    "Non-Goals",
    "Allowed Scope",
    "Protected Scope",
    "Development Plan",
    "Acceptance Criteria",
    "Stop Conditions",
    "Submission Requirements",
    "GitHub",
)


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


def _write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _ensure_project_wiki_files():
    bootstrap_wiki_files(os.path.dirname(WIKI_DIR), force=False)


def _project_spec_needs_onboarding(project_spec):
    if not project_spec or project_spec == "[file missing]":
        return True
    return ONBOARDING_MARKER in project_spec


def _validate_project_spec(text):
    missing = []
    if not text or not text.strip():
        return ["PROJECT_SPEC content"]
    for term in REQUIRED_SPEC_TERMS:
        if term not in text:
            missing.append(term)
    if "TASK-" not in text:
        missing.append("TASK-*")
    if ONBOARDING_MARKER in text:
        missing.append("complete PROJECT_SPEC without NEEDS_USER_CONFIRMATION")
    return missing


def _normalize_questions(value, limit=5):
    if not isinstance(value, list):
        return []
    questions = []
    for item in value:
        if isinstance(item, str) and item.strip():
            questions.append(item.strip())
        if len(questions) >= limit:
            break
    return questions


def _write_md(verdict, reason, assistant_msg, history, next_action_text, questions=None):
    ts = datetime.now(timezone.utc).isoformat()
    na_display = next_action_text if next_action_text else "_none_"
    history_text = "\n".join(history)
    md = "# Codex SpecPilot -- JUDGE\n\n"
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
    if questions:
        md += "## Questions For User\n\n"
        for question in questions:
            md += "- %s\n" % question
        md += "\n"
    md += "## History\n\n"
    md += history_text + "\n"
    with open(_wiki_path("JUDGE.md"), "w", encoding="utf-8") as f:
        f.write(md)


def _write_context_md(verdict, reason, next_action_text="", auto_continue=False, questions=None):
    md = "# Latest Judge Context\n\n"
    md += "VERDICT: %s\n" % verdict
    md += "AUTO_CONTINUE: %s\n" % ("enabled" if auto_continue else "disabled")
    md += "NEXT_ACTION: %s\n" % (next_action_text if next_action_text else NEXT_ACTION)
    md += "REASON: %s\n" % reason
    if questions:
        md += "QUESTIONS:\n"
        for question in questions:
            md += "- %s\n" % question
    with open(_wiki_path("latest_context.md"), "w", encoding="utf-8") as f:
        f.write(md)


def _write_json(verdict, reason, auto_continue, next_action, loop_count=0,
                llm_ok=False, llm_error=None, original_verdict=None,
                original_next_action=None, progress_made=None, questions=None):
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
    if progress_made is not None:
        data["progress_made"] = bool(progress_made)
    if questions:
        data["questions"] = questions
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


def _system_message(verdict, reason, next_action, questions=None):
    if verdict == "onboarding_required":
        msg = (
            "Codex SpecPilot needs project onboarding before worker development.\n"
            "Reason: %s\n"
            "Next action: %s"
            % (reason, next_action if next_action else "answer onboarding questions")
        )
        if questions:
            msg += "\nQuestions for the user:\n"
            for question in questions:
                msg += "- %s\n" % question
        return msg
    if verdict == "spec_update_required":
        msg = (
            "Codex SpecPilot requires a PROJECT_SPEC update before continuing.\n"
            "Reason: %s\n"
            "Next action: %s"
            % (reason, next_action if next_action else NEXT_ACTION)
        )
        if questions:
            msg += "\nQuestions for the user:\n"
            for question in questions:
                msg += "- %s\n" % question
        else:
            msg += (
                "\nNo questions were provided by the judge. Ask the user to confirm "
                "the goal change before running Spec Steward."
            )
        return msg
    if verdict == "human_review":
        return (
            "Codex SpecPilot requires human review before continuing.\n"
            "Reason: %s\n"
            "Next action: %s" % (reason, next_action if next_action else NEXT_ACTION)
        )
    return "Codex SpecPilot wrote %s judgment." % verdict


def _build_onboarding_prompt(project_spec, onboarding_doc, latest_ctx, assistant_msg):
    return (
        "You are Codex SpecPilot Onboarding Steward. Return ONLY JSON.\n"
        "The project has no complete task contract yet. Your job is to decide "
        "whether the last Codex response has enough confirmed information to "
        "write `.project_wiki/PROJECT_SPEC.md`, or whether the user must answer "
        "more questions.\n"
        "Schema: {\"decision\":\"ask_user|write_spec|human_review\","
        "\"reason\":\"brief\","
        "\"questions\":[\"question\"],"
        "\"updated_project_spec\":\"full markdown PROJECT_SPEC or empty\"}\n"
        "Rules:\n"
        "- Use only requirements confirmed in LAST_ASSISTANT_MESSAGE and the "
        "project snapshot; do not invent missing goals, stack, scope, or tests.\n"
        "- If Project Goal, Allowed Scope, Protected Scope, Development Plan, or "
        "Acceptance Criteria are missing or vague, return ask_user with up to 5 "
        "high-signal questions.\n"
        "- GitHub sync policy is required during onboarding. If the user does not "
        "need upload/sync, encode local-only. If GitHub sync is requested, ask for "
        "auth method without token/key text, repo owner/name, public/private "
        "visibility, and allowed push/tag/checkpoint behavior.\n"
        "- Do not request, write, or expose API keys, tokens, or secrets.\n"
        "- If enough information is confirmed, return write_spec with a complete "
        "PROJECT_SPEC containing sections 0 through 10 and TASK-* checklist items.\n"
        "- Codex Worker must not write PROJECT_SPEC.md directly; this Hook writes "
        "the accepted task contract.\n"
        "- Do not output code fences.\n\n"
        "CURRENT PROJECT_SPEC:\n```\n%s\n```\n"
        "PROJECT_ONBOARDING:\n```\n%s\n```\n"
        "LATEST_CONTEXT:\n```\n%s\n```\n"
        "LAST_ASSISTANT_MESSAGE:\n```\n%s\n```\n"
        % (
            project_spec[:3000],
            onboarding_doc[:3000],
            latest_ctx[:1000],
            assistant_msg[:4000],
        )
    )


def _handle_onboarding_stop(assistant_msg, history, project_spec, latest_ctx):
    onboarding_doc = _read_file(_wiki_path("PROJECT_ONBOARDING.md"))
    prompt = _build_onboarding_prompt(project_spec, onboarding_doc, latest_ctx, assistant_msg)
    llm_result = call_codex_default(prompt, timeout=120)
    llm_ok = False
    llm_error = None
    parsed = None
    if llm_result.get("ok"):
        llm_ok = True
        parsed = _parse_llm_response(llm_result.get("content", ""))
    else:
        llm_error = llm_result.get("error", "unknown error")

    if not isinstance(parsed, dict):
        verdict = "human_review"
        reason = "Onboarding Steward AI call failed or returned unparseable JSON: %s" % (
            llm_error or "no content"
        )
        next_action = "Ask the user to confirm project goal, allowed scope, protected scope, and validation."
        questions = []
        _write_loop_state(0, False, verdict)
        _write_json(verdict, reason, False, next_action,
                    loop_count=0, llm_ok=llm_ok, llm_error=llm_error)
        _write_md(verdict, reason, assistant_msg, history, next_action)
        _write_context_md(verdict, reason, next_action, auto_continue=False)
        return {"systemMessage": _system_message(verdict, reason, next_action)}

    decision = parsed.get("decision", "")
    questions = _normalize_questions(parsed.get("questions", []))
    if decision not in ONBOARDING_DECISIONS:
        verdict = "human_review"
        reason = "Onboarding Steward returned invalid decision: %s" % decision
        next_action = "Ask the user to answer onboarding questions."
    elif decision == "write_spec":
        updated_spec = parsed.get("updated_project_spec", "")
        missing = _validate_project_spec(updated_spec)
        if missing:
            verdict = "onboarding_required"
            reason = "Proposed PROJECT_SPEC is incomplete: %s" % ", ".join(missing[:5])
            next_action = "Ask the user for missing task-contract information."
            if not questions:
                questions = [
                    "项目最终目标是什么？",
                    "Codex 允许修改哪些具体文件或目录？",
                    "哪些文件或目录必须保护？",
                    "每个阶段完成后用什么方式验证？",
                    "是否需要 GitHub 同步？不需要则默认 local-only；需要则说明认证方式、公开/私有、仓库目标和允许的 push/tag/checkpoint 行为，不要提供 token 或密钥原文。",
                ]
        else:
            _write_file(_wiki_path("PROJECT_SPEC.md"), updated_spec.rstrip() + "\n")
            verdict = "pass"
            reason = parsed.get("reason", "PROJECT_SPEC was written by onboarding Hook.")
            next_action = "PROJECT_SPEC.md is ready. User can say 开始工作 to begin worker development."
            questions = []
    elif decision == "ask_user":
        verdict = "onboarding_required"
        reason = parsed.get("reason", "More project requirements are needed.")
        next_action = "Ask the user the onboarding questions."
    else:
        verdict = "human_review"
        reason = parsed.get("reason", "Onboarding requires human review.")
        next_action = "Review the project onboarding state."

    _write_loop_state(0, False, verdict)
    _write_json(verdict, reason, False, next_action,
                loop_count=0, llm_ok=llm_ok, llm_error=llm_error,
                questions=questions)
    _write_md(verdict, reason, assistant_msg, history, next_action, questions=questions)
    _write_context_md(verdict, reason, next_action, auto_continue=False, questions=questions)

    if verdict == "pass":
        return {
            "systemMessage": (
                "Codex SpecPilot wrote `.project_wiki/PROJECT_SPEC.md` from confirmed onboarding information.\n"
                "Next action: %s" % next_action
            )
        }
    return {"systemMessage": _system_message(verdict, reason, next_action, questions=questions)}


def stop_judge(turn_payload):
    """Called when a Codex turn ends (Stop event)."""
    _ensure_project_wiki_files()
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
    if _project_spec_needs_onboarding(project_spec):
        return _handle_onboarding_stop(assistant_msg, history, project_spec, latest_ctx)

    compact_project_spec = _compact_project_spec_for_stop(project_spec)

    # LLM judgment with compact real context. Keep this prompt light because
    # Stop hooks must finish inside Codex hook timeouts.
    llm_prompt = (
        "You are Codex SpecPilot Stop Judge. Return ONLY JSON.\n"
        "Schema: {\"verdict\":\"pass|continue|revise|done|human_review|spec_update_required\","
        "\"reason\":\"brief\",\"next_action\":\"action or empty\","
        "\"auto_continue\":true,\"progress_made\":true,"
        "\"questions\":[\"question for user\"]}\n"
        "Rules: done only when the whole PROJECT_SPEC is complete, including every "
        "Development Plan task and final acceptance criteria. If the last assistant "
        "message says one TASK is done and names another TASK as next step, verdict "
        "must be continue with that next task as next_action and auto_continue true. "
        "If the user changed project goals, scope, priorities, acceptance criteria, "
        "or asks to rewrite the task contract, verdict must be spec_update_required; "
        "set auto_continue false and next_action to the required PROJECT_SPEC / "
        "Development Plan update. For spec_update_required, include up to 5 concise "
        "questions the user must answer before Spec Steward can update the task contract. "
        "Set progress_made true when the last turn completed a task, passed validation, "
        "or advanced the project plan; set it false only when the loop is repeating "
        "without useful progress. "
        "pass is only for a no-op reply; continue/revise when work should proceed; "
        "human_review if unsafe or unclear. "
        "GitHub sync, push, tag, checkpoint, release marker, or remote operations "
        "must follow PROJECT_SPEC GitHub policy. If policy is local-only or missing, "
        "do not request remote GitHub actions. If policy allows sync and the current "
        "development node needs a checkpoint, next_action may request the allowed "
        "git/GitHub operation without exposing tokens or secrets. "
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
        if v in VALID_VERDICTS:
            verdict = v
            reason = parsed.get("reason", DEFAULT_REASON)
            next_action = parsed.get("next_action", "")
            llm_auto_continue = parsed.get("auto_continue", False)
            progress_made = bool(parsed.get("progress_made", False))
        else:
            verdict = "human_review"
            reason = "LLM returned invalid verdict: %s" % v
            next_action = ""
            llm_auto_continue = False
            progress_made = False
            questions = []
        if parsed and isinstance(parsed, dict):
            questions = _normalize_questions(parsed.get("questions", []))
    else:
        verdict = "human_review"
        reason = "LLM call failed or returned unparseable: %s" % (llm_error or "no content")
        next_action = ""
        llm_auto_continue = False
        progress_made = False
        questions = []

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
            effective_loop_count = 0 if progress_made else loop_count
            if effective_loop_count >= 3:
                can_continue = False
                verdict = "human_review"
                reason = "loop limit (3) reached without progress, human_review required"
            else:
                can_continue = True

    # Write state files
    if can_continue:
        loop_count = _read_loop_state()
        next_loop_count = 0 if progress_made else loop_count + 1
        _write_loop_state(next_loop_count, True, verdict)
        auto_continue = True
        reason_max = next_action[:1200] if next_action else "safe continue loop"
        _write_json(verdict, reason, auto_continue, next_action,
                    loop_count=next_loop_count, llm_ok=llm_ok, llm_error=llm_error,
                    progress_made=progress_made, questions=questions)
        _write_md(verdict, reason, assistant_msg, history, next_action, questions=questions)
        _write_context_md(verdict, reason, next_action, auto_continue=True, questions=questions)
        return {
            "decision": "block",
            "reason": reason_max,
        }

    if verdict in ("done", "pass", "human_review", "spec_update_required"):
        _write_loop_state(0, False, verdict)

    _write_json(verdict, reason, auto_continue, next_action,
                loop_count=0 if verdict in ("done", "pass", "human_review", "spec_update_required") else _read_loop_state(),
                llm_ok=llm_ok, llm_error=llm_error, progress_made=progress_made,
                questions=questions)
    _write_md(verdict, reason, assistant_msg, history, next_action, questions=questions)
    _write_context_md(verdict, reason, next_action, auto_continue=False, questions=questions)

    # When verdict is done, write completion report
    _write_completion_report(verdict, reason)

    return {
        "systemMessage": _system_message(verdict, reason, next_action, questions=questions),
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
