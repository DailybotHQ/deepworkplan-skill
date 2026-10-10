# Preset — FastAPI (Python)

> Reasoning aid, not a template. Verify every assumption against the live repo;
> detected reality wins. Capture the **real** validation command, not the
> example below.

## Signals that identify this stack

- `fastapi` in `pyproject.toml` / `requirements.txt`, plus an ASGI server:
  `uvicorn`, or `gunicorn` with `uvicorn.workers.UvicornWorker`.
- An application factory or module-level instance: `app = FastAPI(...)`, often
  in `app/main.py` / `main.py` / `src/<pkg>/main.py`.
- `APIRouter` modules wired in via `app.include_router(...)`, `async def` (and
  some `def`) path operations decorated with `@router.get/post/...`.
- Pydantic models for request/response schemas (Pydantic v1 vs v2 matters), and
  `pydantic-settings`/`BaseSettings` for configuration.
- Dependency injection via `Depends(...)`; common deps for DB sessions, auth,
  and pagination.
- Package manager from the lockfile: `poetry.lock` → Poetry, `uv.lock` → uv,
  `Pipfile.lock` → Pipenv, bare `requirements.txt` → pip/venv. **Infer from the
  lockfile present.**
- Frequently paired with SQLAlchemy + Alembic (`alembic.ini`, `migrations/` or
  `alembic/`), or an async ORM (SQLModel, Tortoise). Often containerized
  (`Dockerfile`, `docker-compose.yml`).

## What to look for in recon

- The **real** test runner: almost always `pytest` (`pytest.ini` /
  `pyproject [tool.pytest.ini_options]`), driving endpoints through Starlette's
  `TestClient` or async `httpx.AsyncClient` with `ASGITransport`. Confirm the
  test layout (`tests/`, `test_*.py`) and any `conftest.py` fixtures.
- The **real** lint/format/typecheck gate: `ruff` (lint + format), `black`,
  `isort`, `mypy`/`pyright` — and whether it's wrapped in a Makefile/script and
  whether it **runs inside Docker** (flag it if so).
- The Pydantic major version (v1 vs v2) — it changes validators, config, and
  serialization patterns the generated skills must follow.
- Sync vs async surface: blocking I/O inside `async def` handlers is a hazard;
  note the DB driver (async vs sync) and the event-loop discipline.
- Router composition (`include_router`, prefixes, tags), the settings/secrets
  layout (`.env`, `BaseSettings`), and the run command (`uvicorn app.main:app`).
- Migration workflow if Alembic is present (`alembic revision --autogenerate`,
  `alembic upgrade head`) and whether it runs in the container.

## Stack-specific skills/agents/commands to generate

- Skills: `router-add` (an `APIRouter` module + handlers + `include_router`
  wiring), `schema` (Pydantic request/response models), `dependency` (a
  `Depends` provider — auth, DB session, pagination), `endpoint` (path operation
  + schema + test), optionally `migration` (Alembic revision) if SQLAlchemy is
  present.
- Agents: baseline roles + an `api-reviewer` / `schema-author` persona aware of
  Pydantic validation, response models, and async/blocking hazards.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — app assembly (`include_router`), request → dependency →
  handler → response-model flow, async vs sync boundaries, DB/session lifecycle.
- `TESTING_GUIDE.md` — `pytest` + `TestClient`/`httpx`, async fixtures, how to
  override dependencies (`app.dependency_overrides`) and scope one router's
  tests.
- `SECURITY.md` — auth scheme (OAuth2/JWT, API keys), `BaseSettings`/secrets
  handling, input validation via Pydantic, CORS.
- Per-module docs: one per router/feature (its schemas, dependencies,
  endpoints).

## Typical validation command (FIND the real one)

Often `ruff check && mypy && pytest`, or a wrapped/Dockerized gate (e.g. `make
check`, or commands run *inside* the container). **Do not assume** the package
manager or script names — read the Makefile/`pyproject.toml`/CI and capture the
exact command, flagging that it runs inside Docker if so.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; the target repo's version may differ, so re-verify. Items marked
*documented example* were **not** run here — confirm the exit code and the
selection count in the target repo before trusting them in a gate.

### 1. Full commands
- Tests: `pytest` (async via `pytest-asyncio`/`anyio`; endpoints through `TestClient` or `httpx.AsyncClient`), from the project root — or via the wrapped `make test` / Docker gate the repo defines.
- Static: `ruff check .` (+ `ruff format --check .`), `mypy <package>` or `pyright`, optionally `python -c 'import app.main'` as an import smoke.

### 2. Scoped invocation
**pytest** (reference run — pytest 9.1.1, contributor environment): `pytest tests/unit/test_orders.py` (file), `pytest tests/unit/test_orders.py::TestOrders::test_total` (node id), `pytest tests/unit/orders/` (directory), `pytest -k "orders and not slow"` (name expression), `pytest -m integration` (marker). `pytest --co -q <selection>` lists what *would* run — the cheapest evidence of a non-empty, relevant selection; record its count. **Zero-selection behavior (verified):** nothing collected (a `-k`/`-m` that matches nothing) exits **5** (`no tests ran`); a nonexistent path exits **4** (usage error) — both detectable, never a silent pass. Impact selection: `pytest --testmon` (plugin `pytest-testmon`, tracks coverage-based dependencies) or `pytest --lf` (last failed); both need a warm cache and have the blind spots below.

### 3. Scoped static checks
- **ruff** (documented example): `ruff check <path>` and `ruff format --check <path>` scope natively to files/directories.
- **mypy** (documented example): `mypy <package>` runs on a subset but can miss errors that only surface with the whole program; prefer `mypy <top-level package>` (project-wide) as the real check and say so. **pyright** likewise.
- **black/isort** (`--check <path>`) scope natively.

### 4. Source-to-test mapping
`tests/` mirroring `app/` (`tests/api/test_orders.py` ↔ `app/api/routes/orders.py`, `tests/services/…` ↔ `app/services/…`), or co-located `*_test.py`; router tests exercise `app/api/routes/*` through the app instance.

### 5. Affected consumers
`pytest --testmon` where installed; otherwise imports plus the dependency-injection graph (`Depends(...)`). **Blind spots:** dependency overrides in `conftest.py`, app-level middleware and exception handlers registered in `main.py`, router inclusion (`include_router`), Pydantic settings from `.env*`, background tasks, Alembic migrations, ORM models shared by many routers. A change to a shared dependency (`get_db`, `get_current_user`) or middleware affects every route ⇒ the full run.

### 6. Escalation and fallback
Shared/core: `app/core/`, `app/deps.py`/`dependencies.py`, `app/db/`, `app/models/`, shared schemas, `main.py`, `conftest.py`. Always full run: `pyproject.toml`/`requirements*`/lockfile, `alembic/`, `pytest.ini`, `.env*`, `Dockerfile`/compose when tests run in Docker. **Fallback:** `ruff check . && mypy <pkg> && pytest` (or the repo's `make test`).

### 7. Layers and posture
Unit (pytest, no app, no DB) for services, schemas, utils — fast base; router tests through `TestClient` with dependency overrides as the integration layer for the HTTP seam; DB-backed tests only where persistence is the behavior under test; few e2e. Unit-first; no ratio quota.

### 8. Zero-selection behavior
pytest exits **5** on nothing collected and **4** on a bad path (verified). An async test that is silently skipped because no async plugin is configured shows as `SKIPPED`/`s` in the summary — count passes, not the exit code alone.
