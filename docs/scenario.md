# Scenario — Zava HR Concierge

## Company

**Zava** is a fictional specialty coffee retailer and supplier (a play on "Java"):
- ~5,000 employees across 12 countries
- HQ in Seattle, US
- Hybrid work model (retail stores + corporate offices + roasting facilities)
- Standard HRIS, learning platform, ticketing system, SharePoint-based handbook
- HR org: shared-services HR Operations + business-aligned HR Partners

## Personas

| Persona | Name (sample) | Pain point the agent solves |
|---|---|---|
| **Employee** | Aarav Patel | "I just need a fast answer or to start a process — I don't want to dig through SharePoint or email HR." |
| **People Manager** | Beatrice Lambert | "Approvals and onboarding tracking eat my calendar." |
| **HR Partner** | Carlos Mendes | "I want the easy questions deflected so I can focus on real cases." |
| **IT / Buddy** | Dana Okafor | "Onboarding tasks reach me late and out of order." |

## Seven use cases

UC1–UC6 are implemented in **all four** solutions (A/B/C/D). UC7 (performance narrative) is implemented in B, C, and D using a fine-tuned model deployment, and in A via a tool call to the same deployment. Where a technology cannot do something cleanly, the limit is documented in [comparison.md](./comparison.md).

UC7 (below) uses a fine-tuned model to generate grade-calibrated performance narratives. It is fully implemented in Solutions B, C, and D, and in A via a tool call to the same fine-tuned Foundry deployment. See [docs/fine-tuning.md](./fine-tuning.md) for the full fine-tuning analysis across all UCs.

### UC1 — Policy & benefits Q&A
- **Trigger:** Employee asks "How many vacation days do I get after 5 years?" / "What does our parental leave policy cover?"
- **Pattern:** Retrieval-augmented generation over the HR handbook + policy PDFs.
- **Participants:** Employee.
- **Success:** Cited answer with policy section reference.

### UC2 — Time-off request with manager approval
- **Trigger:** Employee says "Request 5 days off starting June 10."
- **Pattern:** Slot-filling → balance check → submit request → **proactive notification to manager** (Adaptive Card with Approve/Reject) → confirmation back to employee.
- **Participants:** Employee, Manager.
- **Success:** Manager receives an actionable card; decision flows back to employee within the same conversation.

### UC3 — New-hire onboarding orchestration
- **Trigger:** Hiring manager says "Start onboarding for Eva Schmidt, Software Engineer, starting May 5."
- **Pattern:** Long-running orchestration:
  1. Generate onboarding plan from a template.
  2. Assign tasks: laptop & accounts to **IT**, welcome chat to **Buddy**, kickoff agenda to **Manager**, learning checklist to **New hire**.
  3. Track progress; nudge owners on overdue tasks.
  4. Notify HR Partner when all critical tasks are done.
- **Participants:** New hire, Manager, IT, Buddy, HR Partner.
- **Success:** All four humans get the right notifications at the right time; status visible to manager on demand.

### UC4 — Internal mobility / career coach
- **Trigger:** Employee says "I'm looking for my next role — something in product management."
- **Pattern:** Profile-aware tool calls (skills, tenure, location) → search internal jobs → LLM-drafted pitch / cover summary → optional "express interest" action.
- **Participants:** Employee (and indirectly the recruiter through the express-interest action).
- **Success:** Two or three matched roles + a personalized pitch the employee can send.

### UC5 — 360° performance feedback collection
- **Trigger:** Employee or manager initiates "Run a 360 for [name] for the H1 review."
- **Pattern:** Agent suggests reviewer set (peers/reports/skip-level) → sends individual feedback prompts → collects responses → summarizes themes.
- **Participants:** Employee being reviewed, Manager, 3–6 peers.
- **Success:** A balanced, theme-grouped summary delivered to the manager.
- **Fine-tuning note:** Summary format and calibration language must be consistent across all employees. A fine-tuned model trained on HR-approved summary examples significantly reduces format variation and the equity risk of inconsistent specificity. See [docs/fine-tuning.md](./fine-tuning.md).

### UC6 — HR ticket triage & escalation
- **Trigger:** Employee describes a sensitive issue: harassment claim, payroll error, immigration question, etc.
- **Pattern:** Classify → answer if low-sensitivity & well-known → otherwise create a ticket and **hand off** to HR Partner with conversation transcript.
- **Participants:** Employee → HR Partner.
- **Success:** Sensitive cases never get auto-answered; HR Partner gets context-rich handoff.
- **Fine-tuning note:** The sensitivity classifier is a safety control. A base model with a prompt is unstable across rephrasing; a fine-tuned classifier is the recommended production approach for the `HARASSMENT/CRITICAL` and `ER/HIGH` categories. See [docs/fine-tuning.md](./fine-tuning.md) for the worked example.

### UC7 — Calibrated performance narrative generation *(fine-tuning use case)*
- **Trigger:** Manager says "Draft a performance narrative for [employee name] for the H1 review."
- **Pattern:** Inputs (employee grade + tenure, UC5 360 summary, manager's bullet notes) → fine-tuned model drafts a grade-level-calibrated narrative → manager reviews and edits in-conversation → manager approves → narrative submitted to review system; HR Partner copy sent for calibration session.
- **Participants:** Manager (primary author), HR Partner (calibration).
- **Success:** Manager receives a draft narrative calibrated to the employee's grade level and Zava's competency framework; the manager's edits are minor; the calibration committee can compare narratives across employees without systematic wording bias.
- **Why fine-tuning is required:** Without it, different managers receive different quality and length of drafts for employees at the same grade. This creates an equity risk that HR Legal cannot accept. A model fine-tuned on HR-approved narratives from prior cycles produces consistent grade-level language, consistent specificity, and consistent structure. See [docs/fine-tuning.md](./fine-tuning.md) for the full worked example.

## Sample dialogues

### UC2 — Time-off

**Employee (Aarav)** → "Can I take June 10–14 off?"

**Agent** → "You currently have **17 days** vacation balance and there are no team conflicts that week. I'll send a request to **Beatrice Lambert** for approval. OK?"

**Aarav** → "Yes."

**Agent** → "Sent. I'll notify you when Beatrice responds."

*(Beatrice receives a card: "Approve Aarav's vacation request for June 10–14? [Approve] [Reject] [Need more info]")*

**Beatrice** → *clicks Approve*

**Agent → Aarav** → "Beatrice approved your time-off request. Calendar invite created. Have a great trip!"

### UC6 — Sensitive escalation

**Employee** → "I want to report something that happened with a colleague last week."

**Agent** → "I'm sorry that happened. This sounds like something an HR Partner should handle directly and confidentially. I won't ask you for details here. I've created **case INC-1042** and pinged **Carlos Mendes** (your HR Partner). Carlos will reach out within 1 business day. Would you like a Teams chat opened with Carlos now?"

### UC7 — Performance narrative (fine-tuning)

**Beatrice (Manager)** → "Draft a performance narrative for Aarav Patel for the H1 review."

**Agent** → "Here's a draft calibrated for a **Senior Software Engineer (L5)** narrative, based on his H1 360 feedback and your notes:

---
*Aarav delivered the Payments v3 API ahead of schedule while coordinating with three cross-functional teams, demonstrating strong ownership and stakeholder management at the L5 level. Peer feedback consistently highlights his ability to simplify complex technical trade-offs for non-engineering partners. One area of focus for H2: extending his impact beyond the immediate team by sharing design patterns more broadly.*

---

Does this reflect your assessment? You can edit the draft directly or ask me to adjust the tone, specificity, or any specific section."

**Beatrice** → "Make the first sentence more specific about the business impact."

**Agent** → "Updated: *Aarav delivered the Payments v3 API three weeks ahead of schedule, unblocking the Q2 merchant launch and directly contributing to €2M in new payment volume.* Does that work?"

**Beatrice** → "Yes, submit it."

**Agent** → "Submitted to the H1 2026 review record. Carlos Mendes (HR Partner) has a copy for the calibration session."

## Success metrics for the demo

A successful demo run shows, for each technology:
1. UC1 produces a **cited** answer.
2. UC2 produces a **proactive Adaptive Card** to the manager and round-trips back.
3. UC3 produces tasks visible to **at least three different participants**.
4. UC4 produces **personalized** matches (not generic).
5. UC5 produces a **summary across multiple inputs**.
6. UC6 **does not auto-answer** sensitive cases and produces a real handoff artifact.
7. UC7 (fine-tuning path) produces a **grade-level-calibrated narrative** that the manager approves with minor edits; the calibration committee can compare narratives across employees without systematic wording differences.
