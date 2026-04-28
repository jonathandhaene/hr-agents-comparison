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
