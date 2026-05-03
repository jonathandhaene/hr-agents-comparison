# Findings — Mixed (Solution D)

## What worked well

- **Copilot Studio as the primary surface** keeps day-to-day evolution in HR's hands. Phrasing tweaks, new triggers, and approval wording stop being PRs.
- **Connected Foundry agent for the two model-led use cases** is the right shape — most of the value of Foundry (model + tools + evals) without taking on its full surface for things that are really CRUD.
- **Azure Functions Consumption** removed the resting cost of the backend. No container image rebuilds, no min-replicas to tune.
- **SharePoint generative answers** replaced AI Search for UC1 with no measurable quality loss for an internal handbook of this size (~150 pages). HR can update content in place.
- **`TransferConversation` to a Teams HR queue** is still the cleanest live-handoff in the Microsoft stack — works the same here as in pure Solution B.

## What hurt

- **Two connectors to maintain.** Each backend domain (HR API, Foundry agent) needs its own swagger/OpenAPI; mismatched schemas are a class of bugs unique to Power Platform.
- **Auth split between two surfaces.** The Functions key (HR API connector) and Foundry MI (agent connector) are configured in different places — document the wiring or new joiners will struggle.
- **Copilot Studio's `InvokeConnectorAction` doesn't stream Foundry token-by-token** the way a code-first Bot would. UC4's response shows up as a single message; for an internal tool this was acceptable.
- **Function key rotation** has to be coordinated with the connector's stored secret in Power Platform — no first-class binding between them yet.
- **Dataverse tables for onboarding/feedback are simpler than Cosmos but less queryable** for product analytics. If you need rich analytics, mirror the rows to a dataflow.

## Cost observations (informal)

Compared with pure Solution A in the same demo tenant over a week of internal use:

| Item | Solution A (M365 Agents SDK) | Solution D (Mixed) |
|---|---|---|
| Container Apps min replica | 1 (constant) | n/a |
| Cosmos serverless RU floor | yes | n/a |
| AI Search Basic | constant | n/a |
| APIM Consumption | constant overhead per req | n/a |
| Functions Consumption | n/a | ~zero idle |
| Foundry | n/a | per token only |

Total Azure resting cost dropped to a small App Insights + Storage tail. Power Platform per-message licensing applies on the Copilot Studio side.

## Recommendations

- Pick **Mixed** when the org is heavily M365/Power-licensed already and HR can own day-to-day changes — and only if a small (≤2) number of UCs really need model-led reasoning.
- Keep the Foundry connected agent **narrow** (≤4 tools). Once it grows beyond that, you're effectively building Solution C and should re-evaluate.
- Keep all UC state in Dataverse — don't reach for Cosmos just because the pure solutions used it.
- Document the connector key/MI wiring in `mixed-agent/README.md`; it's the one thing that drifts.
- If you outgrow `TransferConversation` (e.g., you need a custom handoff card), the cleanest evolution is to add an M365 Agents SDK skill as a *second* connected agent — keep Copilot Studio as the primary surface.
