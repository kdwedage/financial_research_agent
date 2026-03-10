"""Risk Agent: flags regulatory and macroeconomic risk factors."""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.report_schema import RiskFactors
from app.config import OPENAI_MODEL


def run_risk_agent(
    symbol: str,
    sector: str,
    sec_filings_list: list[dict],
    data_summary: str,
    model: ChatOpenAI | None = None,
) -> RiskFactors:
    """Identify regulatory, macro, and sector risks from context; return RiskFactors."""
    llm = model or ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    filings_text = "\n".join(
        f"- {f.get('form', '')} filed {f.get('filingDate', '')}" for f in sec_filings_list[:10]
    ) if sec_filings_list else "No SEC filings listed."
    prompt = (
        f"You are a risk analyst. For {symbol} (sector: {sector or 'Unknown'}), identify risks.\n\n"
        "Recent SEC filings:\n" + filings_text + "\n\n"
        "Context:\n" + (data_summary or "None") + "\n\n"
        "List risks in three categories. Respond with JSON only (no markdown):\n"
        "{\"regulatory_risks\": [\"...\", \"...\"], \"macro_risks\": [\"...\"], \"sector_risks\": [\"...\"]}\n"
        "Use 0-3 items per category; be concise. If none, use empty list []."
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    text = (response.content or "").strip()
    try:
        if "{" in text:
            json_str = text[text.index("{"): text.rindex("}") + 1]
            import json
            d = json.loads(json_str)
            return RiskFactors(
                regulatory_risks=d.get("regulatory_risks", [])[:5],
                macro_risks=d.get("macro_risks", [])[:5],
                sector_risks=d.get("sector_risks", [])[:5],
            )
    except Exception:
        pass
    return RiskFactors(regulatory_risks=[], macro_risks=[], sector_risks=[])
