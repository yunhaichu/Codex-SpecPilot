"""UserPromptSubmit hook - injects short task-loop context into Codex prompts."""
import json
import os
import sys

# Recursive guard: skip if child Codex process
if os.environ.get("CODEX_WIKIGUARD_CHILD") == "1":
    print(json.dumps({}, indent=2, ensure_ascii=False))
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from project_paths import wiki_dir

WIKI_DIR = wiki_dir()

PRIMARY_FILE = "INJECTION.md"
LATEST_CTX_FILE = "latest_context.md"
FALLBACK_FILES = ["HOME.md", "RULES.md", "CURRENT_TASK.md", "JUDGE.md"]
MAX_CONTEXT_CHARS = 6000


def _read_file(rel_path):
    path = os.path.join(WIKI_DIR, rel_path)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _truncate(text):
    if len(text) > MAX_CONTEXT_CHARS:
        return text[:MAX_CONTEXT_CHARS] + (
            "\n\n[TRUNCATED BY Codex-WikiGuard: injection context exceeded limit]"
        )
    return text


def _inject_start_work_prompt(prompt_text):
    """If user says '开始工作', inject start work instruction."""
    if not prompt_text:
        return ""
    if "开始工作" in prompt_text:
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

    # Append work flow instruction (start/end)
    start_end_prompt = _inject_start_work_prompt(prompt_text)
    context += start_end_prompt

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
