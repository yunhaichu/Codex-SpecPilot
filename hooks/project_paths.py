"""Project path resolution for SpecPilot hooks."""
import os
from pathlib import Path


PROJECT_MARKERS = (
    ".git",
    ".codex",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "Package.swift",
)


def _has_project_marker(path):
    if any((path / name).exists() for name in PROJECT_MARKERS):
        return True
    try:
        return any(child.name.endswith(".xcodeproj") for child in path.iterdir())
    except OSError:
        return False


def _ancestors_from(path):
    yield path
    yield from path.parents


def _find_owner(start, predicate):
    home = Path.home().resolve()
    for path in _ancestors_from(start):
        if predicate(path):
            return path
        if path == home:
            break
    return None


def project_root():
    """Return the project root whose .project_wiki should drive the hooks.

    If a project has not been onboarded yet, return the current project-shaped
    directory so UserPromptSubmit can create the first .project_wiki files.
    """
    fallback = Path(__file__).resolve().parents[1]
    env_dir = os.environ.get("CODEX_WIKIGUARD_PROJECT_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    cwd = Path(os.getcwd()).resolve()
    if (cwd / ".project_wiki").is_dir():
        return cwd

    marker_owner = _find_owner(cwd, _has_project_marker)
    if marker_owner:
        return marker_owner

    if cwd != fallback:
        return cwd
    return fallback


def wiki_dir():
    return str(project_root() / ".project_wiki")
