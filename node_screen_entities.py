
from setup import *
from node_fetch_alert import *
from node_enrich_customer import *
from node_fetch_transaction import *
from node_check_prior_alerts import *
def screen_entities(state: SARState) -> SARState:
    """
    Node 5: Screen all counterparties linked to this alert.
    Checks for:
      - FATF grey/black list jurisdictions
      - Flagged entities in our counterparty table
      - PEP network connections
      - Sanctions exposure
    Input:  transactions (from Node 3) — contains counterparty_ids
    Output: counterparties, fatf_hits, flagged_entities,
            sanctions_hit, pep_network_hit
    """

    alert_id     = state["alert_id"]
    transactions = state["transactions"]

    print(f"\n🌐 [Node 5] Screening entities for: {alert_id}")

    # ── FATF grey and black list countries ────────────────
    # Source: FATF public list (as of 2024)
    FATF_GREY_LIST  = [
        "BF", "CM", "CG", "CI", "HR", "ET", "HT",
        "KE", "LB", "ML", "MZ", "NA", "NG", "PH",
        "SA", "SN", "SS", "SY", "TZ", "TT", "VN",
        "VU", "YE"
    ]
    FATF_BLACK_LIST = ["KP", "IR", "MM"]  # North Korea, Iran, Myanmar

    # ── Extract unique counterparty IDs from transactions ─
    counterparty_ids = list(set(
        t["counterparty_id"]
        for t in transactions
        if t.get("counterparty_id")
    ))

    print(f"   Counterparty IDs found: {counterparty_ids}")

    # ── Query counterparty details ────────────────────────
    counterparties = []
    if counterparty_ids:
        id_list = "', '".join(counterparty_ids)
        counterparties = query(f"""
            SELECT
                counterparty_id,
                name,
                account_number,
                bank_name,
                bank_country,
                bank_swift,
                fatf_status,
                relationship_to_cust,
                flagged,
                notes
            FROM silver.counterparties
            WHERE counterparty_id IN ('{id_list}')
        """)

    # ── Also check destination countries directly ─────────
    # Even if counterparty isn't in our table,
    # the country itself might be on FATF list
    offshore_destinations = state.get("offshore_destinations") or []

    # ── Calculate risk fields ─────────────────────────────

    # FATF hits — countries in transaction destinations
    all_countries = (
        [c["bank_country"] for c in counterparties]
        + offshore_destinations
    )
    fatf_hits = list(set(
        country for country in all_countries
        if country in FATF_GREY_LIST + FATF_BLACK_LIST
    ))

    # Flagged entities — in our counterparty watchlist
    flagged_entities = [
        c["name"] for c in counterparties
        if c.get("flagged") == True
    ]

    # Sanctions hit — black list country or flagged entity
    sanctions_hit = any(
        c in FATF_BLACK_LIST for c in all_countries
    )

    # PEP network — counterparty linked to PEP
    pep_network_hit = (
        state.get("pep_flag") == True or
        any(
            "pep" in str(c.get("notes", "")).lower()
            for c in counterparties
        )
    )

    # ── Log findings ──────────────────────────────────────
    print(f"✅ [Node 5] Entity screening complete")
    print(f"   Counterparties screened: {len(counterparties)}")
    print(f"   FATF hits:               {fatf_hits}")
    print(f"   Flagged entities:        {flagged_entities}")
    print(f"   Sanctions hit:           {sanctions_hit}")
    print(f"   PEP network hit:         {pep_network_hit}")

    if counterparties:
        print(f"\n   ── Counterparty Details ──────────────────────")
        for c in counterparties:
            flag = "🚨" if c.get("flagged") else "✅"
            fatf = f"⚠️  FATF {c['fatf_status']}" \
                   if c["fatf_status"] != "STANDARD" else ""
            print(f"   {flag} {c['name']}")
            print(f"      Bank:         {c['bank_name']} ({c['bank_country']}) {fatf}")
            print(f"      SWIFT:        {c['bank_swift']}")
            print(f"      Relationship: {c['relationship_to_cust']}")
            if c["notes"]:
                notes = str(c["notes"])[:80] + "..." \
                        if len(str(c["notes"])) > 80 \
                        else c["notes"]
                print(f"      Notes:        {notes}")

    if fatf_hits:
        print(f"\n   🚨 FATF JURISDICTION ALERT")
        for country in fatf_hits:
            list_type = "BLACK LIST" \
                        if country in FATF_BLACK_LIST \
                        else "GREY LIST"
            print(f"      {country} → FATF {list_type}")

    return {
        **state,
        "counterparties":  counterparties,
        "fatf_hits":       fatf_hits,
        "flagged_entities": flagged_entities,
        "sanctions_hit":   sanctions_hit,
        "pep_network_hit": pep_network_hit,
        "error":           None,
    }

print("✅ Node 5 — screen_entities defined")