# AGENTS.md — Documentation for AI Agents working on this repo

**Purpose:** Single source of truth for any AI coding assistant (Claude Code,
Cursor AI, OpenAI Codex, Gemini CLI, GitHub Copilot, others) that **edits
this repository**. This file is for contributors, not for end users of the
skill.

> [!IMPORTANT]
> **This file is NOT installed.** When users install the skill (via
> `npx skills add`, `openclaw skills install`, or `git clone + setup.sh`),
> only the contents of `skills/deepworkplan/` ship to their machine. Anything
> outside that directory — including this file, `.github/`, `tests/`,
> `scripts/`, `docs/`, `README.md`, `LICENSE`, etc. — is repo-development
> infrastructure that lives only on GitHub and on contributors' machines.

`CLAUDE.md` at the repo root is a symlink to this file so Claude Code reads
the same instructions other agents do.

---

## Detailed Documentation

| Category | Document |
|----------|----------|
| User-facing README | [README.md](README.md) |
| Human contributor guide (narrative companion to this file) | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Design decisions (the *why* behind the layout) | [docs/DESIGN.md](docs/DESIGN.md) |
| Install guide (compare / update / uninstall) | [docs/INSTALLATION.md](docs/INSTALLATION.md) |
| OpenClaw-specific notes | [docs/OPENCLAW.md](docs/OPENCLAW.md) |
| Adding a new sub-skill (step-by-step) | [docs/SUB_SKILL_GUIDE.md](docs/SUB_SKILL_GUIDE.md) |
| Security posture (secrets handling, boundaries, dogfooded review) | [docs/SECURITY.md](docs/SECURITY.md) |
| Security policy (report a vulnerability) | [SECURITY.md](SECURITY.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| Launch / publishing playbook | [PUBLISHING.md](PUBLISHING.md) |
| Router meta-skill (version source of truth) | [skills/deepworkplan/SKILL.md](skills/deepworkplan/SKILL.md) |
| Normative specification (the standard; 5 RFC-2119 docs) | [skills/deepworkplan/spec/](skills/deepworkplan/spec/README.md) |
| `create` sub-skill | [skills/deepworkplan/create/SKILL.md](skills/deepworkplan/create/SKILL.md) |
| `execute` sub-skill | [skills/deepworkplan/execute/SKILL.md](skills/deepworkplan/execute/SKILL.md) |
| `refine` sub-skill | [skills/deepworkplan/refine/SKILL.md](skills/deepworkplan/refine/SKILL.md) |
| `resume` sub-skill | [skills/deepworkplan/resume/SKILL.md](skills/deepworkplan/resume/SKILL.md) |
| `status` sub-skill | [skills/deepworkplan/status/SKILL.md](skills/deepworkplan/status/SKILL.md) |
| `verify` sub-skill (conformance check) | [skills/deepworkplan/verify/SKILL.md](skills/deepworkplan/verify/SKILL.md) |
| `onboard` sub-skill (make any repo AI-first) | [skills/deepworkplan/onboard/SKILL.md](skills/deepworkplan/onboard/SKILL.md) |
| `author` sub-skill (author/update skills, agents, commands) | [skills/deepworkplan/author/SKILL.md](skills/deepworkplan/author/SKILL.md) |
| Methodology guide | [skills/deepworkplan/guide/GUIDE.md](skills/deepworkplan/guide/GUIDE.md) |
| Context detection + `.dwp/` resolution | [skills/deepworkplan/shared/context.sh](skills/deepworkplan/shared/context.sh) |
| `.dwp/` output path convention | [skills/deepworkplan/shared/dwp-paths.md](skills/deepworkplan/shared/dwp-paths.md) |
| Reasoning-over-copy-paste principle | [skills/deepworkplan/shared/adaptation.md](skills/deepworkplan/shared/adaptation.md) |
| Onboarding presets (per-stack) | [skills/deepworkplan/onboard/presets/](skills/deepworkplan/onboard/presets/README.md) |
| Devcontainer addon (opt-in) | [skills/deepworkplan/addons/devcontainer/SKILL.md](skills/deepworkplan/addons/devcontainer/SKILL.md) |
| Dailybot addon (opt-in) | [skills/deepworkplan/addons/dailybot/SKILL.md](skills/deepworkplan/addons/dailybot/SKILL.md) |
| AI Diff Reviewer addon (opt-in) | [skills/deepworkplan/addons/ai-diff-reviewer/SKILL.md](skills/deepworkplan/addons/ai-diff-reviewer/SKILL.md) |
| Dependency Upgrade addon (opt-in) | [skills/deepworkplan/addons/dependency-upgrade/SKILL.md](skills/deepworkplan/addons/dependency-upgrade/SKILL.md) |
| Design System addon (opt-in) | [skills/deepworkplan/addons/design-system/SKILL.md](skills/deepworkplan/addons/design-system/SKILL.md) |
| Workflows reference (`auto-release`, `ci`, `pr-review`) | [.github/docs/WORKFLOWS.md](.github/docs/WORKFLOWS.md) |

## Project Overview

This repository is the **official DeepWorkPlan agent skill pack**, maintained
by [Dailybot](https://www.dailybot.com) and distributed via
[skills.sh](https://skills.sh), [OpenClaw](https://www.openclaw.dev), and
direct git clone. It is a **Markdown-first** skill: it teaches AI coding agents
how to (1) turn any repository AI-first — generating an adapted `AGENTS.md`,
`docs/`, per-module docs, `.agents/`, and the `.claude → .agents` /
`.cursor → .agents` symlinks — and
(2) run structured multi-task **Deep Work Plans** whose outputs land in a
gitignored `.dwp/` directory. The skill follows the
[Open Agent Skills](https://agentskills.io) standard.

**Stack:** Markdown + Bash. No application runtime, no compiled artifacts.
The "code" is the `SKILL.md` prompt files an agent reads at runtime, plus two
small helper scripts: `setup.sh` (the symlink installer at the repo root) and
`skills/deepworkplan/shared/context.sh` (repo/branch/agent + `.dwp/`
resolution). There is **no** CLI, no HTTP API, no auth flow, and no network
calls — unlike the `dailybot` skill pack this repo is modeled on.

## Project Structure

```
deepworkplan-skill/
├── AGENTS.md, CLAUDE.md (symlink)              ← this file (NOT installed)
├── README.md                                   ← public README on GitHub (NOT installed)
├── assets/                                      ← README brand marks (NOT installed)
├── LICENSE, SECURITY.md, CHANGELOG.md          ← repo metadata (NOT installed)
├── PUBLISHING.md                               ← launch playbook (NOT installed)
├── setup.sh                                    ← symlink installer for non-skills.sh users (NOT installed)
├── .gitignore                                  ← repo hygiene (NOT installed)
├── CONTRIBUTING.md                             ← human contributor guide (NOT installed)
├── .vscode_example/                            ← shared editor settings template (NOT installed)
├── .github/
│   ├── workflows/auto-release.yml              ← conventional-commit auto-release + three-way dogfood (NOT installed)
│   ├── workflows/ci.yml                        ← frontmatter + shellcheck + bats + smoke (NOT installed)
│   ├── workflows/pr-review.yml                 ← Cursor-based AI Diff Reviewer, ready-label gated (NOT installed)
│   ├── docs/WORKFLOWS.md                       ← per-workflow reference (Trigger / Jobs / Gate / Failures) (NOT installed)
│   ├── PULL_REQUEST_TEMPLATE.md                ← PR checklist (NOT installed)
│   ├── ISSUE_TEMPLATE/                         ← bug_report + feature_request + config.yml (NOT installed)
│   └── markdown-link-check.json                ← link-check config (NOT installed)
├── .agents/skills/                             ← THREE vendored dogfood copies (NOT installed on end-user machines)
│   ├── deepworkplan/                           ← this repo's OWN skill, vendored via auto-release Step 5
│   ├── dailybot/                               ← DailybotHQ/agent-skill vendored copy
│   └── ai-diff-reviewer/                       ← DailybotHQ/ai-diff-reviewer vendored copy
├── skills-lock.json                            ← pinned versions/hashes for the three vendored skills (NOT installed)
├── .review/extension.md                        ← repo-tailored severity overrides read by both local skill + CI Action
├── scripts/
│   └── validate-frontmatter.py                 ← schema check on every SKILL.md (NOT installed)
├── tests/                                      ← bats-core tests: context-sh.bats, setup-sh.bats (NOT installed)
├── docs/                                       ← contributor docs: DESIGN, INSTALLATION, OPENCLAW, SUB_SKILL_GUIDE (NOT installed)
├── tmp/                                        ← gitignored scratch space (only .gitkeep tracked; NOT installed)
└── skills/deepworkplan/                        ← THE INSTALLED ARTIFACT — only this ships
    ├── SKILL.md                                ← router (version source of truth)
    ├── spec/                                   ← the 5 RFC-2119 normative docs (the standard; ships)
    ├── shared/                                 ← context.sh, dwp-paths.md, adaptation.md
    ├── create/SKILL.md                         ← create a Deep Work Plan
    ├── execute/SKILL.md                        ← execute a plan task-by-task
    ├── refine/SKILL.md                         ← refine a draft / modify a final plan
    ├── resume/SKILL.md                         ← resume an interrupted plan
    ├── status/SKILL.md                         ← report plan status
    ├── verify/SKILL.md                         ← verify repo/plan conformance (read-only)
    ├── onboard/SKILL.md                        ← make any repo AI-first (+ presets/)
    ├── author/SKILL.md                         ← author/update skills, agents, commands (+ templates/)
    ├── guide/GUIDE.md                          ← methodology guide
    ├── examples/                               ← plan + orchestrator templates
    └── addons/                                 ← opt-in addons (each with its own SKILL.md + INTEGRATION.md)
        ├── devcontainer/                       ← compose-based devcontainer scaffolding
        ├── dailybot/                           ← Dailybot standup reporting for plan lifecycle events
        ├── ai-diff-reviewer/                   ← AI Diff Reviewer for PR reviews (defers to upstream skill + Action)
        ├── dependency-upgrade/                 ← safe, batched, revertible dependency upgrades
        └── design-system/                      ← DESIGN.md generator for UI-having repos
```

The hard rule: **anything you put outside `skills/deepworkplan/` is invisible
to the runtime agent**. Use that to keep this repo discoverable and auditable
on GitHub without polluting the skill itself.

## Quick Commands

```bash
# Validate every SKILL.md frontmatter (kebab-case name, quoted SemVer, etc.):
python3 scripts/validate-frontmatter.py

# Lint the shell scripts we ship + the installer:
shellcheck setup.sh skills/deepworkplan/shared/context.sh scripts/*.sh

# Run the bats-core unit tests (context.sh + setup.sh):
bats tests/

# Smoke-test setup.sh against a throwaway HOME (won't touch ~/.claude):
HOME="$(mktemp -d)" ./setup.sh --host claude

# Smoke-test context.sh (should emit single-line JSON):
bash skills/deepworkplan/shared/context.sh
```

## CRITICAL: Mandatory Rules

### 1. English only

All code, comments, documentation, and commit messages MUST be in English.
This is a public open-source repo consumed worldwide.

### 2. The runtime artifact is `skills/deepworkplan/` — keep it pure

If you create a new file or directory, ask: *"does this need to be on the
end user's disk for the skill to work at runtime?"*

- **Yes** → it lives under `skills/deepworkplan/`
- **No** → it lives at the repo root or under `.github/`, `tests/`,
  `scripts/`, `docs/`

Never reach **out of** `skills/deepworkplan/` for anything at runtime — every
runtime file must be self-contained inside that directory because that's
what skills.sh ships. The frontmatter validator, the CI workflow, and the
auto-release workflow all depend on this boundary holding.

### 3. SKILL.md frontmatter conventions

Every `SKILL.md` MUST have YAML frontmatter with at least:

```yaml
---
name: deepworkplan-<thing>       # kebab-case, never snake_case (deepworkplan_thing) or camelCase
description: <one paragraph>     # used by skills.sh + every agent harness for relevance scoring
version: "2.0.0"                 # SemVer, quoted to keep it a string
documentation_url: https://deepworkplan.com  # NEVER use `homepage:` (legacy, dangerous)
user-invocable: true|false       # whether `/<name>` becomes a slash command
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
---
```

The router skill is named `deepworkplan`; sub-skills are `deepworkplan-create`,
`deepworkplan-execute`, `deepworkplan-refine`, `deepworkplan-resume`,
`deepworkplan-status`, `deepworkplan-onboard`, and the addon is
`deepworkplan-addon-devcontainer`. The `documentation_url` field replaces the
legacy `homepage` because some agent harnesses interpret `homepage` as a
re-fetch source. `validate-frontmatter.py` fails CI if any SKILL.md uses the
old key, is not kebab-case, does not start with `deepworkplan`, or has an
unquoted `version`.

### 4. Versioning is automatic — write good commits

You do **not** edit `version:` fields, `CHANGELOG.md`, git tags, or the
vendored dogfood copy at `.agents/skills/deepworkplan/` by hand.
The `auto-release.yml` workflow runs on every merge to `main` and:

1. Reads the current version from the **router** `skills/deepworkplan/SKILL.md`
 frontmatter (single source of truth).
2. Looks at commits merged since the last `vX.Y.Z` tag.
3. Decides the bump level:
 - `feat(scope)!:` or `BREAKING CHANGE:` in body → **MAJOR**
 - `feat(scope):` → **MINOR**
 - everything else (`fix:`, `chore:`, no prefix, etc.) → **PATCH**
4. Bumps `version:` in **all** SKILL.md files in sync (router + six sub-skills
 + addon), prepends a section to `CHANGELOG.md`, commits as
 `chore(release): X.Y.Z [skip ci]`, tags `vX.Y.Z`, and pushes.
5. **Dogfoods the just-published tag** — fetches
 `DailybotHQ/deepworkplan-skill@vX.Y.Z` via `npx skills add` into
 `.agents/skills/deepworkplan/`, verifies the vendored `SKILL.md` version
 matches, and commits any diff (plus `skills-lock.json`) as
 `chore(release): dogfood vendored deepworkplan to vX.Y.Z [skip release]`.
 This doubles as a live smoke test — if the release doesn't install
 cleanly for consumers, the workflow fails HERE. Contributors never
 hand-refresh the vendored copy anymore.
6. Creates a GitHub Release with auto-generated notes and the SHA256SUMS
 provenance artifact attached.

What this means for you:

- Write meaningful commit messages with the right `<type>(<scope>):` prefix.
  The workflow reads them.
- A bug-fix-only PR → PATCH automatically. A new sub-skill or addon → MINOR
  (use `feat(...):`). A removed slash command, renamed `name:`, or changed
  `.dwp/` convention → MAJOR (use `feat(...)!:` and explain in the PR body).
- **Don't touch `CHANGELOG.md` or `version:` fields manually.** The bot owns
  them. If you do, the next auto-release overwrites the version line and
  prepends a duplicate changelog section.
- Bump-level guide for this skill specifically:
  - **MAJOR** = breaking the public surface (see rule 5).
  - **MINOR** = additive (new sub-skill, new addon, new preset, new flag).
  - **PATCH** = bug fixes, docs, internal refactors, CI changes.

### 5. Don't break the public surface

These are public contracts other systems depend on. Changing them is a
breaking change that requires a MAJOR version bump and a migration note in
`CHANGELOG.md`:

- Skill `name` fields in frontmatter (skills.sh registry references them).
- The six `/deepworkplan-*` slash commands (`create`, `execute`, `refine`,
  `resume`, `status`, `onboard`).
- The `.dwp/` output convention (`.dwp/plans/`, `.dwp/drafts/`) and the
  `DWP_DIR` / `DWP_AGENT_TOOL` env-var overrides read by `shared/context.sh`.
- `setup.sh` flags (`--host`, `--help`) and the resulting symlink names.

### 6. `set -euo pipefail` everywhere + bash 3.2 compatibility

macOS still ships bash 3.2 by default. `setup.sh` and
`skills/deepworkplan/shared/context.sh` must run on bash 3.2:

- ❌ No `mapfile` / `readarray` (bash 4+)
- ❌ No associative arrays `declare -A` (bash 4+)
- ❌ No `${var^^}` / `${var,,}` case conversion (bash 4+)
- ✅ Use `while IFS= read -r line; do ...; done < <(cmd)` instead of `mapfile`
- ✅ Use `tr '[:lower:]' '[:upper:]'` for case conversion

All shell scripts start with `#!/usr/bin/env bash` then `set -euo pipefail`.
CI runs the `setup.sh` smoke job on both `ubuntu-latest` and `macos-latest`
to enforce bash 3.2 compatibility.

## Commit Message Format (MANDATORY)

```
<type>(<scope>): <short description>

<body — Summary, motivation, what changed, risks>

Co-Authored-By: <agent name + version> <noreply@anthropic.com>
```

**Types:** `feat` (new behavior), `fix` (bug fix), `docs` (docs only),
`chore` (repo maintenance), `test` (adding tests), `ci` (CI config),
`refactor` (no user-visible change).

**Scopes:** `skill` (general pack/router), `create` / `execute` / `refine` /
`resume` / `status` / `onboard` (specific sub-skill), `addon` (an addon under
`addons/`), `shared` (context.sh, dwp-paths.md, adaptation.md), `setup`
(setup.sh), `ci` (.github/), `docs` (docs/, README, guide), `release`
(versioning, CHANGELOG).

Examples:

```
feat(onboard): reason about monorepo workspaces when generating per-module docs
fix(execute): handle a plan with zero remaining tasks gracefully
docs(skill): polish the router SKILL.md to read well on the skills.sh listing
feat(create)!: replace the two-step draft flow with a single-step create
```

## Pre-Commit Checklist

- [ ] All changes in English
- [ ] `python3 scripts/validate-frontmatter.py` passes
- [ ] `shellcheck setup.sh skills/deepworkplan/shared/context.sh scripts/*.sh` clean
- [ ] `bats tests/` passes
- [ ] Ship boundary intact — no runtime file added outside `skills/deepworkplan/`,
      no dev-infra file added inside it
- [ ] No `name: deepworkplan_*` (snake_case) introduced
- [ ] No `homepage:` (legacy field) introduced; `version:` stays quoted
- [ ] No bash 4+ idioms (`mapfile`, `declare -A`, `${var^^}`) introduced
- [ ] Public surface preserved (slash-command names, `.dwp/` convention,
      `setup.sh` flags, skill `name` fields)
- [ ] Did NOT hand-edit `version:` or `CHANGELOG.md` (the bot owns them)
- [ ] `setup.sh` tested with at least `./setup.sh --host claude`
- [ ] Commit message follows `<type>(<scope>): description` format

## Common Mistakes

### DON'T

1. Put runtime files outside `skills/deepworkplan/` — they won't ship to users
2. Use `name: deepworkplan_create` (snake_case) — must be `deepworkplan-create` (kebab)
3. Use `homepage:` in frontmatter — use `documentation_url:`
4. Hand-edit `version:` fields or `CHANGELOG.md` — the auto-release bot owns them
5. Use bash 4+ features (`mapfile`, associative arrays, `${var^^}`) in any script — they break on macOS bash 3.2
6. Rename a slash command or change the `.dwp/` convention without a MAJOR bump
7. Add a new sub-skill or addon folder without giving it its own `SKILL.md` with full frontmatter

### DO

1. Keep dev infrastructure (`.github/`, `tests/`, `scripts/`, `docs/`, this file) at the repo root
2. Use kebab-case `deepworkplan-*` for `name:` in frontmatter
3. Run `python3 scripts/validate-frontmatter.py` and `shellcheck setup.sh skills/deepworkplan/shared/context.sh` before pushing
4. Write conventional commits so the auto-release picks the right bump level
5. Test `setup.sh` manually with `--host claude` after touching it

## Shared Agent Coordination

Multiple AI agents may work on this repo simultaneously. They all read this
`AGENTS.md`:

- **Claude Code** reads `CLAUDE.md` (symlink to `AGENTS.md`)
- **Cursor AI** reads `AGENTS.md`
- **OpenAI Codex** reads `AGENTS.md`
- **Gemini CLI** reads `AGENTS.md`
- **GitHub Copilot** reads `AGENTS.md`

`AGENTS.md` is the canonical source — you don't need to mirror to per-agent files.

## Vendored agent skills — three dogfood copies under `.agents/skills/`

This repo now vendors **three** agent skills under `.agents/skills/`, all
tracked in git and pinned via [`skills-lock.json`](skills-lock.json). They are
the exact same artifacts a downstream consumer would install via
`npx skills add`, kept in-repo so any AI agent that clones this repo — or that
runs `.agents/`-aware tooling on it — gets the current snapshot of the entire
toolchain the DWP methodology recommends:

| Vendored skill | Upstream | Purpose in this repo |
|----------------|----------|----------------------|
| `.agents/skills/deepworkplan/` | [`DailybotHQ/deepworkplan-skill`](https://github.com/DailybotHQ/deepworkplan-skill) (this repo) | **Self-dogfood** — proves each release installs cleanly and gives contributors the DWP methodology while working here |
| `.agents/skills/dailybot/` | [`DailybotHQ/agent-skill`](https://github.com/DailybotHQ/agent-skill) | Powers Dailybot standup reporting for plan lifecycle events (see the Dailybot addon) |
| `.agents/skills/ai-diff-reviewer/` | [`DailybotHQ/ai-diff-reviewer`](https://github.com/DailybotHQ/ai-diff-reviewer) | Powers the local pre-push code review AND the `pr-review.yml` CI Action (same `prompt.md`) |

**How they stay fresh.** [`.github/workflows/auto-release.yml`](.github/workflows/auto-release.yml)
runs on every merge to `main` and, after cutting the release for this repo,
resolves the latest published tags of `agent-skill` and `ai-diff-reviewer`
(via `gh release view`), compares to the vendored `SKILL.md` `version:`, and
if either moved runs:

```bash
npx --yes skills add <repo>@<tag> --skill <name> --force -y
```

Both `--yes` (npm's proceed prompt) AND `-y` (the skills CLI's agent-picker
prompt) are required in a non-TTY runner — dropping either hangs the workflow
indefinitely. After each install the workflow asserts that the vendored
`SKILL.md`'s `version:` equals the requested tag; a mismatch fails the release.
If any file changes, the workflow commits
`chore(release): dogfood vendored <skill> to v<tag> [skip release]` and
pushes. The `[skip release]` marker prevents an infinite auto-release loop.

**Do not hand-edit files under `.agents/skills/deepworkplan/`, `.agents/skills/dailybot/`,
or `.agents/skills/ai-diff-reviewer/`.** The next release cut will overwrite
your changes. Contribute upstream first, land a release there, then the
`auto-release` job here will refresh the vendored copy on its next run.

## PR review workflow — Cursor-based, `ready`-label gated

This repo ships an AI code-review workflow at
[`.github/workflows/pr-review.yml`](.github/workflows/pr-review.yml) powered
by [`DailybotHQ/ai-diff-reviewer`](https://github.com/marketplace/actions/ai-diff-reviewer)
(GitHub Marketplace listing: **"AI Diff Reviewer"**). It runs on every
`pull_request` to `main` that carries the `ready` label AND is opened by a
write-tier author (`OWNER` / `MEMBER` / `COLLABORATOR`), single Cursor
provider (`model: auto`), and applies the `pr-reviewed` label on success.
`critical` findings block the merge; `warning` and `info` findings are
reported inline but non-blocking.

**How to use it.**

1. Open a PR against `main` as normal.
2. Apply the `ready` label. The workflow triggers on the label event.
3. If the review passes, `pr-reviewed` is applied automatically and the
   `AI review gate` check turns green.
4. If a `critical` finding is posted, address it (edit, push a fix, or reply
   inline if you disagree), then toggle the `ready` label off and on to
   re-run — pushes to the branch alone do NOT re-review.

**Branch-protection integration.** Mark ONLY the stable-named `AI review gate`
job as a required status check in Settings > Branches > Protection rules.
GitHub treats `skipped` required checks as passing, so a PR without `ready`
becomes mergeable without a review — pair this with a separate rule that
enforces `ready` on every PR if that's the workflow you want.

**Setup: `CURSOR_API_KEY` secret.**

1. Get a Cursor subscription key from Cursor's dashboard (unlimited reviews on Pro).
2. Repo Settings > Secrets and variables > Actions > **New repository secret**.
3. Name: exactly `CURSOR_API_KEY`. Value: the key. Save.
4. Without the secret, the `AI review gate` job fails loud with an actionable
   message ("`CURSOR_API_KEY` is not configured on this repo").

**Local ↔ CI ↔ apply-review three-moment loop.** The same
[`ai-diff-reviewer`](https://skills.sh/DailybotHQ/ai-diff-reviewer) skill
vendored at `.agents/skills/ai-diff-reviewer/` powers both the local
pre-push review and the CI pass — the skill's `prompt.md` is byte-identical
to the CI Action's shipped `prompts/default.md` at the same tag (enforced
by upstream CI). Three moments in a maintainer's day:

1. **Local pre-push review** (optional) — run the `ai-diff-reviewer` skill's
   parent default flow (`/ai-diff-reviewer` or "Review my current branch")
   before pushing. Same findings CI will produce, minus the round-trip.
2. **CI review** — push, apply `ready`, this workflow runs.
3. **Post-CI walkthrough** (optional) — invoke the skill's `apply-review`
   sub-skill to walk through the CI-posted findings per-finding (apply /
   defer / skip) with explicit consent. Read-only by default; edits require
   per-finding yes; never commits or pushes.

**Shared override file: [`.review/extension.md`](.review/extension.md).**
Repo-tailored severity overrides + "don't comment on" scopes + repo-specific
context (the runtime boundary, the auto-release ownership, the addon
contract, the vendor-neutrality invariant). The local skill and the CI
Action read the SAME file via `prompt-extension-file:` — one source of
truth for what maps to `critical` vs `warning` vs `info` in this codebase.

## The `ai-diff-reviewer` addon (opt-in, DWP-adjacent)

Living alongside the vendored skill above, this repo also ships an
**opt-in DWP addon** at
[`skills/deepworkplan/addons/ai-diff-reviewer/SKILL.md`](skills/deepworkplan/addons/ai-diff-reviewer/SKILL.md).
It is the DWP-side counterpart to the raw skill: while the vendored skill at
`.agents/skills/ai-diff-reviewer/` is a general-purpose reviewer that any
repo can use, the **addon** is what onboards `ai-diff-reviewer` into a
concrete plan.

**Two adoption flows** (documented in the addon's SKILL.md + INTEGRATION.md):

- **Flow A — local-only.** Vendor the skill under `.agents/skills/`,
  bootstrap `.review/extension.md` (required for SR detection), and run
  the local review pre-push. No CI Action, no GitHub secret.
- **Flow B — dual-surface.** Vendor the skill AND install `pr-review.yml`.
  Local ↔ CI parity is guaranteed because both read the same `prompt.md`
  and the same `.review/extension.md`.

**Five sub-skills** the addon defers to (all live in the upstream
`ai-diff-reviewer` repo — the DWP addon does NOT re-implement them):

- **parent default flow** — run a local review on the current branch.
- **`generate-extension`** — draft a repo-specific `.review/extension.md`.
- **`setup`** — install `pr-review.yml` (Flow B). Reference manual for
  every `action.yml` input.
- **`open-pr`** — draft a PR title + body from the current diff.
- **`apply-review`** — read CI reviews on a PR and walk through findings
  per-finding (apply / defer / skip). Read-only by default. Optional
  Flow B companion.

**How the addon augments a DWP plan.** When present, DWP's
[`deepworkplan-create`](skills/deepworkplan/create/SKILL.md) and
[`deepworkplan-execute`](skills/deepworkplan/execute/SKILL.md) sub-skills
notice the addon and **augment the mandatory Security Review task** with an
`ai-diff-reviewer` local pass whose findings feed into
`.dwp/plans/<plan>/analysis_results/SECURITY_REVIEW.md`. This is additive:
the mandatory-final-task order is unchanged (Security Review → Skills &
Agents Discovery → Executive Report), the Security Review task itself is
not replaced, and the addon is never required. Soft-fail applies only when
the local pass cannot be *invoked* (missing skill/extension or invocation
error); `critical` findings from a completed pass still follow the existing
Security Review contract. When the addon is absent, the plan runs exactly
as before.

---

## When in Doubt

- **Behavior of an end-user-facing flow** → read the relevant SKILL.md inside
  `skills/deepworkplan/`
- **An install / packaging decision** → consult the
  [skills.sh CLI README](https://github.com/vercel-labs/skills) and the
  [Open Agent Skills spec](https://agentskills.io)
- **A breaking-change decision** → bump major version (via `feat(...)!:`),
  document the migration path in `CHANGELOG.md`, mention in the PR description

This repository is small but plays in a public ecosystem. Lean toward caution
on behavior changes — your work is auditable by every agent that reads our
SKILL.md and by every team that evaluates the skill.
