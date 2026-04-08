# node_fetch_alert.py
from setup import *

def fetch_alert(state: SARState) -> SARState:
    alert_id = state["alert_id"]
    print(f"\n🔍 [Node 1] Fetching alert: {alert_id}")

    alert = query_one(f"""
        SELECT alert_id, customer_id, account_id, rule_id,
               rule_name, alert_type, alert_subtype, risk_score,
               risk_tier, total_amount, transaction_count,
               period_start, period_end, detected_at,
               status, sar_filed, model_version, notes
        FROM silver.alerts
        WHERE alert_id = '{alert_id}'
    """)

    if not alert:
        print(f" [Node 1] Alert {alert_id} not found")
        return {**state, "error": f"Alert {alert_id} not found in silver.alerts"}

    print(f" [Node 1] Alert found")
    print(f"   Type:       {alert['alert_type']} — {alert['alert_subtype']}")
    print(f"   Risk Score: {alert['risk_score']} ({alert['risk_tier']})")
    print(f"   Amount:     AUD ${alert['total_amount']:,.2f}")
    print(f"   Period:     {alert['period_start']} → {alert['period_end']}")
    print(f"   Customer:   {alert['customer_id']}")

    return {
        **state,
        "rule_name":         alert["rule_name"],
        "alert_type":        alert["alert_type"],
        "alert_subtype":     alert["alert_subtype"],
        "risk_score":        alert["risk_score"],
        "risk_tier":         alert["risk_tier"],
        "total_amount":      alert["total_amount"],
        "transaction_count": alert["transaction_count"],
        "period_start":      str(alert["period_start"]),
        "period_end":        str(alert["period_end"]),
        "detected_at":       str(alert["detected_at"]),
        "alert_notes":       alert["notes"],
        "customer_id":       alert["customer_id"],
        "account_id":        alert["account_id"],
        "error":             None,
    }
