"""HR mock backend — Solution A (M365 Agents SDK).

This FastAPI app is dedicated to the M365 Agents SDK solution. It is intentionally
not shared with the other two solutions; each ships its own copy.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Data loading — fixtures are baked in at build time (copied from /shared-fixtures)
# ---------------------------------------------------------------------------
DATA_DIR = Path(os.environ.get("HR_DATA_DIR", Path(__file__).parent / "data"))


def _load(name: str) -> dict | list:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


EMPLOYEES: list[dict] = _load("employees.json")
LEAVE_BALANCES: dict = _load("leave_balances.json")
JOBS: list[dict] = _load("jobs.json")
ONBOARDING_TEMPLATE: dict = _load("onboarding_template.json")
FEEDBACK_CYCLES: dict = _load("feedback_cycles.json")
TICKET_CATEGORIES: dict = _load("ticket_categories.json")

# In-memory mutable state (resets on restart — fine for demo)
LEAVE_REQUESTS: dict[str, dict] = {}
ONBOARDING_PLANS: dict[str, dict] = {}
FEEDBACK_REQUESTS: dict[str, dict] = {}
TICKETS: dict[str, dict] = {}


def _emp(emp_id: str) -> dict:
    for e in EMPLOYEES:
        if e["id"] == emp_id:
            return e
    raise HTTPException(status_code=404, detail=f"Employee {emp_id} not found")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class Employee(BaseModel):
    id: str
    displayName: str
    email: str
    title: str
    department: str
    location: str
    managerId: str | None
    hireDate: str
    skills: list[str]
    persona: str


class LeaveBalance(BaseModel):
    employeeId: str
    vacationDays: int
    sickDays: int
    personalDays: int


class LeaveRequestIn(BaseModel):
    employeeId: str
    startDate: date
    endDate: date
    type: Literal["vacation", "sick", "personal"] = "vacation"
    note: str | None = None


class LeaveRequest(BaseModel):
    id: str
    employeeId: str
    managerId: str
    startDate: date
    endDate: date
    type: str
    days: int
    status: Literal["pending", "approved", "rejected", "needs-info"]
    note: str | None = None
    decisionNote: str | None = None
    createdAt: datetime


class OnboardingStartIn(BaseModel):
    newHireId: str
    startDate: date
    managerId: str
    buddyId: str | None = None


class OnboardingTask(BaseModel):
    id: str
    title: str
    owner: str
    ownerEmployeeId: str
    dueDate: date
    critical: bool
    status: Literal["not-started", "in-progress", "done", "overdue"]
    description: str


class OnboardingPlan(BaseModel):
    id: str
    newHireId: str
    managerId: str
    buddyId: str | None
    startDate: date
    tasks: list[OnboardingTask]
    status: Literal["active", "complete"]


class JobMatchQuery(BaseModel):
    employeeId: str
    interests: list[str] = Field(default_factory=list)
    location: str | None = None


class FeedbackRequestIn(BaseModel):
    cycleId: str
    subjectEmployeeId: str
    requestedReviewerIds: list[str]


class FeedbackSubmitIn(BaseModel):
    requestId: str
    reviewerId: str
    answers: dict[str, str | int]


class TicketCreateIn(BaseModel):
    employeeId: str
    description: str


class TicketClassifyIn(BaseModel):
    description: str


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Contoso HR API (Foundry)",
    version="1.0.0",
    description="Mock HR backend for the M365 Agents SDK solution.",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "solution": "foundry"}


# ----- Employees -----
@app.get("/employees", response_model=list[Employee])
def list_employees(persona: str | None = None) -> list[dict]:
    if persona:
        return [e for e in EMPLOYEES if e["persona"] == persona]
    return EMPLOYEES


@app.get("/employees/{emp_id}", response_model=Employee)
def get_employee(emp_id: str) -> dict:
    return _emp(emp_id)


# ----- Leave -----
@app.get("/leave/balance/{emp_id}", response_model=LeaveBalance)
def leave_balance(emp_id: str) -> dict:
    for b in LEAVE_BALANCES["balances"]:
        if b["employeeId"] == emp_id:
            return b
    raise HTTPException(status_code=404, detail="Balance not found")


@app.post("/leave/request", response_model=LeaveRequest)
def request_leave(payload: LeaveRequestIn) -> dict:
    emp = _emp(payload.employeeId)
    if not emp.get("managerId"):
        raise HTTPException(status_code=400, detail="Employee has no manager on file")
    days = (payload.endDate - payload.startDate).days + 1
    if days <= 0:
        raise HTTPException(status_code=400, detail="endDate must be on/after startDate")
    req_id = f"LR-{uuid.uuid4().hex[:8].upper()}"
    record = {
        "id": req_id,
        "employeeId": payload.employeeId,
        "managerId": emp["managerId"],
        "startDate": payload.startDate,
        "endDate": payload.endDate,
        "type": payload.type,
        "days": days,
        "status": "pending",
        "note": payload.note,
        "decisionNote": None,
        "createdAt": datetime.utcnow(),
    }
    LEAVE_REQUESTS[req_id] = record
    return record


@app.post("/leave/{req_id}/approve", response_model=LeaveRequest)
def approve_leave(req_id: str, decisionNote: str | None = None) -> dict:
    req = LEAVE_REQUESTS.get(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    req["status"] = "approved"
    req["decisionNote"] = decisionNote
    # decrement balance
    for b in LEAVE_BALANCES["balances"]:
        if b["employeeId"] == req["employeeId"]:
            key = {"vacation": "vacationDays", "sick": "sickDays", "personal": "personalDays"}[req["type"]]
            b[key] = max(0, b[key] - req["days"])
    return req


@app.post("/leave/{req_id}/reject", response_model=LeaveRequest)
def reject_leave(req_id: str, decisionNote: str | None = None) -> dict:
    req = LEAVE_REQUESTS.get(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    req["status"] = "rejected"
    req["decisionNote"] = decisionNote
    return req


@app.get("/leave/{req_id}", response_model=LeaveRequest)
def get_leave(req_id: str) -> dict:
    req = LEAVE_REQUESTS.get(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return req


# ----- Onboarding -----
@app.post("/onboarding/start", response_model=OnboardingPlan)
def start_onboarding(payload: OnboardingStartIn) -> dict:
    new_hire = _emp(payload.newHireId)
    manager = _emp(payload.managerId)
    buddy = _emp(payload.buddyId) if payload.buddyId else None
    it_lead = next((e for e in EMPLOYEES if e["persona"] == "it"), None)
    hr_partner = next((e for e in EMPLOYEES if e["persona"] == "hr-partner"), None)

    owner_to_emp = {
        "new-hire": new_hire,
        "manager": manager,
        "buddy": buddy or manager,
        "it": it_lead or manager,
        "hr-partner": hr_partner or manager,
    }
    plan_id = f"OB-{uuid.uuid4().hex[:8].upper()}"
    tasks = []
    for t in ONBOARDING_TEMPLATE["tasks"]:
        owner_emp = owner_to_emp.get(t["owner"], manager)
        due = date.fromordinal(payload.startDate.toordinal() + t["dueOffsetDays"])
        tasks.append(
            {
                "id": t["id"],
                "title": t["title"],
                "owner": t["owner"],
                "ownerEmployeeId": owner_emp["id"],
                "dueDate": due,
                "critical": t["critical"],
                "status": "not-started",
                "description": t["description"],
            }
        )
    plan = {
        "id": plan_id,
        "newHireId": new_hire["id"],
        "managerId": manager["id"],
        "buddyId": buddy["id"] if buddy else None,
        "startDate": payload.startDate,
        "tasks": tasks,
        "status": "active",
    }
    ONBOARDING_PLANS[plan_id] = plan
    return plan


@app.get("/onboarding/{plan_id}", response_model=OnboardingPlan)
def get_onboarding(plan_id: str) -> dict:
    plan = ONBOARDING_PLANS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@app.post("/onboarding/{plan_id}/task/{task_id}/status")
def set_task_status(
    plan_id: str,
    task_id: str,
    status: Literal["not-started", "in-progress", "done", "overdue"],
) -> dict:
    plan = ONBOARDING_PLANS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    for t in plan["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            if all(tt["status"] == "done" for tt in plan["tasks"] if tt["critical"]):
                plan["status"] = "complete"
            return {"ok": True, "plan": plan}
    raise HTTPException(status_code=404, detail="Task not found")


# ----- Jobs (UC4) -----
@app.post("/jobs/search")
def search_jobs(q: JobMatchQuery) -> list[dict]:
    emp = _emp(q.employeeId)
    interests_lower = {i.lower() for i in q.interests}
    scored = []
    for j in JOBS:
        score = 0
        for s in j["skills"]:
            if s.lower() in interests_lower:
                score += 2
            if s in emp["skills"]:
                score += 1
        if q.location and q.location.lower() in j["location"].lower():
            score += 1
        if score > 0:
            scored.append((score, j))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [j for _, j in scored[:5]]


# ----- Feedback (UC5) -----
@app.post("/feedback/request")
def feedback_request(payload: FeedbackRequestIn) -> dict:
    cycle = next((c for c in FEEDBACK_CYCLES["cycles"] if c["id"] == payload.cycleId), None)
    if not cycle:
        raise HTTPException(status_code=404, detail="Cycle not found")
    req_id = f"FBR-{uuid.uuid4().hex[:8].upper()}"
    FEEDBACK_REQUESTS[req_id] = {
        "id": req_id,
        "cycleId": payload.cycleId,
        "subjectEmployeeId": payload.subjectEmployeeId,
        "reviewerIds": payload.requestedReviewerIds,
        "responses": [],
        "questions": cycle["questions"],
    }
    return FEEDBACK_REQUESTS[req_id]


@app.post("/feedback/submit")
def feedback_submit(payload: FeedbackSubmitIn) -> dict:
    req = FEEDBACK_REQUESTS.get(payload.requestId)
    if not req:
        raise HTTPException(status_code=404, detail="Feedback request not found")
    if payload.reviewerId not in req["reviewerIds"]:
        raise HTTPException(status_code=403, detail="Reviewer not invited")
    req["responses"].append({"reviewerId": payload.reviewerId, "answers": payload.answers})
    return {"ok": True, "received": len(req["responses"]), "expected": len(req["reviewerIds"])}


@app.get("/feedback/{req_id}/summary")
def feedback_summary(req_id: str) -> dict:
    req = FEEDBACK_REQUESTS.get(req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Feedback request not found")
    # Plain aggregation; the agent's LLM produces the narrative summary.
    return {
        "subjectEmployeeId": req["subjectEmployeeId"],
        "received": len(req["responses"]),
        "expected": len(req["reviewerIds"]),
        "questions": req["questions"],
        "responses": req["responses"],
    }


# ----- Tickets (UC6) -----
@app.post("/tickets/classify")
def tickets_classify(payload: TicketClassifyIn) -> dict:
    text = payload.description.lower()
    best = None
    for cat in TICKET_CATEGORIES["categories"]:
        for ex in cat["examples"]:
            if ex.lower() in text:
                best = cat
                break
        if best:
            break
    cat = best or {
        "id": "OTHER",
        "label": "Uncategorized",
        "sensitivity": "medium",
        "autoAnswer": False,
    }
    return {
        "categoryId": cat["id"],
        "categoryLabel": cat["label"],
        "sensitivity": cat["sensitivity"],
        "autoAnswer": cat.get("autoAnswer", False),
        "escalateImmediately": cat.get("escalateImmediately", False),
    }


@app.post("/tickets/create")
def tickets_create(payload: TicketCreateIn) -> dict:
    emp = _emp(payload.employeeId)
    classification = tickets_classify(TicketClassifyIn(description=payload.description))
    ticket_id = f"INC-{1000 + len(TICKETS) + 1}"
    hr_partner = next((e for e in EMPLOYEES if e["persona"] == "hr-partner"), None)
    TICKETS[ticket_id] = {
        "id": ticket_id,
        "employeeId": emp["id"],
        "assignedToId": hr_partner["id"] if hr_partner else None,
        "description": payload.description,
        "category": classification,
        "status": "open",
        "createdAt": datetime.utcnow().isoformat(),
    }
    return TICKETS[ticket_id]


@app.post("/tickets/{ticket_id}/escalate")
def tickets_escalate(ticket_id: str) -> dict:
    t = TICKETS.get(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    t["status"] = "escalated"
    return t


@app.get("/tickets/{ticket_id}")
def tickets_get(ticket_id: str) -> dict:
    t = TICKETS.get(ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return t


@app.get("/policies")
def list_policies() -> list[dict]:
    """List policy markdown files baked into this backend (UC1 fallback)."""
    pol_dir = DATA_DIR / "policies"
    return [
        {"name": p.stem, "path": str(p.relative_to(DATA_DIR))}
        for p in sorted(pol_dir.glob("*.md"))
    ]


@app.get("/policies/{name}")
def get_policy(name: str) -> dict:
    p = DATA_DIR / "policies" / f"{name}.md"
    if not p.exists():
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"name": name, "content": p.read_text(encoding="utf-8")}
