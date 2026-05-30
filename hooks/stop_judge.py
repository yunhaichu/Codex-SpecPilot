"""StopJudge hook — writes judgment on turn stop.

Reads last_assistant_message from the stop payload,
then writes to .project_wiki/JUDGE.md and judge_latest.json.
Default verdict is always 'human_review' in v1.
"""
import json
import os
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
    """Called when a Codex turn ends (stop signal).
    
    Args:
        turn_payload: dict from Codex containing turn metadata.
                      Expected: 'last_assistant_message' key.
    
    Returns:
        dict with 'verdict', 'reason', 'wiki_updated'.
    """
    # Extract last assistant message
    assistant_msg = turn_payload.get("last_assistant_message", "")
    if isinstance(assistant_msg, list):
        # Convert message objects to string
        assistant_msg = "\n".join(
            m.get("content", "") if isinstance(m, dict) else str(m)
            for m in assistant_msg
        )

    verdict = DEFAULT_VERDICT
    reason = "Default verdict: manual review required before continuing (v1 conservative)."

    # Read existing history
    history = []
    if os.path.isfile(JUDGE_MD):
        content = _read_file(JUDGE_MD)
        # Extract previous history section
        history_marker = "## History"
        if history_marker in content:
            history_text = content.split(history_marker, 1)[1]
            # Remove header lines and blank lines for concise history
            lines = [l.strip() for l in history_text.split("\n") if l.strip() and not l.strip().startswith("#")]
            history = lines[:10]  # Keep last 10 entries

    # Write outputs
    _write_md(verdict, reason, assistant_msg, history)
    _write_json(verdict, reason)

    return {
        "verdict": verdict,
        "reason": reason,
        "wiki_updated": True,
    }


if __name__ == "__main__":
    # Allow standalone test
    result = stop_judge({
        "last_assistant_message": "I will analyze the data and provide a summary."
    })
    print(json.dumps(result, indent=2, ensure_ascii=False))
