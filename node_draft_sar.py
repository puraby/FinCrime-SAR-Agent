from setup import *
from node_fetch_alert import *
from node_enrich_customer import *
from node_fetch_transaction import *
from node_check_prior_alerts import *
from node_score_and_route import *
import requests
import json
from datetime import datetime

def draft_sar(state: SARState) -> SARState:
    """
    Node 7: Calls Databricks AI Gateway to write SAR narrative.
    Uses built-in session token — no external API key needed.
    """

    print(f"\n [Node 7] Drafting SAR for: {state['alert_id']}")

    # ── Skip if not routed to SAR ─────────────────────────
    if state.get("routing_decision") != "SAR_DRAFT":
        print(f"  [Node 7] Skipping — routing is "
              f"{state.get('routing_decision')}, not SAR_DRAFT")
        return state

    # ── Auth + endpoint from 00_setup ─────────────────────
    token    = DATABRICKS_TOKEN
    endpoint = DATABRICKS_GATEWAY
    model    = DATABRICKS_MODEL

    # ── Build transaction summary ─────────────────────────
    txn_lines = []
    for t in (state.get("transactions") or []):
        direction = "CREDIT" if t["direction"] == "CREDIT" else "DEBIT"
        txn_lines.append(
            f"  {t['txn_date']}  {direction}  "
            f"AUD ${t['amount']:,.2f}  "
            f"{t['channel']}  "
            f"{t['branch']}"
        )
    txn_summary = "\n".join(txn_lines)

    # ── Build red flags ───────────────────────────────────
    flags_text = "\n".join(
        f"  {i+1}. {f}"
        for i, f in enumerate(state.get("red_flags") or [])
    )

    # ── Build counterparty summary ────────────────────────
    cpty_lines = []
    for c in (state.get("counterparties") or []):
        cpty_lines.append(
            f"  - {c['name']} | "
            f"{c['bank_name']} ({c['bank_country']}) | "
            f"FATF: {c['fatf_status']} | "
            f"Flagged: {c.get('flagged', False)}"
        )
    cpty_summary = "\n".join(cpty_lines) if cpty_lines \
                   else "  No external counterparties identified"

    # ── Build prior alert summary ─────────────────────────
    prior_lines = []
    for a in (state.get("prior_alerts") or []):
        prior_lines.append(
            f"  - {a['alert_date']}  "
            f"{a['alert_type']}  "
            f"Risk: {a['risk_score']}  "
            f"→ {a['disposition']}"
        )
    prior_summary = "\n".join(prior_lines) if prior_lines \
                    else "  No prior alert history"

    # ── Prompt ────────────────────────────────────────────
    prompt = f"""You are a senior AML/CTF compliance officer at Commonwealth Bank of Australia (CBA).
Draft a formal Suspicious Matter Report (SMR) for submission to AUSTRAC under the Anti-Money Laundering and Counter-Terrorism Financing Act 2006.

Write in precise, formal compliance language. Be specific with all dates, amounts, branches, and entity names. Do not use vague language. Do not add disclaimers.

═══════════════════════════════════════════════
ALERT INTELLIGENCE
═══════════════════════════════════════════════
Alert ID:         {state['alert_id']}
Rule:             {state['rule_name']}
Alert Type:       {state['alert_type']} — {state['alert_subtype']}
TM Risk Score:    {state['risk_score']}/100
Agent Risk Score: {state['agent_risk_score']}/100
Risk Tier:        {state['risk_tier']}
Detected:         {state['detected_at']}

═══════════════════════════════════════════════
SUBJECT / CUSTOMER
═══════════════════════════════════════════════
Full Name:        {state['customer_name']}
Date of Birth:    {state['dob']}
Occupation:       {state['occupation']} at {state['employer']}
Industry:         {state['industry']}
Declared Income:  AUD ${state['annual_income']:,.2f} per annum
Address:          {state['address']}
Customer Since:   {state['customer_since']}
KYC Tier:         {state['kyc_tier']} (last reviewed: {state['kyc_last_review']})
Internal Rating:  {state['risk_rating']}
PEP Flag:         {state['pep_flag']}
Account:          BSB {state['bsb']} / {state['account_number']} ({state['account_type']})
Avg Monthly Credit: AUD ${state['avg_monthly_credit']:,.2f}
Avg Monthly Debit:  AUD ${state['avg_monthly_debit']:,.2f}

═══════════════════════════════════════════════
TRANSACTION ACTIVITY
═══════════════════════════════════════════════
Period:             {state['period_start']} to {state['period_end']}
Total Amount:       AUD ${state['total_amount']:,.2f}
Transaction Count:  {state['transaction_count']}
Branches Used:      {', '.join(state.get('branches_used') or [])}
Offshore Wire:      {state['has_offshore_wire']}
Destinations:       {', '.join(state.get('offshore_destinations') or [])}

Transaction Detail:
{txn_summary}

═══════════════════════════════════════════════
COUNTERPARTIES
═══════════════════════════════════════════════
{cpty_summary}

FATF Jurisdiction Hits: {', '.join(state.get('fatf_hits') or [])}
Flagged Entities:       {', '.join(state.get('flagged_entities') or [])}
Sanctions Hit:          {state['sanctions_hit']}

═══════════════════════════════════════════════
PRIOR ALERT HISTORY
═══════════════════════════════════════════════
Prior Alert Count:  {state['prior_alert_count']}
SAR Ever Filed:     {state['prior_sar_filed']}
Repeat Pattern:     {state['repeat_pattern']}

{prior_summary}

═══════════════════════════════════════════════
AGENT RED FLAGS ({len(state.get('red_flags') or [])} identified)
═══════════════════════════════════════════════
{flags_text}

═══════════════════════════════════════════════

Write the complete SMR narrative with EXACTLY these five sections:

1. BACKGROUND AND CUSTOMER PROFILE
2. DESCRIPTION OF SUSPICIOUS ACTIVITY
3. INDICATORS OF SUSPICIOUS BEHAVIOUR
4. TYPOLOGY AND REGULATORY ANALYSIS
5. RECOMMENDATION AND PROPOSED NEXT STEPS
"""

    # ── Call Databricks AI Gateway ────────────────────────
    print(f"   Calling Databricks AI Gateway...")
    print(f"   Model: {model}")

    try:
        response = requests.post(
            endpoint,
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            json = {
                "model":      model,
                "max_tokens": 4000,
                "messages": [
                    {
                        "role":    "user",
                        "content": prompt
                    }
                ],
            },
            timeout = 120
        )

        print(f"   Status: {response.status_code}")

        if response.status_code != 200:
            error_msg = (f"Gateway error {response.status_code}: "
                        f"{response.text[:200]}")
            print(f" [Node 7] {error_msg}")
            return {**state, "error": error_msg}

        # ── Extract narrative ─────────────────────────────
        result        = response.json()
        sar_narrative = result["choices"][0]["message"]["content"]
        model_used    = result.get("model", model)
        sar_reference = f"SMR-{state['alert_id']}"
        draft_time    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        word_count = len(sar_narrative.split())
        print(f" [Node 7] SAR narrative generated")
        print(f"   Reference:  {sar_reference}")
        print(f"   Model:      {model_used}")
        print(f"   Words:      {word_count}")
        print(f"   Timestamp:  {draft_time}")

        return {
            **state,
            "sar_narrative":   sar_narrative,
            "sar_reference":   sar_reference,
            "draft_timestamp": draft_time,
            "model_used":      model_used,
            "error":           None,
        }

    except Exception as e:
        error_msg = f"Request failed: {str(e)}"
        print(f" [Node 7] {error_msg}")
        return {**state, "error": error_msg}

print("Node 7 — draft_sar defined")

