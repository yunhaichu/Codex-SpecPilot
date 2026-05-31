"""Light smoke tests for the Codex WikiGuard unattended loop.

These tests avoid turning WikiGuard back into a large hardcoded permission
engine. They verify the thin control loop: prompt injection, recursive guards,
judge-system boundary, AI decision plumbing, Stop auto-continue, and completion
report writing.
"""
import importlib
import json
import os
import subprocess
import sys
import tempfile

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS_DIR = os.path.join(ROOT_DIR, "hooks")
WIKI_DIR = os.path.join(ROOT_DIR, ".project_wiki")
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
            print("              %s" % detail)
        FAILED += 1


def _run_hook(script_name, child=False, input_text="{}"):
    env = os.environ.copy()
    env["PYTHONPATH"] = HOOKS_DIR
    if child:
        env["CODEX_WIKIGUARD_CHILD"] = "1"
    return subprocess.run(
        [sys.executable, os.path.join(HOOKS_DIR, script_name)],
        capture_output=True,
        text=True,
        env=env,
        input=input_text,
    )


def _load_hook_module(name):
    sys.path.insert(0, HOOKS_DIR)
    return importlib.import_module(name)


def test_user_prompt_submit():
    print("\n[UserPromptSubmit]")
    r = _run_hook("user_prompt_submit.py", input_text=json.dumps({"prompt": "开始工作"}))
    test("return code 0", r.returncode == 0, r.stderr)
    data = json.loads(r.stdout)
    ctx = data.get("hookSpecificOutput", {}).get("additionalContext", "")
    test("injects WikiGuard context", "Codex WikiGuard" in ctx)
    test("injects start-work instruction", "开始工作" in ctx or "Start Work" in ctx)
    test("context stays short", len(ctx) <= 6000, "length=%d" % len(ctx))

    child = _run_hook("user_prompt_submit.py", child=True)
    test("child user prompt hook is no-op", json.loads(child.stdout) == {})


def test_pre_tool_guard_light_boundary():
    print("\n[PreToolUse]")
    pre = _load_hook_module("pre_tool_guard")
    old_call = pre.call_codex_default
    old_wiki = pre.WIKI_DIR
    old_guard_log = pre.GUARD_LOG
    old_project_spec = pre.PROJECT_SPEC_PATH
    try:
        with tempfile.TemporaryDirectory() as td:
            pre.WIKI_DIR = td
            pre.GUARD_LOG = os.path.join(td, "guard_log.jsonl")
            pre.PROJECT_SPEC_PATH = os.path.join(td, "PROJECT_SPEC.md")
            with open(pre.PROJECT_SPEC_PATH, "w", encoding="utf-8") as f:
                f.write("# Spec\nsupervised_project_development\n")

            pre.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": '{"decision":"allow","reason":"ok"}',
            }

            read_result = pre.pre_tool_use({"tool_input": {"command": "ls .project_wiki"}})
            test("read-only command does not call AI or block", read_result == {})

            business_result = pre.pre_tool_use({
                "tool": "apply_patch",
                "tool_input": {"target_file": "src/main.py", "patch": "*** Update File: src/main.py\n"},
            })
            test("ordinary business write can be AI-allowed", business_result == {})

            blocked = pre.pre_tool_use({
                "tool": "apply_patch",
                "tool_input": {"target_file": ".project_wiki/JUDGE.md", "patch": ""},
            })
            decision = blocked.get("hookSpecificOutput", {}).get("permissionDecision")
            reason = blocked.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
            test("judge-system file is blocked", decision == "deny", blocked)
            test("boundary reason is explicit", "judge system" in reason)

            win_blocked = pre.pre_tool_use({
                "tool": "Write",
                "tool_input": {"file_path": ".project_wiki\\JUDGE.md", "content": "x"},
            })
            win_decision = win_blocked.get("hookSpecificOutput", {}).get("permissionDecision")
            test("Windows-style judge-system path is blocked", win_decision == "deny", win_blocked)
    finally:
        pre.call_codex_default = old_call
        pre.WIKI_DIR = old_wiki
        pre.GUARD_LOG = old_guard_log
        pre.PROJECT_SPEC_PATH = old_project_spec

    child = _run_hook("pre_tool_guard.py", child=True)
    test("child pre-tool hook is no-op", json.loads(child.stdout) == {})


def test_stop_auto_continue_and_done_helpers():
    print("\n[Stop]")
    stop = _load_hook_module("stop_judge")
    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR
    with tempfile.TemporaryDirectory() as td:
        stop.WIKI_DIR = td
        for name, content in {
            "PROJECT_SPEC.md": "# Spec\n- [ ] TASK-001: do work\n",
            "latest_context.md": "# Latest\n",
            "JUDGE.md": "# Judge\n",
            "loop_state.json": '{"loop_count":0,"auto_continue":false}',
        }.items():
            with open(os.path.join(td, name), "w", encoding="utf-8") as f:
                f.write(content)

        try:
            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "verdict": "continue",
                    "reason": "more implementation is needed",
                    "next_action": "Implement TASK-001 and run validation.",
                    "auto_continue": True,
                }),
            }
            cont = stop.stop_judge({"last_assistant_message": "Implemented part of TASK-001."})
            test("continue returns decision:block", cont.get("decision") == "block", cont)
            ctx = open(os.path.join(td, "latest_context.md"), encoding="utf-8").read()
            test("latest_context records enabled auto-continue", "AUTO_CONTINUE: enabled" in ctx)

            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "verdict": "done",
                    "reason": "all acceptance criteria are satisfied",
                    "next_action": "",
                    "auto_continue": False,
                }),
            }
            done = stop.stop_judge({"last_assistant_message": "All tasks are complete."})
            test("done does not block", "systemMessage" in done and "done" in done["systemMessage"])
            report = open(os.path.join(td, "COMPLETION_REPORT.md"), encoding="utf-8").read()
            test("done writes completion report", "Stop Hook Done Record" in report)
        finally:
            stop.call_codex_default = old_call
            stop.WIKI_DIR = old_wiki

    child = _run_hook("stop_judge.py", child=True)
    test("child stop hook is no-op", json.loads(child.stdout) == {})


def test_codex_command_profile_inheritance():
    print("\n[codex exec command]")
    codex_client = _load_hook_module("codex_client")
    old_profile = os.environ.pop("CODEX_PROFILE", None)
    old_wiki_profile = os.environ.pop("CODEX_WIKIGUARD_PROFILE", None)
    try:
        test("default command has no profile",
             codex_client.build_codex_exec_command("prompt") == ["codex", "exec", "--skip-git-repo-check", "prompt"])
        os.environ["CODEX_PROFILE"] = "base"
        test("CODEX_PROFILE is inherited",
             codex_client.build_codex_exec_command("prompt") == ["codex", "exec", "--skip-git-repo-check", "--profile", "base", "prompt"])
        os.environ["CODEX_WIKIGUARD_PROFILE"] = "wiki"
        test("CODEX_WIKIGUARD_PROFILE wins",
             codex_client.build_codex_exec_command("prompt") == ["codex", "exec", "--skip-git-repo-check", "--profile", "wiki", "prompt"])
    finally:
        if old_profile is not None:
            os.environ["CODEX_PROFILE"] = old_profile
        else:
            os.environ.pop("CODEX_PROFILE", None)
        if old_wiki_profile is not None:
            os.environ["CODEX_WIKIGUARD_PROFILE"] = old_wiki_profile
        else:
            os.environ.pop("CODEX_WIKIGUARD_PROFILE", None)


def test_project_path_resolution():
    print("\n[project path resolution]")
    project_paths = _load_hook_module("project_paths")
    old_project_dir = os.environ.pop("CODEX_WIKIGUARD_PROJECT_DIR", None)
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as td:
            wiki = os.path.realpath(os.path.join(td, ".project_wiki"))
            os.mkdir(wiki)

            os.environ["CODEX_WIKIGUARD_PROJECT_DIR"] = td
            test("project dir env selects target wiki",
                 project_paths.wiki_dir() == wiki,
                 project_paths.wiki_dir())

            os.environ.pop("CODEX_WIKIGUARD_PROJECT_DIR", None)
            os.chdir(td)
            test("cwd selects target wiki",
                 project_paths.wiki_dir() == wiki,
                 project_paths.wiki_dir())
    finally:
        os.chdir(old_cwd)
        if old_project_dir is not None:
            os.environ["CODEX_WIKIGUARD_PROJECT_DIR"] = old_project_dir
        else:
            os.environ.pop("CODEX_WIKIGUARD_PROJECT_DIR", None)


def main():
    print("=== Codex-WikiGuard Light Smoke Tests ===")
    test_user_prompt_submit()
    test_pre_tool_guard_light_boundary()
    test_stop_auto_continue_and_done_helpers()
    test_codex_command_profile_inheritance()
    test_project_path_resolution()
    print("\n=== Results ===")
    print("Passed: %d, Failed: %d" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
