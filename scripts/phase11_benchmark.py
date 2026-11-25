"""Comparative local Ollama benchmark for the existing Crypto Analysis Agent.

Run this from the repository root in the same native PowerShell context that
can reach Ollama. It never stores prompts, answers, credentials, or raw API
payloads; only sanitized timings and validation counters are written.
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
RESULT = BACKEND / "evaluation" / "results" / "phase11_benchmark.json"
sys.path.insert(0, str(BACKEND))

MODELS = ["qwen3:8b", "qwen3:4b", "phi3:mini"]
SCENARIOS = {
    "btc_market": "Analyze Bitcoin using current live market data.",
    "eth_market": "Analyze Ethereum using current live market data.",
    "btc_news": "Analyze Bitcoin news using current retrieved articles.",
    "eth_news": "Analyze Ethereum news using current retrieved articles.",
    "comparison": "Compare Bitcoin and Ethereum using current market data.",
}


def now_ms(start):
    return round((time.perf_counter() - start) * 1000, 2)


def valid_citations(answer, evidence):
    ids = {item.get("id") for item in evidence}
    cited = {item.strip("[]") for item in re.findall(r"\[(?:market|news):[^\]]+\]", answer or "")}
    return len(cited), cited.issubset(ids)


def error_category(exc):
    name = type(exc).__name__.lower()
    return "timeout" if "timeout" in name else "connection" if "connect" in name or "network" in name else "model_or_schema_error"


async def inventory(base_url):
    async with httpx.AsyncClient(timeout=15) as client:
        version = (await client.get(f"{base_url.rstrip('/')}/api/version")).json().get("version")
        tags = await client.get(f"{base_url.rstrip('/')}/api/tags")
        tags.raise_for_status()
        models = tags.json().get("models", [])
        try:
            ps = (await client.get(f"{base_url.rstrip('/')}/api/ps")).json()
        except Exception:
            ps = {}
    return version, models, ps


async def warm_model(base_url, model):
    """Load one model before timing structured requests; report load separately."""
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/api/generate",
                json={"model": model, "prompt": "Reply with OK.", "stream": False, "keep_alive": "5m", "options": {"num_predict": 1}},
            )
            response.raise_for_status()
        return {"classification": "LIVE", "status": "passed", "duration_ms": now_ms(started), "model": model}
    except Exception as exc:
        return {"classification": "LIVE", "status": "failed", "duration_ms": now_ms(started), "model": model, "error_type": type(exc).__name__, "error_category": error_category(exc)}


async def direct_run(model, repetition):
    from app.core.config import get_settings
    from app.llm.factory import create_llm
    from app.schemas.analysis import AnalysisResponse

    get_settings.cache_clear()
    settings = get_settings()
    llm = create_llm(settings).with_structured_output(AnalysisResponse)
    prompt = (
        "Return a structured educational crypto analysis using only this verified "
        "evidence: [market:BTC] BTC price observation retrieved from FreeCryptoAPI."
    )
    started = time.perf_counter()
    try:
        result = await llm.ainvoke([
            ("system", "Use only supplied evidence. Return the requested structured schema."),
            ("human", prompt),
        ])
        parsed = result if isinstance(result, AnalysisResponse) else AnalysisResponse.model_validate(result)
        return {
            "model": model,
            "repetition": repetition,
            "classification": "LIVE",
            "status": "passed",
            "duration_ms": now_ms(started),
            "structured_output": True,
            "pydantic_valid": True,
            "prompt_chars": len(prompt),
            "answer_sections_nonempty": sum(bool(x) for x in [parsed.executive_summary, parsed.market_data, parsed.ai_analysis]),
        }
    except Exception as exc:
        return {"model": model, "repetition": repetition, "classification": "LIVE", "status": "failed", "duration_ms": now_ms(started), "error_type": type(exc).__name__, "error_category": error_category(exc)}


async def graph_run(model, scenario, question, repetition, history=None):
    from app.agents.graph import run_agent

    started = time.perf_counter()
    history = history or []
    try:
        state = await run_agent(question, history)
        evidence = state.get("evidence", [])
        answer = state.get("answer", "")
        cited_count, citations_valid = valid_citations(answer, evidence)
        synthesis = next((x for x in state.get("activity", []) if x.get("stage") == "llm_synthesis"), {})
        selection = next((x for x in state.get("activity", []) if x.get("stage") == "evidence_processing"), {})
        sections = {name: f"### {name}" in answer for name in ("Market Data", "News & Context", "AI Analysis", "Sources")}
        source_urls_in_answer = sum(bool(item.get("url")) and item["url"] in answer for item in evidence)
        quality = {
            "structured_response_validated": any(x.get("stage") == "response_validation" for x in state.get("activity", [])),
            "evidence_grounded": citations_valid,
            "source_attribution": cited_count > 0 and (scenario not in {"btc_news", "eth_news"} or source_urls_in_answer > 0),
            "response_sections_present": sections,
        }
        return {
            "model": model,
            "scenario": scenario,
            "repetition": repetition,
            "status": "passed" if answer and any(x.get("stage") == "response_validation" for x in state.get("activity", [])) else "failed",
            "duration_ms": now_ms(started),
            "tools": state.get("tools_needed", []),
            "evidence_count": len(evidence),
            "cited_count": cited_count,
            "citations_valid": citations_valid,
            "source_urls": sum(bool(x.get("url")) for x in evidence),
            "source_urls_in_answer": source_urls_in_answer,
            "classification": "LIVE",
            "stages": [x.get("stage") for x in state.get("activity", [])],
            "synthesis_status": synthesis.get("status"),
            "evidence_selection": {k: selection.get(k) for k in ("available_news", "selected_news", "dropped_news") if k in selection},
            "prompt_chars_estimate": int(re.search(r"prompt (\d+) chars", synthesis.get("label", "")).group(1)) if re.search(r"prompt (\d+) chars", synthesis.get("label", "")) else None,
            "quality": quality,
            "_answer": answer,
        }
    except Exception as exc:
        return {"model": model, "scenario": scenario, "repetition": repetition, "classification": "LIVE", "status": "failed", "duration_ms": now_ms(started), "error_type": type(exc).__name__, "error_category": error_category(exc)}


async def main(args):
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    report = {"phase": "11", "classification": "LIVE", "timestamp": datetime.now(timezone.utc).isoformat(), "configuration": {"news_evidence_limit": os.getenv("NEWS_EVIDENCE_LIMIT", "5"), "evidence_context_char_budget": os.getenv("EVIDENCE_CONTEXT_CHAR_BUDGET", "18000"), "llm_timeout_seconds": os.getenv("LLM_TIMEOUT_SECONDS", "60"), "direct_repetitions": args.direct_repetitions, "graph_repetitions": args.graph_repetitions}, "inventory": {}, "model_warmup": [], "direct_inference": [], "graph_scenarios": []}
    try:
        version, models, ps = await inventory(base_url)
        installed = {m.get("name") for m in models}
        report["inventory"] = {"ollama_version": version, "installed_models": sorted(installed), "model_metadata": [{k: v for k, v in item.items() if k in {"name", "size", "digest", "modified_at"}} for item in models], "running": [{k: v for k, v in item.items() if k in {"name", "size", "size_vram", "context_length", "processor"}} for item in ps.get("models", [])]}
    except Exception as exc:
        report["classification"] = "NOT RUN"
        report["inventory"] = {"status": "unavailable", "error_type": type(exc).__name__}
        RESULT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return

    installed = set(report["inventory"].get("installed_models", []))
    for model in args.models:
        if model not in installed:
            report.setdefault("not_run_models", []).append({"model": model, "classification": "NOT RUN", "reason": "not_installed"})
            continue
        os.environ["LLM_PROVIDER"] = "ollama"
        os.environ["OLLAMA_MODEL"] = model
        report["model_warmup"].append(await warm_model(base_url, model))
        for repetition in range(1, args.direct_repetitions + 1):
            report["direct_inference"].append(await direct_run(model, repetition))
        questions = dict(SCENARIOS)
        questions["follow_up"] = "What about Ethereum?"
        for scenario, question in questions.items():
            for repetition in range(1, args.graph_repetitions + 1):
                history = None
                if scenario == "follow_up":
                    prior = await graph_run(model, "btc_market_context", SCENARIOS["btc_market"], repetition)
                    prior_answer = prior.pop("_answer", "")
                    history = [{"role": "user", "content": SCENARIOS["btc_market"]}, {"role": "assistant", "content": prior_answer}] if prior_answer else None
                    prior["context_source"] = "actual_prior_graph_execution"
                    report["graph_scenarios"].append(prior)
                result = await graph_run(model, scenario, question, repetition, history)
                result.pop("_answer", None)
                if scenario == "follow_up": result["follow_up_context_present"] = bool(history)
                report["graph_scenarios"].append(result)
    grouped = {}
    for row in report["direct_inference"] + report["graph_scenarios"]:
        if row.get("status") == "passed":
            key = (row["model"], "direct" if "prompt_chars" in row else "graph")
            grouped.setdefault(key, []).append(row["duration_ms"])
    report["aggregates"] = [{"model": model, "kind": kind, "successful_runs": len(values), "mean_ms": round(mean(values), 2), "median_ms": round(median(values), 2)} for (model, kind), values in grouped.items()]
    RESULT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", choices=MODELS, default=MODELS)
    parser.add_argument("--direct-repetitions", type=int, default=3)
    parser.add_argument("--graph-repetitions", type=int, default=1)
    asyncio.run(main(parser.parse_args()))
