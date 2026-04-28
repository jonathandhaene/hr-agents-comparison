"""Mixed-solution HR API on Azure Functions (Python v2 model).

A thin, anonymous-by-key HTTP API backed by the shared fixtures. Replaces
the FastAPI+Container App in the pure solutions because Functions Consumption
scales to zero and costs ~nothing at rest.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date
from pathlib import Path

import azure.functions as func  # type: ignore[import-not-found]

DATA_DIR = Path(os.environ.get("HR_DATA_DIR", Path(__file__).parent / "data"))
SOLUTION = "mixed"

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def _load(name: str) -> list[dict]:
    return json.loads((DATA_DIR / f"{name}.json").read_text())


def _ok(body: dict | list) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(body), mimetype="application/json")


@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS)
def health(_: func.HttpRequest) -> func.HttpResponse:
    return _ok({"status": "ok", "solution": SOLUTION})


@app.route(route="employees/{id}", methods=["GET"])
def get_employee(req: func.HttpRequest) -> func.HttpResponse:
    eid = req.route_params["id"]
    for e in _load("employees"):
        if e["id"] == eid or e.get("email") == eid:
            return _ok(e)
    return func.HttpResponse(status_code=404)


@app.route(route="leave/request", methods=["POST"])
def request_leave(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json()
    return _ok({"requestId": f"LR-{uuid.uuid4().hex[:8].upper()}", "status": "pending", **body})


@app.route(route="leave/{id}/approve", methods=["POST"])
def approve_leave(req: func.HttpRequest) -> func.HttpResponse:
    return _ok({"requestId": req.route_params["id"], "status": "approved"})


@app.route(route="leave/{id}/reject", methods=["POST"])
def reject_leave(req: func.HttpRequest) -> func.HttpResponse:
    return _ok({"requestId": req.route_params["id"], "status": "rejected"})


@app.route(route="onboarding/start", methods=["POST"])
def start_onboarding(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json()
    template = _load("onboarding_template")
    plan_id = f"OB-{uuid.uuid4().hex[:8].upper()}"
    return _ok({
        "planId": plan_id,
        "newHireName": body.get("newHireName"),
        "startDate": body.get("startDate"),
        "tasks": [{"id": t["id"], "title": t["title"], "owner": t["owner"], "status": "not-started"} for t in template],
    })


@app.route(route="onboarding/{id}/tick", methods=["POST"])
def tick_onboarding(req: func.HttpRequest) -> func.HttpResponse:
    return _ok({"planId": req.route_params["id"], "advanced": [], "dueReminders": []})


@app.route(route="jobs/search", methods=["POST"])
def jobs_search(req: func.HttpRequest) -> func.HttpResponse:
    return _ok(_load("jobs"))


@app.route(route="feedback/suggest-reviewers", methods=["POST"])
def suggest_reviewers(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json() or {}
    pool = [e["email"] for e in _load("employees") if e.get("email") and e.get("email") != body.get("subjectEmail")]
    return _ok({"reviewers": pool[:3]})


@app.route(route="feedback/request", methods=["POST"])
def open_feedback(req: func.HttpRequest) -> func.HttpResponse:
    return _ok({"requestId": f"FBR-{uuid.uuid4().hex[:8].upper()}"})


@app.route(route="feedback/raw", methods=["POST"])
def feedback_raw(req: func.HttpRequest) -> func.HttpResponse:
    return _ok({"requestId": req.get_json().get("requestId"), "responses": []})


@app.route(route="tickets/classify", methods=["POST"])
def classify_ticket(req: func.HttpRequest) -> func.HttpResponse:
    text = (req.get_json() or {}).get("description", "").lower()
    sensitive_words = ("harass", "discriminat", "retaliat", "abuse", "bully")
    sensitivity = "high" if any(w in text for w in sensitive_words) else "low"
    return _ok({"sensitivity": sensitivity, "category": "employee-relations" if sensitivity == "high" else "general", "summary": text[:120]})


@app.route(route="tickets/create", methods=["POST"])
def create_ticket(req: func.HttpRequest) -> func.HttpResponse:
    return _ok({"id": f"INC-{uuid.uuid4().hex[:6].upper()}", "createdAt": date.today().isoformat()})
