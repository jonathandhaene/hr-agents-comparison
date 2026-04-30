"""Smoke tests for the Foundry agent's tools (against the dedicated backend)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2] / "shared-fixtures"
os.environ.setdefault("HR_DATA_DIR", str(SHARED))

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.json()["solution"] == "foundry-agent"


def test_onboarding_creates_plan() -> None:
    employees = client.get("/employees").json()
    new_hire = next(e for e in employees if e.get("managerId"))
    manager_id = new_hire["managerId"]
    r = client.post(
        "/onboarding/start",
        json={
            "newHireId": new_hire["id"],
            "startDate": "2026-05-05",
            "managerId": manager_id,
        },
    )
    assert r.status_code in (200, 201)
    plan = r.json()
    assert plan["newHireId"] == new_hire["id"]
    assert len(plan["tasks"]) >= 1
