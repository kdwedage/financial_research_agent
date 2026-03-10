"""Yahoo Finance tools for quote, financials, and news."""
from typing import Any

import yfinance as yf


def get_quote(symbol: str) -> dict[str, Any]:
    """Get current quote (price, P/E, volume, market cap) for a ticker."""
    try:
        t = yf.Ticker(symbol.upper())
        info = t.info
        return {
            "symbol": symbol.upper(),
            "shortName": info.get("shortName"),
            "currentPrice": info.get("currentPrice"),
            "peRatio": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "marketCap": info.get("marketCap"),
            "volume": info.get("volume"),
            "beta": info.get("beta"),
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol.upper()}


def get_financials_df(symbol: str) -> dict[str, Any]:
    """Get financials (income statement, balance sheet) as structured data for ratios."""
    try:
        t = yf.Ticker(symbol.upper())
        inc = t.income_stmt
        bal = t.balance_sheet
        if inc is not None and not inc.empty:
            inc = inc.head(5).to_dict()
        else:
            inc = {}
        if bal is not None and not bal.empty:
            bal = bal.head(5).to_dict()
        else:
            bal = {}
        return {"symbol": symbol.upper(), "income_stmt": inc, "balance_sheet": bal}
    except Exception as e:
        return {"error": str(e), "symbol": symbol.upper()}


def get_news(symbol: str, count: int = 10) -> dict[str, Any]:
    """Get recent news headlines and links for sentiment analysis."""
    try:
        t = yf.Ticker(symbol.upper())
        news = t.news[:count] if t.news else []
        return {
            "symbol": symbol.upper(),
            "news": [
                {"title": n.get("title"), "link": n.get("link"), "publisher": n.get("publisher")}
                for n in news
            ],
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol.upper()}
