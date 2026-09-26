# Template — AI Diff Reviewer Integration (reason, don't copy-paste)

Reasoning guidance for wiring the AI Diff Reviewer addon into a target repo.
This is **not** a file to drop in verbatim — the commands, workflow shape,
and doc wording are **reasoned against the target repo** (its stack, its
actual DWP execution docs, whether it is public/private, whether it wants
Flow A or Flow B, whether it already has any review workflow). Keep the
SPEC contract intact: **local review required / CI surface opt-in, defer to
upstream, never block,
reconcile-don't-clobber, vendor-neutral, both flows are first-class.**

Read [`../SKILL.md`](../SKILL.md) and [`../SPEC.md`](../SPEC.md) first.

---

## 1. Detect if the AI Diff Reviewer is already installed (reconcile-don't-clobber)

Run these **before** offering to install anything. Where a piece exists, do
not redo it — record it and only fill gaps.

```bash
# Is the vendored skill already installed?
ls -d .agents/skills/ai-diff-reviewer/ 2>/dev/null && \
  sed -nE 's/^version:[[:space:]]*"([^"]+)".*/\1/p' \
    .agents/skills/ai-diff-reviewer/SKILL.md 2>/dev/null | head -1

# Is skills-lock.json tracking it?
grep -l '"skillPath":[[:space:]]*"skills/ai-diff-reviewer/' skills-lock.json 2>/dev/null

# Is an extension file already present? Check all three recognized paths
# in precedence order (first match wins per upstream skill's Step 2).
ls .review/extension.md 2>/dev/null                              # 1. recommended
ls .github/ai-diff-reviewer/extension.md 2>/dev/null             # 2. fallback
ls .github/ai-pr-reviewer/extension.md 2>/dev/null               # 3. back-compat

# Is the opt-out marker present? (developer previously answered "never" to
# upstream's Step 2.5 bootstrap offer — respect it)
ls .review/.skip-bootstrap 2>/dev/null

# Is a review workflow already wired?
grep -l 'DailybotHQ/ai-diff-reviewer\|DailybotHQ/ai-pr-reviewer' \
  .github/workflows/*.y*ml 2>/dev/null

# Is a provider secret documented?
grep -l 'CURSOR_API_KEY\|ANTHROPIC_API_KEY\|OPENAI_API_KEY\|XAI_API_KEY' \
  AGENTS.md docs/*.md .github/README.md 2>/dev/null
```

Decision notes:

- **Vendored skill present** → do not reinstall. Verify the version invariant
  against `skills-lock.json`. If lagging, offer `npx --yes skills update ai-diff-reviewer -y`.
- **Extension file present at any path** → keep it. Never migrate silently
  from `.github/ai-diff-reviewer/extension.md` (or the back-compat
  `.github/ai-pr-reviewer/extension.md`) to `.review/extension.md` — ask.
- **`.review/.skip-bootstrap` present** → the developer opted out of the
  bootstrap offer. The addon MUST NOT re-offer it and MUST NOT delete the
  marker. To re-enable, the developer deletes the marker themselves.
- **Workflow present** → do not overwrite. If the maintainer wants to switch
  providers or change the label gate, hand off to the upstream `setup`
  sub-skill to regenerate (it's idempotent and reconciles).
- **Provider secret documentation present** → keep it; only extend to
  mention the label workflow if missing.

---

## 2. Offer the CI surface separately — do NOT guess

On the CI offer, mirror the upstream skill's own ambiguity tie-break policy:
when the signal is unclear, **ask**. Never default to Flow B (installing the
workflow unrequested is a much bigger footprint than declining Flow B).

Install Flow A (local skill plus extension) under the existing onboarding
request, without a second flow-choice confirmation. CI is a separate offer:
only an explicit request or accepted offer authorizes Flow B. A production repo,
CODEOWNERS, unrelated CI or an unanswered offer is not CI authorization.
Preserve existing reviewer configuration and previously accepted choices.

Record the chosen flow in `AGENTS.md` (or equivalent docs) so future
maintainers and future agent runs see it — mirrors upstream's own recommended
signalling ("Flow A / Flow B" phrases every subsequent request).

---

## 3. Install the vendored skill (REQUIRED — covered by the onboarding consent; never unpinned)

```bash
# Tag-pinned install: pin the current published tag at install time (this is
# the reproducible form; the moving @v3 is the documented default pin for
# CI workflows).
npx --yes skills add DailybotHQ/ai-diff-reviewer@v3.1.1 --skill ai-diff-reviewer -y

# Verify the vendored version matches the requested tag
VENDORED=$(sed -nE 's/^version:[[:space:]]*"([^"]+)".*/\1/p' \
  .agents/skills/ai-diff-reviewer/SKILL.md | head -1)
echo "Vendored: $VENDORED"

# Bump later (updates to the latest published tag)
# npx --yes skills update ai-diff-reviewer -y
```

**Critical: both `--yes` and `-y` are required.** `npx --yes` covers npm's
own "Ok to proceed?" prompt. The subcommand `-y` covers the `skills` CLI's
own "Which agents do you want to install to?" picker (interactive in
non-TTY hangs indefinitely). Upstream `ai-diff-reviewer` fixed exactly this
bug in v1.7.0 after their own auto-release ran without the subcommand `-y`
and left a partially-published release. Do NOT drop either flag.

The install vendors the skill into `.agents/skills/ai-diff-reviewer/` and
records source + content hash in `skills-lock.json` so teammates can restore
identical bytes with `npx skills experimental_install`.

---

## 4. Bootstrap the extension file (REQUIRED — both flows, during onboarding)

Security-pass detection needs **skill + extension**. Finish this during
**addon onboarding** (after the vendored skill install, before declaring
the addon installed). Do **not** rely on mid-plan `execute` / Security
Review to heal a missing extension — `execute/SKILL.md` forbids surprise-
bootstrap there (warn once that Flow A/B install is incomplete, continue
the base security pass).

Where possible, hand off to the upstream `generate-extension` sub-skill —
its ≥12 tool-call Discovery produces a repo-specific file grounded in the
actual codebase, not templated boilerplate.

- **During addon onboarding, no extension yet** — invoke `generate-extension`
  explicitly: *"generate a `.review/extension.md` for this repo"*. Do not
  defer this to a later parent-default-flow bootstrap prompt.
- **Hand-written** — the developer writes the file directly using the
  upstream skill's examples. Best when the overrides are already known.
- **Already present** — reconcile; do not clobber. Do not silently migrate
  `.github/…/extension.md` → `.review/extension.md`.
- **`.review/.skip-bootstrap` present** — respect the opt-out; document that
  the local SR augmentation stays inactive until the marker is removed and
  an extension exists.

Extension file location — use `.review/extension.md` when writing a new one.
Reason: runtime-agnostic, works even for teams that don't use GitHub
Actions. The `.github/ai-diff-reviewer/extension.md` fallback is fine for
teams that prefer keeping the file next to workflows; both are recognized
by the upstream skill.

---

## 5. Install the CI workflow (Flow B only) — DEFER to `setup`

Do **not** hand-roll `.github/workflows/pr-review.yml`. Hand off to the
upstream `setup` sub-skill's 6-question wizard:

```
Invoke: "Set up AI Diff Reviewer for this repo" (or /ai-diff-reviewer-setup)
```

The wizard asks (v3):

1. **Runner and backend** — the runner drives the review loop
   (`anthropic` / `openai` in-process, or the `claude-code` / `codex` /
   `grok` / `cursor` CLIs); the backend is where the model lives
   (`api-base`, the provider secret, and a suggested `model` — `balanced`
   by default).
2. **Strictness** (`lenient` / `block-on-critical` / `block-on-warning` /
   `block-on-any`).
3. **Trigger mode** (every push to the PR / `trigger-mode: label-once` +
   `label-gate: ready` — toggle the label off/on to re-run /
   `label-added-only`).
4. **External contributors** (author-association whitelist).
5. **PR-description mode** (`off` / `warn` / `block` / `autocomplete`).
6. **Complexity labels** (apply / skip).

It writes the workflow adapted to the answers — a single review (verifier
and risk-tiered budgets on by default) or, on request, the RFC-04 ensemble
matrix (`mode: emit` read-only legs + one `mode: aggregate` job) — sets up
the label-bootstrap step, and generates the stable-named gate job for
branch protection. Consumers on pre-v3 workflows keep working unchanged. Point at [`setup/reference.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/skills/ai-diff-reviewer/setup/reference.md)
as the reference manual for every `action.yml` input.

**Fallback (developer wants to skip the wizard).** Prefer the wizard. If you
must hand-roll, **mirror the shipped four-job pattern** (`scope` →
`labels-bootstrap` → `review` → stable-named `AI review gate`) from this
repo's `.github/workflows/pr-review.yml` (or the upstream `setup` wizard
output) — do **not** invent a two-job gate that embeds `needs.review.result`
directly in a `run:` script and treats every `skipped` as success (that
silently greens merges when the review never ran for reasons other than
"no ready label", including `no-provider-secret`).

Minimum review-job inputs (the gate/scope jobs still come from the wizard
or a full copy of the four-job workflow):

```yaml
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: DailybotHQ/ai-diff-reviewer@v3
        with:
          provider: <provider>
          api-key: ${{ secrets.<PROVIDER>_API_KEY }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          prompt-extension-file: .review/extension.md
          strictness: block-on-critical
          # v3 defaults, shown so you know what to change:
          verifier: 'on'        # verified criticals (BC-07): a critical publishes
                                # as critical only when the verifier confirms it
          budget-profile: auto  # risk-tiered budgets — 8/20/30/40 turns (BC-13);
                                # 'fixed' restores the pre-v3 constants (transition knob)
          # high-risk-paths: 'glob, list'  # raises the risk tier to critical (raises only)
          # Opt-in emergency bypass. Empty = feature OFF. Protect the
          # label with a repo ruleset if the AI review is a merge gate.
          skip-review-label: skip-ai-review
      # Optional ensemble (RFC-04): `mode: emit` read-only legs + one
      # `mode: aggregate` job that dedups by anchor, verifies once and
      # publishes one review — see the upstream examples/ensemble-matrix.yml
```

The gate job **MUST** map results through `env:` (never embed
`${{ needs.*.result }}` directly in a shell script), fail loud on
`no-provider-secret`, and only treat label/author skips as non-blocking —
see the shipped `gate` job in `pr-review.yml`.

Reasoning notes:

- **`fetch-depth: 0`** on `actions/checkout` is REQUIRED — the Action diffs
  `origin/<base>...HEAD` and needs the base ref locally. A shallow
  checkout yields a broken or empty review. This repo's `pr-review.yml`
  and the upstream `setup` wizard both set it.
- **`persist-credentials: false`** on `actions/checkout` is REQUIRED — the
  reviewer runs with broad local access; no credential should persist.
- **`skip-review-label: skip-ai-review`** is the opt-in emergency bypass —
  when that label is on the PR the Action short-circuits with a successful
  check and a ⏭️ skipped tracking comment (no LLM). Distinct from the IAR
  escape label (`iteration-escape-label`, default `full-review-please`),
  which forces one full review instead of skipping.
- **Pin `@v3`** (moving major) or a frozen `@v3.x.y`. Do not pin `@v1`/`@v2`
  on new installs; existing `@v2` pins keep working (frozen maintenance line
  on `release/v2`, six months of security/catalog fixes).
- **`AI review gate`** is stable-named so branch protection can be
  configured against it once and continue to work when the review-job name
  changes across provider matrices.
- **Skipped ≠ Failed for label/author scope only.** A PR without the
  trigger label stays mergeable; a requested review with a missing provider
  secret MUST fail the gate. Since v3, an **`incomplete` or `timeout`
  review is red under blocking strictness** (BC-04 — it posts partial
  findings and fails the check), and `block-on-critical` fires on
  **verified** criticals (BC-07); `strict-unverified-criticals: true`
  restores claim-based gating during the transition.
- The wizard version is preferred because it handles multi-provider
  matrices, complexity-label integration, external-contributor policy edge
  cases, and label-bootstrap. Only hand-roll when the developer explicitly
  asks to skip the wizard.

---

## 6. Wire the security-pass augmentation into DWP execution

Once the addon is installed, the DWP `create` sub-skill's
`{N}.task_final_review.md` template already carries the augmentation
callout (added by `../../create/SKILL.md` — search for
`ai-diff-reviewer`). Every plan materialized in this repo from now on will
carry the addon-augmented SR body.

Add a short note to the repo's DWP execution docs (the generated
`AGENTS.md` reporting section and/or `docs/AI_AGENT_COLLAB.md`). The
shape to convey:

> **Required — AI Diff Reviewer local review (baseline since standard
> 2.3.0; verified criticals still gate SR):** the Final Review's security
> pass always runs the local review. Invokes the upstream skill's parent
> default flow ("Review my current branch"), captures verdict + findings
> table + severity, and appends them to
> `analysis_results/SECURITY_REVIEW.md` under `## AI Diff Reviewer local
> review`. If `.agents/skills/ai-diff-reviewer/` or the extension file is
> missing, record a `local reviewer not installed` finding and carry it into
> the completion report — never a silent skip. Installation belongs to
> onboarding or an explicit addon invocation. Soft-fail
> (warn once, record, continue) applies only to **invocation errors** of
> a review that could start. Once a review ran, a **verified** `critical`
> finding blocks completion until fixed or explicitly accepted (v3, BC-07:
> unverified critical claims arrive as annotated warnings — visible and
> non-blocking unless `strict-unverified-criticals: true`); a review with
> `status: incomplete` or `timeout` is not a clean pass under blocking
> strictness (BC-04); `warning` / `info` findings are appended and
> reported but do not block. In Flow B (opt-in CI surface), an OPTIONAL
> post-PR companion is available: the `apply-review` sub-skill walks
> through CI-posted findings per-finding (apply / defer / skip) with
> explicit consent, read-only by default, never commits or pushes — and
> the `address-review` sub-skill (new in v3.1.1) is the one-invocation
> alternative: find the branch's open PR(s), check the review is fresh for
> the current head, present the findings, then on one yes apply, commit,
> push and re-arm the reviewer (label-gated → toggle the label;
> push-triggered → confirm the new run; no workflow → offer the local
> review). On aggregated (ensemble) reviews it reads the aggregate
> document and the `ai-pr-reviewer-aggregate` marker. When wiring
> automation, prefer the structured output (`review-output/3.0`; outputs
> `structured-output-path` / `-sha256`) over scraping review bodies — the
> document carries the run record, the findings with verification, and
> the gate. A body that says `Recommendation: approve` is not evidence
> the check passed — read the tracking marker's Highest severity /
> Strictness gate / Check status block first.

Decision notes:

- **Both flows benefit from the SR augmentation.** The local review runs
  the same base prompt + extension file regardless of whether the CI Action
  is wired. The parity guarantee (`prompt.md` byte-identical between skill
  and Action) is only material in Flow B; in Flow A the local review IS
  the whole reviewer.
- **`apply-review` / `address-review` are companions, not tasks.** The
  addon MUST NOT insert a task file for either into any plan — they are
  developer-invoked conveniences during `execute`, surfaced when the addon
  is installed AND Flow B is active AND a PR exists for the plan's branch.
- **Reconcile:** if the repo's DWP docs already mention a review step,
  correct or keep it; do not duplicate.

---

## 7. Consent + never-block rules (do not violate)

- **Consent:** the onboarding consent covers the pinned skill install and
  the extension bootstrap (a decline is a recorded declared exception);
  commit no workflow and add no Flow B piece without explicit acceptance —
  never default to Flow B.
- **Defer to upstream:** never reimplement the `setup` wizard, the
  `generate-extension` Discovery, the `open-pr` inference, the
  `apply-review` walkthrough, the `address-review` loop, or the review
  methodology. Point at the vendored sub-skills.
- **Verified install only:** never recommend piping a remote installer to
  a shell. Use `npx --yes skills add <repo>@<tag> … -y` — the tag pin plus
  `skills-lock.json` content-hash verification is what makes the install
  reproducible and auditable.
- **Never block (invocation only):** the wired **local** review step is
  best-effort to *start*; invocation/network errors mean
  warn-once-record-and-continue — no retries, no diagnostic loop. An absent
  skill or extension file is a recorded `local reviewer not installed`
  finding, carried into the completion report, never a silent skip. Installation
  belongs to onboarding or an explicit addon invocation. Once a review **ran**, **verified** `critical`
  findings follow the existing Final Review contract (block until fixed or
  explicitly accepted); unverified critical claims arrive as annotated
  warnings (BC-07) — do not mark SR `[x]` anyway. An unset CI provider
  secret is a Flow B CI/gate warning only — it MUST NOT suppress the local
  security pass (Flow A needs no secret).
- **Vendor-neutral:** DWP never requires a commercial service, CI provider
  or secret; the local reviewer is a pinned MIT skill run by the developer's
  own agent, and a repo with zero optional addons is fully conformant.
- **Both flows are first-class:** Flow A (local-only) is a supported use
  case, not a degraded mode. Whichever the consumer picks, run the flow's
  sub-skill set and stop.
