"""UC1 — Policy & benefits Q&A.

Uses Azure AI Search for retrieval and Azure OpenAI for generation. The
search index is seeded from ``shared-fixtures/policies/`` by the deployment
pipeline (`infra/scripts/seed_search.py`).
"""
from __future__ import annotations

import os

from azure.identity.aio import DefaultAzureCredential  # type: ignore[import-not-found]
from azure.search.documents.aio import SearchClient  # type: ignore[import-not-found]
from openai import AsyncAzureOpenAI

SEARCH_ENDPOINT = os.environ.get("SEARCH_ENDPOINT", "")
SEARCH_INDEX = os.environ.get("SEARCH_INDEX", "hr-policies")
AOAI_ENDPOINT = os.environ.get("AOAI_ENDPOINT", "")
AOAI_DEPLOYMENT = os.environ.get("AOAI_DEPLOYMENT", "gpt-4o")

SYSTEM_PROMPT = """You are Contoso HR Concierge. Answer ONLY from the provided policy excerpts.
Always cite the source policy name in [brackets]. If the answer is not in the excerpts,
say you cannot find it and suggest contacting an HR Partner."""


async def handle(turn, hr, state) -> None:
    question = turn.activity.text
    cred = DefaultAzureCredential()

    async with SearchClient(SEARCH_ENDPOINT, SEARCH_INDEX, credential=cred) as search:
        results = await search.search(search_text=question, top=4)
        chunks = []
        async for r in results:
            chunks.append(f"[{r['policy']}] {r['content']}")

    if not chunks:
        # Fallback: ask the backend for raw policies (offline/local dev)
        policies = await hr.get("/policies")
        for p in policies[:2]:
            doc = await hr.get(f"/policies/{p['name']}")
            chunks.append(f"[{p['name']}] {doc['content'][:1500]}")

    client = AsyncAzureOpenAI(
        azure_endpoint=AOAI_ENDPOINT,
        azure_ad_token_provider=lambda: cred.get_token("https://cognitiveservices.azure.com/.default").token,
        api_version="2024-10-21",
    )
    completion = await client.chat.completions.create(
        model=AOAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nPolicy excerpts:\n" + "\n\n".join(chunks)},
        ],
        temperature=0.2,
    )
    answer = completion.choices[0].message.content
    await turn.send_activity(answer)
