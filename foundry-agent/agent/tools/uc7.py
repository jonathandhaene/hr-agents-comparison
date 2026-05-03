"""UC7 — Calibrated performance narrative generation.

Uses a fine-tuned model deployment (FOUNDRY_NARRATIVE_DEPLOYMENT) registered
in the Foundry project. Falls back to the primary model when the env var is not
set so the demo runs without a fine-tuned checkpoint.

The tool:
1. Fetches the employee profile + UC5 360 summary from the backend.
2. Fetches grade-level competency descriptors from the backend.
3. Calls the fine-tuned deployment (or primary) to draft a narrative.
4. Returns the draft text and a draft_id so the agent can ask the manager
   for edits and then call submit_performance_narrative.
"""
from __future__ import annotations

import os
from typing import Annotated

from pydantic import Field

from ._client import hr_get, hr_post


async def draft_performance_narrative(
    employee_id: Annotated[str, Field(description="The employee id whose narrative is being drafted (e.g. E001)")],
    cycle_id: Annotated[str, Field(description="Review cycle id, e.g. H1-2026")],
    manager_notes: Annotated[str, Field(description="Manager's raw bullet notes about the employee's performance")],
    feedback_request_id: Annotated[
        str | None, Field(description="UC5 feedback request id (e.g. FBR-XXXXXXXX) to include 360 context")
    ] = None,
) -> dict:
    """Draft a grade-level-calibrated performance narrative.

    Calls the backend /narratives/draft endpoint, which:
    - Retrieves the employee profile and competency framework for their grade.
    - Optionally pulls in the aggregated 360 feedback (if feedback_request_id given).
    - Invokes the fine-tuned Foundry model deployment to produce a calibrated draft.

    Returns:
        draft_id: opaque id used to submit the approved text.
        draft: the narrative text for the manager to review and edit.
        grade: the employee's current grade (e.g. L5).
    """
    body: dict = {
        "employeeId": employee_id,
        "cycleId": cycle_id,
        "managerNotes": manager_notes,
        "narrativeDeployment": os.environ.get("FOUNDRY_NARRATIVE_DEPLOYMENT", ""),
    }
    if feedback_request_id:
        body["feedbackRequestId"] = feedback_request_id
    return await hr_post("/narratives/draft", json=body)


async def submit_performance_narrative(
    draft_id: Annotated[str, Field(description="Draft id returned by draft_performance_narrative")],
    approved_text: Annotated[str, Field(description="The manager-approved final narrative text")],
) -> dict:
    """Submit the approved narrative to the HR review record.

    Writes the narrative to the review system and sends an HR Partner copy for
    the calibration session. ALWAYS confirm the final text with the manager
    before calling this tool.
    """
    return await hr_post("/narratives/submit", json={"draftId": draft_id, "approvedText": approved_text})
