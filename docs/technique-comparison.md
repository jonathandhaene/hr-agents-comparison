# Prompting, RAG, and fine-tuning — what they mean for HR, without the jargon

Three different levers. More than one can be active at the same time. The question for
each use case is: which combination is sufficient, and which is required for safety or
equity?

---

## The three levers in plain language

### Lever 1 — Prompting

**What it is.** You write the AI's "job description" in plain text. You tell it to act
like an HR assistant, answer concisely, never guess, always cite a source, and hand off
sensitive topics to a human. The AI reads your instructions and follows them when it
answers.

**Analogy.** A well-educated new contractor on their first day. They are capable, but
they only know what you told them in the briefing. Ask them about Zava's
parental-leave policy and they will produce a plausible-sounding answer — because they
never read your handbook. The more detailed your briefing, the better they perform, but
they still cannot quote facts they were never given.

**Best for.** Tasks where the instructions alone define what "good" looks like:
slot-filling, conversation flow, confirmation messages, greeting style. Prompting is
always present — every other technique builds on top of it.

**Not enough when.** The answer requires facts the model was never trained on (your
policies, your grades, your ticket categories), or when you need the *same* answer
regardless of how the question is phrased.

---

### Lever 2 — RAG (Retrieval-Augmented Generation)

**What it is.** Before the AI answers, the system searches your own document library
(policy PDFs, handbooks, job descriptions, benefits guides) and passes the relevant
excerpts to the AI alongside the question. The AI answers from *your* documents — not
from its training.

**Analogy.** Same contractor, but now they carry a searchable copy of all your handbooks.
Ask about parental leave and they look it up, quote the relevant paragraph, and tell you
the section number. They are reliable for "what does the policy say" — but they still
cannot classify a harassment report or write a calibrated performance narrative from
memory.

**Best for.** Policy Q&A, benefits questions, job-matching from an internal vacancy
catalogue, any question whose correct answer lives in a document you control and update.

**Not enough when.** The task is classification (the answer is a label, not a document
excerpt), or when you need consistent *language and format* across employees — not just
consistent facts.

---

### Lever 3 — Fine-tuning

**What it is.** You collect examples of the AI doing the task exactly right — HR-approved
360° summaries, correctly classified tickets, grade-calibrated performance narratives.
Those examples are used to update the model so it produces your standard by default,
rather than a generic approximation.

**Analogy.** Not a contractor, but a new hire who spent their first month shadowing your
best HR Operations analyst. They have internalised *how Zava handles things* — the
exact language for a critical escalation, the structure of a Senior Software Engineer
narrative, the difference between an immigration question and a payroll question. They
do not need to look it up; it is part of how they think.

**Best for.** Classification tasks that must be stable regardless of how the employee
phrases the input; generation tasks where format, length, and grade calibration must be
consistent across all employees.

**Not enough when.** You do not yet have approved examples to train on (dataset curation
takes 200–500 hours of HR Operations time), or the task is simple enough that a good
prompt and the right document already cover it.

---

## How the three levers combine in practice

All three levers can be active at the same time. Most production HR agents use:

- **Prompting** everywhere — defines behaviour, tone, and format constraints.
- **RAG** for knowledge-grounded use cases (UC1, UC4).
- **Fine-tuning** for safety-critical and equity-critical use cases (UC5, UC6, UC7).

The key insight is that RAG and fine-tuning solve *different* problems. RAG brings
external facts inside the conversation. Fine-tuning shapes *how the model reasons about
and communicates* those facts once they arrive. For most HR use cases you need both.

---

## Mapping to the seven use cases

| Use case | Prompting alone | + RAG | + Fine-tuning | Bottom line |
|---|---|---|---|---|
| **UC1** Policy & benefits Q&A | ⚠️ Model guesses when the policy is not in its training data | ✅ Grounded, cited answer | Optional | RAG is the primary control. Fine-tuning can standardise citation phrasing but is not required on day one. |
| **UC2** Time-off approval | ✅ Slot-filling and confirmation messages are reliable | Not needed | Not needed | The model's role is structural: extract dates, check a balance, confirm. Prompting is sufficient. |
| **UC3** Onboarding orchestration | ✅ Plan text from a template is reliable | Not needed for plan text; useful if role/IT catalogues are retrieved | Optional | Template-driven plan generation works well with prompting. Fine-tuning adds value once you accumulate 200+ manager-edited plan pairs from real cycles. |
| **UC4** Internal mobility | ⚠️ Generated pitch is generic, not calibrated to Zava grade levels | ✅ Relevant job matches from internal catalogue | **Recommended** | RAG finds the right jobs; fine-tuning makes the pitch language match Zava's competency model and grade vocabulary. |
| **UC5** 360° feedback summary | ⚠️ Format and specificity vary across employees — equity risk | Not the primary control | **Required for equity** | Two employees at the same grade must receive summaries of equal depth. A fine-tuned model is the documented standard; a prompted base model produces variation that HR Legal cannot defend. |
| **UC6** Triage & escalation | ⚠️ Classification drifts across rephrasing — safety risk | Not the primary control | **Required for safety** | A harassment signal must be caught regardless of how the employee phrases it. A fine-tuned classifier is stable across paraphrasing; a prompted model is not. |
| **UC7** Performance narrative | ⚠️ Generic draft, not grade-calibrated; managers from different teams produce inconsistent results | Not the primary control | **Core value proposition** | Consistent, grade-calibrated narratives across all managers is the entire point of this use case. Fine-tuning is not optional. |

---

## The practical sequence for most organisations

Most teams should **not** start with fine-tuning. Dataset curation takes months and
requires HR's active involvement. The practical sequence is:

### Phase 1 — Prompting + RAG (Day one to Month 3)

UC1, UC2, and UC3 work well from day one with prompting and RAG. Stand these up first:

- Wire UC1 to your SharePoint policy library (generative answers, or AI Search for larger
  corpora).
- Implement UC2 as a slot-filling flow with a manager-approval card.
- Implement UC3 as a template-driven orchestration with Dataverse state.

**Start the fine-tuning dataset curation in parallel**, even though you do not need it
yet. Ask HR Operations to begin pulling historical ticket classifications (for UC6) and
past 360 summaries (for UC5) in the background. Curation takes longer than training.

### Phase 2 — Fine-tune for safety (Month 3–6)

Once HR Operations has 200–350 labelled ticket examples, fine-tune the UC6 sensitivity
classifier on `gpt-4o-mini`. This is the safety-critical step:

- Block any deployment where `HARASSMENT_recall` falls below 0.99.
- Add UC4 and UC5 to the agent; UC5 can run on a prompted base model at this stage —
  communicate to HR that the summary format will vary until the fine-tuned model is ready.

### Phase 3 — Fine-tune for equity (Month 6–12, aligned to a review cycle)

Once you have 50–150 approved 360 summaries from a real review cycle, fine-tune for
UC5. UC7 follows naturally — performance narratives share the same fine-tuning
infrastructure as UC5.

After this phase all seven use cases are running on the combination of levers they
require. From here, the work is evaluation, dataset refresh, and expansion — not
architectural change.

---

## Quick reference

| Technique | What it costs | What it gives you | When to use it |
|---|---|---|---|
| **Prompting** | Near zero | Behaviour, tone, format constraints | Always — it is the baseline |
| **RAG** | Index maintenance + retrieval compute | Factual accuracy grounded in your documents | UC1, UC4, any knowledge-grounded UC |
| **Fine-tuning** | 200–500 hrs of HR curation + tens of euros of compute | Consistent classification and generation calibrated to your standard | UC5, UC6, UC7 — where variation is a liability |

---

## Cross-references

| Topic | Document |
|---|---|
| Seven use cases described | [docs/scenario.md](scenario.md) |
| Per-UC fine-tuning analysis | [docs/fine-tuning.md](fine-tuning.md) |
| Stakeholder guide to fine-tuning | [docs/fine-tuning-why.md](fine-tuning-why.md) |
| Technology capability matrix | [docs/comparison.md](comparison.md) |
| EU public-sector day-one recommendation | [docs/public-sector-eu.md](public-sector-eu.md) |
| Timeline and day-one choices | [docs/timeline.md](timeline.md) |
