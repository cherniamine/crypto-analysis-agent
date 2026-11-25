"""Sanitized live market/news and agent validation.

Credentials are loaded by the application's Settings object and are never printed.
The report contains counts, statuses, timings, symbols, and public article metadata only.
"""
import argparse, asyncio, json, re, time
from datetime import datetime, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

def timer(): return time.perf_counter()
def duration(start): return round((time.perf_counter()-start)*1000,2)
def error_category(data):
    text=str(data.get("message","")).lower()
    if any(x in text for x in ["401","403","unauthorized","forbidden","api key","authentication"]): return "authentication"
    if "429" in text or "rate" in text: return "rate_limit"
    if "timeout" in text: return "timeout"
    return "provider_error"

async def provider_checks():
    from app.core.config import get_settings
    from app.tools.crypto_market import market_data
    from app.tools.crypto_news import crypto_news
    settings=get_settings(); report={"timestamp":datetime.now(timezone.utc).isoformat(),"providers":{}}
    if not settings.freecryptoapi_api_key: report["providers"]["market"]={"status":"not_run","reason":"key_not_configured"}
    else:
        started=timer(); data=await market_data(["BTC","ETH"]); assets=data.get("assets",[]); symbols=[]
        for item in assets if isinstance(assets,list) else []:
            if isinstance(item,dict) and item.get("symbol"): symbols.append(str(item["symbol"]).upper())
        report["providers"]["market"]={"status":"passed" if data.get("status")=="ok" and len(symbols)>0 else "failed","provider_status":data.get("status"),"error_category":None if data.get("status")=="ok" else error_category(data),"duration_ms":duration(started),"record_count":len(assets) if isinstance(assets,list) else 0,"symbols":symbols,"retrieved_at_present":bool(data.get("retrieved_at"))}
    if not settings.newsapi_api_key: report["providers"]["news"]={"status":"not_run","reason":"key_not_configured"}
    else:
        news_results={};
        for query in ["bitcoin","ethereum"]:
            started=timer(); data=await crypto_news(query); articles=data.get("articles",[]); urls=[a.get("url") for a in articles if isinstance(a,dict)]
            news_results[query]={"status":"passed" if data.get("status")=="ok" and all(a.get("title") and a.get("source") and a.get("published_at") and a.get("url") for a in articles) else "failed","provider_status":data.get("status"),"error_category":None if data.get("status")=="ok" else error_category(data),"duration_ms":duration(started),"article_count":len(articles),"unique_url_count":len(set(urls)),"retrieved_at_present":bool(data.get("retrieved_at"))}
        report["providers"]["news"]={"status":"passed" if all(x["status"]=="passed" for x in news_results.values()) else "failed","queries":news_results}
    return report

async def agent_checks(only=None):
    from app.agents.graph import run_agent
    scenarios=[("btc_market","Analyze Bitcoin using live market data",None),("eth_market","Analyze Ethereum using live market data",None),("btc_news","Analyze Bitcoin news",None),("eth_news","Analyze Ethereum news",None),("compare","Compare Bitcoin and Ethereum",None),("follow_up","What about Ethereum?",[{"role":"user","content":"Analyze Bitcoin using live market data"}])]
    if only: scenarios=[item for item in scenarios if item[0] in only]
    rows=[]
    for name,question,history in scenarios:
        started=timer()
        try:
            state=await run_agent(question,history); evidence=state.get("evidence",[]); ids={x.get("id") for x in evidence}; answer=state.get("answer",""); cited=set(re.findall(r"\[(?:market|news):[^\]]+\]",answer)); cited_ids={x.strip("[]") for x in cited}
            rows.append({"id":name,"status":"passed" if state.get("answer") and any(x.get("stage")=="response_validation" for x in state.get("activity",[])) else "failed","duration_ms":duration(started),"tools":state.get("tools_needed",[]),"evidence_count":len(evidence),"cited_evidence_ids_valid":cited_ids.issubset(ids),"llm_synthesis_status":next((x.get("status") for x in state.get("activity",[]) if x.get("stage")=="llm_synthesis"),"unknown"),"tool_statuses":{x.get("stage"):x.get("status") for x in state.get("activity",[]) if x.get("stage") in {"market_tool","news_tool"}}})
        except Exception as exc: rows.append({"id":name,"status":"failed","duration_ms":duration(started),"error_type":type(exc).__name__})
    return rows

async def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--agent",action="store_true",help="run six real Ollama-backed scenarios"); parser.add_argument("--only",action="append",choices=["btc_market","eth_market","btc_news","eth_news","compare","follow_up"]); args=parser.parse_args()
    report=await provider_checks()
    if args.agent or args.only: report["agent_scenarios"]=await agent_checks(args.only)
    path=Path("backend/evaluation/results/phase9_live.json"); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(report,indent=2),encoding="utf-8"); print(json.dumps(report,indent=2))
if __name__=="__main__": asyncio.run(main())
