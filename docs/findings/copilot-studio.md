# Findings — Copilot Studio

## What worked well

- Time-to-first-demo is unbeatable. Topics + generative answers cover UC1 with ~zero code.
- The Approvals connector is exactly the right primitive for UC2; the manager adaptive card is generated for you.
- `TransferConversation` plus a Teams HR queue is the most enterprise-ready human handoff in Microsoft's stack today (UC6).
- `pac solution pack`/`import` makes the whole agent — topics, flows, tables, connector, channels — reproducible from Git.

## What hurt

- Slim Custom Connector schemas — you have to model the API twice (FastAPI + slimmed swagger). Mismatch is a class of bugs.
- Power Fx + YAML topic syntax is its own thing; expression debugging is harder than Python.
- Generative answers behave differently when grounded on SharePoint vs uploaded files — pick one and stick with it.
- Long-running multi-actor work (UC3) splits across Topic + Agent Flow + scheduled flow + Dataverse — keep the diagram handy.

## Recommendations

- One Custom Connector per backend domain; don't pack unrelated APIs together (DLP gets messy).
- Persist anything you'd want a manager dashboard for in Dataverse; don't chase Cosmos parity.
- Use environment variables in flows, not hard-coded URLs/IDs; they survive solution import.
- Reserve code-first work (M365 Agents SDK or Foundry) for the few use cases that need it; mix via connected agents instead of porting everything.
