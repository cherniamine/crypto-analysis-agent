"""Strict Phase 13.1 citation/evidence validation for native Windows."""
import asyncio, json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'backend'))
RESULT=ROOT/'backend/evaluation/results/phase13_1_report.json'

def duration(start): return round((time.perf_counter()-start)*1000,2)

def inspect_state(name, query, state, elapsed, history_used=False):
    from app.agents.intelligence import validate_citations
    evidence=state.get('evidence',[]); answer=state.get('answer',''); news=[x for x in evidence if x.get('type')=='news']; market=[x for x in evidence if x.get('type')=='market']; activities=state.get('activity',[])
    result_validation=next((x for x in activities if x.get('stage')=='result_validation'),{})
    selection=next((x for x in activities if x.get('stage')=='evidence_processing'),{})
    synthesis=next((x for x in activities if x.get('stage')=='llm_synthesis'),{})
    citations=validate_citations(answer,evidence,bool(news))
    urls={x.get('url') for x in news if x.get('url')}; cited_urls=sum(url in answer for url in urls)
    tools={x.get('stage'):x.get('status') for x in activities if x.get('stage') in {'market_tool','news_tool'}}
    usable=all(x=='ok' for x in tools.values()) and synthesis.get('status')=='complete' and any(x.get('stage')=='response_validation' for x in activities)
    if 'news' in state.get('tools_needed',[]): usable=usable and bool(news) and citations['valid'] and cited_urls>0
    if 'market' in state.get('tools_needed',[]): usable=usable and bool(market)
    return {'name':name,'query':query,'classification':'LIVE','status':'passed' if usable else 'failed','duration_ms':elapsed,'history_used':history_used,'tools_selected':state.get('tools_needed',[]),'tool_statuses':tools,'stages':[x.get('stage') for x in activities],'market_records':len(market),'news_articles_received':result_validation.get('api_articles_received',0),'news_normalized':result_validation.get('normalized_articles',0),'news_evidence_created':selection.get('news_evidence_created',0),'news_evidence_selected':selection.get('selected_news',0),'news_evidence_in_context':int(re.search(r'news evidence in context (\d+)',synthesis.get('label','')).group(1)) if re.search(r'news evidence in context (\d+)',synthesis.get('label','')) else 0,'market_evidence_in_context':int(re.search(r'market evidence in context (\d+)',synthesis.get('label','')).group(1)) if re.search(r'market evidence in context (\d+)',synthesis.get('label','')) else 0,'citation_validation':{**citations,'cited_urls_in_answer':cited_urls,'url_attribution_valid':cited_urls>0 if news else True},'llm_synthesis_status':synthesis.get('status'),'response_validation_status':next((x.get('status') for x in activities if x.get('stage')=='response_validation'),'unknown')}

async def main():
    from app.agents.graph import run_agent
    from app.core.config import get_settings
    s=get_settings(); report={'phase':'13.1','classification':'LIVE','timestamp':datetime.now(timezone.utc).isoformat(),'environment':{'provider':s.llm_provider,'model':s.active_llm_model},'scenarios':[],'limitations':[]}
    cases=[('btc_news','Latest Bitcoin news'),('eth_news','Latest Ethereum news'),('btc_market','Analyze the current Bitcoin market situation'),('eth_market','Analyze the current Ethereum market situation'),('combined','Analyze Bitcoin\'s current market situation and explain the latest important news affecting it.')]
    for name,query in cases:
        start=time.perf_counter()
        try: report['scenarios'].append(inspect_state(name,query,await run_agent(query),duration(start)))
        except Exception as exc: report['scenarios'].append({'name':name,'query':query,'classification':'LIVE','status':'failed','duration_ms':duration(start),'error_type':type(exc).__name__})
    initial='Analyze the current Bitcoin market situation and summarize the latest Bitcoin news.'; start=time.perf_counter(); first=await run_agent(initial); first_duration=duration(start); history=[{'role':'user','content':initial},{'role':'assistant','content':first.get('answer','')}]; start=time.perf_counter(); follow=await run_agent('What about Ethereum?',history); row=inspect_state('follow_up_eth','What about Ethereum?',follow,duration(start),True); row['initial_duration_ms']=first_duration; row['initial_evidence_count']=len(first.get('evidence',[])); report['scenarios'].append(row)
    report['verdict']='FIXED' if all(x.get('status')=='passed' for x in report['scenarios']) else 'PARTIALLY FIXED' if any(x.get('status')=='passed' for x in report['scenarios']) else 'INCONCLUSIVE'
    RESULT.parent.mkdir(parents=True,exist_ok=True); RESULT.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))

if __name__=='__main__': asyncio.run(main())
