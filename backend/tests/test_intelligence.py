import pytest
from app.agents.intelligence import _exception_metadata, _llm_error_category, evidence_packet, generate_analysis
from app.schemas.analysis import AnalysisResponse
from google.api_core.exceptions import DeadlineExceeded, GatewayTimeout, NotFound, ResourceExhausted, ServiceUnavailable

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

@pytest.mark.parametrize("error,expected_status", [
    (NotFound("missing"),404),
    (ServiceUnavailable("unavailable"),503),
    (GatewayTimeout("gateway timeout"),504),
    (DeadlineExceeded("deadline"),504),
    (ResourceExhausted("quota"),429),
])
def test_google_exception_statuses_are_inferred_without_claiming_http_response(error, expected_status):
    metadata=_exception_metadata(error)
    assert metadata["http_status_code"] is None
    assert metadata["inferred_http_status_code"]==expected_status
    assert metadata["status_source"]=="exception_mapping"

def test_deadline_exceeded_exposes_google_status_when_available():
    metadata=_exception_metadata(DeadlineExceeded("deadline"))
    assert metadata["google_api_status"]=="DEADLINE_EXCEEDED"

def test_custom_not_found_name_does_not_receive_google_mapping():
    class NotFound(Exception): pass
    metadata=_exception_metadata(NotFound("custom"))
    assert metadata["inferred_http_status_code"] is None
    assert metadata["status_source"]=="unavailable"

def test_actual_http_response_status_takes_precedence_over_inference():
    class Response: status_code=503
    error=RuntimeError("service failure")
    error.response=Response()
    metadata=_exception_metadata(error)
    assert metadata=={"http_status_code":503,"inferred_http_status_code":None,"google_api_status":None,"status_source":"http_response"}

def test_exception_metadata_follows_context_chain():
    outer=RuntimeError("outer")
    inner=ServiceUnavailable("unavailable")
    outer.__context__=inner
    assert _exception_metadata(outer)["inferred_http_status_code"]==503

def test_exception_chain_is_limited_to_three_levels():
    first=RuntimeError("first"); second=RuntimeError("second"); third=RuntimeError("third"); fourth=NotFound("hidden")
    first.__cause__=second; second.__cause__=third; third.__cause__=fourth
    assert _exception_metadata(first)["inferred_http_status_code"] is None

def test_exception_with_unsafe_properties_returns_safe_metadata():
    class Unsafe(Exception):
        @property
        def response(self): raise RuntimeError("unsafe")
        @property
        def grpc_status_code(self): raise RuntimeError("unsafe")
        @property
        def __cause__(self): raise RuntimeError("unsafe")
    metadata=_exception_metadata(Unsafe("unsafe details"))
    assert metadata=={"http_status_code":None,"inferred_http_status_code":None,"google_api_status":None,"status_source":"unavailable"}

@pytest.mark.parametrize("error", [TimeoutError("timeout"), ConnectionError("connection")])
def test_generic_errors_do_not_receive_fabricated_status(error):
    metadata=_exception_metadata(error)
    assert metadata=={"http_status_code":None,"inferred_http_status_code":None,"google_api_status":None,"status_source":"unavailable"}

def test_exception_metadata_supports_bounded_cause_chain_and_cycles():
    wrapped=RuntimeError("secret prompt and api-key-value")
    wrapped.__cause__=NotFound("missing")
    metadata=_exception_metadata(wrapped)
    assert metadata["inferred_http_status_code"]==404
    cycle=RuntimeError("cycle")
    cycle.__cause__=cycle
    assert _exception_metadata(cycle)["status_source"]=="unavailable"

def test_error_log_contains_metadata_but_not_raw_exception_content(monkeypatch, caplog):
    class FailingLLM:
        def with_structured_output(self, _schema): return self
        async def ainvoke(self, _messages): raise NotFound("SECRET_API_KEY prompt-content", details=({"sensitive":"sensitive-detail"},))
    monkeypatch.setattr("app.agents.intelligence.create_llm", lambda _settings: FailingLLM())
    monkeypatch.setattr("app.agents.intelligence.get_settings", lambda: type("S", (), {"evidence_context_char_budget":18000})())
    monkeypatch.setattr("app.agents.intelligence.descriptor", lambda _settings: type("D", (), {"provider":"gemini","model":"gemini-3.8-flash","configured":True})())
    with caplog.at_level("INFO", logger="crypto_agent"):
        import asyncio
        asyncio.run(generate_analysis("private prompt", [], {"market":{"status":"ok"}}, []))
    message=" ".join(record.message for record in caplog.records)
    assert '"inferred_http_status_code": 404' in message
    assert "SECRET_API_KEY" not in message
    assert "prompt-content" not in message
    assert "sensitive-detail" not in message
    assert "private prompt" not in message

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
