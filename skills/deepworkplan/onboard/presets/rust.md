# Preset — Rust (Cargo)

> Reasoning aid, not a template. Verify every assumption against the live repo;
> detected reality wins. Capture the **real** validation command, not the
> example below.

## Signals that identify this stack

- `Cargo.toml` and `Cargo.lock` at the repo (or crate) root; `Cargo.toml`
  declares `[package]`, `[dependencies]`, and often `[features]`.
- Entry point: `src/main.rs` (binary crate) or `src/lib.rs` (library crate);
  some crates ship both, plus extra binaries under `src/bin/`.
- Module tree under `src/` via `mod`/`pub mod` and `mod.rs` or `foo.rs`+`foo/`.
- **Workspace** monorepos: a root `Cargo.toml` with `[workspace]` and
  `members = [...]`, each member its own crate with its own `Cargo.toml`.
- Edition (`edition = "2021"/"2024"`) and an MSRV (`rust-version`) may be pinned;
  a `rust-toolchain.toml` may pin the toolchain. `build.rs` indicates a build
  script. **Read what's present** rather than assuming.

## What to look for in recon

- The **real** test command: `cargo test` (workspace-wide vs `-p <crate>`),
  whether `cargo nextest run` is used, and where tests live — inline
  `#[cfg(test)] mod tests` vs integration tests under `tests/` vs doctests.
- The **real** lint/format gate: `cargo clippy` (often `-- -D warnings` to fail
  on lints) and `cargo fmt --check` (or `cargo fmt -- --check`). Confirm whether
  CI denies warnings.
- The **real** build: `cargo build` vs `cargo build --release`; which features
  are enabled (`--all-features`, `--no-default-features`, specific `--features`).
- Feature flags and their meaning; `unsafe` blocks and FFI boundaries; any
  `build.rs` codegen. Async runtime if present (`tokio`/`async-std`).
- **Interface surface for the design-system addon:** a `clap` binary styled with
  `colored`/`owo-colors`/`indicatif`/`ratatui` (or a centralized output module
  with semantic styles) is a `cli-output` signal — in Phase 7b, recommend the
  design-system addon's `cli-output` profile (ask, never auto-apply).

## Stack-specific skills/agents/commands to generate

- Skills: `module-add` (new module + tests), `error-type` (define an error enum /
  `thiserror` variant), `crate-add` (new workspace member wired into `members`),
  optionally `bench` (criterion) and `feature-flag` (gate code behind a feature).
- Agents: baseline roles + an `ownership-reviewer` / `unsafe-auditor` persona
  aware of borrow/lifetime and `unsafe` safety invariants.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — crate/workspace boundaries, module tree, trait/ownership
  model, error-handling strategy (`Result`/`?`), async runtime if any.
- `TESTING_GUIDE.md` — unit (`#[cfg(test)]`) vs integration (`tests/`) vs
  doctests, how to scope a single crate (`-p`), fixtures/builders.
- `SECURITY.md` — `unsafe`/FFI boundaries and their invariants, dependency
  audit (`cargo audit`/`cargo deny`), secrets handling.
- Per-module docs: one per significant crate (workspace) or module group.

## Typical validation command (FIND the real one)

Often `cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo
test` (workspace-wide), with a separate `cargo build --release` for release
artifacts. **Do not assume** the feature set or whether warnings are denied —
read the `Makefile`/`justfile`/CI and capture the exact command.

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
- Tests: `cargo test` (or `cargo test --workspace`) from the workspace root; `cargo nextest run` where adopted.
- Static: `cargo fmt --check` (or `--all`), `cargo clippy --all-targets -- -D warnings` (`--workspace`), `cargo build`/`cargo check`.

### 2. Scoped invocation
**`cargo test`** (documented example — Rust is not available in the contributor environment): `cargo test -p orders` (one crate), `cargo test -p orders total` (substring filter on test names), `cargo test -p orders --lib` (unit tests only), `cargo test -p orders --test api` (one integration test file `tests/api.rs`), `cargo test --doc`; `-- --exact <path::to::test>` for one test; `cargo nextest run -p orders -E 'test(total)'` with nextest filters. **Evidence:** `test result: ok. N passed; 0 failed` per test binary — `N` must be non-zero for the intended binary.

### 3. Scoped static checks
- `cargo clippy -p orders --all-targets -- -D warnings` and `cargo fmt --check -p orders` (documented example) scope by crate; `cargo check -p orders` compiles one crate and its deps. Within a crate, clippy/fmt are per-crate, not per-file.

### 4. Source-to-test mapping
Unit tests live **inside** the source file (`#[cfg(test)] mod tests`), so a source file maps to its own tests; integration tests in `tests/*.rs` (each file is a separate binary) exercise the crate's public API; doc tests in `///` examples; workspace crates under `crates/<name>/`.

### 5. Affected consumers
Workspace dependency graph via `cargo tree -p <crate> -i` (inverse: who depends on this crate) — the affected set is the crate plus its dependents' tests. **Blind spots:** feature flags (`--features`/`--all-features` change what compiles), `build.rs`, proc-macros, `include_str!`/`include_bytes!` fixtures, conditional compilation (`cfg`), environment-driven config. A public-API or trait change in a shared crate ⇒ dependents' tests or `--workspace`.

### 6. Escalation and fallback
Shared/core: crates depended on by most others (`core`, `common`, `domain`, proc-macro crates), shared traits. Always full run: `Cargo.toml`/`Cargo.lock` (workspace or shared crate), `rust-toolchain*`, `build.rs`, feature definitions, `clippy.toml`/`rustfmt.toml`. **Fallback:** `cargo fmt --check && cargo clippy --workspace --all-targets -- -D warnings && cargo test --workspace`.

### 7. Layers and posture
Unit (`#[cfg(test)]` in-file, no I/O) — fast base; integration under `tests/` against the public API; doc tests as executable documentation; few e2e. Unit-first; no ratio quota.

### 8. Zero-selection behavior
`cargo test <filter>` with no match prints `running 0 tests` and `test result: ok. 0 passed` with exit **0** (documented) — a silent empty run; check the `N passed` count. A wrong `-p` name fails loudly (`package ID specification … did not match`).
