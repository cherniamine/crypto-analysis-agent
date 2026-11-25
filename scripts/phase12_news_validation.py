"""Focused live NewsAPI -> evidence -> Ollama citation validation.

Run from native PowerShell where the configured providers are reachable. The
report contains counts, statuses, stage names, and timing only.
"""
import argparse
import asyncio
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
RESULT = ROOT / "backend" / "evaluation" / "results" / "phase12_news_live.json"


def elapsed(start):
    return round((time.perf_counter() - start) * 1000, 2)


async def main(query):
    from app.core.config import get_settings
    from app.agents.graph import run_agent
    from app.agents.intelligence import validate_citations
    from app.tools.crypto_news import crypto_news

    settings = get_settings()
    report = {"phase": "12", "classification": "LIVE", "timestamp": datetime.now(timezone.utc).isoformat(), "provider": "NewsAPI", "llm_provider": settings.llm_provider, "query": query, "pipeline": {}}

    started = time.perf_counter()
    provider = await crypto_news(query)
    report["pipeline"]["provider_retrieval"] = {
        "status": "passed" if provider.get("status") == "ok" and provider.get("normalized_articles", 0) > 0 else "failed",
        "duration_ms": elapsed(started),
        "provider_status": provider.get("status"),
        "api_articles_received": provider.get("api_articles_received", 0),
        "normalized_articles": provider.get("normalized_articles", len(provider.get("articles", []))),
        "unique_urls": len({a.get("url") for a in provider.get("articles", []) if a.get("url")}),
        "retrieved_at_present": bool(provider.get("retrieved_at")),
    }

    started = time.perf_counter()
    try:
        state = await run_agent(query)
        evidence = state.get("evidence", [])
        news_evidence = [item for item in evidence if item.get("type") == "news"]
        answer = state.get("answer", "")
        citation = validate_citations(answer, evidence, any(item.get("type") == "news" for item in evidence))
        validation = next((x for x in state.get("activity", []) if x.get("stage") == "result_validation"), {})
        selection = next((x for x in state.get("activity", []) if x.get("stage") == "evidence_processing"), {})
        synthesis = next((x for x in state.get("activity", []) if x.get("stage") == "llm_synthesis"), {})
        news_tool = next((x for x in state.get("activity", []) if x.get("stage") == "news_tool"), {})
        report["pipeline"]["graph_synthesis"] = {
            "status": "passed" if news_tool.get("status") == "ok" and len(news_evidence) > 0 and synthesis.get("status") == "complete" and citation.get("valid") else "failed",
            "duration_ms": elapsed(started),
            "tool_status": news_tool.get("status"),
            "tools_selected": state.get("tools_needed", []),
            "stages": [x.get("stage") for x in state.get("activity", [])],
            "api_articles_received": validation.get("api_articles_received", 0),
            "normalized_articles": validation.get("normalized_articles", 0),
            "news_evidence_created": selection.get("news_evidence_created", 0),
            "available_news": selection.get("available_news", 0),
            "selected_news": selection.get("selected_news", 0),
            "dropped_news": selection.get("dropped_news", 0),
            "news_evidence_in_llm_context": len(news_evidence),
            "news_evidence_with_urls": sum(bool(item.get("url")) for item in news_evidence),
            "citation_validation": citation,
            "llm_synthesis_status": synthesis.get("status"),
            "prompt_chars_estimate": int(re.search(r"prompt (\d+) chars", synthesis.get("label", "")).group(1)) if re.search(r"prompt (\d+) chars", synthesis.get("label", "")) else None,
        }
    except Exception as exc:
        report["pipeline"]["graph_synthesis"] = {"status": "failed", "duration_ms": elapsed(started), "error_type": type(exc).__name__}

    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="Latest Bitcoin news")
    args = parser.parse_args()
    asyncio.run(main(args.query))
