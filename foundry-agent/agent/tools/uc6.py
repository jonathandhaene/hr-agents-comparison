"""UC6 — Ticket triage & escalation."""
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ._client import hr_post


async def classify_ticket(
    description: Annotated[str, Field(description="Free-text employee message")],
) -> dict:
    """Classify a ticket. Returns sensitivity, autoAnswer flag, and escalateImmediately.

    Sensitive categories (harassment, employee relations, immigration, leave)
    return autoAnswer=False and escalateImmediately=True for harassment.
    The agent MUST NOT auto-answer any of these.
    """
    return await hr_post("/tickets/classify", json={"description": description})


async def create_ticket(
    employee_id: Annotated[str, Field(description="Reporting employee's id")],
    description: Annotated[str, Field(description="Free-text employee message")],
) -> dict:
    return await hr_post("/tickets/create", json={"employeeId": employee_id, "description": description})


async def escalate_ticket(
    ticket_id: Annotated[str, Field(description="Ticket id, e.g. INC-1001")],
) -> dict:
    return await hr_post(f"/tickets/{ticket_id}/escalate")
