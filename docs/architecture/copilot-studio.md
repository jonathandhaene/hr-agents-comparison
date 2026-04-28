# Architecture — Solution B: Microsoft Copilot Studio

![Copilot Studio architecture](./img/copilot-studio.svg)

<details><summary>Mermaid source</summary>

```mermaid
flowchart LR
  user["Employee / Manager in M365 Copilot or Teams"]
  copilot["M365 Copilot"]
  teams["Teams"]
  cs["Copilot Studio agent — topics + generative answers"]
  flows["Agent Flows (Power Automate)"]
  approvals["Approvals connector"]
  dataverse[("Dataverse — onboarding + feedback state")]
  sp[("SharePoint — HR handbook and policies")]
  conn["Custom Connector — HR API OpenAPI"]
  apim["Azure API Management"]
  api["Container Apps — FastAPI mock HR backend"]

  user --> copilot
  user --> teams
  copilot --> cs
  teams --> cs
  cs <-->|knowledge| sp
  cs --> flows
  flows --> approvals
  flows <--> dataverse
  flows --> conn
  conn --> apim --> api
```

</details>

## Key choices

- **Copilot Studio** owns the conversational surface; one topic per UC.
- **Generative answers + SharePoint knowledge** for UC1 (no custom RAG needed).
- **Agent Flows** (Power Automate) for everything stateful or multi-step (UC2, UC3, UC5).
- **Approvals connector** for UC2 manager approval — no custom card code.
- **Dataverse** for onboarding plan rows (UC3) and feedback responses (UC5).
- **Custom Connector** generated from the FastAPI backend's OpenAPI spec, fronted by **APIM** for OAuth.
- **Built-in human handoff** to Teams for UC6 escalations.
