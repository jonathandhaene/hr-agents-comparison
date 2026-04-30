"""UC5 — 360° performance feedback collection."""
from __future__ import annotations

import os

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider  # type: ignore[import-not-found]
from openai import AsyncAzureOpenAI

AOAI_ENDPOINT = os.environ.get("AOAI_ENDPOINT", "")
AOAI_DEPLOYMENT = os.environ.get("AOAI_DEPLOYMENT", "gpt-4o")


async def handle(turn, hr, state) -> None:
    text = (turn.activity.text or "").lower()
    if "summary" in text or "summarize" in text:
        await _summarize(turn, hr)
        return
    await _kickoff(turn, hr, state)


async def _kickoff(turn, hr, state) -> None:
    # For demo: subject is the message author; reviewers are 3 peers.
    subject_id = turn.activity.from_property.aad_object_id or "E001"
    employees = await hr.get("/employees")
    peers = [e["id"] for e in employees if e["persona"] == "employee" and e["id"] != subject_id][:3]
    req = await hr.post(
        "/feedback/request",
        json={"cycleId": "FB-H1-2026", "subjectEmployeeId": subject_id, "requestedReviewerIds": peers},
    )
    await turn.send_activity(
        f"360° request **{req['id']}** opened for **{subject_id}**. Invitations queued for {len(peers)} reviewers."
    )


async def _summarize(turn, hr) -> None:
    # In a real flow we'd resolve the request id from context; demo uses the most recent one.
    text = turn.activity.text or ""
    rid = text.split()[-1] if text.split()[-1].startswith("FBR-") else None
    if not rid:
        await turn.send_activity("Tell me which feedback request to summarize, e.g. `summarize FBR-12345678`.")
        return
    raw = await hr.get(f"/feedback/{rid}/summary")
    if raw["received"] == 0:
        await turn.send_activity("No responses yet — try again once reviewers have submitted.")
        return

    client = AsyncAzureOpenAI(
        api_version="2024-10-21",
        azure_endpoint=AOAI_ENDPOINT,
        azure_ad_token_provider=get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        ),
    )
    completion = await client.chat.completions.create(
        model=AOAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": "Summarize 360 feedback into Strengths, Growth areas, Notable moments. Keep it neutral and quote sparingly."},
            {"role": "user", "content": str(raw)},
        ],
        temperature=0.3,
    )
    await turn.send_activity(completion.choices[0].message.content or "(no summary)")
