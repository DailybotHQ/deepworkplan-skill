# Preset — Python package / CLI

> Reasoning aid, not a template. Verify against the live repo; detected reality
> wins. Capture the **real** validation command, not the example below.

## Signals that identify this stack

- `pyproject.toml` with a `[project.scripts]` (or legacy `console_scripts` in
  `setup.py`/`setup.cfg`) entry point → an installable CLI.
- A CLI framework in deps: `click`, `typer`, or stdlib `argparse`.
- An importable package layout: `src/<pkg>/` (src-layout) or `<pkg>/` at root,
  with `__init__.py`, a `cli.py`/`__main__.py`, and `commands/`/`subcommands/`.
- Packaging/build via `hatch`, `poetry`, `setuptools`, or `flit`; publishing to
  PyPI (a `twine`/build step in CI). Package manager from the lockfile present.

## What to look for in recon

- The **real** validation gate: `ruff check` / `flake8`, `black --check`,
  `mypy`, and the test command (`pytest`). Capture verbatim.
- Test convention: `tests/test_*.py` or co-located `*_test.py`; pytest fixtures.
- The console-script entry point name (the actual CLI command users type) and
  the command/subcommand structure.
- Whether it's published (PyPI) — drives a packaging/release doc emphasis and a
  `SECURITY.md` note on supply-chain (a public OSS surface).
- **Interface surface for the design-system addon:** a `rich`/`textual`/
  `questionary` dependency plus a deliberate display layer (a `display.py`-style
  module with semantic print helpers) is a `cli-output` signal — in Phase 7b,
  recommend the design-system addon's `cli-output` profile (ask, never
  auto-apply). A bare `argparse` script with raw prints is not a signal.

## Stack-specific skills/agents/commands to generate

- Skills: `command-add` (add a top-level CLI command), `subcommand` (add a
  subcommand under an existing group), `option`/`flag` (add an option with help +
  test); optionally `release` (version bump + changelog + publish) if it ships to
  PyPI.
- Agents: baseline + a `cli-author` / `dx-reviewer` persona aware of help text,
  exit codes, and backward compatibility of the CLI surface.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — package layout, the command/subcommand tree, the public
  API surface vs internal modules.
- `STANDARDS.md` — public-API stability, help-text conventions, exit codes,
  error messages as a user-facing surface.
- `TESTING_GUIDE.md` — pytest patterns, CLI-runner testing (e.g. Click's
  `CliRunner`), coverage target.
- Per-module docs: per command group / major subpackage.

## Typical validation command (FIND the real one)

Commonly `ruff check . && mypy <pkg> && pytest`, or wrapped in a `make
lint test` / `hatch run` / `tox` target. **Do not assume** — read
`pyproject.toml`/Makefile/`tox.ini`/CI and capture the exact commands.

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
- Tests: `pytest` from the package root (or `tox -e py311` / `nox -s tests` when the repo uses a matrix runner — record the session names).
- Static: `ruff check .` (+ `ruff format --check .` / `black --check .`), `mypy <package>`, optionally `python -m build` / `pip install -e .` as the packaging smoke.

### 2. Scoped invocation
**pytest** (reference run — pytest 9.1.1, contributor environment): `pytest tests/unit/test_orders.py` (file), `pytest tests/unit/test_orders.py::TestOrders::test_total` (node id), `pytest tests/unit/orders/` (directory), `pytest -k "orders and not slow"` (name expression), `pytest -m integration` (marker). `pytest --co -q <selection>` lists what *would* run — the cheapest evidence of a non-empty, relevant selection; record its count. **Zero-selection behavior (verified):** nothing collected (a `-k`/`-m` that matches nothing) exits **5** (`no tests ran`); a nonexistent path exits **4** (usage error) — both detectable, never a silent pass. Impact selection: `pytest --testmon` (plugin `pytest-testmon`, tracks coverage-based dependencies) or `pytest --lf` (last failed); both need a warm cache and have the blind spots below.

With tox/nox: `tox -e py311 -- tests/test_cli.py -k parse` passes the selection through to pytest (after `--`); with nox, `nox -s tests -- tests/test_cli.py`.

### 3. Scoped static checks
- **ruff** (documented example): `ruff check <path>` and `ruff format --check <path>` scope natively to files/directories.
- **mypy** (documented example): `mypy <package>` runs on a subset but can miss errors that only surface with the whole program; prefer `mypy <top-level package>` (project-wide) as the real check and say so. **pyright** likewise.
- **black/isort** (`--check <path>`) scope natively.

### 4. Source-to-test mapping
`tests/test_<module>.py` ↔ `src/<pkg>/<module>.py` (src layout) or co-located `<module>_test.py`; CLI commands tested through Click's `CliRunner` / Typer's `CliRunner` in `tests/test_cli.py`; doctests where the package uses them (`pytest --doctest-modules`).

### 5. Affected consumers
`pytest --testmon` where installed; otherwise the import graph is usually small and explicit. **Blind spots:** entry points declared in `pyproject.toml` (`[project.scripts]`), plugin registration via entry points, `__init__.py` re-exports, packaged data files, version metadata. A change to a shared helper module or the CLI's option parsing affects most commands ⇒ the full run (it is usually seconds anyway).

### 6. Escalation and fallback
Shared/core: `<pkg>/__init__.py`, `<pkg>/cli.py`/`main.py`, `<pkg>/core/` or `utils/`, `conftest.py`. Always full run: `pyproject.toml`, `setup.cfg`, lockfiles, `tox.ini`/`noxfile.py`, `pytest.ini`. **Fallback:** `ruff check . && mypy <pkg> && pytest` — for most packages the full suite is fast; prefer it over elaborate selection when it finishes in seconds.

### 7. Layers and posture
Unit (pytest) for library functions — the base and often the whole suite; CLI tests with `CliRunner` as the integration seam (argument parsing → behavior → exit code); a packaging smoke (`python -m build`, `pip install -e .`). Unit-first; no ratio quota.

### 8. Zero-selection behavior
pytest exits **5** on nothing collected and **4** on a bad path (verified). `tox`/`nox` propagate pytest's exit code; `--doctest-modules` over a path with no doctests is a silent zero — check the collected count.
