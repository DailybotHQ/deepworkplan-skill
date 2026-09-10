# Preset — Django / DRF (Python)

> Reasoning aid, not a template. Verify every assumption against the live repo;
> detected reality wins. Capture the **real** validation command, not the
> example below.

## Signals that identify this stack

- `manage.py` at the repo root and a `settings.py` (often under a project
  package or `config/`/`settings/` split into `base.py`/`local.py`/`prod.py`).
- `Django` in `pyproject.toml` / `requirements.txt`; DRF via `djangorestframework`.
- Package manager from the lockfile: `poetry.lock` → Poetry, `Pipfile.lock` →
  Pipenv, bare `requirements.txt` → pip/venv. **Infer from the lockfile present.**
- App layout: an `apps/` or top-level set of Django apps, each with
  `models.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py`, `migrations/`.
- Frequently containerized: look for `Dockerfile`, `docker-compose.yml`, a
  `docker.sh` helper, and Celery/Redis/Postgres services.

## What to look for in recon

- The **real** test runner: `pytest` (`pytest.ini`/`pyproject [tool.pytest]`) vs
  Django's `manage.py test`. Test file naming is commonly `*_test.py` or
  `tests/test_*.py` — confirm which.
- The **real** lint/format/typecheck gate: `ruff`, `flake8`, `black`, `isort`,
  `mypy` — and whether it's wrapped (e.g. a `codecheck` script) and whether it
  **runs inside a Docker container** (very common for Django here — flag it).
- Migration workflow (`makemigrations` / `migrate`), and whether migrations run
  in the container.
- Settings split and where **secrets** live (`.env`, a settings module, a vault).

## Stack-specific skills/agents/commands to generate

- Skills: `model-add` (add a model + migration), `migration` (make/apply
  migrations safely), `drf-endpoint` (serializer + viewset + URL), optionally
  `management-command` and `celery-task` if Celery is present.
- Agents: baseline roles + a `migration-author` / `db-reviewer` persona aware of
  migration safety.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — app boundaries, request → view → serializer → model flow,
  async/Celery, caching/Redis, DB.
- `TESTING_GUIDE.md` — pytest vs Django test runner, fixtures/factories, the real
  `*_test.py` pattern, how to scope a single app's tests.
- `SECURITY.md` — settings/secrets handling, auth model (sessions/JWT/DRF auth),
  PII boundaries.
- Per-module docs: one per Django **app** (its models, endpoints, signals,
  tasks).

## Typical validation command (FIND the real one)

Often a wrapped, **Dockerized** gate, e.g. `codecheck -f` run *inside* the
container (`bash docker.sh bash <service>`), or `poetry run ruff check && poetry
run pytest`. **Do not assume** — read the Makefile/`docker.sh`/CI and capture the
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
- Tests: `pytest` (with `pytest-django`, `DJANGO_SETTINGS_MODULE` from `pytest.ini`/`pyproject`) or `python manage.py test`; from the project root — or **inside the container** when the repo wraps it (`codecheck -f` via `docker.sh`): record the real cwd/container.
- Static: `ruff check .` (+ `ruff format --check .`), `mypy <project package>` (django-stubs), `python manage.py check`, `python manage.py makemigrations --check --dry-run`.

### 2. Scoped invocation
**pytest** (reference run — pytest 9.1.1, contributor environment): `pytest tests/unit/test_orders.py` (file), `pytest tests/unit/test_orders.py::TestOrders::test_total` (node id), `pytest tests/unit/orders/` (directory), `pytest -k "orders and not slow"` (name expression), `pytest -m integration` (marker). `pytest --co -q <selection>` lists what *would* run — the cheapest evidence of a non-empty, relevant selection; record its count. **Zero-selection behavior (verified):** nothing collected (a `-k`/`-m` that matches nothing) exits **5** (`no tests ran`); a nonexistent path exits **4** (usage error) — both detectable, never a silent pass. Impact selection: `pytest --testmon` (plugin `pytest-testmon`, tracks coverage-based dependencies) or `pytest --lf` (last failed); both need a warm cache and have the blind spots below.

Django labels with the built-in runner: `python manage.py test orders` (app), `orders.tests.test_models` (module), `orders.tests.test_models.OrderTest.test_total`; `--parallel` and `--keepdb` speed reruns. **unittest runner** (Django's default `manage.py test`, or `python -m unittest`) (reference run — CPython 3, contributor environment): `python -m unittest tests.test_orders` (module), `python -m unittest tests.test_orders.OrdersTest.test_total`, `python -m unittest -k <pattern>`. **Zero-selection behavior (verified, CPython 3.12+):** `-k` that matches nothing prints `NO TESTS RAN` (older CPython: `Ran 0 tests … OK`) and exits **0** — a silent empty run; always check the `Ran N tests` count.

### 3. Scoped static checks
- **ruff** (documented example): `ruff check <path>` and `ruff format --check <path>` scope natively to files/directories.
- **mypy** (documented example): `mypy <package>` runs on a subset but can miss errors that only surface with the whole program; prefer `mypy <top-level package>` (project-wide) as the real check and say so. **pyright** likewise.
- **black/isort** (`--check <path>`) scope natively.
- `manage.py check` / `makemigrations --check`: project-wide by nature (they load every app).

### 4. Source-to-test mapping
Per app: `orders/tests/test_models.py`, `test_views.py`, `test_api.py` (or a single `orders/tests.py`); `tests/` at the root for cross-app suites. A model change maps to its app's model tests **and** to every app that imports the model or uses it via a FK/serializer.

### 5. Affected consumers
`pytest --testmon` (coverage-based) where installed; otherwise reason from imports plus the ORM graph. **Blind spots:** signals (`@receiver`) fire with no import edge from the caller; migrations; `settings.py`/`INSTALLED_APPS`/middleware order; URLconfs; templates and template tags; DRF serializers/routers; fixtures/factories; Celery task registration. A middleware, settings or shared-model change affects many apps ⇒ the full run.

### 6. Escalation and fallback
Shared/core: `core/`, `common/`, abstract base models, custom user model, middleware, permissions, shared serializers, `conftest.py`. Always full run: `settings*.py`, `urls.py` at the project level, migrations, `pytest.ini`/`pyproject`, `requirements*`/`poetry.lock`, `Dockerfile`/compose when tests run in Docker, `.env*`. **Fallback:** the wrapped gate (`codecheck -f` inside the container) or `ruff check . && mypy <pkg> && pytest`.

### 7. Layers and posture
Unit (pytest, `SimpleTestCase`/plain functions with no DB) for services, forms, utils — fast base; model/view tests with the test DB (`TestCase`) as the integration layer for ORM + URL + view wiring; API tests with DRF's `APIClient`; a few browser/system tests at most. Unit-first; don't reclassify DB-backed tests as units.

### 8. Zero-selection behavior
pytest exits **5** on nothing collected and **4** on a bad path (verified). `manage.py test` / unittest print `NO TESTS RAN` (or `Ran 0 tests … OK` on older CPython) and exit **0** (verified) — check the count. Django's `--parallel` can hide a mis-scoped label behind `Ran 0 tests` in a worker; prefer explicit labels.
