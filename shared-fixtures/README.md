# shared-fixtures

**Build-time seed data only.** None of the three solutions reads from this folder at runtime — each solution copies what it needs into its own `backend/` during build/deploy.

## Files

| File | Used by | Purpose |
|---|---|---|
| `employees.json` | All backends | Sample directory of 15 employees across personas |
| `leave_balances.json` | All backends | UC2 vacation/sick/personal balances for 2026 |
| `jobs.json` | All backends | UC4 internal job listings |
| `onboarding_template.json` | All backends | UC3 default onboarding plan template |
| `feedback_cycles.json` | All backends | UC5 active 360° review cycle and questions |
| `ticket_categories.json` | All backends | UC6 ticket categorization schema (sensitivity levels) |
| `policies/*.md` | UC1 RAG corpora (all solutions) | HR handbook, PTO policy, benefits, code of conduct |

## Persona IDs

| ID range | Persona |
|---|---|
| `E0xx` | Employees & people managers |
| `H0xx` | HR Partners & HR leadership |
| `I0xx` | IT |
| `B0xx` | Onboarding buddies |

## Demo cast

- **Aarav Patel (E001)** — primary employee persona for UC1, UC2, UC4
- **Beatrice Lambert (E010)** — manager persona for UC2, UC3, UC5
- **Eva Schmidt (E002)** — new hire persona for UC3
- **Carlos Mendes (H001)** — HR Partner persona for UC6
- **Dana Okafor (I001)** — IT persona for UC3
- **Sofia Kowalski (B001)** — onboarding buddy persona for UC3
