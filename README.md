# HR Agents — three-way comparison

Demonstrates the **same HR scenario** ("Contoso HR Concierge") implemented three independent ways:

| Folder | Technology | Surfaces in |
|---|---|---|
| [m365-agent/](./m365-agent/) | Microsoft 365 Agents SDK (Python) | M365 Copilot, Teams |
| [copilot-studio-agent/](./copilot-studio-agent/) | Microsoft Copilot Studio (declarative) | M365 Copilot, Teams |
| [foundry-agent/](./foundry-agent/) | Microsoft Foundry — Hosted Agent (Python) inside a Foundry project | M365 Copilot, Teams |

Each folder is **completely independent**: its own backend, IaC, packaging, CI/CD workflow, and deploy target. The three solutions share **no runtime dependencies**. The only shared thing is committed reference seed data in [`shared-fixtures/`](./shared-fixtures/), which each solution copies/loads at build time.

> **Mixing is forbidden in code.** The decision tree in [docs/decision-tree.md](./docs/decision-tree.md) discusses honest "when to mix" guidance separately, for the reader.

## Scenario in one paragraph

Contoso Ltd (5,000 employees) wants an HR Concierge for **Employees, Managers, HR Partners, IT/Buddies**. The same six use cases (policy Q&A, time-off approval, onboarding orchestration, internal mobility, 360° feedback, ticket triage) are implemented in all three technologies. See [docs/scenario.md](./docs/scenario.md).

## Quickstart

| | Local dev | Deploy |
|---|---|---|
| M365 Agents SDK | `cd m365-agent && make dev` | `gh workflow run m365-agent.yml` |
| Copilot Studio | Author in Copilot Studio portal; export with `pac solution unpack` into `copilot-studio-agent/solution/` | `gh workflow run copilot-studio.yml` |
| Foundry | `cd foundry-agent && make dev` | `gh workflow run foundry.yml` |

See each solution's `README.md` for prerequisites.

## Documentation

- [docs/scenario.md](./docs/scenario.md) — personas, use cases, sample dialogues
- [docs/comparison.md](./docs/comparison.md) — capability matrix per UC × technology
- [docs/decision-tree.md](./docs/decision-tree.md) — when to choose what (incl. mixing guidance)
- [docs/architecture/](./docs/architecture/) — Mermaid diagrams per solution
- [docs/findings/](./docs/findings/) — build-time observations, gotchas, limits hit
- [docs/demo-script.md](./docs/demo-script.md) — exact prompts to run in M365 Copilot

## Repository layout

```
hr-agents/
├─ m365-agent/                 # Solution A
├─ copilot-studio-agent/       # Solution B
├─ foundry-agent/              # Solution C
├─ shared-fixtures/            # Build-time seed data only
├─ docs/                       # Cross-cutting documentation
└─ .github/workflows/          # One workflow per solution
```

## License

MIT — see [LICENSE](./LICENSE).
