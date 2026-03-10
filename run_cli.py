#!/usr/bin/env python3
"""CLI entrypoint: run the research pipeline for a ticker (no Streamlit)."""
import os
import sys
import json
from pathlib import Path

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv()

from app.graph import build_graph
from app.state import ResearchState
from app.evaluation import get_analyst_consensus_reference, score_report_quality
from langgraph.checkpoint.memory import MemorySaver


def main():
    symbol = (sys.argv[1] or os.getenv("SYMBOL", "AAPL")).upper()
    require_approval = os.getenv("REQUIRE_HUMAN_APPROVAL", "true").lower() == "true"

    print(f"Running research pipeline for {symbol} (REQUIRE_HUMAN_APPROVAL={require_approval})...")
    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": f"cli-{symbol}"}}

    state = graph.invoke({"symbol": symbol}, config=config)

    if state.get("error"):
        print("Error:", state["error"], file=sys.stderr)
        sys.exit(1)

    report = state.get("report")
    if not report:
        print("No report produced.", file=sys.stderr)
        sys.exit(1)

    if require_approval and getattr(graph.get_state(config), "next", None):
        print("\n[Pipeline paused for human approval. Resume with Command(resume={...}) in code.]")
        print("Report (pending approval):")
    else:
        print("\n--- Investment Brief ---")
        print(report.model_dump_json(indent=2))

    consensus = get_analyst_consensus_reference(symbol)
    scores = score_report_quality(report, consensus=consensus)
    print("\n--- Evaluation ---")
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
