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

## Working principles

Work with autonomy, ownership, and sound judgment. Pursue excellence through
correctness, clarity, simplicity, and verified completion.

- **Own the outcome.** Carry authorized work through investigation, execution,
  and appropriate validation. Continue until the requested outcome is complete
  or a concrete blocker prevents further progress.
- **Be resourceful before asking.** Inspect available code, documentation,
  tools, and prior decisions. Resolve questions you can answer through
  reasonable investigation instead of transferring that work to the user.
- **Make routine decisions independently.** Choose sensible approaches within
  the authorized scope. State consequential assumptions. Avoid confirmation
  requests for routine steps or actions already authorized.
- **Ask when judgment or authorization is missing.** Consult the user when
  essential information is unavailable, a material decision cannot be inferred
  reliably, or an action requires approval not already granted. Bring the
  investigation, relevant options, and your recommendation.
- **Make approvals concrete.** Complete authorized preparation before asking
  for approval. Present a reviewable result and identify the action requiring
  approval and why it requires it.
- **Work through obstacles.** Investigate failures and attempt reasonable
  recovery within scope. Continue independent authorized work when possible.
  Respect applicable stop conditions; escalate when progress requires user
  input or an external change.
- **Respect intent and scope.** Analysis requests remain analysis. Propose
  broader improvements separately unless already authorized. Preserve the
  user's existing work, decisions, and repository-specific approval rules.
- **Apply proportionate rigor.** Address underlying causes and favor
  maintainable solutions. Match investigation, validation, and polish to the
  task's impact. Avoid unnecessary complexity and unrelated changes.
- **Communicate directly and precisely.** Lead with the result or decision.
  Explain consequential tradeoffs concisely. Distinguish verified facts,
  assumptions, and unresolved uncertainty.
- **Verify before declaring completion.** Review the result against the
  request, perform appropriate checks, and fix issues within scope. Report
  what was validated and any remaining limitations. Never claim actions,
  checks, or outcomes that did not occur.

---

## Detailed Documentation

| Category | Document |
|----------|----------|
| User-facing README | [README.md](README.md) |
| Human contributor guide (narrative companion to this file) | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Validation commands and source-to-test mapping | [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) |
| Design decisions (the *why* behind the layout) | [docs/DESIGN.md](docs/DESIGN.md) |
| Install guide (compare / update / uninstall) | [docs/INSTALLATION.md](docs/INSTALLATION.md) |
| Installation + agent support matrix (what is actually tested) | [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) |
| Reproducing the evaluation pack (what is measured, and what is not) | [docs/EVALUATION.md](docs/EVALUATION.md) |
| Efficiency evidence, claims and their limits | [docs/evaluations/token-efficiency.md](docs/evaluations/token-efficiency.md) |
| v5 reliability evidence: guarantees, guard cost, instruction accounting | [docs/evaluations/v5-reliability.md](docs/evaluations/v5-reliability.md) |
| Cross-agent handoff trial (Claude Code ↔ Codex, both directions) | [docs/evaluations/cross-agent-handoff.md](docs/evaluations/cross-agent-handoff.md) |
| Upgrading an existing repository (adoption pilot) | [docs/evaluations/adoption-pilot.md](docs/evaluations/adoption-pilot.md) |
| Working-principles authoring and reconciliation trial | [docs/evaluations/working-principles.md](docs/evaluations/working-principles.md) |
| Per-preset onboarding coverage | [docs/PRESET_TESTING_MATRIX.md](docs/PRESET_TESTING_MATRIX.md) |
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
| Runtime troubleshooting decision path (read only when something is wrong) | [skills/deepworkplan/shared/troubleshooting.md](skills/deepworkplan/shared/troubleshooting.md) |
| Onboarding presets (per-stack) | [skills/deepworkplan/onboard/presets/](skills/deepworkplan/onboard/presets/README.md) |
| Devcontainer addon (opt-in) | [skills/deepworkplan/addons/devcontainer/SKILL.md](skills/deepworkplan/addons/devcontainer/SKILL.md) |
| Dailybot addon (opt-in) | [skills/deepworkplan/addons/dailybot/SKILL.md](skills/deepworkplan/addons/dailybot/SKILL.md) |
| AI Diff Reviewer addon (required local review, optional CI surface) | [skills/deepworkplan/addons/ai-diff-reviewer/SKILL.md](skills/deepworkplan/addons/ai-diff-reviewer/SKILL.md) |
| Dependency Upgrade addon (opt-in) | [skills/deepworkplan/addons/dependency-upgrade/SKILL.md](skills/deepworkplan/addons/dependency-upgrade/SKILL.md) |
| Design System addon (opt-in) | [skills/deepworkplan/addons/design-system/SKILL.md](skills/deepworkplan/addons/design-system/SKILL.md) |
| Workflows reference (`auto-release`, `ci`, `self-review`) | [.github/docs/WORKFLOWS.md](.github/docs/WORKFLOWS.md) |

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
│   ├── workflows/auto-release.yml              ← conventional-commit auto-release + addon dogfood (NOT installed)
│   ├── workflows/ci.yml                        ← frontmatter + shellcheck + bats + smoke (NOT installed)
│   ├── docs/WORKFLOWS.md                       ← per-workflow reference (Trigger / Jobs / Gate / Failures) (NOT installed)
│   ├── PULL_REQUEST_TEMPLATE.md                ← PR checklist (NOT installed)
│   ├── ISSUE_TEMPLATE/                         ← bug_report + feature_request + config.yml (NOT installed)
│   └── markdown-link-check.json                ← link-check config (NOT installed)
├── .agents/skills/                             ← THREE vendored dogfood copies (NOT installed on end-user machines)
│   ├── deepworkplan/                           ← byte-identical dogfood copy of this skill (sync via scripts/refresh-dogfood-skill.sh; NOT auto-overwritten on release)
│   ├── dailybot/                               ← DailybotHQ/agent-skill — auto-refreshed on release
│   └── ai-diff-reviewer/                       ← DailybotHQ/ai-diff-reviewer — auto-refreshed on release
├── skills-lock.json                            ← pinned versions/hashes for the vendored skills (NOT installed)
├── .review/extension.md                        ← repo-tailored severity overrides read by both local skill + CI Action
├── scripts/
│   └── validate-frontmatter.py                 ← schema check on every SKILL.md (NOT installed)
├── tests/                                      ← bats-core tests: context-sh.bats, setup-sh.bats (NOT installed)
├── docs/                                       ← contributor docs: DESIGN, INSTALLATION, OPENCLAW, SUB_SKILL_GUIDE (NOT installed)
├── tmp/                                        ← gitignored scratch space (only .gitkeep tracked; NOT installed)
└── skills/deepworkplan/                        ← THE INSTALLED ARTIFACT — only this ships
    ├── SKILL.md                                ← router (version source of truth)
    ├── spec/                                   ← the 5 RFC-2119 normative docs (the standard; ships)
    ├── shared/                                 ← context.sh, dwp-paths.md, adaptation.md, troubleshooting.md, install-verification.md, update-state.py, state_contract.py, finalize_plan.py
    ├── create/SKILL.md                         ← create a Deep Work Plan
    ├── execute/SKILL.md                        ← execute a plan task-by-task
    ├── refine/SKILL.md                         ← modify a plan / promote Lite to Full
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

You do **not** edit `version:` fields, `CHANGELOG.md`, or git tags by hand.
The `auto-release.yml` workflow runs on every merge to `main` and:

1. Reads the current version from the **router** `skills/deepworkplan/SKILL.md`
 frontmatter (single source of truth).
2. Looks at commits merged since the last `vX.Y.Z` tag.
3. Decides the bump level:
 - `feat(scope)!:` or `BREAKING CHANGE:` in body → **MAJOR**
 - `feat(scope):` → **MINOR**
 - everything else (`fix:`, `chore:`, no prefix, etc.) → **PATCH**
4. Bumps `version:` in **all** SKILL.md files in sync (router + nine sub-skills
 + addons), prepends a section to `CHANGELOG.md`, commits as
 `chore(release): X.Y.Z [skip ci]`, tags `vX.Y.Z`, and pushes.
5. **Smoke-tests the just-published tag** — runs `npx skills add
 DailybotHQ/deepworkplan-skill@vX.Y.Z` into a **temp directory** and asserts
 the installed `version:` matches. This proves the release installs for
 consumers **without** overwriting the dogfood copy at
 `.agents/skills/deepworkplan/`.
6. **Dogfoods addon skills only** — refreshes `.agents/skills/dailybot/` and
 `.agents/skills/ai-diff-reviewer/` to their latest upstream tags (see
 "Vendored agent skills" below). `deepworkplan` is intentionally excluded.
7. Creates a GitHub Release with auto-generated notes and the SHA256SUMS
 provenance artifact attached.

To refresh the in-repo `deepworkplan` dogfood after changing
`skills/deepworkplan/`, run `bash scripts/refresh-dogfood-skill.sh`, review
the diff, and commit it on a PR — never rely on auto-release to do it.

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
- The `/deepworkplan-*` slash commands (`create`, `execute`, `refine`,
  `resume`, `status`, `onboard`, `verify`, `author`, `upgrade`) — the same set
  `setup.sh` links as `deepworkplan-<name>` symlinks.
- The `.dwp/` output convention (`.dwp/plans/`) and the
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
`addons/`), `shared` (context.sh, dwp-paths.md, adaptation.md, update-state.py,
state_contract.py, finalize_plan.py), `setup`
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

The tracked copies are pinned in `skills-lock.json`. Treat DeepWorkPlan as a
**generated mirror** of `skills/deepworkplan/`: refresh only with
`bash scripts/refresh-dogfood-skill.sh`, review the checksum-verified diff,
and commit the updated lockfile. Auto-release smoke-tests the published tag
in a temporary directory; it does not refresh this mirror.

Do not hand-edit the Dailybot or AI Diff Reviewer copies; contribute upstream.
Auto-release refreshes those two addons. Every exact `ai-diff-reviewer@vX.Y.Z`
install pin in the shipped pack must match the vendored reviewer's version
(`tests/agents-dogfood.bats`). The Action's floating `@v2` pin is exempt.

The full refresh procedure, rationale, and release-loop safeguards are in
[Design — vendored agent skills](docs/DESIGN.md#vendored-agent-skills--three-dogfood-copies-under-agentsskills).

## Local AI Diff Reviewer

The vendored `ai-diff-reviewer` skill remains available for local reviews
during Deep Work Plan Final Reviews. The repository also runs a CI
self-review (`.github/workflows/self-review.yml`): a single `grok` leg via
`DailybotHQ/ai-diff-reviewer@v3`, label-gated on `ready` (case-insensitive,
run-once per application — remove and re-add the label to re-run), with an
honest skip when `XAI_API_KEY` is not configured. That secret is required
only for the CI leg; the local review never needs it. The
repository-specific `.review/extension.md` configures both the local and
the CI review.

## The `ai-diff-reviewer` addon (required local review, optional CI surface)

Living alongside the vendored skill above, this repo also ships the
**DWP addon** at
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
  Local and CI read the **same inputs** — the same `prompt.md` and the same
  `.review/extension.md` — so the review criteria are identical by
  construction. The findings a model returns on a given diff are not
  guaranteed to be identical run to run; input parity is the claim, output
  equality is not.

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

**How the addon fits a DWP plan.** Since DWP standard 2.3.0 the local review
is part of the baseline (`skills/deepworkplan/spec/ADDONS.md` §6.5):
`onboard` installs the vendored skill and bootstraps `.review/extension.md`
in Phase 7a, and the
[`deepworkplan-create`](skills/deepworkplan/create/SKILL.md) /
[`deepworkplan-execute`](skills/deepworkplan/execute/SKILL.md) sub-skills run
the `ai-diff-reviewer` local pass inside the **Final Review's security pass**,
appending its findings to
`.dwp/plans/<plan>/analysis_results/SECURITY_REVIEW.md`. A missing skill or
extension is a recorded `local reviewer not installed` finding, carried into
the completion report, never a silent skip; installation belongs to onboarding
Phase 7a or an explicit addon invocation;
invocation errors soft-fail; `critical` findings from a completed pass still
block completion until fixed or explicitly accepted. The CI Action (Flow B)
remains an explicit opt-in. Legacy plans keep their recorded three-final-task
shape and get the same pass on their Security Review task.

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
