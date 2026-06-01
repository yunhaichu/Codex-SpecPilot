"""UserPromptSubmit hook - injects short task-loop context into Codex prompts."""
import json
import os
import sys

# Recursive guard: skip if child Codex process
if os.environ.get("CODEX_SPECPILOT_CHILD") == "1":
    print(json.dumps({}, indent=2, ensure_ascii=False))
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from project_paths import wiki_dir
from project_injector import bootstrap_wiki_files

WIKI_DIR = wiki_dir()

PRIMARY_FILE = "INJECTION.md"
LATEST_CTX_FILE = "latest_context.md"
PROJECT_SPEC_FILE = "PROJECT_SPEC.md"
PROJECT_ONBOARDING_FILE = "PROJECT_ONBOARDING.md"
FALLBACK_FILES = ["HOME.md", "RULES.md", "CURRENT_TASK.md", "JUDGE.md"]
MAX_CONTEXT_CHARS = 6000

GOAL_CHANGE_RULE = """

### Goal Change Rule ###
If the user's prompt changes the project goal, scope, priority, acceptance
criteria, or Development Plan, do not edit business code in that turn.
Summarize the requested contract change, list the affected PROJECT_SPEC
sections, and state that the task contract must be updated by the controlled
Spec Steward flow before worker development continues. Codex Worker must not
modify PROJECT_SPEC.md itself.
"""

ONBOARDING_RULE = """

### Project Onboarding Rule ###
If PROJECT_SPEC.md is missing or contains NEEDS_USER_CONFIRMATION, the project
is not ready for worker development. Do not edit business code. Interview the
user with at most 5 high-signal questions per round. In every onboarding reply,
summarize the confirmed facts so far. When enough information is confirmed,
output a complete PROJECT_SPEC candidate with concrete Allowed Scope,
Protected Scope, Development Plan, and Acceptance Criteria. Codex Worker must
not write PROJECT_SPEC.md directly; the controlled SpecPilot Hook flow writes
the task contract.

GitHub sync must be decided during onboarding. Ask whether the user wants
GitHub upload/sync. If not, default to local-only. If yes, ask for auth method
without requesting token/key text, repository owner/name, public/private
visibility, and which push/tag/checkpoint operations Hook may request.
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
    bootstrap_wiki_files(project_dir, force=False)


def _truncate(text):
    if len(text) > MAX_CONTEXT_CHARS:
        suffix = "\n\n[TRUNCATED BY Codex SpecPilot: injection context exceeded limit]"
        return text[:MAX_CONTEXT_CHARS - len(suffix)] + suffix
    return text


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
    return "NEEDS_USER_CONFIRMATION" in spec


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

    if os.path.isfile(os.path.join(WIKI_DIR, PRIMARY_FILE)):
        context = _read_file(PRIMARY_FILE)
        ctx_append = _read_file(LATEST_CTX_FILE)
        if ctx_append is not None:
            context += "\n--- Latest Judge Context ---\n" + ctx_append
    else:
        parts = []
        for fname in FALLBACK_FILES:
            content = _read_file(fname)
            parts.append("### %s ###\n%s" % (fname, content))
        context = "\n\n".join(parts)

    # Put dynamic control rules first so truncation cannot remove them.
    dynamic_context = ""
    needs_onboarding = _project_spec_needs_onboarding()
    if needs_onboarding:
        dynamic_context += ONBOARDING_RULE
        onboarding = _read_file(PROJECT_ONBOARDING_FILE)
        if onboarding:
            dynamic_context += "\n--- Project Onboarding ---\n" + onboarding
    dynamic_context += GOAL_CHANGE_RULE
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
