# Review overrides for deepworkplan-skill

This repo IS the DeepWorkPlan (DWP) methodology — the source of truth that
ships to consumers via `npx skills add DailybotHQ/deepworkplan-skill`. Every
change here propagates to every AI-first repo that installs the skill, so
the review bar is calibrated to durability, vendor-neutrality, the
runtime-boundary invariant that lets the skill package cleanly, and —
critically — the public **skills.sh Security Audits** posture that users
see before they install.

Public listing (audited continuously by skills.sh):
<https://www.skills.sh/dailybothq/deepworkplan-skill/deepworkplan>

Target posture on that page: **Gen Agent Trust Hub = Pass**, **Socket =
Pass** (or at worst a residual Warn that is not a delivery-vector hit),
**Snyk = Pass**. A release that reintroduces a known audit FAIL erodes
install-time trust even when the methodology itself is sound. skills.sh
re-scans on a delay after merge — do not treat a stale FAIL on the
dashboard as permission to add more risk; treat the shipped tree as the
contract that must stay clean.

The load-bearing rules live in [`AGENTS.md`](../AGENTS.md),
[`skills/deepworkplan/TRUST.md`](../skills/deepworkplan/TRUST.md), and the
normative methodology at
[`skills/deepworkplan/spec/DWP_SPECIFICATION.md`](../skills/deepworkplan/spec/DWP_SPECIFICATION.md).
This file overrides the base prompt for the patterns most likely to slip a
review in this codebase.

**Primary review mission:** protect the methodology so consumers can keep
creating and executing **long-horizon Deep Work Plans** — durable plans that
survive across sessions and agents, with atomic tasks, acceptance criteria,
validation gates, and resumability. A PR that ships a neat addon or CI
improvement but quietly breaks `create` / `execute` / `resume` / the
mandatory finals / `.dwp/` / zero-addon conformance is a **methodology
regression** and must fail the review.

## Severity overrides for this codebase

### Methodology integrity (long-horizon plans must keep working)

When the diff touches ANY of
`skills/deepworkplan/{create,execute,refine,resume,status,verify,onboard,author}/`,
`skills/deepworkplan/spec/**`, `skills/deepworkplan/guide/**`, or the router
`skills/deepworkplan/SKILL.md`, the review **MUST** run the **Methodology
integrity checklist** (below) and surface failures as findings — not as a
silent pass. Addons and CI may change; the core loop must not.

- **Always `critical` (methodology / long-horizon loop):** removing,
  renaming, or collapsing any of the core sub-skills that make long-horizon
  work possible — `create`, `execute`, `refine`, `resume`, `status`,
  `verify`, `onboard` — or teaching agents that any of them are optional /
  deprecated without a `feat(...)!:` migration. Consumers run multi-hour
  plans by chaining these; losing `resume` or `execute`'s gate discipline
  breaks the product.
- **Always `critical` (methodology / plan durability):** changing the
  `.dwp/` output convention (plans under `.dwp/plans/PLAN_{name}/`, drafts
  under `.dwp/drafts/`, gitignored working state) or reintroducing a legacy
  results path as the primary location. Long-horizon state lives here;
  scattering it makes resume impossible.
- **Always `critical` (methodology / task contract):** weakening the
  required task anatomy so tasks can ship without **Acceptance Criteria**
  and **Validation** (or equivalent semantic sections). Spec-driven
  execution depends on verifiable checkboxes + gates; "just do the work and
  mark done" is a methodology break even if prose still sounds serious.
- **Always `critical` (methodology / completion protocol):** teaching
  `execute` (or guide/spec parallels) to mark a task `[x]` when validation
  failed, acceptance criteria are unmet, or a Security Review `critical`
  finding is still open/unaccepted. Soft-fail language MUST stay scoped to
  *invocation* failures of optional augmentations — never to gate results
  after a check actually ran.
- **Always `critical` (methodology / mandatory finals):** inserting a new
  mandatory final task, removing one of the three, or reordering
  Security Review → Skills & Agents Discovery → Executive Report in
  `create/SKILL.md` / `spec/DWP_SPECIFICATION.md` / `guide/GUIDE.md`.
  Addons **MAY only AUGMENT** an existing final task (e.g. local review
  under Security Review); they **MUST NOT** become a fourth plan task file
  or reorder the finals. Same bar as before, elevated from warning —
  this is the spine of every plan.
- **Always `critical` (methodology / zero-addon conformance):** any change
  that makes an addon, commercial service, CI provider, or external skill
  **required** for `create` / `execute` / `onboard` / `verify` to succeed
  on a repo with zero addons installed. Baseline AI-first + long-horizon
  plans MUST work with only the core pack.
- **Always `critical` (methodology / resume & interruptibility):** removing
  or gutting resume/progress semantics (`PROGRESS.md`, `[x]` trust rules,
  blocked-task reporting, "continue from recorded state") so an interrupted
  multi-session plan cannot be continued by a new agent. Long-horizon
  without resume is short-horizon with marketing.
- **Always `critical` (methodology / normative contradiction):** a change
  where `guide/GUIDE.md` (or an addon SKILL) **contradicts**
  `spec/*.md` / `create` / `execute` on a normative MUST/MUST NOT (detection
  predicates, gate behavior, final-task order, `.dwp/` layout, never-block
  scope). Friendly prose is fine; opposing contracts are not — agents pick
  one surface and silently diverge.

### Ship boundary, packaging, trust

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
  commit that touches the router. Every in-tree
  `skills/deepworkplan/**/SKILL.md` (router + sub-skills + all addons —
  currently 14 files) MUST move in lockstep; `scripts/validate-frontmatter.py`
  fails CI when they don't. Prefer this "every SKILL.md under the pack"
  rule over a hard-coded size so future addons don't stale the count.
  Applies equally to the vendored `.agents/skills/*` version invariants
  against their upstream tags in `skills-lock.json` (drift means a stale
  dogfood copy).
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
- **Always `critical` (skills.sh / Snyk E005 / Socket W012):** any
  fetch-and-execute installer pipeline as a literal string anywhere under
  `skills/deepworkplan/**` — including opt-in addons, templates, SPEC
  examples, and "do not do this" illustrations that still spell the
  command. Scanners are lexical; surrounding prose does not help. Banned
  shapes include POSIX `curl … | bash` / `curl … | sh` / `wget … | sh`,
  PowerShell `irm … | iex` / `iwr … | iex`, and any single-line
  `download → pipe → shell` or `download → Invoke-Expression`. Prefer
  package-manager installs (`pip`, `brew`, `npm`, `apt`) or a verified
  multi-step flow described without the pipe (`download` → verify
  SHA-256/cosign → execute as separate steps), linked out rather than
  inlined. Precedent: `fix(security): eliminate remote-installer pipes`
  (`6a05ed9`) — that FAIL was what moved Snyk to Fail on the public
  [skills.sh listing](https://www.skills.sh/dailybothq/deepworkplan-skill/deepworkplan).
  Reintroducing the string is a release blocker for user trust, not a
  docs nit.
- **Always `critical` (skills.sh / Gen Agent Trust Hub):** a `SKILL.md`
  under `skills/deepworkplan/**` that lists write-capable tools in
  `allowed-tools:` (`Edit`, `Write`, `Bash`, `MultiEdit`) without a
  human-readable **Trust boundary / write-scope** section that enumerates
  (a) what may be written and only after which consent, and (b) what MUST
  NOT be written (credentials, remote-installer pipes, silent clobbers,
  telemetry). Trust Hub treats `allowed-tools` as the trust boundary;
  missing scope fails the audit users see before install. Canonical shape:
  upstream `ai-diff-reviewer/apply-review` Step 0 and this repo's
  `addons/ai-diff-reviewer/SKILL.md` "Trust boundary (write scope)".
- **Always `critical` (skills.sh / core no-network promise):** introducing
  `curl` / `wget` / HTTP client usage into the CORE tree
  (`skills/deepworkplan/**` excluding `addons/`) or into
  `skills/deepworkplan/shared/context.sh`. Core methodology + helpers make
  **no network calls** — that is the TRUST.md / skills.sh Pass contract.
  Network references belong only in opt-in addons, and even there never as
  a pipe-to-shell installer (see E005/W012 rule above).

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
- **Always `warning`:** an addon that documents a "required" extra plan
  task, a mandatory pre-create hook, or a blocking dependency on CI /
  provider secrets for the **local** Security Review pass. Optional
  companions during `execute` are fine; new mandatory plan steps are not
  (see methodology criticals above).
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

## Methodology integrity checklist (mandatory when core is in the diff)

If the PR touches core methodology surfaces (list under "Methodology
integrity" above), the review body **MUST** include a short explicit
checklist — pass/fail per row — before the verdict. Do not bury this in
notes; failures are `critical` findings.

| # | Check | Fail when… |
|---|--------|------------|
| M1 | **Long-horizon loop intact** | `create` → plan materialization → `execute` (gates) → `resume`/`status` path is removed, skipped, or described as optional |
| M2 | **`.dwp/` durability** | Plans/drafts/progress no longer live under gitignored `.dwp/`, or resume cannot find recorded state |
| M3 | **Atomic task contract** | Tasks can complete without Acceptance Criteria + Validation (or semantic equivalents) |
| M4 | **Gate discipline** | `execute` may mark `[x]` despite failed validation, unmet AC, or unaccepted SR `critical` |
| M5 | **Mandatory finals** | Order/count of Security Review → Skills & Agents Discovery → Executive Report changed, or an addon adds a fourth mandatory task |
| M6 | **Zero-addon baseline** | Core flows require an addon, CI secret, or commercial service to succeed |
| M7 | **Interruptibility** | A new agent cannot continue a partially executed plan from on-disk progress alone |
| M8 | **Spec ↔ guide ↔ create/execute** | Normative MUST/MUST NOT disagree across those surfaces on the same rule |

When the PR **only** touches addons, CI, or docs outside the core loop,
still skim M5–M6 if the addon claims to wire into Security Review /
`execute` — augment-only, never-block-on-invocation, no new mandatory
task files.

## Repo-specific conventions

- **Methodology first.** Packaging, dogfood, and skills.sh Pass matter —
  but not at the expense of the long-horizon plan loop. If a change forces
  a tradeoff, protect `create` / `execute` / `resume` / finals / `.dwp/` /
  zero-addon conformance first.
- **skills.sh Security Audits (user-trust invariant).** The public page
  <https://www.skills.sh/dailybothq/deepworkplan-skill/deepworkplan>
  continuously shows Gen Agent Trust Hub / Socket / Snyk. Maintainers
  MUST keep all three at **Pass** on every release that changes
  `skills/deepworkplan/**`. Known FAIL vectors already hit in production:
  Snyk E005 + Socket W012 on literal remote-installer pipes inside opt-in
  addon docs (`6a05ed9`). After a security fix merges, skills.sh can lag
  before the dashboard flips — that lag is NOT a green light to add new
  risky strings. Before merging skill-tree changes, mentally re-run the
  TRUST.md self-audit greps (no network in core; no `curl|sh` / `irm|iex`
  anywhere in the pack) and confirm every write-capable `SKILL.md` still
  has a Trust boundary section.
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
  everything else PATCH), bumps every in-tree `skills/deepworkplan/**/SKILL.md`
  in sync (router + sub-skills + all addons), updates `CHANGELOG.md`, tags
  `vX.Y.Z`, and re-vendors the dogfood copy.
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
  every other in-tree `skills/deepworkplan/**/SKILL.md` (router +
  sub-skills + all addons — currently 14) moved to the same version.
  Mismatch fails `validate-frontmatter.py` in CI.
- If a new addon under `skills/deepworkplan/addons/` was added → verify
  SPEC.md + templates/ + SKILL.md + validation checklist all exist, and
  `addons/README.md` was updated with the new addon row.
- If `.github/workflows/auto-release.yml` changed → verify every
  `npx skills add` invocation still carries both `--yes` AND `-y`.
- If a `SKILL.md` under `.agents/skills/` (any of the three vendored
  skills) was edited by hand → this is almost certainly a bug; the
  vendored copies are refreshed by `auto-release.yml` or `skills update`.
- If `skills/deepworkplan/**` changed → dual checklist:
  **(A) Methodology integrity** — run the M1–M8 table above whenever
  create/execute/refine/resume/status/verify/onboard/spec/guide/router
  are in the diff; for addon-only diffs, at least M5–M6.
  **(B) skills.sh / trust** —
  1. No one-line remote-installer / fetch-and-execute literals anywhere
     in the pack (addons included) — describe the ban without spelling
     the pipe command when editing docs under `skills/deepworkplan/**`.
  2. No new network clients in core or `shared/context.sh`.
  3. Every `SKILL.md` with write-capable `allowed-tools` still has a
     Trust boundary / write-scope section.
  4. After merge + release, expect the
     [skills.sh listing](https://www.skills.sh/dailybothq/deepworkplan-skill/deepworkplan)
     Security Audits row to stay (or return to) Pass / Pass / Pass —
     dashboard lag is normal; a known bad string in the tree is not.
