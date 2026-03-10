"""Synthesis Agent: orchestrates inputs and produces the final structured investment brief."""
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.report_schema import (
    InvestmentBrief,
    QuantitativeMetrics,
    SentimentSummary,
    RiskFactors,
    ApprovalStatus,
)
from app.config import OPENAI_MODEL


def run_synthesis_agent(
    symbol: str,
    company_name: str,
    data_sources: list[str],
    quantitative_metrics: QuantitativeMetrics,
    sentiment_summary: SentimentSummary,
    risk_factors: RiskFactors,
    data_summary: str,
    model: ChatOpenAI | None = None,
) -> InvestmentBrief:
    """Produce the final InvestmentBrief from all agent outputs."""
    llm = model or ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    prompt = (
        f"Write a 2-3 sentence executive summary and recommendation for {company_name} ({symbol}) "
        "for an investment brief. Base it on: "
        f"Metrics: P/E={quantitative_metrics.pe_ratio}, Revenue growth YoY={quantitative_metrics.revenue_growth_yoy}, "
        f"Debt/Equity={quantitative_metrics.debt_to_equity}. "
        f"Sentiment: {sentiment_summary.news_sentiment}; tone: {sentiment_summary.earnings_tone}. "
        f"Risks: regulatory={risk_factors.regulatory_risks}, macro={risk_factors.macro_risks}, sector={risk_factors.sector_risks}. "
        "Be concise and professional. State a clear view: Buy/Hold/Reduce and why."
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    exec_summary = (response.content or "").strip()[:1500]
    return InvestmentBrief(
        company_symbol=symbol,
        company_name=company_name or symbol,
        generated_at=datetime.utcnow(),
        executive_summary=exec_summary,
        quantitative_metrics=quantitative_metrics,
        sentiment_summary=sentiment_summary,
        risk_factors=risk_factors,
        data_sources=data_sources,
        approval_status=ApprovalStatus.PENDING,
    )
