# Preset — Go (modules)

> Reasoning aid, not a template. Verify every assumption against the live repo;
> detected reality wins. Capture the **real** validation command, not the
> example below.

## Signals that identify this stack

- `go.mod` and `go.sum` at the repo root; the first line of `go.mod` is the
  module path, followed by the `go` directive (language version) and `require`
  blocks.
- A `package main` with `func main()` as the binary entry point — frequently
  under `cmd/<binary>/main.go` when there are several binaries.
- Idiomatic layout: `cmd/` (binaries), `internal/` (private packages the module
  alone can import), `pkg/` (exported reusable packages), plus domain packages.
- Multi-module repos carry more than one `go.mod` (e.g. a `go.work` workspace or
  nested modules). **Infer from what's present.**
- Optional: a `Makefile`, a `vendor/` directory (vendored deps), `.golangci.yml`,
  and a `Dockerfile` for containerized builds.

## What to look for in recon

- The **real** test command: `go test ./...` (often with `-race`, `-cover`, or
  `-count=1`). Tests are table-driven `*_test.go` files **beside** the code they
  test; check for `testdata/` fixtures and any `TestMain`.
- The **real** lint/vet gate: `go vet ./...`, `golangci-lint run` (read
  `.golangci.yml` for enabled linters), and a format check (`gofmt -l .` or
  `goimports`). Confirm which one CI enforces.
- The **real** build: `go build ./...`, plus any release wiring (`-ldflags`,
  `CGO_ENABLED`, cross-compilation via `GOOS`/`GOARCH`).
- The module path, exported vs `internal/` boundaries, and where binaries live.
- **Interface surface for the design-system addon:** a `cobra` binary styled
  with `lipgloss`/`bubbletea` (or a centralized output package with semantic
  styles) is a `cli-output` signal — in Phase 7b, recommend the design-system
  addon's `cli-output` profile (ask, never auto-apply).

## Stack-specific skills/agents/commands to generate

- Skills: `package-add` (new package + table-driven test), `handler` (HTTP
  handler + test) if it's a service, `cmd-add` (new binary under `cmd/`),
  optionally `interface` (define an interface + mock) and `error-wrap`.
- Agents: baseline roles + an `api-reviewer` / `concurrency-reviewer` persona
  aware of goroutine/channel safety and `context.Context` propagation.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — package boundaries (`cmd`/`internal`/`pkg`), interface
  seams, concurrency model (goroutines/channels/`context`), error-handling
  conventions (wrapping with `%w`).
- `TESTING_GUIDE.md` — table-driven tests, `testdata/` fixtures, subtests
  (`t.Run`), how to scope a single package (`go test ./path/...`).
- `SECURITY.md` — input validation, secrets handling, dependency hygiene
  (`govulncheck`), the sensitive-data boundary.
- Per-module docs: one per significant package or `cmd/` binary.

## Typical validation command (FIND the real one)

Often `gofmt -l . && go vet ./... && golangci-lint run && go test -race ./...`,
with a separate `go build ./...`. **Do not assume** the lint tool or test flags
— read the `Makefile`/`.golangci.yml`/CI and capture the exact command.

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
- Tests: `go test ./...` from the module root (`-race`, `-cover` as the repo's CI does); `go vet ./...`; `gofmt -l .` (or `goimports -l .`); `golangci-lint run` per `.golangci.yml`.
- `go build ./...` as the compile gate.

### 2. Scoped invocation
**`go test`** (documented example — Go is not available in the contributor environment): `go test ./internal/orders/...` (package tree), `go test ./internal/orders -run 'TestTotal'` (regex on test names; `-run 'TestTotal/subcase'` for `t.Run` subtests), `go test ./... -run '^TestOrder'`. `go test -v` prints each test; `-count=1` bypasses the cache. **Evidence:** per-package `ok <pkg>` lines with test names under `-v`, or a coverage summary. **Cache note:** `go test` results are content-hashed (`(cached)`); a cached pass is legitimate reuse — the inputs are provably equivalent — and `-count=1` forces a fresh run when in doubt.

### 3. Scoped static checks
- `go vet ./internal/orders/...` and `golangci-lint run ./internal/orders/...` (documented example) scope by package path; `gofmt -l <dir>` by directory. `go build ./...` is whole-module by nature (cheap).

### 4. Source-to-test mapping
`foo_test.go` beside `foo.go` in the same package (white-box) or `package foo_test` (black-box) in the same directory; `internal/` packages are consumed across the module; `cmd/<bin>/` mains have little logic and few tests; testdata under `testdata/`.

### 5. Affected consumers
`go list -deps ./...` / `go list -f '{{.Deps}}' ./internal/orders` reveal the dependency graph; running `go test` on a changed package **and** on every package that imports it (`go list -f '{{.ImportPath}} {{.Imports}}' ./... | grep <pkg>`) is the affected set. **Blind spots:** build tags, cgo, generated code (`go generate`, protobuf), embedded files (`//go:embed`), testdata fixtures, environment-driven config, integration tests behind `-tags integration` or `testing.Short()`. Interface changes ripple to all implementers ⇒ the full run (`go test ./...` is usually fast).

### 6. Escalation and fallback
Shared/core: `internal/` packages imported widely (`pkg/`, `internal/platform`, `internal/domain`), interfaces, shared test helpers. Always full run: `go.mod`/`go.sum`, `.golangci.yml`, build tags/`Makefile`, generated-code sources, `Dockerfile`. **Fallback:** `gofmt -l . && go vet ./... && golangci-lint run && go test -race ./...`.

### 7. Layers and posture
Unit (table-driven `go test` on packages, no I/O) — fast base; integration behind a build tag or `testing.Short()` for DB/network seams (`-tags integration`); a few end-to-end binaries under `cmd/…` tests. Unit-first; no ratio quota.

### 8. Zero-selection behavior
`go test -run <no-match>` prints `testing: warning: no tests to run` and reports `ok` with exit **0** (documented) — a silent empty run: check `-v` output or the coverage summary for actual test names. A package with no test files prints `[no test files]` (also exit 0).
