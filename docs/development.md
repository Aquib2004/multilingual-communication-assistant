# Development Guide

## Requirements

| Tool | Version |
| --- | --- |
| Python | 3.11+ (developed on 3.11 / 3.12) |
| Node.js | 18+ (developed on 20 LTS) |
| Docker | optional, for the full PostgreSQL stack |
| `uv` | optional, faster installs |

## Repository layout

```
backend/    FastAPI service
frontend/   React SPA
docs/       architecture, api, verification, deployment
examples/   fictional demo fixtures
```

## Backend

```bash
cd backend
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Or with `uv`:

```bash
uv venv && uv pip install -r requirements.txt
uv run uvicorn app.main:app --reload
```

### Database

Default: SQLite at `./app.db` — no server needed.

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./app.db
```

PostgreSQL:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/multilingual_assistant
```

```bash
alembic upgrade head                       # apply migrations
alembic revision --autogenerate -m "msg"   # after changing models
alembic downgrade -1                       # roll back
```

### Running tests

```bash
pytest                          # all
pytest tests/test_verification.py -v
pytest -k "date_mismatch"        # by name
pytest --cov=app --cov-report=term-missing
```

The suite runs entirely on the mock provider and SQLite. **No API key, no
network, no database server.** If a test needs an API key it is a bug in the
test.

### Quality gates

```bash
ruff check app tests      # lint
ruff check --fix app tests
black app tests           # format
black --check app tests   # format check (CI)
mypy app                  # type check
```

Ruff and Black are configured in `backend/pyproject.toml`; mypy runs in strict
mode over `app/`.

### Adding a language

1. Add an entry to `LANGUAGES` in `app/core/languages.py`.
2. Add glossaries to the mock provider's term tables if you want offline
   translation quality for it.
3. Nothing else. The API, the verification engine, and the UI read the registry.

## Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
npm run build          # type-checked production build
npm run test           # vitest
npm run test:watch
npm run lint
npm run typecheck
npm run format
```

The API base URL comes from `VITE_API_BASE_URL` (default
`http://localhost:8000/api`).

### Adding a component

- Keep it presentational. Fetching and mutations belong in `hooks/`.
- Shared API response types live in `src/types/index.ts` — mirror the Pydantic
  schemas; do not re-declare them inline.
- Every new component needs a test if it has behaviour.

## Working on prompts

Prompts live in `app/ai/prompts/*.py` as template strings with
`{placeholders}`. They are not inlined in service functions.

Rules for every prompt:

1. Require a JSON object matching a Pydantic model.
2. State explicitly: *do not invent information; if uncertain, say so.*
3. State explicitly: *never claim a translation is certified or accurate.*
4. State the risk level and, for high-risk content, instruct the model to
   recommend escalation rather than produce a final answer.
5. Pass the protected items and their placeholders into the prompt.

## Adding an AI provider

```python
# app/ai/providers/my_provider.py
class MyProvider(AIProvider):
    name = "my-provider"
    async def complete_structured(self, request: AIRequest) -> dict[str, Any]: ...
```

Register it in `app/ai/factory.py`, add its settings to `app/core/config.py`,
and document the environment variables in `.env.example`. Services must not
change.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `AIProviderAuthError` on start | `AI_PROVIDER=openai` without a key | Set `AI_PROVIDER=mock` or add the key |
| `DATABASE_ERROR` | Postgres unreachable | Use the SQLite URL, or start the container |
| `AIInvalidOutputError` | Model returned non-JSON / wrong shape | Check the prompt and the model; the request fails closed by design |
| Frontend `ERR_CONNECTION_REFUSED` | Backend not running | Start `uvicorn` on port 8000 |
| CORS error in the browser | Origin not in `CORS_ORIGINS` | Add it and restart |
