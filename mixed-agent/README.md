# Solution D — Mixed (Copilot Studio + Foundry connected agent)

The lowest-cost, lowest-maintenance, most maker-friendly path that still gives you advanced model reasoning where it matters.

> **Pattern.** Copilot Studio is the **primary surface**. A small Foundry hosted agent is invoked as a **connected agent** for the two use cases that benefit most from model-led reasoning (UC4 internal mobility, UC5 feedback summary). Everything else stays declarative.

## Why this mix

| Goal | How this mix delivers |
|---|---|
| **Lowest cost** | No APIM, no dedicated Container Apps for the agent, no Cosmos, no AI Search service. SharePoint hosts the handbook (UC1) → no AI Search. Dataverse hosts state → no Cosmos. Backend is **Azure Functions Consumption** instead of Container Apps → scales to zero. Foundry charges only for the few advanced calls. |
| **Lowest maintenance** | Power Platform managed solution + Foundry hosted agent + serverless Functions. No container images to roll, no APIM versioning, no scheduled-job container to babysit (Copilot Studio's scheduled flows replace it). |
| **Highest flexibility for business users** | HR makers edit topics, generative answers grounding, and Agent Flows directly in Copilot Studio. The Foundry agent has only two narrow tools — devs touch it rarely. |

See [docs/architecture/mixed.md](../docs/architecture/mixed.md) and [docs/findings/mixed.md](../docs/findings/mixed.md).

## What lives where

| UC | Implementation | Owner |
|---|---|---|
| UC1 Policy Q&A | Copilot Studio **generative answers over SharePoint** | HR maker |
| UC2 Time-off approval | Agent Flow + **Approvals connector** | HR maker |
| UC3 Onboarding | Agent Flow + **Dataverse** + scheduled flow | HR maker |
| UC4 Internal mobility | Topic → **connected Foundry agent** (`match_internal_jobs` tool + LLM pitch) | Dev (rarely) |
| UC5 360° feedback | Topic kicks off Agent Flow (open) **or** connected Foundry agent (summarize) | Maker + Dev |
| UC6 Triage & escalation | Topic + classifier flow + **`TransferConversation`** to HR queue | HR maker |

## Layout

```
mixed-agent/
├─ solution/                     # Copilot Studio managed solution (primary surface)
│  ├─ topics/                    # Six topics — most are hand-off-to-flow or generative
│  ├─ flows/                     # Agent Flows: time-off, onboarding, feedback open, triage
│  ├─ connectors/
│  │  ├─ hr-api.swagger.json     # Slim Custom Connector to the Functions backend
│  │  └─ foundry-agent.swagger.json  # Thin connector → Functions /agent/invoke (proxies Foundry)
│  └─ solution.yaml
├─ foundry/                      # Tiny connected agent (only UC4 + UC5 summary)
│  ├─ agent/main.py              # Microsoft Agent Framework, 3 tools total
│  ├─ project/agent.yaml         # Hosted agent definition; published as REST endpoint
│  └─ Dockerfile
├─ backend/                      # Azure Functions (Python) — replaces FastAPI+Container App
│  ├─ function_app.py            # Single function app exposing /api/* HTTP triggers
│  ├─ host.json
│  └─ requirements.txt
├─ infra/main.bicep              # Functions (Consumption) + Foundry account+project
├─ Makefile
└─ tests/test_backend.py
```

## Cost shape (rough order-of-magnitude)

> **Illustrative only.** Actual cost depends on region, traffic, retention, SKU choices, and Microsoft list-price changes. Run the Azure Pricing Calculator and the Power Platform / Copilot Studio message-pack pricing against your real numbers before relying on these figures.

| Resource | Resting cost | Notes |
|---|---|---|
| Power Platform Copilot Studio | per-message licensing | no Azure resting cost |
| SharePoint document library | included in M365 | UC1 grounding lives here |
| Dataverse | per env | UC3/UC5/UC6 state |
| Azure Functions (Consumption) | **\$0 idle** | small HR API; scales to zero |
| Microsoft Foundry account+project | small | pay per token |
| Microsoft Foundry (gpt-4o GlobalStandard) | per token | only UC4 + UC5 calls |
| App Insights + Log Analytics | small | shared workspace |

Compare with Solution A's Container Apps (min 1 replica = constant) + Cosmos serverless RU floor + AI Search Basic (≈ €70/mo always-on) and Solution B's APIM Consumption + Container Apps backend.

## Local dev

```bash
make seed              # copy ../shared-fixtures into backend/data
make dev               # start Azure Functions locally on :7071 + Foundry agent REPL
make test
```

## Deploy

GitHub Actions workflow: [.github/workflows/mixed.yml](../.github/workflows/mixed.yml).

1. Build & deploy the Azure Functions backend (zip deploy).
2. Deploy `infra/main.bicep` (Functions + Foundry).
3. `az ai-foundry agent create --file foundry/project/agent.yaml` (creates the connected agent).
4. `pac solution pack` + `pac solution import` (Copilot Studio).
5. Wire the Foundry connector's host to the deployed agent endpoint.

## Operational shape

| Thing | Where | Who edits |
|---|---|---|
| New topic / phrase | Copilot Studio portal (or `solution/topics/*.yaml` in Git) | HR maker |
| New approval branch | Agent Flow designer | HR maker |
| Add a Foundry tool | `foundry/agent/main.py` | Dev |
| Add an HR API endpoint | `backend/function_app.py` + connector swagger | Dev |
| Manifest / publishing | `solution.yaml` | Dev (rare) |

## When NOT to pick this mix

- You need a **bespoke conversation surface** (e.g., custom Adaptive Cards driven from code on every turn) → use Solution A.
- You need **deep Microsoft Graph proactive plumbing** (e.g., manager DMs scheduled at midnight) → use Solution A.
- You want a **single technology** to point procurement at → see [decision-tree.md](../docs/decision-tree.md).

## Prerequisites

- Azure subscription with Owner on the target resource group.
- Power Platform environment with Copilot Studio enabled and Dataverse provisioned.
- Microsoft Foundry access in the chosen region.
- `az` CLI ≥ 2.60 with Bicep, `pac` CLI ≥ 1.34, Azure Functions Core Tools v4, Python 3.11.
- Entra app registration with federated credentials for GitHub OIDC.
- A Power Platform service principal with **System Administrator** on the target environment.

## Responsible AI

- UC1 grounds answers in SharePoint via Copilot Studio's generative answers — keep grounding mandatory and citations on.
- UC4 / UC5 summary calls go to a Foundry connected agent through the Functions proxy. The proxy uses managed identity (no API keys), so calls are auditable per-employee in App Insights and Foundry traces.
- UC6 always uses `TransferConversation` for sensitive cases.
- Approvals connector keeps humans in the loop on UC2.
- Run Foundry safety evaluators (Groundedness, Hate & Unfairness, Self-harm, Violence, Sexual, Protected Material, Indirect Attack) before each release.
- Disclose AI usage in the agent's welcome message; let users request a human alternative.

## Voice / IVR

**No extra Azure resources are required.** Copilot Studio is the orchestrator and is voice-enabled by default:

- **Microsoft Teams** and **Microsoft 365 Copilot** — voice is a host capability on both surfaces.
- **Copilot Studio telephony channel** — Channels → Telephony provides a Microsoft-managed PSTN voice runtime (STT/TTS included).

The connected Foundry agent is reached via the same Copilot Studio surface, so it inherits voice automatically. Azure AI Speech and Azure Communication Services are intentionally **not** provisioned here — add them only if a future requirement (custom IVR menus, ACS-side recording, warm transfer to a human queue) calls for it.

## Cleanup

```bash
az group delete -n <rg-name> --yes --no-wait
pac solution delete --solution-name ContosoHrConciergeMixed
az ai-foundry agent delete --name ContosoHRMobilityAdvisor
```
