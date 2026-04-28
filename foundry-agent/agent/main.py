"""Foundry hosted HR agent — built with the Microsoft Agent Framework (Python).

Connects to the dedicated FastAPI backend via tools, uses Foundry File Search
for UC1, and is published to M365 Copilot natively via the Foundry project's
"Publish to Copilot" feature (see project/agent.yaml).
"""
from __future__ import annotations

import asyncio
import logging
import os

from agent_framework import ChatAgent  # type: ignore[import-not-found]
from agent_framework.azure import AzureOpenAIChatClient  # type: ignore[import-not-found]
from azure.ai.agents.aio import AgentsClient  # type: ignore[import-not-found]
from azure.identity.aio import DefaultAzureCredential  # type: ignore[import-not-found]

from .tools import uc1, uc2, uc3, uc4, uc5, uc6

log = logging.getLogger(__name__)

PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
MODEL = os.environ.get("FOUNDRY_MODEL", "gpt-4o")

INSTRUCTIONS = """You are Contoso HR Concierge, a Foundry-hosted agent.

Personas you serve: employees, managers, HR partners, IT, buddies, and new hires.

Tools you have:
- search_policies      → UC1 grounded answers from the policy corpus (Foundry File Search)
- request_time_off / approve_or_reject_time_off → UC2 with manager HITL
- start_onboarding / advance_onboarding → UC3 long-running plan
- match_internal_jobs  → UC4 role suggestions
- open_feedback / summarize_feedback → UC5 360° loops
- classify_ticket / create_ticket / escalate_ticket → UC6 triage; ALWAYS escalate
  sensitive cases (harassment, employee relations, immigration, leave) to HR Partners
  without auto-answering.

Be concise. Cite sources for policy answers. Confirm before submitting state-changing
actions like time-off requests or escalations.
"""


def build_agent() -> ChatAgent:
    cred = DefaultAzureCredential()
    client = AzureOpenAIChatClient(
        endpoint=os.environ["AOAI_ENDPOINT"],
        deployment=os.environ.get("AOAI_DEPLOYMENT", "gpt-4o"),
        credential=cred,
    )
    return ChatAgent(
        chat_client=client,
        name="ContosoHRConcierge",
        instructions=INSTRUCTIONS,
        tools=[
            uc1.search_policies,
            uc2.request_time_off,
            uc2.approve_or_reject_time_off,
            uc3.start_onboarding,
            uc3.advance_onboarding,
            uc4.match_internal_jobs,
            uc5.open_feedback,
            uc5.summarize_feedback,
            uc6.classify_ticket,
            uc6.create_ticket,
            uc6.escalate_ticket,
        ],
    )


async def main() -> None:
    """Run the agent locally for development.

    In production, the agent is hosted by the Foundry project (see
    `project/agent.yaml` and `infra/main.bicep`); this entry point is only
    used by `make dev` for a chat REPL against the same code.
    """
    logging.basicConfig(level=logging.INFO)
    agent = build_agent()
    print("HR Concierge ready. Type 'exit' to quit.")
    while True:
        text = input("you> ").strip()
        if text in {"exit", "quit"}:
            return
        async for chunk in agent.run_stream(text):
            print(chunk.text, end="", flush=True)
        print()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
