"""Codex client - calls codex exec using the default model and config.

No model parameter, no API base URL, no API key.
Child Codex inherits parent default model and configuration.
"""
import json
import os
import queue
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
try:
    from project_paths import wiki_dir
except ModuleNotFoundError:
    from hooks.project_paths import wiki_dir

WIKI_DIR = wiki_dir()

LOOP_STATE_PATH = os.path.join(WIKI_DIR, "loop_state.json")
MAX_LOOP_COUNT = 3


def _read_stream_lines(stream, stream_name, output_queue):
    try:
        for line in iter(stream.readline, ""):
            output_queue.put((stream_name, line))
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _drain_output_queue(output_queue, stdout_lines, stderr_lines):
    while True:
        try:
            stream_name, line = output_queue.get_nowait()
        except queue.Empty:
            return
        if stream_name == "stdout":
            stdout_lines.append(line)
        else:
            stderr_lines.append(line)


def _terminate_process(proc, grace_seconds=2.0):
    if proc.poll() is not None:
        return

    if os.name != "nt":
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        except Exception:
            proc.terminate()
    else:
        proc.terminate()

    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.05)

    if proc.poll() is not None:
        return

    if os.name != "nt":
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except Exception:
            proc.kill()
    else:
        proc.kill()

    try:
        proc.wait(timeout=1)
    except Exception:
        pass


def _parse_agent_message(line):
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(event, dict):
        return None
    item = event.get("item", {})
    if (
        event.get("type") == "item.completed"
        and isinstance(item, dict)
        and item.get("type") == "agent_message"
    ):
        return item.get("text", "").strip()
    return None



def _profile_from_env():
    return os.environ.get("CODEX_SPECPILOT_PROFILE") or os.environ.get("CODEX_PROFILE")


def _child_env_enabled():
    return os.environ.get("CODEX_SPECPILOT_CHILD") == "1"


def build_codex_exec_command(prompt):
    """Build the codex exec command, inheriting profile from environment variables.

    Priority:
    1. CODEX_SPECPILOT_PROFILE (highest)
    2. CODEX_PROFILE
    3. None (default)

    Never hardcodes a profile name in this file.
    """
    profile = _profile_from_env()
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
    if _child_env_enabled():
        return {
            "ok": False,
            "content": "",
            "error": "recursive guard: skipped codex exec in child process",
            "profile": None,
            "command_mode": "default",
        }

    cmd = build_codex_exec_command(prompt)
    profile = _profile_from_env()
    command_mode = "profile" if profile else "default"

    try:
        env = {
            **os.environ,
            "CODEX_SPECPILOT_CHILD": "1",
            "PYTHONUNBUFFERED": "1",
        }
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=WIKI_DIR,
            env=env,
            start_new_session=(os.name != "nt"),
        )
        output_queue = queue.Queue()
        stdout_lines = []
        stderr_lines = []
        stdout_thread = threading.Thread(
            target=_read_stream_lines,
            args=(proc.stdout, "stdout", output_queue),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_read_stream_lines,
            args=(proc.stderr, "stderr", output_queue),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        deadline = time.monotonic() + timeout
        while proc.poll() is None:
            remaining = max(0.0, min(0.05, deadline - time.monotonic()))
            try:
                stream_name, line = output_queue.get(timeout=remaining)
            except queue.Empty:
                if time.monotonic() >= deadline:
                    _terminate_process(proc)
                    stdout_thread.join(timeout=0.5)
                    stderr_thread.join(timeout=0.5)
                    _drain_output_queue(output_queue, stdout_lines, stderr_lines)
                    stdout = "".join(stdout_lines)
                    stderr = "".join(stderr_lines)
                    return {
                        "ok": False,
                        "content": "",
                        "error": "codex exec timed out",
                        "profile": profile,
                        "command_mode": command_mode,
                        "raw_stdout": stdout[-2000:],
                        "raw_stderr": stderr[-2000:],
                    }
                continue

            if stream_name == "stdout":
                stdout_lines.append(line)
                content = _parse_agent_message(line)
                if content is not None:
                    _terminate_process(proc)
                    stdout_thread.join(timeout=0.5)
                    stderr_thread.join(timeout=0.5)
                    _drain_output_queue(output_queue, stdout_lines, stderr_lines)
                    return {
                        "ok": True,
                        "content": content,
                        "error": None,
                        "profile": profile,
                        "command_mode": command_mode,
                    }
            else:
                stderr_lines.append(line)

        stdout_thread.join(timeout=0.5)
        stderr_thread.join(timeout=0.5)
        _drain_output_queue(output_queue, stdout_lines, stderr_lines)
        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)

        stdout_lines = (stdout or "").splitlines(True)
        for line in stdout_lines:
            content = _parse_agent_message(line)
            if content is not None:
                return {
                    "ok": True,
                    "content": content,
                    "error": None,
                    "profile": profile,
                    "command_mode": command_mode,
                }

        returncode = proc.returncode
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
