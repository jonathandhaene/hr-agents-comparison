"""Mixed-solution HR API on Azure Functions (Python v2 model).

A thin, function-key-protected HTTP API backed by the shared fixtures. Replaces
the FastAPI+Container App in the pure solutions because Functions Consumption
scales to zero and costs ~nothing at rest.

Notes:
- Auth: function key in `x-functions-key`. Enforced by the platform; never
    inspect/log the key here. `/health` is anonymous.
- State is in-memory (resets on cold start). For production, persist
    `_LEAVE_REQUESTS`, `_ONBOARDING_PLANS`, `_FEEDBACK_REQUESTS`, `_TICKETS`
    to Cosmos / Dataverse.
- The ticket classifier is a deterministic keyword stub so the demo runs
    offline. For production, replace `_classify_text` with a Microsoft Foundry
    call backed by Azure AI Content Safety; default to escalation on
    uncertainty.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import azure.functions as func  # type: ignore[import-not-found]

DATA_DIR = Path(os.environ.get("HR_DATA_DIR", Path(__file__).parent / "data"))
SOLUTION = "mixed"

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

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

# Mutable state.
_LEAVE_REQUESTS: dict[str, dict] = {}
_LEAVE_IDEM: dict[str, str] = {}  # idempotency-key -> request id
_ONBOARDING_PLANS: dict[str, dict] = {}
_FEEDBACK_REQUESTS: dict[str, dict] = {}
_TICKETS: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(body: dict | list, status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body, default=str),
        status_code=status,
        mimetype="application/json",
    )


def _problem(status: int, title: str, detail: str | None = None) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(
            {
                "type": "about:blank",
                "title": title,
                "status": status,
                "detail": detail or title,
            }
        ),
        status_code=status,
        mimetype="application/problem+json",
    )


def _emp(eid_or_email: str) -> dict | None:
    for e in _EMPLOYEES:
        if e["id"] == eid_or_email or e.get("email") == eid_or_email:
            return e
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _classify_text(text: str) -> dict:
    """Demo classifier — returns the unified classification shape used across
    all four solutions.
    """
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS)
def health(_: func.HttpRequest) -> func.HttpResponse:
    return _ok({"status": "ok", "solution": SOLUTION})


# ----- Employees -----
@app.route(route="employees/{id}", methods=["GET"])
def get_employee(req: func.HttpRequest) -> func.HttpResponse:
    e = _emp(req.route_params["id"])
    if not e:
        return _problem(404, "Employee not found")
    return _ok(e)


@app.route(route="employees/byName", methods=["GET"])
def find_employees_by_name(req: func.HttpRequest) -> func.HttpResponse:
    needle = (req.params.get("name") or "").lower().strip()
    if not needle:
        return _problem(400, "name is required")
    matches = [
        {"id": e["id"], "displayName": e["displayName"], "email": e["email"]}
        for e in _EMPLOYEES
        if needle in e["displayName"].lower()
    ]
    return _ok({"matches": matches})


@app.route(route="employees/byPersona", methods=["GET"])
def find_employee_by_persona(req: func.HttpRequest) -> func.HttpResponse:
    persona = req.params.get("persona")
    if not persona:
        return _problem(400, "persona is required")
    for e in _EMPLOYEES:
        if e.get("persona") == persona:
            return _ok({"id": e["id"], "displayName": e["displayName"], "email": e["email"]})
    return _problem(404, "No employee with that persona")


# ----- Leave -----
@app.route(route="leave/request", methods=["POST"])
def request_leave(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _problem(400, "Invalid JSON body")

    employee_id = body.get("employeeId")
    start = body.get("startDate")
    end = body.get("endDate")
    leave_type = body.get("type", "vacation")
    if not (employee_id and start and end):
        return _problem(400, "employeeId, startDate, endDate are required")
    if leave_type not in {"vacation", "sick", "personal"}:
        return _problem(400, "type must be vacation|sick|personal")

    emp = _emp(employee_id)
    if not emp:
        return _problem(404, f"Employee {employee_id} not found")
    if not emp.get("managerId"):
        return _problem(400, "Employee has no manager on file")

    try:
        s = date.fromisoformat(start)
        e = date.fromisoformat(end)
    except ValueError:
        return _problem(400, "startDate / endDate must be yyyy-mm-dd")
    days = (e - s).days + 1
    if days <= 0:
        return _problem(400, "endDate must be on/after startDate")

    idem = req.headers.get("Idempotency-Key")
    if idem and idem in _LEAVE_IDEM:
        return _ok(_LEAVE_REQUESTS[_LEAVE_IDEM[idem]], status=200)

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
    if idem:
        _LEAVE_IDEM[idem] = rid
    return _ok(record, status=201)


def _decide_leave(req: func.HttpRequest, target: str) -> func.HttpResponse:
    rid = req.route_params["id"]
    rec = _LEAVE_REQUESTS.get(rid)
    if not rec:
        return _problem(404, "Leave request not found")
    if rec["status"] == target:
        return _ok(rec)  # idempotent
    if rec["status"] != "pending":
        return _problem(409, f"Cannot transition from {rec['status']} to {target}")
    note: str | None = None
    try:
        body = req.get_json()
        note = body.get("decisionNote") if isinstance(body, dict) else None
    except ValueError:
        pass
    rec["status"] = target
    rec["decisionNote"] = note
    if target == "approved":
        for b in _LEAVE_BALANCES.get("balances", []):
            if b["employeeId"] == rec["employeeId"]:
                key = {"vacation": "vacationDays", "sick": "sickDays", "personal": "personalDays"}[rec["type"]]
                b[key] = max(0, b[key] - rec["days"])
    return _ok(rec)


@app.route(route="leave/{id}/approve", methods=["POST"])
def approve_leave(req: func.HttpRequest) -> func.HttpResponse:
    return _decide_leave(req, "approved")


@app.route(route="leave/{id}/reject", methods=["POST"])
def reject_leave(req: func.HttpRequest) -> func.HttpResponse:
    return _decide_leave(req, "rejected")


# ----- Onboarding -----
@app.route(route="onboarding/start", methods=["POST"])
def start_onboarding(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _problem(400, "Invalid JSON body")
    new_hire = _emp(body.get("newHireId", ""))
    manager = _emp(body.get("managerId", ""))
    if not (new_hire and manager):
        return _problem(404, "newHireId or managerId not found")
    try:
        start = date.fromisoformat(body["startDate"])
    except (KeyError, ValueError):
        return _problem(400, "startDate must be yyyy-mm-dd")
    buddy = _emp(body.get("buddyId", "")) if body.get("buddyId") else None
    plan_id = f"OB-{uuid.uuid4().hex[:8].upper()}"
    template_tasks = _ONBOARDING_TEMPLATE.get("tasks", _ONBOARDING_TEMPLATE) if isinstance(_ONBOARDING_TEMPLATE, dict) else _ONBOARDING_TEMPLATE
    owner_to_emp = {
        "new-hire": new_hire,
        "manager": manager,
        "buddy": buddy or manager,
        "it": next((e for e in _EMPLOYEES if e.get("persona") == "it"), manager),
        "hr-partner": next((e for e in _EMPLOYEES if e.get("persona") == "hr-partner"), manager),
    }
    tasks = []
    for t in template_tasks:
        owner = owner_to_emp.get(t.get("owner", ""), manager)
        due = date.fromordinal(start.toordinal() + int(t.get("dueOffsetDays", 0)))
        tasks.append(
            {
                "id": t["id"],
                "title": t["title"],
                "owner": t.get("owner", ""),
                "ownerEmployeeId": owner["id"],
                "dueDate": due.isoformat(),
                "critical": bool(t.get("critical", False)),
                "status": "not-started",
                "description": t.get("description", ""),
            }
        )
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
    return _ok(plan, status=201)


@app.route(route="onboarding/{id}/tick", methods=["POST"])
def tick_onboarding(req: func.HttpRequest) -> func.HttpResponse:
    """Idempotent daily tick. Marks not-started tasks whose due date has
    passed as in-progress and emits them as `dueTasks`. The `notified` flag
    on each task ensures repeated ticks don't re-notify."""
    plan_id = req.route_params["id"]
    plan = _ONBOARDING_PLANS.get(plan_id)
    if not plan:
        return _problem(404, "Plan not found")
    today = date.today()
    advanced: list[str] = []
    due_tasks: list[dict] = []
    for t in plan["tasks"]:
        if t["status"] != "not-started":
            continue
        if date.fromisoformat(t["dueDate"]) > today:
            continue
        if not t.get("notified"):
            due_tasks.append(
                {"taskId": t["id"], "title": t["title"], "ownerEmployeeId": t["ownerEmployeeId"]}
            )
            t["status"] = "in-progress"
            t["notified"] = True
            advanced.append(t["id"])
    return _ok({"planId": plan_id, "advanced": advanced, "dueTasks": due_tasks})


# ----- Jobs (UC4) -----
@app.route(route="jobs/search", methods=["POST"])
def jobs_search(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json() or {}
    except ValueError:
        return _problem(400, "Invalid JSON body")
    employee_id = body.get("employeeId")
    if not employee_id:
        return _problem(400, "employeeId is required")
    emp = _emp(employee_id)
    if not emp:
        return _problem(404, "Employee not found")
    interests = {i.lower() for i in (body.get("interests") or [])}
    location = (body.get("location") or "").lower()
    scored = []
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
    matches = [
        {"id": j["id"], "title": j["title"], "location": j["location"], "skills": j.get("skills", [])}
        for _, j in scored[:5]
    ]
    return _ok({"matches": matches})


# ----- Feedback (UC5) -----
@app.route(route="feedback/suggest-reviewers", methods=["POST"])
def suggest_reviewers(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json() or {}
    except ValueError:
        return _problem(400, "Invalid JSON body")
    subject_id = body.get("subjectEmployeeId")
    if not subject_id:
        return _problem(400, "subjectEmployeeId is required")
    subject = _emp(subject_id)
    if not subject:
        return _problem(404, "Subject employee not found")
    pool = []
    for e in _EMPLOYEES:
        if e["id"] == subject["id"]:
            continue
        reason = []
        if e.get("department") == subject.get("department"):
            reason.append("same department")
        if e.get("managerId") == subject.get("managerId"):
            reason.append("peer of subject")
        if e.get("id") == subject.get("managerId"):
            reason.append("subject's manager")
        if reason:
            pool.append({"id": e["id"], "email": e["email"], "reason": ", ".join(reason)})
    return _ok({"reviewers": pool[:3]})


@app.route(route="feedback/request", methods=["POST"])
def open_feedback(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json() or {}
    except ValueError:
        return _problem(400, "Invalid JSON body")
    subject_id = body.get("subjectEmployeeId")
    if not subject_id:
        return _problem(400, "subjectEmployeeId is required")
    rid = f"FBR-{uuid.uuid4().hex[:8].upper()}"
    _FEEDBACK_REQUESTS[rid] = {
        "id": rid,
        "subjectEmployeeId": subject_id,
        "reviewerIds": body.get("requestedReviewerIds") or [],
        "responses": [],
    }
    return _ok({"id": rid, "subjectEmployeeId": subject_id, "reviewerIds": _FEEDBACK_REQUESTS[rid]["reviewerIds"]})


@app.route(route="feedback/raw", methods=["POST"])
def feedback_raw(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json() or {}
    except ValueError:
        return _problem(400, "Invalid JSON body")
    rid = body.get("requestId")
    if not rid:
        return _problem(400, "requestId is required")
    rec = _FEEDBACK_REQUESTS.get(rid)
    if not rec:
        return _problem(404, "Feedback request not found")
    return _ok({"requestId": rid, "responses": rec.get("responses", [])})


# ----- Tickets (UC6) -----
@app.route(route="tickets/classify", methods=["POST"])
def classify_ticket(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json() or {}
    except ValueError:
        return _problem(400, "Invalid JSON body")
    description = body.get("description")
    if not description:
        return _problem(400, "description is required")
    return _ok(_classify_text(description))


# ---------------------------------------------------------------------------
# Foundry connected-agent proxy
# ---------------------------------------------------------------------------
#
# The Copilot Studio topic calls `invokeAgent` (one round-trip). Behind the
# scenes the Foundry Agents data plane needs at least three calls (create
# thread, run agent, poll, fetch messages), so we collapse them here.
#
# Production path: when `FOUNDRY_PROJECT_ENDPOINT` is set, we use the
# `azure-ai-projects` SDK with a managed identity token. Demo / offline path:
# when it is empty we return a deterministic local answer so the whole stack
# can run without an Azure subscription.
#
# Auth: the Function key is enforced by the platform on this route. The
# Function App itself uses a UAMI (`AZURE_CLIENT_ID`) with `Cognitive Services
# OpenAI User` on the Foundry account.


def _foundry_invoke(agent_name: str, user_input: str, context: dict) -> dict:
    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    if not endpoint:
        # Offline / demo answer — keeps the connector contract honest.
        return {
            "message": (
                f"(demo) {agent_name} would answer: {user_input}. "
                "Configure FOUNDRY_PROJECT_ENDPOINT to call the real agent."
            ),
            "citations": [],
        }

    # Lazy imports so the offline path doesn't pay the cold-start cost.
    from azure.ai.projects import AIProjectClient  # type: ignore[import-not-found]
    from azure.identity import DefaultAzureCredential  # type: ignore[import-not-found]

    project = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
    agents = project.agents
    agent = agents.get_agent(agent_name)  # by name, not id, requires that the agent exists.
    run = agents.create_thread_and_process_run(
        agent_id=agent.id,
        thread={"messages": [{"role": "user", "content": user_input}]},
    )
    if run.status != "completed":
        raise RuntimeError(f"Agent run failed: {run.status} {run.last_error}")
    msgs = list(agents.messages.list(thread_id=run.thread_id, order="desc"))
    last_assistant = next((m for m in msgs if m.role == "assistant"), None)
    if last_assistant is None:
        return {"message": "(no reply)", "citations": []}
    text = "".join(c.text.value for c in last_assistant.content if c.type == "text")
    citations = [
        {"title": ann.text, "url": getattr(ann, "url", "")}
        for c in last_assistant.content
        if c.type == "text"
        for ann in (getattr(c.text, "annotations", []) or [])
    ]
    return {"message": text, "citations": citations}


@app.route(route="agent/invoke", methods=["POST"])
def invoke_agent(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json() or {}
    except ValueError:
        return _problem(400, "Invalid JSON body")
    agent_name = body.get("agentName")
    user_input = body.get("input")
    if not (agent_name and user_input):
        return _problem(400, "agentName and input are required")
    context = body.get("context") or {}
    try:
        return _ok(_foundry_invoke(agent_name, user_input, context))
    except Exception as exc:  # noqa: BLE001 — proxy-style boundary
        return _problem(502, "Upstream agent failed", str(exc))


@app.route(route="tickets/create", methods=["POST"])
def create_ticket(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json() or {}
    except ValueError:
        return _problem(400, "Invalid JSON body")
    employee_id = body.get("employeeId")
    description = body.get("description")
    if not (employee_id and description):
        return _problem(400, "employeeId and description are required")
    emp = _emp(employee_id)
    if not emp:
        return _problem(404, "Employee not found")
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
    return _ok(record, status=201)
