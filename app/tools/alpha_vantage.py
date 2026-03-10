"""Alpha Vantage API tools for company overview, earnings, and financials."""
import os
from typing import Any, Optional

import requests


def _base_url() -> str:
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    if not key:
        return ""
    return f"https://www.alphavantage.co/query?apikey={key}"


def get_company_overview(symbol: str) -> dict[str, Any]:
    """Get company overview (description, sector, P/E, market cap, etc.) for a ticker.
    Use this for high-level company info and valuation metrics.
    """
    url = _base_url()
    if not url:
        return {"error": "ALPHA_VANTAGE_API_KEY not set", "symbol": symbol}
    params = {"function": "OVERVIEW", "symbol": symbol.upper()}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "Error Message" in data:
        return {"error": data["Error Message"], "symbol": symbol}
    return data


def get_earnings_annual(symbol: str) -> dict[str, Any]:
    """Get annual earnings (EPS, reported EPS) for a ticker. Useful for earnings transcripts context."""
    url = _base_url()
    if not url:
        return {"error": "ALPHA_VANTAGE_API_KEY not set", "symbol": symbol}
    params = {"function": "EARNINGS", "symbol": symbol.upper()}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "Error Message" in data:
        return {"error": data["Error Message"], "symbol": symbol}
    return data


def get_income_statement(symbol: str, limit: int = 5) -> dict[str, Any]:
    """Get annual income statements (revenue, net income, etc.) for quantitative analysis."""
    url = _base_url()
    if not url:
        return {"error": "ALPHA_VANTAGE_API_KEY not set", "symbol": symbol}
    params = {"function": "INCOME_STATEMENT", "symbol": symbol.upper()}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "Error Message" in data:
        return {"error": data["Error Message"], "symbol": symbol}
    reports = data.get("annualReports", [])[:limit]
    return {"symbol": symbol, "annualReports": reports}


def get_balance_sheet(symbol: str, limit: int = 5) -> dict[str, Any]:
    """Get balance sheet (assets, liabilities, equity) for debt and liquidity ratios."""
    url = _base_url()
    if not url:
        return {"error": "ALPHA_VANTAGE_API_KEY not set", "symbol": symbol}
    params = {"function": "BALANCE_SHEET", "symbol": symbol.upper()}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if "Error Message" in data:
        return {"error": data["Error Message"], "symbol": symbol}
    reports = data.get("annualReports", [])[:limit]
    return {"symbol": symbol, "annualReports": reports}
