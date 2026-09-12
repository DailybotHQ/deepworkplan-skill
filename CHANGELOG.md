# Changelog

All notable changes to the DeepWorkPlan skill pack are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **This file is bot-owned after launch.** The `auto-release.yml` workflow
> prepends a new section to this file on every release. Do not hand-edit version
> sections or the `version:` fields in SKILL.md — write good conventional
> commits and let the workflow do the bump. See [AGENTS.md](AGENTS.md).

## [5.0.0] — 2026-09-12

### Changes

- Merge pull request #41 from DailybotHQ/fix/methodology-final-hardening
- feat(skill): harden author sub-skill, plan-local analysis_results contract, setup.sh parity
- chore(skill): refresh the dogfood copy to the hardened pack
- docs(evaluation): add the final-hardening evaluation record
- feat(upgrade): add the deepworkplan-upgrade sub-skill (/dwp-upgrade)
- feat(skill)!: align the DWP standard with the product line (2.4.0 -> 4.0.0)
- feat(verify): enforce the Context section the v4 spec already mandates
- feat(guide): absorb corpus-proven long-plan machinery — optional Stage Gates and enriched Plan Variables
- feat(create): every plan declares its execution-parallelism decision explicitly
- fix(addon): one cross-addon consent matrix — no contradicting surface left
- fix(addon): devcontainer entrypoint link_persist seeds volumes correctly — now regression-tested
- fix(addon): close the stale addons/README.md mirror rows left by the design-system and reviewer policy tasks
- feat(addon): dependency upgrade becomes near-default — offered for every repo with declared dependencies
- feat(addon): design-system smart install - mandatory offer, acceptance-gated install
- fix(addon): reviewer augmentation reviews the plan's explicit diff, not the tracking ref
- fix(addon): finish the ai-diff-reviewer mirror audit across SKILL, SPEC and INTEGRATION
- feat(skill): one-purpose-per-task decomposition rule across the methodology
- fix(skill): one approval rule and promotion recovery across the lifecycle
- fix(skill): pin mode-aware hub readiness and block insufficient legacy fallbacks
- fix(skill): hub returns to its saved root and keeps child DWP_DIR isolated
- fix(skill): orchestrator hand-off templates can no longer false-pass
- fix(verify): stop false conformance without Python and accept bold-label fields


## [4.0.3] — 2026-09-11

### Changes

- Merge pull request #40 from DailybotHQ/fix/provenance-standard-version
- fix(onboard): stamp the standard the checker enforces, and resync the dogfood


## [4.0.2] — 2026-09-11

### Changes

- Merge pull request #39 from DailybotHQ/fix/v4-lifecycle-contracts
- docs(readme): document the verify sub-skill and the methodology it rests on
- chore(dogfood): resync the vendored copy to 4.0.1 after merging main
- Merge remote-tracking branch 'origin/main' into fix/v4-lifecycle-contracts
- fix(addon): repin the documented AI Diff Reviewer install to v2.0.1 and gate it


## [4.0.1] — 2026-09-11

### Changes

- Merge pull request #38 from DailybotHQ/fix/v4-lifecycle-contracts
- fix(verify): one plan contract for both eras, with the legacy path restored
- fix(state): preserve v2 task evidence and validated commits


## [4.0.0] — 2026-09-11

### Changes

- Merge pull request #37 from DailybotHQ/feat/lite-plan-lifecycle
- fix(create): author each task contract once, and name the promotion recovery
- feat(skill)!: remove the refined draft and .dwp/drafts entirely
- fix(verify): repair Lite conformance defects and settle the approval axis
- fix(create): make the Lite-first flow actually executable
- fix(test): commit Lite fixtures and make lite-plans.bats CI-safe
- fix(verify): validate Lite state correspondence
- feat(lifecycle): ship Lite-first plan workflow
- test(verify): cover Lite plan contracts
- feat(execute): support Lite plan lifecycle
- feat(create): add Lite-first creation and option grammar
- feat(spec): define Lite and Full plan lifecycle


## [3.0.0] — 2026-09-10

### Changes

- Merge pull request #36 from DailybotHQ/feat/token-efficiency-upgrade
- chore(ci): remove AI reviewer workflow
- fix(review): harden resume and legacy conformance gates
- fix(review): preserve local review across legacy plans
- fix(review): remove remaining execute-time install guidance
- fix(review): unify onboarding-only reviewer installation
- fix(review): reconcile final review protocol and references
- fix(review): Dailybot opt-in wording, completed-plan SECURITY_REVIEW gate, portable checksums
- fix(review): align progressive-load triggers and refresh dogfood for required local review
- fix(fixtures): avoid dead link in partial materialization README
- feat(create): resumable plan materialization — manifest first, README skeleton, recorded analysis, status flipped last
- feat(skill)!: release Deep Work Plan v3 on standard 2.3.0
- feat(addons): make the AI Diff Reviewer local review a required baseline component; CI surface stays opt-in
- fix(review): PR #36 review corrections — skills decision before validation, conformance DWP_DIR resolution, identity checks, re-measured ledger
- feat: v2.17.1 — progressive disclosure, targeted upgrade path, Final Review consolidation
- feat(adoption): targeted upgrade path, troubleshooting decision path, pilot evidence
- docs(skill): compatibility matrix and bidirectional cross-agent handoff evidence - Task 20 of PLAN_dwp_token_efficiency_upgrade
- docs(skill): publish the efficiency evaluation with an honest evidence ledger - Task 19 of PLAN_dwp_token_efficiency_upgrade
- fix(create): repair ten defects found by the behavioral evaluation - Task 18 of PLAN_dwp_token_efficiency_upgrade
- test(skill): state-layer schema/contract regressions and CI wiring - Task 17 of PLAN_dwp_token_efficiency_upgrade
- feat(skill): conformance accepts both lifecycle shapes, checks identity and reports harness-version findings - Task 16 of PLAN_dwp_token_efficiency_upgrade
- feat(onboard): testing sections for mobile, infrastructure and generic presets plus the contributor testing matrix - Task 15 of PLAN_dwp_token_efficiency_upgrade
- feat(onboard): add the verified testing section to the eight backend presets - Task 14 of PLAN_dwp_token_efficiency_upgrade
- feat(onboard): add the verified testing section to the nine web presets - Task 13 of PLAN_dwp_token_efficiency_upgrade
- feat(onboard): verified testing discovery, testing-map generation and targeted harness upgrade - Task 12 of PLAN_dwp_token_efficiency_upgrade
- feat(resume): bounded-context resume with boundary-aware recovery, takeover and state-first status - Task 11 of PLAN_dwp_token_efficiency_upgrade
- feat(execute): affected-scope gates, bounded repair, task-local closure and Final Review completion - Task 10 of PLAN_dwp_token_efficiency_upgrade
- feat(refine): lifecycle-aware plan edits with evidence invalidation and explicit migration - Task 9 of PLAN_dwp_token_efficiency_upgrade
- feat(create): materialize directly in trust mode and generate efficient-by-construction plans - Task 8 of PLAN_dwp_token_efficiency_upgrade
- docs(guide): align the split guide with spec 2.3.0 - Task 7 of PLAN_dwp_token_efficiency_upgrade
- refactor(guide): split the methodology guide into flow-scoped files behind a routing index - Task 7 of PLAN_dwp_token_efficiency_upgrade
- feat(spec): make testing-guide content normative and define install/onboard/upgrade adoption - Task 6 of PLAN_dwp_token_efficiency_upgrade
- feat(spec): recoverable state, closed-schema versioning and standard discovery - Task 5 of PLAN_dwp_token_efficiency_upgrade
- feat(spec): one Final Review, task-local skills decisions, optional report, mode-aware create - Task 4 of PLAN_dwp_token_efficiency_upgrade
- feat(spec): select validation gates from the touched surface and state the unit-first posture - Task 3 of PLAN_dwp_token_efficiency_upgrade
- test(efficiency): add pre-registered fixtures, oracles and instruction-load measurement - Task 2 of PLAN_dwp_token_efficiency_upgrade
- docs(adr): ratify the token-efficiency architecture and quality contract - Task 1 of PLAN_dwp_token_efficiency_upgrade


## [2.17.1] — 2026-09-08

### Changes

- Merge pull request #35 from DailybotHQ/fix/security-audits-e006-w012-trust
- chore(skill): refresh dogfood copy with the round-2 review fixes
- fix(skill): align resume trust wording with the DWP Resume Protocol (spec 5.3)
- chore(skill): refresh dogfood copy with the review-fix round
- docs(security): self-audit grep #5 catches un-tagged skills installs; precise history
- fix(skill): concrete pass-through wrappers, full design-system scope, read-only status tools
- fix(skill): pin every remaining cross-repo install in onboard, spec, and reviewer docs
- chore(skill): refresh dogfood copy with the audit-invariant changes
- docs(security): codify skills.sh audit invariants in review rules and repo docs
- fix(skill): add trust boundaries to every write-capable SKILL.md
- fix(addon): pin ai-diff-reviewer install example and document supply-chain trust
- fix(addon): pin Dailybot skill installs to tags, drop unpinned clone path
- fix(addon): gate SSH seeding behind explicit opt-in, make AI-CLI wrappers pass-through
- Merge pull request #34 from DailybotHQ/chore/stop-self-dogfood-deepworkplan
- ci(release): stop auto-overwriting repo-adapted deepworkplan dogfood [skip release]


## [2.17.0] — 2026-07-16

### Changes

- Merge pull request #33 from DailybotHQ/feat/ai-diff-reviewer-addon
- fix(ci): ignore vendored IAR docs links; address AI review warnings
- feat(review): upgrade AI Diff Reviewer to v2 with skip-ai-review
- docs(addon): align Flow A consent copy with required extension bootstrap
- docs(spec): align ADDONS.md never-block wording with SR gate discipline
- fix(addon): scope never-block to local-review invocation only
- chore(review): require methodology-integrity checklist in AI review
- fix(addon): require extension bootstrap before Flow A onboarding completes
- fix(security): remove lexical install-pipe strings from addon docs
- fix(review): split local SR never-block from Flow B secrets
- fix(review): address AI Diff Reviewer warnings on PR #33
- fix(ci): unbreak frontmatter, bats catalog, and markdown-link-check after vendoring
- docs: describe pr-review workflow, vendored-skill dogfooding, and CURSOR_API_KEY setup
- chore(review): add Cursor-based pr-review workflow gated on ready label
- chore(review): add repo-tailored .review/extension.md for skill repo
- chore(review): install dailybot v3.10.3 and ai-diff-reviewer v1.7.0 vendored
- feat(dwp): augment Security Review with ai-diff-reviewer local pass when addon installed
- feat(dwp): add ai-diff-reviewer addon (opt-in, two-flow, defers to upstream v1.7.0)


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
