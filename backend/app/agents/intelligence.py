import json
import re
from app.agents.prompts import SYSTEM_PROMPT
from app.core.config import get_settings
from app.schemas.analysis import AnalysisResponse
from app.llm.factory import create_llm, descriptor

def validate_citations(answer: str, evidence: list[dict] | None = None, require_news_citation: bool = False) -> dict:
    records={item.get("id"):item for item in (evidence or [])}
    cited=set(re.findall(r"\[(?:market|news):[^\]]+\]",answer or ""))
    invalid=[]; news_without_url=[]; namespace_mismatch=[]
    for citation in sorted(cited):
        evidence_id=citation.strip("[]")
        record=records.get(evidence_id)
        if not record: invalid.append(evidence_id); continue
        namespace=evidence_id.split(":",1)[0]
        if record.get("type") != namespace: namespace_mismatch.append(evidence_id)
        if record.get("type")=="news" and not record.get("url"): news_without_url.append(citation)
    supplied_urls={item.get("url") for item in (evidence or []) if item.get("url")}
    raw_urls={url.rstrip(").,\"") for url in re.findall(r"https?://[^\s)]+",answer or "")}
    unknown_urls=sorted(raw_urls-supplied_urls)
    cited_news=any(item.startswith("[news:") for item in cited)
    missing_required_news=require_news_citation and any(item.get("type")=="news" for item in (evidence or [])) and not cited_news
    return {"valid":not invalid and not news_without_url and not namespace_mismatch and not unknown_urls and not missing_required_news,"cited_count":len(cited),"invalid_ids":invalid,"news_without_url":news_without_url,"namespace_mismatch":namespace_mismatch,"unknown_urls":unknown_urls,"missing_structured_news_citation":missing_required_news}

def sanitize_invalid_citations(answer: str, validation: dict) -> str:
    invalid=set(validation.get("invalid_ids",[]))|set(validation.get("namespace_mismatch",[]))
    for evidence_id in invalid: answer=answer.replace(f"[{evidence_id}]","[citation removed]")
    if validation.get("missing_structured_news_citation") or validation.get("unknown_urls"):
        answer += "\n\n### Risks & Uncertainty\n- Source attribution was withheld because the response did not provide valid structured citations for the retrieved evidence."
    return answer

def evidence_packet(observations: dict, evidence: list[dict] | None = None) -> str:
    """Create a small, stable, model-facing evidence contract."""
    market = observations.get("market", {})
    news = observations.get("news", {})
    records=list(evidence or [])
    packet = {"market": {"status": market.get("status"), "provider": market.get("source")},
              "news": {"status": news.get("status"), "provider": news.get("source")},
              "validated_evidence": records,
              "evidence_selection": {"available": len(records), "included": len(records),"news_available":sum(x.get("type")=="news" for x in records),"news_included":sum(x.get("type")=="news" for x in records),"truncated_for_context":False}}
    budget=max(4000,get_settings().evidence_context_char_budget)
    encoded=json.dumps(packet, ensure_ascii=False, default=str)
    if len(encoded)<=budget: return encoded
    # Evidence has already been selected by the graph. Trim only optional descriptions
    # and then whole records, preserving valid JSON, IDs, and source metadata.
    for item in packet["validated_evidence"]:
        if item.get("type")=="news" and item.get("description"):
            item["description"]=str(item["description"])[:240]
    while packet["validated_evidence"] and len(json.dumps(packet, ensure_ascii=False, default=str))>budget:
        packet["validated_evidence"].pop()
    packet["evidence_selection"]["included"]=len(packet["validated_evidence"])
    packet["evidence_selection"]["news_included"]=sum(x.get("type")=="news" for x in packet["validated_evidence"])
    packet["evidence_selection"]["truncated_for_context"]=len(packet["validated_evidence"]) < len(records)
    return json.dumps(packet, ensure_ascii=False, default=str)

async def generate_analysis(question: str, history: list[dict], observations: dict, evidence: list[dict] | None = None) -> tuple[str, list[dict]]:
    settings = get_settings()
    active=descriptor(settings)
    if not active.configured:
        return (f"## Analyst unavailable\n\nThe configured LLM provider `{active.provider}` is not configured, so no AI-generated interpretation was produced. The application will not substitute a fabricated analysis.\n\n### Data status\n- Provider results remain available in the evidence panel.\n- Configure the provider and retry this question.", [{"stage":"llm_synthesis","status":"unavailable","label":f"{active.provider} credentials or model are not configured"}])
    try:
        llm=create_llm(settings)
        structured = llm.with_structured_output(AnalysisResponse)
        prior = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in history[-8:])
        packet=evidence_packet(observations, evidence)
        prompt = f"Question:\n{question}\n\nRecent conversation:\n{prior or '(none)'}\n\nValidated evidence packet:\n{packet}"
        result = await structured.ainvoke([("system", SYSTEM_PROMPT), ("human", prompt)])
        analysis = result if isinstance(result, AnalysisResponse) else AnalysisResponse.model_validate(result)
        packet_selection=json.loads(packet).get("evidence_selection",{})
        selected_news=packet_selection.get("news_included",0)
        selected_market=sum(item.get("type")=="market" for item in json.loads(packet).get("validated_evidence",[]))
        return analysis.to_markdown(), [{"stage":"llm_synthesis","status":"complete","label":f"Generated structured analysis with {active.provider}/{active.model}; prompt {len(prompt)} chars (~{len(prompt)//4} tokens); market evidence in context {selected_market}; news evidence in context {selected_news}"}]
    except Exception as exc:
        return (f"## Analyst unavailable\n\nThe {active.provider} synthesis request failed safely: `{type(exc).__name__}`. No unsupported market claims were generated.\n\nRetry after checking the provider configuration and availability.", [{"stage":"llm_synthesis","status":"error","label":f"{active.provider} synthesis failed"}])
