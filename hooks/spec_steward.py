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
        "- If the change is ambiguous or conflicts with the current contract, return needs_user_confirmation.\n"
        "- Preserve judge-system protected scope unless the user explicitly changes SpecPilot itself.\n"
        "- Preserve or add GitHub sync policy. If upload/sync is not confirmed, use local-only.\n"
        "- Never request, write, or expose API keys, tokens, or secrets.\n"
        "- Update Development Plan so remaining work is clear; mark obsolete work in Notes if needed.\n"
        "- Do not add RAG, multi-agent platforms, graph memory, external schedulers, or cloud defaults.\n"
        "- Do not output code fences.\n"
        "- If decision is apply, updated_project_spec must be the complete PROJECT_SPEC markdown.\n\n"
        "CURRENT PROJECT_SPEC:\n```\n%s\n```\n\n"
        "LATEST CONTEXT:\n```\n%s\n```\n\n"
        "USER CHANGE REQUEST:\n```\n%s\n```\n"
        % (current_spec[:12000], latest_context[:2000], change_request[:4000])
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
