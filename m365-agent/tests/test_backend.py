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
    assert r.status_code == 200
    rid = r.json()["id"]

    r2 = client.post(f"/leave/{rid}/approve")
    assert r2.status_code == 200
    assert r2.json()["status"] == "approved"


def test_ticket_classification_sensitive() -> None:
    r = client.post("/tickets/classify", json={"description": "I want to report harassment by my manager"})
    assert r.json()["sensitivity"] == "critical"
    assert r.json()["autoAnswer"] is False


def test_jobs_match() -> None:
    r = client.post("/jobs/search", json={"employeeId": "E001", "interests": ["product management"]})
    assert r.status_code == 200
    assert len(r.json()) >= 1
