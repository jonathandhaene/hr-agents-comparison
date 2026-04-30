"""Smoke tests for the Mixed-solution Functions backend.

We test the route handlers directly (no functions host) by invoking them as
plain callables and asserting the JSON shape, since `azure.functions` is a
runtime-provided module and may not be on dev machines.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2] / "shared-fixtures"
os.environ["HR_DATA_DIR"] = str(SHARED)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def test_classifier_flags_sensitive() -> None:
    # Defer import so HR_DATA_DIR is set first.
    try:
        import azure.functions  # noqa: F401
    except ImportError:
        import pytest  # type: ignore[import-not-found]

        pytest.skip("azure-functions not installed in this env")

    from function_app import classify_ticket  # type: ignore[import-not-found]

    class Req:
        def get_json(self) -> dict:
            return {"description": "I'd like to report harassment by my manager."}

    res = classify_ticket(Req())  # type: ignore[arg-type]
    body = json.loads(res.get_body())
    assert body["sensitivity"] == "critical"
    assert body["escalateImmediately"] is True
