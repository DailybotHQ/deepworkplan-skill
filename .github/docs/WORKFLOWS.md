# GitHub Workflows Reference — `deepworkplan-skill`

Per-workflow reference for the two GitHub Actions workflows that live in
[`.github/workflows/`](../workflows/). Each section documents the trigger,
jobs, gate semantics, and failure modes so a maintainer (or an AI agent
piloting this repo) can reason about why a job did or didn't run.

| Workflow | File | Purpose |
|----------|------|---------|
| Auto-release | [`auto-release.yml`](../workflows/auto-release.yml) | Conventional-commit-driven release + temp install smoke + addon dogfood |
| CI | [`ci.yml`](../workflows/ci.yml) | Frontmatter validation, shellcheck, bats tests, `setup.sh`/`context.sh` smoke, markdown link check |

---

## 1. auto-release.yml — Bump, tag, release, dogfood

| Property | Value |
|----------|-------|
| **Trigger** | `push` to `main` |
| **Concurrency** | `auto-release-main`, no in-progress cancellation |
| **Permissions** | `contents: write` at workflow level |
| **Skip guard** | Skips if head commit starts with `chore(release):` OR contains `[skip release]` (breaks the auto-release loop) |
| **Token** | `AUTOMATION_GITHUB_TOKEN` (org convention) so the bot user can push to protected `main`; falls back to `GITHUB_TOKEN` |

### Job: `release`

Sequenced steps (a-i below), all in one long-running job on `ubuntu-latest`:

| Step | Purpose |
|------|---------|
| a. Set git identity | `Dailybot Automations <ops@dailybot.com>` |
| b. Determine bump level | Reads current version from the router `skills/deepworkplan/SKILL.md`; scans commits since last `vX.Y.Z` tag; picks MAJOR (`feat(...)!:` / `BREAKING CHANGE:`), MINOR (`feat(...):`), or PATCH (safe default) |
| c. Bump version in all SKILL.md | Router + every sub-skill + every addon (`devcontainer`, `dailybot`, `ai-diff-reviewer`, `dependency-upgrade`, `design-system`) stay in lock-step |
| d. Prepend CHANGELOG.md section | Merged commits since last tag become bullets |
| e. Commit `chore(release): X.Y.Z [skip ci]` | The `[skip ci]` marker prevents CI from re-running on the release commit |
| f. Tag `vX.Y.Z` and push | With `--follow-tags` so commit + tag land atomically |
| g. **Smoke — published tag installs (temp dir)** | Runs `npx --yes skills add DailybotHQ/deepworkplan-skill@vX.Y.Z --skill deepworkplan --force -y` into an isolated temp directory and asserts `version:` matches. Does **not** overwrite `.agents/skills/deepworkplan/` (that copy is repo-adapted; sync via `scripts/refresh-dogfood-skill.sh`) |
| h. **Dogfood — dailybot** | `DailybotHQ/agent-skill` → `.agents/skills/dailybot/`. Only commits if the upstream tag moved. Non-interactive contract (`--yes` + `-y`) is mandatory — dropping either flag hangs the workflow indefinitely on the CLI's agent-picker prompt |
| i. **Dogfood — ai-diff-reviewer** | `DailybotHQ/ai-diff-reviewer` → `.agents/skills/ai-diff-reviewer/`. Same non-interactive contract |
| j. Create GitHub Release | Uses `gh release create` with auto-generated notes; the release notes include the addon dogfood commits when those skills moved |

### Failure semantics

| Failure | Behavior |
|---------|----------|
| Version bump script cannot read current version | **Fails** — a corrupt router SKILL.md must be fixed before any release |
| Temp-dir smoke `npx skills add` fails, or installed version ≠ tag | **Fails** — the just-published tag must install cleanly for consumers |
| Any `npx skills add` fails during addon dogfood | **Fails** — a broken upstream tag must never quietly ship inside a release |
| Version-invariant mismatch after addon install (installed `SKILL.md` `version:` != requested tag) | **Fails** — refuses to commit a misrepresented dogfood snapshot |
| Upstream `gh release view` fails for one of the two external skills (rate limit, transient outage) | **Fails** — refuses to cut a release whose dogfood snapshot cannot resolve upstream |
| Head commit already `chore(release):` OR carries `[skip release]` | Whole workflow skips (loop guard) |

### The `--yes` + `-y` non-interactive contract (critical)

Both `npx --yes` (accepts npm's proceed-with-install prompt) AND `-y` (accepts
the `skills` CLI's own "which agent picker?" prompt) are required in the
non-TTY GitHub Actions runner. Historically an upstream `ai-diff-reviewer` bug
(fixed in v1.7.0) caused the second prompt to hang indefinitely without a
timeout — dropping either flag will hang this workflow. The temp smoke step
and both addon dogfood steps carry both flags; the pattern is:

```bash
npx --yes skills add <owner/repo>@<tag> --skill <name> --force -y
```

---

## 2. ci.yml — Frontmatter, shellcheck, bats, smoke, links

| Property | Value |
|----------|-------|
| **Trigger** | `push` to `main`, `pull_request` (any branch), `workflow_dispatch` |
| **Concurrency** | Per-branch / per-PR, cancel in-progress |
| **Permissions** | `contents: read` (default), individual jobs opt in explicitly |

### Jobs

| Job | Runs on | Purpose |
|-----|---------|---------|
| `frontmatter-validation` | ubuntu-latest | `python3 scripts/validate-frontmatter.py` — every `SKILL.md` has `name:` (kebab-case, starts with `deepworkplan`), `version:` (quoted SemVer), no legacy `homepage:` field |
| `shellcheck` | ubuntu-latest | Lints `setup.sh`, `skills/deepworkplan/shared/context.sh`, `skills/deepworkplan/verify/conformance.sh`, any `scripts/*.sh`, and `tests/efficiency/*.sh` (they gate the published instruction-accounting numbers) |
| `context-sh-smoke` | ubuntu-latest | Runs `shared/context.sh` and asserts (1) single-line JSON output; (2) `DWP_AGENT_TOOL=<x>` override honored; (3) `DWP_DIR=<path>` override honored |
| `bats-tests` | ubuntu-latest | **Installs `jsonschema` + `pyyaml` first**, then `bats tests/`, then enforces the skip policy. The Python packages are not optional: without them the schema, lifecycle and Lite-plan cases call `skip "jsonschema not installed"` and the job goes **green having verified none of them** — the exact "missing dependencies are unavailable validation, never a pass" rule in [`docs/TESTING_GUIDE.md`](../../docs/TESTING_GUIDE.md). The gate then (1) reads the TAP plan and fails if fewer than 300 tests were planned, because Bats exits 0 on an empty or fully filtered selection, and (2) fails on **any** `# skip` other than the one allowed environment-dependent case (the installer's no-agents auto-detect branch, unreachable when an agent binary is on PATH) |
| `setup-smoke` | ubuntu-latest AND macos-latest | Matrix run of `setup.sh --host claude` and `setup.sh --host cursor` in a throwaway `HOME` — asserts the pack symlink and **all nine** sub-skill symlinks (`create`, `execute`, `refine`, `resume`, `status`, `verify`, `onboard`, `author`, `upgrade`) land in the expected place. macOS row guards bash 3.2 compatibility |
| `python-floor` | ubuntu-latest | Runs the shipped helpers on **Python 3.9**, the documented floor, with **no** third-party package installed — and asserts `jsonschema` is absent so the stdlib-only path is the one under test. Compiles each helper, then runs the read-only checker over a real fixture plan end to end, then fails if any `__pycache__` remains inside the hash-pinned pack. Nothing verified this claim before: every other job runs 3.11 with `jsonschema` and `pyyaml` present |
| `markdown-links` | ubuntu-latest | `gaurav-nelson/github-action-markdown-link-check@v1` with `.github/markdown-link-check.json` config |

- **`contract-checks`** — installs `jsonschema`, validates every plan fixture's `manifest.json`/`state.json` against the shipped v1 schemas in both directions (a 2.2.0 legacy fixture and a 2.3.0 fixture), runs negative probes (extra top-level or gate field rejected — the schemas are closed; v2 URL rejected; unknown future `spec_version` flagged, never legacy; zero-selection gate evidence rejected; stale/ahead projection rejected; partial materialization reported), then runs `scripts/check-guide-migration.py` (split-guide links, section map, pointer headers) and smoke-runs the instruction-load measurement. Dev-only scripts; the installed pack never depends on them.

### Failure semantics

Any job failure fails the run and blocks merge (`main` branch protection
should require every job). The `setup-smoke` macOS row is the only place
bash 3.2 compat is enforced — losing it means `mapfile` / `${var^^}`
regressions could slip through, and `python-floor` is the only place the
Python 3.9 stdlib-only claim is enforced.

**A green job is not automatically a verified one.** Two failure modes this
workflow now guards against explicitly, because both produced a green run
while verifying nothing: a suite whose required cases all *skipped* for want
of a dependency, and a selection that matched no tests at all. Neither shows
up as a failure — they show up as success. If you add a job that runs a test
suite, give it the same two guards.

---

---

## 3. self-review.yml — grok self-review (label-gated, run-once)

| Property | Value |
|----------|-------|
| **Trigger** | `pull_request` to `main`, `types: [opened, labeled]` only — deliberately no `synchronize` (pushes never re-review) |
| **Concurrency** | Per-PR, cancel in-progress |
| **Permissions** | `contents: read` default; the review job adds `pull-requests: write` to publish the review |
| **Action pin** | `DailybotHQ/ai-diff-reviewer@v3` (the documented moving-major default for workflows) |

### Jobs

| Job | Purpose |
|-----|---------|
| `scope` | Run-once `ready` label gate (case-insensitive): runs only on a `labeled` event whose label is `ready`, or on `opened` when the PR already carries it. Also checks `XAI_API_KEY` presence — when `ready` is applied but the secret is unset, the job records a `::error::` annotation and the review leg skips (honest status, never a fake green) |
| `self-review` | One grok leg: `provider: grok`, `strictness: block-on-critical`, the v3 defaults explicit (`verifier: 'on'`, `budget-profile: auto`), `.review/extension.md` as the extension, `label-gate: ready` + `trigger-mode: label-once` as defense in depth, and the opt-in `skip-review-label: skip-ai-review` emergency bypass |

### Failure semantics

- **No `ready` label (or an unrelated label event)** → `scope` skips everything; the checks are Skipped (grey), never red.
- **`ready` applied, `XAI_API_KEY` unset** → `scope` posts an error annotation and the review leg is Skipped. Add the secret, then toggle the label to run.
- **Review posts a verified `critical` finding** → the check fails under `block-on-critical` (BC-07: only verified criticals gate).
- **Re-run** → remove and re-add the `ready` label. Pushes do not re-trigger.

Not wired as a required merge check. Design source: `DailybotHQ/ai-diff-reviewer` `.github/workflows/self-review.yml`.

---

## Workflow interactions

```
push to main               pull_request
      │                          │
      ▼                          ▼
 auto-release                  ci.yml               self-review.yml
   (release +               (validate +           (scope → review (grok),
    temp smoke +               smoke)              label-gated, run-once)
    addon dogfood)
      │
      ▼
GitHub Release (with dogfood commits in the notes)
```

- `auto-release.yml` and `ci.yml` do **not** depend on each other — a merge
  to `main` triggers both, and `ci.yml` also runs on every PR.
- `self-review.yml` is scoped to PRs only and runs independently of the
  release pipeline.
- The `[skip ci]` marker on release commits and the `[skip release]` marker
  on dogfood commits together prevent auto-release loops without silencing
  `ci.yml` on regular PRs.

---

## External Actions used

| Action | Version | Used in |
|--------|---------|---------|
| `actions/checkout@v4` / `@v5` | v4 / v5 | ci.yml (v4), auto-release.yml (v5), self-review.yml (v4) |
| `actions/setup-python@v5` | v5 | ci.yml (frontmatter-validation) |
| `gaurav-nelson/github-action-markdown-link-check@v1` | v1 | ci.yml (markdown-links) |
| `DailybotHQ/ai-diff-reviewer@v3` | v3 | self-review.yml (review job) |

---

## Secrets used

| Secret | Required by | Where to configure |
|--------|-------------|---------------------|
| `AUTOMATION_GITHUB_TOKEN` | `auto-release.yml` (push to protected `main`) | Repo settings — org's bot user PAT |
| `XAI_API_KEY` | `self-review.yml` (grok provider — CI leg only; the local review never needs it) | Repo Settings > Secrets and variables > Actions |
