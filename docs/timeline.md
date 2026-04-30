# Timeline — How an HR agent estate evolves, and why day-one choices matter

A composite story drawn from real engagements. The numbers, names, and use cases are illustrative, but the **shape of the curve** is what we see again and again. Read this before you commit to one of the four solutions in this repo.

> TL;DR — most teams *think* they're picking a tech for today's six use cases. They're actually picking the **substrate** that the next twenty will be built on. The choices that matter on day one are the ones that are expensive to undo in year three.

## The cast

- **Contoso Ltd** — 5,000 employees, single tenant, M365 E5, Power Platform per-user licensing for HR, no existing agents.
- **HR Operations** (12 people) — owns policies, onboarding, feedback cycles, ticketing.
- **HR Tech / People Analytics** (3 people, one of whom can write Python) — owns the integrations.
- **Central Platform team** — owns Azure tenancy, networking, security, FinOps.
- **CISO / DPO** — has opinions about data egress, retention, EU residency.

## Day 0 — the brief

> "We want a Copilot agent that answers HR policy questions and books time off. Six use cases by end of quarter."

Three solutions on the table — A (M365 Agents SDK), B (Copilot Studio), C (Foundry). Mixed (D) wasn't on the slide. The team picks **B (Copilot Studio)** for time-to-demo. Reasonable.

---

## Year 1 — "this is great, can we add…"

**State of the estate:** 1 agent, 6 UCs, ~600 monthly active users, ~12k messages/mo.

**What gets added (typical):**
- *"Can it read the new starter handbook?"* → second SharePoint library wired into generative answers. **Cost: a maker afternoon.**
- *"Can it post the time-off summary into the manager's Teams chat?"* → Agent Flow tweak. **Cost: a maker afternoon.**
- *"Can it explain the new bonus policy?"* → policy update in SharePoint, agent picks it up. **Cost: zero engineering.**
- *"Can the IT team have one too, for laptop returns?"* → second Copilot Studio agent, shares the HR custom connector. **Cost: a couple of weeks.**

**What hurts (typical):**
- The first time a manager asks *"summarise this employee's last three feedback cycles"*, generative answers produces a confident-but-shallow summary. HR wants something better.
- Onboarding plans live in Dataverse but People Analytics wants them in Fabric. Someone writes a dataflow.
- One bad weekend: a topic edit in production breaks a flow because connection references didn't transfer with the unmanaged solution. New rule: only managed solutions in prod.

**Day-one choice that paid off:** picking a path with **built-in long-running orchestration** (flows + Dataverse, or SDK + Cosmos). Teams that picked C-only here are already writing their own Logic-App tick.

**Day-one choice that hurt:** picking AI Search for UC1 when SharePoint generative answers would have been fine. The Search service has been at €70/mo since week one with nobody to update the index.

---

## Year 2 — "the agent is the front door"

**State of the estate:** 3–4 agents (HR, IT, Facilities, Finance-lite), ~2.5k MAU, ~80k messages/mo, two of those agents call each other.

**What gets added:**
- A **mobility / careers** experience that needs ranked job matches and a generated pitch. Generative answers can't do this; the team adds a model-led component.
- **360° feedback summaries.** Same problem.
- **Manager dashboards.** People Analytics ships a Power BI report on top of Dataverse.
- **Live human handoff** to HR Partners in Teams becomes a hard requirement (regulator asked).

**The branch point.** This is where the "pure" solutions diverge:

- **Pure B teams** add **connected agents** — a small Foundry agent for the model-led parts. Congratulations, you have arrived at **Solution D (Mixed)**. The teams that started on D in year 1 have a six-month head start.
- **Pure A teams** are fine — they add tools to the SDK app. But HR makers can't change anything without a PR.
- **Pure C teams** struggle on live human handoff and proactive multi-actor flows; they end up bolting on Logic Apps and a Bot Service channel for handoff. Some quietly migrate the conversation surface to Copilot Studio and keep Foundry as a connected agent — same destination as D, slower path.

**What hurts (typical):**
- Connector sprawl. Three agents, two backends, four custom connectors, DLP policy now blocks one of them in a sub-environment. Someone documents the wiring.
- Function key rotation breaks the HR connector at 2 a.m. Someone writes a Key Vault reference + a runbook.
- Foundry tokens become a real line item once UC4 + UC5 ramp up. FinOps asks for per-UC cost attribution. App Insights custom dimensions to the rescue.
- Evaluations. HR Legal wants to know "how often does the agent give a wrong policy answer?" Teams without an evaluation harness are stuck reading transcripts.

**Day-one choice that paid off:** treating the agent as a **product with a backlog**, not a project. Teams that did this in year 1 already had `evaluations/`, `fixtures/`, and `docs/findings/` folders.

**Day-one choice that hurt:** putting the HR API behind APIM "in case we need it later." Two years in, nobody has needed APIM, but the resting cost has compounded and the operations team treats it as load-bearing.

---

## Year 3 — "agents everywhere, one rulebook"

**State of the estate:** 8–12 agents across HR, IT, Finance, Sales Ops, Legal-lite. ~6k MAU, ~300k messages/mo. Cross-agent calls. A growing shared library of tools (`get_employee`, `find_manager`, `book_room`).

**What gets added:**
- An **agent registry**. Which agents exist, who owns them, what tools they expose, what data they touch.
- A **shared identity & secrets posture**: managed identity everywhere, Key Vault references, no more function keys in connector definitions.
- **Per-environment governance**: dev/test/prod Power Platform environments, dev/test/prod Foundry projects, DLP policies per environment.
- **A platform team** (1–2 people) that owns the agent runtime, evaluations, FinOps reporting, and the HR API.
- **Voice / IVR** asks ("can the agent answer the after-hours HR line?"). Copilot Studio voice channel covers it cleanly. Pure-A and pure-C teams eat this one.

**What hurts (typical):**
- The HR API is no longer "the HR API" — it's "the people-data plane." Versioning becomes real. v1 endpoints are still wired into three custom connectors that nobody wants to touch.
- Long-running flows (UC3 onboarding) reveal **Dataverse table-design debt**. The shape that worked for 1k plans/year creaks at 50k.
- Evaluations diverge between platforms. Foundry has first-class evals; Copilot Studio's analytics are conversation-shaped, not model-shaped. Teams build a unified eval harness in their CI.
- Compliance asks for **PII redaction at the agent boundary**. Pure-B teams discover that Copilot Studio's redaction is per-channel, not per-tool-call. Mixed-D teams add it at the Functions backend and move on.

**Day-one choice that paid off:** picking a **substrate that lets HR makers ship 80% of changes**. Year-3 backlogs are dominated by phrasing tweaks, new approval branches, and new SharePoint sources — exactly what HR can do without engineering.

**Day-one choice that hurt:** any choice that *required* a compute floor (min-replica Container Apps, AI Search Basic, APIM Consumption baseline). At year-3 volumes the unit economics are fine, but the **22 months of resting cost** between year-1 launch and year-3 traction were dead money.

---

## Year 5 — "the agent is the org chart"

**State of the estate:** ~25 agents, agents-of-agents, an internal "agent of agents" router. Voice + chat + email-bot surfaces. Agentic workflows that span HR + IT + Finance for things like leaver/joiner. ~15k MAU, millions of messages/mo. New hires onboard *to the agent estate* on day one.

**What gets added:**
- An **internal developer platform** for agents — golden-path templates, shared evaluation pipelines, shared tool registry, shared observability.
- **Multi-region** for non-EU subsidiaries. Foundry + AOAI regional pinning. Power Platform geo selection (set once, expensive to undo).
- **Audit-grade traceability** — every tool call, every grounding, every model output stored for X years per a retention policy.
- **A formal tools team** (3–5 people) producing reusable, versioned, OpenAPI-described tools. The HR people-data plane is one of many.

**What hurts (typical):**
- The agents written in year 1 with v1-style conventions are now the legacy estate. Teams that followed conventions early have ~10 lines of diff to upgrade; teams that didn't have rewrites.
- Per-message Copilot Studio licensing meets traffic volume; FinOps re-evaluates surface choice for the chattiest agents. A few migrate to SDK-first; most don't.
- Foundry hosted-agent evolution (model versions, tool schemas) drifts from what the connectors expect; **schema-first integration** pays its dividend.
- The org realises the most valuable thing the platform produced isn't any single agent — it's **the people-data plane** and **the tool registry**. Both should have been first-class on day one.

**Day-one choice that paid off:** **OpenAPI everywhere.** Every backend, every connector, every tool — described in OpenAPI, versioned, in Git. This is the single highest-leverage discipline.

**Day-one choice that hurt:** putting too much logic *in the conversation layer*. Topics that contain business rules end up duplicated across agents; the platform team eventually moves them down into the people-data plane, but only after a year of pain.

---

## Cross-references in this repo

| Year | Reading |
|---|---|
| 0 — picking a path | [docs/decision-tree.md](decision-tree.md), [docs/comparison.md](comparison.md) |
| 1 — first six UCs | [docs/scenario.md](scenario.md), each solution's `README.md` |
| 2 — adding model-led reasoning | [mixed-agent/README.md](../mixed-agent/README.md), [docs/architecture/mixed.md](architecture/mixed.md) |
| 3 — operationalising | [docs/findings/](findings/) — read all four |
| 5 — platforming | this document |

---

## What the day-one choices actually are

Distilled from the timeline above. None of these are about which tool you pick *today* — they're about which **doors stay open** for years 1-5.

| # | Day-one choice | Cost of getting it right on day one | Cost of fixing in year 3 |
|---|---|---|---|
| 1 | **Schema-first backend** (OpenAPI in Git, semantic versioning, no slim swagger by hand) | one engineer-week | several engineer-months |
| 2 | **Compute that scales to zero** (Functions Consumption ≫ min-replica Container Apps, until you outgrow it) | a deploy-time decision | rewrites + 22 months of resting cost |
| 3 | **State in Dataverse, not Cosmos** (unless you have a *specific* reason for Cosmos) | a config decision | a migration |
| 4 | **Knowledge in SharePoint with generative answers, not AI Search** (until corpus or quality forces otherwise) | nothing | painless, but you carried €70/mo for two years for nothing |
| 5 | **Copilot Studio as the conversational surface** + targeted **connected agents** (Solution D) for code-first parts | adopt the mixed pattern from day one | rewrite the front door, retrain HR makers |
| 6 | **Managed solutions in prod**, source-controlled | a sprint of CI plumbing | a production outage |
| 7 | **Managed identity from day one**, no function keys in connectors | one extra deployment step | rotation incident at 2 a.m. |
| 8 | **Per-UC cost attribution** (App Insights custom dimensions, Foundry project tags) | a half-day | a re-instrumentation project |
| 9 | **Evaluation harness in CI** with a tiny seed dataset | a day | a quarter, after Legal asks |
| 10 | **Agent registry** (one markdown table is enough on day one) | an afternoon | a discovery exercise across the company |

## The one-page recommendation

If you're at day 0 and your shape looks roughly like Contoso's:

1. Adopt **Solution D (Mixed)** as the substrate. It costs no more than B on day one and saves you the year-2 migration.
2. Put your HR backend behind **OpenAPI in Git** with semver from commit one.
3. Use **SharePoint generative answers** for knowledge unless you can articulate why not.
4. Use **Dataverse** for state unless you can articulate why not.
5. Stand up the **evaluation harness** with two prompts before you stand up the second use case.
6. Write the **agent registry** README before you ship the second agent.
7. Wire **managed identity + Key Vault references** before the first production deploy.
8. Plan for **HR makers to own ≥ 60% of future changes** — because they will whether you plan for it or not.

Everything else can wait. These eight don't.
