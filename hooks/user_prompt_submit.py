"""UserPromptSubmit hook — injects short context into Codex prompts.

优先注入 INJECTION.md;如果不存在,回退到 HOME/RULES/CURRENT_TASK/JUDGE。
如果 latest_context.md 存在,会追加在 INJECTION.md 之后。
输出限制最大长度,避免本地模型上下文溢出。

当用户 prompt 包含"开始工作"或"结束工作"时,注入对应的执行指令。
"""
import json
import os
import sys

# Recursive guard: skip if child Codex process
if os.environ.get("CODEX_WIKIGUARD_CHILD") == "1":
    print(json.dumps({}, indent=2, ensure_ascii=False))
    sys.exit(0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from permission_policy import get_permission_summary

WIKI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".project_wiki"
)

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
            "1. Read .project_wiki/PROJECT_SPEC.md to understand the task.\n"
            "2. Find the first uncompleted task in Development Plan (marked [ ]).\n"
            "3. Execute ONLY that task. Do not jump ahead.\n"
            "4. At end of each turn, report: which TASK, which files modified, "
            "what validation done, what is next.\n"
            "5. Do NOT modify PROJECT_SPEC.md, RULES.md, DECISIONS.md, REJECTED.md, "
            "PERMISSIONS.md, WORKFLOW.md, COMPLETION_REPORT_TEMPLATE.md.\n"
            "6. Do NOT modify JUDGE.md, latest_context.md, judge_latest.json, "
            "loop_state.json, guard_log.jsonl.\n"
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

    # Append permission summary
    perm_summary = get_permission_summary()
    context += "\n\n" + perm_summary

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
