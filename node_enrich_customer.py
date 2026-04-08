from setup import *
from node_fetch_alert import *
def enrich_customer(state: SARState) -> SARState:
    """
    Node 2: Pull full customer profile + account details
    Input:  customer_id, account_id (from Node 1)
    Output: name, dob, occupation, address, kyc, account info
    """

    customer_id = state["customer_id"]
    account_id  = state["account_id"]

    print(f"\n👤 [Node 2] Enriching customer: {customer_id}")

    # ── Query customer ────────────────────────────────────
    customer = query_one(f"""
        SELECT
            customer_id,
            full_name,
            dob,
            occupation,
            employer,
            industry,
            annual_income,
            address,
            state,
            customer_since,
            kyc_tier,
            kyc_last_review,
            risk_rating,
            pep_flag,
            fatca_flag,
            adverse_media,
            notes
        FROM silver.customers
        WHERE customer_id = '{customer_id}'
    """)

    if not customer:
        print(f"❌ [Node 2] Customer {customer_id} not found")
        return {**state, "error": f"Customer {customer_id} not found"}

    # ── Query account ─────────────────────────────────────
    account = query_one(f"""
        SELECT
            account_id,
            bsb,
            account_number,
            account_type,
            product,
            open_date,
            avg_monthly_credit,
            avg_monthly_debit
        FROM silver.accounts
        WHERE account_id = '{account_id}'
    """)

    if not account:
        print(f"❌ [Node 2] Account {account_id} not found")
        return {**state, "error": f"Account {account_id} not found"}

    # ── Log what we found ─────────────────────────────────
    print(f"✅ [Node 2] Customer found")
    print(f"   Name:          {customer['full_name']}")
    print(f"   DOB:           {customer['dob']}")
    print(f"   Occupation:    {customer['occupation']} @ {customer['employer']}")
    print(f"   Address:       {customer['address']}")
    print(f"   Customer Since:{customer['customer_since']}")
    print(f"   KYC Tier:      {customer['kyc_tier']} (last review: {customer['kyc_last_review']})")
    print(f"   Risk Rating:   {customer['risk_rating']}")
    print(f"   PEP Flag:      {customer['pep_flag']}")
    print(f"   Account:       {account['bsb']} {account['account_number']} ({account['account_type']})")
    print(f"   Avg Credit:    AUD ${account['avg_monthly_credit']:,.2f}/month")
    print(f"   Avg Debit:     AUD ${account['avg_monthly_debit']:,.2f}/month")

    return {
        **state,
        "customer_name":      customer["full_name"],
        "dob":                str(customer["dob"]),
        "occupation":         customer["occupation"],
        "employer":           customer["employer"],
        "industry":           customer["industry"],
        "annual_income":      customer["annual_income"],
        "address":            customer["address"],
        "state":              customer["state"],
        "customer_since":     str(customer["customer_since"]),
        "kyc_tier":           customer["kyc_tier"],
        "kyc_last_review":    str(customer["kyc_last_review"]),
        "risk_rating":        customer["risk_rating"],
        "pep_flag":           bool(customer["pep_flag"]),
        "fatca_flag":         bool(customer["fatca_flag"]),
        "adverse_media":      bool(customer["adverse_media"]),
        "customer_notes":     customer["notes"],
        "bsb":                account["bsb"],
        "account_number":     account["account_number"],
        "account_type":       account["account_type"],
        "avg_monthly_credit": account["avg_monthly_credit"],
        "avg_monthly_debit":  account["avg_monthly_debit"],
        "error":              None,
    }

print("✅ Node 2 — enrich_customer defined")