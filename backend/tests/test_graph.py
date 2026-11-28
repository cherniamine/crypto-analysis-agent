import pytest
from app.agents.graph import normalize_route_text, route

@pytest.mark.parametrize("question,expected", [
    ("What is Bitcoin doing in the latest news?", ["news"]),
    ("What is the Bitcoin price and latest news?", ["market", "news"]),
    ("Analyze Bitcoin using recent news", ["market", "news"]),
    ("Show BTC price and explain recent headlines", ["market", "news"]),
    ("Analyse le prix du Bitcoin et les derni\u00e8res actualit\u00e9s.", ["market", "news"]),
    ("Donne-moi le cours actuel du BTC et les nouvelles importantes.", ["market", "news"]),
    ("Quel est le prix actuel du BTC ?", ["market"]),
    ("Quelles sont les derni\u00e8res actualit\u00e9s sur Ethereum ?", ["news"]),
    ("Pourquoi le Bitcoin baisse-t-il aujourd'hui ?", ["market"]),
    ("Pourquoi le prix du Bitcoin évolue-t-il et quelles sont les actualités ?", ["market", "news"]),
    ("What are the latest developments in Bitcoin?", ["news"]),
    ("Analyze the latest Bitcoin headlines", ["news"]),
    ("The price tag appeared in the news story", ["news"]),
    ("What is the source of the latest Bitcoin news?", ["news"]),
    ("Analyse les dernières actualités sur Bitcoin", ["news"]),
])
def test_multilingual_routes_select_expected_tools(question, expected):
    assert route({"question":question})["tools_needed"]==expected

@pytest.mark.parametrize("question,expected", [
    ("BITCOIN PRICE!!!", ["market"]),
    ("Quelles sont les dernieres actualites BTC", ["news"]),
    ("Bitcoin price and NEWS", ["market", "news"]),
    ("Tell me about a price tag in a story", ["market"]),
    ("What is a blockchain?", []),
])
def test_route_normalization_case_accents_punctuation_and_general_questions(question, expected):
    assert route({"question":question})["tools_needed"]==expected

def test_route_normalization_does_not_replace_original_question():
    original="Analyse le prix du Bitcoin et les derni\u00e8res actualit\u00e9s."
    assert normalize_route_text(original)=="analyse le prix du bitcoin et les dernieres actualites"
def test_routes_news_and_market():
    assert set(route({"question":"Compare BTC price with latest news"})["tools_needed"])=={"market","news"}

def test_route_tool_order_is_deterministic():
    question="Bitcoin price and latest news"
    assert route({"question":question})["tools_needed"]==["market","news"]
    assert route({"question":question})["tools_needed"]==["market","news"]
