"""SEC EDGAR tools for recent filings (10-K, 10-Q, 8-K)."""
import json
import urllib.request
from typing import Any


def get_recent_filings(symbol: str, cik: str | None = None, limit: int = 5) -> dict[str, Any]:
    """Get recent SEC filings (10-K, 10-Q, 8-K) for a company by ticker symbol."""
    try:
        ticker = symbol.upper()
        company_name = ticker
        tickers_url = "https://www.sec.gov/files/company_tickers.json"
        req = urllib.request.Request(tickers_url, headers={"User-Agent": "FinancialResearchAgent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            tickers_data = json.loads(r.read().decode())
        cik_str = None
        for v in tickers_data.values():
            if v.get("ticker") == ticker:
                cik_str = str(v.get("cik_str", "")).zfill(10)
                company_name = v.get("title", ticker)
                break
        if not cik_str:
            return {"error": f"No CIK found for ticker {ticker}", "symbol": symbol}
        cik_str = None
        for v in tickers_data.values():
            if v.get("ticker") == ticker:
                cik_str = str(v.get("cik_str", "")).zfill(10)
                company_name = v.get("title", ticker)
                break
        if not cik_str:
            return {"error": f"No CIK found for ticker {ticker}", "symbol": symbol}
        url = f"https://data.sec.gov/submissions/CIK{cik_str}.json"
        req = urllib.request.Request(url, headers={"User-Agent": "FinancialResearchAgent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            sub = json.loads(r.read().decode())
        recent = sub.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filings_list = []
        for i, form in enumerate(forms[: limit * 3]):
            if form in ("10-K", "10-Q", "8-K"):
                filings_list.append({
                    "form": form,
                    "filingDate": recent.get("filingDate", [])[i] if i < len(recent.get("filingDate", [])) else "",
                    "primaryDocument": recent.get("primaryDocument", [])[i] if i < len(recent.get("primaryDocument", [])) else "",
                    "accessionNumber": recent.get("accessionNumber", [])[i] if i < len(recent.get("accessionNumber", [])) else "",
                })
            if len(filings_list) >= limit:
                break
        return {"symbol": symbol, "company_name": company_name, "cik": cik_str, "filings": filings_list}
    except Exception as e:
        return {"error": str(e), "symbol": symbol}
