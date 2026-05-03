# HR Agents — three-way comparison

Demonstrates the **same HR scenario** ("Zava HR Concierge") implemented three independent ways:

| Folder | Technology | Surfaces in |
|---|---|---|
| [m365-agent/](./m365-agent/) | Microsoft 365 Agents SDK (Python) | M365 Copilot, Teams |
| [copilot-studio-agent/](./copilot-studio-agent/) | Microsoft Copilot Studio (declarative) | M365 Copilot, Teams |
| [foundry-agent/](./foundry-agent/) | Microsoft Foundry — Hosted Agent (Python) inside a Foundry project | M365 Copilot, Teams |
| [mixed-agent/](./mixed-agent/) | **Mixed** — Copilot Studio primary + Foundry connected agent + Azure Functions backend | M365 Copilot, Teams |

The first three folders (A/B/C) are **completely independent** from each other so they can be compared on their own merits — same seven use cases, three pure implementations. The only shared thing is committed reference seed data in [`shared-fixtures/`](./shared-fixtures/), which each solution copies/loads at build time.

The fourth folder ([`mixed-agent/`](./mixed-agent/)) is the recommended **production starting point** for most teams: it deliberately combines Copilot Studio + Foundry to optimise for **lowest cost, lowest maintenance, highest flexibility for HR makers** while keeping advanced reasoning where it earns its keep. See [docs/architecture/mixed.md](./docs/architecture/mixed.md) and [docs/findings/mixed.md](./docs/findings/mixed.md).

## Scenario in one paragraph

Zava (a fictional specialty coffee retailer with 5,000 employees) wants an HR Concierge for **Employees, Managers, HR Partners, IT/Buddies**. All seven use cases (policy Q&A, time-off approval, onboarding orchestration, internal mobility, 360° feedback, ticket triage, and calibrated performance narrative generation) are implemented across the four solutions. UC7 uses a fine-tuned model deployment and is fully implemented in B, C, and D; Solution A uses a tool call to the same fine-tuned Foundry deployment. See [docs/scenario.md](./docs/scenario.md) and [docs/fine-tuning.md](./docs/fine-tuning.md).

## Quickstart

| | Local dev | Deploy |
|---|---|---|
| M365 Agents SDK | `cd m365-agent && make dev` | `gh workflow run m365-agent.yml` |
| Copilot Studio | Author in Copilot Studio portal; export with `pac solution unpack` into `copilot-studio-agent/solution/` | `gh workflow run copilot-studio.yml` |
| Foundry | `cd foundry-agent && make dev` | `gh workflow run foundry.yml` |
| **Mixed** | `cd mixed-agent && make dev` | `gh workflow run mixed.yml` |

See each solution's `README.md` for prerequisites.

## Documentation

- [docs/scenario.md](./docs/scenario.md) — personas, use cases (including UC7), sample dialogues
- [docs/comparison.md](./docs/comparison.md) — capability matrix per UC × technology
- [docs/technique-comparison.md](./docs/technique-comparison.md) — prompting vs RAG vs fine-tuning explained without jargon, mapped to all seven use cases
- [docs/fine-tuning.md](./docs/fine-tuning.md) — when fine-tuning adds value per UC, worked examples for UC6 triage classifier and UC7 performance narrative
- [docs/fine-tuning-why.md](./docs/fine-tuning-why.md) — stakeholder guide: why fine-tuning must be considered (C-Level, HR, DPO & CISO, Legal)
- [docs/public-sector-eu.md](./docs/public-sector-eu.md) — EU Public Sector sovereignty story (data residency, EU AI Act, NIS2, procurement)
- [docs/decision-tree.md](./docs/decision-tree.md) — when to choose what (incl. mixing guidance)
- [docs/timeline.md](./docs/timeline.md) — how an HR-agent estate evolves over 1/2/3/5 years and how that should shape your day-one choices
- [docs/architecture/](./docs/architecture/) — Mermaid diagrams per solution
- [docs/findings/](./docs/findings/) — build-time observations, gotchas, limits hit
- [docs/demo-script.md](./docs/demo-script.md) — exact prompts to run in M365 Copilot

## Repository layout

```
hr-agents/
├─ m365-agent/                 # Solution A
├─ copilot-studio-agent/       # Solution B
├─ foundry-agent/              # Solution C
├─ mixed-agent/                # Solution D — recommended mix
├─ shared-fixtures/            # Build-time seed data only
├─ docs/                       # Cross-cutting documentation
└─ .github/workflows/          # One workflow per solution
```

## Responsible AI

All three solutions handle employee data and HR policy. Anyone running this in production must:

- **Ground every generative answer** in retrieved context (policies, employee record, ticket history) and surface citations to the user. UC1 enforces this; do not loosen it for other UCs.
- **Never auto-action sensitive cases.** UC6 routes harassment / discrimination / mental-health signals straight to a human HR partner — that classifier and the human-handoff path are mandatory, not optional.
- **Mask PII in logs and traces.** Application Insights, Foundry traces, and Dataverse audit must not contain free-text descriptions of grievances.
- **Respect data residency.** Pin Microsoft Foundry to a region your HR data is allowed to leave. Use `GlobalStandard` only after legal sign-off; otherwise pin to a regional deployment.
- **Run the Microsoft Foundry safety evaluators** (Groundedness, Hate & Unfairness, Self-harm, Violence, Sexual, Protected Material, Indirect Attack) on a representative eval set before any release.
- **Keep humans in the loop** on irreversible actions (UC2 leave approval, UC3 access provisioning, UC6 escalation) — the workflows in this repo always do.
- **Disclose AI use** to employees and let them request a human alternative.

See Microsoft's [Responsible AI Standard](https://aka.ms/RAIStandard) and [Transparency Notes for Microsoft Foundry](https://learn.microsoft.com/legal/cognitive-services/openai/transparency-note).

## License

MIT — see [LICENSE](./LICENSE).
