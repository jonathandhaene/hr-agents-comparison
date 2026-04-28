"""UC4 — Internal mobility."""
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ._client import hr_post


async def match_internal_jobs(
    employee_id: Annotated[str, Field(description="Employee id requesting mobility advice")],
    interests: Annotated[list[str], Field(description="Stated career interests")] ,
    location: Annotated[str | None, Field(description="Preferred location, optional")] = None,
) -> list[dict]:
    """Return the top internal openings for an employee, ranked by skill+interest fit."""
    return await hr_post(
        "/jobs/search",
        json={"employeeId": employee_id, "interests": interests, "location": location},
    )
