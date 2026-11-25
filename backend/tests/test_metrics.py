from app.evaluation.metrics import evidence_grounding_score, source_attribution_accuracy, tool_selection_accuracy

def test_evaluation_metrics_are_measurable():
    rows=[{"selected_tools":["market"],"expected_tools":["market"],"answer":"Use [market:BTC]", "evidence_ids":["market:BTC"], "source_urls":[]}]
    assert tool_selection_accuracy(rows)==1
    assert evidence_grounding_score(rows)==1
    assert source_attribution_accuracy(rows)==1
