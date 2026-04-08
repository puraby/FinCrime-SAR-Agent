
from setup import *
from node_fetch_alert import *
from node_enrich_customer import *
from node_fetch_transaction import *
from node_check_prior_alerts import *

def score_and_route(state: SARState) -> SARState:
    """
    Node 6: The agent's brain.
    Reasons over ALL collected data and:
      1. Calculates its own risk score (independent of TM system)
      2. Identifies specific red flags with explanations
      3. Makes a routing decision:
           SAR_DRAFT   → risk >= 80 or critical indicators present
           ESCALATE    → risk 60-79 or ambiguous case needs L2
           AUTO_CLOSE  → risk < 60 and no critical indicators
    Input:  everything from Nodes 1-5
    Output: agent_risk_score, red_flags, routing_decision,
            routing_reason
    """

    print(f"\n⚖️  [Node 6] Scoring and routing: {state['alert_id']}")

    # ── Build red flags list ──────────────────────────────
    # Each rule adds a red flag string if condition is met.
    # These feed directly into the SAR narrative.
    red_flags = []

    # --- Structuring indicators ---
    if state.get("transaction_count") and state["transaction_count"] >= 3:
        red_flags.append(
            f"Multiple cash deposits ({state['transaction_count']} transactions) "
            f"totalling AUD ${state['total_amount']:,.2f} — "
            f"consistent with deliberate structuring to avoid "
            f"AUSTRAC CTF reporting threshold of AUD $10,000"
        )

    if state.get("branches_used") and len(state["branches_used"]) >= 3:
        red_flags.append(
            f"Deposits spread across {len(state['branches_used'])} "
            f"separate branches ({', '.join(state['branches_used'])}) — "
            f"indicative of deliberate threshold avoidance strategy"
        )

    # --- Offshore wire ---
    if state.get("has_offshore_wire"):
        destinations = ", ".join(state.get("offshore_destinations") or [])
        red_flags.append(
            f"Outward SWIFT wire to offshore account following "
            f"cash deposit accumulation — "
            f"classic placement to layering pattern"
        )

    # --- FATF jurisdiction ---
    if state.get("fatf_hits"):
        for country in state["fatf_hits"]:
            red_flags.append(
                f"Transaction destination country '{country}' "
                f"is on the FATF grey list — "
                f"elevated money laundering risk jurisdiction"
            )

    # --- Flagged counterparties ---
    if state.get("flagged_entities"):
        for entity in state["flagged_entities"]:
            red_flags.append(
                f"Counterparty '{entity}' is flagged in "
                f"the internal watchlist — "
                f"no verifiable legitimate business purpose"
            )

    # --- Customer risk profile ---
    if state.get("risk_rating") == "HIGH":
        red_flags.append(
            f"Customer carries a HIGH internal risk rating — "
            f"heightened scrutiny required under CDD obligations"
        )

    if state.get("kyc_tier") == "ENHANCED":
        red_flags.append(
            f"Customer is subject to Enhanced Due Diligence (EDD) — "
            f"KYC last reviewed {state.get('kyc_last_review')} "
            f"which may be overdue given current activity"
        )

    # --- Income inconsistency ---
    if state.get("annual_income") and state.get("total_amount"):
        income_ratio = state["total_amount"] / (state["annual_income"] / 12)
        if income_ratio > 5:
            red_flags.append(
                f"Transaction total AUD ${state['total_amount']:,.2f} "
                f"represents {income_ratio:.1f}x the customer's "
                f"estimated monthly income — "
                f"grossly inconsistent with declared financial profile"
            )

    # --- Prior alerts same typology ---
    if state.get("repeat_pattern"):
        red_flags.append(
            f"Customer has {state['prior_alert_count']} prior alert(s) "
            f"for the same typology ({state['alert_type']}) — "
            f"previously closed as false positive; "
            f"current pattern warrants escalated scrutiny"
        )

    # --- Sanctions ---
    if state.get("sanctions_hit"):
        red_flags.append(
            "SANCTIONS EXPOSURE DETECTED — "
            "transaction linked to FATF black list jurisdiction"
        )

    # ── Calculate agent risk score ────────────────────────
    # Start from TM system score as baseline
    # Then adjust up/down based on what we found
    base_score = state.get("risk_score") or 50
    adjustment = 0

    # Upward adjustments
    if state.get("has_offshore_wire"):        adjustment += 5
    if state.get("fatf_hits"):                adjustment += 5
    if state.get("flagged_entities"):         adjustment += 5
    if state.get("repeat_pattern"):           adjustment += 5
    if state.get("sanctions_hit"):            adjustment += 15
    if state.get("pep_network_hit"):          adjustment += 10
    if len(state.get("branches_used") or []) >= 4:  adjustment += 3

    # Downward adjustments
    if not state.get("has_offshore_wire"):    adjustment -= 5
    if not state.get("fatf_hits"):            adjustment -= 3
    if state.get("prior_sar_filed") == False \
       and state.get("prior_alert_count", 0) == 0:
                                              adjustment -= 2

    # Cap between 0 and 100
    agent_risk_score = max(0, min(100, base_score + adjustment))

    # ── Routing decision ──────────────────────────────────
    if agent_risk_score >= 80 or state.get("sanctions_hit"):
        routing_decision = "SAR_DRAFT"
        routing_reason   = (
            f"Agent risk score {agent_risk_score}/100 exceeds SAR threshold. "
            f"{len(red_flags)} red flags identified. "
            f"Sufficient indicators to proceed with SAR narrative draft."
        )

    elif agent_risk_score >= 60:
        routing_decision = "ESCALATE"
        routing_reason   = (
            f"Agent risk score {agent_risk_score}/100 — "
            f"ambiguous case requiring L2 analyst review. "
            f"{len(red_flags)} red flags identified but "
            f"insufficient for automatic SAR filing."
        )

    else:
        routing_decision = "AUTO_CLOSE"
        routing_reason   = (
            f"Agent risk score {agent_risk_score}/100 — "
            f"below threshold for SAR or escalation. "
            f"Recommend closing with documented rationale."
        )

    # ── Log decision ──────────────────────────────────────
    print(f" [Node 6] Scoring complete")
    print(f"   TM Score:        {state.get('risk_score')}/100")
    print(f"   Agent Score:     {agent_risk_score}/100  "
          f"(adjustment: {'+' if adjustment >= 0 else ''}{adjustment})")
    print(f"   Red Flags:       {len(red_flags)}")
    print(f"   Routing:         {routing_decision}")
    print(f"   Reason:          {routing_reason}")

    print(f"\n   ── Red Flags Identified ──────────────────────")
    for i, flag in enumerate(red_flags, 1):
        print(f"   {i}. {flag}")

    print(f"\n   {'='*50}")
    if routing_decision == "SAR_DRAFT":
        print(f"   ⚡ DECISION: DRAFT SAR → proceeding to Node 7")
    elif routing_decision == "ESCALATE":
        print(f"    DECISION: ESCALATE → routing to L2 analyst")
    else:
        print(f"    DECISION: AUTO CLOSE → insufficient for SAR")
    print(f"   {'='*50}")

    return {
        **state,
        "agent_risk_score": agent_risk_score,
        "routing_decision": routing_decision,
        "routing_reason":   routing_reason,
        "red_flags":        red_flags,
        "error":            None,
    }

print("Node 6 — score_and_route defined")
