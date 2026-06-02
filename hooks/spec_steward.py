"""Spec Steward -- controlled PROJECT_SPEC update flow.

This is not a worker-development hook. It is a narrow entry point for turning
mid-run user goal changes into an updated task contract.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codex_client import call_codex_default
from project_paths import wiki_dir
from secret_scan import find_secret_material

WIKI_DIR = wiki_dir()
PROJECT_SPEC_PATH = os.path.join(WIKI_DIR, "PROJECT_SPEC.md")
LATEST_CONTEXT_PATH = os.path.join(WIKI_DIR, "latest_context.md")

VALID_DECISIONS = ("apply", "needs_user_confirmation", "reject")
MAX_PROJECT_SPEC_PROMPT_CHARS = 50000
MAX_LATEST_CONTEXT_PROMPT_CHARS = 6000
MAX_CHANGE_REQUEST_PROMPT_CHARS = 8000
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
PROJECT_SPEC_PROMPT_SECTIONS = (
    ("Project Mode", "0. Project Mode", ("1. Project Goal",), 0.4),
    ("Project Goal", "1. Project Goal", ("2. Background",), 1.1),
    ("User Requirements", "3. User Requirements", ("4. Non-Goals",), 1.4),
    ("Non-Goals", "4. Non-Goals", ("5. Allowed Scope",), 0.8),
    ("Allowed Scope", "5. Allowed Scope", ("6. Protected Scope",), 0.8),
    ("Protected Scope", "6. Protected Scope", ("7. Development Plan",), 1.0),
    ("Development Plan", "7. Development Plan", ("8. Acceptance Criteria",), 3.6),
    ("Acceptance Criteria", "8. Acceptance Criteria", ("9. Stop Conditions",), 1.4),
    ("Stop Conditions", "9. Stop Conditions", ("GitHub Sync Policy", "10. Submission Requirements"), 1.2),
    ("GitHub Sync Policy", "GitHub Sync Policy", ("10. Submission Requirements",), 1.0),
    ("Submission Requirements", "10. Submission Requirements", (), 1.2),
)
CONFIRMATION_TERMS = {
    "同意",
    "确认",
    "确认更新",
    "可以",
    "好的",
    "好",
    "没问题",
    "行",
    "yes",
    "y",
    "ok",
    "okay",
    "approved",
    "approve",
    "apply",
    "goahead",
    "sounds good",
}
REJECTION_TERMS = {
    "不同意",
    "不确认",
    "不要改",
    "不要更新",
    "先不要",
    "取消",
    "算了",
    "no",
    "n",
    "reject",
    "rejected",
    "cancel",
    "decline",
    "disagree",
}
AMBIGUOUS_CONFIRMATION_TERMS = {
    "可以吧",
    "也行吧",
    "应该可以",
    "随便",
    "再说",
    "maybe",
    "probably",
    "not sure",
}


def _normalize_response(text):
    return "".join((text or "").strip().lower().split()).strip("。.!！?？,，;；:：")


def is_confirmation_only(text):
    normalized = _normalize_response(text)
    if not normalized or normalized.startswith("不"):
        return False
    return normalized in CONFIRMATION_TERMS


def is_rejection_only(text):
    normalized = _normalize_response(text)
    return normalized in REJECTION_TERMS


def is_ambiguous_confirmation(text):
    normalized = _normalize_response(text)
    return normalized in AMBIGUOUS_CONFIRMATION_TERMS


def latest_context_requires_spec_update(latest_context):
    return "VERDICT: spec_update_required" in (latest_context or "")


def build_user_prompt_change_request(prompt_text, latest_context=""):
    prompt_text = (prompt_text or "").strip()
    latest_context = latest_context or ""
    if is_confirmation_only(prompt_text):
        if not latest_context_requires_spec_update(latest_context):
            return ""
        return (
            "The user confirmed the previously summarized task-contract change. "
            "Apply the controlled PROJECT_SPEC update described by Latest Judge Context. "
            "Do not ask the user to manually edit task-book files.\n\n"
            "LATEST_CONTEXT:\n%s" % latest_context
        )
    return (
        "The user provided a task-contract modification suggestion. Run the "
        "controlled Spec Steward update flow. If the suggestion is sufficient, "
        "write the complete updated PROJECT_SPEC and update the Development Plan. "
        "If information is insufficient, ask only the minimum clarifying questions. "
        "Do not ask the user to manually edit task-book files.\n\n"
        "USER_PROMPT:\n%s" % prompt_text
    )


def _read_file(path, default=""):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return default


def _write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _parse_llm_response(content):
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
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def _slice_project_spec_section(text, start_term, end_terms):
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


def _clip_for_prompt(text, limit):
    if len(text) <= limit:
        return text
    marker = "\n[...middle omitted to preserve prompt budget...]\n"
    if limit <= len(marker) + 120:
        return text[:limit].rstrip() + "\n[...truncated...]"
    head = max(80, (limit - len(marker)) // 2)
    tail = max(80, limit - len(marker) - head)
    return text[:head].rstrip() + marker + text[-tail:].lstrip()


def compact_project_spec_for_prompt(project_spec, limit=MAX_PROJECT_SPEC_PROMPT_CHARS,
                                    force_sections=False):
    """Return PROJECT_SPEC context that preserves key sections and late tasks."""
    if not project_spec:
        return "(no PROJECT_SPEC.md)"
    if not force_sections and len(project_spec) <= limit:
        return project_spec

    sections = []
    for title, start, ends, weight in PROJECT_SPEC_PROMPT_SECTIONS:
        section = _slice_project_spec_section(project_spec, start, ends)
        if section:
            sections.append((title, section, weight))

    if not sections:
        return _clip_for_prompt(project_spec, limit)

    total_weight = sum(weight for _, _, weight in sections) or 1.0
    budget = max(1000, limit - 500)
    pieces = [
        "[PROJECT_SPEC compacted for prompt: key sections preserved with head/tail clips.]"
    ]
    for title, section, weight in sections:
        section_limit = max(280, int(budget * weight / total_weight) - len(title) - 8)
        pieces.append("## %s\n%s" % (title, _clip_for_prompt(section, section_limit)))

    compact = "\n\n".join(pieces)
    if len(compact) > limit:
        return _clip_for_prompt(compact, limit)
    return compact


def validate_project_spec(text):
    """Return missing required terms for a proposed PROJECT_SPEC."""
    missing = []
    if not text or not text.strip():
        return ["PROJECT_SPEC content"]
    for term in REQUIRED_SPEC_TERMS:
        if term not in text:
            missing.append(term)
    if "TASK-" not in text:
        missing.append("TASK-*")
    secret_findings = find_secret_material(text)
    for finding in secret_findings:
        missing.append("secret material: %s" % finding)
    return missing


def build_spec_update_prompt(change_request, current_spec, latest_context=""):
    current_spec_context = compact_project_spec_for_prompt(
        current_spec,
        limit=MAX_PROJECT_SPEC_PROMPT_CHARS,
    )
    return (
        "You are Codex SpecPilot Spec Steward. Return ONLY JSON.\n"
        "Your job is to update the task contract, not to write project code.\n"
        "Schema: {\"decision\":\"apply|needs_user_confirmation|reject\","
        "\"reason\":\"brief\","
        "\"questions\":[\"question\"],"
        "\"update_summary\":\"brief\","
        "\"updated_project_spec\":\"full markdown PROJECT_SPEC or empty\"}\n"
        "Rules:\n"
        "- Only encode the user's confirmed change request.\n"
        "- If the user provided a modification suggestion and the requested contract "
        "change is clear enough, apply it directly through this controlled flow.\n"
        "- If the user only replied with an approval such as 同意, yes, ok, or apply, "
        "treat it as confirmation of the spec_update_required change in latest context.\n"
        "- If the user clearly rejects the summarized change, do not apply it. "
        "If confirmation wording is ambiguous, ask the minimum confirmation question.\n"
        "- If the change is ambiguous or conflicts with the current contract, return "
        "needs_user_confirmation with only the minimum necessary questions.\n"
        "- Never tell the user to manually edit PROJECT_SPEC.md or task-book files.\n"
        "- Preserve judge-system protected scope unless the user explicitly changes SpecPilot itself.\n"
        "- Preserve or add GitHub sync policy. If upload/sync is not confirmed, use local-only.\n"
        "- If CURRENT PROJECT_SPEC is compacted for prompt length, preserve the "
        "visible required sections, late Development Plan items, and Submission "
        "Requirements; do not drop them because they appear late in the task book.\n"
        "- Never request, write, or expose API keys, tokens, or secrets.\n"
        "- Update Development Plan so remaining work is clear; mark obsolete work in Notes if needed.\n"
        "- Do not add RAG, multi-agent platforms, graph memory, external schedulers, or cloud defaults.\n"
        "- Do not output code fences.\n"
        "- If decision is apply, updated_project_spec must be the complete PROJECT_SPEC markdown.\n\n"
        "CURRENT PROJECT_SPEC:\n```\n%s\n```\n\n"
        "LATEST CONTEXT:\n```\n%s\n```\n\n"
        "USER CHANGE REQUEST:\n```\n%s\n```\n"
        % (
            current_spec_context,
            latest_context[:MAX_LATEST_CONTEXT_PROMPT_CHARS],
            change_request[:MAX_CHANGE_REQUEST_PROMPT_CHARS],
        )
    )


def propose_spec_update(change_request, apply_update=False):
    current_spec = _read_file(PROJECT_SPEC_PATH)
    latest_context = _read_file(LATEST_CONTEXT_PATH)
    if not current_spec.strip():
        return {
            "ok": False,
            "applied": False,
            "decision": "reject",
            "reason": "PROJECT_SPEC.md is missing or empty.",
        }
    if not change_request.strip():
        return {
            "ok": False,
            "applied": False,
            "decision": "needs_user_confirmation",
            "reason": "No change request was provided.",
        }

    prompt = build_spec_update_prompt(change_request, current_spec, latest_context)
    llm_result = call_codex_default(prompt, timeout=120)
    if not llm_result.get("ok"):
        return {
            "ok": False,
            "applied": False,
            "decision": "reject",
            "reason": "Spec Steward AI call failed.",
            "error": llm_result.get("error", "unknown error"),
        }

    parsed = _parse_llm_response(llm_result.get("content", ""))
    if not isinstance(parsed, dict):
        return {
            "ok": False,
            "applied": False,
            "decision": "reject",
            "reason": "Spec Steward AI returned unparseable JSON.",
        }

    decision = parsed.get("decision", "")
    if decision not in VALID_DECISIONS:
        return {
            "ok": False,
            "applied": False,
            "decision": "reject",
            "reason": "Spec Steward AI returned invalid decision: %s" % decision,
        }

    response = {
        "ok": True,
        "applied": False,
        "decision": decision,
        "reason": parsed.get("reason", ""),
        "questions": parsed.get("questions", []),
        "update_summary": parsed.get("update_summary", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if decision != "apply":
        return response

    updated_spec = parsed.get("updated_project_spec", "")
    missing = validate_project_spec(updated_spec)
    if missing:
        response.update({
            "ok": False,
            "decision": "reject",
            "reason": "Proposed PROJECT_SPEC is missing required content.",
            "missing": missing,
        })
        return response

    response["would_write"] = True
    if apply_update:
        _write_file(PROJECT_SPEC_PATH, updated_spec.rstrip() + "\n")
        response["applied"] = True
    else:
        response["updated_project_spec"] = updated_spec
    return response


def propose_user_prompt_update(prompt_text, latest_context="", apply_update=True):
    if latest_context_requires_spec_update(latest_context):
        if is_rejection_only(prompt_text):
            return {
                "ok": True,
                "applied": False,
                "decision": "reject",
                "reason": "User rejected the previously summarized task-contract change.",
                "questions": ["如需改成其他方向，请直接说明新的任务合同修改建议。"],
                "update_summary": "",
                "source": "user_prompt_rejection",
            }
        if is_ambiguous_confirmation(prompt_text):
            return {
                "ok": True,
                "applied": False,
                "decision": "needs_user_confirmation",
                "reason": "User confirmation is ambiguous and cannot be treated as 同意.",
                "questions": ["请明确回复“同意”以应用这次任务合同更新，或说明要怎样调整。"],
                "update_summary": "",
                "source": "user_prompt_ambiguous_confirmation",
            }

    change_request = build_user_prompt_change_request(prompt_text, latest_context)
    if not change_request:
        return {
            "ok": True,
            "applied": False,
            "decision": "needs_user_confirmation",
            "reason": "User confirmation has no prior spec_update_required context.",
            "questions": ["请先说明要调整的任务合同内容。"],
            "update_summary": "",
        }
    result = propose_spec_update(change_request, apply_update=apply_update)
    result["source"] = "user_prompt_confirmation" if is_confirmation_only(prompt_text) else "user_prompt_suggestion"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Controlled PROJECT_SPEC update flow.")
    parser.add_argument("--change", default="", help="User change request.")
    parser.add_argument("--apply", action="store_true", help="Write the updated PROJECT_SPEC.md.")
    args = parser.parse_args(argv)

    change_request = args.change
    if not change_request:
        stdin_text = sys.stdin.read()
        change_request = stdin_text.strip()

    result = propose_spec_update(change_request, apply_update=args.apply)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
