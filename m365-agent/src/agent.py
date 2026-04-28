"""Root agent for the M365 Agents SDK HR Concierge.

This module wires up:
- The Agents SDK app + Bot Framework adapter
- A simple intent router that dispatches to per-UC skills
- A shared HRApiClient for the dedicated FastAPI backend

For local development, run via `uvicorn` against the included `app` (see Makefile).
For production, this same app is hosted in Azure Container Apps and registered
with Azure Bot Service per `infra/main.bicep`.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from microsoft.agents.builder import (  # type: ignore[import-not-found]
    Agent,
    ChannelAdapter,
    TurnContext,
)
from microsoft.agents.hosting.aiohttp import start_agent_process  # type: ignore[import-not-found]

from .skills import (
    uc1_policy_qa,
    uc2_time_off,
    uc3_onboarding,
    uc4_mobility,
    uc5_feedback,
    uc6_triage,
)
from .state import StateStore

log = logging.getLogger(__name__)

HR_API_BASE = os.environ["HR_API_BASE"]
COSMOS_CONN = os.environ.get("COSMOS_CONN")  # optional in local dev


class HRApiClient:
    """Thin async client over the dedicated FastAPI backend."""

    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def get(self, path: str, **kwargs: Any) -> Any:
        r = await self._client.get(path, **kwargs)
        r.raise_for_status()
        return r.json()

    async def post(self, path: str, json: dict | None = None, **kwargs: Any) -> Any:
        r = await self._client.post(path, json=json, **kwargs)
        r.raise_for_status()
        return r.json()


class HRConciergeAgent(Agent):
    """One agent, six skills."""

    def __init__(self) -> None:
        super().__init__()
        self.hr = HRApiClient(HR_API_BASE)
        self.state = StateStore(COSMOS_CONN)

    async def on_message(self, turn: TurnContext) -> None:  # type: ignore[override]
        text = (turn.activity.text or "").strip()
        intent = await self._route(text)
        log.info("Routed '%s' -> %s", text[:80], intent)

        handler = {
            "policy": uc1_policy_qa.handle,
            "timeoff": uc2_time_off.handle,
            "onboarding": uc3_onboarding.handle,
            "mobility": uc4_mobility.handle,
            "feedback": uc5_feedback.handle,
            "triage": uc6_triage.handle,
        }[intent]
        await handler(turn, self.hr, self.state)

    async def _route(self, text: str) -> str:
        """Lightweight keyword router.

        In production this is replaced by a routing LLM call; the Agents SDK
        also supports declarative intent maps. Kept simple here so the demo
        is deterministic.
        """
        t = text.lower()
        if any(k in t for k in ["policy", "handbook", "vacation days", "parental", "benefit", "401k"]):
            return "policy"
        if any(k in t for k in ["time off", "vacation", "pto", "leave"]):
            return "timeoff"
        if any(k in t for k in ["onboard", "new hire", "starting"]):
            return "onboarding"
        if any(k in t for k in ["job", "next role", "mobility", "career"]):
            return "mobility"
        if any(k in t for k in ["360", "feedback", "review"]):
            return "feedback"
        if any(k in t for k in ["report", "concern", "complaint", "harass", "payroll", "issue"]):
            return "triage"
        return "policy"  # safe default


def build_app() -> Any:
    adapter = ChannelAdapter()
    agent = HRConciergeAgent()
    return start_agent_process(agent=agent, adapter=adapter)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)
    build_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", "3978")))
