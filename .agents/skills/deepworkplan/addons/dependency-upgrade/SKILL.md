---
name: deepworkplan-addon-dependency-upgrade
description: DeepWorkPlan addon that safely upgrades a repo's dependencies — reasoning about the repo's ACTUAL package manager (npm/pnpm/yarn + ncu, pip/poetry/uv, cargo, go mod, bundler, composer, and more) rather than assuming npm — with a batched, validated, revertible workflow that detects the manager and manifests/lockfiles, classifies upgrades (patch/minor/major), upgrades in safe batches, runs the repo's real validation gate after each batch, reverts a failing batch, and summarizes. Near-default — offered for every repo with declared dependencies, and its delegator installs under the onboarding consent unless declined; upgrades themselves never run automatically, only as explicit, gated work. Never required for baseline conformance; reconciles with the repo's existing tooling. Use when the developer wants to bring dependencies up to date without breaking the build.
version: "4.0.3"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"⬆️","homepage":"https://deepworkplan.com"}}
---

# DeepWorkPlan — Dependency-Upgrade Addon

Safely bring a repo's dependencies up to date with a **batched, validated,
revertible** workflow. This is the methodology's **third addon** —
**near-default**: offered for every repo with declared dependencies, and its
`/lib-upgrade` delegator installs under the onboarding consent **unless
explicitly declined**. Installing the delegator changes no dependencies — an
upgrade itself always runs as explicit, gated work (a plan task or a direct
invocation). It is **never** required for a repo to be AI-first.

> ## The rule that overrides everything: REASON about the package manager, then upgrade
>
> The legacy version of this workflow assumed npm. **It does not.** The first job
> is to **detect the repo's actual package manager from the manifest and lockfile
> that exist** (see `SPEC.md` §2 and `templates/ecosystems.md`), then drive that
> manager's real upgrade and install commands. Never run `ncu`/`pnpm` in a Go,
> Rust, Python, Ruby, or PHP repo. Never assume a lockfile you have not seen.

## Read these first (all relative inside the skill)

- [`SPEC.md`](SPEC.md) — the normative (RFC-2119) contract: detection, semver
  classification, batched-upgrade rule, validate-after-each-batch gate,
  revert-on-failure rule, reconcile-don't-clobber, validation step.
- [`templates/ecosystems.md`](templates/ecosystems.md) — the **per-ecosystem
  reasoning table**: how to detect each manager and its real detect / classify /
  upgrade / install / lockfile commands. Match the row for the detected stack as
  a *checklist*, then verify against the real repo — **detected reality wins**.
- [`templates/upgrade-report.md`](templates/upgrade-report.md) — the report shape
  to summarize what was upgraded, skipped, reverted, and validated.
- [`templates/lib-upgrade-command.md`](templates/lib-upgrade-command.md) — the
  `/lib-upgrade` delegator this addon installs into the target repo's
  `.agents/commands/` **only when accepted**.
- `../README.md` — the addon mechanism (opt-in, reconcile-don't-clobber, contract).

## When this runs

- From **`onboard` Phase 7b** — after the core AI-first scaffolding, `onboard`
  offers this addon for **every repo with declared dependencies** (any manifest
  or lockfile) and installs the `/lib-upgrade` delegator under the onboarding
  consent **unless explicitly declined**; a decline leaves a baseline-conformant
  repo with no command. Installing the delegator runs **no** upgrade — the flow
  below always starts from an explicit request.
- **Directly** — `/deepworkplan-addon-dependency-upgrade` on an already-onboarded
  repo to upgrade dependencies, or via the installed `/lib-upgrade` delegator.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`.

**Writes:** manifests and lockfiles (`package.json` + `package-lock.json` /
`pnpm-lock.yaml`, `pyproject.toml` + lock, `Cargo.toml` + `Cargo.lock`, and
equivalents), a batch/upgrade report under the repo's working-state directory,
and per-batch snapshots in that working-state directory. Commits require the
developer's explicit instruction. Remote registry access is limited
to the package manager's own resolution commands (`npm view`, `pip index`,
`cargo update`…) — metadata queries and lockfile regeneration, never script
execution. (Ecosystem post-install scripts run only if the developer opts in,
stated per batch.)

**It MUST NOT:** run a major-version jump that fails the repo's validation gate
and still record the batch as upgraded, commit a lockfile inconsistent with its manifest (a lockfile-only update
within an existing allowed range is valid), force-push or rewrite history, or discard prior successful batches while reverting a later one. Each batch
is revertible from its own pre-batch snapshot, including before any commit.

## The flow

### Step 0 — Consent + clean tree
1. Confirm the developer wants a dependency upgrade (skip silently if declined —
   the repo stays baseline-conformant).
2. **Establish a recoverable baseline.** Inspect git status and ownership. Use
   an isolated checkout or preserve relevant existing changes in a verified
   snapshot; never stash, discard or commit unrelated work implicitly. Run the
   real gate once to distinguish pre-existing failure from an upgrade failure.

### Step 1 — Detect the package manager (the part you MUST reason about)
Detect the manager(s) from the **manifest + lockfile that actually exist**, never
by assuming npm. Use `templates/ecosystems.md`:

- **JS/TS** → `package.json` + which lockfile: `pnpm-lock.yaml` (pnpm),
  `yarn.lock` (yarn), `package-lock.json` (npm). `ncu` is the cross-manager
  version checker; the install/update verb is the detected manager's.
- **Python** → `pyproject.toml` + `poetry.lock` (poetry) / `uv.lock` (uv);
  `requirements*.txt` (pip / pip-tools); `Pipfile.lock` (pipenv).
- **Rust** → `Cargo.toml` + `Cargo.lock` (`cargo update`).
- **Go** → `go.mod` + `go.sum` (`go get -u` / `go get` per module + `go mod tidy`).
- **Ruby** → `Gemfile` + `Gemfile.lock` (`bundle update`).
- **PHP** → `composer.json` + `composer.lock` (`composer update`).

A repo MAY have **more than one** ecosystem (e.g. a JS frontend + a Python
service). Handle each ecosystem with its own manager, in its own batches.

### Step 2 — Classify upgrades (patch / minor / major)
For every outdated dependency, classify by semver against the version in the
manifest/lockfile:

- **patch** `X.Y.Z → X.Y.(Z+1)` — safest (bug fixes).
- **minor** `X.Y.Z → X.(Y+1).0` — usually safe (additive, backward-compatible).
- **major** `X.Y.Z → (X+1).0.0` — breaking changes possible.

Group **patch + minor** as the auto-batchable set. **Majors require explicit
developer approval** before inclusion (present them and wait). Upgrade tightly
coupled packages **together** (e.g. `typescript` + its plugins; a framework + its
companion packages) so a peer-dependency constraint is not split across batches.

### Step 3 — Upgrade in safe batches
Apply upgrades in **small, coherent batches** — never all at once (that makes a
failure impossible to isolate). A reasonable order: patch batch → minor batch →
each approved major **on its own**. For each batch, run the detected manager's
approved package/version update commands, restricted to that batch. Resolve
exact target versions before mutation; never use a broad latest/all-packages
command that can pull in an unapproved major or unrelated package. A lockfile-only
update is valid when existing manifest constraints already admit the target.
Before each batch, snapshot every file it may change (including file absence),
record the manager/environment and previous gate, and verify the snapshot is
recoverable. Suppress dependency lifecycle scripts using the manager's supported
controls unless already explicitly authorized; if safe suppression is unavailable,
stop before running them. Validation that executes dependency build hooks needs
that same authorization. The manager owns lockfile regeneration.

### Step 4 — Validate after EACH batch (the gate)
After every batch, run the **repo's real validation gate** — the commands the
repo actually uses, discovered from `AGENTS.md` Quick Commands /
`docs/DEVELOPMENT_COMMANDS.md` / the manifest's scripts, or the devcontainer's
`codecheck`/`check`/`fix`/`test` aliases if that addon is present. Examples:
`pnpm run biome:check && pnpm run astro:check && pnpm run build`;
`ruff check && mypy && pytest`; `cargo test`; `go build ./... && go test ./...`;
`bundle exec rspec`; `composer test`. **Never invent a gate** — use the repo's
real one.

### Step 5 — Revert a failing batch
If the gate fails for a batch, **revert just that batch** and continue:
restore the exact **pre-batch snapshot** of the manifest, lockfile and other
owned files, preserving earlier successful batches and pre-existing changes.
Never restore from `HEAD` unless it is proven identical to that snapshot.
Re-sync the environment without advancing resolution or enabling unapproved
scripts; confirm the previous gate again, then record the batch as
**skipped/failed** with the reason. Retry only with a new hypothesis or narrower selection; after two attempts
without progress, stop blind retries. If restore or its gate fails, stop with
the snapshot and blocker recorded instead of proceeding to another batch. A failing major is set aside, not forced.

### Step 6 — Summarize
Produce the report from `templates/upgrade-report.md`: upgraded (by tier),
skipped (with reason), reverted (with the failing gate), the manager(s) used, the
files changed (manifest + lockfile), and recommended follow-ups. **Do not commit
automatically** — surface the diff and let the developer commit (suggest
`chore(deps): …`).

## Failure-mode guardrails

- **Never required, never blocking.** If the developer declines, stop cleanly.
- **Reason about the manager.** Never run npm/ncu in a non-JS repo; never assume a
  lockfile you have not seen.
- **Never all-at-once.** Batch so a failure is isolable and revertible.
- **Real gate only.** Validate with the repo's actual commands, never a guess.
- **Revert, don't push through.** A failing batch is reverted and recorded, never
  force-installed past a broken gate.
- **Don't hand-edit lockfiles.** The manager owns them; regenerate via install.
- **Don't auto-commit.** Surface the diff; the developer commits.
