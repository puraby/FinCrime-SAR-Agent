
from setup import *
from node_fetch_alert import *
from node_enrich_customer import *
def fetch_transactions(state: SARState) -> SARState:
    """
    Node 3: Pull all transactions linked to the alert.
    Also calculates summary fields the SAR agent needs:
      - which branches were used
      - which channels (CASH, SWIFT etc)
      - destination countries
      - whether there is an offshore wire
    Input:  alert_id (from Node 1)
    Output: transactions list + summary fields
    """

    alert_id = state["alert_id"]
    print(f"\n💳 [Node 3] Fetching transactions for: {alert_id}")

    # ── Query all transactions for this alert ─────────────
    transactions = query(f"""
        SELECT
            txn_id,
            txn_date,
            txn_time,
            amount,
            currency,
            channel,
            direction,
            branch,
            branch_state,
            counterparty_id,
            counterparty_account,
            counterparty_bank,
            counterparty_country,
            reference,
            suspicious_flag,
            notes
        FROM silver.transactions
        WHERE alert_id = '{alert_id}'
        ORDER BY txn_date, txn_time
    """)

    if not transactions:
        print(f"❌ [Node 3] No transactions found for {alert_id}")
        return {**state, "error": f"No transactions found for {alert_id}"}

    # ── Calculate summary fields ──────────────────────────
    # These summaries are what the SAR narrative needs —
    # the agent doesn't want to loop through raw transactions

    # Unique branches used
    branches_used = list(set(
        t["branch"] for t in transactions
        if t["branch"] and t["channel"] == "CASH_DEPOSIT"
    ))

    # Unique channels used
    channels_used = list(set(
        t["channel"] for t in transactions
    ))

    # All destination countries
    counterparty_countries = list(set(
        t["counterparty_country"] for t in transactions
        if t["counterparty_country"]
    ))

    # Offshore wire detection
    # AU = domestic, anything else = offshore
    offshore_destinations = list(set(
        t["counterparty_country"] for t in transactions
        if t["counterparty_country"]
        and t["counterparty_country"] != "AU"
        and t["channel"] == "SWIFT_OUTWARD"
    ))
    has_offshore_wire = len(offshore_destinations) > 0

    # ── Log summary ───────────────────────────────────────
    cash_txns  = [t for t in transactions if t["channel"] == "CASH_DEPOSIT"]
    swift_txns = [t for t in transactions if t["channel"] == "SWIFT_OUTWARD"]
    cash_total = sum(t["amount"] for t in cash_txns)

    print(f"✅ [Node 3] Transactions loaded")
    print(f"   Total txns:     {len(transactions)}")
    print(f"   Cash deposits:  {len(cash_txns)} deposits = AUD ${cash_total:,.2f}")
    print(f"   SWIFT wires:    {len(swift_txns)}")
    print(f"   Branches used:  {len(branches_used)} → {', '.join(branches_used)}")
    print(f"   Offshore wire:  {has_offshore_wire}")
    if offshore_destinations:
        print(f"   Destinations:   {', '.join(offshore_destinations)}")

    print(f"\n   ── Transaction Timeline ──────────────────────")
    for t in transactions:
        direction = "↓ IN " if t["direction"] == "CREDIT" else "↑ OUT"
        country   = f"→ {t['counterparty_country']}" if t["counterparty_country"] != "AU" else ""
        print(f"   {t['txn_date']}  {direction}  "
              f"AUD ${t['amount']:>10,.2f}  "
              f"{t['channel']:<20}  "
              f"{country}")

    # Convert dates to strings for JSON serialisation
    clean_transactions = []
    for t in transactions:
        clean_t = dict(t)
        clean_t["txn_date"] = str(t["txn_date"])
        clean_transactions.append(clean_t)

    return {
        **state,
        "transactions":           clean_transactions,
        "branches_used":          branches_used,
        "channels_used":          channels_used,
        "counterparty_countries": counterparty_countries,
        "has_offshore_wire":      has_offshore_wire,
        "offshore_destinations":  offshore_destinations,
        "error":                  None,
    }

print("✅ Node 3 — fetch_transactions defined")