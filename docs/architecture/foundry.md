# Architecture — Solution C: Microsoft Foundry hosted agent

![Foundry hosted agent architecture](./img/foundry.svg)

<details><summary>Mermaid source</summary>

```mermaid
flowchart LR
  user["Employee / Manager in M365 Copilot or Teams"]
  copilot["M365 Copilot"]
  teams["Teams"]
  foundry["Microsoft Foundry project — published agent endpoint"]
  hosted["Hosted Agent container — Microsoft Agent Framework Python"]
  filesearch["Foundry File Search tool over handbook"]
  models["Foundry model catalog — gpt-4o"]
  cosmos[("Cosmos DB — workflow state")]
  api["Container Apps — FastAPI mock HR backend"]
  msgraph["Microsoft Graph — OBO"]
  obs["App Insights + Foundry tracing"]

  user --> copilot
  user --> teams
  copilot -->|publish-to-Copilot| foundry
  teams -->|publish-to-Teams| foundry
  foundry --> hosted
  hosted <--> filesearch
  hosted <--> models
  hosted <--> cosmos
  hosted <--> api
  hosted --> msgraph
  hosted --> obs
```

</details>

## Key choices

- **Foundry project** is mandatory per the brief. All Azure resources sit under one project.
- **Hosted agent** (preview) — code-first using **Microsoft Agent Framework (Python)**, deployed to Foundry as a container.
- **Foundry File Search** built-in tool for UC1 (handbook uploaded to the project) — no separate Azure AI Search.
- **Cosmos DB** for long-running workflow state (UC3, UC5).
- **Foundry → M365 Copilot publish** is the surfacing path. No M365 Agents SDK shell, no Copilot Studio in front.
- **Agent identity** (Entra) used for Microsoft Graph calls in UC2 (manager DM) and UC6 (handoff chat) via OBO.
- **Foundry agent tracing + App Insights** for observability.
