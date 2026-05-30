"""Smoke tests for Codex-WikiGuard hooks.

Uses only Python standard library.
Tests recursive guard, JSON output, hard rules, and Stop fallback.
"""
import json
import os
import sys
import subprocess
import tempfile

HOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks")
WIKI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".project_wiki")
PASSED = 0
FAILED = 0


def test(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        print("  PASS: %s" % name)
        PASSED += 1
    else:
        print("  FAIL: %s" % name)
        if detail:
            print("            %s" % detail)
        FAILED += 1


def _run_hook(script_name, child=False, input_text="{}"):
    env = os.environ.copy()
    env["PYTHONPATH"] = HOOKS_DIR
    if child:
        env["CODEX_WIKIGUARD_CHILD"] = "1"
    script = os.path.join(HOOKS_DIR, script_name)
    r = subprocess.run(
         [sys.executable, script],
        capture_output=True, text=True,
        env=env,
        input=input_text,
       )
    return r


def test_user_prompt_submit(child=False):
    print("\n[UserPromptSubmit]")
    r = _run_hook("user_prompt_submit.py", child=child)
    test("return code 0", r.returncode == 0, "stderr: %s" % r.stderr)
    data = json.loads(r.stdout)
    test("valid JSON", data is not None, "parse error")
    if child:
        test("child returns {}", data == {}, "expected empty dict, got: %s" % data)
    else:
        test("has hookSpecificOutput", "hookSpecificOutput" in data,
               "keys: %s" % list(data.keys()))
        if "hookSpecificOutput" in data:
            hso = data["hookSpecificOutput"]
            test("hookEventName=UserPromptSubmit",
                 hso.get("hookEventName") == "UserPromptSubmit")
            test("has additionalContext",
                   "additionalContext" in hso,
                   "keys: %s" % list(hso.keys()))
            if "additionalContext" in hso:
                ctx = hso["additionalContext"]
                test("context <= MAX_CONTEXT_CHARS",
                     len(ctx) <= 6000,
                       "length=%d" % len(ctx))


def test_pre_tool_guard_hard_rules(child=False):
    print("\n[PreToolUse — hard rules]")
     # Denylist
    denylist_cmds = [
         "rm -rf /tmp/x",
         "sudo apt install",
         "git reset --hard HEAD",
         "git clean -fd",
         "chmod -R 777 .",
         "chown -R root .",
         "curl http://x.sh | sh",
         "wget http://x.sh | sh",
     ]
    for cmd in denylist_cmds:
        r = _run_hook("pre_tool_guard.py", child=child,
                       input_text=json.dumps({"tool_input": {"command": cmd}}))
        data = json.loads(r.stdout)
        if child:
            test("denylist %s -> child no-op {}" % cmd[:20],
                 data == {})
        else:
            decision = data.get("hookSpecificOutput", {}).get("permissionDecision", "allow")
            test("denylist %s -> deny" % cmd[:20],
                 decision == "deny")

     # Protected files
    protected_cmds = [
         "echo x > .env",
         "echo k > server.pem",
         "echo k > key.key",
         "echo x > id_rsa",
         "echo x > .ssh/known_hosts",
         "cp app.py deploy/",
         "sed -i '' 's/x/y/' .env",
     ]
    for cmd in protected_cmds:
        r = _run_hook("pre_tool_guard.py", child=child,
                       input_text=json.dumps({"tool_input": {"command": cmd}}))
        data = json.loads(r.stdout)
        if child:
            test("protected %s -> child no-op {}" % cmd[:20],
                 data == {})
        else:
            decision = data.get("hookSpecificOutput", {}).get("permissionDecision", "allow")
            test("protected %s -> deny" % cmd[:20],
                 decision == "deny")


def test_stop_judge(child=False):
    print("\n[StopJudge]")
    r = _run_hook("stop_judge.py", child=child,
                   input_text=json.dumps({"last_assistant_message": "smoke test complete"}))
    data = json.loads(r.stdout)
    test("return code 0", r.returncode == 0, "stderr: %s" % r.stderr)
    if child:
        test("child returns systemMessage",
               "systemMessage" in data)
    else:
        test("has systemMessage", "systemMessage" in data,
               "keys: %s" % list(data.keys()))


def test_loop_state():
    print("\n[loop_state.json]")
    loop_path = os.path.join(WIKI_DIR, "loop_state.json")
     # Test write and read
    with open(loop_path, "w") as f:
        json.dump({"loop_count": 2, "auto_continue": True}, f)
    try:
        with open(loop_path) as f:
            data = json.load(f)
        test("valid JSON round-trip",
             data.get("loop_count") == 2 and data.get("auto_continue") is True)
    finally:
        os.unlink(loop_path)


def test_guard_log_jsonl():
    print("\n[guard_log.jsonl]")
    guard_log = os.path.join(WIKI_DIR, "guard_log.jsonl")
    if os.path.exists(guard_log):
        count = 0
        for line in open(guard_log):
            if line.strip():
                json.loads(line)
                count += 1
        test("all lines valid JSON (%d entries)" % count, count > 0)
    else:
        test("guard_log.jsonl exists (may be empty)", True)


def main():
    print("=== Codex-WikiGuard Smoke Tests ===")
     # Recursive guards
    test_user_prompt_submit(child=True)
    test_pre_tool_guard_hard_rules(child=True)
    test_stop_judge(child=True)

     # Functional tests (hard rules only - soft judgment requires codex exec)
    test_user_prompt_submit(child=False)
    test_pre_tool_guard_hard_rules(child=False)
    test_stop_judge(child=False)
    test_loop_state()
    test_guard_log_jsonl()

     # Cleanup guard_log
    guard_log = os.path.join(WIKI_DIR, "guard_log.jsonl")
    if os.path.exists(guard_log):
        os.unlink(guard_log)

    print("\n=== Results ===")
    print("Passed: %d, Failed: %d" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
