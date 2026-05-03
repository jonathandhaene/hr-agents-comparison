"""Copilot Studio HR API — FastAPI backend for Solution B.

Exposes the same endpoint shapes defined in
`solution/connectors/hr-api.swagger.json`. Copilot Studio topics call these
via the Custom Connector (through APIM in production). Includes UC7
performance narrative endpoints.

Notes:
- Auth: none for local dev; in production the Custom Connector routes through
  APIM with an API key enforced at the gateway.
- State is in-memory (resets on restart). For production, store mutable data in
  Dataverse (native to the Power Platform solution).
- UC7 uses the fine-tuned Foundry deployment when FOUNDRY_NARRATIVE_DEPLOYMENT
  is set, otherwise returns a fixture-based demo draft.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

DATA_DIR = Path(os.environ.get("HR_DATA_DIR", Path(__file__).parent.parent / "data"))
SOLUTION = "copilot-studio-agent"

app = FastAPI(title="Zava HR API (Copilot Studio)", version="1.0.0")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _load(name: str) -> Any:
    return json.loads((DATA_DIR / f"{name}.json").read_text(encoding="utf-8"))


_EMPLOYEES: list[dict] = _load("employees")
_LEAVE_BALANCES: dict = _load("leave_balances")
_JOBS: list[dict] = _load("jobs")
_ONBOARDING_TEMPLATE: dict = _load("onboarding_template")
_FEEDBACK_CYCLES: dict = _load("feedback_cycles")
_TICKET_CATEGORIES: dict = _load("ticket_categories")
_COMPETENCY_FRAMEWORK: dict = _load("competency_framework")
_PERFORMANCE_NARRATIVES: dict = _load("performance_narratives")

# Mutable state — replace with Dataverse in production.
_LEAVE_REQUESTS: dict[str, dict] = {}
_ONBOARDING_PLANS: dict[str, dict] = {}
_FEEDBACK_REQUESTS: dict[str, dict] = {}
_TICKETS: dict[str, dict] = {}
_NARRATIVE_DRAFTS: dict[str, dict] = {}
_SUBMITTED_NARRATIVES: dict[str, dict] = {}

_POLICIES_DIR = DATA_DIR / "policies"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emp(eid_or_email: str) -> dict | None:
    for e in _EMPLOYEES:
        if e["id"] == eid_or_email or e.get("email") == eid_or_email:
            return e
    return None


def _classify_text(text: str) -> dict:
    lowered = text.lower()
    chosen = None
    for cat in _TICKET_CATEGORIES.get("categories", []):
        for ex in cat.get("examples", []):
            if ex.lower() in lowered:
                chosen = cat
                break
        if chosen:
            break
    if not chosen:
        chosen = {
            "id": "OTHER",
            "label": "Uncategorized",
            "sensitivity": "medium",
            "autoAnswer": False,
            "escalateImmediately": False,
        }
    return {
        "categoryId": chosen["id"],
        "categoryLabel": chosen["label"],
        "sensitivity": chosen.get("sensitivity", "medium"),
        "autoAnswer": chosen.get("autoAnswer", False),
        "escalateImmediately": chosen.get("escalateImmediately", False),
    }


def _grade_competencies(grade: str) -> list[dict]:
    for level in _COMPETENCY_FRAMEWORK.get("levels", []):
        if level["grade"] == grade:
            return level.get("competencies", [])
    return []


def _example_narrative(grade: str) -> str:
    for n in _PERFORMANCE_NARRATIVES.get("narratives", []):
        if n["employee_grade"] == grade and n.get("manager_approved"):
            return n["narrative"]
    return ""


def _draft_narrative(employee: dict, grade: str, cycle_id: str, manager_notes: str, feedback_summary: str) -> str:
    """Return a grade-calibrated draft narrative.

    Production path: call the fine-tuned Foundry deployment specified by
    FOUNDRY_NARRATIVE_DEPLOYMENT. In Copilot Studio this is invoked via a
    generative answers node pointing at the fine-tuned deployment.
    Demo path: use the fixture narratives as a template.
    """
    deployment = os.environ.get("FOUNDRY_NARRATIVE_DEPLOYMENT")
    if deployment:
        try:
            from azure.ai.projects import AIProjectClient  # type: ignore[import-not-found]
            from azure.identity import DefaultAzureCredential  # type: ignore[import-not-found]

            endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
            proj = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
            competencies = _grade_competencies(grade)
            competency_text = "\n".join(f"- {c['name']}: {c['descriptor']}" for c in competencies)
            prompt = (
                f"You are an HR writing assistant. Draft a performance narrative for "
                f"{employee['displayName']} (grade {grade}) for cycle {cycle_id}.\n\n"
                f"Grade-level competencies:\n{competency_text}\n\n"
                f"360 feedback summary:\n{feedback_summary or '(not provided)'}\n\n"
                f"Manager notes:\n{manager_notes}\n\n"
                "Write a 3-sentence narrative calibrated to the grade level. "
                "Be specific, cite evidence, and include one growth area."
            )
            response = proj.inference.get_chat_completions(
                model=deployment,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content.strip()
        except Exception:  # noqa: BLE001
            pass

    example = _example_narrative(grade)
    if example:
        return example
    return (
        f"{employee['displayName']} has delivered strong results during {cycle_id}. "
        f"Manager notes highlight: {manager_notes[:120]}{'...' if len(manager_notes) > 120 else ''}. "
        "Growth area: continue expanding cross-functional impact."
    )


# ---------------------------------------------------------------------------
# Routes — Health
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "solution": SOLUTION}


# ---------------------------------------------------------------------------
# Routes — Employees
# ---------------------------------------------------------------------------


@app.get("/employees/byName")
def find_employees_by_name(name: str) -> dict:
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    needle = name.lower()
    matches = [
        {"id": e["id"], "displayName": e["displayName"], "email": e["email"]}
        for e in _EMPLOYEES
        if needle in e["displayName"].lower()
    ]
    return {"matches": matches}


@app.get("/employees/byPersona")
def find_employee_by_persona(persona: str) -> dict:
    for e in _EMPLOYEES:
        if e.get("persona") == persona:
            return {"id": e["id"], "displayName": e["displayName"], "email": e["email"]}
    raise HTTPException(status_code=404, detail="No employee with that persona")


@app.get("/employees/{employee_id}")
def get_employee(employee_id: str) -> dict:
    e = _emp(employee_id)
    if not e:
        raise HTTPException(status_code=404, detail="Employee not found")
    return e


# ---------------------------------------------------------------------------
# Routes — Leave
# ---------------------------------------------------------------------------


@app.post("/leave/request", status_code=201)
def request_leave(body: dict) -> dict:
    employee_id = body.get("employeeId")
    start = body.get("startDate")
    end = body.get("endDate")
    leave_type = body.get("type", "vacation")
    if not (employee_id and start and end):
        raise HTTPException(status_code=400, detail="employeeId, startDate, endDate are required")
    if leave_type not in {"vacation", "sick", "personal"}:
        raise HTTPException(status_code=400, detail="type must be vacation|sick|personal")
    emp = _emp(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    if not emp.get("managerId"):
        raise HTTPException(status_code=400, detail="Employee has no manager on file")
    try:
        s = date.fromisoformat(start)
        e_date = date.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="startDate / endDate must be yyyy-mm-dd")
    days = (e_date - s).days + 1
    if days <= 0:
        raise HTTPException(status_code=400, detail="endDate must be on/after startDate")
    rid = f"LR-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "id": rid,
        "employeeId": employee_id,
        "managerId": emp["managerId"],
        "startDate": start,
        "endDate": end,
        "type": leave_type,
        "days": days,
        "status": "pending",
        "note": body.get("note"),
        "decisionNote": None,
        "createdAt": _now(),
    }
    _LEAVE_REQUESTS[rid] = record
    return record


@app.get("/leave/{leave_id}")
def get_leave(leave_id: str) -> dict:
    rec = _LEAVE_REQUESTS.get(leave_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return rec


def _decide_leave(leave_id: str, target: str, body: dict) -> dict:
    rec = _LEAVE_REQUESTS.get(leave_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if rec["status"] == target:
        return rec
    if rec["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot transition from {rec['status']} to {target}")
    rec["status"] = target
    rec["decisionNote"] = body.get("decisionNote") if isinstance(body, dict) else None
    if target == "approved":
        for b in _LEAVE_BALANCES.get("balances", []):
            if b["employeeId"] == rec["employeeId"]:
                key = {"vacation": "vacationDays", "sick": "sickDays", "personal": "personalDays"}[rec["type"]]
                b[key] = max(0, b[key] - rec["days"])
    return rec


@app.post("/leave/{leave_id}/approve")
def approve_leave(leave_id: str, body: dict = None) -> dict:  # type: ignore[assignment]
    return _decide_leave(leave_id, "approved", body or {})


@app.post("/leave/{leave_id}/reject")
def reject_leave(leave_id: str, body: dict = None) -> dict:  # type: ignore[assignment]
    return _decide_leave(leave_id, "rejected", body or {})


# ---------------------------------------------------------------------------
# Routes — Onboarding
# ---------------------------------------------------------------------------


@app.post("/onboarding/start", status_code=201)
def start_onboarding(body: dict) -> dict:
    new_hire = _emp(body.get("newHireId", ""))
    manager = _emp(body.get("managerId", ""))
    if not (new_hire and manager):
        raise HTTPException(status_code=404, detail="newHireId or managerId not found")
    try:
        start = date.fromisoformat(body["startDate"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="startDate must be yyyy-mm-dd")
    buddy = _emp(body.get("buddyId", "")) if body.get("buddyId") else None
    plan_id = f"OB-{uuid.uuid4().hex[:8].upper()}"
    template_tasks = (
        _ONBOARDING_TEMPLATE.get("tasks", _ONBOARDING_TEMPLATE)
        if isinstance(_ONBOARDING_TEMPLATE, dict)
        else _ONBOARDING_TEMPLATE
    )
    owner_to_emp = {
        "new-hire": new_hire,
        "manager": manager,
        "buddy": buddy or manager,
        "it": next((e for e in _EMPLOYEES if e.get("persona") == "it"), manager),
        "hr-partner": next((e for e in _EMPLOYEES if e.get("persona") == "hr-partner"), manager),
    }
    tasks = [
        {
            "id": t["id"],
            "title": t["title"],
            "owner": t.get("owner", ""),
            "ownerEmployeeId": owner_to_emp.get(t.get("owner", ""), manager)["id"],
            "dueDate": date.fromordinal(start.toordinal() + int(t.get("dueOffsetDays", 0))).isoformat(),
            "critical": bool(t.get("critical", False)),
            "status": "not-started",
            "description": t.get("description", ""),
        }
        for t in template_tasks
    ]
    plan = {
        "id": plan_id,
        "newHireId": new_hire["id"],
        "managerId": manager["id"],
        "buddyId": buddy["id"] if buddy else None,
        "startDate": start.isoformat(),
        "tasks": tasks,
        "status": "active",
    }
    _ONBOARDING_PLANS[plan_id] = plan
    return plan


@app.get("/onboarding/{plan_id}")
def get_onboarding(plan_id: str) -> dict:
    plan = _ONBOARDING_PLANS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@app.post("/onboarding/{plan_id}/task/{task_id}/status")
def update_task_status(plan_id: str, task_id: str, body: dict) -> dict:
    plan = _ONBOARDING_PLANS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    new_status = body.get("status")
    valid = {"not-started", "in-progress", "done", "overdue"}
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(valid)}")
    for t in plan["tasks"]:
        if t["id"] == task_id:
            t["status"] = new_status
            return t
    raise HTTPException(status_code=404, detail="Task not found")


# ---------------------------------------------------------------------------
# Routes — Jobs (UC4)
# ---------------------------------------------------------------------------


@app.post("/jobs/search")
def jobs_search(body: dict) -> dict:
    employee_id = body.get("employeeId")
    if not employee_id:
        raise HTTPException(status_code=400, detail="employeeId is required")
    emp = _emp(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    interests = {i.lower() for i in (body.get("interests") or [])}
    location = (body.get("location") or "").lower()
    scored: list[tuple[int, dict]] = []
    for j in _JOBS:
        score = 0
        for s in j.get("skills", []):
            if s.lower() in interests:
                score += 2
            if s in emp.get("skills", []):
                score += 1
        if location and location in j.get("location", "").lower():
            score += 1
        if score > 0:
            scored.append((score, j))
    scored.sort(key=lambda x: x[0], reverse=True)
    return {
        "matches": [
            {"id": j["id"], "title": j["title"], "location": j["location"], "skills": j.get("skills", [])}
            for _, j in scored[:5]
        ]
    }


# ---------------------------------------------------------------------------
# Routes — Feedback (UC5)
# ---------------------------------------------------------------------------


@app.post("/feedback/request", status_code=201)
def open_feedback(body: dict) -> dict:
    subject_id = body.get("subjectEmployeeId")
    if not subject_id:
        raise HTTPException(status_code=400, detail="subjectEmployeeId is required")
    rid = f"FBR-{uuid.uuid4().hex[:8].upper()}"
    _FEEDBACK_REQUESTS[rid] = {
        "id": rid,
        "subjectEmployeeId": subject_id,
        "reviewerIds": body.get("requestedReviewerIds") or [],
        "responses": [],
    }
    return {"id": rid, "subjectEmployeeId": subject_id, "reviewerIds": _FEEDBACK_REQUESTS[rid]["reviewerIds"]}


@app.get("/feedback/{request_id}/summary")
def get_feedback_summary(request_id: str) -> dict:
    rec = _FEEDBACK_REQUESTS.get(request_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Feedback request not found")
    return {"requestId": request_id, "responses": rec.get("responses", [])}


# ---------------------------------------------------------------------------
# Routes — Tickets (UC6)
# ---------------------------------------------------------------------------


@app.post("/tickets/classify")
def classify_ticket(body: dict) -> dict:
    description = body.get("description")
    if not description:
        raise HTTPException(status_code=400, detail="description is required")
    return _classify_text(description)


@app.post("/tickets/create", status_code=201)
def create_ticket(body: dict) -> dict:
    employee_id = body.get("employeeId")
    description = body.get("description")
    if not (employee_id and description):
        raise HTTPException(status_code=400, detail="employeeId and description are required")
    emp = _emp(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    classification = _classify_text(description)
    tid = f"INC-{1000 + len(_TICKETS) + 1}"
    record = {
        "id": tid,
        "employeeId": emp["id"],
        "description": description,
        "category": classification,
        "status": "open",
        "createdAt": _now(),
    }
    _TICKETS[tid] = record
    return record


@app.post("/tickets/{ticket_id}/escalate")
def escalate_ticket(ticket_id: str) -> dict:
    rec = _TICKETS.get(ticket_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Ticket not found")
    rec["status"] = "escalated"
    rec["escalatedAt"] = _now()
    return rec


# ---------------------------------------------------------------------------
# Routes — Performance Narratives (UC7)
# ---------------------------------------------------------------------------


@app.post("/narratives/draft", status_code=201)
def draft_narrative(body: dict) -> dict:
    employee_id = body.get("employeeId")
    cycle_id = body.get("cycleId")
    manager_notes = body.get("managerNotes", "")
    feedback_request_id = body.get("feedbackRequestId")
    if not (employee_id and cycle_id):
        raise HTTPException(status_code=400, detail="employeeId and cycleId are required")
    emp = _emp(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    grade = emp.get("grade", "L3")

    feedback_summary = ""
    if feedback_request_id:
        rec = _FEEDBACK_REQUESTS.get(feedback_request_id)
        if rec:
            responses = rec.get("responses", [])
            if responses:
                feedback_summary = "; ".join(str(r) for r in responses[:5])

    draft_text = _draft_narrative(emp, grade, cycle_id, manager_notes, feedback_summary)
    draft_id = f"ND-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "draftId": draft_id,
        "employeeId": employee_id,
        "cycleId": cycle_id,
        "grade": grade,
        "draft": draft_text,
        "status": "draft",
        "createdAt": _now(),
    }
    _NARRATIVE_DRAFTS[draft_id] = record
    return record


@app.post("/narratives/submit", status_code=201)
def submit_narrative(body: dict) -> dict:
    draft_id = body.get("draftId")
    approved_text = body.get("approvedText")
    if not (draft_id and approved_text):
        raise HTTPException(status_code=400, detail="draftId and approvedText are required")
    draft = _NARRATIVE_DRAFTS.get(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.get("status") == "submitted":
        raise HTTPException(status_code=409, detail="Draft already submitted")
    submission_id = f"NS-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "submissionId": submission_id,
        "draftId": draft_id,
        "employeeId": draft["employeeId"],
        "cycleId": draft["cycleId"],
        "grade": draft["grade"],
        "approvedText": approved_text,
        "status": "submitted",
        "submittedAt": _now(),
    }
    _SUBMITTED_NARRATIVES[submission_id] = record
    draft["status"] = "submitted"
    return record
