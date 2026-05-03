# Fine-tuning datasets — Contoso HR Concierge

Each `.jsonl` file in this folder is a **supervised fine-tuning (SFT) dataset** in the
[Azure OpenAI chat-completion format](https://learn.microsoft.com/azure/ai-services/openai/how-to/fine-tuning).
Every line is a complete `{"messages": [...]}` training example.

These files contain **dummy data only** — names, ticket text, policies, and
narratives are fictional and have been reviewed to contain no real PII.
Before using real HR data, follow the bias-audit and legal-review steps
described in [docs/fine-tuning.md](../../docs/fine-tuning.md).

## Files

| File | UC | Fine-tuning value | Recommended base model |
|---|---|---|---|
| `uc1_policy_qa_train.jsonl` | UC1 Policy Q&A | Optional | `gpt-4o-mini` |
| `uc3_onboarding_plan_train.jsonl` | UC3 Onboarding | Optional | `gpt-4o-mini` |
| `uc4_mobility_pitch_train.jsonl` | UC4 Internal mobility | Recommended | `gpt-4o` |
| `uc5_360_summary_train.jsonl` | UC5 360° feedback summary | **Required for equity** | `gpt-4o` |
| `uc6_triage_classifier_train.jsonl` | UC6 Triage & escalation | **Required for safety** | `gpt-4o-mini` |
| `uc7_performance_narrative_train.jsonl` | UC7 Performance narrative | **Core value prop** | `gpt-4o` |

## How to run a fine-tuning job on Microsoft Foundry

```bash
# 1. Upload training file to the Foundry project
az cognitiveservices account deployment list \
  --name <foundry-account-name> --resource-group <rg>

# 2. Split each .jsonl 90/10 train/validation
python - <<'EOF'
import json, pathlib, random
src = pathlib.Path("uc6_triage_classifier_train.jsonl").read_text().splitlines()
random.shuffle(src)
split = int(len(src) * 0.9)
pathlib.Path("train.jsonl").write_text("\n".join(src[:split]))
pathlib.Path("val.jsonl").write_text("\n".join(src[split:]))
EOF

# 3. Submit fine-tuning job via Azure OpenAI
openai api fine_tuning.jobs.create \
  --training-file train.jsonl \
  --validation-file val.jsonl \
  --model gpt-4o-mini-2024-07-18 \
  --suffix "hr-uc6-triage-v1"
```

Register the resulting deployment in `project/agent.yaml` (Solution C/D) or update the
generative-answers resource selector in Copilot Studio (Solution B).

## Eval gate

Run `evaluations/uc6_classifier/run_eval.py` before any deployment. Block if
`HARASSMENT_recall < 0.99`. See [docs/fine-tuning.md](../../docs/fine-tuning.md) for details.
