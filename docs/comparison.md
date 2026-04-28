# Capability comparison

Three pure implementations of the same six HR use cases — plus one **recommended mix** — surfaced in **Microsoft 365 Copilot** and **Teams**. Solutions A/B/C deliberately avoid mixing technologies so each can be evaluated on its own. Solution D combines them where it pays off; see [decision-tree.md](decision-tree.md).

Legend: ✅ first-class · ⚠️ possible but constrained · ❌ not supported / not idiomatic

## Per use-case fit

| Use case | M365 Agents SDK (A) | Copilot Studio (B) | Foundry hosted agent (C) | Mixed (D) |
|---|---|---|---|---|
| UC1 Policy Q&A (RAG) | ✅ Custom retrieval over Azure AI Search; full control | ✅ Generative answers grounded on SharePoint + uploaded files; zero code | ✅ Built-in **File Search** tool; minimal code | ✅ SharePoint generative answers — same as B |
| UC2 Time-off approval (HITL) | ✅ Adaptive Card + proactive message via Bot Service | ✅ Approvals connector inside an Agent Flow | ⚠️ HITL through tool calls + Copilot card surfaces; less prescriptive | ✅ Approvals connector — same as B |
| UC3 Onboarding (long-running, multi-actor) | ✅ Cosmos checkpoints + scheduled tick + proactive Graph posts | ✅ Dataverse + scheduled flow + Teams reminders | ⚠️ Foundry threads + Logic App tick; multi-actor proactive notifications need extra plumbing | ✅ Dataverse + scheduled flow — same as B |
| UC4 Internal mobility | ✅ Tool call + LLM | ✅ Custom Connector + generative summary | ✅ Tool + LLM | ✅ **Foundry connected agent** (delegated from Copilot Studio) |
| UC5 360° feedback | ✅ Fan-out via Graph + LLM summary | ✅ Outlook fan-out + Dataverse + generative summary | ✅ Tools + model summary | ✅ Open via flow (B); summary via Foundry connected agent (C) |
| UC6 Triage & escalation | ✅ Sensitivity classifier + Graph 1:1 chat handoff | ✅ Built-in `TransferConversation` to HR queue | ⚠️ Tool-driven escalation; live human handoff requires custom integration | ✅ `TransferConversation` — same as B |

## Engineering & operations

| Concern | A — Agents SDK | B — Copilot Studio | C — Foundry | D — Mixed |
|---|---|---|---|---|
| Primary skill set | Python developer | HR/business power user + maker | Python developer + AI ops | **Maker-led, with thin dev surface for the connected agent** |
| Source of truth | Git | Git (`pac solution` export) + Power Platform env | Git + Foundry project state | Git (`pac solution` + Foundry agent yaml + Functions) |
| Auth surface | Bot Service + Entra app + Managed Identity | Power Platform connections + APIM key | Foundry project MI + AOAI/Search RBAC | Power Platform connections + Functions key + Foundry MI |
| Long-running orchestration | Manual (scheduled job + Cosmos) | Built-in (scheduled flows + Dataverse) | Manual (Logic App tick + Cosmos) | Built-in (scheduled flows + Dataverse) |
| Built-in human handoff | Build with Graph | ✅ `TransferConversation` to queue | Build with tools | ✅ `TransferConversation` |
| Built-in RAG | Build with AI Search | ✅ Generative answers + SharePoint | ✅ File Search | ✅ Generative answers + SharePoint |
| Native publish to **M365 Copilot Chat** | Via M365 Agents Toolkit + manifest | ✅ One toggle | ✅ Foundry publish flow | ✅ One toggle (Copilot Studio) |
| Native publish to **Teams** | Via M365 Agents Toolkit + manifest | ✅ One toggle | ✅ Foundry publish flow | ✅ One toggle (Copilot Studio) |
| Observability | App Insights, custom | Power Platform analytics | Foundry tracing + App Insights | Power Platform analytics + App Insights (Functions + Foundry) |
| Evaluations | Custom (PromptFlow / pytest) | Limited | ✅ Foundry evaluations + datasets | ✅ on the Foundry agent only |
| Lifecycle tooling | M365 Agents Toolkit (`teamsapp.yml`) | `pac solution import` | `az ai-foundry agent create` | `pac` + `az ai-foundry agent create` + Functions zip deploy |
| IaC | Bicep | Bicep (Azure side only) + Power Platform solution | Bicep | Bicep (Functions + Foundry) + Power Platform solution |
| Per-environment promotion | GitHub Actions + Toolkit envs | `pac` + Power Platform DLP-aware envs | GitHub Actions + Foundry envs | All three combined |
| Time-to-first-demo | Medium | **Lowest** | Low | Low |
| Operational cost (resting) | Container Apps min-replicas + Cosmos + AI Search | APIM + Container Apps + Power Platform licenses | Foundry + AOAI + Container Apps + Search | **Lowest Azure-side** — Functions Consumption + Foundry pay-per-token; Power Platform licensing on the conversation side |
| Vendor coupling to M365/Power | Medium (Bot Service) | High (Power Platform) | Medium (Foundry) | High (Power Platform + Foundry) |

## When each one wins

- **A (M365 Agents SDK)** — bespoke conversation logic, long-running custom orchestrations, deep Graph use, code-review-first workflow.
- **B (Copilot Studio)** — fastest delivery, citizen-developer-friendly, heavy use of approvals/SharePoint/Dataverse, tight M365 integration.
- **C (Foundry hosted agent)** — model-led reasoning with a few tools, you want hosted threads + evaluations + rapid Copilot publishing, and you treat the agent as a deployable asset.
- **D (Mixed)** — you're already heavy on M365/Power, you want HR makers to own day-to-day topic and flow changes, and a *small* number of UCs benefit from model-led reasoning. Lowest resting cost; best balance of flexibility-for-makers and depth-where-needed.

## What is *not* in this comparison

- Cost modelling at scale (depends on volume and model choices).
- Multi-tenant ISV scenarios (different governance shape).
- Voice / IVR experiences (Copilot Studio leads here; out of scope for this repo).
