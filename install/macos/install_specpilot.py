#!/usr/bin/env python3
"""macOS installer for Codex SpecPilot global hooks."""
import argparse
import json
import os
import shlex
import shutil
from datetime import datetime
from pathlib import Path


HOOK_EVENTS = (
    ("UserPromptSubmit", "", "spec-pilot-user-prompt", "user_prompt_submit.py", 10,
     "Codex SpecPilot: injecting project context"),
    ("PreToolUse", "Bash", "spec-pilot-tool-guard-bash", "pre_tool_guard.py", 10,
     "Codex SpecPilot: guarding Bash"),
    ("PreToolUse", "apply_patch", "spec-pilot-tool-guard-apply-patch", "pre_tool_guard.py", 10,
     "Codex SpecPilot: guarding patch"),
    ("PreToolUse", "Edit", "spec-pilot-tool-guard-edit", "pre_tool_guard.py", 10,
     "Codex SpecPilot: guarding edit"),
    ("PreToolUse", "Write", "spec-pilot-tool-guard-write", "pre_tool_guard.py", 10,
     "Codex SpecPilot: guarding write"),
    ("Stop", "", "spec-pilot-stop-judge", "stop_judge.py", 60,
     "Codex SpecPilot: judging stop state"),
)


def repo_root():
    return Path(__file__).resolve().parents[2]


def default_codex_home():
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def _command_for(script_path):
    return "python3 %s" % shlex.quote(str(script_path))


def build_hooks_config(root):
    hooks = {}
    for event, matcher, name, script, timeout, status in HOOK_EVENTS:
        hooks.setdefault(event, []).append({
            "matcher": matcher,
            "hooks": [{
                "type": "command",
                "name": name,
                "command": _command_for(root / "hooks" / script),
                "timeout": timeout,
                "enabled": True,
                "statusMessage": status,
            }],
        })
    return {"hooks": hooks}


def _write_json_if_changed(path, data, dry_run=False):
    text = json.dumps(data, indent=4, ensure_ascii=False) + "\n"
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == text:
        return {"changed": False, "backup": None}
    backup = None
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name("%s.specpilot-backup-%s" % (path.name, stamp))
        if not dry_run:
            shutil.copy2(path, backup)
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return {"changed": True, "backup": str(backup) if backup else None}


def install(codex_home=None, dry_run=False):
    root = repo_root()
    if not (root / "hooks" / "user_prompt_submit.py").is_file():
        return {
            "ok": False,
            "error": "Cannot locate SpecPilot hook source from installer path.",
            "repo_root": str(root),
        }

    home = Path(codex_home).expanduser().resolve() if codex_home else default_codex_home()
    hooks_path = home / "hooks.json"
    config_path = home / "config.toml"
    result = _write_json_if_changed(
        hooks_path,
        build_hooks_config(root),
        dry_run=dry_run,
    )
    return {
        "ok": True,
        "repo_root": str(root),
        "codex_home": str(home),
        "hooks_path": str(hooks_path),
        "config_path": str(config_path),
        "changed": result["changed"],
        "backup": result["backup"],
        "dry_run": dry_run,
        "next_action": "Enable Codex hooks in Codex settings if they are not already enabled.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install Codex SpecPilot hooks for this macOS user.")
    parser.add_argument("--codex-home", help="Override Codex home for testing or custom installs.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be installed without writing.")
    args = parser.parse_args(argv)
    result = install(codex_home=args.codex_home, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
