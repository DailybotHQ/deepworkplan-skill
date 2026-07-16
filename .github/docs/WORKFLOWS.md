# GitHub Workflows Reference — `deepworkplan-skill`

Per-workflow reference for the three GitHub Actions workflows that live in
[`.github/workflows/`](../workflows/). Each section documents the trigger,
jobs, gate semantics, and failure modes so a maintainer (or an AI agent
piloting this repo) can reason about why a job did or didn't run.

| Workflow | File | Purpose |
|----------|------|---------|
| Auto-release | [`auto-release.yml`](../workflows/auto-release.yml) | Conventional-commit-driven release + three-way vendored-skill dogfood |
| CI | [`ci.yml`](../workflows/ci.yml) | Frontmatter validation, shellcheck, bats tests, `setup.sh`/`context.sh` smoke, markdown link check |
| PR review | [`pr-review.yml`](../workflows/pr-review.yml) | AI-driven pull request code review via Cursor, `ready`-label gated |

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
| g. **Dogfood — self (`deepworkplan`)** | Fetches the just-published tag via `npx --yes skills add DailybotHQ/deepworkplan-skill@vX.Y.Z --skill deepworkplan --force -y` into `.agents/skills/deepworkplan/`. Verifies `SKILL.md` `version:` equals the requested tag. Commits any diff as `chore(release): dogfood vendored deepworkplan to vX.Y.Z [skip release]`. Doubles as a live smoke test — if the release doesn't install cleanly for consumers, this step fails |
| h. **Dogfood — dailybot** | Same pattern for `DailybotHQ/agent-skill` → `.agents/skills/dailybot/`. Only runs if the upstream tag moved. Non-interactive contract (`--yes` + `-y`) is mandatory — dropping either flag hangs the workflow indefinitely on the CLI's agent-picker prompt |
| i. **Dogfood — ai-diff-reviewer** | Same pattern for `DailybotHQ/ai-diff-reviewer` → `.agents/skills/ai-diff-reviewer/`. Same non-interactive contract |
| j. Create GitHub Release | Uses `gh release create` with auto-generated notes; the release notes include the dogfood commits, so downstream consumers see exactly which skills refreshed with this release |

### Failure semantics

| Failure | Behavior |
|---------|----------|
| Version bump script cannot read current version | **Fails** — a corrupt router SKILL.md must be fixed before any release |
| Any `npx skills add` fails during dogfood | **Fails** — a broken upstream tag must never quietly ship inside a release |
| Version-invariant mismatch after install (installed `SKILL.md` `version:` != requested tag) | **Fails** — refuses to commit a misrepresented dogfood snapshot |
| Upstream `gh release view` fails for one of the two external skills (rate limit, transient outage) | **Fails** — refuses to cut a release whose dogfood snapshot cannot resolve upstream |
| Head commit already `chore(release):` OR carries `[skip release]` | Whole workflow skips (loop guard) |

### The `--yes` + `-y` non-interactive contract (critical)

Both `npx --yes` (accepts npm's proceed-with-install prompt) AND `-y` (accepts
the `skills` CLI's own "which agent picker?" prompt) are required in the
non-TTY GitHub Actions runner. Historically an upstream `ai-diff-reviewer` bug
(fixed in v1.7.0) caused the second prompt to hang indefinitely without a
timeout — dropping either flag will hang this workflow. The three dogfood
steps carry both flags; the pattern is:

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

### Failure semantics

Any job failure fails the run and blocks merge (`main` branch protection
should require all six jobs). The `setup-smoke` macOS row is the only
place bash 3.2 compat is enforced — losing it means `mapfile` / `${var^^}`
regressions could slip through.

---

## 3. pr-review.yml — AI Code Review on Pull Requests

| Property | Value |
|----------|-------|
| **Trigger** | `pull_request` to `main`, types: `opened, labeled` (NOT `synchronize`) |
| **Concurrency** | `pr-review-${{ pull_request.number }}`, cancel in-progress |
| **Permissions** | `contents: read`, `pull-requests: write` at workflow level |
| **Powered by** | [`DailybotHQ/ai-diff-reviewer@v2`](https://github.com/marketplace/actions/ai-diff-reviewer) (Marketplace listing: "AI Diff Reviewer", skill + Action v2) |

### Jobs

| Job | Depends on | Purpose |
|-----|------------|---------|
| `scope` | — | Three-tier gate: (1) `author-association ∈ {OWNER, MEMBER, COLLABORATOR}` (cheapest, payload-based, not spoofable); (2) `ready` label present on the PR (case-insensitive); (3) `CURSOR_API_KEY` secret configured. Also re-runs when `skip-ai-review` is labeled while `ready` is already present. Emits `should_run` + `empty_reason` outputs consumed by downstream jobs |
| `labels-bootstrap` | `scope` | Idempotent `gh label create` for `ready` (green), `pr-reviewed` (blue), and `skip-ai-review` (red — emergency bypass). Only runs when `should_run == 'true'`. |
| `review` | `scope, labels-bootstrap` | Checks out with `fetch-depth: 0` and `persist-credentials: false` (Cursor CLI has broad local access — a persisted token on disk is an exfil surface). Invokes `DailybotHQ/ai-diff-reviewer@v2` with `provider: cursor`, `model: auto`, `label-gate: ready`, `author-association: OWNER,MEMBER,COLLABORATOR`, `applied-label: pr-reviewed`, `skip-review-label: skip-ai-review`, `strictness: block-on-critical`, `prompt-extension-file: .review/extension.md`, `max-inline-comments: 15`. Applying `skip-ai-review` while `ready` is present re-runs the job and short-circuits the LLM. |
| `gate` | `scope, review` | Stable-named `'AI review gate'`. This is the ONLY job to mark as required in branch protection |

### Gate semantics

The `gate` job runs `if: always() && needs.scope.outputs.empty_reason != 'no-ready-label' && needs.scope.outputs.empty_reason != 'author-association'`, which produces the following outcomes:

| `empty_reason` | `review.result` | `gate` outcome | Branch-protection effect |
|----------------|-----------------|----------------|--------------------------|
| `no-ready-label` | (skipped) | Skipped | Required check counts as passing — PRs without `ready` are mergeable |
| `author-association` | (skipped) | Skipped | Same — external-contributor forks never trigger a review |
| `no-provider-secret` | (skipped) | **Failed** | Fails with an actionable message; unblock by setting `CURSOR_API_KEY` |
| `` (empty) | `success` | **Passed** | Gate green |
| `` (empty) | `failure` / `cancelled` | **Failed** | Reviewer signaled a blocking finding OR the review job errored |

### Failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Gate fails with "CURSOR_API_KEY is not configured" | Missing secret | Add it in Settings > Secrets and variables > Actions |
| Gate fails with "AI review did not pass" | `critical` finding in the review | Address findings, toggle `ready` label off + on to re-run |
| No review appears; gate is skipped | PR missing `ready` label OR author is external contributor | Apply `ready` (if maintainer); external forks are intentionally not reviewed |
| Review posts findings but gate passes | Findings are `warning` / `info` only | Working as designed — non-blocking findings are reported for context, not gated |

### Trigger discipline

- `pull_request` only, `types: [opened, labeled]` — NOT `synchronize`. Pushes to the PR do **not** re-review; toggle the `ready` label off and on to force a re-run.
- Concurrency keyed on PR number with `cancel-in-progress: true`, so a rapid label-toggle sequence resolves to the latest state.

### Shared with the local `ai-diff-reviewer` skill

The vendored skill at `.agents/skills/ai-diff-reviewer/` reads the SAME
`.review/extension.md` this workflow reads via `prompt-extension-file:`. The
upstream skill's `prompt.md` is byte-identical to the CI Action's
`prompts/default.md` at the same tag (enforced by upstream CI's "Skills —
prompt-sync invariant" job). Consequence: running the local skill on a
branch before pushing yields the same findings CI will produce.

**Post-CI walkthrough.** After this workflow posts its review, developers
can invoke the vendored skill's `apply-review` sub-skill locally to walk
through CI findings per-finding (apply / defer / skip) with explicit
consent. Read-only by default; edits require per-finding yes; never commits
or pushes.

---

## Workflow interactions

```
push to main               pull_request
      │                          │
      ▼                          ▼
 auto-release                  ci.yml               pr-review.yml
   (release +               (validate +           (scope → labels-bootstrap
    three-way                  smoke)              → review → gate)
    dogfood)
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
