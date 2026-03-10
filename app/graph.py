"""LangGraph workflow: data -> analysis -> sentiment -> risk -> synthesis -> human approval."""
from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

from app.state import ResearchState
from app.report_schema import ApprovalStatus
from app.agents.data_agent import run_data_agent
from app.agents.analysis_agent import run_analysis_agent
from app.agents.sentiment_agent import run_sentiment_agent
from app.agents.risk_agent import run_risk_agent
from app.agents.synthesis_agent import run_synthesis_agent
from app.tools.alpha_vantage import get_company_overview, get_income_statement, get_balance_sheet
from app.tools.yahoo_finance import get_quote, get_news
from app.tools.sec_edgar import get_recent_filings


def _gather_raw_data(symbol: str) -> tuple[dict, list[str], str]:
    """Call data APIs and return (raw_data, data_sources, data_summary)."""
    raw: dict = {}
    sources: list[str] = []
    summary_parts: list[str] = []

    ov = get_company_overview(symbol)
    if "error" not in ov:
        raw["overview"] = ov
        sources.append("Alpha Vantage (OVERVIEW)")
        summary_parts.append(f"Sector: {ov.get('Sector', 'N/A')}; {ov.get('Description', '')[:500]}")
    else:
        raw["overview"] = {}

    q = get_quote(symbol)
    if "error" not in q:
        raw["quote"] = q
        sources.append("Yahoo Finance (Quote)")
        summary_parts.append(f"Price: {q.get('currentPrice')}; P/E: {q.get('peRatio')}; Market cap: {q.get('marketCap')}")
    else:
        raw["quote"] = {}

    inc_av = get_income_statement(symbol, limit=5)
    if "annualReports" in inc_av:
        raw["income_reports"] = inc_av["annualReports"]
        sources.append("Alpha Vantage (Income Statement)")
    bal_av = get_balance_sheet(symbol, limit=5)
    if "annualReports" in bal_av:
        raw["balance_reports"] = bal_av["annualReports"]
        sources.append("Alpha Vantage (Balance Sheet)")

    yf_fin = __import__("app.tools.yahoo_finance", fromlist=["get_financials_df"]).get_financials_df(symbol)
    if "error" not in yf_fin:
        raw["income_stmt"] = yf_fin.get("income_stmt", {})
        raw["balance_sheet"] = yf_fin.get("balance_sheet", {})
        if "Yahoo Finance (Financials)" not in sources:
            sources.append("Yahoo Finance (Financials)")

    news = get_news(symbol, count=10)
    if "error" not in news:
        raw["news"] = news.get("news", [])
        sources.append("Yahoo Finance (News)")
    else:
        raw["news"] = []

    sec = get_recent_filings(symbol, limit=5)
    if "error" not in sec:
        raw["sec_filings"] = sec.get("filings", [])
        raw["company_name"] = sec.get("company_name", symbol)
        sources.append("SEC EDGAR")
    else:
        raw["sec_filings"] = []

    data_summary = " ".join(summary_parts)[:2000] if summary_parts else "No summary available."
    return raw, sources, data_summary


def data_node(state: ResearchState) -> ResearchState:
    """Fetch all external data via APIs and optional LLM summary."""
    symbol = (state.get("symbol") or "").upper()
    if not symbol:
        return {"error": "Missing symbol"}
    raw_data, data_sources, data_summary = _gather_raw_data(symbol)
    company_name = raw_data.get("company_name") or raw_data.get("overview", {}).get("Name") or symbol
    # Optional: run LLM data agent for a richer narrative summary
    try:
        result = run_data_agent(symbol)
        if result.get("summary"):
            data_summary = result["summary"][:3000]
    except Exception:
        pass
    return {
        "company_name": company_name,
        "data_sources": data_sources,
        "raw_data": raw_data,
        "data_summary": data_summary,
        "error": "",
    }


def analysis_node(state: ResearchState) -> ResearchState:
    """Compute quantitative metrics from raw data."""
    raw_data = state.get("raw_data") or {}
    symbol = state.get("symbol") or ""
    metrics = run_analysis_agent(raw_data, symbol)
    return {"quantitative_metrics": metrics}


def sentiment_node(state: ResearchState) -> ResearchState:
    """Analyze news and context sentiment with LLM."""
    raw_data = state.get("raw_data") or {}
    news_list = raw_data.get("news", [])
    headlines = [n.get("title", "") for n in news_list if isinstance(n, dict) and n.get("title")]
    data_summary = state.get("data_summary") or ""
    symbol = state.get("symbol") or ""
    sentiment = run_sentiment_agent(headlines, data_summary, symbol)
    return {"sentiment_summary": sentiment}


def risk_node(state: ResearchState) -> ResearchState:
    """Identify regulatory and macro risks."""
    raw_data = state.get("raw_data") or {}
    symbol = state.get("symbol") or ""
    sector = (raw_data.get("overview") or {}).get("Sector", "") or (raw_data.get("quote") or {}).get("sector", "")
    sec_filings = raw_data.get("sec_filings", [])
    data_summary = state.get("data_summary") or ""
    risk = run_risk_agent(symbol, sector, sec_filings, data_summary)
    return {"risk_factors": risk}


def synthesis_node(state: ResearchState) -> ResearchState:
    """Produce the final investment brief."""
    symbol = state.get("symbol") or ""
    company_name = state.get("company_name") or symbol
    data_sources = state.get("data_sources") or []
    qm = state.get("quantitative_metrics")
    ss = state.get("sentiment_summary")
    rf = state.get("risk_factors")
    data_summary = state.get("data_summary") or ""
    if not qm or not ss or not rf:
        return {"error": "Missing metrics, sentiment, or risk outputs from pipeline."}
    report = run_synthesis_agent(
        symbol=symbol,
        company_name=company_name,
        data_sources=data_sources,
        quantitative_metrics=qm,
        sentiment_summary=ss,
        risk_factors=rf,
        data_summary=data_summary,
    )
    return {"report": report}


def human_approval_node(state: ResearchState) -> ResearchState:
    """Human-in-the-loop: interrupt for approval; on resume, apply decision."""
    report = state.get("report")
    if not report:
        return {"error": "No report to approve."}
    # interrupt() pauses the graph; resume with Command(resume=<decision>) — decision is returned here
    decision = interrupt({
        "message": "Review the investment brief below and approve or reject for publication.",
        "report": report.model_dump() if hasattr(report, "model_dump") else report,
    })
    if decision and decision.get("approved") is True:
        report.approval_status = ApprovalStatus.APPROVED
        report.approved_by = decision.get("reviewer", "human")
        from datetime import datetime
        report.approved_at = datetime.utcnow()
    else:
        report.approval_status = ApprovalStatus.REJECTED
        report.approved_by = decision.get("reviewer", "human") if decision else None
    return {"report": report, "approval_status": report.approval_status}


def should_require_approval(state: ResearchState) -> Literal["approve", "end"]:
    """Route to human approval or end (e.g. if approval disabled)."""
    from app.config import REQUIRE_HUMAN_APPROVAL
    if REQUIRE_HUMAN_APPROVAL:
        return "approve"
    return "end"


def build_graph(checkpointer=None):
    """Build and return the compiled LangGraph."""
    builder = StateGraph(ResearchState)
    builder.add_node("data", data_node)
    builder.add_node("analysis", analysis_node)
    builder.add_node("sentiment", sentiment_node)
    builder.add_node("risk", risk_node)
    builder.add_node("synthesis", synthesis_node)
    builder.add_node("human_approval", human_approval_node)

    builder.set_entry_point("data")
    builder.add_edge("data", "analysis")
    builder.add_edge("analysis", "sentiment")
    builder.add_edge("sentiment", "risk")
    builder.add_edge("risk", "synthesis")
    builder.add_conditional_edges("synthesis", should_require_approval, {"approve": "human_approval", "end": END})
    builder.add_edge("human_approval", END)

    return builder.compile(checkpointer=checkpointer or MemorySaver())
