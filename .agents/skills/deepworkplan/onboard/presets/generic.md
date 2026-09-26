# Preset — Generic fallback (any unrecognized stack)

> The safety net. When none of the specific presets match (Go, Rust, Ruby/Rails,
> Java/Kotlin, PHP/Laravel, .NET, Elixir, a polyglot or unusual repo, or a
> mostly-data/docs repo), reason **from first principles**. This guide guarantees
> `onboard` never fails on an unknown stack — it produces a minimally-correct but
> **real** standard, never a generic stub.

## The reasoning method (apply to any stack)

1. **Find the manifest(s) and lockfile(s).** `go.mod`, `Cargo.toml`, `Gemfile`,
   `composer.json`, `pom.xml`/`build.gradle`, `*.csproj`/`*.sln`, `mix.exs`,
   `pyproject.toml`, `package.json`, etc. The manifest tells you the language,
   the dependency set, and usually the entry points. The lockfile tells you the
   real package manager.
2. **Find the real build/test/lint/run commands.** Look, in order, at: the
   manifest's task/script section (e.g. `Cargo` subcommands, `go` subcommands,
   `composer scripts`, Gradle tasks), a `Makefile`/`Taskfile.yml`/`justfile`, CI
   workflows (`.github/workflows/*`, `.gitlab-ci.yml`), and any `docker.sh`/
   `docker-compose.yml`. Capture the **exact** commands; flag any that are
   CI-only or container-only.
3. **Find the source roots and modules.** Inspect the tree for the conventional
   source dirs of the language (`src/`, `cmd/`+`pkg/` for Go, `lib/` for Ruby,
   `app/` for Rails/Laravel, etc.). The major subfolders become per-module docs.
4. **Find the test convention.** Locate existing tests and copy their real
   naming + framework (`*_test.go`, `*_spec.rb`, `*Test.java`, `#[test]` in
   Rust, etc.) and where they live.
5. **Find the deployment/runtime shape.** Binary? Service? Library? Static
   output? This shapes `ARCHITECTURE.md` and `PERFORMANCE.md`.
6. **Carry forward existing conventions** — README, contributing guide, linter
   config, commit style. Never override a working convention with a generic one.

> Detected reality always wins. If you can identify the language but not a
> command, **ask the developer** for the canonical build/test/lint command
> rather than guessing — never write a placeholder.

## What to generate

- **Skills/agents/commands:** generic-but-**accurate** ones grounded in what you
  found — e.g. a `module`/`feature` skill, a `test` skill (using the repo's real
  test command), and the baseline agent personas (`reviewer`, `architect`,
  `executor`, `debugger`, `qa`, `perf-optimizer`, `security-auditor`) plus the
  five DWP commands and `code-review`/`pr`/`commit`. Add a stack-specific skill
  only if you can name a real, repeated task in the repo.
- **Docs:** all the MUST `docs/` categories, each filled with the **real**
  commands, module names, and test pattern you discovered — never an empty stub.
- **Per-module docs:** a `README.md` for each major source folder you found.

## Validation command

There is no preset command here by design — **the whole point is to find the
real one** (step 2). Capture it verbatim into `AGENTS.md` Quick Commands and
`docs/DEVELOPMENT_COMMANDS.md`, and use it for the Phase 8 smoke test.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; items marked *documented example* were **not** run here —
confirm the exit code and the selection count in the target repo before trusting
them in a gate.

### 1. Full commands
- Whatever the repo's manifest/Makefile/CI defines as the test, lint, format and type-check commands — captured **verbatim** with their working directory (Phase 1). If none exist, the **proposed** setup (Phase 4) names them and marks them proposed.

### 2. Scoped invocation
**Discover, don't assume** (a recipe, since the stack is unknown): (1) read the runner's own help (`<runner> --help`) for a path argument, a name filter (`-k`, `-t`, `--filter`, `--tests`, `-run`), a tag/marker filter, and an impact/changed-since option; (2) find one real test file and run the runner on **that file only**; (3) record the output line that proves selection (a file/test count) and the exit code; (4) run the runner with a filter that **cannot** match (`--filter zzz_no_such_test`) and record what it prints and its exit code — that is this repo's zero-selection behavior; (5) write the pattern into `TESTING_GUIDE.md` as *verified* only if steps 2–3 selected a non-empty relevant set, otherwise as *proposed/unverified* with the full command as fallback.

### 3. Scoped static checks
- Try the linter/formatter/type-checker with a single path argument; if it rejects paths or its correctness depends on whole-program analysis, record it as project-wide (the real, often cheap, option). Never invent a per-file form.

### 4. Source-to-test mapping
Derive from the real layout found in Phase 1: co-located tests, a mirrored `tests/`/`test/`/`spec/` tree, or a naming convention (`*_test.*`, `*.spec.*`, `*Test.*`). Write the rule down with one concrete pair (`<source> ↔ <test>`).

### 5. Affected consumers
Use the ecosystem's dependency tooling if it exists (`<pm> deps`, `--findRelatedTests`, `--changed`, `testmon`, a task graph); otherwise treat imports/requires as the graph and grep for consumers. Record the blind spots you can see: configuration files, generated code, templates, fixtures, plugin/entry-point registration, environment variables.

### 6. Escalation and fallback
Name the shared/core directories (anything imported by most of the code), and list the files whose change always triggers the full run: dependency manifests and lockfiles, build/test configuration, environment/config files, generated-code sources. **Fallback:** the full command(s) — for an unknown stack, prefer the full run whenever the scoped form is unverified.

### 7. Layers and posture
Identify which layers exist (unit / integration / e2e) by where tests live and what they touch (I/O, network, DB). Propose unit-first behavioral coverage for new work; use integration for real seams; keep e2e few. No ratio quota; no rewrite of what exists.

### 8. Zero-selection behavior
Unknown until measured: step (4) of §2 is how you find out. Record the exact message and exit code in `TESTING_GUIDE.md`; if the runner exits 0 on an empty selection, say so and require the selection count as evidence.
