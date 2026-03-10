"""Data Agent: pulls earnings transcripts context, SEC/SEDAR filings, and news via APIs using tool calling."""
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.tools.alpha_vantage import get_company_overview, get_earnings_annual, get_income_statement, get_balance_sheet
from app.tools.yahoo_finance import get_quote, get_financials_df, get_news
from app.tools.sec_edgar import get_recent_filings
from app.config import OPENAI_MODEL


@tool
def fetch_company_overview(symbol: str) -> dict:
    """Fetch company overview (description, sector, P/E, market cap) from Alpha Vantage. Symbol is stock ticker e.g. AAPL."""
    return get_company_overview(symbol)


@tool
def fetch_earnings_annual(symbol: str) -> dict:
    """Fetch annual earnings (EPS) from Alpha Vantage for earnings context."""
    return get_earnings_annual(symbol)


@tool
def fetch_income_statement(symbol: str, limit: int = 5) -> dict:
    """Fetch annual income statements (revenue, net income) from Alpha Vantage."""
    return get_income_statement(symbol, limit=limit)


@tool
def fetch_balance_sheet(symbol: str, limit: int = 5) -> dict:
    """Fetch balance sheet (assets, liabilities, equity) from Alpha Vantage."""
    return get_balance_sheet(symbol, limit=limit)


@tool
def fetch_quote(symbol: str) -> dict:
    """Fetch current quote (price, P/E, volume, market cap) from Yahoo Finance."""
    return get_quote(symbol)


@tool
def fetch_financials_yahoo(symbol: str) -> dict:
    """Fetch income statement and balance sheet from Yahoo Finance for ratio analysis."""
    return get_financials_df(symbol)


@tool
def fetch_news(symbol: str, count: int = 10) -> dict:
    """Fetch recent news headlines and links for the ticker from Yahoo Finance."""
    return get_news(symbol, count=count)


@tool
def fetch_sec_filings(symbol: str, limit: int = 5) -> dict:
    """Fetch recent SEC filings (10-K, 10-Q, 8-K) for the company."""
    return get_recent_filings(symbol, limit=limit)


DATA_TOOLS = [
    fetch_company_overview,
    fetch_earnings_annual,
    fetch_income_statement,
    fetch_balance_sheet,
    fetch_quote,
    fetch_financials_yahoo,
    fetch_news,
    fetch_sec_filings,
]


def run_data_agent(symbol: str, model: ChatOpenAI | None = None) -> dict:
    """Run the Data Agent: use LLM with tool calling to gather all relevant data for the symbol."""
    llm = (model or ChatOpenAI(model=OPENAI_MODEL, temperature=0)).bind_tools(DATA_TOOLS)
    prompt = (
        f"Research the publicly traded company with ticker symbol {symbol.upper()}. "
        "Use your tools to fetch: (1) company overview and valuation metrics, "
        "(2) earnings data, (3) income statement and balance sheet from Alpha Vantage and/or Yahoo Finance, "
        "(4) recent news headlines, (5) recent SEC filings (10-K, 10-Q). "
        "Call each relevant tool and summarize the raw results into a single structured summary. "
        "Include company name, sector, key metrics (P/E, revenue, debt if available), recent news titles, and listing of SEC filings."
    )
    messages = [HumanMessage(content=prompt)]
    max_rounds = 15
    for _ in range(max_rounds):
        response = llm.invoke(messages)
        if not response.tool_calls:
            return {"summary": response.content, "raw_calls": []}
        for tc in response.tool_calls:
            name = tc["name"]
            args = tc.get("args", {})
            tool_map = {t.name: t for t in DATA_TOOLS}
            if name in tool_map:
                out = tool_map[name].invoke(args)
                messages.append(
                    ToolMessage(content=str(out)[:8000], tool_call_id=tc["id"])
                )
        messages.append(
            AIMessage(content=response.content or "", tool_calls=response.tool_calls)
        )
    return {"summary": "Max tool rounds reached.", "raw_calls": []}
