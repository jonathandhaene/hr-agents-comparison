"""Tiny Foundry connected agent — only UC4 (mobility) and UC5 summary.

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

INSTRUCTIONS = """You are Contoso HR's Mobility & Feedback Advisor.
- For mobility questions, call match_internal_jobs and return a 90-word first-person pitch
  for the top role plus a one-line "why this fits" for the runner-up.
- For feedback summary questions, call summarize_feedback_raw and produce a candid 5-bullet
  summary: strengths, blind spots, action items, theme, anonymity-safe quote.
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


def build_agent() -> ChatAgent:
    cred = DefaultAzureCredential()
    client = AzureOpenAIChatClient(
        endpoint=os.environ["AOAI_ENDPOINT"],
        deployment=os.environ.get("AOAI_DEPLOYMENT", "gpt-4o"),
        credential=cred,
    )
    return ChatAgent(
        chat_client=client,
        name="ContosoHRMobilityAdvisor",
        instructions=INSTRUCTIONS,
        tools=[match_internal_jobs, summarize_feedback_raw],
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
