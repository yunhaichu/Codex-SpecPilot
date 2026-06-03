"""Light smoke tests for the Codex SpecPilot unattended loop.

These tests avoid turning SpecPilot back into a large hardcoded permission
engine. They verify the thin control loop: prompt injection, recursive guards,
judge-system boundary, AI decision plumbing, Stop auto-continue, and completion
report writing.
"""
import importlib
import importlib.util
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


def _load_module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _complete_project_spec(plan="- [ ] TASK-001: Build app", acceptance="- Tests pass."):
    return (
        "# PROJECT_SPEC\n\n"
        "## 0. Project Mode\nsupervised_project_development\n\n"
        "## 1. Project Goal\nBuild the app.\n\n"
        "## 2. Background\nLocal supervised project.\n\n"
        "## 3. User Requirements\n- REQ-001: Complete the Development Plan.\n\n"
        "## 4. Non-Goals\n- No cloud default.\n\n"
        "## 5. Allowed Scope\n- src/\n- tests/\n- README.md\n\n"
        "## 6. Protected Scope\n- .project_wiki/PROJECT_SPEC.md\n- .codex/hooks.json\n- hooks/*.py\n\n"
        "## 7. Development Plan\n%s\n\n"
        "## 8. Acceptance Criteria\n%s\n\n"
        "## 9. Stop Conditions\n- Need user decision.\n\n"
        "## GitHub Sync Policy\n- Mode: local-only.\n- No push, tag, release, or remote operation.\n\n"
        "## 10. Submission Requirements\n- Report status.\n"
    ) % (plan, acceptance)


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

    user_prompt = _load_hook_module("user_prompt_submit")
    old_wiki = user_prompt.WIKI_DIR
    with tempfile.TemporaryDirectory() as td:
        wiki = os.path.join(td, ".project_wiki")
        os.makedirs(wiki)
        user_prompt.WIKI_DIR = wiki
        try:
            with open(os.path.join(wiki, "PROJECT_SPEC.md"), "w", encoding="utf-8") as f:
                f.write(_complete_project_spec())
            with open(os.path.join(wiki, "INJECTION.md"), "w", encoding="utf-8") as f:
                f.write("# Codex SpecPilot\n\n" + ("long base context\n" * 500))
            with open(os.path.join(wiki, "latest_context.md"), "w", encoding="utf-8") as f:
                f.write(
                    "VERDICT: spec_update_required\n"
                    "NEXT_ACTION: Add TASK-099 for export.\n"
                    "REASON: User requested a contract update.\n"
                )
            injected = user_prompt.user_prompt_submit({"prompt": "同意"})
            latest_ctx = injected.get("hookSpecificOutput", {}).get("additionalContext", "")
            test("latest spec-update context survives truncation for confirmation",
                 "VERDICT: spec_update_required" in latest_ctx
                 and "Add TASK-099" in latest_ctx
                 and len(latest_ctx) <= user_prompt.MAX_CONTEXT_CHARS,
                 latest_ctx[:1000])
        finally:
            user_prompt.WIKI_DIR = old_wiki


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

            template_result = pre.pre_tool_use({
                "tool": "apply_patch",
                "tool_input": {
                    "command": (
                        "*** Begin Patch\n"
                        "*** Update File: %s\n"
                        "@@\n"
                        "+experience evaluation\n"
                        "*** End Patch\n"
                    ) % os.path.join(ROOT_DIR, ".project_wiki", "COMPLETION_REPORT_TEMPLATE.md"),
                },
            })
            test("self-dev completion template path is allowed",
                 template_result == {}, template_result)

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

            absolute_hook_patch = pre.pre_tool_use({
                "tool": "apply_patch",
                "tool_input": {
                    "command": (
                        "*** Begin Patch\n"
                        "*** Update File: %s\n"
                        "@@\n"
                        "+x\n"
                        "*** End Patch\n"
                    ) % os.path.join(ROOT_DIR, "hooks", "stop_judge.py"),
                },
            })
            absolute_hook_decision = absolute_hook_patch.get("hookSpecificOutput", {}).get(
                "permissionDecision"
            )
            test("absolute hooks/*.py path is blocked outside self-dev",
                 absolute_hook_decision == "deny", absolute_hook_patch)
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
            "PROJECT_SPEC.md": _complete_project_spec("- [ ] TASK-001: do work"),
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
                    "auto_continue": False,
                }),
            }
            cont = stop.stop_judge({"last_assistant_message": "Implemented part of TASK-001."})
            test("continue returns decision:block", cont.get("decision") == "block", cont)
            test("decision:block carries explicit next_action",
                 cont.get("reason") == "NEXT_ACTION: Implement TASK-001 and run validation.",
                 cont)
            data = json.load(open(os.path.join(td, "judge_latest.json"), encoding="utf-8"))
            loop = json.load(open(os.path.join(td, "loop_state.json"), encoding="utf-8"))
            test("continue records next_action and auto_continue",
                 data.get("next_action") == "Implement TASK-001 and run validation."
                 and data.get("auto_continue") is True
                 and data.get("loop_count") == 1,
                 data)
            test("continue increments loop_state",
                 loop.get("loop_count") == 1 and loop.get("auto_continue") is True,
                 loop)
            ctx = open(os.path.join(td, "latest_context.md"), encoding="utf-8").read()
            test("latest_context records enabled auto-continue",
                 "AUTO_CONTINUE: enabled" in ctx
                 and "NEXT_ACTION: Implement TASK-001 and run validation." in ctx,
                 ctx)

            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "verdict": "revise",
                    "reason": "validation needs a correction",
                    "next_action": "Revise TASK-001 validation and rerun tests.",
                    "auto_continue": False,
                }),
            }
            rev = stop.stop_judge({"last_assistant_message": "Validation exposed a task issue."})
            test("revise returns decision:block", rev.get("decision") == "block", rev)
            test("revise block carries explicit next_action",
                 rev.get("reason") == "NEXT_ACTION: Revise TASK-001 validation and rerun tests.",
                 rev)
            data = json.load(open(os.path.join(td, "judge_latest.json"), encoding="utf-8"))
            loop = json.load(open(os.path.join(td, "loop_state.json"), encoding="utf-8"))
            test("revise increments loop_state",
                 data.get("last_verdict") == "revise"
                 and data.get("loop_count") == 2
                 and loop.get("loop_count") == 2
                 and loop.get("auto_continue") is True,
                 (data, loop))

            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "verdict": "continue",
                    "reason": "missing action",
                    "next_action": "",
                    "auto_continue": True,
                }),
            }
            missing_action = stop.stop_judge({
                "last_assistant_message": "More work remains but no action was specified."
            })
            data = json.load(open(os.path.join(td, "judge_latest.json"), encoding="utf-8"))
            loop = json.load(open(os.path.join(td, "loop_state.json"), encoding="utf-8"))
            test("continue without next_action fails safe",
                 data.get("last_verdict") == "human_review"
                 and loop.get("loop_count") == 0
                 and loop.get("auto_continue") is False
                 and "systemMessage" in missing_action,
                 (data, loop, missing_action))

            with open(os.path.join(td, "PROJECT_SPEC.md"), "w", encoding="utf-8") as f:
                f.write(_complete_project_spec("- [x] TASK-001: do work"))

            responses = [
                {
                    "verdict": "done",
                    "reason": "all acceptance criteria are satisfied",
                    "next_action": "",
                    "auto_continue": False,
                },
                {
                    "decision": "final_done",
                    "evaluation_status": "no obvious user-facing issues found",
                    "reason": "user can complete the intended flow",
                    "findings": [],
                    "filtered_findings": [],
                    "change_request": "",
                    "questions": [],
                },
            ]
            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps(responses.pop(0)),
            }
            done = stop.stop_judge({"last_assistant_message": "All tasks are complete."})
            test("done does not block after experience evaluation",
                 "systemMessage" in done and "experience evaluation" in done["systemMessage"],
                 done)
            report = open(os.path.join(td, "COMPLETION_REPORT.md"), encoding="utf-8").read()
            test("done writes completion report after evaluation",
                 "Stop Hook Done Record" in report and "Experience Evaluation" in report,
                 report)
            data = json.load(open(os.path.join(td, "judge_latest.json"), encoding="utf-8"))
            loop = json.load(open(os.path.join(td, "loop_state.json"), encoding="utf-8"))
            ctx = open(os.path.join(td, "latest_context.md"), encoding="utf-8").read()
            test("done resets loop state and disables auto-continue",
                 data.get("last_verdict") == "done"
                 and data.get("loop_count") == 0
                 and loop.get("loop_count") == 0
                 and loop.get("auto_continue") is False
                 and "AUTO_CONTINUE: disabled" in ctx,
                 (data, loop, ctx))
            test("done latest context has no manual-review next action",
                 "NEXT_ACTION: None (task complete)" in ctx
                 and "manual review required" not in ctx,
                 ctx)
        finally:
            stop.call_codex_default = old_call
            stop.WIKI_DIR = old_wiki

    child = _run_hook("stop_judge.py", child=True)
    test("child stop hook is no-op", json.loads(child.stdout) == {})


def test_stop_experience_evaluation_gate():
    print("\n[Stop experience evaluation]")
    stop = _load_hook_module("stop_judge")
    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR

    def write_base_files(wiki, loop_state='{"loop_count":0,"auto_continue":false}'):
        report_path = os.path.join(wiki, "COMPLETION_REPORT.md")
        if os.path.exists(report_path):
            os.remove(report_path)
        for name, content in {
            "PROJECT_SPEC.md": _complete_project_spec(
                "- [x] TASK-001: Build app",
                "- User can add and read notes.",
            ),
            "latest_context.md": "# Latest\n",
            "JUDGE.md": "# Judge\n",
            "loop_state.json": loop_state,
        }.items():
            with open(os.path.join(wiki, name), "w", encoding="utf-8") as f:
                f.write(content)

    def run_done_case(wiki, evaluation_response, loop_state='{"loop_count":0,"auto_continue":false}'):
        write_base_files(wiki, loop_state=loop_state)
        responses = [
            {
                "verdict": "done",
                "reason": "all tasks and acceptance criteria are complete",
                "next_action": "",
                "auto_continue": False,
                "progress_made": True,
            },
            evaluation_response,
        ]

        def fake_call(prompt, timeout=120):
            return {"ok": True, "content": json.dumps(responses.pop(0))}

        stop.call_codex_default = fake_call
        result = stop.stop_judge({"last_assistant_message": "All tasks complete and tests pass."})
        data = json.load(open(os.path.join(wiki, "judge_latest.json"), encoding="utf-8"))
        report_path = os.path.join(wiki, "COMPLETION_REPORT.md")
        report = open(report_path, encoding="utf-8").read() if os.path.exists(report_path) else ""
        return result, data, report

    with tempfile.TemporaryDirectory() as td:
        stop.WIKI_DIR = td
        try:
            result, data, report = run_done_case(td, {
                "decision": "spec_update_required",
                "evaluation_status": "issues found and converted to spec update",
                "reason": "new users cannot discover how to create the first note",
                "findings": ["The empty state gives no path to create the first note."],
                "filtered_findings": [],
                "change_request": "Add a task to provide a clear empty-state create-note action.",
                "questions": [],
            })
            test("experience findings enter spec_update_required",
                 data.get("last_verdict") == "spec_update_required"
                 and "Spec Steward" in data.get("next_action", "")
                 and not report,
                 (result, data, report))

            result, data, report = run_done_case(td, {
                "decision": "final_done",
                "evaluation_status": "no obvious user-facing issues found",
                "reason": "claimed done while still listing a real issue",
                "findings": ["First-time users cannot discover the primary action."],
                "filtered_findings": [],
                "change_request": "Add a task for a visible primary action in the empty state.",
                "questions": [],
            })
            test("actionable findings override mistaken final_done",
                 data.get("last_verdict") == "spec_update_required"
                 and "Spec Steward" in data.get("next_action", "")
                 and not report,
                 (result, data, report))

            result, data, report = run_done_case(td, {
                "decision": "final_done",
                "evaluation_status": "issues filtered as low-value/out-of-scope",
                "reason": "core user flow works; only cosmetic preferences remain",
                "findings": [],
                "filtered_findings": ["Button color preference is low-value polish."],
                "change_request": "",
                "questions": [],
            })
            test("low-value evaluation suggestions still allow final done",
                 data.get("last_verdict") == "done"
                 and "Button color preference" in report
                 and "Stop Hook Done Record" in report,
                 (result, data, report))

            result, data, report = run_done_case(td, {
                "decision": "human_review",
                "evaluation_status": "evaluation environment-blocked",
                "reason": "the app cannot be launched from available evidence",
                "findings": [],
                "filtered_findings": [],
                "change_request": "",
                "questions": ["Can the app be launched locally for evaluation?"],
            })
            test("blocked experience evaluation requires human review",
                 data.get("last_verdict") == "human_review"
                 and "COMPLETION_REPORT" not in report,
                 (result, data, report))

            write_base_files(
                td,
                loop_state='{"loop_count":0,"auto_continue":false,"experience_evaluation_count":3}',
            )
            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "verdict": "done",
                    "reason": "all tasks complete again",
                    "next_action": "",
                    "auto_continue": False,
                    "progress_made": True,
                }),
            }
            result = stop.stop_judge({"last_assistant_message": "All tasks complete again."})
            data = json.load(open(os.path.join(td, "judge_latest.json"), encoding="utf-8"))
            test("experience evaluation loop limit fails safe",
                 data.get("last_verdict") == "human_review"
                 and "loop limit" in data.get("reason", ""),
                 (result, data))
        finally:
            stop.call_codex_default = old_call
            stop.WIKI_DIR = old_wiki


def test_stop_prompt_keeps_development_plan_context():
    print("\n[Stop long PROJECT_SPEC context]")
    stop = _load_hook_module("stop_judge")
    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR
    captured = {}
    with tempfile.TemporaryDirectory() as td:
        stop.WIKI_DIR = td
        long_background = "Background detail.\n" * 250
        long_tasks = "".join(
            "* TASK-%03d: Filler stage work\n"
            "    * Acceptance: filler stage %03d is tracked.\n"
            % (idx, idx)
            for idx in range(3, 90)
        )
        project_spec = (
            "# PROJECT_SPEC\n\n"
            "0. Project Mode\nsupervised_project_development\n\n"
            "1. Project Goal\nBuild a local iOS app.\n\n"
            "2. Background\n%s\n\n"
            "3. User Requirements\n* Users can operate the app locally.\n\n"
            "4. Non-Goals\n* No cloud default.\n\n"
            "5. Allowed Scope\n* App files.\n\n"
            "6. Protected Scope\n* .project_wiki/PROJECT_SPEC.md\n* .codex/hooks.json\n* hooks/*.py\n\n"
            "7. Development Plan\n"
            "* TASK-001: Create app skeleton\n"
            "    * Acceptance: simulator launches the home screen.\n"
            "* TASK-002: Build local dossier models\n"
            "    * Acceptance: model files exist and compile.\n\n"
            "%s"
            "* TASK-099: Verify final import boundary\n"
            "    * Acceptance: late tasks remain visible to the judge.\n\n"
            "8. Acceptance Criteria\n"
            "* Development Plan 中所有任务均完成。\n"
            "* App can build and run.\n\n"
            "9. Stop Conditions\n"
            "* Needs protected scope change.\n\n"
            "## GitHub Sync Policy\n"
            "* Mode: local-only.\n\n"
            "10. Submission Requirements\n"
            "* Generate completion report with tail sentinel.\n"
        ) % (long_background, long_tasks)
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
            test("long spec prompt keeps tail task",
                 "TASK-099" in prompt and "late tasks remain visible" in prompt,
                 prompt[-2000:])
            test("long spec prompt includes acceptance criteria",
                 "Acceptance Criteria" in prompt, prompt[:1000])
            test("long spec prompt includes submission requirements",
                 "Submission Requirements" in prompt and "tail sentinel" in prompt,
                 prompt[-2000:])
            test("stop prompt distinguishes task done from project done",
                 "one TASK is done" in prompt and "whole PROJECT_SPEC" in prompt,
                 prompt[:1000])
            test("stop prompt includes GitHub sync boundary",
                 "GitHub sync" in prompt and "local-only" in prompt,
                 prompt[:1000])
            test("stop prompt prefers blocker self-recovery before human review",
                 "stage goal" in prompt and "re-evaluate" in prompt
                 and "real user decision" in prompt,
                 prompt[:2000])
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
            "PROJECT_SPEC.md": _complete_project_spec(
                "* TASK-005: recording flow\n"
                "* TASK-006: background recording boundary",
                "* All tasks complete.",
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
            "PROJECT_SPEC.md": _complete_project_spec(
                "* TASK-001: current work",
                "* Confirmed acceptance criteria pass.",
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


def test_stop_spec_update_required_applies_when_sufficient():
    print("\n[Stop spec update auto apply]")
    stop = _load_hook_module("stop_judge")
    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR
    old_update = stop.spec_steward.propose_spec_update
    captured = {}
    with tempfile.TemporaryDirectory() as td:
        stop.WIKI_DIR = td
        for name, content in {
            "PROJECT_SPEC.md": _complete_project_spec(
                "- [ ] TASK-001: Build app",
                "- Tests pass.",
            ),
            "latest_context.md": "# Latest\nVERDICT: spec_update_required\nNEXT_ACTION: Add TASK-002.\n",
            "JUDGE.md": "# Judge\n",
            "loop_state.json": '{"loop_count":1,"auto_continue":true}',
        }.items():
            with open(os.path.join(td, name), "w", encoding="utf-8") as f:
                f.write(content)

        try:
            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "verdict": "spec_update_required",
                    "reason": "user confirmed the summarized contract update",
                    "next_action": "Add TASK-002 for automatic contract updates.",
                    "auto_continue": False,
                    "progress_made": False,
                    "questions": [],
                }),
            }

            def fake_update(change_request, apply_update=False):
                captured["change_request"] = change_request
                captured["apply_update"] = apply_update
                return {
                    "ok": True,
                    "applied": True,
                    "decision": "apply",
                    "reason": "confirmed update",
                    "questions": [],
                    "update_summary": "Added TASK-002.",
                }

            stop.spec_steward.propose_spec_update = fake_update
            result = stop.stop_judge({
                "last_assistant_message": (
                    "The user said 同意. The confirmed contract update is to add TASK-002."
                )
            })
            data = json.load(open(os.path.join(td, "judge_latest.json"), encoding="utf-8"))
            ctx = open(os.path.join(td, "latest_context.md"), encoding="utf-8").read()
            test("sufficient spec update calls Spec Steward apply",
                 captured.get("apply_update") is True
                 and "Add TASK-002" in captured.get("change_request", ""),
                 captured)
            test("applied spec update records pass state",
                 data.get("last_verdict") == "pass"
                 and data.get("auto_continue") is False
                 and "Spec Steward applied" in data.get("reason", ""),
                 data)
            test("applied spec update updates latest context",
                 "VERDICT: pass" in ctx and "Spec Steward applied" in ctx,
                 ctx)
            test("applied spec update returns system message",
                 "controlled Spec Steward flow" in result.get("systemMessage", ""),
                 result)
        finally:
            stop.call_codex_default = old_call
            stop.WIKI_DIR = old_wiki
            stop.spec_steward.propose_spec_update = old_update


def test_stop_github_sync_policy_gate():
    print("\n[Stop GitHub sync policy]")
    stop = _load_hook_module("stop_judge")
    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR

    def project_spec(policy_text):
        return (
            "# PROJECT_SPEC\n\n"
            "## 0. Project Mode\nsupervised_project_development\n\n"
            "## 1. Project Goal\nBuild the app.\n\n"
            "## 5. Allowed Scope\n- src/\n- tests/\n\n"
            "## 6. Protected Scope\n- .project_wiki/PROJECT_SPEC.md\n- .codex/hooks.json\n- hooks/*.py\n\n"
            "## 7. Development Plan\n- [ ] TASK-001: Build app\n\n"
            "## 8. Acceptance Criteria\n- Tests pass.\n\n"
            "## 9. Stop Conditions\n- Need user decision.\n\n"
            "%s\n\n"
            "## 10. Submission Requirements\n- Report status.\n"
        ) % policy_text

    def run_case(wiki, policy_text, next_action):
        for name, content in {
            "PROJECT_SPEC.md": project_spec(policy_text),
            "latest_context.md": "# Latest\n",
            "JUDGE.md": "# Judge\n",
            "loop_state.json": '{"loop_count":0,"auto_continue":false}',
        }.items():
            with open(os.path.join(wiki, name), "w", encoding="utf-8") as f:
                f.write(content)
        stop.call_codex_default = lambda prompt, timeout=120: {
            "ok": True,
            "content": json.dumps({
                "verdict": "continue",
                "reason": "checkpoint requested",
                "next_action": next_action,
                "auto_continue": True,
                "progress_made": True,
            }),
        }
        result = stop.stop_judge({"last_assistant_message": "Ready for checkpoint."})
        data = json.load(open(os.path.join(wiki, "judge_latest.json"), encoding="utf-8"))
        return result, data

    with tempfile.TemporaryDirectory() as td:
        wiki = os.path.join(td, ".project_wiki")
        os.makedirs(wiki)
        stop.WIKI_DIR = wiki
        try:
            local_only = (
                "## GitHub Sync Policy\n"
                "- Mode: local-only.\n"
                "- No push, tag, release, or remote operation.\n"
            )
            result, data = run_case(wiki, local_only, "Push changes to GitHub remote.")
            test("local-only policy blocks remote push",
                 data.get("last_verdict") == "human_review"
                 and "local-only" in data.get("reason", ""),
                 (result, data))

            result, data = run_case(wiki, "", "Create GitHub release tag.")
            test("missing GitHub policy blocks remote action",
                 data.get("last_verdict") == "human_review"
                 and "no GitHub Sync Policy" in data.get("reason", ""),
                 (result, data))

            full_policy = (
                "## GitHub Sync Policy\n"
                "- Mode: github-sync.\n"
                "- GitHub account: owner.\n"
                "- Auth method: local gh CLI login.\n"
                "- Credentials: available through local gh auth.\n"
                "- Repository: existing repository owner/name.\n"
                "- Repository creation policy: must use existing repository.\n"
                "- Visibility: private.\n"
                "- Marker nodes: after TASK completion, create local commit and push checkpoint when allowed.\n"
                "- Allowed automatic operations: push, tag.\n"
                "- Release requires human confirmation.\n"
            )
            result, data = run_case(wiki, full_policy, "Push changes to GitHub remote.")
            test("complete policy allows configured auto push",
                 result.get("decision") == "block"
                 and data.get("last_verdict") == "continue",
                 (result, data))

            incomplete_policy = full_policy.replace("- GitHub account: owner.\n", "")
            result, data = run_case(wiki, incomplete_policy, "Push changes to GitHub remote.")
            test("incomplete GitHub sync policy blocks remote action",
                 data.get("last_verdict") == "human_review"
                 and "policy is incomplete" in data.get("reason", ""),
                 (result, data))

            unavailable = full_policy.replace(
                "Credentials: available through local gh auth.",
                "Credentials unavailable: gh auth is not configured.",
            )
            result, data = run_case(wiki, unavailable, "Push changes to GitHub remote.")
            test("unavailable credentials block remote action",
                 data.get("last_verdict") == "human_review"
                 and "credentials are unavailable" in data.get("reason", ""),
                 (result, data))

            confirm_required = full_policy.replace(
                "Allowed automatic operations: push, tag.",
                "Allowed automatic operations: commit only.",
            ).replace(
                "Release requires human confirmation.",
                "Push requires human confirmation. Tag requires human confirmation. Release requires human confirmation.",
            )
            result, data = run_case(wiki, confirm_required, "Tag release v1.0 and push tag.")
            test("human-confirmation policy blocks auto tag or release",
                 data.get("last_verdict") == "human_review"
                 and "requires human confirmation" in data.get("reason", ""),
                 (result, data))
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

    fake_classic_token = "ghp_" + "1234567890abcdefghijklmnopqrstu"
    secret_spec = completed_spec.replace(
        "- Mode: local-only.",
        "- Mode: github-sync.\n- Token: " + fake_classic_token,
    )
    with tempfile.TemporaryDirectory() as td:
        stop.WIKI_DIR = os.path.join(td, ".project_wiki")
        try:
            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "decision": "write_spec",
                    "reason": "bad secret-bearing spec",
                    "questions": [],
                    "updated_project_spec": secret_spec,
                }),
            }
            result = stop.stop_judge({
                "last_assistant_message": "Confirmed GitHub sync but included a token by mistake."
            })
            spec_path = os.path.join(td, ".project_wiki", "PROJECT_SPEC.md")
            written = open(spec_path, encoding="utf-8").read()
            data = json.load(open(os.path.join(td, ".project_wiki", "judge_latest.json"), encoding="utf-8"))
            test("onboarding rejects PROJECT_SPEC with secret material",
                 data.get("last_verdict") == "onboarding_required"
                 and "secret material" in data.get("reason", "")
                 and fake_classic_token[:14] not in written,
                 (result, data, written[:1000]))
        finally:
            stop.call_codex_default = old_call
            stop.WIKI_DIR = old_wiki


def test_stop_incomplete_project_spec_enters_onboarding():
    print("\n[Stop incomplete PROJECT_SPEC onboarding]")
    stop = _load_hook_module("stop_judge")
    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR
    captured = {}
    with tempfile.TemporaryDirectory() as td:
        stop.WIKI_DIR = os.path.join(td, ".project_wiki")
        os.makedirs(stop.WIKI_DIR)
        with open(os.path.join(stop.WIKI_DIR, "PROJECT_SPEC.md"), "w", encoding="utf-8") as f:
            f.write("# PROJECT_SPEC\n\n## 1. Project Goal\nBuild something useful.\n")
        try:
            def fake_call(prompt, timeout=120):
                captured["prompt"] = prompt
                return {
                    "ok": True,
                    "content": json.dumps({
                        "decision": "ask_user",
                        "reason": "missing Allowed Scope, Protected Scope, plan, and acceptance criteria",
                        "questions": [
                            "Codex 允许修改哪些具体目录和文件？",
                            "哪些文件或目录必须保护？",
                        ],
                        "updated_project_spec": "",
                    }),
                }

            stop.call_codex_default = fake_call
            result = stop.stop_judge({
                "last_assistant_message": "The user said start work, but the task contract is incomplete."
            })
            data = json.load(open(os.path.join(stop.WIKI_DIR, "judge_latest.json"), encoding="utf-8"))
            ctx = open(os.path.join(stop.WIKI_DIR, "latest_context.md"), encoding="utf-8").read()
            test("incomplete PROJECT_SPEC goes through onboarding steward",
                 "Onboarding Steward" in captured.get("prompt", "")
                 and data.get("last_verdict") == "onboarding_required"
                 and data.get("auto_continue") is False,
                 (captured.get("prompt", "")[:1000], data))
            test("incomplete PROJECT_SPEC onboarding asks user instead of continuing",
                 "systemMessage" in result
                 and "Questions for the user" in result.get("systemMessage", "")
                 and "AUTO_CONTINUE: disabled" in ctx,
                 (result, ctx))
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

            fake_fine_grained_token = "github_pat_" + "1234567890abcdefghijklmnopqrstuvwxyz"
            secret_spec = updated_spec.replace(
                "- Mode: local-only.",
                "- Mode: github-sync.\n- Token: " + fake_fine_grained_token,
            )
            steward.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "decision": "apply",
                    "reason": "bad secret spec",
                    "questions": [],
                    "update_summary": "",
                    "updated_project_spec": secret_spec,
                }),
            }
            secret = steward.propose_spec_update("Store GitHub token.", apply_update=True)
            current = open(steward.PROJECT_SPEC_PATH, encoding="utf-8").read()
            test("spec steward rejects PROJECT_SPEC with secret material",
                 secret.get("ok") is False
                 and any("secret material" in item for item in secret.get("missing", []))
                 and fake_fine_grained_token[:22] not in current,
                 (secret, current))

            latest_context = (
                "VERDICT: spec_update_required\n"
                "NEXT_ACTION: Add TASK-003 for confirmed export.\n"
                "REASON: User asked for export support.\n"
            )
            confirmation_request = steward.build_user_prompt_change_request(
                "同意", latest_context
            )
            test("spec steward turns confirmation into prior change request",
                 "Add TASK-003" in confirmation_request
                 and "manually edit" in confirmation_request,
                 confirmation_request)

            missing_context = steward.propose_user_prompt_update(
                "同意", "", apply_update=True
            )
            test("spec steward asks when confirmation lacks prior context",
                 missing_context.get("decision") == "needs_user_confirmation"
                 and missing_context.get("applied") is False,
                 missing_context)

            rejected_confirmation = steward.propose_user_prompt_update(
                "不同意", latest_context, apply_update=True
            )
            test("spec steward rejects refused confirmation without writing",
                 rejected_confirmation.get("decision") == "reject"
                 and rejected_confirmation.get("applied") is False
                 and rejected_confirmation.get("source") == "user_prompt_rejection",
                 rejected_confirmation)

            ambiguous_confirmation = steward.propose_user_prompt_update(
                "可以吧", latest_context, apply_update=True
            )
            test("spec steward asks on ambiguous confirmation",
                 ambiguous_confirmation.get("decision") == "needs_user_confirmation"
                 and ambiguous_confirmation.get("applied") is False
                 and ambiguous_confirmation.get("source") == "user_prompt_ambiguous_confirmation"
                 and ambiguous_confirmation.get("questions"),
                 ambiguous_confirmation)

            steward.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "decision": "needs_user_confirmation",
                    "reason": "missing target platform",
                    "questions": ["Which platform should export support target?"],
                    "update_summary": "",
                    "updated_project_spec": "",
                }),
            }
            prompt_suggestion = steward.propose_user_prompt_update(
                "需求改一下：增加导出功能。", latest_context, apply_update=True
            )
            test("spec steward routes direct suggestion through controlled flow",
                 prompt_suggestion.get("decision") == "needs_user_confirmation"
                 and prompt_suggestion.get("source") == "user_prompt_suggestion"
                 and prompt_suggestion.get("questions"),
                 prompt_suggestion)
        finally:
            steward.call_codex_default = old_call
            steward.WIKI_DIR = old_wiki
            steward.PROJECT_SPEC_PATH = old_spec_path
            steward.LATEST_CONTEXT_PATH = old_latest_path


def test_spec_steward_long_project_spec_prompt_keeps_tail():
    print("\n[Spec Steward long PROJECT_SPEC prompt]")
    steward = _load_hook_module("spec_steward")
    long_background = "Very long background detail.\n" * 3500
    long_plan = "".join(
        "- [ ] TASK-%03d: Long plan item\n"
        "  - Acceptance: long plan item %03d remains tracked.\n"
        % (idx, idx)
        for idx in range(1, 130)
    )
    long_spec = (
        "# PROJECT_SPEC\n\n"
        "## 0. Project Mode\nsupervised_project_development\n\n"
        "## 1. Project Goal\nBuild a long-plan project.\n\n"
        "## 2. Background\n%s\n\n"
        "## 3. User Requirements\n- Keep all confirmed requirements.\n\n"
        "## 4. Non-Goals\n- No RAG.\n\n"
        "## 5. Allowed Scope\n- app/\n\n"
        "## 6. Protected Scope\n- .project_wiki/PROJECT_SPEC.md\n\n"
        "## 7. Development Plan\n%s"
        "- [ ] TASK-199: Late-stage acceptance sentinel\n"
        "  - Acceptance: late-stage task is still visible.\n\n"
        "## 8. Acceptance Criteria\n- Every task is complete.\n\n"
        "## 9. Stop Conditions\n- Need a real user decision.\n\n"
        "## GitHub Sync Policy\n- Mode: local-only.\n\n"
        "## 10. Submission Requirements\n- Completion report keeps submission tail sentinel.\n"
    ) % (long_background, long_plan)
    prompt = steward.build_spec_update_prompt("Add a small confirmed task.", long_spec, "")
    test("spec steward prompt marks compacted task book",
         "PROJECT_SPEC compacted for prompt" in prompt,
         prompt[:1000])
    test("spec steward prompt keeps late Development Plan item",
         "TASK-199" in prompt and "late-stage task is still visible" in prompt,
         prompt[-3000:])
    test("spec steward prompt keeps submission requirements tail",
         "Submission Requirements" in prompt and "submission tail sentinel" in prompt,
         prompt[-3000:])
    test("spec steward prompt warns not to drop late task-book content",
         "late Development Plan items" in prompt,
         prompt[:2000])


def test_active_mission_snapshot_goal_drift_and_context_budget():
    print("\n[Active Mission Snapshot]")
    mission = _load_hook_module("mission_snapshot")
    user_prompt = _load_hook_module("user_prompt_submit")
    stop = _load_hook_module("stop_judge")

    snapshot_spec = (
        "# PROJECT_SPEC\n\n"
        "## Active Mission Snapshot\n"
        "- Current Goal: Stabilize autonomous contract governance.\n"
        "- Current TASK Range: TASK-014 through TASK-023\n"
        "- Current Release Target: v2.6\n"
        "- Context Priority: Active Mission Snapshot -> current TASK -> acceptance.\n\n"
        "## 0. Project Mode\nspecpilot_self_development\n\n"
        "## 1. Project Goal\nBuild SpecPilot.\n\n"
        "## 2. Background\n%s\n\n"
        "## 3. User Requirements\n- Keep current-goal anchor first.\n\n"
        "## 4. Non-Goals\n- No RAG.\n\n"
        "## 5. Allowed Scope\n- hooks/\n- tests/\n\n"
        "## 6. Protected Scope\n- secrets\n\n"
        "## 7. Development Plan\n"
        "- [ ] TASK-014: Active Mission Snapshot\n"
        "- [ ] TASK-023: real regression\n\n"
        "## 8. Acceptance Criteria\n- Snapshot survives long context.\n\n"
        "## 9. Stop Conditions\n- Human decision needed.\n\n"
        "## GitHub Sync Policy\n- Mode: github-sync.\n"
        "- GitHub account: configured.\n"
        "- Auth method: gh CLI.\n"
        "- Credentials: available.\n"
        "- Repository: existing repository.\n"
        "- Repository creation: must use existing repository.\n"
        "- Visibility: public/private as existing.\n"
        "- Marker nodes: commit, push, tag, release.\n"
        "- Allowed automatic operations: push, tag, release.\n\n"
        "## 10. Submission Requirements\n- Publish v2.6.\n"
    ) % ("Old completed phase history.\n" * 3000)

    section = mission.extract_active_mission_snapshot(snapshot_spec)
    test("extracts active mission snapshot",
         "Current TASK Range: TASK-014 through TASK-023" in section,
         section)
    drift = mission.detect_goal_drift("Continue TASK-001 and release v2.1.", snapshot_spec)
    test("detects stale task drift before old history wins",
         drift.get("drift") and "TASK-001" in drift.get("reason", ""),
         drift)
    release_drift = mission.detect_goal_drift("Create release v2.2.", snapshot_spec)
    test("detects release target drift",
         release_drift.get("drift") and "v2.6" in release_drift.get("reason", ""),
         release_drift)
    typo_ok = mission.detect_goal_drift("Create release vv2.6.", snapshot_spec)
    test("normalizes vv release typo",
         not typo_ok.get("drift"),
         typo_ok)

    old_wiki = user_prompt.WIKI_DIR
    try:
        with tempfile.TemporaryDirectory() as td:
            user_prompt.WIKI_DIR = td
            with open(os.path.join(td, "PROJECT_SPEC.md"), "w", encoding="utf-8") as f:
                f.write(snapshot_spec)
            with open(os.path.join(td, "INJECTION.md"), "w", encoding="utf-8") as f:
                f.write("# Codex SpecPilot\n\n" + ("base context\n" * 1000))
            injected = user_prompt.user_prompt_submit({"prompt": "开始工作"})
            ctx = injected.get("hookSpecificOutput", {}).get("additionalContext", "")
            test("prompt injection keeps snapshot before truncation",
                 "### Active Mission Snapshot ###" in ctx
                 and "TASK-014 through TASK-023" in ctx
                 and len(ctx) <= user_prompt.MAX_CONTEXT_CHARS,
                 ctx[:1200])
    finally:
        user_prompt.WIKI_DIR = old_wiki

    old_call = stop.call_codex_default
    old_wiki = stop.WIKI_DIR
    try:
        with tempfile.TemporaryDirectory() as td:
            stop.WIKI_DIR = td
            for name, content in {
                "PROJECT_SPEC.md": snapshot_spec,
                "latest_context.md": "# Latest\n",
                "JUDGE.md": "# Judge\n",
                "loop_state.json": '{"loop_count":0,"auto_continue":false}',
            }.items():
                with open(os.path.join(td, name), "w", encoding="utf-8") as f:
                    f.write(content)
            stop.call_codex_default = lambda prompt, timeout=120: {
                "ok": True,
                "content": json.dumps({
                    "verdict": "continue",
                    "reason": "old phase should continue",
                    "next_action": "Continue TASK-001 using historical phase notes.",
                    "auto_continue": True,
                    "progress_made": False,
                    "questions": [],
                }),
            }
            result = stop.stop_judge({"last_assistant_message": "Worked from old history."})
            data = json.load(open(os.path.join(td, "judge_latest.json"), encoding="utf-8"))
            test("stop judge converts stale next_action to revise",
                 result.get("decision") == "block"
                 and data.get("last_verdict") == "revise"
                 and "Goal drift detected" in data.get("reason", ""),
                 (result, data))
    finally:
        stop.call_codex_default = old_call
        stop.WIKI_DIR = old_wiki


def test_section_patch_evidence_status_and_phase_contract():
    print("\n[Section patch / evidence reconciliation]")
    steward = _load_hook_module("spec_steward")
    evidence = _load_hook_module("evidence_reconciler")
    status = _load_hook_module("status_normalizer")
    phase = _load_hook_module("phase_contract")

    base_spec = _complete_project_spec(
        "- [ ] TASK-150: Finish real-world validation\n"
        "- [x] TASK-151: Preserve release policy",
        "- Validation evidence recorded."
    )
    patched = steward.apply_project_spec_section_patch(base_spec, [{
        "op": "replace",
        "heading": "Development Plan",
        "content": (
            "## 7. Development Plan\n"
            "- [x] TASK-150: Finish real-world validation\n"
            "- [x] TASK-151: Preserve release policy"
        ),
    }])
    test("section patch updates one section without dropping submission tail",
         "TASK-150" in patched
         and "Report status" in patched
         and patched.count("## 10. Submission Requirements") == 1,
         patched[-1000:])

    test("status aliases normalize quality-risk variants",
         status.statuses_equivalent(
             "phase16_complete_with_quality_fix_required",
             "phase16_complete_with_quality_risks",
         )
         and status.status_indicates_complete("phase16_complete_with_quality_fix_required"),
         status.normalize_status("phase16_complete_with_quality_fix_required"))

    reconciliation = evidence.reconcile_project_spec_with_reports(base_spec, [{
        "task_id": "TASK-150",
        "status": "phase16_complete_with_quality_fix_required",
        "source": "novelcreatepilot smoke report",
    }])
    test("evidence reconciliation finds completed evidence vs pending spec",
         not reconciliation.get("ok")
         and reconciliation.get("mismatches")
         and "TASK-150" in reconciliation.get("change_request", ""),
         reconciliation)

    draft = phase.build_next_phase_contract_draft(patched, "All v2.6 tasks verified.")
    test("phase contract drafts next phase after all tasks complete",
         draft.get("ready")
         and "controlled Spec Steward flow" in draft.get("change_request", ""),
         draft)


def test_controlled_spec_steward_write_channel():
    print("\n[Controlled Spec Steward write channel]")
    pre = _load_hook_module("pre_tool_guard")
    old_wiki = pre.WIKI_DIR
    old_guard_log = pre.GUARD_LOG
    old_project_spec = pre.PROJECT_SPEC_PATH
    try:
        with tempfile.TemporaryDirectory() as td:
            pre.WIKI_DIR = td
            pre.GUARD_LOG = os.path.join(td, "guard_log.jsonl")
            pre.PROJECT_SPEC_PATH = os.path.join(td, "PROJECT_SPEC.md")
            with open(pre.PROJECT_SPEC_PATH, "w", encoding="utf-8") as f:
                f.write("# Spec\nspecpilot_self_development\n")

            ordinary = pre.pre_tool_use({
                "tool_input": {
                    "command": "python3 hooks/spec_steward.py --apply --change 'update plan'"
                }
            })
            test("ordinary spec steward apply command is denied",
                 ordinary.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
                 ordinary)

            controlled = pre.pre_tool_use({
                "tool_input": {
                    "command": "CODEX_SPECPILOT_STEWARD=1 python3 hooks/spec_steward.py --apply --change 'update plan'"
                }
            })
            test("controlled spec steward apply command is allowed",
                 controlled == {},
                 controlled)

            direct_spec_patch = pre.pre_tool_use({
                "tool": "apply_patch",
                "tool_input": {
                    "target_file": ".project_wiki/PROJECT_SPEC.md",
                    "patch": "*** Update File: .project_wiki/PROJECT_SPEC.md\n",
                },
            })
            test("direct PROJECT_SPEC patch is denied even in self-dev",
                 direct_spec_patch.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
                 direct_spec_patch)
    finally:
        pre.WIKI_DIR = old_wiki
        pre.GUARD_LOG = old_guard_log
        pre.PROJECT_SPEC_PATH = old_project_spec


def test_readme_task006_role_boundaries():
    print("\n[README role boundaries]")
    readme = open(os.path.join(ROOT_DIR, "README.md"), encoding="utf-8").read()
    expected_terms = [
        "Role Boundaries",
        "Requirement parsing",
        "Spec Steward",
        "Planner",
        "Codex Worker",
        "Stop Hook",
        "spec_update_required",
        "角色分工",
    ]
    missing = [term for term in expected_terms if term not in readme]
    test("README documents TASK-006 role boundaries", not missing, missing)


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
    test("hook commands are module commands, not shell scripts",
         all(
             hook.get("command", "").startswith("python -m hooks.")
             and hook.get("commandWindows", "").startswith("py -3 -m hooks.")
             and not any(token in hook.get("command", "") for token in ("&&", ";", "|", "/bin/sh"))
             and not any(
                 token in hook.get("commandWindows", "").lower()
                 for token in ("&&", ";", "|", "cmd /c", "powershell")
             )
             for hook in all_hooks
         ),
         all_hooks)
    stop_hooks = data.get("hooks", {}).get("Stop", [])[0].get("hooks", [])
    test("Stop hook timeout is at least 60 seconds",
         stop_hooks and stop_hooks[0].get("timeout", 0) >= 60, stop_hooks)


def test_cross_platform_path_helpers():
    print("\n[cross-platform path helpers]")
    policy = _load_hook_module("permission_policy")
    diagnose = _load_module_at(
        "diagnose_codex_exec_for_smoke",
        os.path.join(ROOT_DIR, "tests", "diagnose_codex_exec.py"),
    )

    win_root = "C:" + "\\Users\\alice\\repo"
    win_judge = win_root + "\\.project_wiki\\JUDGE.md"
    win_hook = win_root + "\\hooks\\stop_judge.py"
    win_hooks_json = win_root + "\\.codex\\hooks.json"
    mac_judge = os.path.join(ROOT_DIR, ".project_wiki", "JUDGE.md")
    mac_business = os.path.join(ROOT_DIR, "src", "main.py")

    test("Windows absolute judge path is supervision file",
         policy.is_supervision_file(win_judge), win_judge)
    test("Windows absolute hooks.py path is supervision file",
         policy.is_supervision_file(win_hook), win_hook)
    test("Windows absolute hooks.json path is supervision file",
         policy.is_supervision_file(win_hooks_json), win_hooks_json)
    test("current macOS absolute judge path is supervision file",
         policy.is_supervision_file(mac_judge), mac_judge)
    test("current macOS business path is not supervision file",
         not policy.is_supervision_file(mac_business), mac_business)

    win_command = "Set-" + "Content " + win_judge + " updated"
    win_paths = policy.extract_paths_from_command(win_command)
    test("Windows PowerShell write command extracts target",
         win_judge in win_paths, win_paths)
    test("Windows PowerShell write command has write intent",
         policy.command_has_write_intent("Set-" + "Content README.md updated"))

    mac_paths = policy.extract_paths_from_patch(
        "*** Begin Patch\n"
        "*** Update File: %s\n"
        "@@\n"
        "+x\n"
        "*** End Patch\n" % mac_judge
    )
    test("macOS absolute patch path extracts target",
         mac_judge in mac_paths, mac_paths)

    test("diagnostic command uses argument list",
         diagnose.codex_version_command() == ["codex", "--version"],
         diagnose.codex_version_command())
    test("diagnostic hooks path resolves to current repo hooks",
         os.path.realpath(diagnose.hooks_path()) == os.path.realpath(HOOKS_DIR),
         diagnose.hooks_path())


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

        with tempfile.TemporaryDirectory() as td:
            os.mkdir(os.path.join(td, ".git"))
            nested = os.path.join(td, "src", "feature")
            os.makedirs(nested)
            with open(os.path.join(nested, "work.txt"), "w", encoding="utf-8") as f:
                f.write("nested work\n")
            os.chdir(nested)
            expected = os.path.realpath(os.path.join(td, ".project_wiki"))
            test("nested repo cwd resolves wiki at repo root",
                 os.path.realpath(project_paths.wiki_dir()) == expected,
                 project_paths.wiki_dir())

        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, ".project_wiki"))
            nested = os.path.join(td, "src", "feature")
            os.makedirs(nested)
            with open(os.path.join(nested, "work.txt"), "w", encoding="utf-8") as f:
                f.write("nested work\n")
            os.chdir(nested)
            expected = os.path.realpath(os.path.join(td, ".project_wiki"))
            test("nested cwd uses ancestor project wiki without repo marker",
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
             any(
                 "GitHub" in q
                 and "local-only" in q
                 and "token" in q
                 and "账号" in q
                 and "新建仓库" in q
                 for q in empty_questions
             ),
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
             any(
                 "GitHub" in q
                 and "公开" in q
                 and "私有" in q
                 and "人工确认" in q
                 for q in existing_questions
             ),
             existing_questions)
        wiki_only = injector.bootstrap_wiki_files(existing_dir)
        test("wiki bootstrap writes task-contract placeholder only",
             ".project_wiki/PROJECT_SPEC.md" in wiki_only.get("written", [])
             and not any(path.startswith("hooks/") for path in wiki_only.get("written", [])),
             wiki_only)
        result = injector.bootstrap_project(existing_dir)
        test("bootstrap writes hooks and codex config",
             "hooks/stop_judge.py" in result.get("written", [])
             and "hooks/project_injector.py" in result.get("written", [])
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
                 "Project Onboarding Rule" in ctx and "business code" in ctx,
                 ctx[:1000])
            test("onboarding injection includes GitHub local-only default",
                 "GitHub" in ctx and "local-only" in ctx,
                 ctx[:1200])
            test("start work is deferred during onboarding",
                 "Start Work Deferred" in ctx and "Start Work Instruction" not in ctx,
                 ctx[:1000])

            with open(os.path.join(existing_dir, ".project_wiki", "PROJECT_SPEC.md"), "w", encoding="utf-8") as f:
                f.write("# PROJECT_SPEC\n\n## 1. Project Goal\nBuild something useful.\n")
            injected = user_prompt.user_prompt_submit({"prompt": "开始工作"})
            ctx = injected.get("hookSpecificOutput", {}).get("additionalContext", "")
            test("incomplete PROJECT_SPEC without marker still defers start work",
                 "Project Onboarding Rule" in ctx
                 and "Start Work Deferred" in ctx
                 and "Start Work Instruction" not in ctx,
                 ctx[:1200])
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

    with tempfile.TemporaryDirectory() as repo_dir:
        os.mkdir(os.path.join(repo_dir, ".git"))
        nested = os.path.join(repo_dir, "src", "feature")
        os.makedirs(nested)
        env = os.environ.copy()
        env["PYTHONPATH"] = HOOKS_DIR
        env.pop("CODEX_SPECPILOT_PROJECT_DIR", None)
        env.pop("CODEX_SPECPILOT_CHILD", None)
        result = subprocess.run(
            [sys.executable, os.path.join(HOOKS_DIR, "user_prompt_submit.py")],
            capture_output=True,
            text=True,
            env=env,
            cwd=nested,
            input=json.dumps({"prompt": "接管这个项目"}),
        )
        root_spec = os.path.join(repo_dir, ".project_wiki", "PROJECT_SPEC.md")
        nested_spec = os.path.join(nested, ".project_wiki", "PROJECT_SPEC.md")
        test("nested repo auto-onboarding writes PROJECT_SPEC at repo root",
             result.returncode == 0
             and os.path.isfile(root_spec)
             and not os.path.exists(nested_spec),
             result.stderr or result.stdout)


def test_project_injector_runtime_upgrade():
    print("\n[Runtime upgrade]")
    injector = _load_hook_module("project_injector")

    with tempfile.TemporaryDirectory() as target_dir:
        result = injector.bootstrap_project(target_dir)
        test("runtime bootstrap writes manifest",
             ".project_wiki/specpilot_manifest.json" in result.get("written", [])
             or ".project_wiki/specpilot_manifest.json" in result.get("updated", []),
             result)

        spec_path = os.path.join(target_dir, ".project_wiki", "PROJECT_SPEC.md")
        with open(spec_path, "w", encoding="utf-8") as f:
            f.write("# PROJECT_SPEC\n\nCUSTOM CONTRACT MUST STAY\n")

        protected_state = {
            "JUDGE.md": "# custom judge state\n",
            "latest_context.md": "# custom latest context\n",
            "judge_latest.json": '{"custom": true}\n',
            "loop_state.json": '{"loop_count": 99}\n',
            "guard_log.jsonl": '{"custom": true}\n',
            "COMPLETION_REPORT.md": "# custom completion report\n",
        }
        for name, content in protected_state.items():
            with open(os.path.join(target_dir, ".project_wiki", name), "w", encoding="utf-8") as f:
                f.write(content)

        hook_path = os.path.join(target_dir, "hooks", "user_prompt_submit.py")
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write("# stale local hook\n")

        injection_path = os.path.join(target_dir, ".project_wiki", "INJECTION.md")
        with open(injection_path, "w", encoding="utf-8") as f:
            f.write("# stale injection\n")

        upgraded = injector.ensure_runtime_files(target_dir)
        test("runtime upgrade refreshes stale hook",
             "hooks/user_prompt_submit.py" in upgraded.get("updated", []),
             upgraded)
        test("runtime upgrade refreshes managed wiki instruction",
             ".project_wiki/INJECTION.md" in upgraded.get("updated", []),
             upgraded)
        test("runtime upgrade preserves PROJECT_SPEC",
             "CUSTOM CONTRACT MUST STAY" in open(spec_path, encoding="utf-8").read(),
             open(spec_path, encoding="utf-8").read())
        preserved = {
            name: open(os.path.join(target_dir, ".project_wiki", name), encoding="utf-8").read()
            for name in protected_state
        }
        test("runtime upgrade preserves judge state and completion report",
             preserved == protected_state,
             preserved)

        manifest_path = os.path.join(target_dir, ".project_wiki", "specpilot_manifest.json")
        manifest = json.load(open(manifest_path, encoding="utf-8"))
        test("runtime manifest records source root",
             manifest.get("source_root") == ROOT_DIR and manifest.get("runtime_version"),
             manifest)
        managed_files = manifest.get("managed_files", [])
        protected_names = {
            ".project_wiki/PROJECT_SPEC.md",
            ".project_wiki/JUDGE.md",
            ".project_wiki/latest_context.md",
            ".project_wiki/judge_latest.json",
            ".project_wiki/loop_state.json",
            ".project_wiki/guard_log.jsonl",
            ".project_wiki/COMPLETION_REPORT.md",
        }
        test("runtime manifest excludes protected state files",
             protected_names.isdisjoint(set(managed_files))
             and "hooks/user_prompt_submit.py" in managed_files
             and "hooks/secret_scan.py" in managed_files
             and ".project_wiki/INJECTION.md" in managed_files,
             manifest)


def test_macos_installer_config_generation():
    print("\n[macOS installer]")
    installer = _load_module_at(
        "install_specpilot",
        os.path.join(ROOT_DIR, "install", "macos", "install_specpilot.py"),
    )

    with tempfile.TemporaryDirectory() as codex_home:
        result = installer.install(codex_home=codex_home)
        hooks_path = os.path.join(codex_home, "hooks.json")
        data = json.load(open(hooks_path, encoding="utf-8"))
        text = open(hooks_path, encoding="utf-8").read()
        test("installer writes hooks.json",
             result.get("ok") and os.path.isfile(hooks_path),
             result)
        test("installer uses discovered repo root",
             ROOT_DIR in text and "Codex-SpecPilot" in text,
             text[:1000])
        test("installer config stores no credential secret material",
             all(term not in text.lower() for term in ("token", "api key", "private key", "password")),
             text[:1000])
        test("installer config has no GitHub remote operation",
             all(term not in text.lower() for term in ("git push", "gh ", "release", "git tag")),
             text[:1000])
        test("installer writes split PreToolUse matchers",
             len(data.get("hooks", {}).get("PreToolUse", [])) == 4,
             data)
        second = installer.install(codex_home=codex_home)
        test("installer is idempotent",
             second.get("ok") and not second.get("changed"),
             second)


def main():
    print("=== Codex SpecPilot Light Smoke Tests ===")
    test_user_prompt_submit()
    test_pre_tool_guard_light_boundary()
    test_stop_auto_continue_and_done_helpers()
    test_stop_experience_evaluation_gate()
    test_stop_prompt_keeps_development_plan_context()
    test_stop_loop_limit_counts_stalled_work_only()
    test_stop_spec_update_required_pauses_worker()
    test_stop_spec_update_required_applies_when_sufficient()
    test_stop_github_sync_policy_gate()
    test_stop_onboarding_steward_writes_spec()
    test_stop_incomplete_project_spec_enters_onboarding()
    test_spec_steward_controlled_update_flow()
    test_spec_steward_long_project_spec_prompt_keeps_tail()
    test_active_mission_snapshot_goal_drift_and_context_budget()
    test_section_patch_evidence_status_and_phase_contract()
    test_controlled_spec_steward_write_channel()
    test_readme_task006_role_boundaries()
    test_codex_command_profile_inheritance()
    test_hooks_json_cross_platform_fields()
    test_cross_platform_path_helpers()
    test_project_path_resolution()
    test_project_injector_bootstrap_and_onboarding()
    test_project_injector_runtime_upgrade()
    test_macos_installer_config_generation()
    print("\n=== Results ===")
    print("Passed: %d, Failed: %d" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
