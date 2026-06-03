"""Active Mission Snapshot helpers for long PROJECT_SPEC files."""
import re


SNAPSHOT_TITLE = "Active Mission Snapshot"


def _heading_pattern(title):
    return re.compile(
        r"(?im)^##+\s+(?:\d+\.\s*)?%s\s*$" % re.escape(title)
    )


def _next_heading(text, start):
    match = re.search(r"(?m)^##+\s+\S.*$", text[start:])
    if not match:
        return len(text)
    return start + match.start()


def extract_active_mission_snapshot(project_spec):
    """Return the Active Mission Snapshot section body, including its heading."""
    if not project_spec:
        return ""
    match = _heading_pattern(SNAPSHOT_TITLE).search(project_spec)
    if not match:
        return ""
    end = _next_heading(project_spec, match.end())
    return project_spec[match.start():end].strip()


def parse_snapshot_items(project_spec):
    """Parse bullet-style key/value items from Active Mission Snapshot."""
    section = extract_active_mission_snapshot(project_spec)
    items = {}
    for line in section.splitlines():
        match = re.match(r"\s*[-*]\s*([^:：]+)[:：]\s*(.+?)\s*$", line)
        if match:
            key = re.sub(r"\s+", " ", match.group(1)).strip().lower()
            items[key] = match.group(2).strip()
    return items


def _parse_task_id(value):
    match = re.search(r"TASK-(\d+)", value or "", re.IGNORECASE)
    return int(match.group(1)) if match else None


def parse_current_task_range(project_spec):
    """Return (start, end) task numbers from the snapshot, or None."""
    items = parse_snapshot_items(project_spec)
    value = ""
    for key in ("current task range", "current task", "当前任务范围", "当前任务"):
        if key in items:
            value = items[key]
            break
    if not value:
        return None
    task_ids = [int(n) for n in re.findall(r"TASK-(\d+)", value, re.IGNORECASE)]
    if len(task_ids) >= 2:
        return min(task_ids[0], task_ids[1]), max(task_ids[0], task_ids[1])
    if len(task_ids) == 1:
        return task_ids[0], task_ids[0]
    return None


def normalize_release_label(text):
    """Normalize common release-label typos such as vv2.6 -> v2.6."""
    if not text:
        return ""
    lowered = text.strip().lower()
    match = re.search(r"\b(v+)(\d+(?:\.\d+)+)\b", lowered)
    if not match:
        return lowered
    return "v%s" % match.group(2)


def current_release_target(project_spec):
    items = parse_snapshot_items(project_spec)
    for key in ("current release target", "当前发布目标"):
        if key in items:
            return normalize_release_label(items[key])
    section = extract_active_mission_snapshot(project_spec)
    return normalize_release_label(section)


def detect_goal_drift(action_text, project_spec):
    """Detect obvious conflicts between a proposed action and the snapshot.

    This is deliberately narrow. It catches stale task ids and release-label
    conflicts, but avoids turning every wording mismatch into human review.
    """
    snapshot = extract_active_mission_snapshot(project_spec)
    if not snapshot or not action_text:
        return {"drift": False, "reason": ""}

    action = str(action_text)
    task_range = parse_current_task_range(project_spec)
    if task_range:
        start, end = task_range
        task_ids = [int(n) for n in re.findall(r"TASK-(\d+)", action, re.IGNORECASE)]
        stale = [n for n in task_ids if n < start or n > end]
        if stale:
            return {
                "drift": True,
                "reason": (
                    "next_action references TASK-%03d outside current snapshot range "
                    "TASK-%03d through TASK-%03d"
                ) % (stale[0], start, end),
            }

    target = current_release_target(project_spec)
    if target:
        labels = re.findall(r"\bv+\d+(?:\.\d+)+\b", action, re.IGNORECASE)
        conflicts = [
            label for label in labels
            if normalize_release_label(label) != target
        ]
        if conflicts:
            return {
                "drift": True,
                "reason": (
                    "next_action references release %s but current snapshot target is %s"
                ) % (conflicts[0], target),
            }

    return {"drift": False, "reason": ""}


def build_priority_context(project_spec, compact_context, limit):
    """Prepend the snapshot to compacted task-book context within a budget."""
    snapshot = extract_active_mission_snapshot(project_spec)
    if not snapshot:
        return compact_context
    header = (
        "[Context priority: Active Mission Snapshot -> current phase -> current "
        "TASK -> acceptance criteria -> historical summaries.]\n"
        "%s\n\n" % snapshot
    )
    if header in compact_context:
        return compact_context[:limit]
    remaining = max(0, limit - len(header))
    return (header + compact_context[:remaining]).rstrip()
