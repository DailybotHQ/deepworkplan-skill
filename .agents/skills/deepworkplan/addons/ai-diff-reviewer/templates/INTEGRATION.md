# Template — AI Diff Reviewer Integration (reason, don't copy-paste)

Reasoning guidance for wiring the AI Diff Reviewer addon into a target repo.
This is **not** a file to drop in verbatim — the commands, workflow shape,
and doc wording are **reasoned against the target repo** (its stack, its
actual DWP execution docs, whether it is public/private, whether it wants
Flow A or Flow B, whether it already has any review workflow). Keep the
SPEC contract intact: **opt-in, defer to upstream, never block,
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
grep -l 'CURSOR_API_KEY\|ANTHROPIC_API_KEY\|OPENAI_API_KEY' \
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

## 2. Ask the flow question — do NOT guess

Matching upstream v2.0.0's own ambiguity tie-break policy: when the signal is
unclear, **ask**. Never default to Flow B (installing the workflow
unrequested is a much bigger footprint than declining Flow B).

Present both flows plainly:

> This addon supports two adoption modes:
>
> **Flow A — local-only.** Vendored skill + a repo-tailored extension
> file (via `generate-extension`); no GitHub Actions changes. Best for
> personal or experimental repos, or teams not (yet) ready for automated
> PR review. Once both are present, Security Review gains a local review
> pass — skill alone is not enough.
>
> **Flow B — dual-surface.** Skill + CI Action, both reading the same
> `.review/extension.md` for byte-identical parity. Every PR to your default
> branch gets an AI review in CI, gated on a label of your choice (typical:
> `ready`). Recommended for team repos. Adds an optional `apply-review`
> companion for walking through CI findings after push.
>
> Which flow?

Signals that clarify the answer without asking:

- Explicit "local-only", "no CI Action", "just want the skill" → Flow A.
- Explicit "full setup", "install the workflow", "gate my PRs" → Flow B.
- Personal repo, experimental repo, or maintainer says "not ready to
  automate" → default suggestion Flow A (still ask).
- Team repo with existing review culture, `.github/CODEOWNERS`, and other
  automated PR quality checks → default suggestion Flow B (still ask).
- **Ambiguous → ASK.** Do NOT interpret the presence of unrelated workflows
  (CI tests, deploy pipelines, dependency bots) as evidence of Flow B —
  only an existing ai-diff-reviewer workflow is.

Record the chosen flow in `AGENTS.md` (or equivalent docs) so future
maintainers and future agent runs see it — mirrors upstream's own recommended
signalling ("Flow A / Flow B" phrases every subsequent request).

---

## 3. Install the vendored skill (OPT-IN — never run without acceptance)

```bash
npx --yes skills add DailybotHQ/ai-diff-reviewer --skill ai-diff-reviewer -y

# Verify the vendored version matches the requested tag / latest
VENDORED=$(sed -nE 's/^version:[[:space:]]*"([^"]+)".*/\1/p' \
  .agents/skills/ai-diff-reviewer/SKILL.md | head -1)
echo "Vendored: $VENDORED"

# Pin to a specific tag for reproducibility (optional)
# npx --yes skills add DailybotHQ/ai-diff-reviewer@v2.0.0 --skill ai-diff-reviewer -y

# Bump later
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

Security Review detection needs **skill + extension**. Finish this during
**addon onboarding** (after the vendored skill install, before declaring
the addon installed). Do **not** rely on mid-plan `execute` / Security
Review to heal a missing extension — `execute/SKILL.md` forbids surprise-
bootstrap there (warn once that Flow A/B install is incomplete, continue
the base Security Review).

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

The wizard asks:

1. **Provider** (anthropic / claude-code / cursor / codex — pick one, or a
   matrix).
2. **Strictness** (block-on-critical / block-on-warning / advisory).
3. **Trigger mode** (label-gated / on-open / on-synchronize).
4. **External-contributor policy** (author-association whitelist).
5. **PR-description mode** (require / skip).
6. **Complexity labels** (auto-apply / skip).

It writes `.github/workflows/pr-review.yml` adapted to the answers, sets up
the label-bootstrap step, and generates the stable-named gate job for
branch protection. Point at [`setup/reference.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/skills/ai-diff-reviewer/setup/reference.md)
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
      - uses: DailybotHQ/ai-diff-reviewer@v2
        with:
          provider: <provider>
          api-key: ${{ secrets.<PROVIDER>_API_KEY }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          prompt-extension-file: .review/extension.md
          strictness: block-on-critical
          # Opt-in emergency bypass (v2). Empty = feature OFF. Protect the
          # label with a repo ruleset if the AI review is a merge gate.
          skip-review-label: skip-ai-review
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
- **`skip-review-label: skip-ai-review`** (v2) is the opt-in emergency
  bypass — when that label is on the PR the Action short-circuits with a
  successful check and a ⏭️ skipped tracking comment (no LLM). Distinct
  from `full-review-please` (IAR escape: full review once, not skip).
- **Pin `@v2`** (moving major) or `@v2.0.0` (frozen). Do not pin `@v1` on
  new installs — v2 is the current pin surface (IAR + skip-review).
- **`AI review gate`** is stable-named so branch protection can be
  configured against it once and continue to work when the review-job name
  changes across provider matrices.
- **Skipped ≠ Failed for label/author scope only.** A PR without the
  trigger label stays mergeable; a requested review with a missing provider
  secret MUST fail the gate.
- The wizard version is preferred because it handles multi-provider
  matrices, complexity-label integration, external-contributor policy edge
  cases, and label-bootstrap. Only hand-roll when the developer explicitly
  asks to skip the wizard.

---

## 6. Wire the Security Review augmentation into DWP execution

Once the addon is installed, the DWP `create` sub-skill's
`{N-2}.task_security_review.md` template already carries the augmentation
callout (added by `../../create/SKILL.md` — search for
`ai-diff-reviewer`). Every plan materialized in this repo from now on will
carry the addon-augmented SR body.

Add a short, clearly-optional note to the repo's DWP execution docs (the
generated `AGENTS.md` reporting section and/or `docs/AI_AGENT_COLLAB.md`).
The shape to convey:

> **Optional — AI Diff Reviewer review augmentation (best-effort on
> invocation; criticals still gate SR):** when the AI Diff Reviewer addon
> is installed (detected via `.agents/skills/ai-diff-reviewer/` + an
> extension file), the mandatory Security Review task gains an additional
> local review pass. Invokes the upstream skill's parent default flow
> ("Review my current branch"), captures verdict + findings table +
> severity, and appends them to `analysis_results/SECURITY_REVIEW.md`
> under `## AI Diff Reviewer local review`. Soft-fail (warn + skip) only
> if the skill/extension is missing or the local review errors. Once a
> review ran, a `critical` finding blocks completion until fixed or
> explicitly accepted; `warning` / `info` findings are appended and
> reported but do not block. In Flow B, an OPTIONAL post-PR companion is
> available — the `apply-review` sub-skill walks through CI-posted
> findings per-finding (apply / defer / skip) with explicit consent,
> read-only by default, never commits or pushes.

Decision notes:

- **Both flows benefit from the SR augmentation.** The local review runs
  the same base prompt + extension file regardless of whether the CI Action
  is wired. The parity guarantee (`prompt.md` byte-identical between skill
  and Action) is only material in Flow B; in Flow A the local review IS
  the whole reviewer.
- **`apply-review` is a companion, not a task.** The addon MUST NOT insert
  an `apply-review` task file into any plan — it's a developer-invoked
  convenience during `execute`, surfaced when the addon is installed AND
  Flow B is active AND a PR exists for the plan's branch.
- **Reconcile:** if the repo's DWP docs already mention a review step,
  correct or keep it; do not duplicate.

---

## 7. Consent + never-block rules (do not violate)

- **Opt-in:** install nothing, write no extension file, commit no workflow,
  and add no docs without explicit acceptance. Ask about the flow — never
  default to Flow B.
- **Defer to upstream:** never reimplement the `setup` wizard, the
  `generate-extension` Discovery, the `open-pr` inference, the
  `apply-review` walkthrough, or the review methodology. Point at the
  vendored sub-skills.
- **Verified install only:** never recommend piping a remote installer to
  a shell. Use `npx --yes skills add … -y` — pinned via `skills-lock.json`
  with content-hash verification.
- **Never block (invocation only):** the wired **local** review step is
  best-effort to *start*; absence of the skill, missing extension file, or
  invocation/network errors — all mean skip-and-continue — warn once, no
  retries, no diagnostic loop. Once a review **ran**, `critical` findings
  follow the existing Security Review contract (block until fixed or
  explicitly accepted) — do not mark SR `[x]` anyway. An unset CI provider
  secret is a Flow B CI/gate warning only — it MUST NOT suppress the local
  Security Review pass (Flow A needs no secret).
- **Vendor-neutral:** never imply DWP requires the AI Diff Reviewer. A
  repo with zero addons is fully conformant.
- **Both flows are first-class:** Flow A (local-only) is a supported use
  case, not a degraded mode. Whichever the consumer picks, run the flow's
  sub-skill set and stop.
