
import streamlit as st
import sys
import time
# ── Add project to path + import agent ───────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graph import run_agent

# ── Page config ───────────────────────────────────────────
st.set_page_config(
    page_title  = "FinCrime SAR Agent",
    page_icon   = "🏦",
    layout      = "wide",
    initial_sidebar_state = "expanded"

)

# ── Custom CSS ────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1a1612, #2d2420);
        padding: 20px 32px;
        border-radius: 8px;
        border-left: 4px solid #c1440e;
        margin-bottom: 24px;
    }
    .main-header h1 {
        color: white;
        font-size: 24px;
        margin: 0;
    }
    .main-header p {
        color: #8c8070;
        font-size: 12px;
        margin: 4px 0 0 0;
        font-family: monospace;
    }
    .step-box {
        padding: 12px 16px;
        border-radius: 6px;
        margin: 6px 0;
        font-family: monospace;
        font-size: 13px;
    }
    .step-running {
        background: rgba(154,109,26,0.1);
        border-left: 3px solid #9a6d1a;
        color: #9a6d1a;
    }
    .step-done {
        background: rgba(26,92,58,0.1);
        border-left: 3px solid #1a5c3a;
        color: #1a5c3a;
    }
    .step-wait {
        background: rgba(0,0,0,0.03);
        border-left: 3px solid #d4cfc4;
        color: #8c8070;
    }
    .sar-section {
        background: white;
        border: 1px solid #d4cfc4;
        border-radius: 6px;
        padding: 20px;
        margin: 12px 0;
    }
    .sar-section h4 {
        color: #1a1612;
        border-bottom: 1px solid #d4cfc4;
        padding-bottom: 8px;
        margin-bottom: 12px;
    }
    .metric-box {
        background: #faf8f3;
        border: 1px solid #d4cfc4;
        border-radius: 6px;
        padding: 12px;
        text-align: center;
    }
    .red-flag {
        background: rgba(193,68,14,0.05);
        border-left: 3px solid #c1440e;
        padding: 8px 12px;
        margin: 4px 0;
        font-size: 13px;
        border-radius: 0 4px 4px 0;
    }
    .verdict-critical {
        background: rgba(193,68,14,0.1);
        border: 2px solid #c1440e;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .verdict-escalate {
        background: rgba(154,109,26,0.1);
        border: 2px solid #9a6d1a;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .verdict-close {
        background: rgba(26,92,58,0.1);
        border: 2px solid #1a5c3a;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏦 FinCrime SAR Agent</h1>
    <p>AUSTRAC SMR DRAFTING PIPELINE · POWERED BY LANGGRAPH · AI-ASSISTED · ANALYST REVIEW REQUIRED</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 Quick Reference")
    st.markdown("**Test Alert IDs:**")
    st.code("ALT-2024-08821")
    st.caption("CRITICAL — Morrison / Structuring + Vanuatu wire")
    st.code("ALT-2024-08734")
    st.caption("HIGH — Tran / Cash business deviation")
    st.code("ALT-2024-08612")
    st.caption("CRITICAL — Kowalski / PAYG + Philippines wire")
    st.divider()
    st.markdown("### ⚙️ Pipeline Nodes")
    st.markdown("""
    1. 🔍 Fetch Alert
    2. 👤 Enrich Customer
    3. 💳 Fetch Transactions
    4. 📋 Check Prior Alerts
    5. 🌐 Screen Entities
    6. ⚖️ Score & Route
    7. 📝 Draft SAR
    """)
    st.divider()
    st.caption("FinCrime AI Agent v1.0")
    st.caption("Not for production use without compliance review")

# ── Main layout ───────────────────────────────────────────
col_left, col_right = st.columns([1, 1.6])

with col_left:
    st.markdown("### Enter Alert ID")
    alert_id = st.text_input(
        label       = "Alert ID",
        placeholder = "e.g. ALT-2024-08821",
        label_visibility = "collapsed"
    )

    run_btn = st.button(
        "⚡ Run Agent",
        type = "primary",
        use_container_width = True,
        disabled = not alert_id
    )

    # ── Agent steps display ───────────────────────────────
    if run_btn and alert_id:

        st.markdown("### 🤖 Agent Running")

        # Define steps
        steps = [
            ("🔍", "Fetch Alert",         "Querying silver.alerts..."),
            ("👤", "Enrich Customer",     "Pulling CIF + account data..."),
            ("💳", "Fetch Transactions",  "Loading transaction timeline..."),
            ("📋", "Check Prior Alerts",  "Scanning alert history..."),
            ("🌐", "Screen Entities",     "Checking FATF + counterparties..."),
            ("⚖️",  "Score & Route",      "Calculating risk + routing..."),
            ("📝", "Draft SAR",           "Calling LLM — generating narrative..."),
        ]

        # Create placeholder for each step
        step_placeholders = []
        for icon, name, desc in steps:
            ph = st.empty()
            ph.markdown(
                f'<div class="step-box step-wait">'
                f'{icon} {name} — waiting</div>',
                unsafe_allow_html=True
            )
            step_placeholders.append(ph)

        # ── Run the graph ─────────────────────────────────
        # We stream step updates by running nodes manually
        # and updating placeholders as each completes

        result = None
        start_time = time.time()

        try:
            # Import run_agent from graph
            # (already loaded via %run in notebook)
            step_placeholders[0].markdown(
                f'<div class="step-box step-running">'
                f'🔍 Fetch Alert — running...</div>',
                unsafe_allow_html=True
            )

            # Run full pipeline
            result = run_agent(alert_id)

            # Update all steps to done
            icons_names = [(s[0], s[1]) for s in steps]
            for i, (icon, name) in enumerate(icons_names):
                step_placeholders[i].markdown(
                    f'<div class="step-box step-done">'
                    f'✅ {name} — complete</div>',
                    unsafe_allow_html=True
                )
                time.sleep(0.15)  # stagger for visual effect

        except Exception as e:
            st.error(f"❌ Agent error: {str(e)}")
            result = None

        # ── Store result in session state ─────────────────
        if result:
            st.session_state["result"]   = result
            st.session_state["alert_id"] = alert_id
            elapsed = round(time.time() - start_time, 1)
            st.success(f"✅ Pipeline complete in {elapsed}s")

        # ── Error display ─────────────────────────────────
        if result and result.get("error"):
            st.error(f"⛔ {result['error']}")

# ── Right column — Results ────────────────────────────────
with col_right:

    result = st.session_state.get("result")

    if not result:
        st.markdown("### Results")
        st.info("Enter an Alert ID and click Run Agent to begin.")

    elif result.get("error") and not result.get("sar_narrative"):
        st.error(f"⛔ {result['error']}")

    else:
        # ── Metrics row ───────────────────────────────────
        st.markdown("### 📊 Alert Summary")
        m1, m2, m3, m4 = st.columns(4)

        with m1:
            st.metric("Risk Score",
                      f"{result.get('agent_risk_score')}/100")
        with m2:
            st.metric("Red Flags",
                      len(result.get("red_flags") or []))
        with m3:
            st.metric("Transactions",
                      result.get("transaction_count"))
        with m4:
            st.metric("Amount",
                      f"${result.get('total_amount'):,.0f}")

        # ── Verdict ───────────────────────────────────────
        decision = result.get("routing_decision")
        if decision == "SAR_DRAFT":
            st.markdown("""
            <div class="verdict-critical">
                <h3 style="color:#c1440e;margin:0">
                ⚡ VERDICT: DRAFT SAR</h3>
                <p style="color:#8c8070;margin:4px 0 0 0;font-size:12px">
                Sufficient indicators for AUSTRAC SMR filing</p>
            </div>""", unsafe_allow_html=True)
        elif decision == "ESCALATE":
            st.markdown("""
            <div class="verdict-escalate">
                <h3 style="color:#9a6d1a;margin:0">
                📤 VERDICT: ESCALATE TO L2</h3>
                <p style="color:#8c8070;margin:4px 0 0 0;font-size:12px">
                Ambiguous case — requires senior analyst review</p>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="verdict-close">
                <h3 style="color:#1a5c3a;margin:0">
                ✅ VERDICT: AUTO CLOSE</h3>
                <p style="color:#8c8070;margin:4px 0 0 0;font-size:12px">
                Insufficient indicators for SAR filing</p>
            </div>""", unsafe_allow_html=True)

        st.divider()

        # ── Customer + Account ────────────────────────────
        with st.expander("👤 Customer Profile", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Name:** {result.get('customer_name')}")
                st.markdown(f"**DOB:** {result.get('dob')}")
                st.markdown(f"**Occupation:** {result.get('occupation')}")
                st.markdown(f"**Employer:** {result.get('employer')}")
                st.markdown(f"**Address:** {result.get('address')}")
            with c2:
                st.markdown(f"**Customer Since:** {result.get('customer_since')}")
                st.markdown(f"**KYC Tier:** {result.get('kyc_tier')}")
                st.markdown(f"**Risk Rating:** {result.get('risk_rating')}")
                st.markdown(f"**PEP Flag:** {result.get('pep_flag')}")
                st.markdown(f"**Account:** {result.get('bsb')} / {result.get('account_number')}")

        # ── Red Flags ─────────────────────────────────────
        with st.expander(
            f"🚩 Red Flags ({len(result.get('red_flags') or [])} identified)",
            expanded=True
        ):
            for flag in (result.get("red_flags") or []):
                st.markdown(
                    f'<div class="red-flag">⚠️ {flag}</div>',
                    unsafe_allow_html=True
                )

        # ── FATF + Counterparties ─────────────────────────
        with st.expander("🌐 Entity Screening", expanded=False):
            if result.get("fatf_hits"):
                st.error(f"🚨 FATF Hits: {', '.join(result['fatf_hits'])}")
            if result.get("flagged_entities"):
                st.warning(f"⚠️ Flagged: {', '.join(result['flagged_entities'])}")
            st.markdown(f"**Sanctions Hit:** {result.get('sanctions_hit')}")
            st.markdown(f"**Offshore Wire:** {result.get('has_offshore_wire')}")
            st.markdown(f"**Destinations:** {', '.join(result.get('offshore_destinations') or [])}")

        # ── SAR Narrative ─────────────────────────────────
        if result.get("sar_narrative"):
            st.divider()
            st.markdown("### 📄 SAR Narrative")

            # Reference + metadata
            col_ref, col_model, col_time = st.columns(3)
            with col_ref:
                st.caption(f"📋 {result.get('sar_reference')}")
            with col_model:
                st.caption(f"🤖 {result.get('model_used')}")
            with col_time:
                st.caption(f"🕐 {result.get('draft_timestamp')}")

            # Full narrative in editable text area
            # Analyst can edit before approving
            edited_narrative = st.text_area(
                label        = "SAR Narrative (editable)",
                value        = result.get("sar_narrative"),
                height       = 500,
                label_visibility = "collapsed"
            )

            # ── Action buttons ────────────────────────────
            st.markdown("#### Analyst Action")
            b1, b2, b3 = st.columns(3)

            with b1:
                if st.button(
                    "✅ Approve & Save",
                    type="primary",
                    use_container_width=True
                ):
                    # Save to gold.sar_drafts Delta table
                    try:
                        from pyspark.sql import SparkSession
                        from datetime import datetime
                        spark = SparkSession.builder.getOrCreate()

                        save_data = [{
                            "sar_reference":   result["sar_reference"],
                            "alert_id":        result["alert_id"],
                            "customer_id":     result.get("customer_id"),
                            "customer_name":   result.get("customer_name"),
                            "alert_type":      result.get("alert_type"),
                            "risk_score":      result.get("agent_risk_score"),
                            "routing":         result.get("routing_decision"),
                            "sar_narrative":   edited_narrative,
                            "model_used":      result.get("model_used"),
                            "draft_timestamp": result.get("draft_timestamp"),
                            "approved_at":     datetime.now().strftime(
                                                "%Y-%m-%d %H:%M:%S"),
                            "status":          "APPROVED",
                        }]

                        df = spark.createDataFrame(save_data)
                        df.write                           .format("delta")                           .mode("append")                           .option("mergeSchema", "true")                           .saveAsTable("gold.sar_drafts")

                        st.success(
                            f"✅ SAR saved to gold.sar_drafts — "
                            f"{result['sar_reference']}"
                        )
                    except Exception as e:
                        st.error(f"Save failed: {e}")

            with b2:
                if st.button(
                    "📤 Escalate to L2",
                    use_container_width=True
                ):
                    st.warning("📤 Alert escalated to L2 analyst queue")

            with b3:
                if st.button(
                    "❌ Reject & Close",
                    use_container_width=True
                ):
                    st.info("✅ Alert closed — no suspicious activity")
