# Changelog

All notable changes to the DeepWorkPlan skill pack are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **This file is bot-owned after launch.** The `auto-release.yml` workflow
> prepends a new section to this file on every release. Do not hand-edit version
> sections or the `version:` fields in SKILL.md — write good conventional
> commits and let the workflow do the bump. See [AGENTS.md](AGENTS.md).

## [2.0.2] — 2026-05-30

### Changes

- fix(docs): point install commands and repo URLs at the real DailybotHQ org


## [2.0.1] — 2026-05-30

### Changes

- fix(docs): repoint broken cross-reference links in guide and addons spec


## [2.0.0] — 2026-05-21

### Changes

- Initial public release of the DeepWorkPlan methodology as an installable,
  Markdown-first agent skill pack distributed via skills.sh and OpenClaw.
- **Methodology v2** — the canonical standard for an AI-first "autopilot" repo
  (`AGENTS.md` + `docs/` + per-module docs + `.agents/` + `.claude → .agents`
  symlink) and the Deep Work Plan workflow, with **two archetypes** handled
  explicitly: orchestrator hub vs individual repo.
- **Single-step `create`** — the plan flow gathers context, drafts, and refines
  into one final plan in a single pass (the legacy two-step draft flow is gone).
- **`.dwp/` output convention** — all plan artifacts live in a gitignored
  `.dwp/` directory (`.dwp/plans/`, `.dwp/drafts/`), replacing the legacy
  `.agent_commands/agent_deep_work_plans/results/` path.
- **Reasoning-based onboarding** (`deepworkplan-onboard`) — reasons about a
  target repo's stack and archetype and generates *adapted* docs/config rather
  than blind-copying a template.
- **Six sub-skills** — `create`, `execute`, `refine`, `resume`, `status`, and
  `onboard`, plus a router meta-skill.
- **Extensible addons** — an opt-in addons mechanism whose first addon adds a
  reproducible, compose-based devcontainer to an onboarded repo.
- **Repo-dev infrastructure** — conventional-commit auto-release, multi-agent
  `setup.sh` installer, SKILL.md frontmatter validation, and CI, all enforcing
  the ship boundary (only `skills/deepworkplan/` installs).

> This release supersedes the prior unpublished `repo-ready` /
> `deepworkplan` v1 framework work; v2 is the first distributable methodology.
