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
| `shellcheck` | ubuntu-latest | Lints `setup.sh`, `skills/deepworkplan/shared/context.sh`, `skills/deepworkplan/verify/conformance.sh`, and any `scripts/*.sh` |
| `context-sh-smoke` | ubuntu-latest | Runs `shared/context.sh` and asserts (1) single-line JSON output; (2) `DWP_AGENT_TOOL=<x>` override honored; (3) `DWP_DIR=<path>` override honored |
| `bats-tests` | ubuntu-latest | `apt-get install bats` + `bats tests/` — the bats-core unit tests for `context.sh` and `setup.sh` |
| `setup-smoke` | ubuntu-latest AND macos-latest | Matrix run of `setup.sh --host claude` and `setup.sh --host cursor` in a throwaway `HOME` — asserts the pack symlink and every sub-skill symlink land in the expected place. macOS row guards bash 3.2 compatibility |
| `markdown-links` | ubuntu-latest | `gaurav-nelson/github-action-markdown-link-check@v1` with `.github/markdown-link-check.json` config |

- **`contract-checks`** — installs `jsonschema`, validates every plan fixture's `manifest.json`/`state.json` against the shipped v1 schemas in both directions (a 2.2.0 legacy fixture and a 2.3.0 fixture), runs negative probes (extra top-level or gate field rejected — the schemas are closed; v2 URL rejected; unknown future `spec_version` flagged, never legacy; zero-selection gate evidence rejected; stale/ahead projection rejected; partial materialization reported), then runs `scripts/check-guide-migration.py` (split-guide links, section map, pointer headers) and smoke-runs the instruction-load measurement. Dev-only scripts; the installed pack never depends on them.

### Failure semantics

Any job failure fails the run and blocks merge (`main` branch protection
should require all six jobs). The `setup-smoke` macOS row is the only
place bash 3.2 compat is enforced — losing it means `mapfile` / `${var^^}`
regressions could slip through.

---

---

## Workflow interactions

```
push to main               pull_request
      │                          │
      ▼                          ▼
 auto-release                  ci.yml               pr-review.yml
   (release +               (validate +           (scope → labels-bootstrap
    temp smoke +               smoke)              → review → gate)
    addon dogfood)
      │
      ▼
GitHub Release (with dogfood commits in the notes)
```

- `auto-release.yml` and `ci.yml` do **not** depend on each other — a merge
  to `main` triggers both, and `ci.yml` also runs on every PR.
- `pr-review.yml` is scoped to PRs only and runs independently of the
  release pipeline.
- The `[skip ci]` marker on release commits and the `[skip release]` marker
  on dogfood commits together prevent auto-release loops without silencing
  `ci.yml` on regular PRs.

---

## External Actions used

| Action | Version | Used in |
|--------|---------|---------|
| `actions/checkout@v4` / `@v5` | v4 / v5 | ci.yml (v4), auto-release.yml (v5), pr-review.yml (v4) |
| `actions/setup-python@v5` | v5 | ci.yml (frontmatter-validation) |
| `gaurav-nelson/github-action-markdown-link-check@v1` | v1 | ci.yml (markdown-links) |
| `DailybotHQ/ai-diff-reviewer@v2` | v2 | pr-review.yml (review job) |

---

## Secrets used

| Secret | Required by | Where to configure |
|--------|-------------|---------------------|
| `AUTOMATION_GITHUB_TOKEN` | `auto-release.yml` (push to protected `main`) | Repo settings — org's bot user PAT |
| `CURSOR_API_KEY` | `pr-review.yml` (Cursor provider) | Repo Settings > Secrets and variables > Actions |
