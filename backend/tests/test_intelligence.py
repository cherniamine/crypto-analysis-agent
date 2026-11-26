import pytest
from app.agents.intelligence import _llm_error_category, evidence_packet, generate_analysis
from app.schemas.analysis import AnalysisResponse

def test_structured_response_has_required_sections():
    text = AnalysisResponse(executive_summary="BTC was observed.", market_data=["[market:BTC] $100"], risks=["Data may be stale."]).to_markdown()
    assert "## Executive Summary" in text
    assert "### Market Data" in text
    assert "### Risks & Uncertainty" in text

def test_evidence_packet_excludes_unvalidated_raw_records():
    packet = evidence_packet({"market":{"status":"ok","source":"test","assets":[{"secret":"should not be passed"}]},"news":{"status":"unavailable"}}, [{"id":"market:BTC","type":"market"}])
    assert "market:BTC" in packet
    assert "secret" not in packet

@pytest.mark.parametrize("error_name,expected", [
    ("DeadlineExceeded", "timeout"),
    ("TimeoutError", "timeout"),
    ("ServiceUnavailable", "network"),
    ("ConnectionError", "network"),
    ("NotFound", "model_not_found"),
    ("ResourceExhausted", "quota_or_rate_limit"),
])
def test_llm_error_categories_are_distinct(error_name, expected):
    error_type=type(error_name,(Exception,),{})
    assert _llm_error_category(error_type("synthetic failure"))==expected

@pytest.mark.asyncio
@pytest.mark.parametrize("error_name", ["DeadlineExceeded", "NotFound"])
async def test_llm_failure_preserves_fallback_and_logs_safe_metadata(monkeypatch, caplog, error_name):
    error_type=type(error_name,(Exception,),{})
    class FailingLLM:
        def with_structured_output(self, _schema): return self
        async def ainvoke(self, _messages): raise error_type("provider failure")
    monkeypatch.setattr("app.agents.intelligence.create_llm", lambda _settings: FailingLLM())
    monkeypatch.setattr("app.agents.intelligence.get_settings", lambda: type("S", (), {"evidence_context_char_budget":18000})())
    monkeypatch.setattr("app.agents.intelligence.descriptor", lambda _settings: type("D", (), {"provider":"gemini","model":"gemini-3.8-flash","configured":True})())
    with caplog.at_level("INFO", logger="crypto_agent"):
        answer, activity=await generate_analysis("Analyze BTC", [], {"market":{"status":"ok"}}, [])
    assert "Analyst unavailable" in answer
    assert activity[0]["status"]=="error"
    message=" ".join(record.message for record in caplog.records)
    assert "llm_synthesis" in message and "duration_ms" in message
    expected_category="timeout" if error_name=="DeadlineExceeded" else "model_not_found"
    assert expected_category in message
    assert "test-secret" not in message and "api_key" not in message.lower()
