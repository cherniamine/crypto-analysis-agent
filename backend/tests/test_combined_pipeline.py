import asyncio

from app.agents import graph


def fake_market(symbols):
    async def run():
        return {"status": "ok", "assets": [{"symbol": symbol, "price": 100} for symbol in symbols], "retrieved_at": "t"}
    return run()


def fake_news(query):
    async def run():
        return {"status": "ok", "query": query, "source": "NewsAPI", "api_articles_received": 1, "normalized_articles": 1, "articles": [{"title": "Bitcoin update", "source": "Wire", "url": "https://example.test/news", "published_at": "t"}], "retrieved_at": "t"}
    return run()


def test_combined_query_uses_asset_focused_news_query():
    assert graph.build_news_query("Analyze Bitcoin's current market situation and explain the latest important news affecting it.") == "Bitcoin cryptocurrency news"
    assert graph.build_news_query("Analyze Ethereum market and latest news") == "Ethereum cryptocurrency news"


def test_combined_execution_preserves_market_and_news(monkeypatch):
    monkeypatch.setattr(graph, "market_data", fake_market)
    monkeypatch.setattr(graph, "crypto_news", fake_news)
    state = asyncio.run(graph.execute({"question": "Analyze Bitcoin market and latest news", "tools_needed": ["market", "news"], "activity": []}))
    assert state["observations"]["market"]["status"] == "ok"
    assert state["observations"]["news"]["status"] == "ok"
    assert state["observations"]["news"]["query"] == "Bitcoin cryptocurrency news"
    assert len(state["observations"]["market"]["assets"]) == 2
    assert len(state["observations"]["news"]["articles"]) == 1
    assert [x["stage"] for x in state["activity"]] == ["market_tool", "news_tool"]


def test_empty_and_failed_news_statuses_remain_distinct():
    empty = graph.validate_results({"observations": {"news": {"status": "empty", "articles": [], "api_articles_received": 0}}})
    failed = graph.validate_results({"observations": {"news": {"status": "error", "articles": [], "message": "timeout"}}})
    assert empty["observations"]["news"]["status"] == "empty"
    assert failed["observations"]["news"]["status"] == "error"
    assert empty["activity"][-1]["api_articles_received"] == 0


def test_combined_evidence_contains_both_types(monkeypatch):
    monkeypatch.setenv("NEWS_EVIDENCE_LIMIT", "5")
    from app.core.config import get_settings
    get_settings.cache_clear()
    state = graph.process_evidence({"question": "Bitcoin market and latest news", "observations": {"market": {"status": "ok", "assets": [{"symbol": "BTC", "price": 100}]}, "news": {"status": "ok", "api_articles_received": 1, "normalized_articles": 1, "articles": [{"title": "Bitcoin update", "source": "Wire", "url": "https://example.test/news", "published_at": "t"}]}}})
    assert {x["type"] for x in state["evidence"]} == {"market", "news"}
    assert state["activity"][-1]["news_evidence_created"] == 1
