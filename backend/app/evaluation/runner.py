import json, time
from pathlib import Path
from app.agents.graph import route
from app.evaluation.dataset import DATASET_VERSION, EVALUATION_CASES
from app.evaluation.metrics import *

def run_evaluation(output_path="evaluation/results/latest.json"):
    rows=[]
    for case in EVALUATION_CASES:
        started=time.perf_counter(); routing=route({"question":case["question"]}); selected=routing["tools_needed"]
        rows.append({"id":case["id"],"question":case["question"],"expected_tools":case["tools"],"selected_tools":selected,"answer":"","evidence_ids":[],"source_urls":[],"tool_results":[],"is_follow_up":case["intent"]=="follow_up","context_ok":case["intent"]!="follow_up","latency_ms":round((time.perf_counter()-started)*1000,2),"passed":selected==case["tools"]})
    report={"evaluation_timestamp":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"dataset_version":DATASET_VERSION,"mode":"deterministic-routing","scenarios":len(rows),"passed":sum(r["passed"] for r in rows),"failed":sum(not r["passed"] for r in rows),"metrics":{"tool_selection_accuracy":tool_selection_accuracy(rows),"tool_success_rate":tool_success_rate(rows),"evidence_grounding_score":evidence_grounding_score(rows),"source_attribution_accuracy":source_attribution_accuracy(rows),"response_completeness":response_completeness(rows),"context_retention":context_retention(rows),"latency":latency_stats(rows),"token_usage":"unavailable (no LLM execution)","estimated_cost":"unavailable (no LLM execution)"},"cases":rows}
    path=Path(output_path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report

if __name__ == "__main__":
    report=run_evaluation(); print(json.dumps({"scenarios":report["scenarios"],"passed":report["passed"],"metrics":report["metrics"]},indent=2))
