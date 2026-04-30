# Solution C — Microsoft Foundry hosted agent

A **Foundry-hosted** HR Concierge agent. The agent itself runs **inside a Microsoft Foundry project**; the agent's tool implementations are written in Python with the **Microsoft Agent Framework** and connect to a dedicated FastAPI backend. Foundry's File Search powers UC1, and the agent is **published natively to M365 Copilot Chat and Teams** from the Foundry project — no Teams app package required from us.

## Why this technology

- Hosted runtime, threads, evaluations, and observability come from Foundry — minimal infrastructure to babysit.
- File Search and other built-in agent tools shorten time-to-value for RAG-style use cases.
- "Publish to Copilot" flow is the cleanest way to surface a code-first agent in M365 Copilot today.
- Best fit when you want the durability + governance of Foundry projects and have a few custom tool calls but mostly model-driven reasoning.

## Layout

```
foundry-agent/
├─ agent/
│  ├─ main.py                 # Microsoft Agent Framework — ChatAgent + tools
│  └─ tools/uc{1..6}.py       # One tool module per use case
├─ backend/                   # Dedicated FastAPI mock HR API
├─ project/agent.yaml         # Foundry hosted-agent definition (file_search + openapi tools)
├─ search/                    # AI Search index + OpenAPI for the agent
├─ infra/main.bicep           # Foundry account + project + AOAI + Search + Container App + Cosmos
├─ tests/
└─ Makefile
```

## Local dev

```bash
make seed   # copy shared-fixtures/* into backend/data
make dev    # start backend on :8000 and the Agent Framework REPL
make test
```

In dev, the agent runs as a local Python process; in production, the same instructions and tools are owned by the **hosted Foundry agent** defined in `project/agent.yaml`.

## Deploy

GitHub Actions workflow: `.github/workflows/foundry.yml`. It uses OIDC + Foundry's CLI to:
1. Build and push the backend image to ACR.
2. Deploy `infra/main.bicep` (Foundry account + project + AOAI + Search + Cosmos + Container Apps).
3. Seed the Search index from `shared-fixtures/policies/`.
4. Run `az ai-foundry agent create --file project/agent.yaml`.
5. **Publish the agent to M365 Copilot Chat and Teams** via Foundry's publish API.

## Use case mapping

| UC | Where | How |
|---|---|---|
| UC1 Policy Q&A | Foundry **File Search** tool over the policy corpus (no code required) |
| UC2 Time-off approval | `tools/uc2.py` — `request_time_off`, `approve_or_reject_time_off` |
| UC3 Onboarding | `tools/uc3.py` + a Logic App scheduled tick (in `infra/main.bicep`) |
| UC4 Mobility | `tools/uc4.py` — `match_internal_jobs` + model-drafted pitch |
| UC5 360° feedback | `tools/uc5.py` — `open_feedback`, `summarize_feedback` |
| UC6 Triage & escalation | `tools/uc6.py` — classifier + create + escalate; sensitive cases never auto-answered |

## Prerequisites

- Azure subscription with Owner on the target resource group.
- Microsoft Foundry access (the `Microsoft.CognitiveServices/accounts` *AIServices* kind) enabled in the chosen region.
- `az` CLI ≥ 2.60 with Bicep, `az ai-foundry` extension, Python 3.11.
- Entra app registration with federated credentials for GitHub OIDC.
- M365 tenant with permission to publish Foundry agents to Copilot Chat / Teams.

## Responsible AI

- UC1 uses Foundry **File Search** — keep the policy corpus pinned and re-evaluate groundedness when the corpus changes.
- UC6 sensitive-case handling is enforced in the agent instructions and is hard-coded to never produce a final answer for those categories — keep that.
- The hosted agent runs **inside the Foundry project**, which gives you traces and built-in evaluations — use them: run Groundedness, Hate & Unfairness, Self-harm, Violence, Sexual, Protected Material, and Indirect Attack evaluators before publishing.
- Disclose AI usage in the published agent's description; let users request a human alternative.
- The hosted-container surface (`agent/main.py`) is provided so the same code runs identically in dev and Foundry; production traffic flows through the Foundry agent endpoint, not the container.
- Costs in this repo are **illustrative**. Token usage scales with traffic — monitor with Foundry's usage dashboards.

## Cleanup

```bash
az group delete -n <rg-name> --yes --no-wait
az ai-foundry agent delete --name ContosoHRConcierge
```
