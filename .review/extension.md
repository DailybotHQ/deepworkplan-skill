# Review overrides for deepworkplan-skill

This repo IS the DeepWorkPlan (DWP) methodology — the source of truth that
ships to consumers via `npx skills add DailybotHQ/deepworkplan-skill`. Every
change here propagates to every AI-first repo that installs the skill, so
the review bar is calibrated to durability, vendor-neutrality, and the
runtime-boundary invariant that lets the skill package cleanly.

The load-bearing rules live in [`AGENTS.md`](../AGENTS.md); this file
overrides the base prompt for the patterns most likely to slip a review in
this codebase.

## Severity overrides for this codebase

- **Always `critical`:** anything outside `skills/deepworkplan/**` that a
  runtime code path (a SKILL.md or a helper it sources) reads at execution
  time. The whole skill package MUST be self-contained inside
  `skills/deepworkplan/` — that's what `skills.sh` ships. See AGENTS.md
  Rule #2 ("The runtime artifact is `skills/deepworkplan/` — keep it pure").
  `docs/`, `tests/`, `scripts/`, and `.github/` are dev-time only.
- **Always `critical`:** a hand-edit of `version:` in any `SKILL.md`,
  `CHANGELOG.md`, a git tag, or the vendored dogfood copy at
  `.agents/skills/deepworkplan/**`. The `auto-release.yml` workflow OWNS
  those and re-writes them on every merge to `main`; a manual bump collides
  with the next release commit and duplicates changelog sections. See
  AGENTS.md Rule #4 ("Versioning is automatic — write good commits").
- **Always `critical`:** a sub-skill `SKILL.md` frontmatter `version:` that
  drifts from the router `skills/deepworkplan/SKILL.md` `version:` on any
  commit that touches the router. All eight files (router + 6 sub-skills +
  4 addons) MUST move in lockstep; `scripts/validate-frontmatter.py` fails
  CI when they don't. Applies equally to the vendored `.agents/skills/*`
  version invariants against their upstream tags in `skills-lock.json`
  (drift means a stale dogfood copy).
- **Always `critical`:** frontmatter that violates `validate-frontmatter.py`:
  `name:` not kebab-case, `name:` not starting with `deepworkplan`,
  `homepage:` instead of `documentation_url:`, or an unquoted `version`.
  See AGENTS.md Rule #3 for the canonical shape; the validator is the CI
  gate and rejects the merge.
- **Always `critical`:** a change to the public surface listed in AGENTS.md
  Rule #5 without a `feat(...)!:` prefix + migration note in the PR body —
  skill `name:` fields, the six `/deepworkplan-*` slash commands
  (`create`, `execute`, `refine`, `resume`, `status`, `onboard`), the
  `.dwp/` output convention, `DWP_DIR` / `DWP_AGENT_TOOL` env vars, or
  `setup.sh` flags. These are contracts other repos depend on.
- **Always `critical`:** attributing the DWP name to any external author,
  a "productivity framework" backstory, or a commercial platform, in any
  user-facing file (`README.md`, `AGENTS.md`, `CONTRIBUTING.md`,
  `skills/deepworkplan/SKILL.md`, `skills/deepworkplan/spec/*.md`,
  `skills/deepworkplan/guide/GUIDE.md`, or any addon `SKILL.md`). The DWP
  name stands on its own; vendor names ONLY appear inside `addons/*/`,
  never in the core methodology.
- **Always `critical`:** adding a runtime dependency on **any** commercial
  service (Dailybot, GitHub Actions, an LLM provider, a monitoring
  vendor) into the CORE tree (`skills/deepworkplan/{spec,guide,shared,
  create,execute,refine,resume,status,onboard,verify,author,examples}/`).
  Vendor coupling is allowed ONLY inside `skills/deepworkplan/addons/*/`.
  A conformant repo installs zero addons and is still fully AI-first —
  that promise is the reason addons exist as a mechanism.
- **Always `critical`:** weakening any of the four addon rules
  (`skills/deepworkplan/addons/README.md`): (a) never required, (b) reconcile
  don't clobber, (c) reason don't copy-paste, (d) archetype-agnostic. Also
  critical: a new addon shipping fewer than the four mandatory components
  (SPEC.md + templates/ + SKILL.md + validation checklist). The mechanism
  breaks if the contract erodes.
- **Always `critical`:** a `.claude/*` or `.cursor/*` PATH written as a
  canonical location in any NEW file (documentation, prompt, skill,
  template). Canonical is `.agents/*`. `.claude/` and `.cursor/` are
  back-compat SYMLINKS to `.agents/` and MUST stay that way. Files edited
  through the symlinks are fine; new content that TEACHES agents to write
  to `.claude/` is a regression that leaks into every consumer repo.
- **Always `critical`:** a non-MIT license header on a new file, or
  removal of MIT attribution from `LICENSE`. This is a public open-source
  package.
- **Always `critical`:** an `npx skills add` invocation in a new workflow,
  script, or SKILL.md example that omits either `--yes` (npm's proceed
  prompt) or `-y` (the skills CLI's agent-picker prompt). Missing either
  hangs indefinitely in a non-TTY runner — upstream `ai-diff-reviewer`
  v1.7.0 CHANGELOG codified this as the auto-release-hang fix, and
  `.github/workflows/auto-release.yml` in this repo must preserve both
  flags on every `skills add`.

- **Always `warning`:** a shell script under `scripts/**` or
  `setup.sh` or `skills/deepworkplan/shared/context.sh` that uses a
  bash 4+ feature: `mapfile` / `readarray`, `declare -A` (associative
  arrays), `${var^^}` / `${var,,}` case conversion, or `${!prefix*}`
  indirect expansion. macOS still ships bash 3.2 by default; CI runs
  `setup.sh` on `macos-latest` explicitly. See AGENTS.md Rule #6 for
  the approved bash-3.2 patterns.
- **Always `warning`:** a shell script missing `#!/usr/bin/env bash` on
  line 1 and `set -euo pipefail` immediately after. Silent failures in
  release scripts corrupt the vendored dogfood copy.
- **Always `warning`:** copy-paste of one repo's files into a NEW addon
  template (`skills/deepworkplan/addons/*/templates/*`). Addon templates
  are REASONING guides that carry decision anchors and placeholders — the
  agent fills them by inspecting the target repo's actual stack. Verbatim
  file dumps violate the four-rule "reason, don't copy-paste" constraint
  (`addons/README.md`).
- **Always `warning`:** a new mandatory final task inserted anywhere in
  `skills/deepworkplan/create/SKILL.md`'s "Three mandatory final tasks"
  block, or a reorder of the existing three (Security Review → Skills &
  Agents Discovery → Executive Report). The order is normative in
  `spec/DWP_SPECIFICATION.md`; addons AUGMENT existing final tasks — they
  don't add new ones. The `apply-review` sub-skill exposure in the
  ai-diff-reviewer addon is a live example (documented as OPTIONAL
  companion during `execute`, never a plan task).
- **Always `warning`:** documentation change to `skills/deepworkplan/**`
  (spec, guide, addon SKILL.md, or router SKILL.md) that is not mirrored
  into either the vendored dogfood copy at `.agents/skills/deepworkplan/**`
  or explicitly deferred to the next auto-release. Consumers install from
  the vendored copy — drift means agents in the wild read stale guidance.
- **Always `warning`:** RFC-2119 keyword usage in `spec/*.md` that isn't
  uppercase (must / must not / should — should be MUST / MUST NOT /
  SHOULD). The spec is a normative document; lowercase RFC keywords in
  prose are ambiguous. See `spec/DOCUMENTATION_STANDARD.md`.
- **Always `warning`:** a new example, template, or SKILL.md section in
  Spanish (or any non-English language). AGENTS.md Rule #1: this repo is
  public, English-only. Comments, docstrings, PR titles, commit messages,
  all in English.
- **Always `warning`:** a `SKILL.md` `allowed-tools:` field adding
  write-capable tools (`Edit`, `Write`, `Bash`, `MultiEdit`) without an
  accompanying section that scopes exactly what the sub-skill writes.
  Skills.sh Gen Agent Trust Hub reads `allowed-tools` and expects a
  matching trust boundary; `ai-diff-reviewer/apply-review/SKILL.md`
  (upstream) is the canonical shape — mirror it.
- **Always `warning`:** any new step in `.github/workflows/*.yml` that
  interpolates attacker-controlled PR content
  (`github.event.pull_request.title`, `.body`, `.head.ref`, `.head.label`)
  directly into a `run:` shell block via `${{ ... }}`. Route through
  `env:` mapping and reference `"$VAR"` in the script. This is a
  GitHub-Actions RCE pattern; the ai-diff-reviewer PR review workflow
  is specifically at risk if the extension file is edited.
- **Always `warning`:** a workflow using `pull_request_target` combined
  with `actions/checkout@vN` on `github.head_ref` without an explicit
  guard `if: github.event.pull_request.head.repo.full_name == github.repository`.
  This is the most-exploited RCE pattern on GitHub Actions; the
  ai-diff-reviewer workflow (task 5) MUST NOT introduce it.

- **De-escalate to `info`:** the exact section numbering inside
  `spec/DWP_SPECIFICATION.md` shifting when a new section is inserted.
  Sub-skills reference sections by anchor / heading text, not by number;
  a rename that keeps the heading text stable does not break refs.
- **De-escalate to `info`:** the `guide/GUIDE.md` using friendlier /
  prose-first phrasing than the parallel section of `spec/*.md`. That
  divergence is intentional — the spec is normative RFC-2119, the guide
  is prose-first onboarding text. Only flag when the two ACTUALLY
  contradict each other on a normative requirement.

## Don't comment on

- Formatting or content inside `assets/**`. That folder is intentionally
  illustrative — screenshots, brand imagery, example artifacts.
- Line length inside `spec/*.md` — the spec follows its own line-wrap
  discipline (matched to RFC 2119 practice). Prose files use ~80 col.
- Missing unit tests for behavioral changes in `skills/deepworkplan/`
  SKILL.md files or their prose sub-files. The test discipline in
  this repo is `tests/*.bats` bats + `scripts/verify-integrity.sh`
  checksum + smoke jobs on `ubuntu-latest` and `macos-latest`. There is
  no per-SKILL.md unit-test convention; prompt behaviour is verified by
  running the skill end-to-end.
- Any content inside `.agents/skills/dailybot/**`,
  `.agents/skills/ai-diff-reviewer/**`, or `.agents/skills/deepworkplan/**`.
  These are vendored copies — updated automatically by `auto-release.yml`
  (deepworkplan self-dogfood) and by `npx skills update` (the two addon
  skills). Hand-editing them is a bug; the real source is upstream. See
  DON'T list in AGENTS.md Rule #10 pillar (B).
- Content in `.claude/**` or `CLAUDE.md`. Those are symlinks
  (`.claude → .agents`, `CLAUDE.md → AGENTS.md`); any real edit belongs
  at the canonical `.agents/**` and `AGENTS.md` target.
- Absence of a `package.json`, `requirements.txt`, `pyproject.toml`, or
  any runtime-language manifest at the repo root. This is a bash + Python
  stdlib skill; no runtime deps by design.
- Absence of type hints or lint tools on `scripts/*.sh`. Bash discipline
  is `set -euo pipefail` + bash 3.2 compatibility + shellcheck (via CI
  when present) — no separate typing layer.

## Repo-specific conventions

- **Runtime boundary.** Anything read at skill runtime lives inside
  `skills/deepworkplan/**`. Anything at the repo root or under `docs/`,
  `tests/`, `scripts/`, `.github/` is dev-time only. When in doubt: would
  a consumer who runs `npx skills add DailybotHQ/deepworkplan-skill` need
  this file on their disk to invoke the skill? If yes → inside
  `skills/deepworkplan/`. If no → outside.
- **Frontmatter.** Every `SKILL.md` has the six required fields (`name`,
  `description`, `version` quoted, `documentation_url`, `user-invocable`,
  `allowed-tools`). `name:` is kebab-case, starts with `deepworkplan`.
  Sub-skills use `deepworkplan-<sub>`; addons use
  `deepworkplan-addon-<name>`. See AGENTS.md Rule #3 and
  `scripts/validate-frontmatter.py`.
- **Versioning.** Never touched by hand. `auto-release.yml` reads the
  commit-type prefix on merges to `main` (`feat!:` MAJOR, `feat:` MINOR,
  everything else PATCH), bumps all 8 in-tree SKILL.md files in sync,
  updates `CHANGELOG.md`, tags `vX.Y.Z`, and re-vendors the dogfood copy.
- **Addons.** Live under `skills/deepworkplan/addons/<name>/`. Every
  addon ships four things: `SPEC.md` (RFC-2119), `templates/*`
  (reasoning guides), `SKILL.md` (onboarding hook, `user-invocable`),
  and a validation checklist inside SPEC/SKILL. The four rules
  (`addons/README.md`) MUST hold: never required, reconcile don't
  clobber, reason don't copy-paste, archetype-agnostic.
- **Canonical vs symlinked paths.** `.agents/` is canonical. `.claude/`
  and `.cursor/` are back-compat symlinks. Write new content to
  `.agents/`; the symlinks continue to work for legacy tooling.
- **Two DWP dogfoods.** This repo installs its own `deepworkplan` skill
  vendored at `.agents/skills/deepworkplan/` (kept in sync by
  `auto-release.yml`) AND — after Task 3 of the current AI-Diff-Reviewer
  plan — also vendors `dailybot` and `ai-diff-reviewer` under the same
  tree. All three are pinned in `skills-lock.json`.
- **Branding.** Product name is exactly **DeepWorkPlan** (one word, CamelCase)
  or **DWP** (abbreviation). Slug is `deepworkplan`. The skill package
  name on the marketplace is `DailybotHQ/deepworkplan-skill`. Do NOT
  introduce variants ("Deep Work Plan" with spaces in file names,
  "deep-work-plan" kebab as an identifier, "DWorkPlan").
- **Commit format.** Conventional Commits (`type(scope): description`)
  with the body Structure `## Summary / ## Change Log / ## Risks` for
  non-trivial changes. `auto-release.yml` reads the subject line's
  `type` and bumps accordingly.

## PR hygiene

- PR title in Conventional Commits format (`auto-release.yml` reads it
  for the bump level).
- If `skills/deepworkplan/SKILL.md` router `version:` changed → verify
  ALL 7 other in-tree SKILL.md files moved to the same version (router
  + 6 sub-skills, plus every addon `SKILL.md` at
  `addons/*/SKILL.md`). Mismatch fails `validate-frontmatter.py` in CI.
- If a new addon under `skills/deepworkplan/addons/` was added → verify
  SPEC.md + templates/ + SKILL.md + validation checklist all exist, and
  `addons/README.md` was updated with the new addon row.
- If `.github/workflows/auto-release.yml` changed → verify every
  `npx skills add` invocation still carries both `--yes` AND `-y`.
- If a `SKILL.md` under `.agents/skills/` (any of the three vendored
  skills) was edited by hand → this is almost certainly a bug; the
  vendored copies are refreshed by `auto-release.yml` or `skills update`.
