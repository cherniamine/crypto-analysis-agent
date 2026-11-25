# Phase 14 — Final Release Audit

## Executive summary

The application is a **RELEASE CANDIDATE** for a local GitHub portfolio release. The core backend regression suite, deterministic evaluation, SQLite persistence, frontend production build, and the saved native Phase 13.2 live report passed. Browser E2E was attempted but remains inconclusive because the temporary frontend process stopped before Playwright could connect consistently. This audit does not claim cloud deployment or production readiness.

## Verified capabilities

- Compiled LangGraph routing and evidence-based synthesis.
- Live Phase 13.2 validation: seven scenarios passed with Ollama/Qwen3, FreeCryptoAPI, and NewsAPI.
- Combined BTC and ETH scenarios retained both market and news evidence; strict citation validation passed.
- Follow-up scenario used actual prior graph context and fresh Ethereum market evidence.
- Backend regression: 23 tests passed.
- Deterministic evaluation: 20/20.
- Application conversation persistence survived a real backend stop/restart test.
- SQLite LangGraph checkpoint round-trip passed in the automated suite.
- Frontend TypeScript check and production build passed.

## Validation classification

| Area | Result | Evidence |
|---|---|---|
| Backend tests | MOCKED PASSED | `23 passed` |
| Deterministic evaluation | MOCKED PASSED | `20/20` |
| Phase 13.2 providers and graph | LIVE PASSED | `backend/evaluation/results/phase13_2_report.json`, 7/7 |
| HTTP repository restart | LIVE PASSED | 4 messages retrieved after restart; same thread retained |
| SQLite checkpoint adapter | MOCKED PASSED | `test_checkpoint_persistence.py` |
| Frontend production build | PASSED | `npm run build` |
| TypeScript | PASSED | `npx tsc --noEmit` |
| Browser E2E | INCONCLUSIVE | 3 attempted; `ERR_CONNECTION_TIMED_OUT` after local process exit |
| ESLint | NOT RUN | no `lint` script or ESLint dependency |
| PostgreSQL/cloud deployment | NOT RUN | no deployment performed |

## Security and configuration

The actual `.env` was not modified. It is ignored by `.gitignore`, and the public example files now contain placeholders only. A repository scan found no credential-shaped values outside the ignored `.env`. Provider keys remain backend-only; frontend configuration uses only the public API URL. CORS is configurable through `CORS_ORIGINS`.

The example files previously contained credential-shaped values. If those values were ever published or used as real credentials, rotate the affected provider keys before publishing. No keys are reproduced in this report.

The workspace currently has no Git commits (`master` has no commits), so GitHub readiness still requires a user-reviewed initial commit and secret scan before publishing.

## Persistence

`scripts/http_persistence_validate.py` started the real FastAPI process, submitted two messages in one conversation including a follow-up, stopped the backend, restarted it, and retrieved all four persisted messages. The script intentionally reports checkpoint persistence separately. The SQLite checkpoint adapter has an independent automated round-trip test. PostgreSQL persistence was not exercised in this audit.

## Known limitations

- Browser chat, source-link rendering, and browser follow-up remain unverified by a stable Playwright run.
- ESLint is unavailable because no lint configuration/script is present.
- PostgreSQL, Gemini/OpenAI cloud deployment, and production deployment were not performed.
- The local-model comparative benchmark remains historical/incomplete; qwen3:8b remains the configured default.
- The LangGraph checkpoint was not recovered through the HTTP restart harness itself.

## Recommendation

**RELEASE CANDIDATE.** The core local application is evidenced sufficiently for a portfolio candidate, with the browser E2E and cloud/PostgreSQL items explicitly outstanding. Before GitHub publication, rotate any previously exposed credentials, review the initial commit contents, run the Playwright suite with persistent backend/frontend processes, and confirm no `.env` or generated artifacts are staged.

Do not start Phase 15 or claim full production readiness from this audit alone.
