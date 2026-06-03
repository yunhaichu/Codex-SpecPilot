"""Development Plan helpers for phase closure and next-phase drafts."""
import re


TASK_RE = re.compile(r"(?im)^\s*-\s*\[([ xX])\]\s+(TASK-\d+)\s*:\s*(.+?)\s*$")


def development_plan_tasks(project_spec):
    tasks = []
    for match in TASK_RE.finditer(project_spec or ""):
        tasks.append({
            "task_id": match.group(2).upper(),
            "title": match.group(3).strip(),
            "complete": match.group(1).lower() == "x",
        })
    return tasks


def next_incomplete_task(project_spec):
    for task in development_plan_tasks(project_spec):
        if not task["complete"]:
            return task
    return None


def phase_is_complete(project_spec):
    tasks = development_plan_tasks(project_spec)
    return bool(tasks) and all(task["complete"] for task in tasks)


def build_next_phase_contract_draft(project_spec, evidence_summary=""):
    """Draft a controlled spec-update request after a phase is closed."""
    if not phase_is_complete(project_spec):
        task = next_incomplete_task(project_spec)
        return {
            "ready": False,
            "reason": "Current phase still has incomplete work.",
            "next_task": task,
            "change_request": "",
        }

    lines = [
        "Current Development Plan appears complete. Before starting more worker "
        "development, run the controlled Spec Steward flow to close this phase "
        "and add the next phase contract.",
        "",
        "Required next-phase contract fields:",
        "- Active Mission Snapshot with current goal, task range, acceptance focus, non-goals, and release/sync policy.",
        "- Development Plan checklist for the next phase.",
        "- Acceptance Criteria and Stop Conditions for the new work.",
        "- Evidence summary from the completed phase.",
    ]
    if evidence_summary:
        lines.extend(["", "Evidence summary:", evidence_summary.strip()])
    return {
        "ready": True,
        "reason": "Current phase is complete and needs a next-phase contract before more development.",
        "next_task": None,
        "change_request": "\n".join(lines),
    }
