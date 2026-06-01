"""Project injector for bringing SpecPilot into empty or existing projects.

The injector is deliberately local and lightweight. It bootstraps the small
SpecPilot file set, inspects the target project shape, and writes onboarding
guidance so Codex can interview the user before a real PROJECT_SPEC exists.
"""
import argparse
import json
import os
import shutil
from pathlib import Path

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
    "permission_policy.py",
    "pre_tool_guard.py",
    "project_paths.py",
    "spec_steward.py",
    "stop_judge.py",
    "user_prompt_submit.py",
)

ONBOARDING_MARKER = "NEEDS_USER_CONFIRMATION"
GITHUB_SYNC_QUESTION = (
    "是否需要同步或上传到 GitHub？如果不需要，默认 local-only；如果需要，请说明认证方式"
    "（不要提供 token/密钥原文）、仓库 owner/name、公开或私有，以及允许 Hook 在哪些节点 push、tag 或 checkpoint。"
)


def source_root():
    return Path(__file__).resolve().parents[1]


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
        "6. If GitHub sync is requested, ask for auth method, public/private visibility, repo target, and allowed checkpoint/tag behavior.",
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


def _wiki_defaults(root, project_info):
    src_root = source_root()
    return {
        "INJECTION.md": _default_injection_text(src_root),
        "WORKFLOW.md": (
            "# Workflow\n\n"
            "1. SpecPilot Hook auto-detects missing task-contract files.\n"
            "2. Codex interviews the user until requirements and GitHub sync policy are concrete.\n"
            "3. The controlled Hook flow writes `.project_wiki/PROJECT_SPEC.md`.\n"
            "4. User says: `开始工作`.\n"
            "5. Codex Worker develops from the task contract until done.\n"
        ),
        "PERMISSIONS.md": (
            "# Permissions\n\n"
            "Allowed Scope and Protected Scope are defined by `.project_wiki/PROJECT_SPEC.md`.\n\n"
            "Codex Worker must not modify `.project_wiki/PROJECT_SPEC.md` directly.\n"
            "The corresponding SpecPilot Hook may write task-contract and state files.\n"
            "GitHub push/tag/remote operations require explicit PROJECT_SPEC permission; "
            "default is local-only. Tokens and secrets must not be written to project files.\n"
        ),
        "PROJECT_ONBOARDING.md": build_onboarding_markdown(project_info),
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
        "COMPLETION_REPORT_TEMPLATE.md": (
            "# Completion Report\n\n"
            "## Final Status\n\n"
            "- Status:\n"
            "- Completed tasks:\n"
            "- Modified files:\n"
            "- Validation:\n"
        ),
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


def bootstrap_project(target_dir, force=False):
    root = Path(target_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    src_root = source_root()
    written = []
    skipped = []

    hooks_dir = root / "hooks"
    for name in HOOK_FILES:
        src = src_root / "hooks" / name
        dst = hooks_dir / name
        if _copy_if_needed(src, dst, force=force):
            written.append(str(dst.relative_to(root)))
        else:
            skipped.append(str(dst.relative_to(root)))

    hooks_config = root / ".codex" / "hooks.json"
    if _copy_if_needed(src_root / ".codex" / "hooks.json", hooks_config, force=force):
        written.append(str(hooks_config.relative_to(root)))
    else:
        skipped.append(str(hooks_config.relative_to(root)))

    wiki_result = bootstrap_wiki_files(root, force=force)
    written.extend(wiki_result.get("written", []))
    skipped.extend(wiki_result.get("skipped", []))

    return {
        "ok": True,
        "target_dir": str(root),
        "project": wiki_result.get("project", {}),
        "questions": wiki_result.get("questions", []),
        "written": written,
        "skipped": skipped,
        "next_action": "Open Codex in the target project; Hook onboarding will create or finish PROJECT_SPEC.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inject SpecPilot into a project.")
    parser.add_argument("target", nargs="?", default=".", help="Target project directory.")
    parser.add_argument("--inspect", action="store_true", help="Only inspect and print onboarding questions.")
    parser.add_argument("--bootstrap", action="store_true", help="Create SpecPilot files in the target project.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing SpecPilot files.")
    args = parser.parse_args(argv)

    if args.bootstrap:
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
