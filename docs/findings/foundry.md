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
