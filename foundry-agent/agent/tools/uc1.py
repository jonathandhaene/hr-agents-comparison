"""UC1 — Policy & benefits Q&A.

Uses Foundry File Search (an *agent-side* tool registered on the hosted agent
in `project/agent.yaml`) for retrieval. This module exposes a thin wrapper so
local dev can also run UC1 against the FastAPI fallback.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import Field

from ._client import hr_get


async def search_policies(
    question: Annotated[str, Field(description="The employee's policy question.")],
) -> dict:
    """Look up Contoso HR policy text for grounding.

    In production, the hosted agent's File Search tool answers UC1 directly
    from the indexed policies (see `search/index_definition.json`). This
    function is a fallback used during local dev when File Search isn't
    configured; it returns raw policy markdown for the model to ground on.
    """
    policies = await hr_get("/policies")
    chunks = []
    for p in policies:
        doc = await hr_get(f"/policies/{p['name']}")
        chunks.append({"policy": p["name"], "content": doc["content"]})
    return {"question": question, "policies": chunks}
