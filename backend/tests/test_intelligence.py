from app.agents.intelligence import evidence_packet
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
