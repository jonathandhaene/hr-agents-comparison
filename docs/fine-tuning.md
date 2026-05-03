# Fine-tuning — when it adds value and when it doesn't

## The HR consistency problem

HR decisions affect people's livelihoods. An HR agent that tells two employees in identical situations different things is a compliance risk, a trust risk, and — in the worst case — a discrimination risk. That requirement for **consistency and predictability** is the lens through which this document evaluates fine-tuning.

Base models are general-purpose. They produce plausible outputs, but plausible is not the same as *consistent*. For a consumer app, slight output variation is acceptable. For an HR system handling pay questions, sensitive escalations, or performance narratives that feed into promotion decisions, variation is a liability. Fine-tuning moves the output distribution closer to the company's calibrated standard — not by replacing grounding or retrieval, but by shaping **how** the model interprets and frames what it retrieves.

> **When fine-tuning helps:** classification tasks that must be stable across rephrasing, generation tasks where company-specific vocabulary or format consistency matters, and any task where you can collect a labeled "gold standard" dataset from HR.
>
> **When prompting + RAG is enough:** tasks where the answer is entirely in the retrieved document (just return the citation), low-stakes formatting variation that HR can tolerate, and early-stage UCs where you don't yet have enough labeled data to fine-tune safely.

---

## Per use-case analysis

### UC1 — Policy & benefits Q&A

| Dimension | Assessment |
|---|---|
| Primary pattern | RAG over SharePoint or AI Search |
| Fine-tuning value | **Low** |
| Reason | The answer is in the retrieved document. The model's job is to quote or paraphrase, not to recall facts from training. Fine-tuning the citation format is achievable but can also be handled with a strong system prompt. |
| When to revisit | If you have a large library of Q&A pairs that human HR reviewed and approved (e.g., a legacy FAQ database), fine-tuning on those pairs teaches the model *how* Zava HR answers — not just what it says. This raises the bar above RAG alone for ambiguous questions. |

### UC2 — Time-off request with manager approval

| Dimension | Assessment |
|---|---|
| Primary pattern | Slot-filling → balance check → workflow → approval card |
| Fine-tuning value | **Low** |
| Reason | This use case is structural: slot extraction + API call + card rendering. The LLM's generative contribution is small (confirmation phrasing). Prompting is more than sufficient. |
| When to revisit | If the agent must interpret unusual phrasings like "I need time for a religious observance" and distinguish them from vacation requests, a classifier fine-tuned on annotated examples adds reliability. |

### UC3 — New-hire onboarding orchestration

| Dimension | Assessment |
|---|---|
| Primary pattern | Long-running orchestration; template-driven plan generation |
| Fine-tuning value | **Low–Medium** |
| Reason | Onboarding plan generation is template-driven. A structured template + few-shot prompting is usually sufficient for plan text. |
| When to revisit | If Zava generates hundreds of onboarding plans per month and HR periodically reviews and edits the generated plans, those edits are a gold-standard fine-tuning dataset. After 200–500 such pairs, a fine-tuned model learns the company's onboarding language conventions and reduces HR edit time. |

### UC4 — Internal mobility / career coach

| Dimension | Assessment |
|---|---|
| Primary pattern | Profile-aware retrieval + LLM-generated pitch |
| Fine-tuning value | **Medium** |
| Reason | The generated pitch must be aligned with Zava's internal career framework (grade-level language, competency model, tone). A base model generates plausible pitches but may use language above or below the employee's grade, or reference generic skills rather than Zava's competencies. |
| When to revisit | Once you have approved pitches from previous successful internal moves, use those as fine-tuning examples. The delta in pitch quality and manager perception is measurable in user testing. |
| Interaction with UC7 | UC4 pitch generation and UC7 performance narrative generation share the same "calibrated career language" problem; a single fine-tuned model can serve both. |

### UC5 — 360° performance feedback summary

| Dimension | Assessment |
|---|---|
| Primary pattern | Fan-out to reviewers → collect responses → LLM summary |
| Fine-tuning value | **High** |
| Reason | Feedback summaries are legally and ethically sensitive. Two employees at the same grade level must receive summaries in the same format, with the same degree of specificity, and with the same standards for what counts as "balanced." A base model with a prompt produces inconsistent specificity: sometimes three bullet points, sometimes two paragraphs, sometimes an oddly positive framing that does not reflect a 2/5 collaboration score. Fine-tuning on HR-approved summary pairs standardises the output format and the calibration language. |
| Dataset source | HR typically has 1–3 prior 360 cycles with manager-reviewed summaries. That is 50–300 labelled examples — enough for a supervised fine-tune. |
| Risk without it | Employees who receive richer, more specific summaries than peers may perceive bias. HR Legal will ask why Employee A's summary is three paragraphs and Employee B's is seven. A fine-tuned model is auditable: the fine-tuning dataset is the evidence of consistent calibration. |

### UC6 — HR ticket triage & escalation

| Dimension | Assessment |
|---|---|
| Primary pattern | Classify sensitivity → auto-answer or escalate |
| Fine-tuning value | **High** |
| Reason | The classifier is a safety control. Missing a `HARASSMENT / CRITICAL` signal and allowing the agent to auto-answer is a compliance failure. Missing an `ER / HIGH` signal and routing it to the policy Q&A path is a trust failure. A prompted base model is sensitive to rephrasing: "my manager makes me feel uncomfortable" may be classified differently on different runs. A fine-tuned classifier is stable across rephrasing, across languages, and across the edge cases that HR Operations has seen in real tickets. |
| Dataset source | The `ticket_categories.json` fixture seeds the label schema. Historical HR tickets (anonymised) are the fine-tuning signal. Even 200–300 labelled examples per category produce a meaningful improvement in precision/recall on edge cases. |
| Worked example | See [Worked example: UC6 fine-tuned triage classifier](#worked-example-uc6-fine-tuned-triage-classifier) below. |

---

## Worked example: UC6 fine-tuned triage classifier

### Goal

Replace the prompted classification call in `GET /tickets/classify` with a fine-tuned model that returns a stable `{category_id, sensitivity, escalate_immediately}` triple.

### Why not just prompt?

The existing `ticket_categories.json` has seven categories and four sensitivity levels. A base model with a prompt classifies correctly on easy cases but drifts on edge cases:

- *"My manager keeps commenting on how I dress"* — sometimes `ER/HIGH`, sometimes `HARASSMENT/CRITICAL`. The correct answer under most codes of conduct is `HARASSMENT/CRITICAL`.
- *"I got a letter about my work permit"* — sometimes `PAYROLL`, sometimes `IMMIGRATION`. The correct answer is `IMMIGRATION/HIGH`.
- *"I've been struggling a lot lately"* — could be `ER`, could be a mental-health signal that should trigger the same immediate-escalation path as `HARASSMENT`. A fine-tuned model trained on HR's real handling of these cases learns this boundary; a prompted model guesses.

### Dataset shape

```jsonl
{"messages": [
  {"role": "system", "content": "Classify the HR ticket. Return JSON: {\"category_id\": \"...\", \"sensitivity\": \"low|medium|high|critical\", \"escalate_immediately\": true|false}"},
  {"role": "user",   "content": "My manager keeps commenting on how I dress and it makes me feel uncomfortable."},
  {"role": "assistant", "content": "{\"category_id\": \"HARASSMENT\", \"sensitivity\": \"critical\", \"escalate_immediately\": true}"}
]}
{"messages": [
  {"role": "system", "content": "Classify the HR ticket. Return JSON: {\"category_id\": \"...\", \"sensitivity\": \"low|medium|high|critical\", \"escalate_immediately\": true|false}"},
  {"role": "user",   "content": "I got a renewal notice for my work permit, can HR help?"},
  {"role": "assistant", "content": "{\"category_id\": \"IMMIGRATION\", \"sensitivity\": \"high\", \"escalate_immediately\": false}"}
]}
```

Each line is one HR ticket (user message) + the HR Operations team's agreed classification (assistant message). Collect 50–100 examples per category — 350–700 total for the full schema.

### Fine-tuning on Microsoft Foundry

Microsoft Foundry supports supervised fine-tuning on `gpt-4o-mini` (and `gpt-4o`). Use `gpt-4o-mini` for the classifier: the task is classification, not generation, and the smaller model is faster and cheaper per call.

```bash
# 1. Upload training file
az cognitiveservices account deployment list \
  --name <foundry-resource> --resource-group <rg>   # verify the base model is available

openai api fine_tuning.jobs.create \
  --training-file tickets_train.jsonl \
  --validation-file tickets_val.jsonl \
  --model gpt-4o-mini-2024-07-18 \
  --suffix "hr-triage-v1"
```

In Foundry, register the fine-tuned deployment alongside `gpt-4o` for generation tasks:

```yaml
# foundry-agent/agent.yaml  (partial)
models:
  classifier: hr-triage-v1          # fine-tuned gpt-4o-mini
  generator: gpt-4o                 # base model for UC4/UC5 generation
```

### Integration with Solutions A/B/C/D

| Solution | Integration point |
|---|---|
| A (M365 Agents SDK) | Replace the `classify_ticket()` tool call with the fine-tuned deployment endpoint. |
| B (Copilot Studio) | Update the HR API Custom Connector action `POST /tickets/classify` to call the fine-tuned model. No topic changes needed. |
| C (Foundry) | Register the fine-tuned model as a secondary deployment; swap the classifier tool. |
| D (Mixed) | Same as B — the change is entirely in the Azure Functions backend; the Copilot Studio topic and flow are unchanged. |

### Evaluation gate

Add an eval fixture to `evaluations/uc6_classifier/`:

```
evaluations/
  uc6_classifier/
    gold_set.jsonl       # 80 held-out labelled examples
    run_eval.py          # calls the classifier, computes precision/recall per category
    thresholds.json      # {"HARASSMENT_recall": 0.99, "overall_precision": 0.92}
```

Block any deployment where `HARASSMENT_recall` drops below 0.99. Missing one harassment signal in a thousand is too many.

---

## UC7 — Calibrated Performance Narrative Generation *(new use case)*

> This use case is not implemented in the A/B/C/D solutions but is a natural next step once UC5 is running and fine-tuning infrastructure is in place.

### Problem

After 360° feedback is collected (UC5), the **manager** must write a performance narrative — the free-text summary that feeds into the formal review record, calibration sessions, and (for promotion cases) the promotion document. Left to their own devices, managers produce narratives that vary enormously in length, vocabulary, and grade-level calibration. The calibration committee cannot compare "Eva Schmidt consistently delivers high-quality software" with "Aarav Patel demonstrates exceptional technical judgment and cross-functional leadership at the senior level" — the second reads like a senior-level candidate and the first does not, even if Eva's actual performance is equivalent. This is an equity and legal exposure issue.

### Pattern

1. **Inputs:** employee profile (grade, tenure, function), 360 feedback responses (from UC5), manager's bullet-point notes.
2. **Generation:** a fine-tuned model drafts a narrative calibrated to the employee's grade level and Zava's competency framework.
3. **Human review:** the manager reads, edits, and approves the draft before it is submitted to the review system. The agent presents a diff of any manager edits back to the manager before final submit.
4. **Participants:** Manager (primary), HR Partner (secondary — receives a copy for calibration).
5. **Success:** the calibration committee can compare narratives across employees without systematic wording bias introduced by individual managers.

### Sample dialogue

**Beatrice (Manager)** → "Draft a performance narrative for Aarav Patel for the H1 review."

**Agent** → "Here's a draft based on Aarav's H1 360 feedback and your notes. This is calibrated for a **Senior Software Engineer (L5)** narrative.

---

*Aarav delivered the Payments v3 API ahead of schedule while coordinating with three cross-functional teams, demonstrating strong ownership and stakeholder management at the L5 level. Peer feedback consistently highlights his ability to simplify complex technical trade-offs for non-engineering partners. One area of focus for H2: extending his impact beyond the immediate team by sharing design patterns more broadly.*

---

Does this reflect your assessment? You can edit the draft directly or ask me to adjust the tone, specificity, or any specific section."

**Beatrice** → "Make the first sentence more specific about the business impact."

**Agent** → "Updated: *Aarav delivered the Payments v3 API three weeks ahead of schedule, unblocking the Q2 merchant launch and directly contributing to €2M in new payment volume.*

Does that work?"

**Beatrice** → "Yes, submit it."

**Agent** → "Submitted to the H1 2026 review record. Carlos Mendes (HR Partner) has a copy for the calibration session."

### Fine-tuning dataset for UC7

The dataset for UC7 overlaps with UC5: HR already owns approved narratives from past review cycles. The label structure is:

```jsonl
{"messages": [
  {"role": "system",    "content": "Draft a performance narrative calibrated for the given grade level and Zava competency framework. Use the 360 summary and manager notes as grounding."},
  {"role": "user",      "content": "{\"grade\": \"L5 Senior Software Engineer\", \"360_summary\": \"...\", \"manager_notes\": \"...\"}"},
  {"role": "assistant", "content": "<the manager-approved final narrative>"}
]}
```

HR Legal reviews the fine-tuning dataset before training to confirm that no approved narrative introduced language that systematically favoured one demographic group. This is a required step, not optional.

### New fixture additions

Add to `shared-fixtures/`:

```
shared-fixtures/
  performance_narratives.json    # sample HR-approved narratives, one per grade level (L3–L7)
  competency_framework.json      # Zava's competency descriptors per level
```

`performance_narratives.json` structure:

```json
{
  "narratives": [
    {
      "id": "N-001",
      "employee_grade": "L5",
      "function": "Engineering",
      "cycle": "H1 2025",
      "narrative": "...",
      "manager_approved": true,
      "hr_legal_reviewed": true
    }
  ]
}
```

### Capability matrix addition

See the row for **UC7** in [comparison.md](comparison.md) — UC7 is a fine-tuning-dependent use case. It is feasible in all four solutions but only delivers consistent quality with a fine-tuned model.

---

## Fine-tuning in each solution

| Solution | Where to fine-tune | Notes |
|---|---|---|
| A (M365 Agents SDK) | Microsoft Foundry fine-tuning job → new deployment | Register the fine-tuned deployment name in `env/.env.{stage}`. Use a separate deployment for the classifier vs. the generator. |
| B (Copilot Studio) | Microsoft Foundry fine-tuning job → update the Foundry resource wired to generative answers | Copilot Studio's generative answers node can be pointed at a fine-tuned deployment via the Foundry resource selector. |
| C (Foundry) | Foundry fine-tuning UI or `az cognitiveservices account deployment create` → register as a secondary model deployment | Foundry supports multiple model deployments per project; the agent YAML references the deployment by name. |
| D (Mixed) | Fine-tuned classifier lives in the Azure Functions backend (same as C); fine-tuned generator lives in the Foundry connected agent (same as C) | The Copilot Studio topics and flows are unaffected — they call the same API endpoints. |

---

## Responsible AI notes for fine-tuned models

Fine-tuning on HR data introduces risks that do not exist with base models. The following are mandatory, not optional:

- **Bias audit the fine-tuning dataset before training.** HR Legal must review a representative sample of training examples. Any narrative, classification, or Q&A pair that systematically advantages or disadvantages a protected group must be removed or rebalanced before training.
- **Run the Microsoft Foundry safety evaluators on the fine-tuned model**, not just the base model. A model fine-tuned on real HR data can inadvertently learn to produce outputs that are grounded but discriminatory.
- **Version and archive fine-tuning datasets.** Datasets are evidence. If an employee challenges a decision made with the agent's help, HR Legal needs to produce the dataset that shaped the model's outputs.
- **Gate deployments on an eval harness.** The UC6 classifier example above illustrates the pattern: set hard floors on recall for the most sensitive categories and block any deployment that misses the floor.
- **Disclose AI-assisted generation to employees.** If Beatrice's performance narrative was drafted by a fine-tuned agent, Aarav has a right to know that under most data-protection frameworks. The agent's transcript is the disclosure artifact.

---

## Cross-references

| Topic | Document |
|---|---|
| Seven core use cases | [docs/scenario.md](scenario.md) |
| Technology capability matrix | [docs/comparison.md](comparison.md) |
| Foundry evaluations guidance | [docs/findings/foundry.md](findings/foundry.md) |
| Year-2 evolution (when fine-tuning becomes unavoidable) | [docs/timeline.md](timeline.md) — Year 2 section |
| Responsible AI baseline | [README.md](../README.md) — Responsible AI section |
