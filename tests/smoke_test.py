"""Light smoke tests for the Codex SpecPilot unattended loop.

These tests avoid turning SpecPilot back into a large hardcoded permission
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
        env["CODEX_SPECPILOT_CHILD"] = "1"
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
    test("injects SpecPilot context", "Codex SpecPilot" in ctx)
    test("injects start-work instruction", "开始工作" in ctx or "Start Work" in ctx)
    test("injects goal-change rule", "Goal Change Rule" in ctx)
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

            real_patch_result = pre.pre_tool_use({
                "tool": "apply_patch",
                "tool_input": {
                    "command": (
                        "*** Begin Patch\n"
                        "*** Update File: src/main.py\n"
                        "@@\n"
                        "-old\n"
                        "+new\n"
                        "*** End Patch\n"
                    ),
                },
            })
            test("real apply_patch command payload extracts target",
                 real_patch_result == {}, real_patch_result)

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

            self_dev_spec = "# Spec\nspecpilot_self_development\n"
            with open(pre.PROJECT_SPEC_PATH, "w", encoding="utf-8") as f:
                f.write(self_dev_spec)
            hook_config_result = pre.pre_tool_use({
                "tool": "apply_patch",
                "tool_input": {
                    "command": (
                        "*** Begin Patch\n"
                        "*** Update File: %s\n"
                        "@@\n"
                        "+x\n"
                        "*** End Patch\n"
                    ) % os.path.join(ROOT_DIR, ".codex", "hooks.json"),
                },
            })
            test("self-dev absolute hooks.json path is allowed",
                 hook_config_result == {}, hook_config_result)

            with open(pre.PROJECT_SPEC_PATH, "w", encoding="utf-8") as f:
                f.write("# Spec\nsupervised_project_development\n")
            protected_patch = pre.pre_tool_use({
                "tool": "apply_patch",
                "tool_input": {
                    "command": (
                        "*** Begin Patch\n"
                        "*** Update File: .project_wiki/JUDGE.md\n"
                        "@@\n"
                        "+x\n"
                        "*** End Patch\n"
                    ),
                },
            })
            protected_decision = protected_patch.get("hookSpecificOutput", {}).get(
                "permissionDecision"
            )
            test("protected apply_patch command payload is blocked",
                 protected_decision == "deny", protected_patch)
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


def test_stop_prompt_keeps_development_plan_context():
    print("\n[Stop long PROJECT_SPEC context]")
    stop = _load_hook_module("stop_judge")
    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR
    captured = {}
    with tempfile.TemporaryDirectory() as td:
        stop.WIKI_DIR = td
        long_background = "Background detail.\n" * 250
        project_spec = (
            "# PROJECT_SPEC\n\n"
            "0. Project Mode\nsupervised_project_development\n\n"
            "1. Project Goal\nBuild a local iOS app.\n\n"
            "2. Background\n%s\n\n"
            "7. Development Plan\n"
            "* TASK-001: Create app skeleton\n"
            "    * Acceptance: simulator launches the home screen.\n"
            "* TASK-002: Build local dossier models\n"
            "    * Acceptance: model files exist and compile.\n\n"
            "8. Acceptance Criteria\n"
            "* Development Plan 中所有任务均完成。\n"
            "* App can build and run.\n\n"
            "9. Stop Conditions\n"
            "* Needs protected scope change.\n\n"
            "10. Submission Requirements\n"
            "* Generate completion report.\n"
        ) % long_background
        for name, content in {
            "PROJECT_SPEC.md": project_spec,
            "latest_context.md": "# Latest\n",
            "JUDGE.md": "# Judge\n",
            "loop_state.json": '{"loop_count":0,"auto_continue":false}',
        }.items():
            with open(os.path.join(td, name), "w", encoding="utf-8") as f:
                f.write(content)

        try:
            def fake_call(prompt, timeout=120):
                captured["prompt"] = prompt
                return {
                    "ok": True,
                    "content": json.dumps({
                        "verdict": "continue",
                        "reason": "TASK-002 remains",
                        "next_action": "Start TASK-002.",
                        "auto_continue": True,
                    }),
                }

            stop.call_codex_default = fake_call
            result = stop.stop_judge({
                "last_assistant_message": (
                    "TASK-001 done. Next step: start TASK-002."
                )
            })
            prompt = captured.get("prompt", "")
            test("long spec prompt includes later task", "TASK-002" in prompt, prompt[:1000])
            test("long spec prompt includes acceptance criteria",
                 "Acceptance Criteria" in prompt, prompt[:1000])
            test("stop prompt distinguishes task done from project done",
                 "one TASK is done" in prompt and "whole PROJECT_SPEC" in prompt,
                 prompt[:1000])
            test("stop prompt includes GitHub sync boundary",
                 "GitHub sync" in prompt and "local-only" in prompt,
                 prompt[:1000])
            test("long spec continue still blocks next loop",
                 result.get("decision") == "block", result)
        finally:
            stop.call_codex_default = old_call
            stop.WIKI_DIR = old_wiki


def test_stop_loop_limit_counts_stalled_work_only():
    print("\n[Stop loop progress gate]")
    stop = _load_hook_module("stop_judge")
    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR
    with tempfile.TemporaryDirectory() as td:
        stop.WIKI_DIR = td
        for name, content in {
            "PROJECT_SPEC.md": (
                "# PROJECT_SPEC\n\n"
                "7. Development Plan\n"
                "* TASK-005: recording flow\n"
                "* TASK-006: background recording boundary\n\n"
                "8. Acceptance Criteria\n* All tasks complete.\n"
            ),
            "latest_context.md": "# Latest\n",
            "JUDGE.md": "# Judge\n",
            "loop_state.json": '{"loop_count":3,"auto_continue":true}',
        }.items():
            with open(os.path.join(td, name), "w", encoding="utf-8") as f:
                f.write(content)

        try:
            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "verdict": "continue",
                    "reason": "TASK-005 is done and TASK-006 remains",
                    "next_action": "Start TASK-006.",
                    "auto_continue": True,
                    "progress_made": True,
                }),
            }
            progressed = stop.stop_judge({
                "last_assistant_message": "TASK-005 done. Next step: TASK-006."
            })
            test("completed task bypasses stale loop count",
                 progressed.get("decision") == "block", progressed)
            data = json.load(open(os.path.join(td, "judge_latest.json"), encoding="utf-8"))
            test("progress resets loop count", data.get("loop_count") == 0, data)

            with open(os.path.join(td, "loop_state.json"), "w", encoding="utf-8") as f:
                f.write('{"loop_count":3,"auto_continue":true}')
            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "verdict": "continue",
                    "reason": "same step repeated",
                    "next_action": "Retry the same action.",
                    "auto_continue": True,
                    "progress_made": False,
                }),
            }
            stalled = stop.stop_judge({
                "last_assistant_message": "Still could not complete the same action."
            })
            data = json.load(open(os.path.join(td, "judge_latest.json"), encoding="utf-8"))
            test("stalled loop limit still requires human review",
                 data.get("last_verdict") == "human_review" and "systemMessage" in stalled,
                 (data, stalled))
        finally:
            stop.call_codex_default = old_call
            stop.WIKI_DIR = old_wiki


def test_stop_spec_update_required_pauses_worker():
    print("\n[Stop spec update required]")
    stop = _load_hook_module("stop_judge")
    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR
    captured = {}
    with tempfile.TemporaryDirectory() as td:
        stop.WIKI_DIR = td
        for name, content in {
            "PROJECT_SPEC.md": (
                "# PROJECT_SPEC\n\n"
                "7. Development Plan\n"
                "* TASK-001: current work\n"
            ),
            "latest_context.md": "# Latest\n",
            "JUDGE.md": "# Judge\n",
            "loop_state.json": '{"loop_count":1,"auto_continue":true}',
        }.items():
            with open(os.path.join(td, name), "w", encoding="utf-8") as f:
                f.write(content)

        try:
            def fake_call(prompt, timeout=120):
                captured["prompt"] = prompt
                return {
                    "ok": True,
                    "content": json.dumps({
                        "verdict": "spec_update_required",
                        "reason": "user changed acceptance criteria",
                        "next_action": "Pause worker and update PROJECT_SPEC Development Plan.",
                        "auto_continue": False,
                        "progress_made": False,
                        "questions": [
                            "Which acceptance criteria changed?",
                            "Should completed tasks be kept or reworked?",
                        ],
                    }),
                }

            stop.call_codex_default = fake_call
            result = stop.stop_judge({
                "last_assistant_message": (
                    "The user changed the project scope. I did not edit code."
                )
            })
            prompt = captured.get("prompt", "")
            data = json.load(open(os.path.join(td, "judge_latest.json"), encoding="utf-8"))
            ctx = open(os.path.join(td, "latest_context.md"), encoding="utf-8").read()
            loop = json.load(open(os.path.join(td, "loop_state.json"), encoding="utf-8"))
            test("stop prompt exposes spec_update_required verdict",
                 "spec_update_required" in prompt, prompt[:1000])
            test("spec update does not auto-continue",
                 "decision" not in result and data.get("auto_continue") is False,
                 (result, data))
            test("spec update is recorded in latest context",
                 "VERDICT: spec_update_required" in ctx
                 and "AUTO_CONTINUE: disabled" in ctx
                 and "Which acceptance criteria changed?" in ctx,
                 ctx)
            test("spec update resets loop state",
                 loop.get("loop_count") == 0 and loop.get("last_verdict") == "spec_update_required",
                 loop)
            test("spec update questions are shown to the user",
                 "Questions for the user" in result.get("systemMessage", "")
                 and "Which acceptance criteria changed?" in result.get("systemMessage", ""),
                 result)
        finally:
            stop.call_codex_default = old_call
            stop.WIKI_DIR = old_wiki


def test_stop_onboarding_steward_writes_spec():
    print("\n[Stop onboarding steward]")
    stop = _load_hook_module("stop_judge")
    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR
    completed_spec = (
        "# PROJECT_SPEC\n\n"
        "## 0. Project Mode\nsupervised_project_development\n\n"
        "## 1. Project Goal\nBuild a tiny local notes app.\n\n"
        "## 2. Background\nEmpty project.\n\n"
        "## 3. User Requirements\n- REQ-001: Create a local notes app.\n\n"
        "## 4. Non-Goals\n- No cloud sync.\n\n"
        "## 5. Allowed Scope\n- src/\n- tests/\n\n"
        "## 6. Protected Scope\n- .project_wiki/PROJECT_SPEC.md\n- .codex/hooks.json\n- hooks/*.py\n\n"
        "## 7. Development Plan\n"
        "- [ ] TASK-001: Create notes app skeleton\n"
        "  - Goal: Add runnable app files.\n"
        "  - Scope: src/\n"
        "  - Acceptance: App starts.\n"
        "  - Notes: Keep data local.\n\n"
        "## 8. Acceptance Criteria\n- Run tests successfully.\n\n"
        "## 9. Stop Conditions\n- Requirements unclear.\n\n"
        "## GitHub Sync Policy\n- Mode: local-only.\n- No push, tag, or remote operation.\n\n"
        "## 10. Submission Requirements\n- Generate completion report.\n"
    )
    with tempfile.TemporaryDirectory() as td:
        stop.WIKI_DIR = os.path.join(td, ".project_wiki")
        try:
            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "decision": "write_spec",
                    "reason": "enough onboarding facts were confirmed",
                    "questions": [],
                    "updated_project_spec": completed_spec,
                }),
            }
            result = stop.stop_judge({
                "last_assistant_message": (
                    "Confirmed: build a tiny local notes app. Allowed: src/ and tests/. "
                    "Protected: SpecPilot files. Validate by running tests."
                )
            })
            spec_path = os.path.join(td, ".project_wiki", "PROJECT_SPEC.md")
            written = open(spec_path, encoding="utf-8").read()
            ctx = open(os.path.join(td, ".project_wiki", "latest_context.md"),
                       encoding="utf-8").read()
            test("onboarding hook writes completed PROJECT_SPEC",
                 "TASK-001" in written and "NEEDS_USER_CONFIRMATION" not in written,
                 written)
            test("onboarding completion is reported to user",
                 "wrote `.project_wiki/PROJECT_SPEC.md`" in result.get("systemMessage", ""),
                 result)
            test("onboarding completion disables auto-continue",
                 "AUTO_CONTINUE: disabled" in ctx,
                 ctx)
        finally:
            stop.call_codex_default = old_call
            stop.WIKI_DIR = old_wiki


def test_spec_steward_controlled_update_flow():
    print("\n[Spec Steward]")
    steward = _load_hook_module("spec_steward")
    old_call = steward.call_codex_default
    old_wiki = steward.WIKI_DIR
    old_spec_path = steward.PROJECT_SPEC_PATH
    old_latest_path = steward.LATEST_CONTEXT_PATH
    base_spec = (
        "# PROJECT_SPEC\n\n"
        "## 0. Project Mode\nsupervised_project_development\n\n"
        "## 1. Project Goal\nBuild the app.\n\n"
        "## 2. Background\nExisting project.\n\n"
        "## 3. User Requirements\n- REQ-001: Build a local app.\n\n"
        "## 4. Non-Goals\n- No cloud default.\n\n"
        "## 5. Allowed Scope\n- app/\n\n"
        "## 6. Protected Scope\n- .project_wiki/PROJECT_SPEC.md\n\n"
        "## 7. Development Plan\n- [ ] TASK-001: Build app\n\n"
        "## 8. Acceptance Criteria\n- Tests pass.\n\n"
        "## 9. Stop Conditions\n- Need user decision.\n\n"
        "## GitHub Sync Policy\n- Mode: local-only.\n- No push, tag, or remote operation.\n\n"
        "## 10. Submission Requirements\n- Completion report.\n"
    )
    updated_spec = base_spec.replace(
        "- [ ] TASK-001: Build app",
        "- [ ] TASK-001: Build app\n- [ ] TASK-002: Add confirmed offline search"
    )
    with tempfile.TemporaryDirectory() as td:
        steward.WIKI_DIR = td
        steward.PROJECT_SPEC_PATH = os.path.join(td, "PROJECT_SPEC.md")
        steward.LATEST_CONTEXT_PATH = os.path.join(td, "latest_context.md")
        with open(steward.PROJECT_SPEC_PATH, "w", encoding="utf-8") as f:
            f.write(base_spec)
        with open(steward.LATEST_CONTEXT_PATH, "w", encoding="utf-8") as f:
            f.write("VERDICT: spec_update_required\n")

        try:
            def fake_apply(prompt, timeout=120):
                return {
                    "ok": True,
                    "content": json.dumps({
                        "decision": "apply",
                        "reason": "confirmed scope change",
                        "questions": [],
                        "update_summary": "Add offline search task.",
                        "updated_project_spec": updated_spec,
                    }),
                }

            steward.call_codex_default = fake_apply
            dry = steward.propose_spec_update("Add offline search.", apply_update=False)
            current = open(steward.PROJECT_SPEC_PATH, encoding="utf-8").read()
            test("spec steward dry run does not write",
                 dry.get("would_write") is True and dry.get("applied") is False and current == base_spec,
                 dry)

            applied = steward.propose_spec_update("Add offline search.", apply_update=True)
            current = open(steward.PROJECT_SPEC_PATH, encoding="utf-8").read()
            test("spec steward explicit apply writes full spec",
                 applied.get("applied") is True and "TASK-002" in current,
                 (applied, current))

            steward.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "decision": "needs_user_confirmation",
                    "reason": "missing allowed scope",
                    "questions": ["Which files may be changed?"],
                    "update_summary": "",
                    "updated_project_spec": "",
                }),
            }
            ask = steward.propose_spec_update("Add something vague.", apply_update=True)
            test("spec steward asks instead of writing ambiguous changes",
                 ask.get("decision") == "needs_user_confirmation" and ask.get("applied") is False,
                 ask)

            steward.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "decision": "apply",
                    "reason": "bad spec",
                    "questions": [],
                    "update_summary": "",
                    "updated_project_spec": "# PROJECT_SPEC\n\nNo plan.\n",
                }),
            }
            bad = steward.propose_spec_update("Apply bad spec.", apply_update=True)
            test("spec steward rejects incomplete proposed spec",
                 bad.get("ok") is False and "missing" in bad,
                 bad)
        finally:
            steward.call_codex_default = old_call
            steward.WIKI_DIR = old_wiki
            steward.PROJECT_SPEC_PATH = old_spec_path
            steward.LATEST_CONTEXT_PATH = old_latest_path


def test_codex_command_profile_inheritance():
    print("\n[codex exec command]")
    codex_client = _load_hook_module("codex_client")
    old_profile = os.environ.pop("CODEX_PROFILE", None)
    old_wiki_profile = os.environ.pop("CODEX_SPECPILOT_PROFILE", None)
    try:
        test("default command has no profile",
             codex_client.build_codex_exec_command("prompt") == ["codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check", "--disable", "hooks", "--disable", "plugins", "--disable", "apps", "--disable", "memories", "-c", 'model_reasoning_effort="none"', "prompt"])
        os.environ["CODEX_PROFILE"] = "base"
        test("CODEX_PROFILE is inherited",
             codex_client.build_codex_exec_command("prompt") == ["codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check", "--disable", "hooks", "--disable", "plugins", "--disable", "apps", "--disable", "memories", "-c", 'model_reasoning_effort="none"', "--profile", "base", "prompt"])
        os.environ["CODEX_SPECPILOT_PROFILE"] = "wiki"
        test("CODEX_SPECPILOT_PROFILE wins",
             codex_client.build_codex_exec_command("prompt") == ["codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check", "--disable", "hooks", "--disable", "plugins", "--disable", "apps", "--disable", "memories", "-c", 'model_reasoning_effort="none"', "--profile", "wiki", "prompt"])
    finally:
        if old_profile is not None:
            os.environ["CODEX_PROFILE"] = old_profile
        else:
            os.environ.pop("CODEX_PROFILE", None)
        if old_wiki_profile is not None:
            os.environ["CODEX_SPECPILOT_PROFILE"] = old_wiki_profile
        else:
            os.environ.pop("CODEX_SPECPILOT_PROFILE", None)


def test_hooks_json_cross_platform_fields():
    print("\n[hooks.json]")
    hooks_path = os.path.join(ROOT_DIR, ".codex", "hooks.json")
    with open(hooks_path, encoding="utf-8") as f:
        data = json.load(f)

    all_hooks = []
    for groups in data.get("hooks", {}).values():
        for group in groups:
            all_hooks.extend(group.get("hooks", []))

    test("all command hooks include Windows command",
         all(hook.get("commandWindows") for hook in all_hooks), all_hooks)
    stop_hooks = data.get("hooks", {}).get("Stop", [])[0].get("hooks", [])
    test("Stop hook timeout is at least 60 seconds",
         stop_hooks and stop_hooks[0].get("timeout", 0) >= 60, stop_hooks)


def test_project_path_resolution():
    print("\n[project path resolution]")
    project_paths = _load_hook_module("project_paths")
    old_project_dir = os.environ.pop("CODEX_SPECPILOT_PROJECT_DIR", None)
    old_cwd = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as td:
            wiki = os.path.realpath(os.path.join(td, ".project_wiki"))
            os.mkdir(wiki)

            os.environ["CODEX_SPECPILOT_PROJECT_DIR"] = td
            test("project dir env selects target wiki",
                 project_paths.wiki_dir() == wiki,
                 project_paths.wiki_dir())

            os.environ.pop("CODEX_SPECPILOT_PROJECT_DIR", None)
            os.chdir(td)
            test("cwd selects target wiki",
                 project_paths.wiki_dir() == wiki,
                 project_paths.wiki_dir())

        with tempfile.TemporaryDirectory() as td:
            os.chdir(td)
            expected = os.path.realpath(os.path.join(td, ".project_wiki"))
            test("cwd without wiki can be selected for auto-onboarding",
                 os.path.realpath(project_paths.wiki_dir()) == expected,
                 project_paths.wiki_dir())
    finally:
        os.chdir(old_cwd)
        if old_project_dir is not None:
            os.environ["CODEX_SPECPILOT_PROJECT_DIR"] = old_project_dir
        else:
            os.environ.pop("CODEX_SPECPILOT_PROJECT_DIR", None)


def test_project_injector_bootstrap_and_onboarding():
    print("\n[Project injector]")
    injector = _load_hook_module("project_injector")

    with tempfile.TemporaryDirectory() as empty_dir:
        empty_info = injector.inspect_project(empty_dir)
        test("empty project is detected",
             empty_info.get("project_kind") == "empty",
             empty_info)
        empty_questions = injector.onboarding_questions(empty_info)
        test("empty project questions ask final goal",
             any("最终" in q or "final" in q.lower() for q in empty_questions),
             empty_questions)
        test("empty project questions ask GitHub sync policy",
             any("GitHub" in q and "local-only" in q and "token" in q for q in empty_questions),
             empty_questions)

    with tempfile.TemporaryDirectory() as existing_dir:
        with open(os.path.join(existing_dir, "package.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        os.mkdir(os.path.join(existing_dir, "src"))
        existing_info = injector.inspect_project(existing_dir)
        test("existing project is detected",
            existing_info.get("project_kind") == "existing"
             and "node" in existing_info.get("signals", []),
             existing_info)
        existing_questions = injector.onboarding_questions(existing_info)
        test("existing project questions ask GitHub sync policy",
             any("GitHub" in q and "公开" in q and "私有" in q for q in existing_questions),
             existing_questions)
        wiki_only = injector.bootstrap_wiki_files(existing_dir)
        test("wiki bootstrap writes task-contract placeholder only",
             ".project_wiki/PROJECT_SPEC.md" in wiki_only.get("written", [])
             and not any(path.startswith("hooks/") for path in wiki_only.get("written", [])),
             wiki_only)
        result = injector.bootstrap_project(existing_dir)
        test("bootstrap writes hooks and codex config",
             "hooks/stop_judge.py" in result.get("written", [])
             and ".codex/hooks.json" in result.get("written", []),
             result)
        test("bootstrap writes onboarding placeholder spec",
             os.path.isfile(os.path.join(existing_dir, ".project_wiki", "PROJECT_SPEC.md"))
             and injector.ONBOARDING_MARKER in open(
                 os.path.join(existing_dir, ".project_wiki", "PROJECT_SPEC.md"),
                 encoding="utf-8",
             ).read(),
             result)

        # Exercise target injection directly because _run_hook uses this repo's wiki.
        user_prompt = _load_hook_module("user_prompt_submit")
        old_wiki = user_prompt.WIKI_DIR
        try:
            user_prompt.WIKI_DIR = os.path.join(existing_dir, ".project_wiki")
            injected = user_prompt.user_prompt_submit({"prompt": "开始工作"})
            ctx = injected.get("hookSpecificOutput", {}).get("additionalContext", "")
            test("placeholder spec triggers onboarding injection",
                 "Project Onboarding Rule" in ctx and "Do not edit business code" in ctx,
                 ctx[:1000])
            test("onboarding injection includes GitHub local-only default",
                 "GitHub" in ctx and "local-only" in ctx,
                 ctx[:1200])
            test("start work is deferred during onboarding",
                 "Start Work Deferred" in ctx and "Start Work Instruction" not in ctx,
                 ctx[:1000])
        finally:
            user_prompt.WIKI_DIR = old_wiki

    with tempfile.TemporaryDirectory() as takeover_dir:
        with open(os.path.join(takeover_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write("# Old project\n")
        user_prompt = _load_hook_module("user_prompt_submit")
        old_wiki = user_prompt.WIKI_DIR
        try:
            user_prompt.WIKI_DIR = os.path.join(takeover_dir, ".project_wiki")
            injected = user_prompt.user_prompt_submit({"prompt": "接管这个项目"})
            ctx = injected.get("hookSpecificOutput", {}).get("additionalContext", "")
            test("UserPromptSubmit auto-creates missing project wiki",
                 os.path.isfile(os.path.join(takeover_dir, ".project_wiki", "PROJECT_SPEC.md"))
                 and "Project Onboarding Rule" in ctx,
                 ctx[:1000])
        finally:
            user_prompt.WIKI_DIR = old_wiki


def main():
    print("=== Codex SpecPilot Light Smoke Tests ===")
    test_user_prompt_submit()
    test_pre_tool_guard_light_boundary()
    test_stop_auto_continue_and_done_helpers()
    test_stop_prompt_keeps_development_plan_context()
    test_stop_loop_limit_counts_stalled_work_only()
    test_stop_spec_update_required_pauses_worker()
    test_stop_onboarding_steward_writes_spec()
    test_spec_steward_controlled_update_flow()
    test_codex_command_profile_inheritance()
    test_hooks_json_cross_platform_fields()
    test_project_path_resolution()
    test_project_injector_bootstrap_and_onboarding()
    print("\n=== Results ===")
    print("Passed: %d, Failed: %d" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
