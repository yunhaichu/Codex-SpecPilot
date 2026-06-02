"""StopJudge hook -- AI controller for unattended task-book development."""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codex_client import call_codex_default
from project_paths import wiki_dir
from project_injector import ensure_runtime_files
from secret_scan import find_secret_material
import spec_steward

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
MAX_EXPERIENCE_EVALUATIONS = 3
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
EXPERIENCE_EVALUATION_DECISIONS = (
    "final_done",
    "spec_update_required",
    "human_review",
)
REMOTE_GITHUB_ACTION_PATTERNS = {
    "push": ("push", "git push"),
    "tag": ("tag", "git tag"),
    "release": ("release",),
    "repo": (
        "create repo",
        "create repository",
        "gh repo",
        "repository creation",
        "new repository",
        "创建仓库",
    ),
    "pr": ("pull request", "open pr", "create pr", "gh pr"),
    "checkpoint": (
        "github checkpoint",
        "remote checkpoint",
        "checkpoint to github",
        "github marker",
        "remote marker",
    ),
}
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
ONBOARDING_REQUIRED_SPEC_TERMS = (
    "Project Goal",
    "Allowed Scope",
    "Protected Scope",
    "Development Plan",
    "Acceptance Criteria",
    "TASK-",
)


def _read_loop_state():
    data = _read_loop_state_data()
    try:
        return int(data.get("loop_count", 0))
    except (ValueError, TypeError):
        return 0


def _read_loop_state_data():
    try:
        with open(_wiki_path("loop_state.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _read_experience_evaluation_count():
    data = _read_loop_state_data()
    try:
        return int(data.get("experience_evaluation_count", 0))
    except (ValueError, TypeError):
        return 0


def _write_loop_state(count, auto_continue, verdict="human_review",
                      experience_evaluation_count=None):
    existing = _read_loop_state_data()
    data = {
        "loop_count": count,
        "auto_continue": auto_continue,
        "last_verdict": verdict,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if experience_evaluation_count is None:
        if "experience_evaluation_count" in existing:
            data["experience_evaluation_count"] = existing.get("experience_evaluation_count", 0)
    else:
        data["experience_evaluation_count"] = experience_evaluation_count
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
    ensure_runtime_files(os.path.dirname(WIKI_DIR), force=False)


def _sync_spec_steward_paths():
    spec_steward.WIKI_DIR = WIKI_DIR
    spec_steward.PROJECT_SPEC_PATH = _wiki_path("PROJECT_SPEC.md")
    spec_steward.LATEST_CONTEXT_PATH = _wiki_path("latest_context.md")


def _project_spec_needs_onboarding(project_spec):
    if not project_spec or project_spec == "[file missing]":
        return True
    if ONBOARDING_MARKER in project_spec:
        return True
    return any(term not in project_spec for term in ONBOARDING_REQUIRED_SPEC_TERMS)


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
    secret_findings = find_secret_material(text)
    for finding in secret_findings:
        missing.append("secret material: %s" % finding)
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


def _normalize_text_list(value, limit=8):
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            parts = []
            for key in ("title", "issue", "impact", "recommendation", "reason"):
                part = item.get(key)
                if isinstance(part, str) and part.strip():
                    parts.append(part.strip())
            text = " - ".join(parts)
        else:
            text = str(item).strip()
        if text:
            items.append(text)
        if len(items) >= limit:
            break
    return items


def _format_experience_evaluation(evaluation):
    if not evaluation:
        return ""
    lines = [
        "## Experience Evaluation",
        "",
        "- Status: %s" % evaluation.get("status", "unknown"),
        "- Decision: %s" % evaluation.get("decision", "unknown"),
        "- Reason: %s" % evaluation.get("reason", ""),
    ]
    findings = evaluation.get("findings") or []
    if findings:
        lines.extend(["", "### Findings", ""])
        for item in findings:
            lines.append("- %s" % item)
    filtered = evaluation.get("filtered_findings") or []
    if filtered:
        lines.extend(["", "### Filtered Suggestions", ""])
        for item in filtered:
            lines.append("- %s" % item)
    change_request = evaluation.get("change_request", "")
    if change_request:
        lines.extend(["", "### Spec Update Request", "", change_request])
    lines.append("")
    return "\n".join(lines)


def _write_md(verdict, reason, assistant_msg, history, next_action_text, questions=None,
              experience_evaluation=None):
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
    evaluation_md = _format_experience_evaluation(experience_evaluation)
    if evaluation_md:
        md += evaluation_md + "\n"
    md += "## History\n\n"
    md += history_text + "\n"
    with open(_wiki_path("JUDGE.md"), "w", encoding="utf-8") as f:
        f.write(md)


def _write_context_md(verdict, reason, next_action_text="", auto_continue=False, questions=None):
    if next_action_text:
        next_action_display = next_action_text
    elif verdict == "done":
        next_action_display = "None (task complete)"
    else:
        next_action_display = NEXT_ACTION
    md = "# Latest Judge Context\n\n"
    md += "VERDICT: %s\n" % verdict
    md += "AUTO_CONTINUE: %s\n" % ("enabled" if auto_continue else "disabled")
    md += "NEXT_ACTION: %s\n" % next_action_display
    md += "REASON: %s\n" % reason
    if questions:
        md += "QUESTIONS:\n"
        for question in questions:
            md += "- %s\n" % question
    with open(_wiki_path("latest_context.md"), "w", encoding="utf-8") as f:
        f.write(md)


def _write_json(verdict, reason, auto_continue, next_action, loop_count=0,
                llm_ok=False, llm_error=None, original_verdict=None,
                original_next_action=None, progress_made=None, questions=None,
                experience_evaluation=None):
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
    if experience_evaluation:
        data["experience_evaluation"] = experience_evaluation
    with open(_wiki_path("judge_latest.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _write_completion_report(verdict, reason, experience_evaluation=None):
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
    evaluation_md = _format_experience_evaluation(experience_evaluation)
    if evaluation_md:
        record += "\n" + evaluation_md
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


def _github_policy_section(project_spec):
    section = _slice_section(
        project_spec,
        "GitHub Sync Policy",
        ("## 10. Submission Requirements", "## 10.", "10. Submission Requirements"),
    )
    if section:
        return section
    if "GitHub" in project_spec:
        return project_spec
    return ""


def _remote_github_actions(next_action):
    text = (next_action or "").lower()
    actions = []
    for action, patterns in REMOTE_GITHUB_ACTION_PATTERNS.items():
        for pattern in patterns:
            if pattern in text:
                actions.append(action)
                break
    return actions


def _has_unavailable_credentials(policy_text):
    lower = policy_text.lower()
    unavailable_terms = (
        "credential unavailable",
        "credentials unavailable",
        "credential missing",
        "credentials missing",
        "auth unavailable",
        "authentication unavailable",
        "not authenticated",
        "unauthenticated",
        "凭据不可用",
        "凭据缺失",
        "认证失败",
        "未认证",
    )
    return any(term in lower for term in unavailable_terms)


def _is_local_only_policy(policy_text):
    lower = policy_text.lower()
    return "local-only" in lower or "no push" in lower or "no remote" in lower


def _policy_has_required_sync_fields(policy_text):
    lower = policy_text.lower()
    has_account = (
        "github account" in lower
        or "account:" in lower
        or "账号" in policy_text
        or "账户" in policy_text
    )
    has_auth = (
        "auth method" in lower
        or "credential" in lower
        or "gh cli" in lower
        or "认证方式" in policy_text
    )
    has_credentials = (
        "credentials:" in lower
        or "credential status" in lower
        or "凭据" in policy_text
        or "认证状态" in policy_text
    )
    has_repo = "repository" in lower or "repo" in lower or "仓库" in policy_text
    has_repo_creation = (
        "existing repository" in lower
        or "new repository" in lower
        or "create repository" in lower
        or "repository creation" in lower
        or "allow creating" in lower
        or "must use existing" in lower
        or "已有仓库" in policy_text
        or "既有仓库" in policy_text
        or "新建仓库" in policy_text
        or "允许创建" in policy_text
        or "必须使用已有" in policy_text
    )
    has_visibility = (
        "public" in lower
        or "private" in lower
        or "公开" in policy_text
        or "私有" in policy_text
    )
    has_marker_nodes = (
        "marker" in lower
        or "checkpoint" in lower
        or "commit" in lower
        or "push" in lower
        or "tag" in lower
        or "release" in lower
        or "节点" in policy_text
        or "检查点" in policy_text
    )
    has_allowed_ops = (
        "allowed automatic operations" in lower
        or "automatic operations" in lower
        or "auto operations" in lower
        or "human confirmation" in lower
        or "允许自动" in policy_text
        or "人工确认" in policy_text
    )
    return all((
        has_account,
        has_auth,
        has_credentials,
        has_repo,
        has_repo_creation,
        has_visibility,
        has_marker_nodes,
        has_allowed_ops,
    ))


def _operation_requires_human_confirmation(policy_text, action):
    lower = policy_text.lower()
    confirmation_terms = (
        "%s requires human confirmation" % action,
        "%s require human confirmation" % action,
        "%s: human confirmation" % action,
        "%s: manual confirmation" % action,
        "%s not allowed" % action,
        "no %s" % action,
        "forbid %s" % action,
        "forbidden %s" % action,
    )
    if any(term in lower for term in confirmation_terms):
        return True
    if "all remote operations require human confirmation" in lower:
        return True
    if "自动%s" % action in policy_text and "禁止" in policy_text:
        return True
    return False


def _operation_is_automatically_allowed(policy_text, action):
    lower = policy_text.lower()
    allow_terms = (
        "allowed automatic operations: %s" % action,
        "allowed automatic operations: push, tag, release",
        "allowed automatic operations: push, tag",
        "automatic %s allowed" % action,
        "%s: auto allowed" % action,
        "%s: automatic allowed" % action,
        "%s: allowed" % action,
    )
    if any(term in lower for term in allow_terms):
        return True
    allowed_start = lower.find("allowed automatic operations:")
    if allowed_start >= 0:
        allowed_line = lower[allowed_start:].split("\n", 1)[0]
        return action in allowed_line
    return False


def _github_policy_block_reason(project_spec, next_action):
    actions = _remote_github_actions(next_action)
    if not actions:
        return ""

    policy = _github_policy_section(project_spec)
    if not policy:
        return "GitHub remote action requested but PROJECT_SPEC has no GitHub Sync Policy."
    if _is_local_only_policy(policy):
        return "GitHub remote action requested but PROJECT_SPEC GitHub policy is local-only."
    if _has_unavailable_credentials(policy):
        return "GitHub remote action requested but credentials are unavailable."
    if not _policy_has_required_sync_fields(policy):
        return "GitHub remote action requested but PROJECT_SPEC GitHub policy is incomplete."
    for action in actions:
        if _operation_requires_human_confirmation(policy, action):
            return "GitHub %s requires human confirmation or is not allowed by policy." % action
        if not _operation_is_automatically_allowed(policy, action):
            return "GitHub %s is not listed in allowed automatic operations." % action
    return ""


def _compact_project_spec_for_stop(project_spec, limit=12000):
    """Keep Stop context focused on the task contract, not the whole document."""
    return spec_steward.compact_project_spec_for_prompt(
        project_spec,
        limit=limit,
        force_sections=True,
    )


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


def _build_spec_update_change_request(reason, next_action, assistant_msg, latest_ctx):
    return (
        "Stop Judge determined that the user requested or confirmed a task-contract "
        "update. Apply the controlled Spec Steward flow now. If the request is "
        "sufficient, write the complete updated PROJECT_SPEC.md and update the "
        "Development Plan. If the request is insufficient, ask only the minimum "
        "clarifying questions. Do not ask the user to manually edit task-book files.\n\n"
        "STOP_REASON:\n%s\n\n"
        "STOP_NEXT_ACTION:\n%s\n\n"
        "LATEST_CONTEXT:\n%s\n\n"
        "LAST_ASSISTANT_MESSAGE:\n%s"
        % (
            (reason or "").strip(),
            (next_action or "").strip(),
            (latest_ctx or "").strip()[:4000],
            (assistant_msg or "").strip()[:6000],
        )
    )


def _handle_spec_update_required_stop(assistant_msg, history, latest_ctx, reason,
                                      next_action, questions, llm_ok, llm_error,
                                      progress_made):
    if questions:
        verdict = "spec_update_required"
        _write_loop_state(0, False, verdict)
        _write_json(verdict, reason, False, next_action, loop_count=0,
                    llm_ok=llm_ok, llm_error=llm_error,
                    progress_made=progress_made, questions=questions)
        _write_md(verdict, reason, assistant_msg, history, next_action,
                  questions=questions)
        _write_context_md(verdict, reason, next_action, auto_continue=False,
                          questions=questions)
        return {
            "systemMessage": _system_message(verdict, reason, next_action,
                                             questions=questions),
        }

    _sync_spec_steward_paths()
    change_request = _build_spec_update_change_request(
        reason, next_action, assistant_msg, latest_ctx
    )
    steward_result = spec_steward.propose_spec_update(change_request, apply_update=True)

    steward_questions = _normalize_questions(steward_result.get("questions", []))
    if steward_result.get("ok") and steward_result.get("applied"):
        verdict = "pass"
        summary = steward_result.get("update_summary") or steward_result.get("reason") or "PROJECT_SPEC updated."
        steward_reason = "Spec Steward applied PROJECT_SPEC update: %s" % summary
        steward_next_action = (
            "PROJECT_SPEC.md was updated by the controlled Spec Steward flow. "
            "Resume from the updated Development Plan; ordinary Worker must not "
            "manually edit the task contract."
        )
        _write_loop_state(0, False, verdict)
        _write_json(verdict, steward_reason, False, steward_next_action,
                    loop_count=0, llm_ok=llm_ok, llm_error=llm_error,
                    progress_made=True)
        _write_md(verdict, steward_reason, assistant_msg, history,
                  steward_next_action)
        _write_context_md(verdict, steward_reason, steward_next_action,
                          auto_continue=False)
        return {
            "systemMessage": (
                "Codex SpecPilot updated `.project_wiki/PROJECT_SPEC.md` through "
                "the controlled Spec Steward flow.\nNext action: %s"
                % steward_next_action
            )
        }

    if steward_result.get("ok") and steward_result.get("decision") == "needs_user_confirmation":
        verdict = "spec_update_required"
        steward_reason = "Spec Steward needs more information: %s" % (
            steward_result.get("reason", "missing confirmed contract details")
        )
        steward_next_action = "Ask the user the minimum clarifying questions before updating PROJECT_SPEC."
        _write_loop_state(0, False, verdict)
        _write_json(verdict, steward_reason, False, steward_next_action,
                    loop_count=0, llm_ok=llm_ok, llm_error=llm_error,
                    progress_made=False, questions=steward_questions)
        _write_md(verdict, steward_reason, assistant_msg, history,
                  steward_next_action, questions=steward_questions)
        _write_context_md(verdict, steward_reason, steward_next_action,
                          auto_continue=False, questions=steward_questions)
        return {
            "systemMessage": _system_message(verdict, steward_reason,
                                             steward_next_action,
                                             questions=steward_questions),
        }

    verdict = "human_review"
    steward_reason = "Spec Steward could not apply the contract update: %s" % (
        steward_result.get("reason") or steward_result.get("error") or "unknown error"
    )
    steward_next_action = "Review the task-contract update request and rerun the controlled Spec Steward flow."
    _write_loop_state(0, False, verdict)
    _write_json(verdict, steward_reason, False, steward_next_action,
                loop_count=0, llm_ok=llm_ok, llm_error=llm_error,
                progress_made=False, questions=steward_questions)
    _write_md(verdict, steward_reason, assistant_msg, history,
              steward_next_action, questions=steward_questions)
    _write_context_md(verdict, steward_reason, steward_next_action,
                      auto_continue=False, questions=steward_questions)
    return {
        "systemMessage": _system_message(verdict, steward_reason,
                                         steward_next_action,
                                         questions=steward_questions),
    }


def _build_onboarding_prompt(project_spec, onboarding_doc, latest_ctx, assistant_msg):
    project_spec_context = spec_steward.compact_project_spec_for_prompt(
        project_spec,
        limit=5000,
        force_sections=True,
    )
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
        "GitHub account, auth method without token/key text, credential "
        "availability, repo owner/name, whether repository creation is allowed or "
        "an existing repo must be used, public/private visibility, marker nodes, "
        "and allowed automatic operations versus human confirmation.\n"
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
            project_spec_context,
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
                    "是否需要 GitHub 同步？不需要则默认 local-only；需要则说明 GitHub 账号、认证方式、凭据可用状态、公开/私有、使用已有仓库还是允许新建仓库、marker 节点，以及哪些 push/tag/release 等操作允许自动执行或必须人工确认；不要提供 token 或密钥原文。",
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


def _build_experience_evaluation_prompt(project_spec, latest_ctx, assistant_msg, done_reason):
    project_spec_context = spec_steward.compact_project_spec_for_prompt(
        project_spec,
        limit=9000,
        force_sections=True,
    )
    return (
        "You are Codex SpecPilot Experience Evaluation Hook. Return ONLY JSON.\n"
        "The Stop Judge believes the project is done. Before final completion, "
        "evaluate the result from the perspective of a real target user.\n"
        "Schema: {\"decision\":\"final_done|spec_update_required|human_review\","
        "\"evaluation_status\":\"no obvious user-facing issues found|"
        "issues found and converted to spec update|issues filtered as low-value/out-of-scope|"
        "evaluation environment-blocked\","
        "\"reason\":\"brief\","
        "\"findings\":[\"actionable user-facing issue\"],"
        "\"filtered_findings\":[\"low-value or out-of-scope suggestion\"],"
        "\"change_request\":\"self-contained PROJECT_SPEC change request or empty\","
        "\"questions\":[\"question for human\"]}\n"
        "Rules:\n"
        "- Act like a practical user, not a perfectionist reviewer.\n"
        "- Only treat a finding as actionable if it is obvious, user-facing, "
        "within the target user and project goal, and worth another development loop.\n"
        "- Do not convert pure preference, tiny polish, speculative edge cases, "
        "non-target-user scenarios, or unrelated improvements into new work.\n"
        "- If there are actionable findings, decision must be spec_update_required "
        "and change_request must be concrete enough for Spec Steward to update "
        "PROJECT_SPEC / Development Plan. Do not write PROJECT_SPEC yourself.\n"
        "- If only low-value or out-of-scope suggestions remain, decision must be "
        "final_done and list them in filtered_findings.\n"
        "- If the project cannot be realistically used or evaluated from the "
        "available evidence, decision must be human_review with evaluation "
        "environment-blocked.\n"
        "- Do not output code fences.\n\n"
        "PROJECT_SPEC:\n```\n%s\n```\n"
        "LATEST_CONTEXT:\n```\n%s\n```\n"
        "STOP_JUDGE_DONE_REASON:\n```\n%s\n```\n"
        "LAST_ASSISTANT_MESSAGE:\n```\n%s\n```\n"
        % (
            project_spec_context,
            latest_ctx[:1200] if latest_ctx else "(no latest_context.md)",
            done_reason[:1000],
            assistant_msg[:4000],
        )
    )


def _handle_experience_evaluation_done(assistant_msg, history, project_spec, latest_ctx,
                                       done_reason):
    count = _read_experience_evaluation_count()
    if count >= MAX_EXPERIENCE_EVALUATIONS:
        evaluation = {
            "decision": "human_review",
            "status": "evaluation loop limit reached",
            "reason": "Experience evaluation loop limit reached before final completion.",
            "findings": [],
            "filtered_findings": [],
            "change_request": "",
        }
        verdict = "human_review"
        reason = evaluation["reason"]
        next_action = "Human review required to decide whether the evaluation loop should continue."
        _write_loop_state(0, False, verdict, experience_evaluation_count=count)
        _write_json(verdict, reason, False, next_action, loop_count=0,
                    experience_evaluation=evaluation)
        _write_md(verdict, reason, assistant_msg, history, next_action,
                  experience_evaluation=evaluation)
        _write_context_md(verdict, reason, next_action, auto_continue=False)
        return {"systemMessage": _system_message(verdict, reason, next_action)}

    prompt = _build_experience_evaluation_prompt(project_spec, latest_ctx, assistant_msg, done_reason)
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
        reason = "Experience Evaluation Hook failed or returned unparseable JSON: %s" % (
            llm_error or "no content"
        )
        next_action = "Review final completion manually; experience evaluation did not produce a reliable result."
        evaluation = {
            "decision": "human_review",
            "status": "evaluation environment-blocked",
            "reason": reason,
            "findings": [],
            "filtered_findings": [],
            "change_request": "",
        }
        _write_loop_state(0, False, verdict, experience_evaluation_count=count + 1)
        _write_json(verdict, reason, False, next_action, loop_count=0,
                    llm_ok=llm_ok, llm_error=llm_error,
                    experience_evaluation=evaluation)
        _write_md(verdict, reason, assistant_msg, history, next_action,
                  experience_evaluation=evaluation)
        _write_context_md(verdict, reason, next_action, auto_continue=False)
        return {"systemMessage": _system_message(verdict, reason, next_action)}

    decision = parsed.get("decision", "")
    questions = _normalize_questions(parsed.get("questions", []))
    findings = _normalize_text_list(parsed.get("findings", []))
    filtered_findings = _normalize_text_list(parsed.get("filtered_findings", []))
    change_request = parsed.get("change_request", "")
    if not isinstance(change_request, str):
        change_request = ""
    change_request = change_request.strip()
    evaluation = {
        "decision": decision if decision in EXPERIENCE_EVALUATION_DECISIONS else "human_review",
        "status": parsed.get("evaluation_status", "") or "unknown",
        "reason": parsed.get("reason", ""),
        "findings": findings,
        "filtered_findings": filtered_findings,
        "change_request": change_request,
    }

    if decision == "final_done" and (findings or change_request):
        decision = "spec_update_required"
        evaluation["decision"] = "spec_update_required"
        evaluation["status"] = "issues found and converted to spec update"
        if not change_request and findings:
            change_request = (
                "Experience evaluation found actionable user-facing issues that "
                "should become PROJECT_SPEC / Development Plan work:\n- %s"
                % "\n- ".join(findings)
            )
            evaluation["change_request"] = change_request

    if decision == "final_done":
        verdict = "done"
        reason = "Experience evaluation passed: %s" % (
            parsed.get("reason", "no obvious user-facing issues found")
        )
        next_action = ""
        _write_loop_state(0, False, verdict, experience_evaluation_count=0)
        _write_json(verdict, reason, False, next_action, loop_count=0,
                    llm_ok=llm_ok, llm_error=llm_error,
                    experience_evaluation=evaluation)
        _write_md(verdict, reason, assistant_msg, history, next_action,
                  questions=questions, experience_evaluation=evaluation)
        _write_context_md(verdict, reason, next_action, auto_continue=False,
                          questions=questions)
        _write_completion_report(verdict, reason, experience_evaluation=evaluation)
        return {
            "systemMessage": (
                "Codex SpecPilot completed final user-perspective experience evaluation "
                "and wrote `.project_wiki/COMPLETION_REPORT.md`.\n"
                "Reason: %s" % reason
            )
        }

    if decision == "spec_update_required":
        if not change_request:
            if findings:
                change_request = (
                    "Experience evaluation found actionable user-facing issues that "
                    "should become PROJECT_SPEC / Development Plan work:\n- %s"
                    % "\n- ".join(findings)
                )
                evaluation["change_request"] = change_request
            else:
                decision = "human_review"
                evaluation["decision"] = "human_review"
                evaluation["status"] = "evaluation environment-blocked"
                evaluation["reason"] = (
                    "Experience evaluation requested spec update but provided no "
                    "actionable findings or change request."
                )

    if decision == "spec_update_required":
        verdict = "spec_update_required"
        reason = "Experience evaluation found actionable user-facing issues: %s" % (
            parsed.get("reason", "spec update required")
        )
        next_action = (
            "Run the controlled Spec Steward flow with this experience evaluation "
            "change request before worker development continues:\n%s" % change_request
        )
        _write_loop_state(0, False, verdict, experience_evaluation_count=count + 1)
        _write_json(verdict, reason, False, next_action, loop_count=0,
                    llm_ok=llm_ok, llm_error=llm_error, questions=questions,
                    experience_evaluation=evaluation)
        _write_md(verdict, reason, assistant_msg, history, next_action,
                  questions=questions, experience_evaluation=evaluation)
        _write_context_md(verdict, reason, next_action, auto_continue=False,
                          questions=questions)
        return {"systemMessage": _system_message(verdict, reason, next_action, questions=questions)}

    verdict = "human_review"
    if decision not in EXPERIENCE_EVALUATION_DECISIONS:
        reason = "Experience Evaluation Hook returned invalid decision: %s" % decision
    else:
        reason = parsed.get("reason", "Experience evaluation requires human review.")
    next_action = "Review the user-perspective experience evaluation before final completion."
    _write_loop_state(0, False, verdict, experience_evaluation_count=count + 1)
    _write_json(verdict, reason, False, next_action, loop_count=0,
                llm_ok=llm_ok, llm_error=llm_error, questions=questions,
                experience_evaluation=evaluation)
    _write_md(verdict, reason, assistant_msg, history, next_action,
              questions=questions, experience_evaluation=evaluation)
    _write_context_md(verdict, reason, next_action, auto_continue=False,
                      questions=questions)
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
        "Development Plan update. If latest context is already spec_update_required "
        "and the user confirms with 同意/yes/ok/apply or equivalent, keep verdict "
        "spec_update_required and summarize the confirmed update in next_action. "
        "For spec_update_required, include questions only when information is "
        "insufficient; otherwise leave questions empty so the controlled Spec "
        "Steward flow can apply the update directly. Never ask the user to manually "
        "edit PROJECT_SPEC.md or task-book files. "
        "Set progress_made true when the last turn completed a task, passed validation, "
        "or advanced the project plan; set it false only when the loop is repeating "
        "without useful progress. "
        "pass is only for a no-op reply; continue/revise when work should proceed; "
        "ordinary implementation, test, dependency, planning, or stage-goal "
        "blockers should not become human_review by default. Use PROJECT_SPEC, "
        "wiki facts, latest context, current goal, and stage goal to choose "
        "continue or revise with a concrete investigation, recovery, fix, or "
        "validation next_action. If there is no direct solution path, first "
        "re-evaluate whether the current stage goal or Development Plan assumption "
        "is flawed, then set next_action to revise the plan or use "
        "spec_update_required when the task contract must change. Use "
        "human_review only for a real user decision, secrets or credentials, "
        "external environment action, protected-scope authorization, scope choice, "
        "unsafe work, or irreducible ambiguity. "
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

    # Permission gate on auto-continue. For continue/revise, an explicit
    # next_action is enough to drive the next loop; unsafe or unclear work
    # should be represented by human_review instead of a non-continuing
    # continue/revise verdict.
    can_continue = False
    auto_continue = False
    if verdict in ("continue", "revise"):
        if _is_permission_block(verdict, next_action, project_spec):
            blocked_verdict = verdict
            can_continue = False
            verdict = "human_review"
            reason = "auto-continue requires explicit next_action for %s verdict" % blocked_verdict
        else:
            github_block_reason = _github_policy_block_reason(project_spec, next_action)
            if github_block_reason:
                can_continue = False
                verdict = "human_review"
                reason = "GitHub policy blocked auto-continue: %s" % github_block_reason
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
        reason_max = ("NEXT_ACTION: " + next_action)[:1200]
        _write_json(verdict, reason, auto_continue, next_action,
                    loop_count=next_loop_count, llm_ok=llm_ok, llm_error=llm_error,
                    progress_made=progress_made, questions=questions)
        _write_md(verdict, reason, assistant_msg, history, next_action, questions=questions)
        _write_context_md(verdict, reason, next_action, auto_continue=True, questions=questions)
        return {
            "decision": "block",
            "reason": reason_max,
        }

    if verdict == "done":
        return _handle_experience_evaluation_done(
            assistant_msg,
            history,
            project_spec,
            latest_ctx,
            reason,
        )

    if verdict == "spec_update_required":
        return _handle_spec_update_required_stop(
            assistant_msg,
            history,
            latest_ctx,
            reason,
            next_action,
            questions,
            llm_ok,
            llm_error,
            progress_made,
        )

    if verdict in ("done", "pass", "human_review", "spec_update_required"):
        _write_loop_state(0, False, verdict)

    _write_json(verdict, reason, auto_continue, next_action,
                loop_count=0 if verdict in ("done", "pass", "human_review", "spec_update_required") else _read_loop_state(),
                llm_ok=llm_ok, llm_error=llm_error, progress_made=progress_made,
                questions=questions)
    _write_md(verdict, reason, assistant_msg, history, next_action, questions=questions)
    _write_context_md(verdict, reason, next_action, auto_continue=False, questions=questions)

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
