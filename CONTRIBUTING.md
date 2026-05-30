# Contributing to the DeepWorkPlan Skill Pack

Thanks for your interest in improving this skill. This guide is the human
counterpart to [`AGENTS.md`](AGENTS.md) — same conventions, more narrative. If
you're an AI agent reading this, prefer `AGENTS.md` — it's terser and has the
canonical rule list (and `CLAUDE.md` is a symlink to it).

This repo is small but plays in a public ecosystem (skills.sh, OpenClaw, direct
git clone), so the conventions matter. Read once, refer back when you need to.

---

## Table of contents

1. [What this repo is](#what-this-repo-is)
2. [Repo layout: runtime vs. dev infrastructure](#repo-layout-runtime-vs-dev-infrastructure)
3. [Local development setup](#local-development-setup)
4. [Making a change end-to-end](#making-a-change-end-to-end)
5. [Commit conventions and the auto-release flow](#commit-conventions-and-the-auto-release-flow)
6. [What CI checks](#what-ci-checks)
7. [Pull request workflow](#pull-request-workflow)
8. [Adding a new sub-skill](#adding-a-new-sub-skill)
9. [What we will and won't merge](#what-we-will-and-wont-merge)
10. [Reporting bugs and security issues](#reporting-bugs-and-security-issues)
11. [Where to find more](#where-to-find-more)

---

## What this repo is

The **official DeepWorkPlan agent skill pack**, maintained by
[Dailybot](https://www.dailybot.com). It's a **markdown-first** skill that
teaches AI coding agents (Claude Code, Cursor, OpenAI Codex, Gemini CLI, GitHub
Copilot, Cline, Windsurf, OpenClaw) how to (1) turn any repository AI-first —
generating an adapted `AGENTS.md`, `docs/`, per-module docs, `.agents/`, and the
`.claude → .agents` symlink — and (2) run structured multi-task **Deep Work
Plans** whose output lands in a gitignored `.dwp/` directory. The skill follows
the [Open Agent Skills](https://agentskills.io) standard.

There is **no application runtime, no CLI, no HTTP API, and no network calls**.
The "code" is the `SKILL.md` prompt files an agent reads at runtime, the
RFC-2119 spec under `skills/deepworkplan/spec/`, and two small bash helpers
(`setup.sh` and `skills/deepworkplan/shared/context.sh`).

Distribution channels:

- `npx skills add dailybotops/deepworkplan-skill` (skills.sh registry)
- `openclaw skills install deepworkplan` (OpenClaw native registry)
- `git clone … && ./setup.sh` (direct, for users who prefer it)

---

## Repo layout: runtime vs. dev infrastructure

The hard rule: **anything inside `skills/deepworkplan/` ships to users.
Everything else stays on GitHub and on contributors' machines.**

```
deepworkplan-skill/
├── README.md, SECURITY.md, LICENSE, CHANGELOG.md  ← repo metadata (NOT installed)
├── AGENTS.md, CLAUDE.md (symlink), CONTRIBUTING.md ← contributor guide (NOT installed)
├── PUBLISHING.md                  ← launch / release playbook (NOT installed)
├── setup.sh                       ← symlink installer for non-skills.sh users
├── .github/workflows/             ← CI + auto-release workflows (NOT installed)
├── tests/*.bats                   ← bats-core tests (NOT installed)
├── scripts/                       ← repo-dev scripts (NOT installed)
│   └── validate-frontmatter.py    ← schema check on every SKILL.md
├── docs/                          ← contributor docs (NOT installed)
│   ├── DESIGN.md                  ← why the layout is what it is
│   ├── INSTALLATION.md            ← every install method, compare / update / uninstall
│   ├── OPENCLAW.md                ← OpenClaw-specific notes
│   └── SUB_SKILL_GUIDE.md         ← step-by-step for adding a new sub-skill
└── skills/deepworkplan/           ← THE INSTALLED ARTIFACT — only this ships
    ├── SKILL.md                   ← router meta-skill (version source of truth)
    ├── spec/                      ← the 5 RFC-2119 normative docs
    ├── shared/                    ← context.sh, dwp-paths.md, adaptation.md
    ├── create/ execute/ refine/ resume/ status/ onboard/  ← sub-skills
    ├── guide/ examples/           ← methodology guide + templates
    └── addons/                    ← opt-in devcontainer + dailybot addons
```

When you create a new file, ask: *"does the user need this on disk for the skill
to work at runtime?"*

- **Yes** → put it under `skills/deepworkplan/`.
- **No** → put it at the repo root or under `.github/`, `tests/`, `scripts/`,
  `docs/`.

Why it matters: skills.sh and OpenClaw only copy/symlink the contents of
`skills/deepworkplan/`. Anything else is invisible to runtime agents. Every
runtime file must be self-contained inside that directory — never reach *out of*
`skills/deepworkplan/` at runtime. See [`docs/DESIGN.md`](docs/DESIGN.md) for the
reasoning.

---

## Local development setup

### Required tools

| Tool | Why | Install |
|------|-----|---------|
| `git` | Obvious | Pre-installed on most systems |
| `bash` (3.2+) | Run `setup.sh`, `context.sh`, tests | macOS ships 3.2 by default; Linux usually 4+. We support 3.2 deliberately — see AGENTS.md rule #6. |
| `shellcheck` | Lint shell scripts | `brew install shellcheck` (macOS), `apt install shellcheck` (Ubuntu) |
| `bats-core` | Run `tests/*.bats` | `brew install bats-core` (macOS), `apt install bats` (Ubuntu) |
| `python3` (3.10+) + `pyyaml` | Run `validate-frontmatter.py` | `python3 -m pip install --user pyyaml` |

### Clone and install the skill into your local agent

```bash
git clone https://github.com/DailybotHQ/deepworkplan-skill.git
cd deepworkplan-skill

# Install into your local agent (replace claude with your agent of choice).
# This creates symlinks, so edits to the cloned repo are picked up live.
./setup.sh --host claude       # or: cursor, codex, windsurf, copilot, cline, gemini

# Or auto-detect every agent on the machine:
./setup.sh
```

`setup.sh --host <agent>` symlinks `skills/deepworkplan/` into the appropriate
path for that agent (e.g. `~/.claude/skills/deepworkplan`), plus per-sub-skill
symlinks (`deepworkplan-create`, `deepworkplan-execute`, `deepworkplan-refine`,
`deepworkplan-resume`, `deepworkplan-status`, `deepworkplan-onboard`) so each is
invocable as a slash command.

### Verify it's wired up

After `setup.sh --host claude`, restart your agent. In a session, say something
like *"onboard this repo"* or *"create a plan to ship feature X"* — the agent
should route to `deepworkplan-onboard` / `deepworkplan-create`. If it doesn't,
the symlinks aren't being seen — try `ls -la ~/.claude/skills/ | grep deepworkplan`
to confirm.

---

## Making a change end-to-end

### 1. Branch from `main`

```bash
git switch main
git pull
git switch -c feat/your-change-name
```

We don't use Gitflow — branches off `main`, PR back into `main`. **Don't push
directly to `main`.** Branch protection blocks it, and `auto-release.yml` fires
on every merge to `main`, so a direct push would auto-release whatever you
pushed.

### 2. Edit, test, commit

Edit anything under `skills/deepworkplan/` (runtime) or root-level dev
infrastructure (`.github/`, `tests/`, `scripts/`, `docs/`, `AGENTS.md`, etc.).
Your agent picks up runtime changes on its next session because the install was
via symlink.

Run the local checks before you commit:

```bash
# Lint shell scripts
shellcheck setup.sh skills/deepworkplan/shared/context.sh scripts/*.sh

# Run unit tests (bats-core)
bats tests/

# Validate every SKILL.md frontmatter (kebab-case name, quoted version, etc.)
python3 scripts/validate-frontmatter.py

# Smoke-test setup.sh against a throwaway HOME
HOME="$(mktemp -d)" ./setup.sh --host claude
```

If any of these fail, fix before committing — CI runs the same checks and will
block the PR.

Quick sanity test for the shared helper:

```bash
# context.sh emits a single-line JSON object in a regular directory
bash skills/deepworkplan/shared/context.sh

# DWP_DIR / DWP_AGENT_TOOL overrides are honored
DWP_DIR=/tmp/custom-dwp bash skills/deepworkplan/shared/context.sh
DWP_AGENT_TOOL=my-agent  bash skills/deepworkplan/shared/context.sh
```

### 3. Don't bump the version manually

The `auto-release.yml` workflow owns `version:` fields and `CHANGELOG.md`. Just
write good commit messages — see the next section.

### 4. Push and open a PR

```bash
git push -u origin feat/your-change-name
gh pr create --base main --head feat/your-change-name
```

(Or use the GitHub web UI — `gh` is convenient but optional.) The PR template
(`.github/PULL_REQUEST_TEMPLATE.md`) auto-populates your PR body with the
pre-merge checklist. Fill it in honestly.

---

## Commit conventions and the auto-release flow

Every merge to `main` triggers `auto-release.yml`, which:

1. Reads the current version from the router `skills/deepworkplan/SKILL.md`
   frontmatter (the single source of truth).
2. Looks at commits since the last `vX.Y.Z` tag.
3. Decides the bump level from conventional-commit prefixes:
   - `feat(scope)!:` or `BREAKING CHANGE:` in body → **MAJOR**
   - `feat(scope):` → **MINOR**
   - everything else (`fix:`, `chore:`, `docs:`, `ci:`, no prefix) → **PATCH**
4. Syncs the new version into **all** SKILL.md files (router + six sub-skills +
   addons).
5. Prepends a section to `CHANGELOG.md` listing the merged commits.
6. Commits as `chore(release): X.Y.Z [skip ci]`, tags `vX.Y.Z`, creates a GitHub
   Release.

So your commit messages directly determine the release version. Use the format
documented in [`AGENTS.md`](AGENTS.md) → "Commit Message Format":

```
<type>(<scope>): <short description>

<body — Summary, motivation, what changed, risks>
```

**Types:** `feat`, `fix`, `docs`, `chore`, `test`, `ci`, `refactor`.

**Scopes:** `skill` (general pack/router), `create` / `execute` / `refine` /
`resume` / `status` / `onboard` (specific sub-skill), `addon` (an addon under
`addons/`), `shared` (context.sh, dwp-paths.md, adaptation.md), `setup`
(setup.sh), `ci` (.github/), `docs` (docs/, README, guide), `release`
(versioning, CHANGELOG).

### Bump-level guidance for this skill

| Bump | When | Example |
|------|------|---------|
| **MAJOR** | Breaks the public surface | Rename or remove a `/deepworkplan-*` slash command, change the `.dwp/` convention or the `DWP_DIR`/`DWP_AGENT_TOOL` env vars, change `setup.sh` flags, rename a skill `name:` field |
| **MINOR** | Additive — new capability without breaking existing behavior | New sub-skill, new addon, new onboarding preset, new flag |
| **PATCH** | Bug fix, doc, internal refactor, CI change | Typo fix, spec clarification, CI workflow update |

If you're not sure whether your change is MAJOR or MINOR, lean MAJOR and explain
in the PR body. A spurious major bump is recoverable; a silent breaking change in
a minor release is not.

### What you should *never* edit by hand

- `version:` fields in any `SKILL.md` frontmatter
- `CHANGELOG.md` entries (the release section is generated)
- Git tags

If you do edit them by hand, the next auto-release will overwrite the version
line and prepend a duplicate changelog section.

---

## What CI checks

`.github/workflows/ci.yml` runs on every PR and every push to `main`:

| Job | What it checks | Catches |
|-----|----------------|---------|
| **SKILL.md frontmatter validation** | Every `skills/deepworkplan/**/SKILL.md` parses as valid YAML, has a kebab-case `name` starting with `deepworkplan`, a quoted SemVer `version`, `documentation_url` (NOT `homepage`), and `user-invocable` | Frontmatter drift, snake_case, regression to the legacy `homepage` field |
| **shellcheck** | `setup.sh`, `skills/deepworkplan/shared/context.sh`, `scripts/*.sh` | Bash syntax issues, unsafe quoting, unused vars |
| **context.sh smoke** | Output is valid single-line JSON; `DWP_AGENT_TOOL` and `DWP_DIR` overrides are honored | Behavioral regressions in the shared context detector |
| **bats tests** | All cases in `tests/*.bats` | Unit-test regressions in `context.sh` and `setup.sh` |
| **setup.sh smoke (Linux + macOS)** | `--help` runs, and `--host claude` creates the pack + six sub-skill symlinks — on both Ubuntu and macOS bash 3.2 | bash 4+ idioms (`mapfile`, `declare -A`, `${var^^}`) that break for macOS users |
| **Markdown link check** | Internal cross-references and external links resolve | Dead links in docs |

The `concurrency` group ensures consecutive pushes cancel earlier still-running
jobs (the latest commit's status is authoritative).

---

## Pull request workflow

### Before opening

- [ ] Read [`AGENTS.md`](AGENTS.md) once if you haven't.
- [ ] Run the local checks (shellcheck, bats, frontmatter, setup smoke).
- [ ] Confirm your commit messages follow the format and reflect the intended bump level.
- [ ] If you touched the public surface (slash commands, `.dwp/` convention, `setup.sh` flags, skill names), call it out in the PR body.

### CI gates

`main` branch protection requires CI to pass before merge. The automation
identity is allowed to bypass protection so the `chore(release):` commit can
land.

### Auto-release happens on merge

Once your PR merges to `main`, `auto-release.yml` fires and creates a new
release. You don't need to do anything — the workflow handles the version bump,
CHANGELOG, tag, and GitHub Release. If it fails (most likely cause:
`AUTOMATION_GITHUB_TOKEN` secret missing or expired), fix the underlying issue
and the next merge re-fires the release.

---

## Adding a new sub-skill

If you want to add a new capability under `skills/deepworkplan/` (e.g. a
`deepworkplan-review` skill), follow the step-by-step in
[`docs/SUB_SKILL_GUIDE.md`](docs/SUB_SKILL_GUIDE.md). The short version:

1. Decide the name (kebab-case, prefix `deepworkplan-`). The folder drops the
   prefix (`skills/deepworkplan/review/` → `name: deepworkplan-review`).
2. Create `skills/deepworkplan/<verb>/SKILL.md` with the standard frontmatter
   (the guide has a copy-paste template).
3. Register it in the router meta-skill (`skills/deepworkplan/SKILL.md`).
4. Add the verb to the `SKILLS` array in `setup.sh` so symlinks get created.
5. Write a bats test if the skill ships shell behavior.
6. Update the README skills table.

Use `feat(<verb>):` as your commit prefix so the auto-release detects a MINOR
bump.

---

## What we will and won't merge

**We'll merge:**

- Bug fixes, ideally with a regression test under `tests/`.
- New sub-skills, addons, or onboarding presets following the conventions.
- Documentation improvements — especially to the spec, the methodology guide, or
  anything in `docs/DESIGN.md`.
- Cross-platform fixes (bash 3.2 compat, Windows/WSL2, Docker, CI).
- CI improvements that are clearly more value than maintenance cost.

**We probably won't merge** without a strong rationale (and we'll ask for it):

- Anything that reaches *out of* `skills/deepworkplan/` at runtime, or puts a
  dev-infra file inside it (breaks the ship boundary).
- Re-introducing the `homepage:` field in frontmatter — agents misinterpret it as
  a re-fetch source. Use `documentation_url:` (the validator rejects new
  `homepage:` entries).
- Snake_case `name:` values in frontmatter (use kebab-case).
- Bash 4+ idioms (`mapfile`, `declare -A`, `${var^^}`) — they break for macOS users.
- Hand-edited `version:` fields or `CHANGELOG.md` entries — the auto-release bot
  owns them.
- Committing `.dwp/` plan output into the repo — it's gitignored working state.
- Spanish or any non-English content. The repo is consumed worldwide.

When in doubt, open the PR and explain — we'd rather discuss in context than
reject something whose rationale we don't see yet.

---

## Reporting bugs and security issues

### Bugs

Open an issue using the bug report template
(`.github/ISSUE_TEMPLATE/bug_report.md`). Include the agent and version, your OS,
the skill version (from `skills/deepworkplan/SKILL.md`), the install method, and
the exact behavior.

### Security vulnerabilities

**Do not** open a public issue. Follow the coordinated-disclosure process in
[`SECURITY.md`](SECURITY.md) (email `security@dailybot.com`).

---

## Where to find more

| If you want to know… | Read |
|----------------------|------|
| Every convention and rule (canonical, terse) | [`AGENTS.md`](AGENTS.md) |
| Why the layout / ship boundary / `.dwp/` convention are the way they are | [`docs/DESIGN.md`](docs/DESIGN.md) |
| How to add a new sub-skill in detail | [`docs/SUB_SKILL_GUIDE.md`](docs/SUB_SKILL_GUIDE.md) |
| The full install guide (compare / update / uninstall) | [`docs/INSTALLATION.md`](docs/INSTALLATION.md) |
| OpenClaw-specific install notes | [`docs/OPENCLAW.md`](docs/OPENCLAW.md) |
| The normative DeepWorkPlan standard | [`skills/deepworkplan/spec/`](skills/deepworkplan/spec/README.md) |
| The launch / release playbook | [`PUBLISHING.md`](PUBLISHING.md) |
| Per-version release notes | [`CHANGELOG.md`](CHANGELOG.md) |
| Security disclosure | [`SECURITY.md`](SECURITY.md) |
| User-facing install / usage (quickstart) | [`README.md`](README.md) |

---

## Code of conduct

Be kind. Assume good faith. We're a small repo trying to make AI agents reliable
for real engineering work — that goal is incompatible with bad-faith
contributions.
