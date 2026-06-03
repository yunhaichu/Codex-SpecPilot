"""Task evidence reconciliation for PROJECT_SPEC status tracking."""
import json
import os
import re

try:
    from status_normalizer import normalize_status, status_indicates_complete
except ModuleNotFoundError:
    from hooks.status_normalizer import normalize_status, status_indicates_complete


TASK_ID_RE = re.compile(r"\bTASK-(\d+)\b", re.IGNORECASE)


def canonical_task_id(value):
    match = TASK_ID_RE.search(str(value or ""))
    if not match:
        return ""
    return "TASK-%03d" % int(match.group(1))


def _load_report(report):
    if isinstance(report, dict):
        return report
    if not report:
        return {}
    try:
        with open(str(report), "r", encoding="utf-8") as f:
            if str(report).endswith(".json"):
                return json.load(f)
            text = f.read()
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    data = {"raw_text": text}
    task_id = canonical_task_id(text)
    if task_id:
        data["task_id"] = task_id
    status_match = re.search(r"(?im)^\s*(?:status|状态)\s*[:：]\s*(.+?)\s*$", text)
    if status_match:
        data["status"] = status_match.group(1).strip()
    return data


def _report_task_id(report):
    for key in ("task_id", "task", "id", "current_task"):
        task_id = canonical_task_id(report.get(key))
        if task_id:
            return task_id
    return canonical_task_id(report.get("raw_text", ""))


def _report_status(report):
    for key in ("status", "verdict", "result", "phase_status"):
        value = report.get(key)
        if value:
            return normalize_status(value)
    raw = report.get("raw_text", "")
    if raw:
        for line in raw.splitlines():
            if "complete" in line.lower() or "完成" in line:
                return "complete"
    return ""


def _spec_task_state(project_spec, task_id):
    task_id = canonical_task_id(task_id)
    if not task_id:
        return "unknown"
    pattern = re.compile(
        r"(?im)^\s*-\s*\[([ xX])\]\s+%s\b" % re.escape(task_id)
    )
    match = pattern.search(project_spec or "")
    if not match:
        return "missing"
    return "complete" if match.group(1).lower() == "x" else "pending"


def reconcile_project_spec_with_reports(project_spec, reports):
    """Find report/spec status conflicts and build a controlled change request."""
    mismatches = []
    for item in reports:
        report = _load_report(item)
        task_id = _report_task_id(report)
        status = _report_status(report)
        if not task_id or not status_indicates_complete(status):
            continue
        spec_state = _spec_task_state(project_spec, task_id)
        if spec_state in ("pending", "missing"):
            mismatches.append({
                "task_id": task_id,
                "report_status": status,
                "spec_state": spec_state,
                "source": report.get("source") or report.get("path") or (
                    os.fspath(item) if not isinstance(item, dict) else "inline"
                ),
            })

    if not mismatches:
        return {"ok": True, "mismatches": [], "change_request": ""}

    lines = [
        "Task evidence reconciliation found completed-task evidence that conflicts "
        "with PROJECT_SPEC status tracking. Apply a controlled section-level "
        "PROJECT_SPEC update after reviewing the evidence:"
    ]
    for mismatch in mismatches:
        lines.append(
            "- %s: evidence status `%s`, PROJECT_SPEC state `%s`, source `%s`."
            % (
                mismatch["task_id"],
                mismatch["report_status"],
                mismatch["spec_state"],
                mismatch["source"],
            )
        )
    lines.append(
        "Update only the relevant Development Plan checklist/status notes and keep "
        "Active Mission Snapshot, current acceptance focus, GitHub policy, and "
        "Submission Requirements intact."
    )
    return {
        "ok": False,
        "mismatches": mismatches,
        "change_request": "\n".join(lines),
    }
