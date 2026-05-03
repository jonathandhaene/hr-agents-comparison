# Demo script — Zava HR Concierge (three-way comparison)

A 25-minute walkthrough that shows the *same seven* HR use cases in **M365 Copilot Chat** (and Teams) across three independent implementations. Switch between agents in M365 Copilot Chat using the agent picker.

> **Setup:** Sign in as Aarav Patel (E001), Beatrice Lambert (E010), Carlos Mendes (H001). Have the three agents pinned: "HR Concierge (M365 SDK)", "HR Concierge (Copilot Studio)", "HR Concierge (Foundry)".

## 0. Framing (1 min)

> "Same scenario. Same surface — M365 Copilot Chat. Three completely separate builds. We'll compare cost, fit, and operational shape."

## 1. UC1 Policy Q&A (3 min)

For each agent, ask: *"What's our parental leave policy?"*

- **A (SDK)** answers from Azure AI Search; cite the policy file in brackets.
- **B (Copilot Studio)** answers from SharePoint with numbered citations.
- **C (Foundry)** answers from File Search with inline citations.

Talking point: same answer, three retrieval engines.

## 2. UC2 Time-off approval (5 min)

As **Aarav (E001)** in Copilot Chat:

> "I'd like vacation 2026-06-10 to 2026-06-14."

- **A** posts an Adaptive Card to **Beatrice's** Teams. Switch user → click Approve → Aarav gets confirmation.
- **B** Approvals connector pings Beatrice with the standard Approvals card. Approve.
- **C** confirms intent in chat, requests submission, then surfaces the request id; manager approves via the same agent in their Copilot.

Talking point: HITL primitives — A=custom, B=Approvals connector, C=tool calls.

## 3. UC3 Onboarding (5 min)

As **Beatrice (E010)**:

> "Start onboarding for Eva Schmidt, Software Engineer, starting 2026-05-05."

Show the plan in each agent. Then — for A and B — tail the scheduled tick logs to show the proactive reminders flowing to IT (Dana), Buddy (Sofia), New hire (Eva). For C, surface Foundry's thread view to show progress across days.

## 4. UC4 Internal mobility (3 min)

As **Aarav**: *"What internal jobs match my profile? I'm interested in product management."*

All three return ranked matches and a short pitch. Show the difference in pitch tone (deterministic prompt vs generative answer vs Agent Framework instructions).

## 5. UC5 360° feedback (3 min)

As **Beatrice**: *"Open a 360 feedback request for Liam (E003)."*
Then a few minutes later: *"Summarize FBR-XXXXXXXX."*

Highlight that A and C synthesise via Microsoft Foundry, B via Copilot Studio's generative summary.

## 6. UC6 Triage & escalation (4 min)

As **Aarav**:

> "I'd like to report harassment by my manager."

All three agents:
- Do **not** auto-answer.
- Create an INC ticket.
- **B** transfers conversation live to HR queue (Carlos).
- **A** opens a 1:1 Teams chat between Aarav and Carlos via Graph.
- **C** confirms case + assigned partner; escalation tool fires.

Talking point: same policy, three handoff implementations.

## 7. UC7 Performance narrative (3 min) — fine-tuning path

As **Beatrice (E010)**:

> "Draft a performance narrative for Aarav Patel for the H1 review."

- **A (SDK)** calls the fine-tuned Foundry deployment directly via a tool call; returns a grade-calibrated draft.
- **B (Copilot Studio)** topic collects manager notes, calls `/narratives/draft` via Custom Connector; generative answers node surfaces the result; manager approves in-chat.
- **C (Foundry)** tool call → `draft_performance_narrative` → fine-tuned model; agent loops until manager types "approve" → `submit_performance_narrative`.
- **D (Mixed)** topic delegates to the Foundry connected agent; same fine-tuned model as C; Copilot Studio topic unchanged when model is updated.

Talking point: same equity control (grade-calibrated language), four implementations ranging from full code-control (A/C) to near-zero-code (B/D).

## 8. Wrap (2 min)

Open `docs/comparison.md` and `docs/decision-tree.md` side-by-side and align on the recommendation per scenario class.
