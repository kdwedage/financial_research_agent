"""Evaluation framework: score report quality against analyst consensus (or reference metrics)."""
from typing import Any

from app.report_schema import InvestmentBrief, QuantitativeMetrics


def get_analyst_consensus_reference(symbol: str) -> dict[str, Any] | None:
    """Fetch analyst consensus / reference metrics if available (e.g. Alpha Vantage EARNINGS).
    Returns dict with keys like 'consensus_recommendation', 'target_price', 'pe_consensus', etc.
    """
    try:
        from app.tools.alpha_vantage import get_company_overview
        ov = get_company_overview(symbol)
        if "error" in ov:
            return None
        return {
            "pe_consensus": ov.get("PERatio"),
            "analyst_target": ov.get("AnalystTargetPrice"),
            "analyst_rating": ov.get("AnalystRating"),
        }
    except Exception:
        return None


def score_report_quality(
    report: InvestmentBrief,
    consensus: dict[str, Any] | None = None,
) -> dict[str, float | str]:
    """
    Score the generated report against analyst consensus (or heuristics).
    Returns a dict with overall_score (0-100) and component scores/notes.
    """
    scores: dict[str, float | str] = {}
    component_scores: list[float] = []

    # 1) Completeness: has executive summary, metrics, sentiment, risks
    completeness = 0.0
    if report.executive_summary and len(report.executive_summary) > 50:
        completeness += 0.3
    if report.quantitative_metrics and (
        report.quantitative_metrics.pe_ratio is not None
        or report.quantitative_metrics.revenue_growth_yoy is not None
    ):
        completeness += 0.25
    if report.sentiment_summary and report.sentiment_summary.news_sentiment:
        completeness += 0.25
    if report.risk_factors and (
        report.risk_factors.regulatory_risks or report.risk_factors.macro_risks or report.risk_factors.sector_risks
    ):
        completeness += 0.2
    scores["completeness"] = round(completeness * 100, 1)
    component_scores.append(completeness * 100)

    # 2) Alignment with consensus (if available)
    if consensus:
        align = 0.0
        qm = report.quantitative_metrics
        if qm and qm.pe_ratio is not None and consensus.get("pe_consensus") is not None:
            ref_pe = float(consensus["pe_consensus"])
            if ref_pe and abs(qm.pe_ratio - ref_pe) / ref_pe < 0.2:
                align += 50  # within 20% of consensus P/E
        if report.executive_summary and consensus.get("analyst_rating"):
            # Simple check: recommendation present
            align += 25
        align = min(100, align)
        scores["consensus_alignment"] = round(align, 1)
        scores["consensus_note"] = str(consensus)
        component_scores.append(align)
    else:
        scores["consensus_alignment"] = "N/A (no consensus data)"
        scores["consensus_note"] = "Alpha Vantage overview or analyst data not available"

    # 3) Structure: data_sources present
    structure = 100.0 if (report.data_sources and len(report.data_sources) > 0) else 50.0
    scores["structure"] = round(structure, 1)
    component_scores.append(structure)

    # Overall: average of numeric components
    numeric_scores = [s for s in component_scores if isinstance(s, (int, float))]
    overall = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 0.0
    scores["overall_score"] = round(overall, 1)
    scores["grade"] = "A" if overall >= 80 else "B" if overall >= 60 else "C" if overall >= 40 else "D"
    return scores
