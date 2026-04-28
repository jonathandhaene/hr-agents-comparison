# Choosing between M365 Agents SDK, Copilot Studio, and Foundry

Use this decision tree as a starting point. The repo intentionally implements each path *in isolation* — but production teams often **combine** technologies. That is acceptable; it's just out of scope for the demo so each path can be evaluated on its own merits.

> **Note on rendering:** GitHub, GitLab, and Foam render Mermaid natively. VS Code's built-in Markdown preview does **not** — install the [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid) extension to view these diagrams locally.

## Decision tree

![Decision tree](./img/decision-tree.svg)

<details><summary>Mermaid source</summary>

```mermaid
flowchart TD
    Start(["New agent ask"]) --> Q1{"Is the experience primarily knowledge Q&A + simple actions?"}
    Q1 -- Yes --> Q2{"Maker / power user will own day-to-day changes?"}
    Q2 -- Yes --> CPS["Copilot Studio"]
    Q2 -- No  --> Q3{"Hosted runtime, evaluations, and File Search are compelling?"}
    Q3 -- Yes --> FDY["Foundry hosted agent"]
    Q3 -- No  --> SDK["M365 Agents SDK"]

    Q1 -- No --> Q4{"Long-running, multi-actor workflow with proactive nudges?"}
    Q4 -- Yes --> Q5{"Approvals + Dataverse + Outlook fan-out cover it?"}
    Q5 -- Yes --> CPS
    Q5 -- No  --> SDK

    Q4 -- No --> Q6{"Bespoke conversation logic or deep Graph integration?"}
    Q6 -- Yes --> SDK
    Q6 -- No  --> Q7{"Want model-led tool use with built-in evals?"}
    Q7 -- Yes --> FDY
    Q7 -- No  --> CPS

    classDef pick fill:#0078D4,stroke:#003a6b,color:#ffffff,font-weight:bold
    class CPS,SDK,FDY pick
```

</details>

## Mixing them (out of scope here, common in practice)

This repository keeps the three implementations completely separate so you can compare them fairly. In real engagements, the patterns below are common and supported:

1. **Copilot Studio agent → calls an M365 Agents SDK skill** as a connected agent for the bespoke parts (e.g., live Graph handoff).
2. **Copilot Studio agent → calls a Foundry hosted agent** as a connected agent for advanced reasoning while keeping topics for the "happy path".
3. **Foundry hosted agent → calls Copilot Studio actions / flows** when you need approvals or Dataverse rows.
4. **M365 Agents SDK agent → embeds a Foundry agent client** as a tool for evaluation-graded reasoning while the SDK app keeps proactive Graph plumbing.

Choose one as the **primary surface** (the thing the user talks to) and let the others be invoked as tools or connected agents — don't duplicate the same workflow in two places.

## Anti-patterns (avoid)

- Re-implementing approvals in code when Copilot Studio's Approvals connector solves UC2 in a flow.
- Building bespoke RAG in code when File Search or Copilot Studio generative answers fit the corpus.
- Splitting a single workflow across all three technologies — pick a primary, invoke the others.
- Hand-editing the published Copilot Studio agent without exporting via `pac solution export` — divergence will bite you.
