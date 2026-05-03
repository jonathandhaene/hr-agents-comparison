# Solution A — Microsoft 365 Agents SDK

A code-first HR Concierge built on the **Microsoft 365 Agents SDK (Python)**, deployed to Azure Container Apps and surfaced in **M365 Copilot** and **Microsoft Teams** via Azure Bot Service.

## Why this technology

- Maximum control over conversation flow, proactive messaging, and tool calls.
- Direct access to Microsoft Graph for handoffs (UC6) and proactive Adaptive Cards (UC2, UC3).
- Best fit when you need long-running orchestrations and custom tool calls that go beyond declarative authoring.

## Layout

```
m365-agent/
├─ src/                  # Agents SDK app + per-UC skills
│  ├─ agent.py           # Root agent + intent router
│  ├─ state.py           # Cosmos-backed conversation refs / workflow state
│  └─ skills/uc{1..6}.py # One module per use case
├─ backend/              # Dedicated FastAPI mock HR API
├─ appPackage/           # Teams/M365 manifest
├─ infra/main.bicep      # Container Apps, Bot, Foundry, AI Search, Cosmos, KV
├─ tests/
├─ teamsapp.yml          # Microsoft 365 Agents Toolkit lifecycle
└─ Makefile
```

## Local dev

```bash
make seed   # copies shared-fixtures/* into backend/data
make dev    # starts backend on :8000 and agent on :3978
make test   # pytest
```

Test the agent locally with **Microsoft 365 Agents Playground** (`teamsapp playground`).

## Deploy

GitHub Actions workflow: `.github/workflows/m365-agent.yml`. It uses OIDC to Azure to:
1. Build the agent + backend Docker images and push to ACR.
2. Run `az deployment group create` with `infra/main.bicep`.
3. Seed the Azure AI Search index from `shared-fixtures/policies/`.
4. Run the M365 Agents Toolkit (`teamsapp.yml`) to publish the app to the M365 admin centre and Teams.

## Use case mapping

| UC | Module | How |
|---|---|---|
| UC1 Policy Q&A | `skills/uc1_policy_qa.py` | Azure AI Search retrieval + Microsoft Foundry generation |
| UC2 Time-off approval | `skills/uc2_time_off.py` | Adaptive Card + proactive message via stored conversation reference |
| UC3 Onboarding | `skills/uc3_onboarding.py` | Long-running plan + scheduled tick job |
| UC4 Mobility | `skills/uc4_mobility.py` | Profile-aware tool call + LLM-drafted pitch |
| UC5 360° feedback | `skills/uc5_feedback.py` | Fan-out to peers + LLM summary |
| UC6 Triage & escalation | `skills/uc6_triage.py` | Sensitivity classifier + Graph-driven 1:1 chat handoff |

## Prerequisites

- Azure subscription with Owner on the target resource group (one-time, for role assignments).
- Azure CLI ≥ 2.60 with the Bicep extension (`az bicep version`).
- Python 3.11.
- A Microsoft Entra app registered for federated credentials (used by GitHub OIDC).
- M365 tenant with permission to side-load Teams apps and a configured Microsoft 365 Agents Toolkit project.
- Microsoft Foundry access in the chosen region.

## Responsible AI

This solution surfaces HR data to employees in conversational form. Before opening it to real users:

- Ground every UC1 answer in indexed policies and **always show citations** — do not let the model answer policy questions without retrieved context.
- UC6 routes sensitive categories (harassment, discrimination, mental-health, PII leak) straight to a human HR partner; never bypass that classifier.
- Mask employee identifiers and free-text grievances in App Insights traces (the included logger does this; keep it).
- Run Foundry's safety evaluators (Groundedness, Hate & Unfairness, Self-harm, Violence, Sexual, Protected Material, Indirect Attack) on a representative eval set before release.
- Disclose AI usage in the Teams welcome message (the manifest does so) and let users request a human alternative.

Costs shown elsewhere in this repo are **illustrative**. Run the Azure Pricing Calculator for your region and traffic before committing.

## Voice / IVR

**No extra Azure resources are required.** Voice is delivered through the surfaces the agent is published on:

- **Microsoft Teams** — the Bot Service registration enables Teams; voice in 1:1 calls and meetings is a Teams capability.
- **Microsoft 365 Copilot** — the M365Extensions channel makes the agent reachable from Microsoft 365 Copilot, where voice input/output is a host capability.

PSTN/IVR is **deliberately out of scope** for this solution. If a contact-centre style IVR is needed, prefer Solution C (Foundry) or Solution B/D (Copilot Studio telephony channel).

## Cleanup

```bash
az group delete -n <rg-name> --yes --no-wait
# remove the Teams app from the M365 admin centre
# revoke the federated credential on the Entra app registration
```
