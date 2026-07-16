---
name: ai-diff-reviewer-setup
description: Interactive installer for the AI Diff Reviewer GitHub Action — walks the developer through 6 key decisions (provider, strictness, trigger mode, external-contributor policy, PR description mode, complexity labels), detects the repo's stack for sensible defaults, and writes a working `.github/workflows/pr-review.yml` tailored to those choices. Also acts as the reference manual for every `action.yml` input any coding agent might be asked about ("what is `strictness`?", "how do I use label-gate?"). Use when the developer says "set up AI Diff Reviewer for this repo", "configure the reviewer action", "install the AI Diff Reviewer action", "help me create the pr-review workflow", or when the local `ai-diff-reviewer` skill is present on a repo that has no `.github/workflows/pr-review.yml` yet.
version: "2.0.0"
documentation_url: https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/skills/ai-diff-reviewer/setup/SKILL.md
user-invocable: true
metadata: {"openclaw":{"emoji":"⚙️","homepage":"https://github.com/DailybotHQ/ai-diff-reviewer","requires":{"anyBins":["git"]}}}
allowed-tools: Bash, Read, Grep, Glob
---

# AI Diff Reviewer — Setup Wizard (sub-skill)

Companion to the [`ai-diff-reviewer`](../SKILL.md) skill. Where the parent
**runs** the review and [`generate-extension`](../generate-extension/SKILL.md)
**tailors the prompt**, this sub-skill **bootstraps the GitHub Action
itself** — walks the developer through the ~6 key decisions and writes
a working `.github/workflows/pr-review.yml` tailored to those choices.

Also doubles as the **reference manual** for every `action.yml` input:
if a developer asks any coding agent *"what does `strictness` do?"* or
*"how do I run only when a label is added?"*, the agent can read
[`reference.md`](reference.md) in this directory and answer without
opening the source.

---

## When it fires

Explicit triggers (recommended):

- "Set up AI Diff Reviewer for this repo"
- "Configure the reviewer action"
- "Install the AI Diff Reviewer GitHub Action"
- "Help me create the pr-review workflow"
- "How do I add AI Diff Reviewer to this project?"

The parent [`ai-diff-reviewer`](../SKILL.md) skill may also route here
automatically when a review-flow request activates on a repo that
clearly has no `.github/workflows/pr-review.yml` (opt-in — future
enhancement; not the default today).

---

## Step 0 — Trust boundary

This skill **writes** exactly two categories of files, both with
explicit developer consent:

- **`.github/workflows/pr-review.yml`** — the tailored workflow after
  all six questions are answered. If a file already exists at that
  path, the skill ASKS before overwriting (offers to write to
  `pr-review-new.yml` alongside for review).
- **`.review/extension.md`** — only if the developer says **yes** to
  the optional Step 5 handoff, which invokes the
  [`generate-extension`](../generate-extension/SKILL.md) sub-skill.

It **does not**:

- Commit anything, push anything, or open a PR — the developer stages
  and commits themselves.
- Touch GitHub Secrets — they're set once by the developer in the
  repo's Settings UI (link surfaced in Step 4).
- Modify existing unrelated workflows in `.github/workflows/`.
- Call the LLM provider directly or send data off the machine.

---

## Step 1 — Discovery (light — target ≤ 6 tool calls)

Gather just enough to pick sensible defaults; don't do a full
`generate-extension`-style Discovery.

### 1a. Repo identity

```bash
# Slug (owner/repo)
git remote get-url origin | sed -E 's|.*[:/](.+/.+)\.git$|\1|'

# Public or private? (gh required; skip cleanly if absent)
gh repo view --json isPrivate,visibility 2>/dev/null
```

### 1b. Existing workflows

```bash
ls .github/workflows/*.yml 2>/dev/null
test -f .github/workflows/pr-review.yml && echo "EXISTS"
```

If `pr-review.yml` (or a similarly-named workflow) already exists,
tell the developer and offer three paths:

1. **Overwrite** — replace the existing file (require them to confirm
   `yes overwrite`, not just `yes`).
2. **Side-by-side** — write to `.github/workflows/pr-review-new.yml`
   so they can diff and merge manually.
3. **Cancel** — abort the setup entirely.

### 1c. Stack detection (defaults hint)

```bash
# Presence of any of these tells you the primary language / ecosystem.
ls package.json pnpm-lock.yaml yarn.lock 2>/dev/null   # Node
ls pyproject.toml requirements*.txt Pipfile 2>/dev/null # Python
ls go.mod 2>/dev/null                                   # Go
ls Cargo.toml 2>/dev/null                               # Rust
ls Gemfile 2>/dev/null                                  # Ruby
ls pom.xml build.gradle 2>/dev/null                     # Java/Kotlin
```

The stack shapes only one suggestion downstream: whether the CLI
providers make sense (`claude-code` / `cursor` / `codex` all need
Node 20 to install, which is fine on `ubuntu-latest` regardless of
your project's language, but the workflow's `timeout-minutes` may
want to be higher for larger diffs).

### 1d. Default branch

```bash
gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null || echo "main"
```

Used to fill `on.pull_request.branches: [<default>]` in the composed
workflow.

---

## Step 2 — The six questions

Ask them **one at a time**, showing the default marked as
**(recommended)** in the response so the developer can just say "go
with defaults" and get the safest workflow in ~30 seconds. Use the
Discovery data to pre-fill anything you can (e.g. `default_branch`,
`visibility`).

### Q1 — Provider

> **Which LLM provider should run the review?**
>
> - **`anthropic`** (recommended for first setup) — Zero install
>   overhead, uses `ANTHROPIC_API_KEY`. The action calls the
>   chat-completions API directly. Best default unless you already
>   have a specific reason to want a CLI provider.
> - **`claude-code`** — Runs the Claude Code CLI headlessly. Same
>   Anthropic models, but accepts a subscription OAuth token
>   (`sk-ant-oat…`) via `api-key`, so you can bill against a Claude
>   Pro / Max plan instead of API usage.
> - **`cursor`** — Runs the Cursor Agent CLI headlessly. Default
>   model `auto` is unlimited on Cursor Pro plans. Best if the team
>   already lives inside Cursor.
> - **`codex`** — Runs the OpenAI Codex CLI headlessly (GPT models).
>   Best if the team already has OpenAI billing.

Record: `PROVIDER`. Also record the corresponding secret name for
Step 4: `ANTHROPIC_API_KEY` / `CLAUDE_CODE_TOKEN` (or
`ANTHROPIC_API_KEY`) / `CURSOR_API_KEY` / `OPENAI_API_KEY`.

### Q2 — Strictness

> **When should the GitHub check fail?**
>
> - **`lenient`** (recommended for weeks 1–2) — The check never
>   fails; every review posts, no PR is ever blocked. Use this to
>   calibrate the prompt and the extension against your codebase
>   without breaking anyone's merge flow.
> - **`block-on-critical`** (recommended for steady-state) —
>   Fails only if the reviewer marks any comment as `critical`
>   (security, data loss, breaking API). Warnings and info-level
>   comments still post but don't gate merges.
> - **`block-on-warning`** — Fails on `warning` OR `critical`.
>   Aggressive; only recommended when the extension has been tuned
>   to keep false positives near zero.
> - **`block-on-any`** — Fails on ANY inline comment, including
>   `info`. Zero-tolerance mode for security-critical or regulated
>   stacks.

Record: `STRICTNESS`.

### Q3 — Trigger mode

> **When should the reviewer run?**
>
> - **on every push to the PR** (recommended for most teams) — Uses
>   `types: [opened, synchronize]`. Reviews the diff on the first
>   open and again every time new commits are pushed. Predictable
>   feedback loop for the author.
> - **only when a `ready` label is applied** — Uses
>   `trigger-mode: label-once` + `label-gate: ready`. Keeps WIP PRs
>   quiet; costs run only when the author explicitly signals
>   readiness. Toggle the label off/on to re-run. Best for cost
>   discipline in large repos.
> - **only on `labeled` events** — Uses `trigger-mode:
>   label-added-only` and subscribes to `types: [labeled]`. Even
>   more conservative; the workflow doesn't run on `synchronize`
>   at all, so new commits after the label was applied don't
>   trigger new reviews (only re-labeling does).

Record: `TRIGGER`, plus `LABEL_GATE` (empty or `ready`) and the
workflow event types.

### Q4 — External contributors

> **Who should be allowed to trigger the review?**
> (Applies mostly to public open-source repos — private repos can
> skip the gate.)
>
> - **`OWNER,MEMBER,COLLABORATOR`** (recommended for public repos) —
>   Only writes-tier authors trigger the review. Blocks external
>   contributors from opening PRs to burn your API budget.
> - **`OWNER,MEMBER,COLLABORATOR,CONTRIBUTOR`** — Also allows
>   returning contributors (people whose PRs you've merged before).
>   Good middle ground once you have a stable contributor pool.
> - **empty string `''`** — Review every PR from anyone.
>   Recommended for private repos; risky on public ones.

Skip this question if `visibility == "PRIVATE"` (default to empty).

Record: `AUTHOR_ASSOC`.

### Q5 — PR description mode

> **Should the reviewer also check that PR descriptions are meaningful?**
>
> - **`off`** (recommended if you don't have PR-body standards yet) —
>   Ignore the description entirely.
> - **`warn`** — Flag "missing/vague description" in the review
>   summary (doesn't affect the strictness gate).
> - **`block`** — Force the check to fail if the description is
>   missing/vague, regardless of `strictness`. Cheap way to enforce
>   PR hygiene.
> - **`autocomplete`** — The reviewer AI writes a first-draft body
>   for you. Guarded by a marker so it never overwrites your edits.
>   Best UX for solo maintainers.

Record: `PR_DESC_MODE`. If the developer picks anything other than
`off`, ask a follow-up: "Minimum character count?" (default `50`).

### Q6 — Complexity labels

> **Should the reviewer apply complexity labels (`complexity:low` /
> `complexity:medium` / `complexity:high`) to PRs?**
>
> - **no** (recommended for first setup) — Skip this feature until
>   you have a use case for it.
> - **yes** — The reviewer assesses cognitive load / files touched /
>   security surface / coverage delta and applies a label. Useful for
>   triage boards, code-owner routing, or PR-size KPIs. Adds a small
>   amount of latency + one more label the team has to reason about.

Record: `COMPLEXITY_LABELS`.

---

## Step 3 — Compose and write the workflow

Assemble the YAML from the recorded answers. Template below (variables
in `<ANGLE_BRACKETS>` come from Step 2's answers; the header comment is
generated so the developer knows which options this file reflects).

```yaml
# AI Diff Reviewer — generated by the setup skill.
# Source: https://github.com/DailybotHQ/ai-diff-reviewer
#
# What's configured here:
#   - Provider: <PROVIDER>
#   - Strictness: <STRICTNESS>
#   - Trigger: <TRIGGER_HUMAN>  (<TRIGGER>)
#   - External contributors: <AUTHOR_ASSOC or "unrestricted">
#   - PR description mode: <PR_DESC_MODE>
#   - Complexity labels: <yes|no>
#
# Regenerate: run the ai-diff-reviewer-setup skill again.

name: PR review
on:
  pull_request:
    branches: [<DEFAULT_BRANCH>]
    types: [<EVENT_TYPES>]     # e.g. [opened, synchronize]

concurrency:
  group: pr-review-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # required — the action runs `git diff origin/<base>...HEAD`

      - uses: DailybotHQ/ai-diff-reviewer@v2
        with:
          provider: <PROVIDER>
          api-key: ${{ secrets.<SECRET_NAME> }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          strictness: <STRICTNESS>

          # Only include the lines below when they differ from action defaults.
          <optional: trigger-mode: <TRIGGER>>
          <optional: label-gate: <LABEL_GATE>>
          <optional: author-association: '<AUTHOR_ASSOC>'>
          <optional: pr-description-mode: <PR_DESC_MODE>>
          <optional: pr-description-min-length: <MIN_LEN>>
          <optional: complexity-labels-enabled: 'true'>
```

**Rules for the composition:**

1. **Omit every input that matches its action default.** The result
   should read like a hand-written minimal workflow, not a giant
   config dump. Explicit inputs only for the choices that differ.
2. **Never emit a placeholder secret value.** Use
   `${{ secrets.<SECRET_NAME> }}` — the developer wires it in Step 4.
3. **Header comment reflects reality.** If the trigger is
   label-added-only, the comment must say so and the event types
   must match — don't ship a mismatch.
4. **`applied-label` and `collapse-previous`** are not asked (they
   default to sensible values); the composed workflow inherits both
   defaults silently.
5. **`prompt-extension-file`** is not asked in the wizard — it's set
   later, either by the developer or by Step 5's handoff to
   `generate-extension`.

Write the file:

```bash
mkdir -p .github/workflows
# Write the composed YAML to .github/workflows/pr-review.yml (or
# pr-review-new.yml if the developer picked "side-by-side" in Step 1b)
# via the harness's file-write tool.
```

---

## Step 4 — Post-setup instructions

After the file is written, tell the developer the exact next steps.
**Include the repo-specific URL** — makes the friction go away.

```markdown
Workflow written to `.github/workflows/pr-review.yml`. Next steps:

1. **Add the API secret.**
   Go to: https://github.com/<OWNER>/<REPO>/settings/secrets/actions/new
   Name: `<SECRET_NAME>`
   Value: your API key from <PROVIDER_CONSOLE_URL>

2. **Commit + test.**
   ```bash
   git checkout -b chore/setup-ai-diff-reviewer
   git add .github/workflows/pr-review.yml
   git commit -m "chore: add AI Diff Reviewer GitHub Action"
   git push -u origin chore/setup-ai-diff-reviewer
   ```
   Open a draft PR. The reviewer will run on the first push, post its
   findings, and (given your `<STRICTNESS>` choice) either gate the
   check or just comment.

3. **Only if you picked `label-gate: ready`** (Q3, second option):
   also create the label on the repo before merging the workflow.
   ```bash
   gh label create ready --color 0e8a16 --description "Signals PR is ready for AI review"
   ```

4. **Defaults you already have (no extra config needed).**
   Iteration-Aware Review runs on every CI review with
   `convergence-policy: first-pass-exhaustive` — exhaustive first
   pass, then dedup on later rounds so the same warnings don't
   trickle forever. To force a full un-deduped pass once, label
   the PR `full-review-please` (the shipped
   `iteration-escape-label`). Optional emergency bypass for
   hotfixes: add `skip-review-label: skip-ai-review` to the
   workflow and protect that label with a ruleset — see
   `examples/skip-review-label.yml` and
   `docs/ITERATION_AWARENESS.md` / `docs/TRIGGER_MODES.md` in the
   action repo.
```

Provider-console URLs to substitute in the instructions:

| Provider | Console URL for API key |
|---|---|
| `anthropic` | https://console.anthropic.com/settings/keys |
| `claude-code` | https://console.anthropic.com/settings/keys OR `claude setup-token` for subscription-mode |
| `cursor` | https://cursor.com/dashboard → Settings → API Keys |
| `codex` | https://platform.openai.com/api-keys |

---

## Step 5 — Optional handoff: bootstrap the extension file

After the workflow is written, ask ONE more question:

> **Want to also tailor the review to this repo?**
>
> The workflow uses the shipped default prompt right now — great for
> general-purpose review, but it doesn't know YOUR conventions
> (money-handling in `<detected-stack>`, banned patterns, etc.).
>
> I can bootstrap a `.review/extension.md` for this repo now
> (~30 seconds of Discovery + a ~100-line file). The workflow will
> auto-detect it if you also add
> `prompt-extension-file: .review/extension.md` to the `with:` block,
> and the local review skill picks it up too.
>
> - **yes** — invoke `generate-extension` now.
> - **no** — skip; the shipped default is fine. Run
>   `generate-extension` any time later.

Handle:

- **yes** → invoke [`generate-extension`](../generate-extension/SKILL.md)
  in extension mode. After it writes `.review/extension.md`, update the
  freshly-composed workflow file to add
  `prompt-extension-file: .review/extension.md` (a two-line
  in-place edit). Announce both files at the end.
- **no** → stop after Step 4. Tell the developer they can bootstrap
  the extension later ("say 'generate a `.review/extension.md`' any
  time — one command, zero re-config").

---

## Reference — all action inputs

The full input table with description, default, and per-scenario
recommendations lives in [`reference.md`](reference.md) in this
directory. Read it directly when the developer asks a specific
question about any input the wizard didn't cover
(`mcp-config-file`, `max-turns`, `agent-extra-args`, etc.).

Any coding agent with this skill installed can answer
*"what does `<input>` do?"* by consulting `reference.md` alone — no
need to open `action.yml`.

---

## Notes

- **The wizard is the happy path; `reference.md` is the escape hatch.**
  If the developer wants to hand-craft a workflow with knobs the
  wizard doesn't ask about (`mcp-config-file`, `max-turns`, model
  pinning, etc.), point them at `reference.md` and let them compose
  themselves.
- **Re-running the wizard is safe.** If a `.github/workflows/pr-review.yml`
  already exists, the skill offers overwrite / side-by-side / cancel.
  Overwriting requires the explicit phrase `yes overwrite`, not just
  `yes`.
- **The composed workflow tracks the moving major tag** (`@v2`) by
  default so consumers pick up patches and minor features
  automatically. To pin, edit the `uses:` line to a specific
  `@vX.Y.Z` — the auto-release workflow keeps the major tag in sync
  on every release.
- **`prompt-extension-file` is deliberately not asked** in the
  wizard — the developer either doesn't have one yet (Step 5 offers
  to generate it) or already knows the path (in which case they can
  hand-edit the workflow after).
- **Bugs, feature requests, or "the wizard didn't ask about X":**
  https://github.com/DailybotHQ/ai-diff-reviewer/issues.
