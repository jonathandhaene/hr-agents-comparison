# Capability comparison

Three implementations of the same six HR use cases, surfaced in **Microsoft 365 Copilot** and **Teams**. Mixing technologies is intentionally *out of scope* for the implementations in this repo (see [decision-tree.md](decision-tree.md) for guidance on when teams choose to mix).

Legend: ✅ first-class · ⚠️ possible but constrained · ❌ not supported / not idiomatic

## Per use-case fit

| Use case | M365 Agents SDK (A) | Copilot Studio (B) | Foundry hosted agent (C) |
|---|---|---|---|
| UC1 Policy Q&A (RAG) | ✅ Custom retrieval over Azure AI Search; full control | ✅ Generative answers grounded on SharePoint + uploaded files; zero code | ✅ Built-in **File Search** tool; minimal code |
| UC2 Time-off approval (HITL) | ✅ Adaptive Card + proactive message via Bot Service | ✅ Approvals connector inside an Agent Flow | ⚠️ HITL through tool calls + Copilot card surfaces; less prescriptive |
| UC3 Onboarding (long-running, multi-actor) | ✅ Cosmos checkpoints + scheduled tick + proactive Graph posts | ✅ Dataverse + scheduled flow + Teams reminders | ⚠️ Foundry threads + Logic App tick; multi-actor proactive notifications need extra plumbing |
| UC4 Internal mobility | ✅ Tool call + LLM | ✅ Custom Connector + generative summary | ✅ Tool + LLM |
| UC5 360° feedback | ✅ Fan-out via Graph + LLM summary | ✅ Outlook fan-out + Dataverse + generative summary | ✅ Tools + model summary |
| UC6 Triage & escalation | ✅ Sensitivity classifier + Graph 1:1 chat handoff | ✅ Built-in `TransferConversation` to HR queue | ⚠️ Tool-driven escalation; live human handoff requires custom integration |

## Engineering & operations

| Concern | A — Agents SDK | B — Copilot Studio | C — Foundry |
|---|---|---|---|
| Primary skill set | Python developer | HR/business power user + maker | Python developer + AI ops |
| Source of truth | Git | Git (`pac solution` export) + Power Platform env | Git + Foundry project state |
| Auth surface | Bot Service + Entra app + Managed Identity | Power Platform connections + APIM key | Foundry project MI + AOAI/Search RBAC |
| Long-running orchestration | Manual (scheduled job + Cosmos) | Built-in (scheduled flows + Dataverse) | Manual (Logic App tick + Cosmos) |
| Built-in human handoff | Build with Graph | ✅ `TransferConversation` to queue | Build with tools |
| Built-in RAG | Build with AI Search | ✅ Generative answers + SharePoint | ✅ File Search |
| Native publish to **M365 Copilot Chat** | Via M365 Agents Toolkit + manifest | ✅ One toggle | ✅ Foundry publish flow |
| Native publish to **Teams** | Via M365 Agents Toolkit + manifest | ✅ One toggle | ✅ Foundry publish flow |
| Observability | App Insights, custom | Power Platform analytics | Foundry tracing + App Insights |
| Evaluations | Custom (PromptFlow / pytest) | Limited | ✅ Foundry evaluations + datasets |
| Lifecycle tooling | M365 Agents Toolkit (`teamsapp.yml`) | `pac solution import` | `az ai-foundry agent create` |
| IaC | Bicep | Bicep (Azure side only) + Power Platform solution | Bicep |
| Per-environment promotion | GitHub Actions + Toolkit envs | `pac` + Power Platform DLP-aware envs | GitHub Actions + Foundry envs |
| Time-to-first-demo | Medium | **Lowest** | Low |
| Operational cost (resting) | Container Apps min-replicas + Cosmos + AI Search | APIM + Container Apps + Power Platform licenses | Foundry + AOAI + Container Apps + Search |
| Vendor coupling to M365/Power | Medium (Bot Service) | **High** (Power Platform) | Medium (Foundry) |

## When each one wins

- **A (M365 Agents SDK)** — bespoke conversation logic, long-running custom orchestrations, deep Graph use, code-review-first workflow.
- **B (Copilot Studio)** — fastest delivery, citizen-developer-friendly, heavy use of approvals/SharePoint/Dataverse, tight M365 integration.
- **C (Foundry hosted agent)** — model-led reasoning with a few tools, you want hosted threads + evaluations + rapid Copilot publishing, and you treat the agent as a deployable asset.

## What is *not* in this comparison

- Cost modelling at scale (depends on volume and model choices).
- Multi-tenant ISV scenarios (different governance shape).
- Voice / IVR experiences (Copilot Studio leads here; out of scope for this repo).
