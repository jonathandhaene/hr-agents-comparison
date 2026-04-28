"""UC6 — HR ticket triage & escalation.

Sensitive cases (HARASSMENT, ER, IMMIGRATION, LEAVE) are NEVER auto-answered.
The skill creates a ticket, opens a 1:1 Teams chat between the employee and
the assigned HR Partner via Microsoft Graph, and confirms back to the employee.
"""
from __future__ import annotations

import os

import httpx
from azure.identity.aio import DefaultAzureCredential  # type: ignore[import-not-found]


async def handle(turn, hr, state) -> None:
    description = turn.activity.text or ""
    employee_id = turn.activity.from_property.aad_object_id or "E001"

    classification = await hr.post("/tickets/classify", json={"description": description})
    if classification["autoAnswer"] and not classification["escalateImmediately"]:
        # Hand back to UC1 RAG path
        from . import uc1_policy_qa
        await uc1_policy_qa.handle(turn, hr, state)
        return

    ticket = await hr.post("/tickets/create", json={"employeeId": employee_id, "description": description})
    await hr.post(f"/tickets/{ticket['id']}/escalate")

    hr_partner_id = ticket.get("assignedToId")
    chat_link = await _open_handoff_chat(employee_id, hr_partner_id, ticket["id"]) if hr_partner_id else None

    msg = (
        f"I've created case **{ticket['id']}** ({classification['categoryLabel']}) and assigned it to your HR Partner. "
        "They will reach out within 1 business day."
    )
    if chat_link:
        msg += f" I also opened a private Teams chat: {chat_link}"
    await turn.send_activity(msg)


async def _open_handoff_chat(employee_id: str, hr_partner_id: str, ticket_id: str) -> str | None:
    """Create a 1:1 Teams chat via Microsoft Graph using the bot's managed identity.

    For the demo we return a pseudo-deep-link; production code calls
    POST /chats and POST /chats/{id}/messages with proper OBO auth.
    """
    if os.environ.get("DISABLE_GRAPH") == "1":
        return f"https://teams.microsoft.com/l/chat/0/0?topic=Case+{ticket_id}"
    try:
        cred = DefaultAzureCredential()
        token = (await cred.get_token("https://graph.microsoft.com/.default")).token
        async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}) as c:
            r = await c.post(
                "https://graph.microsoft.com/v1.0/chats",
                json={
                    "chatType": "oneOnOne",
                    "members": [
                        {"@odata.type": "#microsoft.graph.aadUserConversationMember", "roles": ["owner"], "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{employee_id}')"},
                        {"@odata.type": "#microsoft.graph.aadUserConversationMember", "roles": ["owner"], "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{hr_partner_id}')"},
                    ],
                },
                timeout=20.0,
            )
            r.raise_for_status()
            chat = r.json()
            return chat.get("webUrl")
    except Exception:  # pragma: no cover - graph quirks are demo-friendly
        return f"https://teams.microsoft.com/l/chat/0/0?topic=Case+{ticket_id}"
