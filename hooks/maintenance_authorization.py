"""One-shot protected maintenance authorization leases."""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone

try:
    from project_paths import wiki_dir as default_wiki_dir
    from permission_policy import is_supervision_file
except ModuleNotFoundError:
    from hooks.project_paths import wiki_dir as default_wiki_dir
    from hooks.permission_policy import is_supervision_file


LEASE_FILE = "maintenance_authorization_leases.json"
DEFAULT_TTL_MINUTES = 45
AUTH_TERMS = (
    "允许",
    "可以",
    "同意",
    "授权",
    "临时关闭",
    "放行",
    "approve",
    "approved",
    "allow",
    "ok",
    "yes",
)
REJECTION_TERMS = (
    "不同意",
    "不允许",
    "不可以",
    "拒绝",
    "不要",
    "no",
    "reject",
    "deny",
)
AMBIGUOUS_AUTH_TERMS = (
    "可以吧",
    "也许",
    "maybe",
)
MAINTENANCE_TERMS = (
    "pretooluse",
    "pre-tool",
    "protected",
    "受保护",
    "保护",
    "hook",
    "guard",
    "judge-system",
    "维护",
    "修复",
)
EXCLUDED_BASENAMES = {
    "PROJECT_SPEC.md",
    "JUDGE.md",
    "latest_context.md",
    "judge_latest.json",
    "loop_state.json",
    "guard_log.jsonl",
    "maintenance_authorization_leases.json",
    "specpilot_manifest.json",
}


def _lease_path(wiki_dir=None):
    return os.path.join(wiki_dir or default_wiki_dir(), LEASE_FILE)


def _project_root(wiki_dir=None):
    return os.path.dirname(wiki_dir or default_wiki_dir())


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _normalize_path(path, wiki_dir=None):
    raw = str(path or "").strip().strip("'\"`()[]")
    raw = raw.replace("\\", "/")
    root = _project_root(wiki_dir).replace("\\", "/")
    if raw.startswith(root + "/"):
        raw = raw[len(root) + 1:]
    raw = os.path.normpath(raw).replace("\\", "/")
    if raw == ".":
        return ""
    return raw.lstrip("./")


def _same_target(left, right, wiki_dir=None):
    left_norm = _normalize_path(left, wiki_dir=wiki_dir)
    right_norm = _normalize_path(right, wiki_dir=wiki_dir)
    return (
        left_norm == right_norm
        or left_norm.endswith("/" + right_norm)
        or right_norm.endswith("/" + left_norm)
    )


def _is_allowed_maintenance_target(path, wiki_dir=None):
    normalized = _normalize_path(path, wiki_dir=wiki_dir)
    basename = normalized.rsplit("/", 1)[-1]
    if not normalized or basename in EXCLUDED_BASENAMES:
        return False
    if normalized.startswith("hooks/") and normalized.endswith(".py"):
        return True
    if normalized.startswith("tests/") and normalized.endswith(".py"):
        return True
    if normalized == ".codex/hooks.json":
        return True
    if basename in {
        "PROJECT_SPEC_TEMPLATE.md",
        "COMPLETION_REPORT_TEMPLATE.md",
        "INJECTION.md",
    }:
        return True
    return False


def extract_authorized_paths(text, wiki_dir=None):
    """Extract narrow maintenance targets from prompt/latest-context text."""
    text = text or ""
    candidates = []

    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        candidates.append(match.group(1))
    for match in re.finditer(
        r"(?:^|[\s`'\"，,：:])((?:/[\w .@+\-]+/)?(?:hooks|tests)/[\w.\-]+\.py|\.codex/hooks\.json|\.project_wiki/[\w.\-]+\.md)",
        text,
    ):
        candidates.append(match.group(1))

    paths = []
    for candidate in candidates:
        normalized = _normalize_path(candidate, wiki_dir=wiki_dir)
        if _is_allowed_maintenance_target(normalized, wiki_dir=wiki_dir):
            if normalized not in paths:
                paths.append(normalized)
    return paths


def _has_authorization_intent(text):
    lower = (text or "").lower()
    original = text or ""
    if any(term in lower for term in REJECTION_TERMS):
        return False
    if any(term in lower for term in AMBIGUOUS_AUTH_TERMS):
        return False
    for term in ("允许", "可以", "同意", "授权", "临时关闭", "放行"):
        if term in original:
            return True
    return any(
        re.search(r"\b%s\b" % re.escape(term), lower)
        for term in ("approve", "approved", "allow", "ok", "yes")
    )


def _has_maintenance_context(text):
    lower = (text or "").lower()
    return any(term in lower for term in MAINTENANCE_TERMS)


def load_leases(wiki_dir=None):
    path = _lease_path(wiki_dir)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("leases", [])
            if isinstance(data, list):
                return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def save_leases(leases, wiki_dir=None):
    path = _lease_path(wiki_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"leases": leases}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def create_maintenance_lease(paths, reason, prompt_text="", wiki_dir=None,
                             ttl_minutes=DEFAULT_TTL_MINUTES, max_uses=1):
    normalized_paths = []
    for path in paths or []:
        normalized = _normalize_path(path, wiki_dir=wiki_dir)
        if _is_allowed_maintenance_target(normalized, wiki_dir=wiki_dir):
            if normalized not in normalized_paths:
                normalized_paths.append(normalized)
    if not normalized_paths:
        return {"created": False, "reason": "no allowed maintenance target paths"}

    now = _utc_now()
    lease = {
        "id": hashlib.sha256(
            ("%s|%s|%s" % (now.isoformat(), reason, ",".join(normalized_paths))).encode("utf-8")
        ).hexdigest()[:16],
        "target_paths": normalized_paths,
        "reason": (reason or "user-authorized protected maintenance")[:500],
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(),
        "max_uses": int(max_uses),
        "used_count": 0,
        "source_prompt_hash": hashlib.sha256((prompt_text or "").encode("utf-8")).hexdigest()[:16],
        "source_summary": (prompt_text or "").strip()[:500],
        "consumed": [],
    }
    leases = load_leases(wiki_dir)
    leases.append(lease)
    save_leases(leases, wiki_dir)
    return {"created": True, "lease": lease}


def create_lease_from_prompt(prompt_text, latest_context="", wiki_dir=None):
    combined = "%s\n%s" % (prompt_text or "", latest_context or "")
    if not _has_authorization_intent(prompt_text):
        return {"created": False, "reason": "prompt has no authorization intent"}
    if not _has_maintenance_context(combined):
        return {"created": False, "reason": "no protected-maintenance context"}
    paths = extract_authorized_paths(combined, wiki_dir=wiki_dir)
    if not paths:
        return {"created": False, "reason": "no explicit allowed maintenance target paths"}
    return create_maintenance_lease(
        paths,
        reason="User authorized one-shot protected maintenance for: %s" % ", ".join(paths),
        prompt_text=prompt_text,
        wiki_dir=wiki_dir,
    )


def _lease_active(lease, now=None):
    now = now or _utc_now()
    expires_at = _parse_time(lease.get("expires_at"))
    if expires_at and now > expires_at:
        return False
    try:
        if int(lease.get("used_count", 0)) >= int(lease.get("max_uses", 1)):
            return False
    except (TypeError, ValueError):
        return False
    return True


def find_matching_lease(file_paths, command="", wiki_dir=None, now=None):
    paths = [_normalize_path(path, wiki_dir=wiki_dir) for path in (file_paths or [])]
    paths = [path for path in paths if path]
    protected_paths = [path for path in paths if is_supervision_file(path)]
    if not protected_paths:
        return {"matched": False, "reason": "no protected target paths"}
    if any(not _is_allowed_maintenance_target(path, wiki_dir=wiki_dir) for path in paths):
        return {
            "matched": False,
            "reason": "maintenance lease can only cover explicit runtime maintenance targets",
        }

    leases = load_leases(wiki_dir)
    for lease in leases:
        if not _lease_active(lease, now=now):
            continue
        targets = lease.get("target_paths", [])
        if all(
            any(_same_target(path, target, wiki_dir=wiki_dir) for target in targets)
            for path in paths
        ):
            return {"matched": True, "lease": lease, "paths": paths}
    return {"matched": False, "reason": "no active lease covers protected target paths"}


def consume_matching_lease(file_paths, command="", wiki_dir=None):
    leases = load_leases(wiki_dir)
    match = find_matching_lease(file_paths, command=command, wiki_dir=wiki_dir)
    if not match.get("matched"):
        return {"allowed": False, "reason": match.get("reason", "no matching lease")}

    lease_id = match["lease"].get("id")
    now = _utc_now().isoformat()
    for lease in leases:
        if lease.get("id") == lease_id:
            lease["used_count"] = int(lease.get("used_count", 0)) + 1
            lease.setdefault("consumed", []).append({
                "at": now,
                "command_hash": hashlib.sha256((command or "").encode("utf-8")).hexdigest()[:16],
                "paths": match.get("paths", []),
            })
            break
    save_leases(leases, wiki_dir)
    return {"allowed": True, "lease_id": lease_id, "paths": match.get("paths", [])}
