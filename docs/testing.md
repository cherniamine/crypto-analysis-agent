# Testing and release validation

## Automated checks

From the repository root:

```powershell
cd backend
$env:PYTHONPATH=(Get-Location).Path
pytest
python -m app.evaluation.runner
cd ..\frontend
npm run build
```

The deterministic benchmark is 20 routing scenarios. It does not claim live provider or LLM quality. The backend suite covers graph routing, structured analysis, metrics, reliability, repository behavior, provider configuration, and SQLite checkpoint round trips.

## Live Ollama validation

With Ollama serving `qwen3:8b`:

```powershell
python scripts/live_validate.py --provider ollama
python scripts/live_validate.py --provider ollama --e2e
```

FreeCryptoAPI and NewsAPI checks execute only when their keys are configured. A missing key is reported as `not_run`.

## HTTP restart persistence

This uses a temporary SQLite database, starts the real Uvicorn application, sends two messages in one thread, stops the server, restarts it, and retrieves the same conversation:

```powershell
python scripts/http_persistence_validate.py
```

This validates application repository persistence. LangGraph checkpoint persistence is a separate adapter and is tested independently by `test_checkpoint_persistence.py`.

## Browser E2E

Install the minimal browser test dependency and Chromium once:

```powershell
cd frontend
npm install
npx playwright install chromium
```

Start the real backend and frontend, then run:

```powershell
npm run e2e
```

These tests do not mock API calls. They use the running application and therefore require Ollama for chat tests. Provider-unavailable states are asserted where the real backend reports them.

## Release classification

Reports must distinguish `LIVE PASSED`, `MOCKED PASSED`, `NOT RUN`, and `FAILED`. No market/news result is considered live unless the corresponding provider key was present and the real endpoint returned validated records.

## Current Phase 8 result snapshot

- LIVE PASSED: Ollama/Qwen3 structured provider check and complete single-request LangGraph E2E.
- LIVE PASSED: Playwright dashboard load and chat submission after fixing local CORS/host compatibility.
- MOCKED PASSED: SQLAlchemy repository, SQLite checkpoint adapter, provider switching, and deterministic evaluation.
- NOT RUN: FreeCryptoAPI and NewsAPI because the current `.env` keys are empty; Gemini/OpenAI/PostgreSQL because they are not configured.
- INCONCLUSIVE: the two-message browser follow-up and the HTTP restart harness did not emit a complete final summary within the local runner window; do not treat them as release evidence.

## Phase 9 live integration snapshot

- LIVE PASSED: FreeCryptoAPI authenticated BTC/ETH retrieval; 2 normalized records, retrieval timestamp present, approximately 1.16 seconds for the two single-symbol requests.
- LIVE PASSED: NewsAPI Bitcoin query; 8 validated unique articles, approximately 0.47 seconds.
- LIVE PASSED: NewsAPI Ethereum query; 8 validated unique articles, approximately 0.40 seconds.
- LIVE PASSED: Ollama Bitcoin market LangGraph scenario; 2 market evidence records, all graph stages complete, approximately 24.9 seconds.
- LIVE PASSED: Ollama Ethereum market LangGraph scenario; 2 market evidence records, all graph stages complete, approximately 25.0 seconds.
- LIVE PASSED: Live dashboard browser load.
- NOT RUN/INCONCLUSIVE: News-heavy Ollama synthesis and live browser chat with external evidence exceeded the local runner window; no success is claimed for those cases.

## Phase 10 performance and live E2E snapshot

- IMPLEMENTED: bounded evidence context. News evidence is ranked against the question, capped by `NEWS_EVIDENCE_LIMIT` (default 5), and records `available_news`, `selected_news`, and `dropped_news` in graph activity. The model packet has an `EVIDENCE_CONTEXT_CHAR_BUDGET` (default 18,000) and remains valid JSON if trimming is required.
- IMPLEMENTED: explicit LLM timeout configuration through `LLM_TIMEOUT_SECONDS` (default 60 seconds) for Ollama, Gemini, and OpenAI.
- MOCKED PASSED: evidence-selection behavior selected 5 of 6 synthetic records by relevance and preserved source metadata; oversized packets remained valid JSON. This is not a live provider result.
- LIVE PASSED (historical Phase 9 evidence): FreeCryptoAPI BTC/ETH retrieval, NewsAPI Bitcoin/Ethereum retrieval, and Ollama BTC/ETH market graphs. The Phase 10 code changes preserve the 11-test backend suite and 20/20 deterministic benchmark.
- NOT RUN: current Phase 10 Ollama reruns because `127.0.0.1:11434` was unreachable during validation. The earlier Phase 9 Ollama timings remain the valid live baseline: BTC approximately 24.9 seconds and ETH approximately 25.0 seconds.
- INCONCLUSIVE: current news-agent and comparison attempts did not emit a completed graph result before the local runner window; no news synthesis pass is claimed. The live NewsAPI provider checks from Phase 9 remain valid (8 unique Bitcoin articles and 8 unique Ethereum articles).
- LIVE PASSED: `npm run build` completed after the optimization. Browser chat with live Ollama/news evidence was not reclassified as passed while Ollama was unavailable.
- NOT RUN/INCONCLUSIVE: the HTTP stop/restart harness did not produce a complete Phase 10 summary in this environment; repository and SQLite checkpoint adapter tests remain covered by the automated suite.

The measured bottleneck is model/runtime availability for article-heavy synthesis, not the provider retrieval path: Phase 9 NewsAPI requests completed in roughly 0.40–0.47 seconds, while Ollama market graph runs completed in roughly 24.9–25.0 seconds. Current application logs do not expose article contents or credentials.

Reproduce the targeted checks:

```powershell
python scripts/phase9_live_validation.py
cd backend
$env:PYTHONPATH=(Get-Location).Path
python -m pytest -q tests
python -m app.evaluation.runner
cd ..\frontend
npm run build
npm run e2e
```

## Phase 11 local-model benchmark snapshot

Environment inspection on 2026-11-24:

- NOT RUN: Ollama was unreachable at `127.0.0.1:11434`; therefore no qwen3:8b, qwen3:4b, or phi3:mini inference was executed in Phase 11.
- NOT RUN: installed-model inventory was unavailable because the Ollama service was not running.
- NOT RUN: GPU/VRAM inventory was unavailable; `nvidia-smi` was not installed or available to this process, and Windows CIM hardware queries were restricted.
- CONFIGURED: `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=qwen3:8b`, `OLLAMA_BASE_URL=http://localhost:11434`, `LLM_TIMEOUT_SECONDS=60`.
- CONFIGURED: `NEWS_EVIDENCE_LIMIT=5` and `EVIDENCE_CONTEXT_CHAR_BUDGET=18000` through application defaults. No explicit Ollama `num_ctx` setting is currently configured.
- LIVE BASELINE: the previous Phase 9 qwen3:8b market runs remain the only valid local-model benchmark: BTC approximately 24.9 seconds and ETH approximately 25.0 seconds, both with structured output and two market evidence records.
- NOT RUN: direct structured inference, news synthesis, comparison, follow-up, browser chat, and HTTP restart validation could not be newly completed without a reachable Ollama service.
- PASSED: backend regression remains 11 tests passed; deterministic routing remains 20/20; frontend production build passed.

No default model was changed. A recommendation among qwen3:8b, qwen3:4b, and phi3:mini requires actual model availability and repeated measurements on the target hardware; the current evidence is insufficient to recommend a smaller model.

### Phase 11 resume attempt 2

The user-provided Ollama server log confirms a successful host startup, CUDA discovery, and an NVIDIA GeForce RTX 3050 6GB Laptop GPU with approximately 5.9 GiB available VRAM. Ollama selected a 4096-token default context. However, the validation process could not query the service afterward: `/api/tags`, `ollama list`, and `ollama ps` timed out, while a second `ollama serve` reported port 11434 already bound. Therefore model inventory and all inference benchmarks remain **NOT RUN**. The sanitized record is `backend/evaluation/results/phase11_resume_attempt2.json`.

### Phase 11 resume attempt

- NOT RUN: `ollama list` and the Ollama HTTP API were inaccessible during the resume attempt.
- NOT RUN: `ollama serve` could not be started because port `127.0.0.1:11434` reported as already bound, while requests to that port remained denied.
- NOT RUN: qwen3:8b, qwen3:4b, and phi3:mini comparison benchmarks.
- NOT RUN: direct inference, structured-output checks, news synthesis, comparison, follow-up, browser chat, and HTTP restart validation.
- PRESERVED: no model, provider, evidence limit, context budget, or timeout defaults were changed.
- REPORT: sanitized result stored in `backend/evaluation/results/phase11_resume.json`.

When Ollama is available, reproduce the benchmark baseline with:

```powershell
ollama serve
ollama list
ollama run qwen3:8b
python scripts/live_validate.py --provider ollama --e2e
python scripts/phase9_live_validation.py --only btc_market
python scripts/phase9_live_validation.py --only eth_market
python scripts/phase9_live_validation.py --only btc_news
python scripts/phase9_live_validation.py --only eth_news
python scripts/phase9_live_validation.py --only compare
python scripts/phase9_live_validation.py --only follow_up
```

Run smaller-model comparisons only after confirming they appear in `ollama list`; do not silently alter `.env` or the application default.

The reproducible comparative runner is:

```powershell
$env:PYTHONPATH = (Get-Location).Path + '\backend'
python scripts/phase11_benchmark.py
```

It inventories Ollama first, skips models that are not installed, runs three direct structured-inference repetitions and one repetition of each graph scenario per available model, and writes sanitized metrics to `backend/evaluation/results/phase11_benchmark.json`. It does not write `.env` or change the production model.

## Phase 12 news evidence and citation audit

Phase 11 exposed an integrity gap: graph completion did not prove that NewsAPI articles reached the model. The audit found that citation validation compared bracketed tokens such as `[news:1]` with unbracketed evidence IDs, causing valid citations to be marked invalid. The news path also lacked separate telemetry for API articles, normalized articles, created evidence, selected evidence, and evidence included in the LLM packet.

Phase 12 repairs and tests:

- MOCKED PASSED: 16 backend tests, including NewsAPI normalization, metadata preservation, deduplication, empty responses, market/news merge, deterministic selection, context budgeting, citation validation, malformed URLs, and telemetry.
- LIVE NOT RUN: focused native validation must be executed with `python scripts/phase12_news_validation.py --query "Latest Bitcoin news"` from the Ollama/credential-reachable PowerShell context.
- LIVE synthesis is not claimed from NewsAPI retrieval alone. The focused report requires nonzero news evidence, completed Ollama synthesis, valid citations, and URLs on cited news records.

The sanitized Phase 12 report is `backend/evaluation/results/phase12_report.json`; a native live run writes `backend/evaluation/results/phase12_news_live.json`.

## Phase 13 multi-scenario integration validation

The Phase 13 runner is `scripts/phase13_integration.py`. It executes sequentially:

- News-only Bitcoin and Ethereum.
- Market-only Bitcoin and Ethereum.
- Combined Bitcoin market/news analysis.
- A real follow-up using the first graph response as conversation history.

Run it from native PowerShell where the configured providers and Ollama are reachable:

```powershell
$env:PYTHONPATH=(Get-Location).Path + '\backend'
python scripts/phase13_integration.py
```

It writes `backend/evaluation/results/phase13_integration.json` and records tool statuses, graph stages, evidence counts by type, context inclusion, citation validation, URL attribution, and durations. The current repository-side result is **PARTIALLY VALIDATED**: the Phase 12 Bitcoin news-only scenario is LIVE PASSED, while the remaining Phase 13 live scenarios are NOT RUN from the restricted sandbox. Backend tests are 16 passed and deterministic evaluation is 20/20.

## Phase 13.1 citation integrity and empty retrieval repair

Phase 13 exposed hallucinated `news:0` references in market-only answers, non-strict ETH news citation acceptance, successful-but-empty combined news retrieval, and invalid follow-up citations. Phase 13.1 repairs strict current-context citation validation, namespace and URL checks, required structured news citations, explicit empty/normalized-empty provider statuses, and safe reporting/removal of invalid citation tokens.

- MOCKED PASSED: 19 backend tests.
- MOCKED PASSED: deterministic evaluation 20/20.
- LIVE NOT RUN: the repaired native runner is `scripts/phase13_1_validation.py`.

Run natively:

```powershell
$env:PYTHONPATH=(Get-Location).Path + '\backend'
python scripts/phase13_1_validation.py
```

The runner writes `backend/evaluation/results/phase13_1_report.json` and requires structured citations tied to current evidence. Raw URLs alone do not pass.

## Phase 13.2 combined market/news reliability

Phase 13.1 showed standalone BTC/ETH news retrieval passing while combined retrieval returned zero news articles. Code tracing found that combined routing passed the entire long user question to NewsAPI; market and news state were not overwriting each other. Phase 13.2 now constructs an asset-focused provider query such as `Bitcoin cryptocurrency news`, while preserving the original question for ranking and synthesis.

- MOCKED PASSED: 23 backend tests, including combined graph-node execution, state preservation, query construction, empty/error distinction, evidence merge, and strict citations.
- MOCKED PASSED: deterministic evaluation 20/20.
- LIVE PASSED: native report `backend/evaluation/results/phase13_2_report.json` contains seven passed scenarios: BTC/ETH news-only, BTC/ETH market-only, BTC/ETH combined market/news, and an Ethereum follow-up using prior graph context. Combined scenarios each retained 2 market records and 5 selected news evidence records with valid citations.

```powershell
$env:PYTHONPATH=(Get-Location).Path + '\backend'
python scripts/phase13_2_validation.py
```

The runner writes `backend/evaluation/results/phase13_2_report.json`. Combined scenarios only pass when both market and news evidence reach the LLM context and strict citation validation succeeds.

## Phase 15 stable browser and GitHub readiness validation

Phase 15 used synchronized persistent local processes on alternate ports, waited for both readiness endpoints, and then ran the existing browser suite without API mocks:

- LIVE PASSED: Playwright 3/3 — dashboard load, real chat submission, and same-browser follow-up.
- LIVE PASSED: backend health and frontend HTTP readiness before Playwright.
- MOCKED PASSED: backend regression 23 tests, deterministic evaluation 20/20, SQLite checkpoint round-trip.
- PASSED: frontend production build and TypeScript validation.
- NOT RUN: ESLint, because no lint script or ESLint dependency exists.

The follow-up test was corrected to wait for the second assistant response before counting rendered analyst messages; the assertion itself remains unchanged. The full publication audit is in `docs/github-publication-audit.md` and `backend/evaluation/results/phase15_github_readiness.json`.

## Phase 14 final release audit

The release audit is documented in `docs/release-audit.md` and the sanitized machine-readable report `backend/evaluation/results/phase14_release_audit.json`.

Historical evaluation reports intentionally use phase-specific schemas. Interpret LIVE, MOCKED, NOT RUN, and INCONCLUSIVE classifications within each report's phase; older reports are preserved unchanged.

- MOCKED PASSED: backend regression, 23 tests; deterministic evaluation, 20/20; Python compilation; frontend TypeScript check; frontend production build.
- LIVE PASSED: Phase 13.2 report integrity; HTTP SQLite conversation restart validation with two messages and a same-thread follow-up; SQLite checkpoint round-trip is covered by the backend suite.
- INCONCLUSIVE: the three Playwright tests were attempted against local services but ended with `ERR_CONNECTION_TIMED_OUT` after the temporary frontend process exited. No browser chat success is claimed from this attempt.
- NOT RUN: ESLint, because the frontend has no `lint` script or ESLint dependency; PostgreSQL/cloud deployment and a separate HTTP checkpoint recovery test were not executed in this audit.

Reproduce the core audit from PowerShell:

```powershell
$env:PYTHONPATH=(Get-Location).Path + '\backend'
python -m pytest -q backend/tests
python -m app.evaluation.runner
python scripts/http_persistence_validate.py
cd frontend
npm run build
npx tsc --noEmit
npx playwright test
```
