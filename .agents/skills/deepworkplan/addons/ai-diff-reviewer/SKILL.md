---
name: deepworkplan-addon-ai-diff-reviewer
description: "Optional DeepWorkPlan addon that connects an AI-first repo to the AI Diff Reviewer (DailybotHQ/ai-diff-reviewer on GitHub, \"AI Diff Reviewer\" on the Marketplace, current v2.0.0) — installing (with consent) the vendored coding-agent skill (DailybotHQ/ai-diff-reviewer, five sub-skills — parent default flow, generate-extension, setup, open-pr, apply-review) and, if the developer picks Flow B (dual-surface), letting the upstream setup sub-skill write .github/workflows/pr-review.yml so every pull request to the target repo is reviewed in CI with byte-identical parity to the local review. Wires the mandatory DWP Security Review task to run the parent default flow (\"Review my current branch\") as an additive step producing verdict + findings table + severity, appended under a dedicated heading in analysis_results/SECURITY_REVIEW.md. In Flow B, also surfaces the upstream apply-review sub-skill as an OPTIONAL developer-invoked companion during execute for walking through CI-posted findings per-finding (apply / defer / skip) with explicit consent. Opt-in, never required, never blocks on missing skill/extension/invocation errors (completed-review critical findings still follow the Security Review contract), reconciles existing setups instead of clobbering them, defers all install/auth/wizard details to the upstream skill's own consent flows, and lets consumers pick Flow A (local-only) or Flow B (dual-surface) — never guesses, always asks. Use when the developer or team wants structured local review + optional CI merge gate on DWP work."
version: "2.17.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"🔍","homepage":"https://deepworkplan.com","requires":{"anyBins":["git","gh"]}}}
---

# DeepWorkPlan — AI Diff Reviewer Addon

Connect the target repo to the **[AI Diff Reviewer](https://github.com/DailybotHQ/ai-diff-reviewer)** (GitHub repo `DailybotHQ/ai-diff-reviewer`, marketplace listing **"AI Diff Reviewer"**, current **v2.0.0**) so DWP work — the mandatory **Security Review** final task — is augmented with a structured local review (verdict + findings table + severity), and (in Flow B, optionally) every pull request to the target repo is gated by a CI-side review Action pinned to the same tag for byte-identical parity. This is an **opt-in addon**; it is **never** required for a repo to be AI-first. Missing skill/extension or invocation errors **never block** the work; `critical` findings from a **completed** local review still follow the existing Security Review contract (block until fixed or explicitly accepted).

> ## The rule that overrides everything: this addon DEFERS, it does not reinvent
>
> The upstream **`DailybotHQ/ai-diff-reviewer`** skill (currently **v2.0.0**)
> already owns install, review methodology, the CI-workflow wizard, the
> extension-file authoring flow, the PR-body drafting flow, and the post-CI
> apply-review walkthrough — as five coordinated sub-skills (parent default
> flow, `generate-extension`, `setup`, `open-pr`, `apply-review`). **This
> addon's job is narrow**: (1) **offer** to install the vendored skill through
> its own consent flow, (2) **ask** whether the consumer wants Flow A
> (local-only) or Flow B (dual-surface) — never guess, matching the upstream
> skill's own ambiguity tie-break policy, (3) if Flow B, defer to the
> upstream `setup` sub-skill for the CI workflow, and (4) **wire** the parent
> default flow into DWP `create`/`execute` so the mandatory Security Review is
> augmented with a local review pass, plus (Flow B only) surface `apply-review`
> as an available companion for post-CI walkthrough. It MUST NOT duplicate,
> bypass, or weaken any upstream consent, auth, wizard, or review flow — it
> points at them. (Normative source: [`SPEC.md`](SPEC.md).)

## Positioning guardrail (read before anything)

The **core DeepWorkPlan methodology has ZERO AI Diff Reviewer dependency.** It
is vendor-neutral, MIT, and agent-agnostic. A repo with **zero addons** —
including this one — is fully conformant. This addon adds *structured
code-review quality* to DWP work for developers who want it; declining leaves
a fully AI-first repo. Never present the AI Diff Reviewer as a precondition
for DWP, and never auto-install it for everyone.

## Two officially-supported adoption flows

The upstream skill (v2.0.0+) defines **two flows** and requires consumers to
pick explicitly. This addon MUST offer both at consent time and MUST NOT
default to either.

| Flow | Use when | Sub-skills used | Sub-skills skipped |
|------|----------|-----------------|--------------------|
| **A — local-only** | Personal repos, experimental repos, or teams not (yet) ready for automated PR review. The vendored skill runs locally; the CI Action is NOT installed. | parent default flow (Security Review augmentation) + **`generate-extension` (required for SR detection)** + optionally `open-pr` | `setup` (would install the workflow), `apply-review` (nothing to apply back — no CI review posts) |
| **B — dual-surface** | Team repos, production-facing repos, and anything where automated PR review is wanted. Skill + CI Action, both wired to the same `.review/extension.md` for byte-identical parity. Recommended for team repos. | All five: parent + `generate-extension` + `setup` + `open-pr` + `apply-review` | Nothing — all capabilities are used across the plan lifecycle |

**Parity guarantee (Flow B).** The upstream skill's `prompt.md` is
**byte-identical** to the Action's shipped `prompts/default.md` at the same
release tag (enforced by the upstream `Skills — prompt-sync invariant` CI
job). Pinning the same version on both surfaces guarantees identical reviews.
When `setup` wires `prompt-extension-file: .review/extension.md`, the CI
Action reads the same file your local agent uses → same base prompt + same
extension = same review, locally and in CI.

## Read these first (all relative inside the skill)

- [`SPEC.md`](SPEC.md) — the normative (RFC-2119) contract: two flows, what is
  installed (all opt-in), how auth is deferred, how the Security Review
  augmentation is wired, the optional `apply-review` companion, the
  never-block rule, and the vendor-neutral guardrail.
- [`templates/INTEGRATION.md`](templates/INTEGRATION.md) — reasoning guidance
  (NOT copy-paste): detect-if-already-installed, how to ask for the flow, how
  to wire the Security Review augmentation, and the consent / never-block
  rules.
- `../README.md` — the addon mechanism (opt-in, reconcile-don't-clobber, contract).

## When this runs

- From **`onboard` Phase 7b** — after the core AI-first scaffolding, `onboard`
  offers this addon alongside devcontainer / dailybot / dependency-upgrade /
  design-system; if accepted it reads this SKILL and runs the flow below.
- **Directly** — `/deepworkplan-addon-ai-diff-reviewer` on an already-onboarded
  repo to add the review integration.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit` and `Write`. Exactly what this
addon may write — and what it MUST NOT — is enumerated below. Skills.sh / Gen
Agent Trust Hub treat `allowed-tools` as a trust boundary; this section is the
human-readable contract for that field. Anything not listed here does not
happen.

**Reads (always allowed, no consent needed):**

- Local files under the current git checkout via `Read` / `Grep` / `Glob` /
  `Bash` (detection only: existence of `.agents/skills/ai-diff-reviewer/`,
  extension-file paths, `pr-review.yml`, `.review/.skip-bootstrap`).
- Upstream sub-skill docs under `.agents/skills/ai-diff-reviewer/**` once
  installed (to hand off correctly).

**Writes (only after explicit developer acceptance of the relevant step):**

- **Vendored skill install** — via `npx --yes skills add … -y` / `npx --yes
  skills update … -y` into `.agents/skills/ai-diff-reviewer/` +
  `skills-lock.json`. Never run without Step 1 consent.
- **Extension file** — hand off to upstream `generate-extension` (writes
  `.review/extension.md` or a consumer-chosen path). This addon itself does
  NOT invent severity rules; it only triggers the upstream sub-skill after
  the developer accepts the bootstrap offer.
- **CI workflow (Flow B only)** — hand off to upstream `setup` (writes
  `.github/workflows/pr-review.yml` and related labels). This addon itself
  does NOT hand-roll the workflow or invent provider secrets.
- **AGENTS.md / docs notes (optional)** — a short pointer that the addon is
  installed and which flow was chosen, only when the developer accepts a
  docs-update prompt. Reconcile; never clobber existing sections.
- **Plan-time Security Review append** — during `execute`, append the local
  review output under `## AI Diff Reviewer local review` in
  `analysis_results/SECURITY_REVIEW.md` (plan working state, typically
  gitignored). Never rewrite the rest of that file.

**It MUST NOT:**

- Store, echo, or commit provider secrets (`CURSOR_API_KEY`, API tokens).
- Pipe a remote installer into a shell (any single-line fetch-and-execute
  variant).
- Auto-install for everyone or default to Flow B when the flow question is
  unanswered.
- Clobber an existing `.review/extension.md`, `pr-review.yml`, or vendored
  skill — reconcile gaps only.
- `git commit` / `git push` as part of the addon flow (those belong to the
  surrounding DWP `execute` / maintainer workflow).
- Edit source files under the consumer's application tree — review findings
  are applied (if at all) by the upstream `apply-review` sub-skill under its
  own per-finding consent contract, not by this addon.

## The flow

### Step 0 — Consent + recommend-only-if-relevant + choose the flow

1. **Confirm relevance.** Offer this addon only when it makes sense: the
   developer or team wants structured code-review quality on DWP work, or
   explicitly asks for local pre-push review or PR merge-gating. In trust/auto
   mode you MAY recommend it **only** on that signal — do **not** auto-install
   for everyone. If the developer declines, stop cleanly; the repo stays
   baseline-conformant.

2. **Ask the flow question — do NOT guess.** This matches upstream v2.0.0's
   own ambiguity tie-break policy. Present both flows plainly:

   > This addon supports two adoption modes:
   >
   > **Flow A — local-only.** Vendored skill + a repo-tailored extension
   > file (via `generate-extension`); no GitHub Actions changes. Best for
   > personal or experimental repos, or teams not (yet) ready for automated
   > PR review. Once both are present, the DWP Security Review is augmented
   > with a local review pass — skill alone is not enough.
   >
   > **Flow B — dual-surface.** Skill + CI Action, both reading the same
   > `.review/extension.md` for byte-identical parity. Every PR to `main`
   > gets an AI review in CI, gated on a label of your choice (typical:
   > `ready`). Recommended for team repos.
   >
   > Which flow?

   If the signal is unclear, ask; never default to Flow B (installing the
   workflow unrequested is a much bigger footprint than declining Flow B and
   only using the local review).

3. **Detect existing setup (reconcile-don't-clobber).** Before installing
   anything, check what is already present (see `templates/INTEGRATION.md`):
   - Vendored skill already installed at `.agents/skills/ai-diff-reviewer/`?
   - Extension file at one of the three recognized paths (in precedence
     order): `.review/extension.md` > `.github/ai-diff-reviewer/extension.md`
     > `.github/ai-pr-reviewer/extension.md` (pre-v1.5 back-compat)?
   - `.review/.skip-bootstrap` marker present (developer opted out of the
     bootstrap offer previously — respect it)?
   - `.github/workflows/pr-review.yml` or any workflow with
     `uses: DailybotHQ/ai-diff-reviewer` (or the pre-rename
     `DailybotHQ/ai-pr-reviewer` — the 301 redirect keeps old pins working)?
   - Provider secret documented anywhere (typical: `CURSOR_API_KEY`)?

   If a piece already exists, **do not redo it** — record it and only fill
   gaps.

### Step 1 — Offer the vendored skill install (OPT-IN, defer consent)

Present the install path and let the developer choose; **never run an
installer without their explicit acceptance**.

- **Vendored coding-agent skill** (recommended — brings the five-sub-skill
  router and the byte-identical prompt parity guarantee; current **v2.0.0**):
  - `npx --yes skills add DailybotHQ/ai-diff-reviewer --skill ai-diff-reviewer -y`
    (vendors into `.agents/skills/ai-diff-reviewer/` and records
    source + content hash in `skills-lock.json`; both `--yes` and `-y` are
    required — `--yes` covers npm's own prompt, subcommand `-y` covers the
    `skills` CLI's own "Which agents do you want to install to?" picker,
    which hangs in non-TTY without it — upstream fixed this in v1.7.0).
  - Or pin to a specific tag: `... DailybotHQ/ai-diff-reviewer@v2.0.0 ...`.
  - Bump to the latest with `npx --yes skills update ai-diff-reviewer -y`.

> **Do not reimplement the install, and never pipe a remote installer to a
> shell.** The `npx skills` command is the supported, checksummed install
> path — it records the content hash in `skills-lock.json` for reproducible
> restores.

### Step 1b — Bootstrap the extension file (REQUIRED for both flows)

Security Review detection (SPEC §6.1 / `create` / `execute`) requires
**skill + an extension file** at one of the three recognized paths. Do
**not** finish addon onboarding without one — otherwise every later
Security Review will warn "install incomplete" and skip the local pass.

1. If an extension already exists at a recognized path → record it; do not
   clobber (and do not migrate fallback/back-compat paths silently — ask).
2. If `.review/.skip-bootstrap` is present → the developer previously opted
   out. Respect it: document that the local SR augmentation will not fire
   until they remove the marker and create an extension; do not surprise-
   bootstrap later during `execute`.
3. Otherwise → hand off to upstream `generate-extension` (or let the
   developer hand-write `.review/extension.md`) **before** proceeding to
   Step 2 / Step 3. Preferred handoff: *"generate a `.review/extension.md`
   for this repo"*.

Mid-plan `execute` **MUST NOT** surprise-bootstrap an extension — that is
an onboarding concern, not a Security Review side effect.

### Step 2 — CI workflow install — DEFER to the upstream `setup` sub-skill (Flow B only)

Do **not** hand-roll `.github/workflows/pr-review.yml`, do **not** prompt for
API keys, and do **not** store any credential. When the developer chose
Flow B, hand off to the upstream `setup` sub-skill — its 6-question wizard
produces a workflow tuned to the consumer's choices (provider / strictness /
trigger mode / external-contributor policy / PR-description mode /
complexity labels), and [`setup/reference.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/skills/ai-diff-reviewer/setup/reference.md)
doubles as the reference manual for every `action.yml` input.

- Point at the vendored skill: `.agents/skills/ai-diff-reviewer/setup/SKILL.md`.
- Handoff phrase: *"Set up AI Diff Reviewer for this repo"* (or
  `/ai-diff-reviewer-setup`) — workflow + label bootstrap only. Step 1b already
  required the extension file for both flows; do **not** re-enter
  `generate-extension` here unless Step 1b was skipped (e.g. explicit
  `.review/.skip-bootstrap` opt-out and the developer later reversed it).
- Provider secret: the wizard tells the maintainer which secret to configure
  (typical: `CURSOR_API_KEY` for the Cursor provider). Maintainer sets it at
  Settings > Secrets and variables > Actions.

The addon **MUST NOT** reimplement the wizard. If the developer wants to skip
the wizard, `templates/INTEGRATION.md` provides a fallback shape and points
at the reference manual — but the wizard is the primary path.

### Step 3 — Wire the Security Review augmentation into DWP execution

This is the integration value. Reasoning guidance is in
`templates/INTEGRATION.md` — adapt it to the repo; do not copy verbatim.

- Add a short, clearly-optional note to the repo's DWP execution docs (the
  generated `AGENTS.md` reporting section and/or `docs/AI_AGENT_COLLAB.md`)
  describing that **when this addon is installed**, the mandatory
  `{N-2}.task_security_review.md` template gains an additional post-existing-checks step:

  1. **Local review augmentation (both flows)** — invoke the upstream
     parent default flow ("Review my current branch"). Capture verdict +
     findings table + per-finding body + notes + recommendation. Append to
     `analysis_results/SECURITY_REVIEW.md` under a dedicated
     `## AI Diff Reviewer local review` heading. A `critical` finding
     follows the existing SR contract — blocks completion until fixed or
     explicitly accepted. `warning` / `info` findings are appended and
     reported but do not block.

  2. **Optional post-CI walkthrough companion (Flow B only)** — after the
     plan's PR has been pushed and CI has reviewed it, the developer MAY
     invoke the upstream `apply-review` sub-skill from within the same
     `execute` session to walk through CI findings per-finding (apply /
     defer / skip) with explicit consent. `apply-review` is **read-only by
     default**; source-file edits require an explicit yes per finding; it
     **never commits and never pushes**. This is surfaced as an *available
     option*, not a new plan task file — the addon **MUST NOT** insert an
     `apply-review` task into any plan.

- Every hook MUST be **best-effort and conditional**: the local Security
  Review pass fires only when the vendored skill is present **and** an
  extension file is detected, and it **MUST NOT block** `create` or
  `execute` if the skill is absent, detection fails, or the local review
  invocation errors — warn once and continue (see SPEC §7 Never-block).
  Do **not** skip the local pass because a CI provider secret is unset;
  that secret is Flow B CI / gate messaging only.

- The reviewer's `.review/extension.md` (repo-tailored via the upstream
  `generate-extension` sub-skill, either through the bootstrap offer or
  invoked explicitly) shapes what maps to which severity. This is the
  primary customization surface; consumers who want repo-specific review
  rules author them here.

### Step 4 — Validate (SPEC §9 Validation)

Run the validation checklist and report: whether the vendored skill is
present with the correct version, whether an extension file is present at
one of the three recognized paths, whether (Flow B) the workflow file is
present with the upstream Action pinned to `@v2`, whether the provider
secret is documented in AGENTS.md, whether the stable-named gate job (if
Flow B) is `AI review gate` for branch protection, and any deferred items.
If nothing could be installed here (sandbox/CI), say why — do not silently
skip, and do not fail the onboarding.

## Failure-mode guardrails

- **Never required; invocation never blocking.** If declined — or if the
  vendored skill is missing, detection fails, or the local review
  invocation errors — stop/continue cleanly. The repo stays
  baseline-conformant. Once a local review **ran**, open `critical`
  findings still block Security Review completion until fixed or
  explicitly accepted (SPEC §6.1 / §7). An unset CI provider secret does
  not skip the local Security Review pass (Flow B CI/gate only).
- **Defer to upstream.** No wizard reimplementation, no review-methodology
  reimplementation, no apply-review reimplementation. Point at the vendored
  sub-skills.
- **Verified install only.** Never recommend piping a remote installer to a
  shell. Use `npx --yes skills add … -y` — pinned via `skills-lock.json`
  with content-hash verification.
- **Reconcile, don't clobber.** An existing extension file, workflow, or
  vendored skill is preserved; only fill gaps. Never migrate a file at
  `.github/ai-diff-reviewer/extension.md` (or the back-compat
  `.github/ai-pr-reviewer/extension.md`) to `.review/extension.md` silently
  — ask.
- **Vendor-neutral.** Never imply DWP needs the AI Diff Reviewer. This addon
  is purely additive review quality.
- **Both flows are first-class.** Flow A (local-only) is a supported use
  case, not a degraded mode. The addon MUST ask; MUST NOT default to Flow B.
