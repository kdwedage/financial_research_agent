# Autonomous Financial Research Agent

A **multi-agent system** that autonomously researches a publicly traded company and produces a structured **investment brief**. Built for the agentic AI trend with a financial domain focus (e.g. bank / buy-side use cases).

## Architecture

Pipeline of specialized agents that collaborate:

| Agent | Role |
|-------|------|
| **Data Agent** | Pulls earnings context, SEC/SEDAR filings, and news via **Alpha Vantage**, **Yahoo Finance**, and **SEC EDGAR** using **tool use / function calling**. |
| **Analysis Agent** | Runs quantitative analysis (P/E, revenue growth, debt ratios, current ratio). |
| **Sentiment Agent** | Analyzes recent news and earnings-call tone using an LLM. |
| **Risk Agent** | Flags regulatory and macroeconomic risk factors. |
| **Synthesis Agent** | Orchestrates the others and produces the final structured report. |

- **Orchestration**: **LangGraph** (stateful graph: data → analysis → sentiment → risk → synthesis → human approval).
- **LLM**: **OpenAI** (configurable; can swap to Cohere via env).
- **Memory**: **Chroma** vector store for persisting runs and semantic search across past research.
- **Human-in-the-loop**: Optional approval step before the report is considered “published” (important for responsible AI in banks).

## Key technical details

- **Tool use and function calling** so agents actually query APIs (Alpha Vantage, Yahoo Finance, SEC EDGAR), not just generate text.
- **Human-in-the-loop** approval before the final report is published (`REQUIRE_HUMAN_APPROVAL=true` by default).
- **Evaluation framework** that scores report quality (completeness, structure, alignment with analyst consensus when available).
- **Streamlit frontend** for demos and interviewer runs.

## Setup

1. **Clone / enter project**
   ```bash
   cd financial_research_agent
   ```

2. **Create virtualenv and install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Environment variables**
   - Copy `.env.example` to `.env`.
   - **Required**: `OPENAI_API_KEY` (for LLM and embeddings).
   - **Optional but recommended**: `ALPHA_VANTAGE_API_KEY` (free tier: 500 req/day) for overview, earnings, income statement, balance sheet.
   - **Optional**: `REQUIRE_HUMAN_APPROVAL=false` to skip the approval step (e.g. for automated demos).

   ```bash
   cp .env.example .env
   # Edit .env and set OPENAI_API_KEY and optionally ALPHA_VANTAGE_API_KEY
   ```

## Running the app

**Streamlit (recommended for demos)**

```bash
streamlit run frontend/streamlit_app.py
```

Or from project root:

```bash
cd financial_research_agent && streamlit run frontend/streamlit_app.py
```

**Programmatic usage**

```python
from app.graph import build_graph
from langgraph.checkpoint.memory import MemorySaver

graph = build_graph(checkpointer=MemorySaver())
config = {"configurable": {"thread_id": "demo-1"}}
state = graph.invoke({"symbol": "AAPL"}, config=config)
# If human approval is required, graph pauses; resume with:
# from langgraph.types import Command
# state = graph.invoke(Command(resume={"approved": True, "reviewer": "you"}), config=config)
report = state.get("report")
```

## Evaluation

The app scores each report on:

- **Completeness** (executive summary, metrics, sentiment, risks).
- **Structure** (data sources listed).
- **Consensus alignment** (when Alpha Vantage analyst/overview data is available).

Scores and a simple grade (A/B/C/D) are shown in the Streamlit UI and via `app.evaluation.score_report_quality(report, consensus)`.

## Project layout

```
financial_research_agent/
├── app/
│   ├── agents/           # Data, Analysis, Sentiment, Risk, Synthesis agents
│   ├── tools/            # Alpha Vantage, Yahoo Finance, SEC EDGAR API wrappers
│   ├── state.py          # LangGraph state schema
│   ├── graph.py          # LangGraph workflow + human-in-the-loop
│   ├── memory.py         # Chroma vector store for research memory
│   ├── evaluation.py     # Report quality vs analyst consensus
│   ├── report_schema.py  # Structured InvestmentBrief (Pydantic)
│   └── config.py         # Env-based config
├── frontend/
│   └── streamlit_app.py  # Demo UI
├── requirements.txt
├── .env.example
└── README.md
```

## APIs used

- **Alpha Vantage**: company overview, earnings, income statement, balance sheet (requires API key).
- **Yahoo Finance** (yfinance): quote, financials, news (no key).
- **SEC EDGAR**: company ticker → CIK → recent 10-K/10-Q/8-K list (no key; User-Agent set).

## License

Use for portfolio / interview demos. Ensure compliance with each API’s terms and your employer’s policies before production use.
