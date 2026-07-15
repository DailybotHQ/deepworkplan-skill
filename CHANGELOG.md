# Changelog

All notable changes to the DeepWorkPlan skill pack are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **This file is bot-owned after launch.** The `auto-release.yml` workflow
> prepends a new section to this file on every release. Do not hand-edit version
> sections or the `version:` fields in SKILL.md — write good conventional
> commits and let the workflow do the bump. See [AGENTS.md](AGENTS.md).

## [2.16.3] — 2026-07-15

### Changes

- Merge pull request #32 from DailybotHQ/security/eliminate-remote-installer-pipes
- fix(security): eliminate remote-installer pipes flagged by Snyk E005 / Socket W012


## [2.16.2] — 2026-07-15

### Changes

- Merge pull request #31 from DailybotHQ/ci/auto-dogfood-after-release
- fix(docs): drop link to skills-lock.json until first release creates it
- ci(release): auto-dogfood vendored skill after each release
- fix(setup): ignore OS-generated .DS_Store inside skills/ and .agents/
- Merge pull request #30 from DailybotHQ/chore/refresh-dogfood-2.16.1
- chore(skill): refresh dogfood copy to v2.16.1 [skip release]


## [2.16.1] — 2026-07-14

### Changes

- Merge pull request #29 from DailybotHQ/docs/dailybot-addon-3.10.3
- docs(addon): align Dailybot addon with agent-skill 3.10.3 and CLI >= 3.7.0


## [2.16.0] — 2026-07-11

### Changes

- Merge pull request #28 from DailybotHQ/feat/cursor-agents-symlink
- chore(skill): sync dogfood copy with .cursor symlink changes [skip release]
- feat: add .cursor → .agents directory symlink alongside .claude → .agents
- Merge pull request #27 from DailybotHQ/chore/dogfood-skill-copy
- chore(skill): replace dogfood symlink with full skill copy [skip release]


## [2.15.1] — 2026-07-11

### Changes

- Merge pull request #25 from DailybotHQ/docs/dailybot-addon-align-3.4.0
- ci: ignore no-color.org in markdown link check
- docs(addon): align Dailybot addon with agent-skill 3.4.0 and CLI >= 3.1.2


## [2.15.0] — 2026-06-12

### Changes

- Merge pull request #24 from DailybotHQ/feat/design-system-interface-profiles
- feat(addon): generalize design-system gate to interface surfaces (visual-ui, cli-output, conversational profiles)


## [2.14.1] — 2026-06-12

### Changes

- Merge pull request #23 from DailybotHQ/fix/dogfood-docs-security-md
- docs(security): add docs/SECURITY.md so the repo dogfoods its own conformance floor


## [2.14.0] — 2026-06-12

### Changes

- Merge pull request #22 from DailybotHQ/feat/mandatory-security-review-final-task
- test(skill): update conformance fixtures to the three-final-task protocol
- feat(skill): per-task security discipline — shift security left of the tests task
- feat(skill): add mandatory Security Review final task and harden the SECURITY.md requirement


## [2.13.0] — 2026-06-10

### Changes

- Merge pull request #21 from DailybotHQ/feat/dailybot-addon-hook-enforcement
- feat(addon): offer deterministic hook enforcement in the dailybot addon


## [2.12.0] — 2026-06-10

### Changes

- Merge pull request #20 from DailybotHQ/feat/dailybot-event-model
- feat(addon): dailybot plan lifecycle event model — kickoff, blocked, and state-derived payloads


## [2.11.0] — 2026-06-09

### Changes

- Merge pull request #19 from DailybotHQ/feat/next-level-spec
- feat(verify): automated conformance checker (conformance.sh) with bats coverage
- feat(skill): spec 2.2.0 — plan state layer, rigor tiers, resume protocol, agent-workspace archetype


## [2.10.1] — 2026-06-09

### Changes

- Merge pull request #18 from DailybotHQ/test/agents-dogfood-coverage
- test(skill): lock in the .agents/ dogfood structure with a bats suite


## [2.10.0] — 2026-06-09

### Changes

- Merge pull request #17 from DailybotHQ/chore/spec-version-2.1.0-sync
- feat(onboard): verify gate, evidence-based scale decision, idempotent plan-driven
- docs(spec): unify methodology spec version to 2.1.0 across all docs


## [2.9.0] — 2026-06-09

### Changes

- Merge pull request #16 from DailybotHQ/docs/spec-version-2.1.0
- Merge branch 'main' into docs/spec-version-2.1.0
- feat(onboard): add plan-driven onboarding for large repos (Phase 2b)
- chore(skill): dogfood DWP by adding the .agents/ kit + .claude symlink


## [2.8.1] — 2026-06-09

### Changes

- Merge pull request #15 from DailybotHQ/docs/spec-version-2.1.0
- docs(spec): bump DWP_SPECIFICATION and DOCUMENTATION_STANDARD to 2.1.0


## [2.8.0] — 2026-06-09

### Changes

- Merge pull request #14 from DailybotHQ/feat/test-validation-discipline
- feat(spec): make test & validation discipline a first-class part of the loop


## [2.7.0] — 2026-06-07

### Changes

- Merge pull request #13 from DailybotHQ/feat/design-system-docs-location
- feat(addon): place design-system DESIGN.md under docs/, discovered via AGENTS.md index


## [2.6.0] — 2026-06-07

### Changes

- Merge pull request #12 from DailybotHQ/feat/design-system-addon
- feat(addon): add design-system addon (repo-root DESIGN.md), default-on when detected


## [2.5.0] — 2026-06-06

### Changes

- Merge pull request #11 from DailybotHQ/feat/product-spec-doc-standard
- docs(onboard): make the "readable by anyone" rationale explicit for PRODUCT_SPEC
- feat(spec): require PRODUCT_SPEC.md in the docs/ standard (MUST, all archetypes)


## [2.4.0] — 2026-06-05

### Changes

- Merge pull request #10 from DailybotHQ/feat/preset-catalog-and-agent-hosts
- feat(onboard): expand preset catalog to 22 stacks + add OpenCode/Antigravity hosts


## [2.3.0] — 2026-06-05

### Changes

- Merge pull request #9 from DailybotHQ/feat/provenance-integrity
- docs(skill): report security via GitHub private vulnerability reporting; drop email + SLA
- docs(skill): ship a TRUST.md trust statement + self-audit inside the skill
- feat(setup): publish + verify SHA256SUMS provenance for releases


## [2.2.2] — 2026-06-03

### Changes

- Merge pull request #8 from DailybotHQ/docs/context-first-narrative-and-logo
- docs(skill): context-first narrative + brand logo in README


## [2.2.1] — 2026-06-01

### Changes

- Merge pull request #7 from DailybotHQ/docs/silent-routing-when-ai-first
- docs(skill): make already-AI-first routing silent


## [2.2.0] — 2026-06-01

### Changes

- Merge pull request #6 from DailybotHQ/feat/router-start-here
- docs(execute): document autonomous mode + context-window checkpointing
- feat(verify): add the verify sub-skill (objective conformance check)
- feat(skill): add 'Start here (first run)' section to the router


## [2.1.0] — 2026-06-01

### Changes

- Merge pull request #5 from DailybotHQ/ci/harden-release-push-order
- ci(release): push main before tagging; bump checkout to v5
- Merge pull request #4 from DailybotHQ/ci/fix-auto-release-quoted-commits
- ci(release): pass commit log + version via env to harden auto-release
- Merge pull request #3 from DailybotHQ/docs/readme-powered-by-dailybot
- Merge branch 'main' into docs/readme-powered-by-dailybot
- feat(onboard): enumerate dependency-upgrade addon in Phase 7b
- fix(addon): use ASCII hyphens in dependency-upgrade name (was U+2011, failed validate-frontmatter)
- feat(addon): add opt-in dependency-upgrade addon (package-manager agnostic)
- feat(author): add deepworkplan-author sub-skill (skills/agents/commands generator)
- Merge pull request #2 from DailybotHQ/docs/readme-powered-by-dailybot
- docs(skill): use the official Dailybot "Powered by" section in the README
- Merge pull request #1 from DailybotHQ/docs/powered-by-dailybot
- docs(skill): add "Powered by Dailybot" footer to the README


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
