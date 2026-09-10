# Preset testing matrix — what was verified, what is documented

Contributor-facing companion to the "Testing and validation (verified vs
example)" section every preset under `skills/deepworkplan/onboard/presets/`
carries. This file is **not installed**; the runtime pack never references it.
It records, per ecosystem, which scoped-invocation claims were **verified by a
run** in the contributor environment, which are **documented examples** (taken
from the tool's documentation or `--help`, not run here), and the open
questions a later contributor should close by running the tool.

Legend: **run** = executed on a real repo/fixture here · **help** = flag
existence confirmed from `--help` output · **doc** = documented behavior, not
run here · **?** = unconfirmed, confirm in a target repo.

| Ecosystem / runner | Path scoping | Name filter | Impact selection | Zero-selection behavior | Verification status |
|---|---|---|---|---|---|
| Vitest 5.0.0 | `vitest run <file|dir>` | `-t` | `--changed [ref]` | path miss → `No test files found`, exit **1**; `-t` miss → exit **0**, all skipped | **run** (`/app` website repo) |
| Biome 2.5.12 | `biome check <path>` | — | — | missing path → exit 1 | **run** |
| Jest 29 | `jest <pattern>` / `--testPathPattern` | `-t` | `--findRelatedTests`, `--changedSince` | `No tests found` → exit 1 unless `--passWithNoTests` | **help** (flags); exit codes **doc** |
| Playwright 1.63 | `playwright test <file>` | `-g` | `--only-changed [ref]` | `No tests found` → exit code **?** | **help** (flags) |
| Karma/Jasmine via Angular CLI | `ng test --include=<glob>` | `fdescribe`/`fit` (source-level) | — | `Executed 0 of 0`, exit **0** (?) | **doc** |
| `astro check`, `tsc`, `vue-tsc`, `svelte-check`, `nuxi typecheck` | project-wide only | — | — | n/a | **help** (`astro check`); **doc** (others) |
| pytest 9.1.1 | file / dir / node id | `-k`, `-m` | `pytest-testmon` (doc), `--lf` | nothing collected → exit **5**; bad path → exit **4** | **run** (fixture) |
| unittest / `manage.py test` (CPython 3.12+) | module / class / method labels | `-k` | — | `NO TESTS RAN`, exit **0** | **run** (fixture) |
| ruff / black / isort / mypy / pyright | path | — | — | — (mypy subset caveat) | **doc** |
| `go test` | `./pkg/...` | `-run` | `go list -deps` / dependents | `no tests to run`, exit **0** | **doc** |
| `cargo test` | `-p <crate>`, `--test <file>`, `--lib` | substring, `--exact` | `cargo tree -i` | `0 passed`, exit **0** | **doc** |
| Maven Surefire | `-pl <module> -am` | `-Dtest=` | `-amd` (dependents) | `No tests were executed!` → build fails unless `failIfNoSpecifiedTests=false` | **doc** |
| Gradle | `:<module>:test` | `--tests` | — | `No tests found for given includes` → fails | **doc** |
| RSpec | file / dir / `file:line` | `-e`, `--tag` | — | `0 examples`, exit **0**; `fail_if_no_examples` config | **doc** |
| Minitest (`bin/rails test`) | file / dir / `file:line` | `-n` | — | `0 runs`, exit **0** | **doc** |
| PHPUnit / Pest (`artisan test`) | file / dir / `--testsuite` | `--filter`, `--group` | — | `No tests executed!`, exit **0**; PHPUnit ≥10 `--fail-on-empty-test-suite` | **doc**; exit code across versions **?** |
| `flutter test` / `dart test` (package:test) | file / dir | `--name`, `--tags` | — | `No tests ran.`, exit **79** (non-zero) | **doc**; confirm code **?** |
| Detox / Maestro | suite / flow file | — | — | wrong path fails; empty flow "passes" | **doc** |
| `xcodebuild test` | `-only-testing:Target/Class/method` | — | — | invalid identifier → error (exit **?**) | **doc** |
| `swift test` | — | `--filter <regex>` | `swift package show-dependencies` | `Executed 0 tests`, exit **0** | **doc** |
| Terraform (`validate`/`tflint`/`terraform test`) | per directory / root module | `terraform test -filter=` | callers by `source =` grep | `validate` on an empty dir → `Success!`, exit **0**; `-filter` missing file → error | **doc** |

## How to close an open item

Run the tool in a repository that uses it, with (a) one real scoped selection
and (b) a filter that cannot match; record the summary line and the exit code;
update the preset's §8 and this table; state the tool version.

## Why this exists

`DOCUMENTATION_STANDARD.md` §3.4 requires a repository's `TESTING_GUIDE.md` to
carry *verified* scoped commands. The presets are reasoning aids, so their
commands are examples until Phase 1 of onboarding verifies them in the target
repo. This matrix keeps the contributor side honest about which examples were
exercised at least once and which still rest on documentation.
