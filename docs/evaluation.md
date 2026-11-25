# Evaluation, observability, and reliability

## Running the benchmark

From `backend`:

```powershell
$env:PYTHONPATH=(Get-Location).Path
python -m app.evaluation.runner
```

The deterministic benchmark loads 20 cases from `app/evaluation/dataset.py`, exercises the routing policy, and writes `backend/evaluation/results/latest.json`. It does not call paid APIs, so token usage, LLM cost, provider success, and generated-answer quality are reported as unavailable rather than guessed.

## Metrics

- Tool selection accuracy: exact match between expected and selected tool sets.
- Tool success rate: valid `ok` provider results divided by tool calls; unavailable when no provider calls were executed.
- Evidence grounding: cited evidence IDs that exist in the evidence set.
- Source attribution: cited URLs that exist in retrieved source metadata.
- Response completeness: non-empty validated answers.
- Context retention: follow-up cases that preserve the expected conversation context.
- Latency: measured routing or execution duration in milliseconds.
- Token usage and cost: only populated when a live model run returns usage metadata.

## Observability

FastAPI emits structured JSON logs with request ID, route, HTTP status, duration, selected tools, graph stages, conversation ID, and provider/LLM statuses. API keys, prompts containing secrets, and hidden chain-of-thought are never logged. `/api/evaluation/latest` exposes the last stored benchmark to the frontend.

## Reliability

Provider clients use 12-second timeouts and bounded exponential backoff for timeouts, network errors, 408, 425, 429, and 5xx responses. Non-retryable 4xx responses are returned immediately. Validation and explicit unavailable states prevent unsupported provider data from entering synthesis.

## Limitations

The included benchmark is deterministic routing evaluation, not a claim that live provider calls or OpenAI responses succeed. Run a separately configured live evaluation before comparing model quality. The current local persistence layer remains SQLite; use a PostgreSQL adapter and external log sink for multi-instance deployment.
