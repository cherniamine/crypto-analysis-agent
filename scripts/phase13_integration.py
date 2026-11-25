"""Sequential Phase 13 live multi-scenario integration validation.

Run this from native PowerShell where FreeCryptoAPI, NewsAPI, and Ollama are
reachable. Output is sanitized and contains no answers, URLs, or credentials.
"""
import argparse, asyncio, json, re, time, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
RESULT=ROOT/'backend/evaluation/results/phase13_integration.json'

SCENARIOS=[
    ('news_btc','Latest Bitcoin news'),
    ('news_eth','Latest Ethereum news'),
    ('market_btc','Analyze the current Bitcoin market situation'),
    ('market_eth','Analyze the current Ethereum market situation'),
    ('combined_btc',"Analyze Bitcoin's current market situation and explain the latest important news affecting it."),
]

def ms(start): return round((time.perf_counter()-start)*1000,2)

def citation_check(answer,evidence):
    from app.agents.intelligence import validate_citations
    result=validate_citations(answer,evidence,any(x.get('type')=='news' for x in evidence))
    urls=[x.get('url') for x in evidence if x.get('type')=='news' and x.get('url')]
    result['cited_urls_in_answer']=sum(url in answer for url in urls)
    result['url_attribution_valid']=result['cited_urls_in_answer']>0 if urls else True
    return result

def row_from_state(name,query,state,duration,history_used=False):
    evidence=state.get('evidence',[]); market=[x for x in evidence if x.get('type')=='market']; news=[x for x in evidence if x.get('type')=='news']
    answer=state.get('answer','')
    activities=state.get('activity',[])
    synthesis=next((x for x in activities if x.get('stage')=='llm_synthesis'),{})
    validation=next((x for x in activities if x.get('stage')=='result_validation'),{})
    selection=next((x for x in activities if x.get('stage')=='evidence_processing'),{})
    tool_status={x.get('stage'):x.get('status') for x in activities if x.get('stage') in {'market_tool','news_tool'}}
    m=re.search(r'market evidence in context (\d+)',synthesis.get('label','')); n=re.search(r'news evidence in context (\d+)',synthesis.get('label',''))
    citations=citation_check(answer,evidence)
    provider_ok=all(v=='ok' for v in tool_status.values()) if tool_status else False
    news_required='news' in state.get('tools_needed',[]); market_required='market' in state.get('tools_needed',[])
    evidence_ok=(not news_required or len(news)>0) and (not market_required or len(market)>0)
    passed=bool(answer) and provider_ok and evidence_ok and synthesis.get('status')=='complete' and citations.get('valid',False) and any(x.get('stage')=='response_validation' for x in activities)
    return {'name':name,'query':query,'classification':'LIVE','status':'passed' if passed else 'failed','duration_ms':duration,'history_used':history_used,'tools_selected':state.get('tools_needed',[]),'tool_statuses':tool_status,'stages': [x.get('stage') for x in activities],'market_records':len(market),'news_articles_received':validation.get('api_articles_received',0),'news_normalized':validation.get('normalized_articles',0),'news_evidence_created':selection.get('news_evidence_created',0),'news_evidence_selected':selection.get('selected_news',0),'news_evidence_dropped':selection.get('dropped_news',0),'market_evidence_in_llm_context':int(m.group(1)) if m else 0,'news_evidence_in_llm_context':int(n.group(1)) if n else 0,'news_evidence_with_urls':sum(bool(x.get('url')) for x in news),'citation_validation':citations,'llm_synthesis_status':synthesis.get('status'),'response_validation_status':next((x.get('status') for x in activities if x.get('stage')=='response_validation'),'unknown'),'prompt_chars_estimate':int(re.search(r'prompt (\d+) chars',synthesis.get('label','')).group(1)) if re.search(r'prompt (\d+) chars',synthesis.get('label','')) else None}

async def main():
    from app.agents.graph import run_agent
    from app.core.config import get_settings
    settings=get_settings()
    report={'phase':'13','classification':'LIVE','timestamp':datetime.now(timezone.utc).isoformat(),'environment':{'llm_provider':settings.llm_provider,'model':settings.active_llm_model,'timeout_seconds':settings.llm_timeout_seconds,'news_evidence_limit':settings.news_evidence_limit,'evidence_context_char_budget':settings.evidence_context_char_budget},'scenarios':[],'limitations':[]}
    try:
        for name,query in SCENARIOS:
            started=time.perf_counter()
            try: report['scenarios'].append(row_from_state(name,query,await run_agent(query),ms(started)))
            except Exception as exc: report['scenarios'].append({'name':name,'query':query,'classification':'LIVE','status':'failed','duration_ms':ms(started),'error_type':type(exc).__name__})
        initial='Analyze the current Bitcoin market situation and summarize the latest Bitcoin news.'
        started=time.perf_counter(); first=await run_agent(initial); first_duration=ms(started)
        history=[{'role':'user','content':initial},{'role':'assistant','content':first.get('answer','')}]
        started=time.perf_counter(); follow=await run_agent('What about Ethereum?',history); follow_duration=ms(started)
        row=row_from_state('follow_up_eth','What about Ethereum?',follow,follow_duration,True); row['initial_execution_duration_ms']=first_duration; row['initial_tools_selected']=first.get('tools_needed',[]); row['initial_evidence_count']=len(first.get('evidence',[])); report['scenarios'].append(row)
    except Exception as exc: report['classification']='INCONCLUSIVE'; report['limitations'].append(type(exc).__name__)
    if report['scenarios'] and all(x.get('status')=='passed' for x in report['scenarios']): report['verdict']='LIVE VALIDATED'
    else: report['verdict']='PARTIALLY VALIDATED' if any(x.get('status')=='passed' for x in report['scenarios']) else 'INCONCLUSIVE'
    RESULT.parent.mkdir(parents=True,exist_ok=True); RESULT.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))

if __name__=='__main__': asyncio.run(main())
