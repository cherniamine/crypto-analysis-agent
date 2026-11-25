import json

from app.agents.graph import process_evidence, validate_results, validate_response
from app.agents.intelligence import evidence_packet, validate_citations
from app.tools.crypto_news import normalize_news_response


def raw_article(title, url, source="Wire", published="2026-11-24T10:00:00Z"):
    return {"title": title, "url": url, "source": {"name": source}, "publishedAt": published, "description": "Verified excerpt"}


def test_news_normalization_preserves_required_metadata_and_deduplicates():
    articles, raw_count = normalize_news_response({"articles": [raw_article("Bitcoin update", "https://example.test/1"), raw_article("Duplicate", "https://example.test/1"), {"title": "Missing URL"}]})
    assert raw_count == 3
    assert len(articles) == 1
    assert articles[0] == {"title": "Bitcoin update", "source": "Wire", "url": "https://example.test/1", "published_at": "2026-11-24T10:00:00Z", "description": "Verified excerpt"}


def test_empty_news_response_is_explicit():
    articles, raw_count = normalize_news_response({"articles": []})
    assert articles == []
    assert raw_count == 0


def test_validation_telemetry_and_evidence_merge(monkeypatch):
    observations = {
        "market": {"status": "ok", "assets": [{"symbol": "BTC", "price": 100}], "retrieved_at": "t"},
        "news": {"status": "ok", "api_articles_received": 3, "normalized_articles": 3, "articles": [
            {"title": "Bitcoin ETF", "source": "Wire", "url": "https://example.test/1", "published_at": "t"},
            {"title": "Bitcoin network", "source": "Wire", "url": "https://example.test/2", "published_at": "t"},
            {"title": "Other", "source": "Wire", "url": "https://example.test/3", "published_at": "t"},
        ], "retrieved_at": "t"},
    }
    monkeypatch.setenv("NEWS_EVIDENCE_LIMIT", "2")
    from app.core.config import get_settings
    get_settings.cache_clear()
    validated = validate_results({"observations": observations})
    state = process_evidence({"question": "Bitcoin news", "observations": validated["observations"], "activity": validated["activity"]})
    activity = state["activity"][-1]
    news = [item for item in state["evidence"] if item["type"] == "news"]
    assert len([item for item in state["evidence"] if item["type"] == "market"]) == 1
    assert {item["id"] for item in news} == {"news:1", "news:2"}
    assert activity["api_articles_received"] == 3
    assert activity["normalized_articles"] == 3
    assert activity["news_evidence_created"] == 3
    assert activity["available_news"] == 3
    assert activity["selected_news"] == 2
    assert activity["dropped_news"] == 1


def test_selected_news_reaches_bounded_llm_packet(monkeypatch):
    monkeypatch.setenv("EVIDENCE_CONTEXT_CHAR_BUDGET", "4000")
    from app.core.config import get_settings
    get_settings.cache_clear()
    evidence = [{"id": "news:1", "type": "news", "title": "Bitcoin", "source": "Wire", "url": "https://example.test/1", "published_at": "t", "description": "x" * 10000}]
    packet = json.loads(evidence_packet({"news": {"status": "ok", "source": "NewsAPI"}}, evidence))
    assert packet["evidence_selection"]["news_available"] == 1
    assert packet["evidence_selection"]["news_included"] == 1
    assert packet["validated_evidence"][0]["url"] == "https://example.test/1"


def test_citation_integrity_accepts_valid_news_and_rejects_unknown_or_urlless():
    evidence = [{"id": "news:1", "type": "news", "url": "https://example.test/1"}, {"id": "news:2", "type": "news", "url": None}]
    assert validate_citations("See [news:1]", evidence)["valid"]
    assert not validate_citations("See [news:99]", evidence)["valid"]
    assert not validate_citations("See [news:2]", evidence)["valid"]


def test_news_requires_structured_citation_even_when_raw_url_is_present():
    evidence = [{"id": "news:1", "type": "news", "url": "https://example.test/1"}]
    result = validate_citations("Read https://example.test/1", evidence, require_news_citation=True)
    assert result["cited_count"] == 0
    assert result["missing_structured_news_citation"] is True
    assert result["valid"] is False


def test_final_response_removes_invalid_market_only_news_reference():
    state = validate_response({"tools_needed": ["market"], "answer": "Price is supported by [news:0].", "evidence": [{"id": "market:BTC", "type": "market", "data": {"symbol": "BTC"}}]})
    assert "[news:0]" not in state["answer"]
    citation = next(item for item in state["activity"] if item["stage"] == "citation_validation")
    assert citation["status"] == "error"
    assert "news:0" in citation["invalid_ids"]


def test_empty_provider_response_is_not_usable_success():
    from app.tools.crypto_news import normalize_news_response
    articles, raw_count = normalize_news_response({"articles": []})
    assert raw_count == 0 and articles == []
