# Phase 15 — GitHub Publication Readiness Audit

## Verdict

**READY WITH DOCUMENTED LIMITATIONS**

The repository is ready for a user-reviewed initial GitHub commit. No Git staging, commit, push, deployment, or remote repository operation was performed. Core functionality, live local browser behavior, regression checks, persistence, and repository secret protection are validated.

## Current validation

| Check | Classification | Result |
|---|---|---|
| Playwright dashboard | LIVE PASSED | 1/1 |
| Playwright real chat | LIVE PASSED | 1/1 |
| Playwright browser follow-up | LIVE PASSED | 1/1 |
| Browser suite | LIVE PASSED | 3/3, 1.2 minutes |
| Backend regression | MOCKED PASSED | 23 passed, 1 deprecation warning |
| Deterministic evaluation | MOCKED PASSED | 20/20 |
| Frontend build | PASSED | `npm run build` |
| TypeScript | PASSED | `npx tsc --noEmit` |
| HTTP repository restart | LIVE PASSED | 4 messages recovered in prior Phase 14 run |
| SQLite checkpoint adapter | MOCKED PASSED | automated round-trip |
| Phase 13.2 live integration | LIVE PASSED | historical 7/7; preserved unchanged |
| ESLint | NOT RUN | no lint script or dependency |
| PostgreSQL/cloud deployment | NOT RUN | outside this phase |

## Browser execution details

The previous `ERR_CONNECTION_REFUSED/TIMED_OUT` result was caused by the tool runner terminating detached services between commands. Phase 15 started backend and frontend together, waited for `/health` and `/` to return HTTP 200, ran Playwright in the same controlled process, and stopped only the processes created for that run.

The follow-up test initially exposed a timing race: it counted two analyst labels immediately after the user message appeared. The test now waits up to the existing 110-second request budget for the second analyst response. It does not weaken the expected count or mock the API.

## Repository integrity

- No Git commits currently exist.
- No `git add`, `git commit`, `git push`, deployment, or remote repository action was performed.
- `.env` is ignored and was not modified.
- SQLite databases, `.next`, `node_modules`, Python caches, and Playwright artifacts are ignored.
- Public environment examples contain placeholders only.
- No known credential patterns were found outside the ignored `.env`.
- The workspace contains no tracked-file baseline yet; review all untracked files before the first commit.

Credential-shaped values were previously present in example files and were replaced with placeholders in Phase 14. If those values were ever real or published, rotate the affected provider credentials before publication.

## Documentation and reproducibility

README, architecture, testing, hybrid-architecture, release-audit, and this publication audit document local setup, provider configuration, evidence/citation behavior, test commands, and known limitations. Historical live results remain identified by phase and are not represented as new executions.

## Remaining limitations and prerequisites

- ESLint is not configured.
- PostgreSQL/cloud deployment remains unvalidated.
- HTTP restart validates application conversation persistence; checkpoint persistence remains a separate SQLite adapter test.
- The comparative local-model benchmark is not a complete basis for changing the qwen3:8b default.
- Before publication, manually review the initial file set and run the secret scan below.

## Manual commands before the first commit

```powershell
git status --short
git status --ignored --short
git check-ignore -v .env .env.local .env.production *.db frontend/node_modules frontend/.next frontend/test-results
Get-ChildItem -LiteralPath . -File -Recurse -Force | Where-Object { $excluded = @('.git','node_modules','.next','__pycache__','.pytest_cache','.mypy_cache','.venv','venv','.cache','coverage','test-results'); $_.Name -ne '.env' -and -not ($_.FullName.Split([IO.Path]::DirectorySeparatorChar) | Where-Object { $_ -in $excluded }) } | Select-String -Pattern '(?i)(AIza[0-9A-Za-z_-]{20,}|(?:sk|pk|rk)-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|(?:OPENAI|GEMINI|FREECRYPTOAPI|NEWSAPI)_API_KEY\s*=\s*(?!replace-with|your-|<|$)[^\s]+)' | ForEach-Object { '{0}:{1}' -f $_.Path, $_.LineNumber }
```

After review, the user—not this agent—can stage and commit the intended files.
