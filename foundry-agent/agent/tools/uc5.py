"""UC5 — 360° performance feedback."""
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ._client import hr_get, hr_post


async def open_feedback(
    cycle_id: Annotated[str, Field(description="Feedback cycle id, e.g. FB-H1-2026")],
    subject_employee_id: Annotated[str, Field(description="Employee to receive feedback")],
    reviewer_ids: Annotated[list[str], Field(description="3-5 reviewer employee ids")] ,
) -> dict:
    return await hr_post(
        "/feedback/request",
        json={"cycleId": cycle_id, "subjectEmployeeId": subject_employee_id, "requestedReviewerIds": reviewer_ids},
    )


async def summarize_feedback(
    request_id: Annotated[str, Field(description="Feedback request id, e.g. FBR-XXXXXXXX")],
) -> dict:
    """Returns raw aggregated answers; the agent's LLM produces the narrative summary."""
    return await hr_get(f"/feedback/{request_id}/summary")
