# Scenario — Contoso HR Concierge

## Company

**Contoso Ltd** is a fictional mid-size company:
- ~5,000 employees across 12 countries
- HQ in Seattle, US
- Hybrid work model
- Standard HRIS, learning platform, ticketing system, SharePoint-based handbook
- HR org: shared-services HR Operations + business-aligned HR Partners

## Personas

| Persona | Name (sample) | Pain point the agent solves |
|---|---|---|
| **Employee** | Aarav Patel | "I just need a fast answer or to start a process — I don't want to dig through SharePoint or email HR." |
| **People Manager** | Beatrice Lambert | "Approvals and onboarding tracking eat my calendar." |
| **HR Partner** | Carlos Mendes | "I want the easy questions deflected so I can focus on real cases." |
| **IT / Buddy** | Dana Okafor | "Onboarding tasks reach me late and out of order." |

## Six use cases

Each is implemented in **all three** technologies (UC × Technology = 18 implementations). Where a technology cannot do something cleanly, the limit is documented in [comparison.md](./comparison.md).

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

### UC6 — HR ticket triage & escalation
- **Trigger:** Employee describes a sensitive issue: harassment claim, payroll error, immigration question, etc.
- **Pattern:** Classify → answer if low-sensitivity & well-known → otherwise create a ticket and **hand off** to HR Partner with conversation transcript.
- **Participants:** Employee → HR Partner.
- **Success:** Sensitive cases never get auto-answered; HR Partner gets context-rich handoff.

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

## Success metrics for the demo

A successful demo run shows, for each technology:
1. UC1 produces a **cited** answer.
2. UC2 produces a **proactive Adaptive Card** to the manager and round-trips back.
3. UC3 produces tasks visible to **at least three different participants**.
4. UC4 produces **personalized** matches (not generic).
5. UC5 produces a **summary across multiple inputs**.
6. UC6 **does not auto-answer** sensitive cases and produces a real handoff artifact.
