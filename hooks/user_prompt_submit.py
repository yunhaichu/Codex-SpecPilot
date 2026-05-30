"""UserPromptSubmit hook — injects short context into Codex prompts.

优先注入 INJECTION.md；如果不存在，回退到 HOME/RULES/CURRENT_TASK/JUDGE。
输出限制最大长度，避免本地模型上下文溢出。
"""
import json
import os
import sys

WIKI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".project_wiki"
)

PRIMARY_FILE = "INJECTION.md"
FALLBACK_FILES = ["HOME.md", "RULES.md", "CURRENT_TASK.md", "JUDGE.md"]
MAX_CONTEXT_CHARS = 6000


def _read_file(rel_path):
    path = os.path.join(WIKI_DIR, rel_path)
    if not os.path.isfile(path):
        return f"[MISSING: {rel_path}]"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _truncate(text):
    if len(text) > MAX_CONTEXT_CHARS:
        return text[:MAX_CONTEXT_CHARS] + (
            "\n\n[TRUNCATED BY Codex-WikiGuard: injection context exceeded limit]"
        )
    return text


def user_prompt_submit(turn_payload):
    """Called before every user prompt.

    Returns the Codex wire-format response with additionalContext.
    Prefers INJECTION.md; falls back to legacy files.
    """
    if os.path.isfile(os.path.join(WIKI_DIR, PRIMARY_FILE)):
        context = _read_file(PRIMARY_FILE)
    else:
        parts = []
        for fname in FALLBACK_FILES:
            content = _read_file(fname)
            parts.append(f"### {fname} ###\n{content}")
        context = "\n\n".join(parts)

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
