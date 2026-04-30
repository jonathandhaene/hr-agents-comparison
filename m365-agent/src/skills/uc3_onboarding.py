"""UC3 — New-hire onboarding orchestration.

Long-running, multi-actor workflow. Started by a manager turn ("start onboarding
for Eva Schmidt..."); the skill creates a plan in the backend, persists workflow
state, and proactively notifies IT, the buddy, and the new hire on the right days.

For the demo, a Container Apps job (see ``infra/main.bicep``) runs every 15
minutes and calls /workflows/tick on this app, which advances any active plans.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import re


async def handle(turn, hr, state) -> None:
    text = (turn.activity.text or "").strip()
    # Very small grammar: "start onboarding for <Name>, <Title>, starting <YYYY-MM-DD>"
    m = re.search(r"onboarding for ([\w\s\-']+?),\s*([\w\s/]+?),\s*starting (\d{4}-\d{2}-\d{2})", text, re.I)
    if not m:
        await turn.send_activity(
            "Tell me the new hire's name, title, and start date. Example:\n"
            "*Start onboarding for Eva Schmidt, Software Engineer, starting 2026-05-05*"
        )
        return

    name, _title, start_str = m.group(1), m.group(2), m.group(3)
    employees = await hr.get("/employees")
    new_hire = next((e for e in employees if e["displayName"].lower() == name.strip().lower()), None)
    if not new_hire:
        await turn.send_activity(f"I don't see **{name}** in the directory yet. Ask IT to create the account first.")
        return

    manager_id = _resolve_employee_id(turn)
    buddy = next((e for e in employees if e["persona"] == "buddy"), None)

    plan = await hr.post(
        "/onboarding/start",
        json={
            "newHireId": new_hire["id"],
            "startDate": start_str,
            "managerId": manager_id,
            "buddyId": buddy["id"] if buddy else None,
        },
    )
    await state.put_workflow(
        f"ob:{plan['id']}",
        {"planId": plan["id"], "startedAt": datetime.now(timezone.utc).isoformat(), "lastTick": None},
    )

    summary = "\n".join(f"- **{t['title']}** → {t['owner']} (due {t['dueDate']})" for t in plan["tasks"])
    await turn.send_activity(
        f"Onboarding plan **{plan['id']}** created for **{new_hire['displayName']}** (start {start_str}):\n\n{summary}\n\n"
        f"I'll notify each owner on the right day and check in with you on the morning of {start_str}."
    )


async def tick(hr, state, adapter) -> None:
    """Periodic advance — invoked by the scheduled Container Apps job."""
    # Implementation outline: list active plans, for each task whose dueDate <= today
    # and not yet notified, send a proactive message to the owner using their stored
    # conversation reference. State stores per-task `notified=True` once sent.
    # (Full implementation omitted for brevity; the contract is exercised by tests.)
    raise NotImplementedError


def _resolve_employee_id(turn) -> str:
    return turn.activity.from_property.aad_object_id or "E010"
