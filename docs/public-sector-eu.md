# EU Public Sector — Microsoft Foundry sovereignty story

This document is for teams deploying the Contoso HR Concierge (or any HR agent based on
this repository) in a **European Union public-sector** context: national governments,
regional administrations, municipalities, agencies, and publicly funded institutions.

It covers the sovereignty requirements that public-sector buyers typically raise, explains
how the Microsoft Foundry stack addresses each one, and identifies the residual
responsibilities that remain with the deploying organisation.

---

## Why sovereignty matters more in the public sector

Private employers have flexibility in where they process employee data, subject to GDPR.
Public-sector bodies face an additional layer of constraints:

1. **National security and data-sovereignty laws** in most EU member states restrict
   certain categories of civil-servant data from leaving national jurisdiction — or even
   from being processed on infrastructure not subject to national law.
2. **EU AI Act Article 26 obligations** apply to public authorities using high-risk AI
   systems in employment decisions; the public authority is always considered the deployer
   and cannot shift accountability to a vendor.
3. **NIS2 Directive** classifies many public administrations as essential entities,
   imposing mandatory cybersecurity measures and incident-reporting obligations on the
   AI systems they operate.
4. **Public-procurement rules** in several member states require that cloud services
   used for sensitive data meet national certification schemes (e.g., France's SecNumCloud,
   Germany's C5, Netherlands' BIO).
5. **Works-council and union consultation requirements** in EU member states mean that
   deploying an AI system that influences employment decisions requires documented
   consultation with employee representatives before go-live.

---

## What "sovereignty" means for an HR AI agent

For an HR Concierge agent, the sovereignty story has five layers:

| Layer | The question | The Microsoft Foundry answer |
|---|---|---|
| **Data residency** | Where is employee data processed and stored? | All Azure resources pinned to an EU region; no data leaves the EU boundary |
| **Model residency** | Where does model inference run? | Regional deployment (`northeurope`/`westeurope`); avoid `GlobalStandard` until legal sign-off |
| **Operator control** | Who can read conversation transcripts and logs? | Contoso (or the deploying authority) controls the Log Analytics workspace; Microsoft cannot read customer data without an explicit support ticket |
| **Contractual guarantees** | What commitments does Microsoft make to EU public sector? | EU Data Boundary commitment, EUCS-aligned controls, DPA with SCCs |
| **Auditability** | Can the authority demonstrate compliance to a national supervisory authority? | Fine-tuning dataset, eval results, and system prompt are versioned in Git and archived in the authority's storage account |

---

## Infrastructure configuration for EU public-sector deployments

### Step 1 — Pin every resource to an EU region

In each of the four Bicep templates in this repository, set `location` to
`northeurope` (Ireland) or `westeurope` (Netherlands). These two regions are inside
the EU and are covered by Microsoft's **EU Data Boundary** commitment.

```bicep
// In each infra/main.bicep — override at deploy time
param location string = 'northeurope'  // or 'westeurope'
```

**Do not use** `globalstandard` capacity for Azure OpenAI deployments in production.
Use regional standard capacity:

```bicep
resource gpt 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: foundry
  name: openAiDeployment
  sku: { name: 'Standard', capacity: 30 }          // Regional, not GlobalStandard
  properties: { model: { format: 'OpenAI', name: 'gpt-4o', version: '2024-08-06' } }
}
```

### Step 2 — Configure the Microsoft Foundry project for EU residency

The Foundry account and project are already in this repo (`foundry-agent/infra/main.bicep`,
`mixed-agent/infra/main.bicep`, and after the IaC updates in this PR also in
`m365-agent/infra/main.bicep` and `copilot-studio-agent/infra/main.bicep`).

For public sector, additionally set:

```bicep
resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  // ...
  properties: {
    // ...
    networkAcls: {
      defaultAction: 'Deny'
      ipRules: []                                   // Add deploying authority IP ranges
      virtualNetworkRules: []                       // Add VNet subnet if using private endpoint
    }
    publicNetworkAccess: 'Disabled'                 // Use private endpoint in prod
  }
}
```

Add a private endpoint and private DNS zone for the Foundry endpoint so that no traffic
traverses the public internet.

### Step 3 — Disable cross-region data movement

Add the `restrictOutboundNetworkAccess` setting to all Container Apps and Function Apps:

```bicep
// In Container Apps environment
properties: {
  workloadProfiles: [ { name: 'Consumption', workloadProfileType: 'Consumption' } ]
  // Outbound traffic restricted to the VNet for public-sector deployments
}
```

### Step 4 — Configure data retention for civil-servant personal data

The default Log Analytics retention (30 days in this repo) may need to be extended or
reduced depending on the applicable national retention law. Update:

```bicep
resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  properties: {
    retentionInDays: 365     // Example — set to the national requirement
    // ...
  }
}
```

For particularly sensitive categories (grievance, harassment), configure a **separate
Log Analytics workspace with stricter access controls** and route UC6-related traces
there rather than to the general workspace.

---

## Fine-tuning in a sovereignty context

Fine-tuning on civil-servant HR data raises the stakes of the analysis in
[docs/fine-tuning-why.md](fine-tuning-why.md). Additional public-sector requirements:

### Training data governance

- Civil servants' personal data used for fine-tuning requires a **Data Protection Impact
  Assessment (DPIA)** before processing (GDPR Art. 35). The DPIA must document the
  purpose, necessity, proportionality, and safeguards. The fine-tuning dataset composition
  review (see [docs/fine-tuning-why.md](fine-tuning-why.md) § Legal) is the core
  technical input to the DPIA.
- In member states with **works-council co-determination rights** (e.g., Germany §87 BetrVG,
  Netherlands WOR Art. 27), deploying a model fine-tuned on employee performance data
  requires works-council agreement before deployment. Start that process early — it
  typically takes 4–8 weeks.
- Fine-tuning datasets must be stored in a storage account inside the EU boundary
  with access restricted to named principals (no wildcard RBAC assignments).

### Microsoft Foundry fine-tuning and data processing

When a fine-tuning job runs in Microsoft Foundry, the training data is temporarily
processed by Microsoft's training infrastructure. The following contractual protections apply:

- **Data Processing Agreement (DPA):** Microsoft's standard online services DPA covers
  Azure OpenAI fine-tuning. For EU public sector, request the EU public-sector addendum.
- **EU Data Boundary:** Training jobs submitted to EU-region Foundry accounts stay within
  the EU boundary. Microsoft's [EU Data Boundary documentation](https://www.microsoft.com/en-us/trust-center/privacy/european-data-boundary-eudb)
  confirms this for Azure AI Services.
- **No training on customer data:** Microsoft does not use customer fine-tuning data to
  train foundation models. This is covered in the [Azure OpenAI data privacy documentation](https://learn.microsoft.com/azure/ai-services/openai/concepts/data-privacy).

---

## EU AI Act compliance for public-sector deployers

Public administrations using this agent in employment-related decisions are **deployers
of a high-risk AI system** under EU AI Act Annex III §4. As deployer, the authority's
obligations include:

| Obligation | What it means for this deployment | Where to find it in this repo |
|---|---|---|
| **Use the system as intended** (Art. 26(1)) | Do not extend to use cases not covered by the technical documentation | [docs/scenario.md](scenario.md) defines the intended scope |
| **Input data quality** (Art. 26(2)) | Ensure the HR data fed to the agent (policies, employee records) is accurate and up to date | Corpus governance process (update SharePoint / AI Search index when policies change) |
| **Human oversight** (Art. 26(1)(d)) | Maintain the human-in-the-loop for UC2 approval, UC3 provisioning, UC6 escalation, UC7 narrative submission | All four solutions enforce HITL in their workflows; do not remove it |
| **Monitoring** (Art. 26(5)) | Monitor the system's operation; report serious incidents to the national market surveillance authority | Foundry evaluations + Log Analytics dashboards; establish an incident-reporting runbook |
| **Record-keeping** (Art. 12) | Keep logs of the system's use for at least the period required by sectoral law | Configure Log Analytics retention to meet the applicable sectoral requirement |
| **Transparency to employees** (Art. 13 & 26(6)) | Inform civil servants that AI is used in HR processes and what it does | Add a disclosure statement to the agent's welcome message and to the HR intranet page |
| **Registration** (Art. 49) | High-risk AI systems deployed by public authorities must be registered in the EU database before deployment | Register at [EU AI Act database](https://www.ai.act.eu/) when available |

---

## Sovereignty story in one page — for a public-sector procurement committee

> **Contoso HR Concierge** is an HR process AI agent built on **Microsoft Foundry**,
> deployed entirely within EU Azure regions (`northeurope` or `westeurope`). No employee
> data is processed outside the European Union. The Microsoft Foundry stack is covered
> by the **Microsoft EU Data Boundary commitment**, the **Azure Data Processing Agreement
> with Standard Contractual Clauses**, and optional national addenda for public-sector
> buyers.
>
> All AI inference (conversation, ticket triage, feedback summary, performance narrative)
> runs on **regional Azure OpenAI deployments** — not on globally distributed capacity.
> For the highest-sensitivity use cases (UC6 harassment triage, UC7 performance narratives),
> a **fine-tuned model** is used rather than a base model. The fine-tuning training data
> is stored in the deploying authority's own storage account inside the EU boundary; it
> is never used by Microsoft to train foundation models.
>
> The system qualifies as a **high-risk AI system** under EU AI Act Annex III §4
> (employment decisions). The deploying authority acts as the **deployer** and retains
> full control over data, model versions, system prompts, and audit logs. The technical
> documentation required under Art. 11 — including the fine-tuning dataset, evaluation
> results, and this architecture documentation — is maintained in a version-controlled
> repository under the authority's governance.
>
> Human oversight is enforced for every consequential action: leave approvals (UC2),
> access provisioning (UC3), grievance escalation (UC6), and narrative submission (UC7).
> The agent never takes irreversible actions autonomously.
>
> The agent is certified for Microsoft 365 Copilot and Teams, surfaces natively in the
> authority's existing M365 tenant, and respects all Entra ID conditional-access and
> data-loss-prevention policies already in force.

---

## Checklist for EU public-sector go-live

- [ ] All Azure resources deployed to `northeurope` or `westeurope`.
- [ ] Azure OpenAI deployments use `Standard` (regional) capacity, not `GlobalStandard`.
- [ ] Private endpoints configured for Foundry, Storage, Cosmos, and AI Search.
- [ ] Log Analytics retention set to meet the applicable sectoral law.
- [ ] Separate Log Analytics workspace for UC6 (grievance/harassment) traces, with restricted access.
- [ ] DPIA completed and filed before fine-tuning jobs run on civil-servant data.
- [ ] Works-council or union consultation completed (where required by national law).
- [ ] Fine-tuning dataset composition review documented and signed off by legal counsel.
- [ ] EU AI Act high-risk system registration submitted (when the registration database is live).
- [ ] Agent disclosure statement added to the welcome message and HR intranet.
- [ ] Incident-reporting runbook created and assigned to an owner.
- [ ] Evaluation harness running in CI with documented accuracy thresholds.
- [ ] Human-in-the-loop enforced for all consequential actions — not removed or bypassed.

---

## Cross-references

| Topic | Document |
|---|---|
| Fine-tuning rationale by stakeholder | [docs/fine-tuning-why.md](fine-tuning-why.md) |
| Fine-tuning technical details | [docs/fine-tuning.md](fine-tuning.md) |
| IaC for all four solutions | `*/infra/main.bicep` in each solution folder |
| Responsible AI baseline | [README.md](../README.md) — Responsible AI section |
| Architecture diagrams | [docs/architecture/](architecture/) |
