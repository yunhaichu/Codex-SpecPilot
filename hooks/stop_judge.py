"""StopJudge hook — writes judgment on turn stop.

Writes to three files:
  - JUDGE.md        (human audit, includes full assistant message)
  - latest_context.md (short summary, NOT injected into next prompt)
  - judge_latest.json (machine-readable)

Returns only a systemMessage. No decision: block. No auto-continue.
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
LATEST_CTX_MD = os.path.join(WIKI_DIR, "latest_context.md")
JUDGE_JSON = os.path.join(WIKI_DIR, "judge_latest.json")


# Recursive guard: skip if child Codex process
if os.environ.get("CODEX_WIKIGUARD_CHILD") == "1":
    print(json.dumps({"systemMessage": "Codex-WikiGuard skipped in child Codex process."}, indent=2, ensure_ascii=False))
    sys.exit(0)

DEFAULT_VERDICT = "human_review"
DEFAULT_REASON = "Default conservative judgment in v1."
NEXT_ACTION = "manual review required before continuing"


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


def _write_context_md(verdict, reason):
    md = f"""# Latest Judge Context

VERDICT: {verdict}
AUTO_CONTINUE: disabled
NEXT_ACTION: {NEXT_ACTION}
REASON: {reason}
"""
    with open(LATEST_CTX_MD, "w", encoding="utf-8") as f:
        f.write(md)


def _write_json(verdict, reason):
    data = {
        "last_verdict": verdict,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "auto_continue": False,
        "next_action": NEXT_ACTION,
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
    reason = DEFAULT_REASON

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
    _write_context_md(verdict, reason)
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
