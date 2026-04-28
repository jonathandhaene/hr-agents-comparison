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
    assert r.json()["solution"] == "foundry"


def test_onboarding_creates_plan() -> None:
    r = client.post(
        "/onboarding/start",
        json={"newHireId": "E002", "startDate": "2026-05-05", "managerId": "E010", "buddyId": "B001"},
    )
    assert r.status_code == 200
    plan = r.json()
    assert plan["newHireId"] == "E002"
    assert len(plan["tasks"]) == 8
