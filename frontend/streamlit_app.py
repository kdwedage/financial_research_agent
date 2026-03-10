"""Streamlit frontend for the Autonomous Financial Research Agent."""
import os
import sys
from pathlib import Path

# Ensure app is on path when running from frontend/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from langgraph.types import Command
from app.graph import build_graph
from app.state import ResearchState
from app.evaluation import get_analyst_consensus_reference, score_report_quality
from app.memory import add_research_memory, search_similar_research
from app.report_schema import ApprovalStatus

st.set_page_config(page_title="Financial Research Agent", page_icon="📊", layout="wide")

st.title("📊 Autonomous Financial Research Agent")
st.caption("Multi-agent pipeline: Data → Analysis → Sentiment → Risk → Synthesis → Human Approval")

symbol = st.text_input("Ticker symbol", value="AAPL", max_chars=10).strip().upper()
if not symbol:
    st.info("Enter a publicly traded ticker (e.g. AAPL, MSFT, GOOGL).")
    st.stop()

# Checkpointing for human-in-the-loop resume
thread_id = f"research_{symbol}"
checkpointer = __import__("langgraph.checkpoint.memory", fromlist=["MemorySaver"]).MemorySaver()
graph = build_graph(checkpointer=checkpointer)
config = {"configurable": {"thread_id": thread_id}}

if "final_state" not in st.session_state:
    st.session_state.final_state = None
if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = False

def run_pipeline(resume_with=None):
    if resume_with is not None:
        return graph.invoke(Command(resume=resume_with), config=config)
    return graph.invoke({"symbol": symbol}, config=config)

col1, col2 = st.columns([1, 3])
with col1:
    run_clicked = st.button("Run research pipeline")
with col2:
    if os.getenv("REQUIRE_HUMAN_APPROVAL", "true").lower() != "true":
        st.caption("Human approval is disabled (REQUIRE_HUMAN_APPROVAL=false).")

# Check if we're paused at human approval (same thread)
try:
    snap = graph.get_state(config)
    at_interrupt = bool(snap and getattr(snap, "next", None))
except Exception:
    snap = None
    at_interrupt = False

if at_interrupt and not run_clicked:
    st.session_state.pending_approval = True
    st.subheader("Human-in-the-loop: Review & Approve")
    # Show last state so user can see the report
    values = snap.values if snap else {}
    report_for_review = values.get("report")
    if report_for_review:
        if hasattr(report_for_review, "model_dump"):
            st.json(report_for_review.model_dump())
        else:
            st.json(report_for_review)
    with st.form("approval_form"):
        approved = st.radio("Approve this report for publication?", ["Approve", "Reject"], horizontal=True)
        reviewer = st.text_input("Reviewer name (optional)", value="")
        submitted = st.form_submit_button("Submit decision")
        if submitted:
            decision = {"approved": approved == "Approve", "reviewer": reviewer or "human"}
            with st.spinner("Resuming pipeline..."):
                final = run_pipeline(resume_with=decision)
                st.session_state.final_state = final
                st.session_state.pending_approval = False
            st.rerun()
    st.stop()

if run_clicked:
    with st.spinner("Running pipeline: Data → Analysis → Sentiment → Risk → Synthesis..."):
        try:
            final_state = run_pipeline()
            st.session_state.final_state = final_state
            # Check again if we stopped at interrupt (approval step)
            snap = graph.get_state(config)
            if getattr(snap, "next", None):
                st.session_state.pending_approval = True
                st.rerun()
        except Exception as e:
            st.error(str(e))
            st.stop()
    st.rerun()

# Display final state
state = st.session_state.final_state
if state and state.get("error"):
    st.error(state["error"])
if state:
    report = state.get("report")
    if report:
        st.success("Pipeline completed.")
        if hasattr(report, "model_dump"):
            r = report.model_dump()
        else:
            r = report

        st.subheader("Investment Brief")
        st.markdown(f"**{r.get('company_name', symbol)}** ({r.get('company_symbol', symbol)})")
        st.markdown("#### Executive summary")
        st.write(r.get("executive_summary", ""))
        st.markdown("#### Quantitative metrics")
        qm = r.get("quantitative_metrics") or {}
        st.write(f"P/E: {qm.get('pe_ratio')} | Revenue growth YoY: {qm.get('revenue_growth_yoy')}% | D/E: {qm.get('debt_to_equity')} | Current ratio: {qm.get('current_ratio')}")
        st.markdown("#### Sentiment")
        ss = r.get("sentiment_summary") or {}
        st.write(ss.get("news_sentiment", ""), "—", ss.get("earnings_tone", ""))
        st.markdown("#### Risk factors")
        rf = r.get("risk_factors") or {}
        st.write("Regulatory:", rf.get("regulatory_risks", []), "| Macro:", rf.get("macro_risks", []), "| Sector:", rf.get("sector_risks", []))
        st.markdown("#### Data sources")
        st.write(", ".join(r.get("data_sources", [])))
        st.write("**Approval status:**", r.get("approval_status", "N/A"))

        # Evaluation
        st.subheader("Evaluation (vs analyst consensus)")
        consensus = get_analyst_consensus_reference(symbol)
        scores = score_report_quality(report, consensus=consensus)
        st.metric("Overall score", f"{scores.get('overall_score', 0)} / 100")
        st.write("Grade:", scores.get("grade", "N/A"), "| Completeness:", scores.get("completeness"), "| Structure:", scores.get("structure"))
        if consensus:
            st.write("Consensus alignment:", scores.get("consensus_alignment"))
        st.json(scores)

        # Persist to memory (Chroma)
        if os.getenv("OPENAI_API_KEY"):
            try:
                add_research_memory(symbol, r.get("company_name", symbol), r.get("executive_summary", "")[:1000], r)
                st.caption("This run was stored in vector memory for future retrieval.")
            except Exception:
                pass

# Similar research search
st.sidebar.header("Memory")
query = st.sidebar.text_input("Search past research", placeholder="e.g. tech revenue growth")
if query and os.getenv("OPENAI_API_KEY"):
    try:
        docs = search_similar_research(query, k=3)
        for d in docs:
            st.sidebar.write("—", d.metadata.get("symbol", ""), ":", d.page_content[:100] + "...")
    except Exception:
        st.sidebar.caption("Memory search unavailable.")
