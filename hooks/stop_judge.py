"""StopJudge hook — writes judgment on turn stop.

Reads last_assistant_message from the stop payload,
writes to .project_wiki/JUDGE.md and .project_wiki/judge_latest.json.
Returns a minimal systemMessage in Codex wire format.
"""
import json
import os
import sys
from datetime import datetime, timezone

WIKI_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
     ".project_wiki"
)

JUDGE_MD = os.path.join(WIKI_DIR, "JUDGE.md")
JUDGE_JSON = os.path.join(WIKI_DIR, "judge_latest.json")

DEFAULT_VERDICT = "human_review"


def _read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "[file missing]"


def _write_md(verdict, reason, assistant_msg, history):
    ts = datetime.now(timezone.utc).isoformat()
    md = f"""# Codex-WikiGuard — JUDGE

## Latest Judgment

**Timestamp**: {ts}

**Verdict**: {verdict}

**Reason**: {reason}

## Assistant Message (last turn)

```
{assistant_msg}
```

## History

{'\n'.join(history)}
"""
    with open(JUDGE_MD, "w", encoding="utf-8") as f:
        f.write(md)


def _write_json(verdict, reason):
    data = {
        "last_verdict": verdict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
    }
    with open(JUDGE_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def stop_judge(turn_payload):
    """Called when a Codex turn ends (Stop event).

    Returns a minimal systemMessage — no decision: block, no auto-continue.
    """
    assistant_msg = turn_payload.get("last_assistant_message", "")
    if isinstance(assistant_msg, list):
        assistant_msg = "\n".join(
            m.get("content", "") if isinstance(m, dict) else str(m)
            for m in assistant_msg
        )

    verdict = DEFAULT_VERDICT
    reason = "Default verdict: manual review required before continuing (v1 conservative)."

    # Read existing history from JUDGE.md
    history = []
    if os.path.isfile(JUDGE_MD):
        content = _read_file(JUDGE_MD)
        history_marker = "## History"
        if history_marker in content:
            history_text = content.split(history_marker, 1)[1]
            lines = [
                l.strip()
                for l in history_text.split("\n")
                if l.strip() and not l.strip().startswith("#")
            ]
            history = lines[:10]

    _write_md(verdict, reason, assistant_msg, history)
    _write_json(verdict, reason)

    return {
        "systemMessage": "Codex-WikiGuard wrote human_review judgment.",
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
