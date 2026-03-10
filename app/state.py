"""Shared state for the research pipeline graph."""
from typing import Any, TypedDict

from app.report_schema import (
    InvestmentBrief,
    QuantitativeMetrics,
    SentimentSummary,
    RiskFactors,
    ApprovalStatus,
)


class ResearchState(TypedDict, total=False):
    """State passed through the pipeline; all keys optional for partial updates."""
    symbol: str
    company_name: str
    data_sources: list[str]
    raw_data: dict[str, Any]
    data_summary: str
    quantitative_metrics: QuantitativeMetrics
    sentiment_summary: SentimentSummary
    risk_factors: RiskFactors
    report: InvestmentBrief
    approval_status: ApprovalStatus
    human_feedback: str
    error: str
