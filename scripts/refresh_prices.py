"""Refresh a static snapshot of Azure retail prices used by the cost calculator.

Writes ``docs/calculator/prices.json`` with gpt-4o GlobalStandard input/output
token rates per region across the ``Azure OpenAI`` and ``Foundry Models`` service
names. The calculator UI reads this file directly so the page works on GitHub
Pages without hitting prices.azure.com from the browser (the API does not
expose CORS headers).
"""

from __future__ import annotations

import datetime
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REGIONS = [
    "eastus", "eastus2", "westus", "westus2", "westus3",
    "centralus", "southcentralus", "northcentralus",
    "canadaeast", "canadacentral",
    "northeurope", "westeurope",
    "swedencentral", "switzerlandnorth", "francecentral",
    "germanywestcentral", "norwayeast", "polandcentral",
    "uksouth", "ukwest",
    "uaenorth",
    "southeastasia", "eastasia", "japaneast", "japanwest",
    "australiaeast", "koreacentral", "centralindia",
    "brazilsouth", "southafricanorth",
]

SERVICES = ["Azure OpenAI", "Foundry Models"]
API = "https://prices.azure.com/api/retail/prices"
API_VERSION = "2023-01-01-preview"


def fetch(filter_expr: str) -> list[dict]:
    items: list[dict] = []
    url = f"{API}?api-version={API_VERSION}&$filter={urllib.parse.quote(filter_expr)}"
    while url:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read())
        items.extend(data.get("Items", []))
        url = data.get("NextPageLink") or None
    return items


def unit_factor(uom: str) -> float:
    """Return multiplier to convert an item's retailPrice into $/1K tokens."""
    if not uom:
        return 1.0
    s = uom.lower()
    if re.search(r"(^|\s)1m\b|1,000,000|million", s):
        return 1 / 1000  # priced per 1M tokens
    return 1.0  # assume per-1K


_BAD = ("mini", "rt-", "realtime", "aud", "audio", "transcribe", "ft model",
        "batch", "cchd", "cached", "grader", "image")


def is_gpt4o_text(name: str) -> bool:
    n = name.lower()
    if "gpt-4o" not in n:
        return False
    return not any(b in n for b in _BAD)


def pick(items: list[dict], region: str) -> dict | None:
    # Prefer the canonical gpt-4o-0806 GlobalStandard text meters.
    cand = [i for i in items
            if i.get("armRegionName") == region
            and (i.get("type") or i.get("priceType")) == "Consumption"
            and is_gpt4o_text(i.get("meterName", ""))]
    glbl = [i for i in cand if re.search(r"\b(glbl|global)\b", i["meterName"], re.I)]
    pool = glbl or cand
    inp = next((i for i in pool if re.search(r"\binp\b|input", i["meterName"], re.I)), None)
    out = next((i for i in pool if re.search(r"\boutp\b|output", i["meterName"], re.I)), None)
    if not (inp and out):
        return None
    return {
        "input_per_1k": round(inp["retailPrice"] * unit_factor(inp["unitOfMeasure"]), 6),
        "output_per_1k": round(out["retailPrice"] * unit_factor(out["unitOfMeasure"]), 6),
        "meter_input": inp["meterName"],
        "meter_output": out["meterName"],
        "service": inp["serviceName"],
    }


def main() -> int:
    all_items: list[dict] = []
    for svc in SERVICES:
        try:
            all_items.extend(fetch(f"serviceName eq '{svc}' and priceType eq 'Consumption'"))
        except Exception as exc:  # noqa: BLE001
            print(f"warn: failed to fetch {svc}: {exc}", file=sys.stderr)

    snapshot = {
        "generated": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "currency": "USD",
        "model": "gpt-4o GlobalStandard",
        "regions": {},
    }
    for region in REGIONS:
        chosen = pick(all_items, region)
        if chosen:
            snapshot["regions"][region] = chosen

    out = Path("docs/calculator/prices.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out} with {len(snapshot['regions'])} regions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
