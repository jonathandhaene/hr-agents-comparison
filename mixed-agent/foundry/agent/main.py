"""Tiny Foundry connected agent — UC4 (mobility), UC5 summary, and UC7 (performance narrative).

Invoked by the Copilot Studio topic via the Foundry-agent connector.
"""
from __future__ import annotations

import os
from typing import Annotated

import httpx
from agent_framework import ChatAgent  # type: ignore[import-not-found]
from agent_framework.azure import AzureOpenAIChatClient  # type: ignore[import-not-found]
from azure.identity.aio import DefaultAzureCredential  # type: ignore[import-not-found]
from pydantic import Field

HR_API_BASE = os.environ["HR_API_BASE"]  # the Functions app URL, e.g. https://hr-api.azurewebsites.net
HR_API_KEY = os.environ.get("HR_API_KEY", "")
# FOUNDRY_MODEL controls which model deployment to use. Defaults to gpt-4o.
# For EU-sovereignty deployments, set FOUNDRY_MODEL=mistral-large and deploy
# with enableMistral=true in infra/main.bicep.
MODEL = os.environ.get("FOUNDRY_MODEL", "gpt-4o")

INSTRUCTIONS = """You are Zava HR's Mobility, Feedback & Narrative Advisor.
- For mobility questions, call match_internal_jobs and return a 90-word first-person pitch
  for the top role plus a one-line "why this fits" for the runner-up.
- For feedback summary questions, call summarize_feedback_raw and produce a candid 5-bullet
  summary: strengths, blind spots, action items, theme, anonymity-safe quote.
- For performance narrative requests, call draft_performance_narrative to get a grade-calibrated
  draft from the fine-tuned model. Present the draft to the manager, incorporate any edits they
  request, and only call submit_performance_narrative when the manager explicitly approves.
Always be concise."""


async def _hr_post(path: str, body: dict) -> dict:
    headers = {"x-functions-key": HR_API_KEY} if HR_API_KEY else {}
    async with httpx.AsyncClient(base_url=HR_API_BASE, timeout=30.0, headers=headers) as c:
        r = await c.post(path, json=body)
        r.raise_for_status()
        return r.json()


async def match_internal_jobs(
    employee_email: Annotated[str, Field(description="The employee's work email.")],
    interests: Annotated[str, Field(description="Free-text career interests.")],
) -> list[dict]:
    """Return ranked internal openings for this employee."""
    return await _hr_post("/api/jobs/search", {"employeeEmail": employee_email, "interests": interests})


async def summarize_feedback_raw(
    request_id: Annotated[str, Field(description="Feedback request id, e.g. FBR-XXXXXXXX.")],
) -> dict:
    """Return the aggregated raw responses for a 360 feedback request."""
    return await _hr_post("/api/feedback/raw", {"requestId": request_id})


async def draft_performance_narrative(
    employee_id: Annotated[str, Field(description="Employee id whose narrative is being drafted (e.g. E001).")],
    cycle_id: Annotated[str, Field(description="Review cycle id, e.g. H1-2026.")],
    manager_notes: Annotated[str, Field(description="Manager's bullet notes on the employee's performance.")],
    feedback_request_id: Annotated[
        str | None, Field(description="Optional UC5 feedback request id (e.g. FBR-XXXXXXXX) for 360 context.")
    ] = None,
) -> dict:
    """Draft a grade-level-calibrated performance narrative using the fine-tuned model.

    Returns draftId, draft text, and employee grade so the Copilot Studio topic
    can present the draft to the manager and ask for approval or edits.
    """
    body: dict = {"employeeId": employee_id, "cycleId": cycle_id, "managerNotes": manager_notes}
    if feedback_request_id:
        body["feedbackRequestId"] = feedback_request_id
    return await _hr_post("/api/narratives/draft", body)


async def submit_performance_narrative(
    draft_id: Annotated[str, Field(description="Draft id returned by draft_performance_narrative.")],
    approved_text: Annotated[str, Field(description="The manager-approved final narrative text.")],
) -> dict:
    """Submit the approved narrative to the HR review record.

    ALWAYS get explicit manager approval before calling this tool.
    """
    return await _hr_post("/api/narratives/submit", {"draftId": draft_id, "approvedText": approved_text})


def build_agent() -> ChatAgent:
    cred = DefaultAzureCredential()
    client = AzureOpenAIChatClient(
        endpoint=os.environ["FOUNDRY_ENDPOINT"],
        deployment=os.environ.get("FOUNDRY_DEPLOYMENT", MODEL),
        credential=cred,
    )
    return ChatAgent(
        chat_client=client,
        name="ZavaHRMobilityAdvisor",
        instructions=INSTRUCTIONS,
        tools=[match_internal_jobs, summarize_feedback_raw, draft_performance_narrative, submit_performance_narrative],
    )


if __name__ == "__main__":  # pragma: no cover
    import asyncio

    async def _repl() -> None:
        agent = build_agent()
        while (q := input("you> ").strip()) not in {"exit", "quit"}:
            async for chunk in agent.run_stream(q):
                print(chunk.text, end="", flush=True)
            print()

    asyncio.run(_repl())
