# ============================================================
# setup.py
# FinCrime SAR Agent — Shared Setup
# Author: Puraby Deb
# ============================================================
# Contains:
#   1. Libraries
#   2. Databricks token + gateway config
#   3. SARState definition
#   4. DB connector (query, query_one)
#   5. empty_state() helper
#   6. print_state() helper
# ============================================================

import os
import requests
from typing import TypedDict, Optional, List
from datetime import datetime
from pyspark.sql import SparkSession

# ── Databricks token ──────────────────────────────────────
try:
    DATABRICKS_TOKEN = (
        dbutils.notebook.entry_point
        .getDbutils().notebook().getContext()
        .apiToken().get()
    )
    print("✅ Databricks token loaded from dbutils")
except NameError:
    DATABRICKS_TOKEN = os.environ.get("DATABRICKS_TOKEN", "")
    if DATABRICKS_TOKEN:
        print("✅ Databricks token loaded from environment")
    else:
        print("⚠️  DATABRICKS_TOKEN not found — set via environment variable")

DATABRICKS_GATEWAY = "https://7474647235375729.ai-gateway.cloud.databricks.com/mlflow/v1/chat/completions"
DATABRICKS_MODEL   = "databricks-meta-llama-3-1-8b-instruct"

if DATABRICKS_TOKEN:
    os.environ["DATABRICKS_TOKEN"] = DATABRICKS_TOKEN

print(f"   Gateway: {DATABRICKS_GATEWAY}")
print(f"   Model:   {DATABRICKS_MODEL}")


# ── SARState ──────────────────────────────────────────────
class SARState(TypedDict):
    # INPUT — analyst provides only this
    alert_id:               str

    # NODE 1 — fetch_alert
    rule_name:              Optional[str]
    alert_type:             Optional[str]
    alert_subtype:          Optional[str]
    risk_score:             Optional[int]
    risk_tier:              Optional[str]
    total_amount:           Optional[float]
    transaction_count:      Optional[int]
    period_start:           Optional[str]
    period_end:             Optional[str]
    detected_at:            Optional[str]
    alert_notes:            Optional[str]
    customer_id:            Optional[str]
    account_id:             Optional[str]

    # NODE 2 — enrich_customer
    customer_name:          Optional[str]
    dob:                    Optional[str]
    occupation:             Optional[str]
    employer:               Optional[str]
    industry:               Optional[str]
    annual_income:          Optional[float]
    address:                Optional[str]
    state:                  Optional[str]
    customer_since:         Optional[str]
    kyc_tier:               Optional[str]
    kyc_last_review:        Optional[str]
    risk_rating:            Optional[str]
    pep_flag:               Optional[bool]
    fatca_flag:             Optional[bool]
    adverse_media:          Optional[bool]
    customer_notes:         Optional[str]
    bsb:                    Optional[str]
    account_number:         Optional[str]
    account_type:           Optional[str]
    avg_monthly_credit:     Optional[float]
    avg_monthly_debit:      Optional[float]

    # NODE 3 — fetch_transactions
    transactions:           Optional[List[dict]]
    branches_used:          Optional[List[str]]
    channels_used:          Optional[List[str]]
    counterparty_countries: Optional[List[str]]
    has_offshore_wire:      Optional[bool]
    offshore_destinations:  Optional[List[str]]

    # NODE 4 — check_prior_alerts
    prior_alerts:           Optional[List[dict]]
    prior_alert_count:      Optional[int]
    prior_sar_filed:        Optional[bool]
    prior_dispositions:     Optional[List[str]]
    repeat_pattern:         Optional[bool]

    # NODE 5 — screen_entities
    counterparties:         Optional[List[dict]]
    fatf_hits:              Optional[List[str]]
    flagged_entities:       Optional[List[str]]
    sanctions_hit:          Optional[bool]
    pep_network_hit:        Optional[bool]

    # NODE 6 — score_and_route
    agent_risk_score:       Optional[int]
    routing_decision:       Optional[str]
    routing_reason:         Optional[str]
    red_flags:              Optional[List[str]]

    # NODE 7 — draft_sar
    sar_narrative:          Optional[str]
    sar_reference:          Optional[str]
    draft_timestamp:        Optional[str]
    model_used:             Optional[str]

    # ERROR handling
    error:                  Optional[str]


# ── DB Connector ──────────────────────────────────────────
def query(sql: str) -> list:
    """Run SQL, return list of dicts."""
    _spark = SparkSession.getActiveSession()
    if _spark is None:
        raise RuntimeError(
            "No active Spark session. "
            "Make sure your Databricks compute is running."
        )
    return [row.asDict() for row in _spark.sql(sql).collect()]


def query_one(sql: str) -> dict | None:
    """Run SQL, return first row as dict or None."""
    results = query(sql)
    return results[0] if results else None


# ── empty_state() ─────────────────────────────────────────
def empty_state(alert_id: str) -> SARState:
    """Creates a blank SARState with just an alert_id."""
    fields = SARState.__annotations__
    state  = {k: None for k in fields}
    state["alert_id"] = alert_id
    return state


# ── print_state() ─────────────────────────────────────────
def print_state(state: SARState):
    """Pretty prints current state — useful for debugging."""
    populated = {k: v for k, v in state.items() if v is not None}
    empty_flds = [k for k, v in state.items() if v is None]
    print(f"\n{'='*55}")
    print(f"  STATE SNAPSHOT — Alert: {state['alert_id']}")
    print(f"{'='*55}")
    print(f"  Populated: {len(populated)}  |  Empty: {len(empty_flds)}")
    print(f"\n  ── Populated ──────────────────────────────────")
    for k, v in populated.items():
        display = str(v)[:57] + "..." if len(str(v)) > 60 else str(v)
        print(f"    ✅  {k:<25} {display}")
    print(f"{'='*55}\n")


print("✅ setup.py loaded")
print("   SARState, query, query_one, empty_state, print_state → ready")