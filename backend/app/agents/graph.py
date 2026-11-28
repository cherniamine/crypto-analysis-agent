import re
import unicodedata
from typing import Any
from app.core.config import get_settings
from langgraph.graph import END, StateGraph
from app.agents.intelligence import generate_analysis, validate_citations, sanitize_invalid_citations
from app.agents.state import AgentState
from app.tools.crypto_market import market_data
from app.tools.crypto_news import crypto_news

MAX_TOOL_CALLS = 2

def normalize_route_text(text: str) -> str:
    normalized=unicodedata.normalize("NFKD", text or "")
    normalized="".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", normalized.lower(), flags=re.UNICODE)).strip()

def contains_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)

def build_news_query(question: str) -> str:
    q=question.lower()
    assets=[]
    for term,name in (("bitcoin","Bitcoin"),("btc","Bitcoin"),("ethereum","Ethereum"),("eth","Ethereum"),("sol","Solana"),("xrp","XRP"),("ada","Cardano"),("doge","Dogecoin")):
        if re.search(rf"\b{term}\b",q) and name not in assets: assets.append(name)
    if assets: return " ".join(assets)+" cryptocurrency news"
    return "cryptocurrency market news"

def process_input(state: AgentState):
    return {"question": state.get("question", "").strip(), "activity": [{"stage":"input_processing","status":"complete","label":"Question normalized"}]}

def route(state: AgentState):
    q=normalize_route_text(state["question"]); tools=[]
    no_tool_terms=("hello", "how are you", "what is a blockchain", "how do crypto wallets", "write python code", "is it a good time")
    if any(re.search(rf"\b{re.escape(term)}\b", q) for term in no_tool_terms):
        return {"tools_needed":[],"activity":state.get("activity",[])+[{"stage":"intent_classification","status":"complete","label":"General or ambiguous question; no live tool required"}]}
    news_terms=("news","actualite","actualites","nouvelle","nouvelles","headline","headlines","titre","titres","development","developments","developpement","developpements","event","evenement","evenements","sentiment","recent","recente","recents","recentes","source")
    why_terms=("why did","pourquoi")
    market_terms=("price","prix","cours","valeur","market","marche","performance","evolution","hausse","baisse","augmentation","diminution","bullish","bearish","movement","variation","compare","comparaison","affect")
    analysis_terms=("analyze","analyse","analysis")
    price_terms=("price","prix","cours","valeur")
    financial_context=("bitcoin","btc","ethereum","eth","sol","xrp","ada","doge","crypto","cryptocurrency","coin","token","market","marche")
    has_explicit_news=contains_term(q,news_terms)
    has_why=contains_term(q,why_terms)
    has_news=has_explicit_news or (has_why and not contains_term(q,market_terms))
    has_asset=contains_term(q,("btc","bitcoin","eth","ethereum","sol","xrp","ada","doge"))
    has_market_action=contains_term(q,market_terms)
    if contains_term(q,analysis_terms) and not has_market_action:
        has_market_action=not has_explicit_news or contains_term(q,("using recent news","using the latest news","en utilisant les dernieres actualites"))
    if contains_term(q,price_terms) and not (has_asset or contains_term(q,financial_context)):
        has_market_action=False
    if has_market_action or (has_asset and not has_news): tools.append("market")
    if has_news: tools.append("news")
    selected=tools or (["news"] if contains_term(q,("what happened",)) else ["market"])
    return {"tools_needed":selected,"activity":state.get("activity",[])+[{"stage":"intent_classification","status":"complete","label":f"Selected {', '.join(selected)} tool"}]}

async def execute(state: AgentState):
    selected=state.get("tools_needed",[])[:MAX_TOOL_CALLS]; observations:dict[str,Any]={}; activity=list(state.get("activity",[]))
    if "market" in selected:
        symbols=re.findall(r"\b(BTC|ETH|SOL|XRP|ADA|DOGE)\b",state["question"].upper()) or ["BTC","ETH"]
        observations["market"]=await market_data(list(dict.fromkeys(symbols))); activity.append({"stage":"market_tool","status":observations["market"].get("status","error"),"label":"FreeCryptoAPI market retrieval"})
    if "news" in selected:
        news_query=build_news_query(state["question"])
        observations["news"]=await crypto_news(news_query); observations["news"]["query"]=news_query
        activity.append({"stage":"news_tool","status":observations["news"].get("status","error"),"label":f"NewsAPI article retrieval ({news_query})","query":news_query,"api_articles_received":observations["news"].get("api_articles_received",0),"normalized_articles":observations["news"].get("normalized_articles",0)})
    return {"observations":observations,"activity":activity}

def validate_results(state: AgentState):
    observations=state.get("observations",{})
    for key,value in observations.items():
        if not isinstance(value,dict): observations[key]={"status":"error","message":"Invalid provider response","assets":[],"articles":[]}; continue
        if key=="news":
            raw=value.get("articles",[]) if isinstance(value.get("articles",[]),list) else []
            value["articles"]=[a for a in raw if a.get("title") and a.get("source") and a.get("published_at") and a.get("url")]
            value["validation_articles_discarded"]=len(raw)-len(value["articles"])
        if key=="market":
            assets=value.get("assets",[])
            if isinstance(assets,dict):
                assets=assets.get("data", [assets]) if isinstance(assets.get("data"),list) else [assets]
            value["assets"]=assets if isinstance(assets,list) else []
    news=observations.get("news",{})
    validation_activity={"stage":"result_validation","status":"complete","label":"Provider responses validated","api_articles_received":news.get("api_articles_received",0),"normalized_articles":news.get("normalized_articles",len(news.get("articles",[]))),"validated_articles":len(news.get("articles",[])),"discarded_articles":news.get("validation_articles_discarded",0)}
    return {"observations":observations,"activity":state.get("activity",[])+[validation_activity]}

def process_evidence(state: AgentState):
    obs=state.get("observations",{}); evidence=[]
    assets=obs.get("market",{}).get("assets",[]) if isinstance(obs.get("market",{}).get("assets"),list) else []
    market_retrieved=obs.get("market",{}).get("retrieved_at")
    for index,asset in enumerate(assets): evidence.append({"id":f"market:{asset.get('symbol',index)}","type":"market","provider":"FreeCryptoAPI","retrieved_at":market_retrieved,"data":asset})
    news_retrieved=obs.get("news",{}).get("retrieved_at")
    articles=obs.get("news",{}).get("articles",[])
    question_tokens={x for x in re.findall(r"[a-z0-9]+",state.get("question","").lower()) if len(x)>2}
    def relevance(article):
        text=" ".join(str(article.get(x) or "") for x in ("title","description","source")).lower()
        return sum(token in text for token in question_tokens)
    ranked=sorted(enumerate(articles),key=lambda item:(relevance(item[1]), item[0]),reverse=True)
    limit=max(1,get_settings().news_evidence_limit)
    news_records=[]
    for original_index,article in enumerate(articles,1):
        news_records.append({"id":f"news:{original_index}","type":"news","provider":"NewsAPI","retrieved_at":news_retrieved,"title":article.get("title"),"source":article.get("source"),"url":article.get("url"),"published_at":article.get("published_at"),"description":article.get("description")})
    selected=ranked[:limit]
    evidence.extend(news_records[item[0]] for item in selected)
    dropped=max(0,len(articles)-len(selected))
    label=f"Prepared {len(evidence)} evidence records"
    if articles: label+=f"; selected {len(selected)}/{len(articles)} news records by relevance"
    return {"evidence":evidence,"activity":state.get("activity",[])+[{"stage":"evidence_processing","status":"complete","label":label,"api_articles_received":obs.get("news",{}).get("api_articles_received",0),"normalized_articles":obs.get("news",{}).get("normalized_articles",len(articles)),"news_evidence_created":len(news_records),"available_news":len(articles),"selected_news":len(selected),"dropped_news":dropped}]}

async def synthesize(state: AgentState):
    answer,llm_activity=await generate_analysis(state["question"],state.get("history",[]),state.get("observations",{}),state.get("evidence",[]))
    return {"answer":answer,"activity":state.get("activity",[])+llm_activity}

def validate_response(state: AgentState):
    answer=state.get("answer","").strip() or "## Analyst unavailable\n\nNo response was generated. Please retry."
    require_news="news" in state.get("tools_needed",[]) and any(item.get("type")=="news" for item in state.get("evidence",[]))
    citation=validate_citations(answer,state.get("evidence",[]),require_news)
    if not citation["valid"]: answer=sanitize_invalid_citations(answer,citation)
    citation_status="complete" if citation["valid"] else "error"
    citation_label="Citation integrity validated" if citation["valid"] else f"Invalid citations: {len(citation['invalid_ids'])}; news records without URLs: {len(citation['news_without_url'])}"
    return {"answer":answer,"activity":state.get("activity",[])+[{"stage":"citation_validation","status":citation_status,"label":citation_label,**citation},{"stage":"response_validation","status":"complete","label":"Response contract validated"}]}

def build_graph():
    graph=StateGraph(AgentState)
    for name,node in [("input_processing",process_input),("intent_classification",route),("tool_execution",execute),("result_validation",validate_results),("evidence_processing",process_evidence),("llm_synthesis",synthesize),("response_validation",validate_response)]: graph.add_node(name,node)
    graph.set_entry_point("input_processing")
    for first,second in [("input_processing","intent_classification"),("intent_classification","tool_execution"),("tool_execution","result_validation"),("result_validation","evidence_processing"),("evidence_processing","llm_synthesis"),("llm_synthesis","response_validation")]: graph.add_edge(first,second)
    graph.add_edge("response_validation",END); return graph.compile()

AGENT_GRAPH=build_graph()
async def run_agent(question:str,history:list[dict]|None=None): return await AGENT_GRAPH.ainvoke({"question":question,"history":history or []})
