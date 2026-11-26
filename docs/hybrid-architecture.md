# Hybrid architecture

The application keeps one LangGraph workflow and swaps only infrastructure through environment variables.

| Environment | LLM | Database |
|---|---|---|
| Local | Ollama / Qwen3 | SQLite |
| Cloud | Gemini API | PostgreSQL via `psycopg` |

Set `LLM_PROVIDER=ollama` for local work or `LLM_PROVIDER=gemini` for cloud inference. The response node calls the same provider factory and preserves the same `AnalysisResponse` structured-output contract. OpenAI remains supported as a compatibility provider.

The application repository uses SQLAlchemy models and sessions for both database URLs. `alembic upgrade head` is the migration path; `create_all` remains a safe bootstrap for an empty local SQLite database. LangGraph checkpoint persistence is kept as a separate adapter concern from application conversation/message persistence; `app/agents/checkpoints.py` exposes SQLite and PostgreSQL adapters without changing the agent nodes.

## Local Ollama

```powershell
ollama serve
ollama pull qwen3:8b
Copy-Item .env.local.example .env
cd backend
pip install -r requirements.txt
$env:PYTHONPATH=(Get-Location).Path
uvicorn app.main:app --reload
```

## Gemini / PostgreSQL

Copy `.env.production.example` to the backend environment, set `GEMINI_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, and provider keys, then run `alembic -c alembic.ini upgrade head` from the repository root before starting Uvicorn. For Neon, use a `postgresql+psycopg://...?...sslmode=require` URL. Migrations are intentionally explicit rather than automatic at application startup. Gemini quota or authentication failures become explicit unavailable/error states; they never trigger fabricated analysis.

For release validation, keep `LLM_PROVIDER=ollama` locally and run browser tests against the actual FastAPI and Next.js processes. Use `LLM_PROVIDER=gemini` only where a Gemini key is configured; deployment configuration alone is not a deployment result.
