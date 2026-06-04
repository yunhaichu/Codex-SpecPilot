"""UserPromptSubmit hook - injects short task-loop context into Codex prompts."""
import json
import os
import re
import sys

# Recursive guard: skip if child Codex process
if os.environ.get("CODEX_SPECPILOT_CHILD") == "1":
    print(json.dumps({}, indent=2, ensure_ascii=False))
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from project_paths import wiki_dir
from project_injector import ensure_runtime_files
from mission_snapshot import extract_active_mission_snapshot
import maintenance_authorization
import task_intent

WIKI_DIR = wiki_dir()

PRIMARY_FILE = "INJECTION.md"
LATEST_CTX_FILE = "latest_context.md"
PROJECT_SPEC_FILE = "PROJECT_SPEC.md"
PROJECT_ONBOARDING_FILE = "PROJECT_ONBOARDING.md"
FALLBACK_FILES = ["HOME.md", "RULES.md", "CURRENT_TASK.md", "JUDGE.md"]
MAX_CONTEXT_CHARS = 6000
REQUIRED_PROJECT_SPEC_TERMS = (
    "Project Goal",
    "Allowed Scope",
    "Protected Scope",
    "Development Plan",
    "Acceptance Criteria",
    "TASK-",
)

GOAL_CHANGE_RULE = """

### Goal Change Rule ###
If the user's prompt changes the project goal, scope, priority, acceptance
criteria, or Development Plan, do not edit business code in that turn.
Summarize the requested contract change, list the affected PROJECT_SPEC
sections, and make the change request clear enough for the controlled Spec
Steward flow. Do not ask the user to manually edit PROJECT_SPEC.md or task-book
files.

If latest context already says spec_update_required and the user replies "同意",
"yes", "ok", "apply", or an equivalent confirmation, treat that as permission
for Spec Steward to apply the previously summarized change.
If the user rejects the summarized change or uses ambiguous confirmation
wording, do not apply the task contract update; ask only the minimum
confirmation or replacement-change question.

The task contract must be updated by the controlled Spec Steward flow before
worker development continues. Codex Worker must not modify PROJECT_SPEC.md
itself.
"""

ONBOARDING_RULE = """

### Project Onboarding Rule ###
If PROJECT_SPEC.md is missing, contains NEEDS_USER_CONFIRMATION, or lacks core
task-contract sections, the project is not ready for worker development. Do not
edit business code. Interview the user with at most 5 high-signal questions per
round. In every onboarding reply, summarize the confirmed facts so far. When
enough information is confirmed, output a complete PROJECT_SPEC candidate with
concrete Allowed Scope, Protected Scope, Development Plan, and Acceptance
Criteria. Codex Worker must not write PROJECT_SPEC.md directly; the controlled
SpecPilot Hook flow writes the task contract.

GitHub sync must be decided during onboarding. Ask whether the user wants
GitHub upload/sync. If not, default to local-only. If yes, ask for GitHub
account, auth method without requesting token/key text, credential availability,
repository owner/name, public/private visibility, whether a new repository may
be created or an existing repository must be used, marker nodes, and which
push/tag/release/checkpoint operations Hook may request automatically versus
only after human confirmation.
"""

CONVERSATION_MODE_RULE = """

### Conversation Mode ###
The current prompt is classified as a normal question or discussion, not a
request to start or continue the Development Plan. Answer directly using the
current project facts if relevant. Do not start worker development, do not run
the full task loop, do not request a PROJECT_SPEC update, and do not ask the
user for task-contract confirmation unless the user clearly asks to change the
goal, plan, scope, release target, or acceptance criteria.
The Stop Hook should record a lightweight pass judgment for this conversation.
"""


def _read_file(rel_path):
    path = os.path.join(WIKI_DIR, rel_path)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _ensure_project_wiki_files():
    """Create the minimal project wiki when a Hook reaches a new project."""
    project_dir = os.path.dirname(WIKI_DIR)
    ensure_runtime_files(project_dir, force=False)


def _truncate(text):
    if len(text) > MAX_CONTEXT_CHARS:
        suffix = "\n\n[TRUNCATED BY Codex SpecPilot: injection context exceeded limit]"
        return text[:MAX_CONTEXT_CHARS - len(suffix)] + suffix
    return text


def _remove_markdown_section(text, heading_title):
    """Remove one level-2 markdown section by exact heading title."""
    if not text:
        return text
    pattern = re.compile(
        r"(?m)^##\s+%s\s*$" % re.escape(heading_title)
    )
    match = pattern.search(text)
    if not match:
        return text
    next_heading = re.search(r"(?m)^##\s+\S.*$", text[match.end():])
    end = len(text) if not next_heading else match.end() + next_heading.start()
    return (text[:match.start()].rstrip() + "\n\n" + text[end:].lstrip()).strip()


def _dedupe_base_context(context, has_active_snapshot):
    """Drop base sections already injected as dynamic high-priority context."""
    deduped = context or ""
    deduped = _remove_markdown_section(deduped, "Goal Change Rule")
    if has_active_snapshot:
        deduped = _remove_markdown_section(deduped, "Active Mission Snapshot Rule")
    return deduped


def _format_active_mission_snapshot(snapshot):
    """Format the dynamic snapshot without repeating the markdown heading."""
    if not snapshot:
        return ""
    body = re.sub(
        r"(?im)^##+\s+(?:\d+\.\s*)?Active Mission Snapshot\s*\n?",
        "",
        snapshot,
        count=1,
    ).strip()
    return (
        "\n\n### Active Mission Snapshot ###\n"
        "Use this as the current-goal anchor before historical summaries.\n"
        "%s\n" % body
    )


def _inject_start_work_prompt(prompt_text, onboarding_required=False):
    """If user says '开始工作', inject start work instruction."""
    if not prompt_text:
        return ""
    if "开始工作" in prompt_text:
        if onboarding_required:
            return (
                "\n\n### Start Work Deferred ###\n"
                "User said '开始工作', but PROJECT_SPEC.md is missing or incomplete. "
                "Do not start worker development yet. Continue project onboarding, "
                "ask the missing questions, and produce a PROJECT_SPEC candidate for "
                "the controlled SpecPilot Hook flow to write.\n"
            )
        return (
            "\n\n### Start Work Instruction ###\n"
            "User has said '开始工作'. You must:\n"
            "1. Read .project_wiki/PROJECT_SPEC.md as the task contract.\n"
            "2. Find the first incomplete Development Plan task.\n"
            "3. Work on that task in a small verifiable step.\n"
            "4. Do not wait for the user between ordinary development steps.\n"
            "5. At turn end, report task id, files changed, validation, done/not done, and next step.\n"
            "6. Let the Stop Hook decide whether to continue, revise, finish, or request human review.\n"
        )
    if "结束工作" in prompt_text:
        return (
            "\n\n### End Work Instruction ###\n"
            "User has said '结束工作'. You must:\n"
            "1. Summarize what was completed this turn.\n"
            "2. Do NOT request auto-continue.\n"
            "3. If all tasks are done, generate or update COMPLETION_REPORT.md.\n"
        )
    return ""


def _project_spec_needs_onboarding():
    spec = _read_file(PROJECT_SPEC_FILE)
    if spec is None:
        return True
    if "NEEDS_USER_CONFIRMATION" in spec:
        return True
    return any(term not in spec for term in REQUIRED_PROJECT_SPEC_TERMS)


def user_prompt_submit(turn_payload):
    """Called before every user prompt.

    Returns the Codex wire-format response with additionalContext.
    Prefers INJECTION.md; falls back to legacy files if INJECTION.md is missing.
    Appends latest_context.md after INJECTION.md if present.
    Appends permission summary at the end.
    Appends start/end work instruction when user prompt matches.
    """
    prompt_text = ""
    if isinstance(turn_payload, dict):
        prompt_text = turn_payload.get("prompt", "") or ""

    _ensure_project_wiki_files()

    latest_context = _read_file(LATEST_CTX_FILE)
    prompt_intent = task_intent.build_prompt_intent(
        prompt_text,
        latest_context=latest_context or "",
    )
    task_intent.save_prompt_intent(prompt_intent, WIKI_DIR)
    if os.path.isfile(os.path.join(WIKI_DIR, PRIMARY_FILE)):
        context = _read_file(PRIMARY_FILE)
    else:
        parts = []
        for fname in FALLBACK_FILES:
            content = _read_file(fname)
            parts.append("### %s ###\n%s" % (fname, content))
        context = "\n\n".join(parts)

    # Put dynamic control rules first so truncation cannot remove them.
    dynamic_context = ""
    project_spec = _read_file(PROJECT_SPEC_FILE)
    snapshot = extract_active_mission_snapshot(project_spec or "")
    context = _dedupe_base_context(context, has_active_snapshot=bool(snapshot))
    if snapshot:
        dynamic_context += _format_active_mission_snapshot(snapshot)
    needs_onboarding = _project_spec_needs_onboarding()
    if needs_onboarding:
        dynamic_context += ONBOARDING_RULE
        onboarding = _read_file(PROJECT_ONBOARDING_FILE)
        if onboarding:
            dynamic_context += "\n--- Project Onboarding ---\n" + onboarding
    dynamic_context += GOAL_CHANGE_RULE
    if latest_context is not None:
        dynamic_context += "\n--- Latest Judge Context ---\n" + latest_context
    lease_result = maintenance_authorization.create_lease_from_prompt(
        prompt_text,
        latest_context=latest_context or "",
        wiki_dir=WIKI_DIR,
    )
    if lease_result.get("created"):
        lease = lease_result.get("lease", {})
        dynamic_context += (
            "\n\n### Protected Maintenance Lease ###\n"
            "A one-shot protected maintenance lease was created from the user's "
            "confirmation. Target files: %s. It expires at %s and is consumed by "
            "the next matching protected write.\n"
            % (
                ", ".join(lease.get("target_paths", [])),
                lease.get("expires_at", "(unknown)"),
            )
        )
    if prompt_intent.get("intent") == "conversation" and not needs_onboarding:
        conversation_context = ""
        if snapshot:
            conversation_context += _format_active_mission_snapshot(snapshot)
        conversation_context += CONVERSATION_MODE_RULE
        conversation_context += (
            "\n--- Prompt Intent ---\n"
            "intent: %s\ncomplexity: %s\nrequires_confirmation: %s\n"
            % (
                prompt_intent.get("intent"),
                prompt_intent.get("complexity"),
                str(prompt_intent.get("requires_confirmation")).lower(),
            )
        )
        if lease_result.get("created"):
            conversation_context += dynamic_context.split("### Protected Maintenance Lease ###", 1)[-1]
        context = _truncate(conversation_context)
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": context,
            }
        }
    start_end_prompt = _inject_start_work_prompt(prompt_text, onboarding_required=needs_onboarding)
    dynamic_context += start_end_prompt
    context = dynamic_context + "\n--- SpecPilot Base Context ---\n" + context

    context = _truncate(context)

    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
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

    result = user_prompt_submit(payload)
    print(json.dumps(result, indent=2, ensure_ascii=False))
