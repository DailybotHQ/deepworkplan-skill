---
name: deepworkplan-addon-ai-diff-reviewer
description: "DeepWorkPlan addon — required local review (baseline since standard 2.3.0), optional CI surface — connects an AI-first repo to the AI Diff Reviewer. Onboarding installs the vendored coding-agent skill and extension with consent; the Final Review runs the local pass when present or records a missing-reviewer finding without bootstrapping. Flow B CI setup remains an explicit opt-in delegated to upstream. Invocation errors never block, completed-review critical findings still follow the Final Review contract, and all install/auth/wizard details defer to upstream consent flows."
version: "4.0.3"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"🔍","homepage":"https://deepworkplan.com","requires":{"anyBins":["git","gh"]}}}
---

# DeepWorkPlan — AI Diff Reviewer Addon

Connect the target repo to the **[AI Diff Reviewer](https://github.com/DailybotHQ/ai-diff-reviewer)**
(GitHub repo `DailybotHQ/ai-diff-reviewer`, marketplace listing **"AI Diff
Reviewer"**, current **v2.0.0**) so DWP work — the mandatory security pass of
the mandatory **Final Review** — runs a structured local review (verdict +
findings table + severity), and (in Flow B, optionally) every pull request is
gated by the same review in CI. Since standard 2.3.0 the **local review is part
of the baseline**: `onboard` installs it (Phase 7a), a targeted harness upgrade
reconciles it, and every Final Review runs it. Only the CI surface is opt-in.

> ## The rule that overrides everything: this addon DEFERS, it does not reinvent
>
> The upstream **`DailybotHQ/ai-diff-reviewer`** skill (currently **v2.0.0**)
> already owns install, review methodology, the CI-workflow wizard, the
> extension-file authoring flow, the PR-body drafting flow, and the post-CI
> apply-review walkthrough — as five coordinated sub-skills (parent default
> flow, `generate-extension`, `setup`, `open-pr`, `apply-review`). **This
> addon's job is narrow**: (1) **install** the vendored skill, pinned, under
> the onboarding consent (a decline is a recorded declared exception), (2)
> **apply** Flow A (local-only) as the baseline and **offer** Flow B
> (dual-surface) as an explicit opt-in — never install the CI surface
> unrequested, (3) if Flow B, defer to the
> upstream `setup` sub-skill for the CI workflow, and (4) **wire** the parent
> default flow into DWP `create`/`execute` so the Final Review's security pass is
> augmented with a local review pass, plus (Flow B only) surface `apply-review`
> as an available companion for post-CI walkthrough. It MUST NOT duplicate,
> bypass, or weaken any upstream consent, auth, wizard, or review flow — it
> points at them. (Normative source: [`SPEC.md`](SPEC.md).)

## Positioning guardrail (read before anything)

The **local review is part of the DeepWorkPlan baseline** since standard 2.3.0
(`spec/ADDONS.md` §6.5): every onboarded repository gets the vendored skill and
a repo-tailored extension file, and every Final Review runs the local review
over the plan's accumulated change set. What stays vendor-neutral, MIT and
agent-agnostic is the boundary that matters: the reviewer is a tag-pinned
skill executed by the developer's **own** coding agent — **no commercial
service, no CI provider and no provider secret is ever required** by any DWP
flow. The CI surface (Flow B) is the only piece that touches a provider, and
it is offered, never assumed. A developer may decline the local reviewer; the
decline is recorded as a declared exception in `AGENTS.md` and `verify`
reports the repository as non-conformant on that point until it is installed.
A repo with **zero optional addons** is fully conformant.

## Two officially-supported adoption flows

The upstream skill (v2.0.0+) defines **two flows**. This addon applies Flow A
as the baseline every onboarded repo gets and offers Flow B as an explicit
opt-in; it MUST NOT install the CI surface unrequested.

| Flow | Use when | Sub-skills used | Sub-skills skipped |
|------|----------|-----------------|--------------------|
| **A — local-only** | Personal repos, experimental repos, or teams not (yet) ready for automated PR review. The vendored skill runs locally; the CI Action is NOT installed. | parent default flow (security-pass augmentation) + **`generate-extension` (required for SR detection)** + optionally `open-pr` | `setup` (would install the workflow), `apply-review` (nothing to apply back — no CI review posts) |
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
  installed (local review required since 2.3.0; CI surface opt-in), how auth
  is deferred, how the security-pass augmentation is wired, the optional
  `apply-review` companion, the never-block rule, and the vendor-neutral
  guardrail.
- [`templates/INTEGRATION.md`](templates/INTEGRATION.md) — reasoning guidance
  (NOT copy-paste): detect-if-already-installed, how to ask for the flow, how
  to wire the security-pass augmentation, and the consent / never-block
  rules.
- `../README.md` — the addon mechanism (opt-in, reconcile-don't-clobber, contract).

## When this runs

- From **`onboard` Phase 7a** — after the core AI-first scaffolding and
  before the optional addons of Phase 7b, `onboard` reads this SKILL and runs
  the flow below as a required step (the four optional addons — devcontainer /
  dailybot / dependency-upgrade / design-system — are offered afterwards).
- From the **targeted harness upgrade** (`onboard` Phase 0) — when a
  previously onboarded repository lacks the vendored skill or the extension
  file, the upgrade reconciles the missing piece.
- From **`execute`** — the Final Review's security pass runs the local review
  when installed, or records a missing-reviewer finding; it never installs.
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

- **Vendored skill install** — via `npx --yes skills add <repo>@<tag> … -y` /
  `npx --yes skills update … -y` into `.agents/skills/ai-diff-reviewer/` +
  `skills-lock.json`. Installs are tag-pinned (Step 1); never run without
  Step 1 consent.
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
- **Plan-time security-pass append** — during `execute`, append the local
  review output under `## AI Diff Reviewer local review` in
  `analysis_results/SECURITY_REVIEW.md` (plan working state, typically
  gitignored). Never rewrite the rest of that file.

**It MUST NOT:**

- Store, echo, or commit provider secrets (`CURSOR_API_KEY`, API tokens).
- Pipe a remote installer into a shell (any single-line fetch-and-execute
  variant).
- Install the CI workflow (Flow B) unrequested, or default to Flow B when the
  flow question is unanswered.
- Clobber an existing `.review/extension.md`, `pr-review.yml`, or vendored
  skill — reconcile gaps only.
- `git commit` / `git push` as part of the addon flow (those belong to the
  surrounding DWP `execute` / maintainer workflow).
- Edit source files under the consumer's application tree — review findings
  are applied (if at all) by the upstream `apply-review` sub-skill under its
  own per-finding consent contract, not by this addon.

### Supply-chain trust (what a "yes" actually installs)

This addon delegates to third-party artifacts, so the trust chain is stated
explicitly rather than implied:

| Artifact | Source | How it is verified |
|----------|--------|--------------------|
| Vendored skill (five sub-skills) | `DailybotHQ/ai-diff-reviewer` at a **published tag** (current `v2.0.0`) | `skills` CLI records source + content hash in the repo's `skills-lock.json`; a restore re-verifies the hash. Installs are consent-gated (Step 1) and always tag-pinned — never a moving branch. |
| CI Action (Flow B only) | `DailybotHQ/ai-diff-reviewer` GitHub Action, referenced by its `@v2` major line (exact-tag pinning is not how the Actions marketplace references actions) | Each Action release in the `@v2` line ships a `prompt.md` **byte-identical** to the skill's at the matching skill tag — an upstream CI invariant. The skill side is pinned to an exact tag; the Action follows its major line, so reviews stay compatible while picking up patch fixes. |
| Extension file | Generated **locally** by `generate-extension` from the repo's own diff | Never downloaded; reviewed by the developer like any other tracked file. |
| Provider secret (Flow B only) | The maintainer's own `CURSOR_API_KEY`, set in GitHub Settings | This addon never reads, stores, echoes, or commits provider secrets. |

Nothing else is fetched. There is no telemetry, no post-install script, and no
runtime download by this addon itself; the only network action it can prompt
for is the consent-gated, tag-pinned `skills add`/`skills update` above.

## The flow

### Step 0 — Consent + choose the flow

1. **Confirm consent.** During `onboard` and the targeted upgrade, the Phase 0
   consent covers this install: in trust mode proceed; in guided mode state
   what will be installed (the pinned skill tag and the extension file) and
   proceed unless the developer declines. A decline is recorded as a
   **declared exception** in `AGENTS.md` and in the onboarding report; it does
   not make the repository conformant — `verify` reports the gap until the
   reviewer is installed. Never install unpinned.

2. **Offer the CI surface — do NOT guess.** Flow A is the baseline; Flow B is
   an explicit opt-in. Present both flows plainly:

   > This addon supports two adoption modes:
   >
   > **Flow A — local-only.** Vendored skill + a repo-tailored extension
   > file (via `generate-extension`); no GitHub Actions changes. Best for
   > personal or experimental repos, or teams not (yet) ready for automated
   > PR review. Once both are present, the DWP Final Review's security pass is augmented
   > with a local review pass — skill alone is not enough.
   >
   > **Flow B — dual-surface.** Skill + CI Action, both reading the same
   > `.review/extension.md` for byte-identical parity. Every PR to `main`
   > gets an AI review in CI, gated on a label of your choice (typical:
   > `ready`). Recommended for team repos.
   >
   > Which flow?

   If the signal is unclear, stay on Flow A and say so; never default to
   Flow B (installing the workflow unrequested is a much bigger footprint than
   staying on the local review).

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

### Step 1 — Install the vendored skill (REQUIRED — covered by the onboarding consent)

Run the pinned install unless the developer explicitly declined in Step 0
(declared exception). **Never run an unpinned installer.**

- **Vendored coding-agent skill** (recommended — brings the five-sub-skill
  router and the byte-identical prompt parity guarantee; current **v2.0.0**):
  - `npx --yes skills add DailybotHQ/ai-diff-reviewer@v2.0.1 --skill ai-diff-reviewer -y`
    (**pinned to a published tag**; vendors into
    `.agents/skills/ai-diff-reviewer/` and records source + content hash in
    `skills-lock.json`; both `--yes` and `-y` are required — `--yes` covers
    npm's own prompt, subcommand `-y` covers the `skills` CLI's own
    "Which agents do you want to install to?" picker, which hangs in non-TTY
    without it — upstream fixed this in v1.7.0).
  - Bump to the latest published tag with `npx --yes skills update ai-diff-reviewer -y`.

> **Do not reimplement the install, and never pipe a remote installer to a
> shell.** The `npx skills` command is the supported, checksummed install
> path — it records the content hash in `skills-lock.json` for reproducible
> restores.

### Step 1b — Bootstrap the extension file (REQUIRED for both flows)

Security-pass detection (SPEC §6.1 / `create` / `execute`) requires
**skill + an extension file** at one of the three recognized paths. Do
**not** finish addon onboarding without one — otherwise every later Final
Review security pass records a `local reviewer not installed` finding instead of a
review.

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
an onboarding concern, not a side effect of the Final Review.

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

### Step 3 — Wire the security-pass augmentation into DWP execution

This is the integration value. Reasoning guidance is in
`templates/INTEGRATION.md` — adapt it to the repo; do not copy verbatim.

- Add a short note to the repo's DWP execution docs (the generated
  `AGENTS.md` reporting section and/or `docs/AI_AGENT_COLLAB.md`) describing
  that the mandatory `{N}.task_final_review.md` template runs, as a required
  post-existing-checks step in its security pass:

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

- The local review is **required, with honest degradation**: it runs whenever
  the vendored skill is present **and** an extension file is detected. When
  either is missing, the security pass records a `local reviewer not
  installed` finding in `SECURITY_REVIEW.md` and carries it into the completion
  report. Installation is an onboarding action, not a Final Review side effect;
  mid-plan `execute` MUST NOT bootstrap the missing piece. It **MUST NOT
  hard-stop** `create` or `execute`; an invocation error of a review that could
  start is warn-once-record-and-continue (see SPEC §6.1 and §7). Do **not** skip the local pass because a
  CI provider secret is unset; that secret is Flow B CI / gate messaging only.

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

- **Required locally; invocation never blocking.** A missing vendored skill or
  extension file is a recorded finding, never a silent skip and never a hard
  stop of the plan; installation is handled only by onboarding or an explicit
  addon invocation. A
  declined install is a recorded declared exception that `verify` keeps
  reporting. A local review invocation error is warn-once-record-and-continue.
  Once a local review **ran**, open `critical`
  findings still block Final Review completion until fixed or
  explicitly accepted (SPEC §6.1 / §7). An unset CI provider secret does
  not skip the local security pass (Flow B CI/gate only).
- **Defer to upstream.** No wizard reimplementation, no review-methodology
  reimplementation, no apply-review reimplementation. Point at the vendored
  sub-skills.
- **Verified install only.** Never recommend piping a remote installer to a
  shell. Use `npx --yes skills add <repo>@<tag> … -y` — the tag pin plus
  `skills-lock.json` content-hash verification is what makes the install
  reproducible and auditable.
- **Reconcile, don't clobber.** An existing extension file, workflow, or
  vendored skill is preserved; only fill gaps. Never migrate a file at
  `.github/ai-diff-reviewer/extension.md` (or the back-compat
  `.github/ai-pr-reviewer/extension.md`) to `.review/extension.md` silently
  — ask.
- **Vendor-neutral.** The reviewer is an MIT, tag-pinned skill run by the
  developer's own agent; DWP never requires a commercial service, CI
  provider or secret. The optional CI surface is the only piece that touches
  a provider.
- **Both flows are first-class.** Flow A (local-only) is the baseline, not a
  degraded mode. Flow B is offered; the addon MUST NOT install it unrequested
  or default to it.
