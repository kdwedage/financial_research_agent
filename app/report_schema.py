"""Structured output schema for the investment brief."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class QuantitativeMetrics(BaseModel):
    """Key financial metrics."""
    pe_ratio: Optional[float] = Field(None, description="Price-to-earnings ratio")
    revenue_growth_yoy: Optional[float] = Field(None, description="Revenue growth year-over-year %")
    debt_to_equity: Optional[float] = Field(None, description="Debt-to-equity ratio")
    current_ratio: Optional[float] = Field(None, description="Current ratio")
    profit_margin: Optional[float] = Field(None, description="Net profit margin %")
    free_cash_flow: Optional[float] = Field(None, description="Free cash flow (latest)")


class SentimentSummary(BaseModel):
    """Sentiment from news and earnings."""
    news_sentiment: str = Field(..., description="Overall news sentiment (bullish/neutral/bearish)")
    earnings_tone: str = Field(..., description="Earnings call tone summary")
    key_quotes: list[str] = Field(default_factory=list, description="Notable quotes or themes")


class RiskFactors(BaseModel):
    """Regulatory and macro risks."""
    regulatory_risks: list[str] = Field(default_factory=list)
    macro_risks: list[str] = Field(default_factory=list)
    sector_risks: list[str] = Field(default_factory=list)


class InvestmentBrief(BaseModel):
    """Final structured investment brief."""
    company_symbol: str
    company_name: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    executive_summary: str = Field(..., description="2-3 sentence summary and recommendation")
    quantitative_metrics: QuantitativeMetrics = Field(default_factory=QuantitativeMetrics)
    sentiment_summary: SentimentSummary = Field(...)
    risk_factors: RiskFactors = Field(default_factory=RiskFactors)
    data_sources: list[str] = Field(default_factory=list, description="APIs/sources used")
    approval_status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
