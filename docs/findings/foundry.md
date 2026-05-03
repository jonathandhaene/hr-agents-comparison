# Findings — Microsoft Foundry hosted agent

## What worked well

- The hosted agent runtime + threads + evaluations remove a lot of bespoke plumbing.
- File Search over the policy corpus solves UC1 without us standing up an AI Search index ourselves (we still have one for tool calls, but it's optional).
- "Publish to Copilot" + Teams from Foundry is a single workflow step — no manifest/bot dance.
- The Microsoft Agent Framework Python SDK is small and idiomatic — tools are just typed async functions.

## What hurt

- Live human handoff is not first-class (compared with Copilot Studio's `TransferConversation`). UC6 escalation is tool-driven.
- Multi-actor proactive notifications (UC3) still need an external scheduler — we use a Logic App tick.
- The Foundry account+project Bicep shape is new; expect API churn around `Microsoft.CognitiveServices/accounts/projects`.
- Tool implementations live in your container; you operate that lifecycle. The "hosted" part stops at the agent definition.

## Recommendations

- Use Foundry evaluations from day one — register a small dataset per UC and gate deployments on score deltas.
- Keep tool functions side-effect-free at the Python level; let the agent confirm before mutating (we do this for UC2/UC6).
- Prefer File Search for stable corpora; reserve AI Search for high-customisation retrieval.
- When you need approvals or Dataverse, call a Copilot Studio agent or flow as a connected agent rather than re-implementing.

## Fine-tuning with Foundry

Foundry is the natural home for fine-tuning in this repo because it already manages model deployments, evaluation datasets, and the deployment lifecycle. The recommended pattern is to register a **fine-tuned model as a secondary deployment** alongside the base `gpt-4o` deployment used for generation:

```yaml
# foundry-agent/agent.yaml  (partial)
models:
  classifier: hr-triage-v1          # fine-tuned gpt-4o-mini — UC6 triage
  generator: gpt-4o                 # base model — UC4/UC5/UC7 generation
  narrative: hr-narrative-v1        # fine-tuned gpt-4o — UC7 performance narratives
```

**When to fine-tune:**

- **UC6 triage classifier** — fine-tune before production. The `HARASSMENT/CRITICAL` recall floor cannot be met reliably with a prompted base model across all real-world phrasings. Use a `gpt-4o-mini` fine-tune: the task is classification, not generation, and the smaller model is faster and cheaper at inference time.
- **UC5 feedback summary** and **UC7 performance narrative** — fine-tune once you have 200+ HR-approved output examples from prior review cycles. The quality lift is measurable in user testing and the consistency is auditable.

**Evaluation gate for fine-tuned models:**

Register a held-out eval dataset in Foundry before the first fine-tuned deployment. Gate on:

| UC | Metric | Hard floor |
|---|---|---|
| UC6 classifier | `HARASSMENT_recall` | 0.99 |
| UC6 classifier | `overall_precision` | 0.92 |
| UC5 summary | `format_adherence` (LLM-as-judge) | 0.85 |
| UC7 narrative | `grade_calibration` (LLM-as-judge vs. rubric) | 0.88 |

Any deployment that misses a hard floor is blocked by the CI pipeline.

**Dataset governance:**

Fine-tuning datasets for UC6, UC5, and UC7 contain or are derived from employee data. They must be:
- Anonymised before training (replace names and identifying details with synthetic stand-ins).
- Reviewed by HR Legal before the first training run.
- Archived in a versioned Azure Blob container with access restricted to the Foundry MI.

See [docs/fine-tuning.md](../fine-tuning.md) for the full analysis.
