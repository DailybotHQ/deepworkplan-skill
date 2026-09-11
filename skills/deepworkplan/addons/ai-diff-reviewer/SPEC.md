# SPEC.md — AI Diff Reviewer Addon (Normative)

## Abstract

This document is the **normative specification** of the DeepWorkPlan **AI Diff
Reviewer addon**: a capability — **required in its local form since standard
2.3.0, optional in its CI form** — that connects an AI-first repository to
the **AI Diff Reviewer** (`DailybotHQ/ai-diff-reviewer`, marketplace listing
"AI Diff Reviewer", current **v2.0.0**) so DWP work — the mandatory
security pass of the mandatory **Final Review** — is augmented with a structured local review
(verdict + findings table + severity), and (in **Flow B — dual-surface**,
optionally) every pull request to the target repo is gated by a CI-side
review Action with byte-identical parity to the local review. It defines the
**two officially-supported adoption flows** (§3), **what the addon
installs/configures** (local review required, CI surface opt-in, §4), how it **defers authentication and
wizard orchestration** to the upstream skill's own consent flows (§5), how
the **security-pass augmentation** and the optional **`apply-review`
post-CI companion** are wired into DWP execution (§6), the **never-block**
rule (§7), the **reconcile-don't-clobber** behavior (§8), the **validation
checklist** (§9), and the **archetype compatibility** notes (§10).

The addon is governed by [`../README.md`](../README.md) and
[`spec/ADDONS.md`](../../spec/ADDONS.md) §6.5: its **local review is part of
baseline conformance** for repositories declaring standard 2.3.0 or newer; its
CI surface is never required.

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 2.16.3 |
| **Status** | Stable |
| **Companions** | `SKILL.md`, `templates/INTEGRATION.md`, `../README.md`, `spec/ADDONS.md`, `../../create/SKILL.md`, `../../guide/authoring.md` §5.4 |
| **License** | MIT |
| **Upstream reference** | `DailybotHQ/ai-diff-reviewer` v2.0.0 (marketplace: "AI Diff Reviewer") |

## 1. Conventions

The RFC 2119 keywords (**MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**,
**MAY**, **OPTIONAL**) are interpreted as in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

Throughout, the **upstream skill** is the vendored coding-agent skill
([`DailybotHQ/ai-diff-reviewer`](https://github.com/DailybotHQ/ai-diff-reviewer)),
a **router with five coordinated sub-skills**:

1. **Parent default flow** — run the local review on the current branch.
2. **`generate-extension`** — author repo-tailored `.review/extension.md`.
3. **`setup`** — install the CI workflow (also the reference manual for every
   `action.yml` input via `setup/reference.md`).
4. **`open-pr`** — draft the PR title + body from the diff.
5. **`apply-review`** (included since v1.7.0) — read the CI review on the current
   branch's PR and walk through findings per-finding (apply / defer / skip)
   with explicit consent. Read-only by default; edits require per-finding
   yes; never commits or pushes.

The **CI Action** is the GitHub Marketplace listing "AI Diff Reviewer"
([`DailybotHQ/ai-diff-reviewer@v2`](https://github.com/marketplace/actions/ai-diff-reviewer)),
same repository as the skill. The skill's `prompt.md` is **byte-identical**
to the Action's shipped `prompts/default.md` at the same tag (enforced by
upstream CI's `Skills — prompt-sync invariant` job).

---

## 2. Vendor-Neutral Guardrail (the rule that frames everything)

- The **local review is part of the DeepWorkPlan baseline** since standard
  2.3.0: `onboard` **MUST** install the vendored skill and bootstrap an
  extension file (Phase 7a), a targeted harness upgrade **MUST** reconcile
  both when missing, and the Final Review's security pass **MUST** run the
  local review (§6.1). A repository declaring standard 2.3.0 or newer without
  the vendored skill and an extension file is **not** conformant; `verify`
  reports the gap as a failure (as a harness-version finding for a legacy
  repository).
- The **CI surface (Flow B) MUST remain opt-in**: never installed unrequested,
  never the default, never a precondition of any DWP flow.
- What stays vendor-neutral: the reviewer is an MIT-licensed, tag-pinned skill
  executed by the developer's own coding agent. DWP **MUST NOT** require a
  commercial service, a CI provider or a provider secret for any of
  create / execute / refine / resume / status / verify / onboard to succeed.
- A developer **MAY** decline the local reviewer; the decline **MUST** be
  recorded as a declared exception in `AGENTS.md` and in the onboarding
  report, and the repository is reported as non-conformant on that point until
  the reviewer is installed. Nothing else in the baseline changes.

---

## 3. Two Supported Adoption Flows

The upstream skill v2.0.0 defines two flows explicitly. This addon applies
Flow A as the baseline and **MUST** offer Flow B as an explicit opt-in.

### 3.1 Flow A — local-only

- Vendored skill installed; the CI Action is **NOT** installed.
- Sub-skills used: **parent default flow** (security-pass augmentation) +
  **`generate-extension` (required)** + optionally `open-pr`.
- Extension requirement: addon onboarding **MUST NOT** complete Flow A
  without an extension file at a recognized path (or an explicit
  `.review/.skip-bootstrap` opt-out, which means the local SR pass will not
  fire). Skill-only install is incomplete for SR detection (§6.1).
- Sub-skills skipped: `setup` (would install the workflow, opting the repo
  into Flow B against the developer's intent), `apply-review` (no CI review
  posts back to any PR without the Action installed).
- Suitable for: personal repos, experimental repos, or teams not (yet) ready
  for automated PR review.

### 3.2 Flow B — dual-surface

- Vendored skill installed + `setup` sub-skill runs the wizard to write
  `.github/workflows/pr-review.yml` referencing `.review/extension.md`.
- Sub-skills used: **all five** — parent + `generate-extension` + `setup` +
  `open-pr` + `apply-review`.
- Suitable for: team repos, production-facing repos, and anything where an
  automated PR merge gate is wanted.

### 3.3 Consent-time rules

- The addon **MUST** apply Flow A (the baseline) and offer Flow B at consent
  time. It **MUST NOT** default to Flow B or install the CI workflow
  unrequested.
- When the developer's signal about Flow B is ambiguous, the addon **MUST**
  ask or stay on Flow A; it **MUST NOT** infer Flow B. The ambiguity
  resolution mirrors upstream v2.0.0's own policy: unrelated
  workflows (CI tests, deploy pipelines, dependency bots) are **NOT**
  evidence of Flow B — only an existing ai-diff-reviewer workflow is.
- The addon **SHOULD** surface the concrete Flow-A-vs-B tradeoff at consent
  time: token-cost predictability (Flow A: only when the developer asks) vs
  merge-gate enforcement (Flow B: every labeled PR).
- The recorded flow decision **SHOULD** be documented in the target repo's
  `AGENTS.md` so future maintainers see it.

---

## 4. What the Addon Installs / Configures (local review REQUIRED, CI surface OPT-IN)

The addon installs or configures the following — §4.1 and §4.2 under the
onboarding consent (required, §2), §4.3 and §4.5 only on explicit Flow B
acceptance — each reconciled if already present (§8):

### 4.1 The upstream skill (both flows)

- The addon **MUST** install the vendored skill (the only supported install
  path) unless the developer recorded a declared exception (§2).
  Supported install method:
  - `npx --yes skills add DailybotHQ/ai-diff-reviewer@v2.0.1 --skill ai-diff-reviewer -y`
    (**tag-pinned**; both flags are required — `--yes` covers npm's own "Ok to
    proceed?" prompt; the subcommand `-y` covers the `skills` CLI's own "Which
    agents do you want to install to?" picker, which hangs in non-TTY without
    it — upstream fixed this bug in v1.7.0. Pin whatever tag is current at
    install time; the pin is what makes the install verifiable and the
    local↔CI parity guarantee exact.)
  - Bump to the latest published tag: `npx --yes skills update ai-diff-reviewer -y`.
- The vendored skill lands at `.agents/skills/ai-diff-reviewer/`. Its
  source + content hash are recorded in `skills-lock.json` for reproducible
  restores.
- The addon **MUST NOT** substitute a one-line remote-installer pipe (any
  variant of "fetch from the network and execute in one command") — that
  pattern is unverifiable at the reader's terminal and is flagged as a
  critical delivery-vector risk by every mainstream security auditor (Snyk
  rule E005, Socket W012).

### 4.2 Repo-tailored `.review/extension.md` (both flows)

- The addon **MUST** ensure an extension file exists (or an explicit
  `.review/.skip-bootstrap` opt-out is recorded) **before** finishing
  onboarding. Prefer handing off to the upstream `generate-extension`
  sub-skill (≥12 tool-call Discovery followed by a ~100-line file of
  concrete overrides). This is the primary customization surface — where
  consumers encode their own severity rules and "don't comment on" scopes.
  Without an extension, security-pass detection (§6.1) fails and the
  advertised local pass never runs.
- The addon **MUST** honor the upstream's three-path precedence when
  detecting an existing extension file (first match wins):
  1. `.review/extension.md` (recommended, runtime-agnostic).
  2. `.github/ai-diff-reviewer/extension.md` (fallback for teams that
     prefer `.github/` sibling to workflow files).
  3. `.github/ai-pr-reviewer/extension.md` (pre-v1.5 back-compat, still
     recognized by upstream).
- The addon **MUST NOT** invent a third location. When writing a new file,
  the addon **SHOULD** use `.review/extension.md` (runtime-agnostic).
- The addon **MUST** respect the `.review/.skip-bootstrap` opt-out marker
  (a tracked 0-byte file created when a developer previously answered
  "never" to upstream's bootstrap offer). When that marker is present, the
  addon **MUST NOT** bootstrap during onboarding or during later `execute`
  the Final Review's security pass — document that the local augmentation stays inactive
  until the marker is removed and an extension is created.
- Mid-plan `execute` **MUST NOT** surprise-bootstrap an extension file as a
  side effect of the Final Review (aligns with `execute/SKILL.md`).

### 4.3 CI workflow `pr-review.yml` (Flow B only)

- When the developer chose Flow B, the addon **MUST** hand off to the
  upstream `setup` sub-skill's 6-question wizard rather than hand-rolling
  the workflow file. The wizard produces `.github/workflows/pr-review.yml`
  adapted to the consumer's answers (provider / strictness / trigger mode /
  external-contributor policy / PR-description mode / complexity labels).
- The workflow **MUST** pin the upstream Action to the **v2** major-line tag
  (`DailybotHQ/ai-diff-reviewer@v2`) so patch-level fixes flow automatically.
  Pinning to a frozen tag (`@v2.0.0`) is also acceptable — parity with the
  vendored skill's version is what makes local ≡ CI worth it. New installs
  **MUST NOT** pin `@v1`.
- The workflow **SHOULD** enable the v2 emergency-bypass input
  `skip-review-label: skip-ai-review` (opt-in; empty means the feature is
  OFF). Document that anyone who can apply that label can bypass the LLM
  review — protect it with a repository ruleset when the AI review is a
  merge gate. This is distinct from `full-review-please` (IAR escape: one
  full review, not a skip).
- CI reviews under v2 run **Iteration-Aware Review (IAR)** by default
  (`convergence-policy: first-pass-exhaustive`). Local skill reviews remain
  a full pass (no IAR dedup). Soften "local ≡ CI" claims accordingly —
  shared `prompt.md` + extension still align methodology/severity; round 2+
  CI may be shorter.
- The addon **MUST NOT** duplicate the wizard, the input reference manual
  ([`setup/reference.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/skills/ai-diff-reviewer/setup/reference.md)),
  or the workflow shape into its own templates. `templates/INTEGRATION.md`
  provides a minimal fallback shape when the developer wants to skip the
  wizard; the wizard is the primary path.

### 4.4 Documentation notes in AGENTS.md (both flows)

- The addon **SHOULD** append a short section to the target repo's
  `AGENTS.md` documenting:
  - Which flow was chosen (A or B) and why.
  - The Final Review security-pass augmentation (both flows).
  - (Flow B) the `pr-review.yml` behavior, the provider-secret requirement,
    the label workflow (`ready` / `pr-reviewed` / optional `skip-ai-review`),
    the `AI review gate` branch-protection target, and the `apply-review`
    post-CI walkthrough companion.
- The section is short-form; the full detail lives in the vendored skill's
  own `SKILL.md` (which any agent already reads).

### 4.5 Provider secret documentation (Flow B only)

- The addon **MUST** point the maintainer at the CI provider secret setup
  (typical: `CURSOR_API_KEY` for the Cursor provider): Settings > Secrets
  and variables > Actions > New repository secret. The addon **MUST NOT**
  prompt for or store the secret itself.

---

## 5. Deferred Authentication and Wizard Handoff

- The addon **MUST** defer all authentication and workflow authoring to the
  upstream skill's own flows (`setup/SKILL.md`, `setup/reference.md`).
- The addon **MUST NOT** prompt for API keys, MUST NOT bypass or weaken any
  upstream consent flow, and **MUST NOT** store any credential in any file
  it creates.
- The addon **MUST NOT** reimplement the `setup` wizard, the `open-pr`
  Conventional-Commits inference, the `generate-extension` Discovery, the
  `apply-review` walkthrough, or the review formatting — every one of these
  belongs to the upstream skill; the addon points at them.
- If the developer declines any part of the setup, the addon **MUST** skip
  that part and continue — installation issues **MUST NOT** block the
  primary work (§7).

---

## 6. Integration Points into DWP Execution

This is the "why": when present, the **security pass** of the mandatory
**Final Review** in every DWP plan gets a structured local review pass, and in Flow B a
developer-invoked companion sub-skill closes the loop on any post-push CI
review.

### 6.1 Augment the Final Review's security pass (both flows — MUST, with honest degradation)

The addon **MUST** wire an additive step into the DWP `create` sub-skill's
`{N}.task_final_review.md` template's security pass. When the addon is installed
(detected by `.agents/skills/ai-diff-reviewer/` present + an extension file
at one of the three recognized paths from §4.2), the Final Review's security pass gains
an additional post-existing-checks step:

1. Invoke the upstream **parent default flow** ("Review my current branch").
2. Capture the reviewer's output: **verdict + findings table + per-finding
   body + notes + recommendation** (the parity contract from the upstream
   skill's Step 4).
3. Append the output to `analysis_results/SECURITY_REVIEW.md` under a
   dedicated `## AI Diff Reviewer local review` heading — so a reader can
   see the manual SR findings and the AI-augmented findings side by side.
4. Severity handling: `critical` findings follow the existing SR contract
   and block completion until fixed or explicitly accepted. `warning` and
   `info` findings are appended and reported but do not block.

- The step is **MUST**, with honest degradation: when the vendored skill or
  the extension file is absent, the security pass **MUST** record a `local
  reviewer not installed` finding in `SECURITY_REVIEW.md` and carry it into
  the completion report. Installation is an onboarding action; the Final
  Review **MUST NOT** surprise-bootstrap a missing piece. A coding-agent /
  upstream-skill invocation error of a review that could start follows §7.
  Do **not** treat an unset CI provider secret as an invocation skip — that
  secret is Flow B CI/gate only. Once a local review **did** run, severity
  handling above (§6.1 item 4) still applies.
- The augmentation is **additive**. The Final Review's own manual security
  reasoning is preserved. Every new 2.3.0 Final Review template includes this
  local-review step; when the reviewer is absent, the step records its missing-
  reviewer finding instead of being omitted. Legacy plans retain their own
  recorded shape.
- **Legacy plans.** A plan created under the pre-2.3.0 lifecycle carries a
  separate `{N-2}.task_security_review.md`. The addon augments *that* task in
  such a plan — same additive step, same severity contract — because a plan is
  always executed under its own recorded shape and is never silently migrated.

### 6.2 CI merge gate (Flow B only)

- The Flow B workflow is separate from any single plan; it applies going
  forward to every PR to the repo's default branch when the maintainer
  applies the configured label (default: `ready`).
- The `AI review gate` job is stable-named (chosen by the upstream `setup`
  wizard) for branch protection.
- **Skipped ≠ Failed.** A PR without the trigger label reports the gate as
  Skipped (green-adjacent grey), which the branch-protection rule treats as
  passing. This is the designed idle behavior — MUST NOT be interpreted as
  a bug.

### 6.3 Post-CI apply-review companion (Flow B only, OPTIONAL)

- When a plan's PR has been pushed and CI has posted its review, the
  developer **MAY** invoke the upstream `apply-review` sub-skill from within
  the same DWP `execute` session to walk through CI findings per-finding
  (apply / defer / skip) with explicit per-finding consent.
- `apply-review` is **read-only by default**. Source-file edits require an
  explicit yes per finding. It **never commits and never pushes** — commit +
  push remains the developer's judgment call.
- Multi-provider awareness: if consumers change the workflow to a matrix
  (e.g. `self-reviewed:anthropic`, `-cursor`, `-codex`, `-claude-code`),
  `apply-review` attributes each finding to its leg and surfaces cross-leg
  consensus automatically.
- The addon **MUST** describe `apply-review` in the target repo's docs as
  an *available option* during `execute` — never as a mandatory extra task.
  The addon **MUST NOT** materialize `apply-review` as a plan task file —
  doing so would violate the mandatory-final-task rule (a plan ends with the
  single Final Review, and nothing may follow it) and turn a
  developer-invoked convenience into a scheduled plan step.

---

## 7. Never-Block Rule (mandatory)

Soft-fail applies to **invocation** of the local review pass only — not to
the Final Review's gate results after a review completed. Post-run severity
is governed by §6.1 (item 4): `critical` findings block the Final Review's
completion until fixed or explicitly accepted.

- **Local augmentation — invocation soft-fail (Flow A and Flow B):** if the
  network is **down** or any upstream skill invocation **errors**, the
  addon's wired local-review step **MUST**: warn briefly once, record the
  failed invocation in `SECURITY_REVIEW.md`, continue the primary task,
  **not** retry automatically, and **not** enter a diagnostic loop. An
  **absent** skill or extension file is not an invocation failure: it is
  handled by §6.1 (recorded finding; installation is onboarding-only), never by
  a silent skip. This mirrors the upstream skill's own
  trust-boundary guarantees. The local parent default flow runs via the
  coding agent and does **not** require a CI provider secret — an unset
  `CURSOR_API_KEY` (or other provider secret) **MUST NOT** suppress the
  local security pass.
- **Local augmentation — after a review ran:** open/`critical` findings
  from that pass **MUST** follow §6.1. Agents **MUST NOT** mark the Final
  Review `[x]` while those criticals remain unfixed and unaccepted. §7 does
  **not** override that gate.
- **Flow B CI / gate only:** when the dual-surface workflow is installed,
  document that the provider secret MUST be set for the CI Action to run;
  warn maintainers when it is unset. That warning **MUST NOT** skip or
  weaken the local SR augmentation.
- Plan execution **MUST** proceed when the local review was **skipped or
  errored** at invocation (soft-fail above). Plan execution **MUST NOT**
  treat "review ran with open criticals" as an invocation skip.
- The CI merge gate (Flow B) **MUST NOT** block merges when the trigger
  label is not applied — Skipped, not Failed. This is enforced by the
  upstream `setup` wizard's default output.

---

## 8. Reconcile, Don't Clobber

- The addon **MUST** detect existing setup before acting: an already-vendored
  skill at `.agents/skills/ai-diff-reviewer/`, an existing extension file at
  any of the three recognized paths, an existing `pr-review.yml` or any
  workflow with `uses: DailybotHQ/ai-diff-reviewer` (or the pre-rename
  `DailybotHQ/ai-pr-reviewer`), a `.review/.skip-bootstrap` opt-out marker,
  or provider-secret documentation.
- Where a piece already exists, the addon **MUST** preserve it and only
  fill gaps.
- **Migration constraint.** If an extension file exists at the fallback
  path (`.github/ai-diff-reviewer/extension.md`) or the back-compat path
  (`.github/ai-pr-reviewer/extension.md`), the addon **MUST NOT** migrate
  it silently to the recommended `.review/extension.md` — ask.
- Any destructive change to an existing file **MUST** be approved by the
  user first (`AGENT_PROTOCOL.md`); the addon **MUST** record what it
  changed.

---

## 9. Conformance + Validation Step

A repo is **conformant to this addon** when **all** hold (after acceptance):

1. The vendored skill is installed at `.agents/skills/ai-diff-reviewer/`
   with the version invariant asserted against `skills-lock.json`, **or**
   the addon recorded why it could not install here (sandbox/CI, or a
   declared exception per §2) without failing onboarding — a recorded gap,
   never a silent one.
2. An extension file is present at one of the three recognized paths (or
   the developer explicitly opted out via `.review/.skip-bootstrap`).
3. Authentication was **deferred** to the upstream skill's own consent flow
   — no API-key prompting and **no credential** written by this addon.
4. The chosen flow (A or B) is recorded in `AGENTS.md` (or equivalent
   docs), and the DWP execution docs describe the security-pass
   local review as **required with honest degradation**: a missing skill or
  extension is a recorded finding and installation remains onboarding-only
  (§6.1), invocation errors soft-fail (§7); `critical` findings from a
   **completed** pass still follow the SR contract (§6.1 / §7).
5. (Flow B only) `.github/workflows/pr-review.yml` exists with the upstream
   Action pinned to `@v2` (or a specific tag), the stable-named gate job
   is present for branch protection, the provider secret is documented in
   AGENTS.md, and the label-gate + author-association policies match what
   the maintainer chose during the `setup` wizard.
6. Existing vendored-skill / extension-file / workflow files were
   **reconciled**, not clobbered.
7. The vendor-neutral guardrail holds (§2): nothing in the repo implies DWP
   requires a commercial service, CI provider or secret; the CI surface is
   documented as optional.
8. No one-line remote-installer / fetch-and-execute install path was
   recommended anywhere in the addon.

---

## 10. Compatibility

### 10.1 Individual repo archetype

- Standard use case. Both flows apply directly. The security-pass
  augmentation wires into the repo's own DWP plans.

### 10.2 Orchestrator hub archetype

- Orchestrator hubs typically install this addon **per sub-repo**, not on
  the hub itself. Each sub-repo picks its own flow (some sub-repos may
  choose Flow A; others may choose Flow B).
- The hub's own workflows MAY or MAY NOT use the AI Diff Reviewer
  independently. The addon does not prescribe hub behavior.
- Child DWPs materialized inside sub-repos gain the SR augmentation from
  each sub-repo's own installation (or don't, if the sub-repo declined
  the addon) — the hub-level plan does not need to know.

---

## 11. References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)
- `SKILL.md` (the onboarding hook + flow), `templates/INTEGRATION.md` (reasoning aid)
- `../README.md` (addon mechanism), [`../../spec/ADDONS.md`](../../spec/ADDONS.md) (concept + pointer)
- Upstream skill: [`DailybotHQ/ai-diff-reviewer`](https://github.com/DailybotHQ/ai-diff-reviewer)
  — `skills/ai-diff-reviewer/SKILL.md` (currently **v2.0.0**), sub-skills:
  `generate-extension/SKILL.md`, `setup/SKILL.md` +
  [`setup/reference.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/skills/ai-diff-reviewer/setup/reference.md),
  `open-pr/SKILL.md`, `apply-review/SKILL.md`.
- Marketplace listing: ["AI Diff Reviewer"](https://github.com/marketplace/actions/ai-diff-reviewer).
- [`../../create/SKILL.md`](../../create/SKILL.md) Step 4.4 (“Local review step (required)”) — where the Final Review local-review wiring is authored into every 2.3.0 plan.
- [`../../guide/authoring.md`](../../guide/authoring.md) §5.4 — the canonical security-discipline rules the Final Review's security pass applies.

---

*Part of the DeepWorkPlan methodology, MIT License, by [Dailybot](https://dailybot.com) / dailybotops.*
