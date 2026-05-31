"""Codex client - calls codex exec using the default model and config.

No model parameter, no API base URL, no API key.
Child Codex inherits parent default model and configuration.
"""
import json
import os
import subprocess
from datetime import datetime, timezone
try:
    from project_paths import wiki_dir
except ModuleNotFoundError:
    from hooks.project_paths import wiki_dir

WIKI_DIR = wiki_dir()

LOOP_STATE_PATH = os.path.join(WIKI_DIR, "loop_state.json")
MAX_LOOP_COUNT = 3


def build_codex_exec_command(prompt):
    """Build the codex exec command, inheriting profile from environment variables.

    Priority:
    1. CODEX_WIKIGUARD_PROFILE (highest)
    2. CODEX_PROFILE
    3. None (default)

    Never hardcodes a profile name in this file.
    """
    profile = os.environ.get("CODEX_WIKIGUARD_PROFILE") or os.environ.get("CODEX_PROFILE")
    base = [
        "codex", "exec", "--json", "--ephemeral",
        "--skip-git-repo-check", "--disable", "hooks",
        "--disable", "plugins", "--disable", "apps", "--disable", "memories",
        "-c", 'model_reasoning_effort="none"',
    ]
    if profile:
        return base + ["--profile", profile, prompt]
    return base + [prompt]


def call_codex_default(prompt, timeout=120):
    """Call codex exec with the default model. No -m flag.

    Returns:
        {"ok": True, "content": "...", "error": None, "profile": "<name>", "command_mode": "default | profile"}  on success
        {"ok": False, "content": "", "error": "...", "profile": "<name>", "command_mode": "default | profile"}    on failure
    """
    if os.environ.get("CODEX_WIKIGUARD_CHILD") == "1":
        return {
            "ok": False,
            "content": "",
            "error": "recursive guard: skipped codex exec in child process",
            "profile": None,
            "command_mode": "default",
        }

    cmd = build_codex_exec_command(prompt)
    profile = os.environ.get("CODEX_WIKIGUARD_PROFILE") or os.environ.get("CODEX_PROFILE")
    command_mode = "profile" if profile else "default"

    try:
        env = {
            **os.environ,
            "CODEX_WIKIGUARD_CHILD": "1",
            "PYTHONUNBUFFERED": "1",
        }
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=WIKI_DIR,
            env=env,
        )
        stdout_lines = []
        assert proc.stdout is not None
        for line in proc.stdout:
            stdout_lines.append(line)
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            item = event.get("item", {}) if isinstance(event, dict) else {}
            if event.get("type") == "item.completed" and item.get("type") == "agent_message":
                content = item.get("text", "").strip()
                proc.kill()
                proc.wait(timeout=1)
                return {
                    "ok": True,
                    "content": content,
                    "error": None,
                    "profile": profile,
                    "command_mode": command_mode,
                }

        stderr = proc.stderr.read() if proc.stderr is not None else ""
        returncode = proc.wait(timeout=timeout)
        if returncode == 0:
            return {
                "ok": True,
                "content": "".join(stdout_lines).strip(),
                "error": None,
                "profile": profile,
                "command_mode": command_mode,
            }
        return {
            "ok": False,
            "content": "",
            "error": "codex exec returned %d: %s" % (returncode, stderr.strip()),
            "profile": profile,
            "command_mode": command_mode,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "content": "",
            "error": "codex exec timed out",
            "profile": profile,
            "command_mode": command_mode,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "content": "",
            "error": "codex command not found",
            "profile": profile,
            "command_mode": command_mode,
        }
    except Exception as e:
        return {
            "ok": False,
            "content": "",
            "error": str(e),
            "profile": profile,
            "command_mode": command_mode,
        }


def _read_loop_state():
    try:
        with open(os.path.join(WIKI_DIR, "loop_state.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            return int(data.get("loop_count", 0))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return 0


def _write_loop_state(count, auto_continue, verdict="human_review"):
    ts = datetime.now(timezone.utc).isoformat()
    data = {
        "loop_count": count,
        "auto_continue": auto_continue,
        "last_verdict": verdict,
        "updated_at": ts,
    }
    with open(os.path.join(WIKI_DIR, "loop_state.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def check_auto_continue():
    """Check loop state and decide whether to allow auto-continue."""
    loop_count = _read_loop_state()
    if loop_count >= MAX_LOOP_COUNT:
        return {
            "continue": False,
            "action": "loop limit (%d) reached, human_review required" % MAX_LOOP_COUNT,
        }
    return {"continue": True, "action": ""}
