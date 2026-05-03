# Why fine-tuning must be considered — a guide for each stakeholder

This document explains the fine-tuning investment decision in language that is relevant
to each of the four stakeholder groups who must weigh in before Contoso HR deploys a
fine-tuned model in production.

Each section is self-contained. Share the relevant section with the relevant audience.

---

## 1. C-Level (CEO, CHRO, CFO)

### The one-paragraph version

A base AI model answers HR questions plausibly. A fine-tuned model answers them *consistently* — using Contoso's vocabulary, formats, and calibration standards. For HR, that difference is not cosmetic: it is the difference between a tool that deflects routine questions and a tool that can be trusted to produce 360° summaries, ticket triage decisions, and performance drafts that will hold up in a calibration meeting or an employment tribunal. Fine-tuning is the mechanism by which Contoso moves from "AI that is good enough for demos" to "AI that HR would stake its credibility on."

### Why it is a strategic investment, not a feature request

| Business outcome | Without fine-tuning | With fine-tuned model |
|---|---|---|
| HR productivity | Agent deflects ~40% of tickets; complex cases still reach HR Operations | Agent deflects ~65% of tickets; triage classification is stable and auditable |
| Review cycle quality | Manager narratives vary in length and specificity; calibration committee spends extra session aligning | Narratives are grade-calibrated; calibration session starts from a common baseline |
| Equity and legal exposure | Format variation in 360 summaries creates disparate-treatment risk | Consistent format is the documented standard; auditable against the training dataset |
| Competitive position | Agents are undifferentiated; any tenant can deploy the same base model | Fine-tuned model embeds Contoso's competency framework and HR vocabulary — this is proprietary IP |

### What it costs and what it returns

- **One-time cost:** 200–500 hours of HR Operations time to curate and label the training dataset. This is the dominant cost — not compute.
- **Compute cost:** Fine-tuning a `gpt-4o-mini` on 500 examples runs in under an hour on Microsoft Foundry. The cost is in the tens of euros.
- **Ongoing cost:** Re-fine-tune after major policy or competency-framework changes (typically once per year).
- **Return:** Faster calibration sessions, fewer escalations, reduced HR Partner time on routine classification, and a defensible audit trail for employment decisions.

### The risk of not doing it

The agent will continue to work — it just will not be reliable enough to extend beyond use cases where format variation is acceptable. For UC6 (harassment triage) and UC5/UC7 (feedback and narrative quality), a base model is not safe enough to deploy without a fine-tuned classifier as a safety net. The decision is not "fine-tune or don't" — it is "which use cases are we willing to hold to a higher standard."

---

## 2. HR (HR Operations, HR Partners, People Analytics)

### The HR framing: consistency is a fairness obligation

When an employee asks a policy question, a slightly different phrasing from the agent is acceptable. When a manager receives a 360° feedback summary, a significantly shorter or less specific summary than the summary their colleague received for an equivalent employee is not acceptable — it is a fairness problem. When an employee files a harassment complaint and the agent routes it incorrectly because the phrasing was unusual, it is a compliance failure.

Fine-tuning solves each of these by teaching the model how Contoso HR does it — using real HR-approved examples as the curriculum.

### What HR contributes to fine-tuning

HR does not write code. HR contributes **labeled examples**: past 360 summaries that managers approved, past ticket-handling decisions, and past onboarding plans that received positive feedback. The typical contribution is:

| Use case | Dataset source | Volume needed |
|---|---|---|
| UC5 360° feedback summary | Past cycles where manager reviewed and approved the summary | 50–150 examples |
| UC6 Triage classifier | Historical HR tickets + HR Operations' agreed classification | 200–350 examples |
| UC7 Performance narrative | Past review cycles — manager-approved final narratives | 80–200 examples |

HR Legal reviews the dataset before it is used for training (see Legal section below).

### What HR gets back

- **360 summaries** that follow the same format for every employee at the same grade. No more calibration-session surprises.
- **Ticket routing** that is stable across different employees' phrasings. A harassment signal is caught whether the employee says "my manager makes me uncomfortable" or "something happened at work last week that I want to report."
- **Performance narrative drafts** that land at the right grade level. The manager edits for specifics, not for calibration — saving typically 20–30 minutes per narrative.

### The HR owner role

HR Operations assigns a **Fine-tuning Dataset Curator** role for each use case. This person:
1. Pulls historical examples from the relevant system (Workday, ServiceNow, the previous review tool).
2. Anonymises PII (names → employee IDs or generic descriptors).
3. Flags any examples that should not be used (e.g., examples involving ongoing litigation).
4. Hands the anonymised dataset to the engineering team for training.

This is a one-time effort per use case, then an annual refresh.

---

## 3. DPO & CISO

### Data used in fine-tuning

Fine-tuning a language model means sending a dataset of text examples to Microsoft Foundry's training infrastructure. For HR, this means historical HR tickets, 360 summaries, or performance narratives — all of which are personal data under GDPR.

**What this means in practice:**

| Requirement | How it is met |
|---|---|
| Lawful basis for processing | Fine-tuning falls under the employer's legitimate interest in operating a safe and fair HR process (Art. 6(1)(f) GDPR) or, where required, explicit consent of affected employees. Contoso Legal confirms the applicable basis per jurisdiction. |
| Data minimisation | Training examples are stripped to the minimum needed: no employee names, no identifiers. Employee IDs are replaced with anonymised tokens. The dataset contains HR content, not identity data. |
| Data residency | Microsoft Foundry fine-tuning jobs are pinned to the same Azure region as the HR data. For EU employees: use `northeurope` or `westeurope`. Do not use `GlobalStandard` without legal sign-off. See [docs/public-sector-eu.md](public-sector-eu.md) for the EU sovereignty details. |
| Data retention | The fine-tuning dataset is archived in a Contoso-controlled storage account (the same Key Vault and managed-identity posture as the rest of the solution). Microsoft does not retain customer fine-tuning data after the job completes, per the [Microsoft Foundry data privacy documentation](https://learn.microsoft.com/azure/ai-services/openai/concepts/data-privacy). |
| Right of access / erasure | Individual employee contributions to the training dataset are identifiable at the row level in the Contoso-controlled archive. If an employee exercises a GDPR erasure right, remove their examples from the archive and schedule a re-fine-tune in the next quarterly cycle. |
| Model outputs as personal data | A performance narrative or 360 summary generated for a named employee is personal data. It must be handled under the same retention and access controls as the equivalent human-authored document. |

### Security controls

- Fine-tuning jobs run inside the Contoso Microsoft Foundry project, authenticated via managed identity. No API keys in the pipeline.
- The training dataset is stored in the project's BYO storage account (Azure Storage, key auth disabled, RBAC-only access).
- The fine-tuned model deployment is registered in the same Foundry project as the base model — no new network surface.
- Foundry traces (inputs, outputs, latency) are routed to the Contoso-controlled Log Analytics workspace. No employee conversation data leaves Contoso's tenant.

### Audit trail

The fine-tuning dataset is the audit artifact. If an employment decision is challenged and the agent's output is in scope, Contoso can produce:
1. The exact training example that shaped the model's classification or generation for the relevant category.
2. The version of the dataset used for training (Git SHA of the fixture file).
3. The evaluation results (precision/recall on the held-out test set) that cleared the deployment gate.

This is a stronger audit position than a prompted base model, which has no equivalent artifact.

---

## 4. Legal

### Why Legal's sign-off is required before training

HR data fine-tunes a model that will be used in employment decisions. That sits at the intersection of data-protection law (GDPR, national implementations), employment law (equal treatment, non-discrimination), and emerging AI regulation (EU AI Act).

Legal's role in the fine-tuning workflow is not to review every training example — it is to approve:
1. **The dataset composition review** (see below).
2. **The disclosure language** shown to employees.
3. **The retention and deletion policy** for fine-tuning datasets and fine-tuned models.

### Dataset composition review

Before any dataset is used for training, HR Legal reviews a representative sample (typically 10–20%) for:

| Risk | What to look for |
|---|---|
| Systematic demographic bias | Do approved narratives or classifications for comparable situations differ by apparent gender, ethnicity, age, or disability status? A fine-tuned model will learn and amplify these differences. |
| Legally inadmissible content | Does any training example reference protected characteristics in a way that would be impermissible in an employment context (e.g., "she went on maternity leave and her performance rating dropped")? |
| Pending litigation | Does any example involve an employee or a case that is currently subject to a dispute or claim? Those examples must be excluded. |
| Over-representation | Is one team, function, or manager disproportionately represented in the dataset? The model will learn from the modal case; outlier contexts may be systematically mishandled. |

This review is documented and archived alongside the dataset. It is the primary legal safeguard.

### EU AI Act classification

Under the EU AI Act, AI systems used in employment decisions — including performance assessment and HR ticket routing — are classified as **high-risk** (Annex III, §4). High-risk obligations relevant to fine-tuning include:

- **Technical documentation:** The fine-tuning dataset, training process, evaluation results, and intended use must be documented before deployment (Art. 11). This repository's `shared-fixtures/fine-tuning/`, `evaluations/`, and this documentation file together constitute the technical documentation.
- **Data governance:** Training data must be relevant, representative, and free from known errors and biases (Art. 10). The dataset composition review above addresses this.
- **Transparency to affected persons:** Employees whose data shaped the model must be informed (see `docs/public-sector-eu.md` for the Public Sector supplement). The agent's disclosure statement must mention AI-assisted generation.
- **Human oversight:** For high-risk outputs (UC6 escalation decisions, UC7 narratives), a human must review before any action is taken. The agent never auto-actions these use cases.
- **Accuracy and robustness:** The evaluation gate (UC6: HARASSMENT_recall ≥ 0.99) is the documented accuracy floor. Any deployment that fails this gate is blocked.

### Retention and deletion

| Artifact | Retention | Deletion trigger |
|---|---|---|
| Fine-tuning dataset (JSONL files) | Retain for the life of the model + 7 years | Erasure request from an employee whose data is in the set; end of AI Act documentation obligation |
| Fine-tuned model weights | Retain in Foundry project for the model's active lifetime | Model decommission |
| Evaluation results | Retain with the dataset | Same as dataset |
| Employee conversation transcripts (agent outputs) | Subject to the HR document retention policy applicable to the equivalent human document | Same trigger as the equivalent document type |

The fine-tuning dataset is stored in a Contoso-controlled Azure Storage account, not in Microsoft's training infrastructure. Deletion is within Contoso's control at any time.
