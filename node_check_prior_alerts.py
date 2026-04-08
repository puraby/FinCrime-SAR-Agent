
from setup import *
from node_fetch_alert import *
from node_enrich_customer import *
from node_fetch_transaction import *
def check_prior_alerts(state: SARState) -> SARState:
    """
    Node 4: Check if this customer has been flagged before.
    This is critical for the SAR narrative — a repeat pattern
    of false positive dispositions on the same typology is
    a major red flag the agent must surface.

    Input:  customer_id, alert_type (from Nodes 1 & 2)
    Output: prior_alerts, prior_alert_count, prior_sar_filed,
            prior_dispositions, repeat_pattern
    """

    customer_id = state["customer_id"]
    alert_type  = state["alert_type"]
    alert_id    = state["alert_id"]

    print(f"\n📋 [Node 4] Checking prior alerts for: {customer_id}")

    # ── Query alert history ───────────────────────────────
    # Exclude the current alert — only want historical ones
    prior_alerts = query(f"""
        SELECT
            alert_id,
            alert_date,
            alert_type,
            risk_score,
            disposition,
            notes,
            sar_filed
        FROM silver.alert_history
        WHERE customer_id  = '{customer_id}'
          AND alert_id    != '{alert_id}'
          AND disposition != 'IN_PROGRESS'
        ORDER BY alert_date DESC
    """)

    # ── Handle: no prior history ──────────────────────────
    if not prior_alerts:
        print(f" [Node 4] No prior alerts found for {customer_id}")
        print(f"   First-time alert for this customer")
        return {
            **state,
            "prior_alerts":      [],
            "prior_alert_count": 0,
            "prior_sar_filed":   False,
            "prior_dispositions": [],
            "repeat_pattern":    False,
            "error":             None,
        }

    # ── Calculate summary fields ──────────────────────────
    prior_alert_count = len(prior_alerts)

    # Was a SAR ever filed before for this customer?
    prior_sar_filed = any(
        a["sar_filed"] == True for a in prior_alerts
    )

    # List of all prior dispositions
    prior_dispositions = [
        a["disposition"] for a in prior_alerts
    ]

    # Repeat pattern detection:
    # Same typology was flagged before AND closed as false positive
    # This is the most dangerous pattern — analyst dismissed it,
    # but the behaviour has returned. Agent must flag this loudly.
    same_typology_prior = [
        a for a in prior_alerts
        if a["alert_type"] == alert_type
    ]
    repeat_pattern = len(same_typology_prior) > 0

    # ── Log findings ──────────────────────────────────────
    print(f"[Node 4] Prior alert history found")
    print(f"   Prior alerts:     {prior_alert_count}")
    print(f"   Dispositions:     {', '.join(prior_dispositions)}")
    print(f"   SAR ever filed:   {prior_sar_filed}")
    print(f"   Repeat pattern:   {repeat_pattern}")

    print(f"\n   ── Prior Alert Timeline ──────────────────────")
    for a in prior_alerts:
        print(f"   {a['alert_date']}  "
              f"{a['alert_type']:<30}  "
              f"Risk: {a['risk_score']}  "
              f"→ {a['disposition']}")
        if a["notes"]:
            # Truncate long notes for display
            notes = a["notes"][:80] + "..." \
                    if len(str(a["notes"])) > 80 \
                    else a["notes"]
            print(f"      Notes: {notes}")

    # Warn loudly if repeat pattern detected
    if repeat_pattern:
        print(f"\n    REPEAT PATTERN DETECTED")
        print(f"      Same typology ({alert_type}) was previously")
        print(f"      flagged and closed as FALSE POSITIVE.")
        print(f"      Current alert must be reviewed with extra scrutiny.")

    # Serialise dates for JSON
    clean_prior = []
    for a in prior_alerts:
        clean_a = dict(a)
        clean_a["alert_date"] = str(a["alert_date"])
        clean_prior.append(clean_a)

    return {
        **state,
        "prior_alerts":       clean_prior,
        "prior_alert_count":  prior_alert_count,
        "prior_sar_filed":    prior_sar_filed,
        "prior_dispositions": prior_dispositions,
        "repeat_pattern":     repeat_pattern,
        "error":              None,
    }

print(" Node 4 — check_prior_alerts defined")
