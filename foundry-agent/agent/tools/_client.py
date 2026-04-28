"""Shared HR API client for Foundry tools."""
from __future__ import annotations

import os
from typing import Any

import httpx

HR_API_BASE = os.environ.get("HR_API_BASE", "http://localhost:8000")


async def hr_get(path: str, **kwargs: Any) -> Any:
    async with httpx.AsyncClient(base_url=HR_API_BASE, timeout=30.0) as c:
        r = await c.get(path, **kwargs)
        r.raise_for_status()
        return r.json()


async def hr_post(path: str, json: dict | None = None, **kwargs: Any) -> Any:
    async with httpx.AsyncClient(base_url=HR_API_BASE, timeout=30.0) as c:
        r = await c.post(path, json=json, **kwargs)
        r.raise_for_status()
        return r.json()
