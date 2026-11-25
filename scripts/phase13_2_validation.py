"""Sequential Phase 13.2 combined market/news reliability validation."""
import asyncio,json,re,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'backend'))
RESULT=ROOT/'backend/evaluation/results/phase13_2_report.json'
CASES=[('btc_news','Latest Bitcoin news'),('eth_news','Latest Ethereum news'),('btc_market','Analyze the current Bitcoin market situation'),('eth_market','Analyze the current Ethereum market situation'),('btc_combined',"Analyze Bitcoin's current market situation and explain the latest important news affecting it."),('eth_combined',"Analyze Ethereum's current market situation and explain the latest important news affecting it.")]
def elapsed(s): return round((time.perf_counter()-s)*1000,2)
def inspect(name,query,state,duration,history_used=False):
 from app.agents.intelligence import validate_citations
 ev=state.get('evidence',[]); market=[x for x in ev if x.get('type')=='market']; news=[x for x in ev if x.get('type')=='news']; act=state.get('activity',[]); rv=next((x for x in act if x.get('stage')=='result_validation'),{}); sel=next((x for x in act if x.get('stage')=='evidence_processing'),{}); syn=next((x for x in act if x.get('stage')=='llm_synthesis'),{}); nt=next((x for x in act if x.get('stage')=='news_tool'),{}); mt=next((x for x in act if x.get('stage')=='market_tool'),{}); citations=validate_citations(state.get('answer',''),ev,bool(news)); nm=re.search(r'news evidence in context (\d+)',syn.get('label','')); mm=re.search(r'market evidence in context (\d+)',syn.get('label','')); tools=state.get('tools_needed',[]); usable=bool(state.get('answer')) and syn.get('status')=='complete' and any(x.get('stage')=='response_validation' for x in act)
 if 'market' in tools: usable=usable and mt.get('status')=='ok' and bool(market) and (int(mm.group(1)) if mm else 0)>0
 if 'news' in tools: usable=usable and nt.get('status')=='ok' and bool(news) and (int(nm.group(1)) if nm else 0)>0 and citations.get('valid',False)
 return {'name':name,'query':query,'classification':'LIVE','status':'passed' if usable else 'failed','duration_ms':duration,'history_used':history_used,'tools_selected':tools,'tool_statuses':{'market':mt.get('status'),'news':nt.get('status')},'news_query':nt.get('query'),'news_api_articles_received':rv.get('api_articles_received',0),'news_normalized_articles':rv.get('normalized_articles',0),'news_rejected_articles':rv.get('discarded_articles',0),'news_evidence_created':sel.get('news_evidence_created',0),'news_evidence_selected':sel.get('selected_news',0),'news_evidence_in_context':int(nm.group(1)) if nm else 0,'market_records':len(market),'market_evidence_in_context':int(mm.group(1)) if mm else 0,'citation_validation':citations,'llm_synthesis_status':syn.get('status'),'response_validation_status':next((x.get('status') for x in act if x.get('stage')=='response_validation'),'unknown')}
async def main():
 from app.agents.graph import run_agent
 from app.core.config import get_settings
 s=get_settings(); report={'phase':'13.2','classification':'LIVE','timestamp':datetime.now(timezone.utc).isoformat(),'environment':{'provider':s.llm_provider,'model':s.active_llm_model},'scenarios':[]}
 for name,q in CASES:
  st=time.perf_counter()
  try: report['scenarios'].append(inspect(name,q,await run_agent(q),elapsed(st)))
  except Exception as e: report['scenarios'].append({'name':name,'query':q,'classification':'LIVE','status':'failed','duration_ms':elapsed(st),'error_type':type(e).__name__})
 initial='Analyze the current Bitcoin market situation and summarize the latest Bitcoin news.'; st=time.perf_counter(); first=await run_agent(initial); first_ms=elapsed(st); hist=[{'role':'user','content':initial},{'role':'assistant','content':first.get('answer','')}]; st=time.perf_counter(); follow=await run_agent('What about Ethereum?',hist); row=inspect('follow_up_eth','What about Ethereum?',follow,elapsed(st),True); row['initial_duration_ms']=first_ms; row['initial_evidence_count']=len(first.get('evidence',[])); report['scenarios'].append(row)
 report['verdict']='LIVE VALIDATED' if all(x.get('status')=='passed' for x in report['scenarios']) else 'PARTIALLY VALIDATED' if any(x.get('status')=='passed' for x in report['scenarios']) else 'INCONCLUSIVE'; RESULT.parent.mkdir(parents=True,exist_ok=True); RESULT.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': asyncio.run(main())
