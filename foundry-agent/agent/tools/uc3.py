"""UC3 — Onboarding orchestration."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from ._client import hr_get, hr_post


async def start_onboarding(
    new_hire_id: Annotated[str, Field(description="The new hire's employee id")],
    start_date: Annotated[str, Field(description="ISO date when they start")],
    manager_id: Annotated[str, Field(description="Manager's employee id")],
    buddy_id: Annotated[str | None, Field(description="Optional buddy's employee id")] = None,
) -> dict:
    """Create a new onboarding plan with eight standard tasks (T01-T08).

    The plan persists in the backend's state. UC3's long-running progress is
    advanced by `advance_onboarding` (called by a Foundry scheduled job — see
    `infra/main.bicep` for the Logic App that pings it every 15 minutes).
    """
    return await hr_post(
        "/onboarding/start",
        json={"newHireId": new_hire_id, "startDate": start_date, "managerId": manager_id, "buddyId": buddy_id},
    )


async def advance_onboarding(
    plan_id: Annotated[str, Field(description="Onboarding plan id, e.g. OB-XXXXXXXX")],
    task_id: Annotated[str, Field(description="Task id within the plan, e.g. T03")],
    status: Annotated[Literal["not-started", "in-progress", "done", "overdue"], Field(description="New task status")],
) -> dict:
    return await hr_post(f"/onboarding/{plan_id}/task/{task_id}/status", json={"status": status})


async def get_onboarding(
    plan_id: Annotated[str, Field(description="Onboarding plan id")],
) -> dict:
    return await hr_get(f"/onboarding/{plan_id}")
