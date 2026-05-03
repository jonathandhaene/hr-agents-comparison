"""UC4 — Internal mobility / career coach."""
from __future__ import annotations

import os

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider  # type: ignore[import-not-found]
from openai import AsyncAzureOpenAI

FOUNDRY_ENDPOINT = os.environ.get("FOUNDRY_ENDPOINT", "")
FOUNDRY_DEPLOYMENT = os.environ.get("FOUNDRY_DEPLOYMENT", "gpt-4o")


async def handle(turn, hr, state) -> None:
    employee_id = turn.activity.from_property.aad_object_id or "E001"
    employee = await hr.get(f"/employees/{employee_id}")
    interests = _extract_interests(turn.activity.text or "")

    matches = await hr.post(
        "/jobs/search",
        json={"employeeId": employee_id, "interests": interests, "location": employee.get("location")},
    )
    if not matches:
        await turn.send_activity("I didn't find strong matches yet. Tell me more about what you're interested in?")
        return

    pitch = await _draft_pitch(employee, matches[0], interests)
    bullets = "\n".join(f"- **{j['title']}** — {j['location']} ({j['level']})" for j in matches[:3])
    await turn.send_activity(
        f"Top matches for you:\n\n{bullets}\n\n**Suggested pitch for the top role**\n\n{pitch}"
    )


def _extract_interests(text: str) -> list[str]:
    text = text.lower()
    keywords = ["product management", "engineering", "design", "research", "data", "analytics", "platform"]
    return [k for k in keywords if k in text] or ["product management"]


async def _draft_pitch(employee: dict, job: dict, interests: list[str]) -> str:
    client = AsyncAzureOpenAI(
        api_version="2024-10-21",
        azure_endpoint=FOUNDRY_ENDPOINT,
        azure_ad_token_provider=get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        ),
    )
    completion = await client.chat.completions.create(
        model=FOUNDRY_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "You write short, candid internal-mobility pitches (max 90 words)."},
            {"role": "user", "content": (
                f"Candidate: {employee['displayName']}, currently {employee['title']} in {employee['department']}, "
                f"based in {employee['location']}, skills: {', '.join(employee['skills'])}.\n"
                f"Target role: {job['title']} ({job['level']}, {job['location']}).\n"
                f"Stated interest: {', '.join(interests)}.\n"
                f"Write the pitch in first person."
            )},
        ],
        temperature=0.5,
    )
    return completion.choices[0].message.content or ""
