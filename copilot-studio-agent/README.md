# Solution B — Copilot Studio

A **declarative** HR Concierge built in **Microsoft Copilot Studio** with Topics, Agent Flows, Dataverse, the Approvals connector, SharePoint knowledge, and a single FastAPI backend exposed via a **Custom Connector** through Azure API Management.

## Why this technology

- Lowest code surface area; HR power users can edit Topics directly.
- Native channel support for **M365 Copilot Chat** and **Microsoft Teams** — published from Copilot Studio, no Teams app package to maintain.
- Approvals + Dataverse + SharePoint give you the entire HITL + storage + knowledge stack out-of-the-box.
- Best fit when most of the value is conversation-driven knowledge + occasional connector calls.

## Layout

```
copilot-studio-agent/
├─ solution/
│  ├─ solution.yaml             # Power Platform managed solution manifest
│  ├─ topics/uc{1..6}.yaml      # Copilot Studio topics
│  ├─ flows/*.json              # Agent Flows + scheduled flow
│  └─ connectors/hr-api.swagger.json  # Custom Connector (slim schema)
├─ backend/                     # Same FastAPI backend, dedicated copy
├─ infra/main.bicep             # APIM + Container Apps for the backend
└─ Makefile
```

## Local dev

```bash
make seed
make dev      # starts backend on :8000
make test
```

Topics are tested in **Copilot Studio Test pane** against a dev environment. Use `pac connection create` to point the Custom Connector at your local backend tunnel for development (e.g. `devtunnel`).

## Deploy

GitHub Actions workflow: `.github/workflows/copilot-studio.yml`. It uses OIDC + a Power Platform service principal to:
1. Build & push the backend image, deploy `infra/main.bicep` (APIM + Container Apps).
2. Run `pac auth create` against the Power Platform target environment.
3. `pac solution pack` then `pac solution import` of `solution/`.
4. Update the Custom Connector host to the APIM gateway URL.
5. Publish the Copilot Studio agent to **M365 Copilot Chat** and **Teams**.

## Use case mapping

| UC | Where | How |
|---|---|---|
| UC1 Policy Q&A | `topics/uc1_policy_qa.yaml` | `SearchAndSummarizeContent` over SharePoint + uploaded files |
| UC2 Time-off approval | `topics/uc2_time_off.yaml` + `flows/HR_RequestLeaveAndApprove.json` | Topic gathers dates → Agent Flow → **Approvals** connector → backend |
| UC3 Onboarding | `topics/uc3_onboarding.yaml` + `flows/HR_StartOnboarding.json` + `flows/HR_OnboardingTick.json` | Dataverse-persisted plan + scheduled flow with Teams reminders |
| UC4 Mobility | `topics/uc4_mobility.yaml` | One Custom Connector call + generative summary |
| UC5 360° feedback | `topics/uc5_feedback.yaml` + `flows/HR_FeedbackOpenOrSummarize.json` | Outlook fan-out + Dataverse storage + generative summary |
| UC6 Triage & escalation | `topics/uc6_triage.yaml` | Classifier call + **TransferConversation** built-in handoff to HR queue |

## Prerequisites

- Azure subscription (for APIM + Container Apps + AOAI) with Owner on the target resource group.
- Microsoft Power Platform environment with Copilot Studio enabled and Dataverse provisioned.
- `pac` CLI ≥ 1.34, `az` CLI ≥ 2.60 with Bicep extension.
- A Power Platform service principal with **System Administrator** on the target environment, plus an Entra app registration with federated credentials for GitHub OIDC.
- Azure OpenAI access in the chosen region.
- SharePoint site with the policy library (or accept the seeded library that the workflow creates).

## Responsible AI

- UC1 generative answers are bound to the SharePoint policy library — **citations are non-negotiable**; keep `groundingSources: [SharePoint, Files]` in the topic and reject ungrounded answers.
- UC6 always uses `TransferConversation` for sensitive cases. Never replace it with an auto-reply.
- Approvals connector (UC2) keeps a human in the loop on every leave decision.
- Dataverse audit log must be enabled on the HR tables; review it monthly.
- Run the Foundry safety evaluators against the topic before publishing to M365 Copilot.
- Costs in this repo are **illustrative** — confirm against the Azure Pricing Calculator and the Copilot Studio message-pack pricing for your tenant.

## Cleanup

```bash
az group delete -n <rg-name> --yes --no-wait
pac solution delete --solution-name ContosoHrConcierge
# unpublish the agent from Copilot Studio and remove the Custom Connector
```
