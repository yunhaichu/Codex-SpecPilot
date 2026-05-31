"""Project path resolution for WikiGuard hooks."""
import os
from pathlib import Path


def project_root():
    """Return the project root whose .project_wiki should drive the hooks."""
    fallback = Path(__file__).resolve().parents[1]
    candidates = [
        os.environ.get("CODEX_WIKIGUARD_PROJECT_DIR"),
        os.getcwd(),
        str(fallback),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser().resolve()
        if (path / ".project_wiki").is_dir():
            return path
    return fallback


def wiki_dir():
    return str(project_root() / ".project_wiki")
