# FinCrime SAR Agent
**Author:** Puraby Deb  
**Stack:** Databricks · LangGraph · Streamlit · Delta Lake · Llama 3.1

---

## What This Does

An autonomous multi-agent system that drafts AUSTRAC-compliant 
Suspicious Matter Reports (SMRs) from a single Alert ID.

Analyst types `ALT-2024-08821` → agent runs 7 nodes → full SAR appears.

---

## Architecture

```
silver.alerts          ← TM system output
silver.customers       ← CIF / customer master  
silver.accounts        ← account details
silver.transactions    ← transaction history
silver.alert_history   ← prior alerts
silver.counterparties  ← external entities

LangGraph Pipeline (7 nodes):
  Node 1 → fetch_alert
  Node 2 → enrich_customer
  Node 3 → fetch_transactions
  Node 4 → check_prior_alerts
  Node 5 → screen_entities
  Node 6 → score_and_route  (conditional routing)
  Node 7 → draft_sar        (LLM writes SAR)

Streamlit UI → app.py
```

---

## File Structure

```
fincrime_sar_agent/
├── app.py                    ← Streamlit UI
├── app.yaml                  ← Databricks Apps config
├── requirements.txt          ← dependencies
├── setup.py                  ← shared state + DB connector
├── graph.py                  ← LangGraph pipeline
├── node_fetch_alert.py
├── node_enrich_customer.py
├── node_fetch_transaction.py
├── node_check_prior_alerts.py
├── node_screen_entities.py
├── node_score_and_route.py
└── node_draft_sar.py
```

---

## Test Alert IDs

| Alert ID | Risk | Customer | Typology |
|---|---|---|---|
| ALT-2024-08821 | CRITICAL (94) | James Morrison | Structuring + Vanuatu wire |
| ALT-2024-08734 | HIGH (72) | Linda Tran | Cash business deviation |
| ALT-2024-08612 | CRITICAL (91) | Daniel Kowalski | PAYG + Philippines wire |

---

## How to Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run Streamlit app
streamlit run app.py
```

---

## Key Design Decisions

- **One Alert ID in → full SAR out** — analyst touches nothing in between
- **Conditional routing** — agent decides SAR / Escalate / Auto-Close
- **Human-in-the-loop** — analyst reviews, edits, approves before filing
- **Saves to gold.sar_drafts** — approved SARs written to Delta Gold layer
- **AUSTRAC-aware** — FATF lists, AML/CTF Act 2006 references, 5-section SMR format

