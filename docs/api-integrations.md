# API integrations

## FreeCryptoAPI

The market tool calls the documented `/getData` endpoint with a `symbol` query and `X-Api-Key`. Configure `FREECRYPTOAPI_API_KEY`. If the key is absent, the API returns an explicit unavailable state.

## NewsAPI

The news tool calls the documented `/v2/everything` endpoint with keyword search, English language, recent sorting, and an eight-article cap. Configure `NEWSAPI_API_KEY`.

## OpenAI

`OPENAI_API_KEY` and `OPENAI_MODEL` are reserved for the intelligence layer. Provider retrieval and persistence remain independently testable; no key is needed for the test suite.
