"""Opt-in live validation for configured LLM and data providers.

Run from the repository root. The script never prints credentials or raw API payloads.
Without credentials/local services it reports ``not_run`` rather than pretending success.
"""
import argparse, asyncio, json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "backend"))

def result(provider,status,detail,duration_ms=None): return {"provider":provider,"status":status,"detail":detail,"duration_ms":duration_ms}

async def check_market():
    from app.tools.crypto_market import market_data
    from app.core.config import get_settings
    if not get_settings().freecryptoapi_api_key: return result("FreeCryptoAPI","not_run","FREECRYPTOAPI_API_KEY is not configured")
    started=time.perf_counter(); data=await market_data(["BTC"]); duration=round((time.perf_counter()-started)*1000,2); assets=data.get("assets",[]); valid=data.get("status")=="ok" and isinstance(assets,(list,dict))
    return result("FreeCryptoAPI","passed" if valid else "failed",{"status":data.get("status"),"record_count":len(assets) if isinstance(assets,(list,dict)) else 0},duration)

async def check_news():
    from app.tools.crypto_news import crypto_news
    from app.core.config import get_settings
    if not get_settings().newsapi_api_key: return result("NewsAPI","not_run","NEWSAPI_API_KEY is not configured")
    started=time.perf_counter(); data=await crypto_news("bitcoin"); duration=round((time.perf_counter()-started)*1000,2); articles=data.get("articles",[]); valid=data.get("status")=="ok" and all(a.get("title") and a.get("url") and a.get("published_at") for a in articles)
    return result("NewsAPI","passed" if valid else "failed",{"status":data.get("status"),"article_count":len(articles)},duration)

async def check_llm(provider):
    from app.agents.intelligence import generate_analysis
    from app.core.config import get_settings
    settings=get_settings(); configured=(bool(settings.ollama_model) and provider=="ollama" and bool(settings.ollama_base_url)) or (bool(settings.gemini_api_key) and provider=="gemini") or (bool(settings.openai_api_key) and provider=="openai")
    if not configured: return result(provider,"not_run",f"{provider} is not configured")
    started=time.perf_counter(); answer,activity=await generate_analysis("Summarize this verified BTC observation",[],{"market":{"status":"ok","source":"test","assets":[{"symbol":"BTC","price":100,"currency":"USD","timestamp":"2026-11-23T00:00:00Z"}]},"news":{"status":"unavailable","articles":[]}},[{"id":"market:BTC","type":"market","provider":"test","data":{"symbol":"BTC","price":100}}]); duration=round((time.perf_counter()-started)*1000,2); passed=bool(answer) and any(a.get("status")=="complete" for a in activity)
    return result(provider,"passed" if passed else "failed",{"structured_response":passed},duration)

async def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--provider",choices=["auto","ollama","gemini","openai"],default="auto"); parser.add_argument("--e2e",action="store_true",help="Run one complete agent call; may incur provider/API costs"); args=parser.parse_args()
    from app.core.config import get_settings
    settings=get_settings(); provider=settings.llm_provider.lower() if args.provider=="auto" else args.provider
    checks=[await check_market(),await check_news(),await check_llm(provider)]
    if args.e2e:
        if provider=="ollama" and not settings.ollama_base_url: checks.append(result("agent-e2e","not_run","Ollama endpoint is not configured"))
        elif provider=="gemini" and not settings.gemini_api_key: checks.append(result("agent-e2e","not_run","GEMINI_API_KEY is not configured"))
        elif provider=="openai" and not settings.openai_api_key: checks.append(result("agent-e2e","not_run","OPENAI_API_KEY is not configured"))
        else:
            from app.agents.graph import run_agent
            started=time.perf_counter(); state=await run_agent("Analyze Bitcoin's current market situation"); checks.append(result("agent-e2e","passed" if state.get("answer") else "failed",{"stages":len(state.get("activity",[])),"evidence":len(state.get("evidence",[]))},round((time.perf_counter()-started)*1000,2)))
    print(json.dumps({"live_validation":True,"active_provider":provider,"checks":checks},indent=2))
if __name__=="__main__":
    # Avoid starting an event loop for the zero-credential preflight path.
    from app.core.config import get_settings
    settings=get_settings(); provider=settings.llm_provider.lower()
    if not any([settings.freecryptoapi_api_key,settings.newsapi_api_key,settings.openai_api_key,settings.gemini_api_key,settings.ollama_base_url]):
        print(json.dumps({"live_validation":True,"active_provider":provider,"checks":[result("FreeCryptoAPI","not_run","API key is not configured"),result("NewsAPI","not_run","API key is not configured"),result(provider,"not_run","Provider credentials or endpoint are not configured")]},indent=2))
    else: asyncio.run(main())
