"""UC2 — Time-off request with manager approval."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from ._client import hr_get, hr_post


async def request_time_off(
    employee_id: Annotated[str, Field(description="Employee id (e.g. E001)")],
    start_date: Annotated[str, Field(description="ISO date YYYY-MM-DD")],
    end_date: Annotated[str, Field(description="ISO date YYYY-MM-DD")],
    leave_type: Annotated[Literal["vacation", "sick", "personal"], Field(description="Type of leave")] = "vacation",
    note: Annotated[str | None, Field(description="Optional note for the manager")] = None,
) -> dict:
    """Submit a time-off request. Returns the request id and pending status.

    The agent should ALWAYS confirm dates and balance with the user before calling.
    The manager is notified out-of-band via M365 Copilot's notification surface
    once the agent is published.
    """
    bal = await hr_get(f"/leave/balance/{employee_id}")
    return await hr_post(
        "/leave/request",
        json={"employeeId": employee_id, "startDate": start_date, "endDate": end_date, "type": leave_type, "note": note},
    ) | {"balanceBefore": bal}


async def approve_or_reject_time_off(
    request_id: Annotated[str, Field(description="Leave request id, e.g. LR-XXXXXXXX")],
    decision: Annotated[Literal["approve", "reject"], Field(description="Manager decision")],
    decision_note: Annotated[str | None, Field(description="Optional note shared with the employee")] = None,
) -> dict:
    """Manager-side decision tool. Updates the request and decrements balances on approval."""
    path = f"/leave/{request_id}/{'approve' if decision == 'approve' else 'reject'}"
    return await hr_post(path, json={"decisionNote": decision_note})
