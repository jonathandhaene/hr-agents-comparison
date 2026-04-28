# Findings — Microsoft 365 Agents SDK

## What worked well

- Full control over conversation state and proactive messaging is exactly what UC2 (manager Adaptive Card approval) and UC3 (multi-actor onboarding nudges) need.
- The SDK's `TurnContext.send_proactive` + stored conversation references give you durable, event-driven user experiences.
- Microsoft Graph access via the bot's managed identity makes UC6 (1:1 chat handoff) clean.
- M365 Agents Toolkit's `teamsapp.yml` removes most of the manifest + bot registration boilerplate.

## What hurt

- You build everything: routing, state, evals, dashboards. Plan for the unglamorous parts.
- Adaptive Card schemas drift between hosts (Teams vs M365 Copilot Chat) — test in both.
- Long-running workflows need a place to live (Cosmos checkpoints + a scheduled job). Without that, restarts lose progress.
- Manifest `copilotAgents.customEngineAgents` is the new shape for surfacing in M365 Copilot — older docs still describe Teams-only manifests.

## Recommendations

- Keep the agent process stateless. Persist *every* long-running thing in Cosmos.
- Treat per-channel rendering as a separate concern (consider a small `cards/` package).
- Use the Toolkit's `env/.env.{stage}` pattern; do not branch on environment in code.
- Add evals (LLM-as-judge or PromptFlow) early — the SDK gives you no opinion here.
