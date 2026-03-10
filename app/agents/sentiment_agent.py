"""Sentiment Agent: analyzes recent news and earnings call tone using an LLM."""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.report_schema import SentimentSummary
from app.config import OPENAI_MODEL


def run_sentiment_agent(
    news_headlines: list[str],
    data_summary: str,
    symbol: str,
    model: ChatOpenAI | None = None,
) -> SentimentSummary:
    """Analyze sentiment from news headlines and data summary; return SentimentSummary."""
    llm = model or ChatOpenAI(model=OPENAI_MODEL, temperature=0)
    headlines_text = "\n".join(news_headlines[:20]) if news_headlines else "No recent headlines found."
    prompt = (
        f"You are a financial analyst. For the company {symbol}, analyze sentiment.\n\n"
        "Recent news headlines:\n" + headlines_text + "\n\n"
        "Additional context (company/data summary):\n" + (data_summary or "None") + "\n\n"
        "Respond with exactly three short paragraphs (2-3 sentences each), in order:\n"
        "1) NEWS SENTIMENT: Overall news sentiment - state 'bullish', 'neutral', or 'bearish' and why.\n"
        "2) EARNINGS TONE: If earnings or fundamentals are mentioned, summarize the tone (confident/cautious/etc.); otherwise say 'No earnings tone evident from headlines.'\n"
        "3) KEY QUOTES OR THEMES: List 1-3 notable themes or quote-worthy points from the headlines, or 'None'.\n"
        "Then on a new line write JSON only (no markdown): {\"news_sentiment\": \"...\", \"earnings_tone\": \"...\", \"key_quotes\": [\"...\", \"...\"]}"
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    text = (response.content or "").strip()
    # Parse JSON from end of response
    try:
        if "{" in text:
            json_str = text[text.rindex("{"):].strip()
            if json_str.endswith("}"):
                import json
                d = json.loads(json_str)
                kq = d.get("key_quotes")
                if not isinstance(kq, list):
                    kq = [kq] if kq else []
                return SentimentSummary(
                    news_sentiment=(d.get("news_sentiment") or "neutral")[:200],
                    earnings_tone=(d.get("earnings_tone") or "N/A")[:300],
                    key_quotes=kq[:5],
                )
    except Exception:
        pass
    return SentimentSummary(
        news_sentiment="neutral",
        earnings_tone=text[:300] if text else "N/A",
        key_quotes=[],
    )
