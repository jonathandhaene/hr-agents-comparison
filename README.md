# HR Agents — three-way comparison

Demonstrates the **same HR scenario** ("Contoso HR Concierge") implemented three independent ways:

| Folder | Technology | Surfaces in |
|---|---|---|
| [m365-agent/](./m365-agent/) | Microsoft 365 Agents SDK (Python) | M365 Copilot, Teams |
| [copilot-studio-agent/](./copilot-studio-agent/) | Microsoft Copilot Studio (declarative) | M365 Copilot, Teams |
| [foundry-agent/](./foundry-agent/) | Microsoft Foundry — Hosted Agent (Python) inside a Foundry project | M365 Copilot, Teams |
| [mixed-agent/](./mixed-agent/) | **Mixed** — Copilot Studio primary + Foundry connected agent + Azure Functions backend | M365 Copilot, Teams |

The first three folders (A/B/C) are **completely independent** from each other so they can be compared on their own merits — same six use cases, three pure implementations. The only shared thing is committed reference seed data in [`shared-fixtures/`](./shared-fixtures/), which each solution copies/loads at build time.

The fourth folder ([`mixed-agent/`](./mixed-agent/)) is the recommended **production starting point** for most teams: it deliberately combines Copilot Studio + Foundry to optimise for **lowest cost, lowest maintenance, highest flexibility for HR makers** while keeping advanced reasoning where it earns its keep. See [docs/architecture/mixed.md](./docs/architecture/mixed.md) and [docs/findings/mixed.md](./docs/findings/mixed.md).

## Scenario in one paragraph

Contoso Ltd (5,000 employees) wants an HR Concierge for **Employees, Managers, HR Partners, IT/Buddies**. The same six use cases (policy Q&A, time-off approval, onboarding orchestration, internal mobility, 360° feedback, ticket triage) are implemented in all three technologies. See [docs/scenario.md](./docs/scenario.md).

## Quickstart

| | Local dev | Deploy |
|---|---|---|
| M365 Agents SDK | `cd m365-agent && make dev` | `gh workflow run m365-agent.yml` |
| Copilot Studio | Author in Copilot Studio portal; export with `pac solution unpack` into `copilot-studio-agent/solution/` | `gh workflow run copilot-studio.yml` |
| Foundry | `cd foundry-agent && make dev` | `gh workflow run foundry.yml` |
| **Mixed** | `cd mixed-agent && make dev` | `gh workflow run mixed.yml` |

See each solution's `README.md` for prerequisites.

## Documentation

- [docs/scenario.md](./docs/scenario.md) — personas, use cases, sample dialogues
- [docs/comparison.md](./docs/comparison.md) — capability matrix per UC × technology
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

## License

MIT — see [LICENSE](./LICENSE).
