"""Shared status enum normalization for SpecPilot evidence checks."""


STATUS_ALIASES = {
    "phase16_complete_with_quality_fix_required": "phase16_complete_with_quality_risks",
    "phase16_complete_with_quality_risk": "phase16_complete_with_quality_risks",
    "complete_with_quality_fix_required": "complete_with_quality_risks",
    "complete_with_quality_risk": "complete_with_quality_risks",
    "quality_fix_required": "quality_risks",
    "quality_risk": "quality_risks",
    "done": "complete",
    "completed": "complete",
    "pass": "complete",
}


COMPLETE_TERMS = (
    "complete",
    "completed",
    "done",
    "pass",
    "passed",
    "verified",
)

BLOCKED_TERMS = (
    "blocked",
    "human_review",
    "environment_blocked",
    "environment-blocked",
    "failed",
    "fail",
    "pending",
    "incomplete",
)


def normalize_status(status):
    """Return a canonical lowercase status string."""
    value = str(status or "").strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in value:
        value = value.replace("__", "_")
    return STATUS_ALIASES.get(value, value)


def statuses_equivalent(left, right):
    return normalize_status(left) == normalize_status(right)


def status_indicates_complete(status):
    """Return True when a status is complete, including complete-with-risks."""
    normalized = normalize_status(status)
    if not normalized:
        return False
    if any(term in normalized for term in BLOCKED_TERMS):
        return False
    return any(term in normalized for term in COMPLETE_TERMS)
