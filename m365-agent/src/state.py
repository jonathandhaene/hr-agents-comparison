"""Conversation state + workflow checkpoint store.

Backed by Cosmos DB in production; falls back to an in-memory dict for local
dev when COSMOS_CONN is not set.

Stores two kinds of records:
1. ``conversation_refs`` — needed to send proactive messages to managers/IT/buddies
   when an asynchronous event arrives (UC2 approval, UC3 task nudges).
2. ``workflow_state`` — long-running orchestration checkpoints for UC3.
"""
from __future__ import annotations

import json
from typing import Any


class StateStore:
    def __init__(self, cosmos_conn: str | None) -> None:
        self._mem: dict[str, dict] = {}
        self._cosmos_conn = cosmos_conn
        self._container = None
        if cosmos_conn:
            from azure.cosmos.aio import CosmosClient  # type: ignore[import-not-found]

            self._client = CosmosClient.from_connection_string(cosmos_conn)
            self._container = self._client.get_database_client("hr").get_container_client("state")

    async def put_conversation_ref(self, employee_id: str, conv_ref: dict[str, Any]) -> None:
        await self._put(f"conv:{employee_id}", conv_ref)

    async def get_conversation_ref(self, employee_id: str) -> dict[str, Any] | None:
        return await self._get(f"conv:{employee_id}")

    async def put_workflow(self, workflow_id: str, state: dict[str, Any]) -> None:
        await self._put(f"wf:{workflow_id}", state)

    async def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        return await self._get(f"wf:{workflow_id}")

    async def _put(self, key: str, value: dict[str, Any]) -> None:
        if self._container:
            await self._container.upsert_item({"id": key, "data": json.dumps(value)})
        else:
            self._mem[key] = value

    async def _get(self, key: str) -> dict[str, Any] | None:
        if self._container:
            try:
                item = await self._container.read_item(item=key, partition_key=key)
                return json.loads(item["data"])
            except Exception:  # pragma: no cover - missing key
                return None
        return self._mem.get(key)
