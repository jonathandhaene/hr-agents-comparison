"""UC2 — Time-off request with manager approval.

Flow:
1. Employee sends a natural-language request.
2. Skill extracts dates + type, checks balance, posts /leave/request to backend.
3. Skill sends an Adaptive Card with [Approve] [Reject] buttons proactively to
   the manager (using the manager's stored conversation reference).
4. Manager click triggers a follow-up turn that calls /leave/{id}/approve or /reject.
5. Employee gets a proactive confirmation.
"""
from __future__ import annotations

import json
import re
from datetime import date

from microsoft.agents.builder import CardFactory, MessageFactory  # type: ignore[import-not-found]


def _extract_dates(text: str) -> tuple[date, date] | None:
    # Very simple parser for the demo; production code would use Recognizers-Text.
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:to|until|-)\s*(\d{4}-\d{2}-\d{2})", text)
    if m:
        return date.fromisoformat(m.group(1)), date.fromisoformat(m.group(2))
    return None


def _approval_card(req: dict, employee_name: str) -> dict:
    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.5",
        "body": [
            {"type": "TextBlock", "size": "Medium", "weight": "Bolder", "text": "Time-off approval request"},
            {"type": "TextBlock", "wrap": True, "text": f"**{employee_name}** requests **{req['days']} day(s)** of {req['type']} from **{req['startDate']}** to **{req['endDate']}**."},
            {"type": "TextBlock", "wrap": True, "isSubtle": True, "text": req.get("note") or ""},
        ],
        "actions": [
            {"type": "Action.Submit", "title": "Approve", "data": {"action": "leave.approve", "id": req["id"]}},
            {"type": "Action.Submit", "title": "Reject", "data": {"action": "leave.reject", "id": req["id"]}},
            {"type": "Action.Submit", "title": "Need more info", "data": {"action": "leave.info", "id": req["id"]}},
        ],
    }


async def handle(turn, hr, state) -> None:
    activity = turn.activity
    # Manager click handling
    if activity.value and isinstance(activity.value, dict) and activity.value.get("action", "").startswith("leave."):
        await _handle_decision(turn, hr, state, activity.value)
        return

    # Employee-facing request
    employee_id = _resolve_employee_id(turn)
    dates = _extract_dates(activity.text or "")
    if not dates:
        await turn.send_activity("Sure — which dates? For example: `2026-06-10 to 2026-06-14`.")
        return

    start, end = dates
    bal = await hr.get(f"/leave/balance/{employee_id}")
    days = (end - start).days + 1
    if bal["vacationDays"] < days:
        await turn.send_activity(f"You have {bal['vacationDays']} vacation days available — not enough for {days} days. Contact HR if you'd like to discuss options.")
        return

    req = await hr.post(
        "/leave/request",
        json={"employeeId": employee_id, "startDate": str(start), "endDate": str(end), "type": "vacation"},
    )

    employee = await hr.get(f"/employees/{employee_id}")
    manager_ref = await state.get_conversation_ref(req["managerId"])
    if manager_ref:
        # Proactive notification to manager
        from microsoft.agents.builder import TurnContext  # type: ignore[import-not-found]
        async def _send(ctx):
            card = CardFactory.adaptive_card(_approval_card(req, employee["displayName"]))
            await ctx.send_activity(MessageFactory.attachment(card))
        await TurnContext.send_proactive(turn.adapter, manager_ref, _send)

    # Save the employee's conv ref for the round-trip back
    await state.put_conversation_ref(employee_id, turn.activity.get_conversation_reference())
    await state.put_workflow(f"leave:{req['id']}", {"employeeRef": turn.activity.get_conversation_reference()})

    await turn.send_activity(f"Sent. I'll let you know when {employee['displayName']}'s manager responds. (Request {req['id']})")


async def _handle_decision(turn, hr, state, value: dict) -> None:
    action = value["action"]
    req_id = value["id"]
    if action == "leave.approve":
        req = await hr.post(f"/leave/{req_id}/approve")
        msg = "✅ Approved."
        notify = f"Your manager approved your time-off request {req_id}."
    elif action == "leave.reject":
        req = await hr.post(f"/leave/{req_id}/reject")
        msg = "Rejected."
        notify = f"Your manager declined your time-off request {req_id}."
    else:
        await turn.send_activity("Please reply with the question you'd like to ask the employee, and I'll forward it.")
        return

    await turn.send_activity(msg)

    wf = await state.get_workflow(f"leave:{req_id}")
    if wf and wf.get("employeeRef"):
        from microsoft.agents.builder import TurnContext  # type: ignore[import-not-found]
        async def _send(ctx):
            await ctx.send_activity(notify)
        await TurnContext.send_proactive(turn.adapter, wf["employeeRef"], _send)


def _resolve_employee_id(turn) -> str:
    """Map the M365 user to an HR employee id.

    For the demo we use a static mapping by AAD object id; production code
    looks this up from Microsoft Graph.
    """
    return turn.activity.from_property.aad_object_id or "E001"
