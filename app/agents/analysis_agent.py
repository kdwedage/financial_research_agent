"""Analysis Agent: runs quantitative analysis on financial metrics (P/E, revenue growth, debt ratios)."""
from typing import Any

from app.report_schema import QuantitativeMetrics


def _float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def compute_metrics_from_overview(overview: dict[str, Any]) -> dict[str, float | None]:
    """Extract metrics from Alpha Vantage OVERVIEW response."""
    return {
        "pe_ratio": _float(overview.get("PERatio")),
        "profit_margin": _float(overview.get("ProfitMargin")),
        "revenue_ttm": _float(overview.get("RevenueTTM")),
        "market_cap": _float(overview.get("MarketCapitalization")),
    }


def compute_metrics_from_income(income_reports: list[dict]) -> dict[str, float | None]:
    """Compute revenue growth YoY from annual income statements."""
    if not income_reports or len(income_reports) < 2:
        return {}
    rev_cur = _float(income_reports[0].get("totalRevenue"))
    rev_prev = _float(income_reports[1].get("totalRevenue"))
    if rev_cur and rev_prev and rev_prev != 0:
        growth = (rev_cur - rev_prev) / rev_prev * 100
        return {"revenue_growth_yoy": growth}
    return {}


def compute_metrics_from_balance(bal_reports: list[dict]) -> dict[str, float | None]:
    """Compute debt-to-equity and current ratio from balance sheet."""
    if not bal_reports:
        return {}
    r = bal_reports[0]
    total_debt = _float(r.get("totalLiabilities")) or 0
    total_equity = _float(r.get("totalShareholderEquity"))
    current_assets = _float(r.get("totalCurrentAssets"))
    current_liab = _float(r.get("totalCurrentLiabilities"))
    out = {}
    if total_equity and total_equity != 0:
        out["debt_to_equity"] = total_debt / total_equity
    if current_assets and current_liab and current_liab != 0:
        out["current_ratio"] = current_assets / current_liab
    return out


def run_analysis_agent(collected_data: dict[str, Any], symbol: str) -> QuantitativeMetrics:
    """Run quantitative analysis on whatever raw data was collected; produce QuantitativeMetrics."""
    metrics = {}
    # From overview (Alpha Vantage or Yahoo quote)
    if "overview" in collected_data:
        metrics.update(compute_metrics_from_overview(collected_data["overview"]))
    if "quote" in collected_data:
        q = collected_data["quote"]
        if _float(q.get("peRatio")) is not None:
            metrics.setdefault("pe_ratio", _float(q.get("peRatio")))
    # From income
    if "income_reports" in collected_data:
        metrics.update(compute_metrics_from_income(collected_data["income_reports"]))
    if "income_stmt" in collected_data:
        # Yahoo format: dict of period -> series
        inc = collected_data["income_stmt"]
        if isinstance(inc, dict):
            keys = sorted(inc.keys(), reverse=True)[:2]
            if len(keys) >= 2:
                rev_cur = _float(inc[keys[0]].get("Total Revenue") or inc[keys[0]].get("Revenue"))
                rev_prev = _float(inc[keys[1]].get("Total Revenue") or inc[keys[1]].get("Revenue"))
                if rev_cur and rev_prev and rev_prev != 0:
                    metrics["revenue_growth_yoy"] = (rev_cur - rev_prev) / rev_prev * 100
    # From balance sheet
    if "balance_reports" in collected_data:
        metrics.update(compute_metrics_from_balance(collected_data["balance_reports"]))
    if "balance_sheet" in collected_data:
        bal = collected_data["balance_sheet"]
        if isinstance(bal, dict):
            keys = sorted(bal.keys(), reverse=True)[:1]
            if keys:
                r = bal[keys[0]] if isinstance(bal[keys[0]], dict) else {}
                if isinstance(bal[keys[0]], dict):
                    r = bal[keys[0]]
                    ca = _float(r.get("Current Assets") or r.get("Total Current Assets"))
                    cl = _float(r.get("Current Liabilities") or r.get("Total Current Liabilities"))
                    te = _float(r.get("Stockholders Equity") or r.get("Total Stockholder Equity"))
                    tl = _float(r.get("Total Liabilities Net Minority Interest") or r.get("Total Liabilities"))
                    if te and te != 0 and tl is not None:
                        metrics["debt_to_equity"] = tl / te
                    if ca and cl and cl != 0:
                        metrics["current_ratio"] = ca / cl
    return QuantitativeMetrics(
        pe_ratio=metrics.get("pe_ratio"),
        revenue_growth_yoy=metrics.get("revenue_growth_yoy"),
        debt_to_equity=metrics.get("debt_to_equity"),
        current_ratio=metrics.get("current_ratio"),
        profit_margin=metrics.get("profit_margin"),
        free_cash_flow=metrics.get("free_cash_flow"),
    )
