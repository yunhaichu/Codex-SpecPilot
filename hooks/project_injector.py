"""Project injector for bringing SpecPilot into empty or existing projects.

The injector is deliberately local and lightweight. It bootstraps the small
SpecPilot file set, inspects the target project shape, and writes onboarding
guidance so Codex can interview the user before a real PROJECT_SPEC exists.
"""
import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

SPEC_PILOT_RUNTIME_VERSION = "1.0"
MANIFEST_FILE = "specpilot_manifest.json"

IGNORED_NAMES = {
    ".DS_Store",
    ".git",
    ".project_wiki",
    ".codex",
    "hooks",
    "__pycache__",
}

HOOK_FILES = (
    "__init__.py",
    "codex_client.py",
    "evidence_reconciler.py",
    "mission_snapshot.py",
    "permission_policy.py",
    "phase_contract.py",
    "pre_tool_guard.py",
    "project_injector.py",
    "project_paths.py",
    "secret_scan.py",
    "spec_steward.py",
    "status_normalizer.py",
    "stop_judge.py",
    "user_prompt_submit.py",
)

MANAGED_WIKI_FILES = (
    "INJECTION.md",
    "WORKFLOW.md",
    "PERMISSIONS.md",
    "PROJECT_ONBOARDING.md",
    "PROJECT_SPEC_TEMPLATE.md",
    "COMPLETION_REPORT_TEMPLATE.md",
)

ONBOARDING_MARKER = "NEEDS_USER_CONFIRMATION"
GITHUB_SYNC_QUESTION = (
    "是否需要同步或上传到 GitHub？如果不需要，默认 local-only；如果需要，请说明 GitHub 账号、认证方式"
    "（不要提供 token/密钥原文）、凭据可用状态、仓库 owner/name、公开或私有、必须使用已有仓库还是允许新建仓库、"
    "哪些 marker 节点需要 commit/push/tag/release，以及哪些操作可自动执行或必须人工确认。"
)


def source_root():
    current_root = Path(__file__).resolve().parents[1]
    manifest = current_root / ".project_wiki" / MANIFEST_FILE
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        configured = data.get("source_root")
        if configured:
            candidate = Path(configured).expanduser().resolve()
            if (candidate / "hooks" / "project_injector.py").is_file():
                return candidate
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return current_root


def _is_meaningful(path):
    return path.name not in IGNORED_NAMES and not path.name.endswith(".pyc")


def inspect_project(target_dir):
    root = Path(target_dir).expanduser().resolve()
    entries = [p for p in root.iterdir() if _is_meaningful(p)] if root.exists() else []
    files = [p for p in entries if p.is_file()]
    dirs = [p for p in entries if p.is_dir()]
    names = {p.name for p in entries}

    signals = []
    if "package.json" in names:
        signals.append("node")
    if "pyproject.toml" in names or "requirements.txt" in names:
        signals.append("python")
    if any(p.name.endswith(".xcodeproj") for p in entries):
        signals.append("xcode")
    if "Package.swift" in names:
        signals.append("swift")
    if "Cargo.toml" in names:
        signals.append("rust")
    if "go.mod" in names:
        signals.append("go")
    if "README.md" in names:
        signals.append("readme")

    visible = sorted(p.name for p in entries)[:30]
    return {
        "target_dir": str(root),
        "project_kind": "empty" if not entries else "existing",
        "top_level_files": sorted(p.name for p in files)[:30],
        "top_level_dirs": sorted(p.name for p in dirs)[:30],
        "signals": sorted(signals),
        "visible_entries": visible,
    }


def onboarding_questions(project_info):
    if project_info["project_kind"] == "empty":
        return [
            "这个新项目最终要实现什么？请用 1-3 句话说明。",
            "你希望使用什么技术栈？如果不指定，是否允许 Codex 自主选择？",
            "Codex 允许创建或修改哪些目录和文件？",
            "哪些文件、目录、密钥、部署或数据结构绝对不能修改？",
            "完成后如何验证项目成功？%s" % GITHUB_SYNC_QUESTION,
        ]
    return [
        "这个老项目当前的主要用途和现阶段目标是什么？",
        "这次接管后第一阶段要完成哪些具体改动？哪些旧功能不能碰？",
        "Codex 允许修改哪些具体目录或文件？",
        "哪些目录、配置、数据、部署、schema、migration 或密钥必须保护？",
        "当前项目如何构建、测试、启动或人工验收？%s" % GITHUB_SYNC_QUESTION,
    ]


def build_onboarding_markdown(project_info):
    questions = onboarding_questions(project_info)
    lines = [
        "# SpecPilot Project Onboarding",
        "",
        "This project is not ready for `开始工作` yet.",
        "Codex must first interview the user and produce a complete PROJECT_SPEC candidate.",
        "The controlled SpecPilot Hook flow writes `.project_wiki/PROJECT_SPEC.md`.",
        "",
        "## Project Snapshot",
        "",
        "- Kind: `%s`" % project_info["project_kind"],
        "- Signals: `%s`" % (", ".join(project_info["signals"]) or "none"),
        "- Top-level entries: `%s`" % (", ".join(project_info["visible_entries"]) or "empty"),
        "",
        "## Rules",
        "",
        "1. Do not write business code during onboarding.",
        "2. Ask at most 5 high-signal questions per round.",
        "3. Do not invent requirements the user did not confirm.",
        "4. When enough information is known, output a complete PROJECT_SPEC candidate.",
        "5. Ask for GitHub sync preference during onboarding; default to local-only if upload is not needed.",
        "6. If GitHub sync is requested, ask for GitHub account, auth method, credential availability, public/private visibility, repo target, existing-vs-new repository policy, marker nodes, and allowed automatic operations versus human confirmation.",
        "7. Never ask the user to paste API keys, tokens, or secrets into project files.",
        "8. Keep Allowed Scope concrete; do not use vague phrases like related files.",
        "",
        "## First Questions",
        "",
    ]
    for question in questions:
        lines.append("- %s" % question)
    lines.append("")
    return "\n".join(lines)


def _default_injection_text(src_root):
    path = src_root / ".project_wiki" / "INJECTION.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return (
        "# Codex SpecPilot Injection\n\n"
        "Read `.project_wiki/PROJECT_SPEC.md` as the task contract. "
        "If the task contract is missing or incomplete, do not develop code; "
        "ask the user for the missing requirements first.\n"
    )


def _source_wiki_text(src_root, name, fallback):
    path = src_root / ".project_wiki" / name
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except OSError:
        pass
    return fallback


def _wiki_defaults(root, project_info):
    src_root = source_root()
    return {
        "INJECTION.md": _default_injection_text(src_root),
        "WORKFLOW.md": _source_wiki_text(src_root, "WORKFLOW.md", (
            "# Workflow\n\n"
            "1. SpecPilot Hook auto-detects missing task-contract files.\n"
            "2. Codex interviews the user until requirements and GitHub sync policy are concrete.\n"
            "3. The controlled Hook flow writes `.project_wiki/PROJECT_SPEC.md`.\n"
            "4. User says: `开始工作`.\n"
            "5. Codex Worker develops from the task contract until done.\n"
        )),
        "PERMISSIONS.md": _source_wiki_text(src_root, "PERMISSIONS.md", (
            "# Permissions\n\n"
            "Allowed Scope and Protected Scope are defined by `.project_wiki/PROJECT_SPEC.md`.\n\n"
            "Codex Worker must not modify `.project_wiki/PROJECT_SPEC.md` directly.\n"
            "The corresponding SpecPilot Hook may write task-contract and state files.\n"
            "GitHub push/tag/remote operations require explicit PROJECT_SPEC permission; "
            "default is local-only. Tokens and secrets must not be written to project files.\n"
        )),
        "PROJECT_ONBOARDING.md": build_onboarding_markdown(project_info),
        "PROJECT_SPEC_TEMPLATE.md": _source_wiki_text(src_root, "PROJECT_SPEC_TEMPLATE.md", (
            "# PROJECT_SPEC\n\n"
            "## 0. Project Mode\n\n"
            "`supervised_project_development`\n\n"
            "## 1. Project Goal\n\n"
            "NEEDS_USER_CONFIRMATION\n"
        )),
        "PROJECT_SPEC.md": (
            "# PROJECT_SPEC\n\n"
            "%s\n\n"
            "This project has been detected by SpecPilot, but the task contract "
            "is not complete yet. Continue onboarding before development starts.\n"
            % ONBOARDING_MARKER
        ),
        "latest_context.md": (
            "# Latest Judge Context\n\n"
            "VERDICT: onboarding_required\n"
            "AUTO_CONTINUE: disabled\n"
            "NEXT_ACTION: Ask onboarding questions and generate PROJECT_SPEC before development.\n"
            "REASON: SpecPilot detected a project without a complete task contract.\n"
        ),
        "loop_state.json": json.dumps({
            "loop_count": 0,
            "auto_continue": False,
            "last_verdict": "onboarding_required",
        }, indent=2),
        "JUDGE.md": "# Codex SpecPilot -- JUDGE\n\n_No judgments yet._\n",
        "guard_log.jsonl": "",
        "COMPLETION_REPORT_TEMPLATE.md": _source_wiki_text(src_root, "COMPLETION_REPORT_TEMPLATE.md", (
            "# Completion Report\n\n"
            "## Final Status\n\n"
            "- Status:\n"
            "- Completed tasks:\n"
            "- Modified files:\n"
            "- Validation:\n"
        )),
    }


def _write_if_missing(path, content, force=False):
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _copy_if_needed(src, dst, force=False):
    if dst.exists() and not force:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _same_bytes(src, dst):
    try:
        return src.read_bytes() == dst.read_bytes()
    except OSError:
        return False


def _copy_if_changed(src, dst, force=False):
    if not src.exists():
        return None
    existed = dst.exists()
    if existed and not force and _same_bytes(src, dst):
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return "updated" if existed else "written"


def _write_if_changed(path, content, force=False):
    existed = path.exists()
    if existed and not force:
        try:
            if path.read_text(encoding="utf-8") == content:
                return None
        except OSError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return "updated" if existed else "written"


def _record_action(action, rel_path, written, updated, skipped):
    if action == "written":
        written.append(rel_path)
    elif action == "updated":
        updated.append(rel_path)
    else:
        skipped.append(rel_path)


def _managed_wiki_defaults(root, project_info):
    defaults = _wiki_defaults(root, project_info)
    return {name: defaults[name] for name in MANAGED_WIKI_FILES if name in defaults}


def _managed_rel_paths():
    paths = ["hooks/%s" % name for name in HOOK_FILES]
    paths.append(".codex/hooks.json")
    paths.extend(".project_wiki/%s" % name for name in MANAGED_WIKI_FILES)
    return sorted(paths)


def _write_manifest(root, src_root, written, updated, skipped, force=False):
    manifest_path = root / ".project_wiki" / MANIFEST_FILE
    data = {
        "name": "Codex SpecPilot",
        "runtime_version": SPEC_PILOT_RUNTIME_VERSION,
        "source_root": str(src_root),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "managed_files": _managed_rel_paths(),
    }
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    return _write_if_changed(manifest_path, text, force=force)


def bootstrap_wiki_files(target_dir, force=False):
    root = Path(target_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    info = inspect_project(root)
    written = []
    skipped = []

    wiki = root / ".project_wiki"
    for name, content in _wiki_defaults(root, info).items():
        path = wiki / name
        if _write_if_missing(path, content, force=force):
            written.append(str(path.relative_to(root)))
        else:
            skipped.append(str(path.relative_to(root)))

    return {
        "ok": True,
        "target_dir": str(root),
        "project": info,
        "questions": onboarding_questions(info),
        "written": written,
        "skipped": skipped,
        "next_action": "Continue onboarding in Codex before saying 开始工作.",
    }


def ensure_runtime_files(target_dir, force=False):
    """Create or refresh the small SpecPilot runtime in a target project.

    This is intentionally narrow: Hook code, hook config, and static wiki
    instruction/template files are managed. The project contract, logs, judge
    state, loop state, and completion report are never overwritten here.
    """
    root = Path(target_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    src_root = source_root().resolve()

    base = bootstrap_wiki_files(root, force=False)
    written = list(base.get("written", []))
    updated = []
    skipped = list(base.get("skipped", []))

    if root != src_root:
        hooks_dir = root / "hooks"
        for name in HOOK_FILES:
            rel = "hooks/%s" % name
            action = _copy_if_changed(src_root / "hooks" / name, hooks_dir / name, force=force)
            _record_action(action, rel, written, updated, skipped)

        rel = ".codex/hooks.json"
        action = _copy_if_changed(
            src_root / ".codex" / "hooks.json",
            root / ".codex" / "hooks.json",
            force=force,
        )
        _record_action(action, rel, written, updated, skipped)

        info = inspect_project(root)
        for name, content in _managed_wiki_defaults(root, info).items():
            rel = ".project_wiki/%s" % name
            action = _write_if_changed(root / ".project_wiki" / name, content, force=force)
            _record_action(action, rel, written, updated, skipped)

    if root != src_root:
        rel = ".project_wiki/%s" % MANIFEST_FILE
        action = _write_manifest(root, src_root, written, updated, skipped, force=True)
        _record_action(action, rel, written, updated, skipped)

    return {
        "ok": True,
        "target_dir": str(root),
        "source_root": str(src_root),
        "runtime_version": SPEC_PILOT_RUNTIME_VERSION,
        "project": inspect_project(root),
        "questions": onboarding_questions(inspect_project(root)),
        "written": written,
        "updated": updated,
        "skipped": skipped,
        "next_action": "SpecPilot runtime files are current; continue onboarding or development.",
    }


def bootstrap_project(target_dir, force=False):
    result = ensure_runtime_files(target_dir, force=force)
    result["next_action"] = (
        "Open Codex in the target project; Hook onboarding will create or finish PROJECT_SPEC."
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inject SpecPilot into a project.")
    parser.add_argument("target", nargs="?", default=".", help="Target project directory.")
    parser.add_argument("--inspect", action="store_true", help="Only inspect and print onboarding questions.")
    parser.add_argument("--bootstrap", action="store_true", help="Create SpecPilot files in the target project.")
    parser.add_argument("--upgrade", action="store_true", help="Refresh managed SpecPilot files in the target project.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing SpecPilot files.")
    args = parser.parse_args(argv)

    if args.upgrade:
        result = ensure_runtime_files(args.target, force=args.force)
    elif args.bootstrap:
        result = bootstrap_project(args.target, force=args.force)
    else:
        info = inspect_project(args.target)
        result = {
            "ok": True,
            "target_dir": info["target_dir"],
            "project": info,
            "questions": onboarding_questions(info),
            "next_action": "Run with --bootstrap to install SpecPilot files.",
        }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
