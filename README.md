# ARC / Intel — Crypto Intelligence Agent

An evidence-first crypto market analyst built with FastAPI, LangGraph, SQLite, and Next.js. It retrieves live market/news data when credentials are present, persists conversations, and clearly reports provider outages without inventing prices or citations.

## Run locally

```powershell
Copy-Item .env.example .env
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. API docs are at `http://localhost:8000/docs`.

## Tests

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
pytest
```

## Configuration

Set `FREECRYPTOAPI_API_KEY` and `NEWSAPI_API_KEY` for live retrieval. Ollama/Qwen3 is the local default; set `LLM_PROVIDER=gemini` with `GEMINI_API_KEY` for Gemini, or `LLM_PROVIDER=openai` with `OPENAI_API_KEY` for the implemented OpenAI compatibility provider. Never commit `.env`. The tracked `.env.example` is a general template, `.env.local.example` is the Ollama/SQLite development template, and `.env.production.example` documents the Gemini/PostgreSQL deployment shape with placeholders only.

## Delivery status

Implemented: modular provider clients, compiled LangGraph input/routing/execution/validation/evidence/LLM-synthesis workflow, mixed market/news routing, provider-independent structured output, SQLite conversation memory, REST API, responsive dashboard/chat/evidence UI, Docker assets, tests, and architecture documentation. If the configured provider is unavailable or the model request fails, the agent returns a clearly labelled unavailable response rather than a fabricated analysis. PostgreSQL deployment should use a production repository adapter.

Phase 3 adds a 20-case deterministic evaluation benchmark, metric calculations, JSON reports at `backend/evaluation/results/latest.json`, structured request/agent logs, request IDs, bounded retry/backoff for transient provider errors, and an evaluation summary card in the frontend. See [docs/evaluation.md](docs/evaluation.md).

The hybrid runtime now supports Ollama/Qwen3 for local development and Gemini for cloud deployment through `LLM_PROVIDER`, while preserving OpenAI compatibility. Persistence uses SQLAlchemy for both SQLite and PostgreSQL URLs, with Alembic migrations. See [docs/hybrid-architecture.md](docs/hybrid-architecture.md), [.env.local.example](.env.local.example), and [.env.production.example](.env.production.example).

## Release validation

The verified local path uses Ollama/Qwen3 and SQLite. Run `python scripts/live_validate.py --provider ollama --e2e` for a real model-backed graph check, `python scripts/http_persistence_validate.py` for a real backend restart check, and `cd frontend; npm run e2e` for browser tests against running services. See [docs/testing.md](docs/testing.md).

External market/news intelligence is only live when `FREECRYPTOAPI_API_KEY` and `NEWSAPI_API_KEY` are configured. Empty keys produce explicit unavailable states; prices and articles are never substituted.

Phase 9 live validation confirmed authenticated BTC/ETH market retrieval and Bitcoin/Ethereum news retrieval with sanitized reports in `backend/evaluation/results/phase9_live.json`. See [docs/testing.md](docs/testing.md) for the exact live/mocked/inconclusive classification.

Phase 10 adds bounded, relevance-ranked news evidence selection, valid JSON context budgeting, and configurable provider timeouts. The Phase 10 report is in [docs/testing.md](docs/testing.md); it does not claim news synthesis or browser-chat success when Ollama is unavailable.

Phase 11 local-model benchmarking was not run because Ollama was unreachable during validation. The configured default remains `qwen3:8b`; see [docs/testing.md](docs/testing.md) for the measured Phase 9 baseline and exact benchmark prerequisites.

The Phase 11 resume attempt also found the Ollama port already bound but inaccessible to this environment. No benchmark or model recommendation was fabricated; see `backend/evaluation/results/phase11_resume.json`.

The second resume attempt confirmed from the supplied host log that Ollama discovered CUDA on an RTX 3050 6GB GPU, but API/model inventory requests still timed out. Benchmarking remains pending a reachable Ollama API; see `backend/evaluation/results/phase11_resume_attempt2.json`.

Use `python scripts/phase11_benchmark.py` from the native Ollama-reachable PowerShell context for the comparative qwen3/phi3 benchmark. Results are written to `backend/evaluation/results/phase11_benchmark.json`.

Phase 12 adds a focused NewsAPI-to-evidence-to-Ollama citation audit. Run `python scripts/phase12_news_validation.py --query "Latest Bitcoin news"` in the native provider-reachable context; it writes a sanitized report under `backend/evaluation/results/`.

Phase 13 adds sequential multi-scenario integration validation through `scripts/phase13_integration.py`. It is currently partially validated: Phase 12 Bitcoin news synthesis passed live, while the remaining native scenarios require execution from the Ollama-reachable PowerShell context.

Phase 13.1 repairs strict citation integrity and explicit empty-news handling. Run `python scripts/phase13_1_validation.py` natively to validate the repaired BTC/ETH news, market-only, combined, and follow-up paths.

Phase 13.2 repairs combined market/news query construction and adds a sequential reliability runner at `scripts/phase13_2_validation.py`. Native validation is LIVE PASSED for BTC/ETH news-only, market-only, combined market/news, and an Ethereum follow-up; the sanitized report is `backend/evaluation/results/phase13_2_report.json`.

Phase 14 release audit results are recorded in [docs/release-audit.md](docs/release-audit.md) and `backend/evaluation/results/phase14_release_audit.json`. The current recommendation is RELEASE CANDIDATE: backend, persistence, deterministic evaluation, Phase 13.2 live evidence, and frontend build passed, while browser E2E remains inconclusive in this runner environment.

Phase 15 resolved the browser-runner lifecycle issue with a synchronized local startup. The existing Playwright suite now passes 3/3 against live local FastAPI and Next.js processes, including dashboard load, real chat submission, and browser follow-up. See [docs/github-publication-audit.md](docs/github-publication-audit.md) and `backend/evaluation/results/phase15_github_readiness.json`.

Historical evaluation reports use phase-specific schemas. Interpret each report's LIVE, MOCKED, NOT RUN, or INCONCLUSIVE classification within its own phase; earlier report formats are intentionally preserved.
