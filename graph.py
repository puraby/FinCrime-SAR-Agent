# ============================================================
# graph.py
# FinCrime SAR Agent — LangGraph Pipeline
# Author: Puraby Deb
# ============================================================
# Wires all 7 nodes into a LangGraph StateGraph.
#
#  START
#    │
#    ▼
#  fetch_alert ──(error)──────────────────────► END
#    │
#    ▼
#  enrich_customer
#    │
#    ▼
#  fetch_transactions
#    │
#    ▼
#  check_prior_alerts
#    │
#    ▼
#  screen_entities
#    │
#    ▼
#  score_and_route
#    │
#    ├── AUTO_CLOSE ──────────────────────────► END
#    ├── ESCALATE ────────────────────────────► END
#    └── SAR_DRAFT ──► draft_sar ──────────────► END
# ============================================================

from langgraph.graph import StateGraph, END
from setup import SARState, empty_state
from node_fetch_alert       import fetch_alert
from node_enrich_customer   import enrich_customer
from node_fetch_transaction import fetch_transactions
from node_check_prior_alerts import check_prior_alerts
from node_screen_entities   import screen_entities
from node_score_and_route   import score_and_route
from node_draft_sar         import draft_sar

# ── Add project to path + import agent ───────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graph import run_agent


# ── Routing: after fetch_alert ────────────────────────────
def route_after_fetch(state: SARState) -> str:
    if state.get("error"):
        print(f" Alert not found — stopping pipeline")
        return "end_error"
    return "enrich_customer"


# ── Routing: after score_and_route ────────────────────────
def route_after_scoring(state: SARState) -> str:
    if state.get("error"):
        print(f" Error in pipeline: {state['error']}")
        return "end_error"

    decision = state.get("routing_decision")

    if decision == "SAR_DRAFT":
        print(f"⚡ Graph routing → draft_sar")
        return "draft_sar"
    elif decision == "ESCALATE":
        print(f" Graph routing → END (escalate)")
        return "end_escalate"
    else:
        print(f"Graph routing → END (auto close)")
        return "end_close"


# ── Build graph ───────────────────────────────────────────
def build_graph():
    graph = StateGraph(SARState)

    # Add nodes
    graph.add_node("fetch_alert",         fetch_alert)
    graph.add_node("enrich_customer",     enrich_customer)
    graph.add_node("fetch_transactions",  fetch_transactions)
    graph.add_node("check_prior_alerts",  check_prior_alerts)
    graph.add_node("screen_entities",     screen_entities)
    graph.add_node("score_and_route",     score_and_route)
    graph.add_node("draft_sar",           draft_sar)

    # Entry point
    graph.set_entry_point("fetch_alert")

    # Conditional edge after fetch_alert
    graph.add_conditional_edges(
        "fetch_alert",
        route_after_fetch,
        {
            "enrich_customer": "enrich_customer",
            "end_error":        END,
        }
    )

    # Fixed edges
    graph.add_edge("enrich_customer",    "fetch_transactions")
    graph.add_edge("fetch_transactions", "check_prior_alerts")
    graph.add_edge("check_prior_alerts", "screen_entities")
    graph.add_edge("screen_entities",    "score_and_route")

    # Conditional edge after score_and_route
    graph.add_conditional_edges(
        "score_and_route",
        route_after_scoring,
        {
            "draft_sar":    "draft_sar",
            "end_escalate": END,
            "end_close":    END,
            "end_error":    END,
        }
    )

    # Final edge
    graph.add_edge("draft_sar", END)

    return graph.compile()


# ── run_agent() ───────────────────────────────────────────
# This is the single function app.py calls.
# Import this function — don't call it at module level.

def run_agent(alert_id: str) -> SARState:
    """
    Runs the full SAR pipeline for a given Alert ID.

    Usage:
        from graph import run_agent
        result = run_agent("ALT-2024-08821")
        print(result["sar_narrative"])
    """
    print(f"\n{'='*60}")
    print(f"  SAR AGENT STARTING — Alert: {alert_id}")
    print(f"{'='*60}")

    graph  = build_graph()
    result = graph.invoke(empty_state(alert_id))

    print(f"\n{'='*60}")
    print(f"  AGENT COMPLETE")
    print(f"  Alert:    {result.get('alert_id')}")
    print(f"  Customer: {result.get('customer_name')}")
    print(f"  Decision: {result.get('routing_decision')}")
    print(f"  Risk:     {result.get('agent_risk_score')}/100")
    if result.get("sar_narrative"):
        words = len(result["sar_narrative"].split())
        print(f"  SAR:      {result.get('sar_reference')} ({words} words)")
    if result.get("error"):
        print(f"  Error:    {result.get('error')}")
    print(f"{'='*60}\n")

    return result


print(" graph.py loaded — call run_agent(alert_id) to start")
