from app.agents.graph import route
def test_routes_news_and_market():
    assert set(route({"question":"Compare BTC price with latest news"})["tools_needed"])=={"market","news"}
