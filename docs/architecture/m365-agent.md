# Architecture — Solution A: Microsoft 365 Agents SDK

![M365 Agents SDK architecture](./img/m365-agent.svg)

<details><summary>Mermaid source</summary>

```mermaid
flowchart LR
  user["Employee / Manager in M365 Copilot or Teams"]
  copilot["M365 Copilot chat"]
  teams["Teams client"]
  bot["Azure Bot Service channel registration"]
  app["Container Apps — Python Agents SDK app"]
  cosmos[("Cosmos DB — conversation + workflow state")]
  search[("Azure AI Search — handbook index")]
  api["Container Apps — FastAPI mock HR backend"]
  msgraph["Microsoft Graph — proactive messages"]
  ai["Microsoft Foundry — gpt-4o"]

  user -->|chat| copilot
  user -->|chat| teams
  copilot --> bot
  teams --> bot
  bot --> app
  app <--> cosmos
  app <--> search
  app <--> api
  app --> msgraph
  app <--> ai
  msgraph -. proactive Adaptive Card .-> teams
```

</details>

## Key choices

- **Azure Bot Service** registration; one channel for M365 Copilot, one for Teams.
- **Container Apps** for the agent runtime (not Functions: long-lived turn handlers + WebSocket-friendly).
- **Cosmos DB** for conversation references (needed for proactive messages in UC2/UC3) and workflow checkpoints.
- **Azure AI Search** for UC1 RAG over `shared-fixtures/policies/`.
- **Microsoft Graph** with the bot's managed identity for proactive Teams messages and creating handoff chats (UC6).
- **Microsoft 365 Agents Toolkit** packages the manifest and publishes to M365 Copilot + Teams.