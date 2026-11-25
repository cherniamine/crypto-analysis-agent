import re
from statistics import mean

def tool_selection_accuracy(rows): return mean([r["selected_tools"] == r["expected_tools"] for r in rows]) if rows else 0.0
def tool_success_rate(rows):
    calls=[c for r in rows for c in r.get("tool_results",[])]
    return mean([c.get("status")=="ok" for c in calls]) if calls else None
def evidence_grounding_score(rows):
    scores=[]
    for r in rows:
        answer=r.get("answer",""); ids=set(r.get("evidence_ids",[])); cited=set(re.findall(r"\[(?:market|news):[^\]]+\]",answer)); scores.append(1.0 if not cited else len([x for x in cited if x.strip("[]") in ids])/len(cited))
    return mean(scores) if scores else 0.0
def source_attribution_accuracy(rows):
    scores=[]
    for r in rows:
        urls=set(r.get("source_urls",[])); cited=[x for x in re.findall(r"https?://\S+",r.get("answer",""))]; scores.append(1.0 if not cited else len([x for x in cited if x.rstrip(').,') in urls])/len(cited))
    return mean(scores) if scores else 0.0
def response_completeness(rows): return mean([bool(r.get("answer")) for r in rows]) if rows else 0.0
def context_retention(rows): return mean([bool(r.get("context_ok")) for r in rows if r.get("is_follow_up")]) if any(r.get("is_follow_up") for r in rows) else None
def latency_stats(rows):
    values=[r["latency_ms"] for r in rows if r.get("latency_ms") is not None]
    return {"count":len(values),"average_ms":round(mean(values),2) if values else None,"min_ms":min(values) if values else None,"max_ms":max(values) if values else None}
