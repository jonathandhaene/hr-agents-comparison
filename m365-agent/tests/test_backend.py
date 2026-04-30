"""Smoke tests for the M365 Agents SDK backend."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow tests to run before fixtures are copied into backend/data
SHARED = Path(__file__).resolve().parents[2] / "shared-fixtures"
os.environ.setdefault("HR_DATA_DIR", str(SHARED))

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["solution"] == "m365-agent"


def test_employees_listed() -> None:
    r = client.get("/employees")
    assert r.status_code == 200
    assert any(e["id"] == "E001" for e in r.json())


def test_leave_lifecycle() -> None:
    r = client.post(
        "/leave/request",
        json={"employeeId": "E001", "startDate": "2026-06-10", "endDate": "2026-06-14"},
    )
    assert r.status_code in (200, 201)
    body = r.json()
    rid = body["id"]
    assert body["days"] == 5
    assert body["managerId"]

    r2 = client.post(f"/leave/{rid}/approve", json={"decisionNote": "approved by manager"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "approved"

    # Idempotent re-approve.
    r3 = client.post(f"/leave/{rid}/approve")
    assert r3.status_code == 200
    assert r3.json()["status"] == "approved"


def test_leave_idempotency_key() -> None:
    headers = {"Idempotency-Key": "test-key-1"}
    payload = {"employeeId": "E001", "startDate": "2026-07-01", "endDate": "2026-07-02"}
    r1 = client.post("/leave/request", json=payload, headers=headers)
    r2 = client.post("/leave/request", json=payload, headers=headers)
    assert r1.json()["id"] == r2.json()["id"]


def test_ticket_classification_sensitive() -> None:
    r = client.post("/tickets/classify", json={"description": "I want to report harassment by my manager"})
    assert r.json()["sensitivity"] == "critical"
    assert r.json()["autoAnswer"] is False
    assert r.json()["escalateImmediately"] is True


def test_jobs_match() -> None:
    r = client.post("/jobs/search", json={"employeeId": "E001", "interests": ["product management"]})
    assert r.status_code == 200
    assert isinstance(r.json()["matches"], list)


def test_employees_by_name() -> None:
    sample = client.get("/employees").json()[0]
    needle = sample["displayName"].split()[0]
    r = client.get("/employees/byName", params={"name": needle})
    assert r.status_code == 200
    assert any(m["id"] == sample["id"] for m in r.json()["matches"])
