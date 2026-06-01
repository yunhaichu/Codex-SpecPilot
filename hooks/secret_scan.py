"""Small local scanner for secret material in task contracts."""
import re

EXPLICIT_SECRET_PATTERNS = (
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("OpenAI-style API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
)

SECRET_FIELD_RE = re.compile(
    r"(?im)^\s*[-*]?\s*(api[_ -]?key|token|password|private[_ -]?key|secret|credential)\s*[:=]\s*(.+)$"
)

SAFE_PLACEHOLDER_TERMS = (
    "not stored",
    "do not",
    "do not store",
    "redacted",
    "placeholder",
    "available",
    "unavailable",
    "local gh auth",
    "local gh cli",
    "none",
    "n/a",
    "<",
    ">",
    "不要",
    "不记录",
    "不保存",
    "不可用",
    "可用",
    "认证方式",
    "描述",
)


def find_secret_material(text):
    """Return short findings for likely secrets in project-facing text."""
    findings = []
    if not text:
        return findings

    for label, pattern in EXPLICIT_SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(label)

    for match in SECRET_FIELD_RE.finditer(text):
        field = match.group(1).strip()
        value = match.group(2).strip()
        lower_value = value.lower()
        if any(term in lower_value or term in value for term in SAFE_PLACEHOLDER_TERMS):
            continue
        compact = re.sub(r"[^A-Za-z0-9]", "", value)
        if len(compact) >= 12:
            findings.append("%s field contains concrete value" % field)

    deduped = []
    for finding in findings:
        if finding not in deduped:
            deduped.append(finding)
    return deduped
