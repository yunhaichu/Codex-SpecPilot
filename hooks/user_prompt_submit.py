"""UserPromptSubmit hook — injects Wiki files into Codex prompts.

Reads HOME.md, RULES.md, CURRENT_TASK.md, JUDGE.md from .project_wiki/
and returns them as additionalContext.
"""
import json
import os
import sys

WIKI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".project_wiki")

FILES_TO_INJECT = ["HOME.md", "RULES.md", "CURRENT_TASK.md", "JUDGE.md"]


def _read_file(rel_path):
    path = os.path.join(WIKI_DIR, rel_path)
    if not os.path.isfile(path):
        return f"[MISSING: {rel_path}]"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def user_prompt_submit(turn_payload):
    """Called before every user prompt.
    
    Args:
        turn_payload: dict from Codex with turn metadata.
    
    Returns:
        dict with additionalContext key.
    """
    parts = []
    for fname in FILES_TO_INJECT:
        content = _read_file(fname)
        parts.append(f"### {fname} ###\n{content}")

    additional_context = "\n\n".join(parts)
    return {"additionalContext": additional_context}


if __name__ == "__main__":
    # Allow standalone test
    result = user_prompt_submit({})
    print(json.dumps(result, indent=2, ensure_ascii=False))
