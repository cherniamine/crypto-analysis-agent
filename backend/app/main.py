from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pathlib import Path
import time
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.database.repository import ConversationRepository
from app.schemas.models import ChatRequest, ChatResponse
from app.agents.graph import run_agent
from app.core.observability import Timer, log_event, new_request_id
from app.database.session import database_health, init_database
from app.llm.factory import descriptor

def evaluation_report_path():
    return Path(__file__).resolve().parents[1] / "evaluation" / "results" / "latest.json"

s=get_settings(); init_database(); repo=ConversationRepository(s.database_url)
cors_origins=set(s.cors_origins.split(","))
if "http://localhost:3000" in cors_origins: cors_origins.add("http://127.0.0.1:3000")
if "http://127.0.0.1:3000" in cors_origins: cors_origins.add("http://localhost:3000")
app=FastAPI(title=s.app_name,version="1.0.0",description="Evidence-based crypto market intelligence")
app.add_middleware(CORSMiddleware,allow_origins=list(cors_origins),allow_methods=["*"],allow_headers=["*"])
@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id=new_request_id(); started=time.perf_counter()
    response=await call_next(request)
    response.headers["X-Request-ID"]=request_id
    log_event("http_request",method=request.method,path=request.url.path,status=response.status_code,duration_ms=round((time.perf_counter()-started)*1000,2))
    return response
@app.get("/health")
async def health(): return {"status":"ok","providers":{"market":bool(s.freecryptoapi_api_key),"news":bool(s.newsapi_api_key),"openai":bool(s.openai_api_key)}}
@app.get("/api/health/providers")
async def provider_health():
    d=descriptor(s); ollama_status="not_tested"
    if d.provider=="ollama":
        try:
            import httpx
            async with httpx.AsyncClient(timeout=2) as client: response=await client.get(f"{s.ollama_base_url.rstrip('/')}/api/tags")
            ollama_status="reachable" if response.is_success else "unavailable"
        except Exception: ollama_status="unavailable"
    return {"llm":{"provider":d.provider,"model":d.model,"configured":d.configured,"reachability":ollama_status},"database":{"status":database_health()},"market_api":{"status":"configured" if s.freecryptoapi_api_key else "not_configured"},"news_api":{"status":"configured" if s.newsapi_api_key else "not_configured"}}
@app.get("/api/conversations")
async def conversations(): return repo.list()
@app.get("/api/conversations/{cid}")
async def conversation(cid:str): return {"id":cid,"messages":repo.messages(cid)}
@app.delete("/api/conversations/{cid}")
async def delete_conversation(cid:str): repo.delete(cid); return {"deleted":True}
@app.post("/api/chat",response_model=ChatResponse)
async def chat(request:ChatRequest):
    cid=repo.ensure(request.thread_id); history=repo.messages(cid); repo.add_message(cid,"user",request.message)
    with Timer() as timer: result=await run_agent(request.message,history)
    log_event("agent_execution",conversation_id=cid,selected_tools=result.get("tools_needed",[]),duration_ms=timer.duration_ms,stages=[x.get("stage") for x in result.get("activity",[])])
    repo.add_message(cid,"assistant",result["answer"])
    return ChatResponse(thread_id=cid,answer=result["answer"],evidence=result.get("evidence",[]),activity=result.get("activity",[]))
@app.get("/api/dashboard")
async def dashboard():
    from app.tools.crypto_market import market_data
    from app.tools.crypto_news import crypto_news
    return {"market":await market_data(),"news":await crypto_news()}
@app.get("/api/evaluation/latest")
async def latest_evaluation():
    import json
    path=evaluation_report_path()
    if not path.exists(): return JSONResponse({"status":"unavailable","message":"No evaluation run has been stored yet."},status_code=404)
    return json.loads(path.read_text(encoding="utf-8"))
