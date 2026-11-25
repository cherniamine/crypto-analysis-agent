# Security checklist

- [x] Provider and OpenAI keys are read only on the backend.
- [x] `.env` and database files are ignored by Git.
- [x] Frontend configuration exposes only `NEXT_PUBLIC_API_URL`.
- [x] Pydantic limits chat input to 4,000 characters.
- [x] Provider timeouts and bounded retries are enabled.
- [x] Structured logs contain request IDs and operational metadata, not keys or hidden reasoning.
- [x] API responses do not return environment variables or credentials.
- [x] CORS is configurable through `CORS_ORIGINS`.
- [ ] Add authentication and per-user authorization before public multi-user deployment.
- [ ] Use managed PostgreSQL and an external secret manager for production.
- [ ] Add a reverse proxy/WAF and rate limiting at the deployment edge.
