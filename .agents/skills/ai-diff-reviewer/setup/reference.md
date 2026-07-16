# AI Diff Reviewer — action.yml reference

Every input the [AI Diff Reviewer](https://github.com/DailybotHQ/ai-diff-reviewer)
GitHub Action accepts, in one place. Adapted from `action.yml` in the
canonical repository; this file is regenerated alongside skill releases,
so it always matches the `@v2` behavior.

**When to read this file:** the developer asks a specific question about
an input — *"what does `strictness` do?"*, *"how do I pin the Claude
Code CLI version?"*, *"is there an MCP config?"*. The
[`SKILL.md`](SKILL.md) wizard only asks about the six most
consequential knobs; everything else is answered here.

**When to skip this file:** the developer wants to install the action
end-to-end. Route to the wizard in [`SKILL.md`](SKILL.md).

---

## Required inputs

Every workflow using AI Diff Reviewer sets these two.

### `api-key`

- **Required.**
- **What it is:** API key (or subscription OAuth token) for the chosen
  provider.
- **Where to get it, by provider:**
  - `anthropic` → https://console.anthropic.com/settings/keys
  - `claude-code` → same as `anthropic` OR run `claude setup-token`
    locally, paste the resulting `sk-ant-oat…` token here to bill
    against a Claude Pro / Max subscription instead of API usage.
  - `cursor` → https://cursor.com/dashboard → Settings → API Keys.
  - `codex` → https://platform.openai.com/api-keys.
- **How to pass it:** `${{ secrets.<NAME> }}` — never inline a key
  literal in the workflow file. GitHub Secrets are set at:
  `https://github.com/<owner>/<repo>/settings/secrets/actions/new`.

### `github-token`

- **Required.**
- **What it is:** Token used to read the PR diff and post the review.
- **Permissions needed:** `pull-requests: write`, `contents: read`.
  Set at the job level:
  ```yaml
  permissions:
    contents: read
    pull-requests: write
  ```
- **Value:** `${{ secrets.GITHUB_TOKEN }}` is the safe default (per-run
  ephemeral token, scoped by the `permissions:` block). Use a PAT or
  bot-account token if you want the review comment attributed to a
  specific bot account.

---

## Provider selection

### `provider`

- **Default:** `anthropic`
- **Choices:** `anthropic` | `claude-code` | `cursor` | `codex`
- **Behavior:**
  - `anthropic` — chat-completions API. Zero install overhead. Sonnet-tier
    default model. Best baseline.
  - `claude-code` — Claude Code CLI, headless agent mode. Same Anthropic
    models; accepts subscription token via `api-key` (see above).
  - `cursor` — Cursor Agent CLI, headless. `model: auto` is unlimited on
    Cursor Pro plans.
  - `codex` — OpenAI Codex CLI, headless. GPT-5.6-luna default.

### `model`

- **Default:** `''` (empty — provider default; see below).
- **Provider-specific defaults:**
  - `anthropic` → `claude-sonnet-4-6`
  - `claude-code` → `claude-sonnet-4-6` (quality/price sweet spot; NEVER
    `auto`, which can silently be Opus; use `claude-haiku-4-5` for a
    cheaper/shallower smoke review).
  - `cursor` → `auto` (unlimited on Pro; pin `composer-2.5` etc. to
    force a specific model).
  - `codex` → `gpt-5.6-luna` (current-gen budget model; the parallel of
    the Sonnet-class choice above; `gpt-5-codex` is deprecated; pin
    `gpt-5.4-mini` for a shallower smoke review).
- **See:** `docs/PROVIDERS.md § "Choosing a cost-efficient model"` in the
  action repo.

---

## Prompt customization

### `prompt-file`

- **Default:** `''` (empty — use the bundled `prompts/default.md`)
- **What it is:** Path inside the consumer checkout to a markdown file
  that **fully replaces** the base prompt.
- **When to use:** you want to completely control the reviewer persona
  and rules.
- **When NOT to use:** you just want to add a few overrides — use
  `prompt-extension-file` for that instead (it's additive and doesn't
  drift from the shipped default).

### `prompt-extension-file`

- **Default:** `''` (empty — no extension)
- **What it is:** Path inside the consumer checkout to a markdown file
  whose content is **appended** to the base prompt.
- **When to use:** layer project-specific severity overrides,
  stack-specific conventions, or repo-specific guidance without
  copy-pasting the whole default. This is the intended customization
  point for most teams.
- **How to generate one:** run the `ai-diff-reviewer-generate-extension`
  sub-skill, or copy from `examples/prompts/` in the action repo.
- **Convention:** the local review skill auto-detects
  `.review/extension.md` — mirror that path in the workflow
  (`prompt-extension-file: .review/extension.md`) to keep local + CI
  reviews in lockstep.
- **Combining both inputs:** if `prompt-file` is also set,
  `prompt-file` becomes the new base and `prompt-extension-file` is
  appended to it.

---

## Trigger gating

### `author-association`

- **Default:** `OWNER,MEMBER,COLLABORATOR` (write-tier only).
- **What it is:** Comma-separated whitelist of GitHub
  `pull_request.author_association` values allowed to trigger the review.
- **Presets:**
  - Public open-source repo (default) — protects your API budget from
    external PR spam.
  - Add `CONTRIBUTOR` to include returning contributors whose PRs have
    already been merged.
  - Remove `COLLABORATOR` to gate on org membership only.
  - Empty string `''` — disable the gate, review every PR from anyone.
    Recommended for private repos; risky on public ones.
- **Case- and whitespace-insensitive.**
- **See:** `docs/SECURITY.md § "Author-association gate"` in the action
  repo for the threat model.

### `label-gate`

- **Default:** `''` (empty — no label required).
- **What it is:** If non-empty, the review only runs when the PR carries
  this label (e.g. `ready`).
- **Common pattern:** combine with `trigger-mode: label-once` to run
  reviews only when the author explicitly signals readiness.
- **Reminder:** if you use this, create the label on the repo first:
  ```bash
  gh label create ready --color 0e8a16 --description "Signals PR is ready for AI review"
  ```

### `trigger-mode`

- **Default:** `''` — resolves to `always` when there's no `label-gate`,
  or to `label-required` when there is.
- **Choices:**
  - `always` — run on every push/synchronize event (the default when
    no `label-gate` is set).
  - `label-required` — run only when `label-gate` is present on the PR
    (the default when `label-gate` is set).
  - `label-once` — run only once per label application; toggle the
    label off/on to re-run. Best cost discipline.
  - `label-added-only` — run only on the `labeled` webhook event.
    Requires the workflow to subscribe with `types: [labeled]`.
- **See:** `docs/TRIGGER_MODES.md` in the action repo for the decision
  matrix.

### `applied-label`

- **Default:** `''` (empty — no label applied).
- **What it is:** If non-empty, this label is applied to the PR after a
  successful, non-blocked review (e.g. `pr-reviewed`).
- **Empty means:** no label is applied, but the review still runs.

### `skip-review-label`

- **Default:** `''` (empty — feature disabled).
- **What it is:** Optional emergency-bypass label (e.g. `skip-ai-review`).
  When BOTH the workflow trigger fires AND this label is on the PR,
  the reviewer short-circuits: no LLM call, no findings, no state
  mutation, the GitHub check reports success (exit 0) so the merge can
  proceed. A `⏭️ skipped` tracking comment records the bypass and names
  the label so the audit trail is intact.
- **When to enable:** you want an emergency-bypass hatch for
  hotfixes, rollbacks, or trivially-safe changes where an LLM review
  would burn tokens for no incremental value.
- **What is NOT done on skip:** `applied-label` is NOT stamped
  (applying it would misrepresent an unreviewed PR as reviewed),
  IAR state is NOT mutated (the next non-skip run resumes exactly
  where the pipeline left off), and `collapse-previous` is NOT run
  (prior reviews stay visible so the human reviewer still has
  context).
- **Security:** anyone who can label a PR can bypass code review.
  Combine this input with a GitHub ruleset or CODEOWNERS-adjacent
  policy that restricts who can apply the label. The runtime does
  not police that — it's a repository-policy question the consumer
  owns.
- **Misconfig guard:** the reviewer aborts loudly at startup if
  this value collides with `label-gate`, `applied-label`, or
  `iteration-escape-label`. Each collision would silently convert
  every normal review trigger into a skip (or, for the
  `applied-label` case, freeze IAR state at round 1 forever).
  Failure surfaces as an exit-1 `CONFIGURATION ERROR:` log entry
  naming the colliding label; rename `skip-review-label` to a
  distinct value (recommended: `skip-ai-review`, `hotfix-no-review`)
  to resolve.
- **See:** `docs/TRIGGER_MODES.md § Emergency-bypass label` in the
  action repo for the full contract and worked security example.

---

## Presentation

### `collapse-previous`

- **Default:** `true`
- **What it is:** On every new run, mark previous bot reviews/comments
  as `OUTDATED` via GraphQL `minimizeComment` so only the latest
  review is visually active.
- **When to disable:** you want the full history visible on the PR
  timeline (rare — noisy).

### `tracking-comment`

- **Default:** `true`
- **What it is:** Post a tracking/spinner comment that transitions
  in-place from `Working…` to `View review →` when the review
  completes. The first line carries a
  `<!-- ai-pr-reviewer-marker -->` marker so downstream automation
  can locate it.
- **When to disable:** you find the extra comment noisy and would
  rather wait silently for the review itself.

---

## Strictness

### `strictness`

- **Default:** `lenient`
- **Choices:**
  - `lenient` — always succeed. Every review posts, no PR is ever
    blocked. Recommended for the first 1–2 weeks of calibration.
  - `block-on-critical` — fail if any inline comment is severity
    `critical` (security, data loss, breaking API). Recommended
    steady-state default.
  - `block-on-warning` — fail if any inline comment is `critical` OR
    `warning`. Aggressive.
  - `block-on-any` — fail if ANY inline comment was posted (including
    `info`). Zero-tolerance mode for security-critical or regulated
    stacks.
- **Severity source:** the model decides per comment via the
  `severity` tool argument, guided by the bundled default prompt
  (`prompts/default.md` in the action repo).

### `max-inline-comments`

- **Default:** `10`
- **What it is:** Hard cap on the number of inline comments the
  reviewer can queue per run.
- **How it works:** the model is instructed to stay well under this;
  the cap is a safety net for runaway reviews.
- **When to raise:** you consistently see the reviewer hitting the
  cap on legitimate reviews and want more headroom (~15–20 is
  reasonable; higher risks noise).

---

## PR metadata checks (v1.2.0+)

### `pr-description-mode`

- **Default:** `off`
- **Choices:**
  - `off` — no check on the PR body.
  - `warn` — flag in the review summary; the strictness gate is
    unchanged.
  - `block` — force the check to fail regardless of severity.
  - `autocomplete` — the reviewer AI writes a first-draft body via a
    PATCH to the PR. Guarded by a marker so it never overwrites
    maintainer edits.
- **See:** `docs/PR_METADATA_CHECKS.md` in the action repo.

### `pr-description-min-length`

- **Default:** `50` characters.
- **What it is:** Character threshold below which the PR body is
  treated as "missing/vague". Applies to `warn`, `block`, and
  `autocomplete` modes; ignored when `pr-description-mode: off`.
- **Common values:** `50` (default), `100` (stricter), `200` (much
  stricter — usually paired with a template).

### `complexity-labels-enabled`

- **Default:** `false`
- **What it is:** When `true`, the reviewer assesses PR complexity
  (`low` / `medium` / `high`) based on the full change (cognitive
  load, files touched, security surface, coverage delta) and applies
  a `<prefix><level>` label.
- **When to enable:** you use complexity labels for triage boards,
  code-owner routing, or PR-size KPIs.

### `complexity-label-prefix`

- **Default:** `complexity:` (produces `complexity:low` /
  `complexity:medium` / `complexity:high`)
- **What it is:** Prefix for the applied complexity label. Any prior
  label matching the prefix is removed before the current one is
  applied.
- **Common override:** `size/` (produces `size/low` etc.) if your
  team already uses `size/*` conventions.

---

## Agentic-loop budget

### `max-turns`

- **Default:** `30`
- **What it is:** Hard cap on the agentic loop iterations for
  chat-completions providers (`anthropic`). Each turn = one API
  call + a batch of tool calls.
- **Ignored by:** agent-runner providers (`claude-code`, `cursor`,
  `codex`) — they use `agent-max-turns` instead.
- **When to raise:** the reviewer runs out of turns on complex diffs
  before submitting. Rare — 30 is generous for a code review.

---

## Agent-runner (CLI) provider tuning

These inputs affect only the CLI providers (`claude-code`, `cursor`,
`codex`). Ignored by `anthropic`. Empty = provider default.

### `agent-max-turns`

- **Default:** `''` (empty).
- **What it is:** Reserved budget hint for CLI providers. Currently
  logs a warning instead of enforcing a cap, because the shipping
  CLIs do not yet expose a single stable cross-provider turn-count
  flag.
- **Status:** placeholder for future enforcement; setting it today is
  informational only.

### `agent-extra-args`

- **Default:** `''` (empty).
- **What it is:** Raw string appended to the CLI invocation. Parsed
  with `shlex.split` on the Python side (never `shell=True`).
- **When to use:** escape hatch for provider-specific flags not
  exposed by other inputs.
- **Example:** `--allowed-tools "read_file,grep,glob"` to further
  restrict CLI tools.

### `mcp-config-file`

- **Default:** `''` (empty).
- **What it is:** Path (relative to the consumer's checkout) to an MCP
  servers JSON config. If set, the file is copied to the CLI's
  expected location before invocation and cleaned up after:
  - `claude-code` → `~/.claude/mcp.json`
  - `cursor` → `~/.cursor/mcp.json`
  - `codex` → `~/.codex/mcp.json`
- **When to use:** the review needs an MCP tool the CLI would
  otherwise not have (e.g. a Sentry MCP for correlating errors, a
  Datadog MCP for metrics, a private-docs MCP for internal
  conventions).

### `claude-code-version`

- **Default:** `''` (empty — resolves to `latest`).
- **What it is:** Pin the Claude Code CLI version (npm semver).
- **When to pin:** you hit a regression on `latest` and want to
  freeze until a fix ships. Otherwise stay on latest.

### `cursor-version`

- **Default:** `''` (empty — resolves to latest stable).
- **What it is:** Pin the Cursor Agent CLI version. Forwarded to
  Cursor's installer via `VERSION` env var.

### `codex-version`

- **Default:** `''` (empty — resolves to `latest`).
- **What it is:** Pin the OpenAI Codex CLI version (npm semver).

---

## Iteration-Aware Review (IAR)

Four tunable inputs shape the IAR pipeline. IAR runs on every review
with `convergence-policy: first-pass-exhaustive` as the default, so
consumers who don't configure anything get IAR automatically with the
recommended profile. Critical severity findings ALWAYS surface
unconditionally — a hardcoded safety rail that no policy can bypass.
Full spec: [docs/ITERATION_AWARENESS.md](../../../docs/ITERATION_AWARENESS.md).

### `convergence-policy`

- **Default:** `first-pass-exhaustive`.
- **What it is:** Which IAR policy to apply. One of:
  - `first-pass-exhaustive` (default) — exhaustive prompt + higher
    findings cap on round 1 of each generation; dedup on rounds 2+.
    Solves the "prefer 20 findings at once vs 10 loops" workflow.
  - `iterative` — dedup only, no cap boost. Cost-neutral vs a no-dedup
    baseline. Set explicitly when your workflow pushes frequently and
    the round-1-of-new-gen boost would fire too often.
  - `round-capped` — dedup pre-cap. Post-cap only critical findings
    surface. Requires `max-review-rounds > 0`.
  - `critical-gate` — strict cross-generation dedup: prior-resolved
    fingerprints stay silenced unless critical.

### `max-review-rounds`

- **Default:** `0` (unlimited).
- **What it is:** Hard cap for the `round-capped` policy. After N rounds
  only critical findings surface; warnings and infos are silenced with a
  "cap reached" annotation. Ignored by other policies.

### `exhaustive-first-pass-cap-multiplier`

- **Default:** `3`.
- **What it is:** Multiplier applied to `max-inline-comments` on round 1
  of each generation when policy is `first-pass-exhaustive`. Default `3`
  means round 1 can post up to 3× the normal cap. Set to `1` to keep the
  exhaustive prompt splicing without amplification. Ignored by other
  policies.

### `iteration-escape-label`

- **Default:** `full-review-please`.
- **What it is:** Label a human applies to force a full review. Dedup is
  skipped for that run only; persisted state is NOT mutated. When the
  label is removed, subsequent reviews resume normal IAR behavior. Useful
  before final merge to see everything again, or when the developer
  suspects IAR silenced something they need to see.
- **Companion gesture (no input needed):** on a PR that already has an
  IAR state block, removing the reviewed label (`applied-label`, e.g.
  `ai-reviewed`) before the next review triggers a full **state reset**
  — the next run is classified `USER_FORCED_RESET`, prior state is
  discarded, generation counter restarts at 1, and round-1 exhaustive
  fires on a clean slate. Distinct from this escape label: applying
  `full-review-please` is "see everything this once, state preserved";
  removing `applied-label` is "start clean, state discarded". Full spec
  in [docs/ITERATION_AWARENESS.md § 8.5](https://github.com/DailybotHQ/ai-diff-reviewer/blob/v1/docs/ITERATION_AWARENESS.md).

---

## Outputs

The action writes these to the workflow's `steps.<id>.outputs.*` for
downstream steps to consume.

| Output | Description |
|---|---|
| `review-url` | URL of the posted PR review (empty when the run was skipped). |
| `severity` | Highest severity flagged in this review: `none`, `info`, `warning`, or `critical`. |
| `inline-attached` | Number of inline comments actually attached to the review. |
| `inline-dropped` | Number of inline comments dropped because GitHub rejected the review with HTTP 422 (the action retries summary-only on 422). |
| `blocked` | Whether the strictness gate decided to fail the check (`true`/`false`). When `true`, the action exits with code 2 so the GitHub check turns red. |
| `skipped` | Whether the run was skipped without invoking the LLM (`true`/`false`) — label/author/`trigger-mode` gate **or** configured `skip-review-label` emergency bypass. |
| `iteration-round` | IAR round number within the current generation. Populated on every successful IAR pipeline run. Empty string if the pipeline crashed (caught by the try/except safety net). |
| `iteration-generation` | IAR generation counter; increments on new commits or rebase. Empty if the IAR pipeline crashed. |
| `iteration-policy-applied` | Which IAR policy actually fired this run. Usually matches `convergence-policy`; the 30% safety net overrides it to `safety-net-forced-first-pass-exhaustive` and the escape label overrides to `escape-label-forced-full-review`. Empty if the IAR pipeline crashed. |
| `iteration-tokens-used` | Cost-telemetry counter. Always emits `"0"` today — the runtime does not yet capture per-provider usage metadata into `RunTelemetry.tokens_used`; safe placeholder that consumers can surface without gating on. Empty ONLY if the IAR pipeline crashed. See `docs/ITERATION_AWARENESS.md § 13.2`. |
| `iteration-cost-vs-baseline-estimate` | Coarse cost-delta heuristic (cap expansion + addendum flag). Always `"0%"` or `"+N%"` today — silenced-finding savings are not yet modelled. Empty if the IAR pipeline crashed. |

---

## Related docs (in the action repo)

- `README.md` — quick-start, provider overview, feature matrix.
- `docs/PROMPTS.md` — how prompts and extensions interact; local review
  parity.
- `docs/STRICTNESS.md` — when to graduate through the strictness levels
  (includes § Strictness × IAR).
- `docs/TRIGGER_MODES.md` — full trigger-mode decision matrix, recipes,
  and § Emergency-bypass label (`skip-review-label`).
- `docs/ITERATION_AWARENESS.md` — IAR policies, escape label,
  USER_FORCED_RESET, outputs, failure fallback.
- `docs/PERFORMANCE.md` — turn budgets plus the IAR cost/latency model.
- `docs/PR_METADATA_CHECKS.md` — description-mode and complexity-label
  details, including the autocomplete marker.
- `docs/PROVIDERS.md` — provider-by-provider setup, model choices, and
  cost tradeoffs.
- `docs/SECURITY.md` — author-association gate, IAR trust boundary,
  `skip-review-label` threat model, responsible-disclosure flow.

---

## When the reference is out of sync

This file mirrors `action.yml` at release-cut time and is regenerated
by the auto-release workflow's skill-sync step. If you spot a drift
(a new input in `action.yml` that's missing here, or a description
mismatch), file an issue at
https://github.com/DailybotHQ/ai-diff-reviewer/issues — this file
should always be a truthful summary of the `@v2` contract.
