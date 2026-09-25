---
name: ai-diff-reviewer-address-review
description: Close the review loop in one invocation — find the open PR(s) for the current branch, check whether the AI Diff Reviewer CI run already covered the current head, walk its findings (apply / defer / skip; unlike apply-review, apply here commits and pushes in small Conventional Commits batches), then re-arm the reviewer adaptively to how the repo is configured — a label-gated review workflow gets its label toggled (present → off/on to re-trigger a label-once run; absent → added), a push-triggered workflow is confirmed to have restarted on the new head, and a repo with no reviewer workflow is told so and offered the local review. Reads the v3 review-output artifact first, falls back to the marker comment and live threads, skips minimized and stale reviews, multi-leg aware. Use when the developer says "address the review and re-run", "resolve the reviewer comments and toggle ready", "loop the review", or repeats the resolve-then-ready instruction.
version: "3.1.1"
documentation_url: https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/skills/ai-diff-reviewer/address-review/SKILL.md
user-invocable: true
metadata: {"openclaw":{"emoji":"🔁","homepage":"https://github.com/DailybotHQ/ai-diff-reviewer","requires":{"anyBins":["git","gh"]}}}
allowed-tools: Bash, Read, Grep, Glob, Edit
---

# AI Diff Reviewer — Address Review (sub-skill)

The one-invocation loop for the most repeated instruction after a CI review:
*"revisa los comentarios del reviewer en el PR, resuélvelos y luego haz toggle
del ready label."* This sub-skill is that sentence, executable — and
**repo-adaptive**: it discovers how THIS repository triggers its reviewer
(label gate or push trigger) and re-arms it the right way instead of guessing.

Relationship to the family:

- [`apply-review`](../apply-review/SKILL.md) **reads** a CI review and walks
  findings with a no-commit / no-push boundary (each apply is a working-tree
  edit needing a per-finding yes).
- This sub-skill **closes the loop**: same finding-loading rules (v3
  review-output artifact first, marker comment + live threads as fallback,
  minimized and stale reviews skipped), but the apply step ends in **commits
  and a push** (small Conventional Commits batches), and the push/label step
  **re-arms the CI reviewer** so the next round starts without the developer
  asking again.
- On a repo with **no reviewer workflow**, it says so and offers the parent
  skill's local review flow instead of pretending a round will start.

## When it fires

- "Address the review and re-run"
- "Resolve the reviewer comments and toggle ready"
- "Fix the review findings and re-trigger CI"
- "Loop the review" / "run the review loop"
- The repeated instruction itself: *"revisa los comentarios del reviewer,
  resuélvelos y haz toggle del ready label"*
- "What's left from the review? Handle it and re-arm CI"

**Fall through** to a sibling when the developer only wants to *read* the
review → [`apply-review`](../apply-review/SKILL.md) (read-only); only wants a
local pre-flight review → parent skill; wants the PR body refreshed →
[`open-pr`](../open-pr/SKILL.md).

## Step 0 — Trust boundary

- **Reads (no consent):** `gh pr view` / `gh pr list` / `gh pr checks` /
  `gh api` (reviews, comments, artifacts, workflow runs), `git status` /
  `rev-parse` / `branch --show-current`, repo workflow files under
  `.github/workflows/`, and local source files a finding references.
- **Writes (consented once, up front):** source edits for the findings the
  developer approved, `git commit` (Conventional Commits, small batches),
  `git push` to the PR branch, and label operations
  (`gh pr edit --add-label / --remove-label`) on the PR. Nothing else — no
  force-push, no merges, no check bypasses, no edits to the workflow files.
- The invocation of this skill by its trigger phrase **is the consent for the
  loop** — but the plan is always shown first (Step 3), and anything ambiguous
  (a finding that can't be mapped to code, conflicting findings between legs)
  is asked, not guessed. A bare "apply the fixes" without the loop intent
  belongs to [`apply-review`](../apply-review/SKILL.md).

## Step 1 — Find the PR(s)

1. Current branch: `git branch --show-current`; head: `git rev-parse HEAD`.
2. `gh pr list --head <branch> --state open --json number,title,headRefName,url`.
   - **Exactly one** → proceed.
   - **Several** (e.g. stacked PRs or the branch open against two bases) →
     list them and ask which (or all). Handle each independently in Steps 2-5.
   - **None** → check whether the conversation mentioned explicit PR numbers;
     otherwise report "no open PR for this branch" and offer
     [`open-pr`](../open-pr/SKILL.md). Stop.
3. Record `head_sha` per PR. Everything downstream is SHA-pinned to it.

## Step 2 — Has the reviewer run on this head?

Freshness rule (same as `apply-review` + `docs/PR_REVIEW_WORKFLOW.md`): the
authoritative review is the one whose marker carries the **current head SHA**.

1. `gh pr view <n> --json comments` (or the GraphQL query in
   `docs/PR_REVIEW_WORKFLOW.md`) → find the latest comment containing
   `<!-- ai-pr-reviewer-marker -->` (aggregate reviews carry
   `<!-- ai-pr-reviewer-aggregate -->` beside it); extract its SHA.
2. Prefer the structured document when it exists: download the
   `ai-diff-reviewer-<head12>-*` artifact for the head's workflow run
   (`gh run download`) or read `.aiprr/review-output.json` if running inside
   the workspace — the artifact's findings come with verification, refuted
   list and per-leg agreement.
3. Decide:
   - **Marker SHA == head SHA** (or artifact for this head exists) → the
     review is fresh; go to Step 3.
   - **Marker SHA != head SHA, or a review workflow run for the head is
     `in_progress`/`queued`** → say so and wait briefly (poll
     `gh pr checks` / `gh run list` at ~30 s intervals, a few minutes at
     most). If it's still running, hand back: *"the reviewer is still running
     on <sha> — invoke me again when it posts"* with the exact watch command.
     Never address a stale review.
   - **No marker at all and no reviewer workflow** (see Step 5's detection) →
     report that this repo has no AI Diff Reviewer in CI; offer the parent
     skill's local review. Stop.

## Step 3 — Present the findings and the plan (the one consent point)

Load the findings the `apply-review` way: skip `isMinimized` comments, skip
threads already resolved, attribute findings to their leg when the repo runs a
matrix, and surface cross-leg consensus. Present:

- **Verdict** (approved / changes requested / review still failing) and the
  findings table (severity, leg/agreement, file:line, one-line summary).
- **The plan** for each finding: `apply` (with the intended edit in one
  sentence), `defer` (recorded in `.review/deferred.md`, same convention as
  apply-review), or `ask` (ambiguous — needs the developer).
- **The re-arm plan** from Step 5's detection, stated concretely: *"...then
  I'll toggle `ready` off/on to re-trigger the review"* or *"...the push alone
  re-triggers the review; nothing else to do."*

Then ask **once**: "Apply the plan? (all / only 1,3 / edit / abort)". On
abort, nothing has been written.

## Step 4 — Apply, commit, push

1. For each `apply` finding: make the edit (the finding's suggestion is the
   default; deviate only with the reason stated). Use
   `git show <marker-sha>:<path>` when a finding's context depends on the
   reviewed version of a file.
2. Commit in **small batches** (one concern per commit, Conventional Commits
   with the repo's required body format when it has one), never mixing
   deferred-notes changes with source fixes. Do not resolve the review
   threads that the next round will supersede — the reviewer's own collapse
   logic handles history.
3. `git push` to the PR branch. Deferred findings: append to
   `.review/deferred.md` (and commit that separately, `docs:` or `chore:`).

## Step 5 — Re-arm the reviewer (repo-adaptive)

Detect the repo's trigger configuration once, then act:

1. **Detection** — inspect the repo's review workflows
   (`.github/workflows/*.yml`): find the job(s) that
   `uses: DailybotHQ/ai-diff-reviewer` (or `uses: ./` on the Action's own
   repo). From their `on:` block and `with:` inputs read:
   - `trigger-mode` / label gating: a `labeled` trigger or
     `trigger-mode: label-once` / `label-gate: <label>` → **label-gated**,
     with the label name from the input (default `ready`).
   - otherwise (`types: [opened, synchronize, reopened]`, or no explicit
     trigger mode) → **push-triggered**.
   - no reviewing workflow at all → see Step 2's stop case.
2. **Label-gated:**
   - Label **present** on the PR → toggle it to re-trigger a label-once run:
     `gh pr edit <n> --remove-label <label>`, wait a few seconds,
     `gh pr edit <n> --add-label <label>`.
   - Label **absent** → add it (a fresh gate application triggers the run).
3. **Push-triggered:** the Step 4 push already re-triggered the review —
   verify with `gh run list` that a new run started for the new head, and say
   so.
4. **After re-arming**, report the loop's outcome and the watch command
   (`gh pr checks <n> --watch`), and offer: *"invoke me again when the new
   review lands and I'll run the next round."* Do not wait for the next
   round unless the developer asks.

## Failure modes

| Situation | Behaviour |
|---|---|
| Review still running on the current head | Report + hand back with the watch command; never address a stale review |
| Several open PRs for the branch | Ask which; handle each independently |
| No reviewer workflow in the repo | Say so; offer the local review flow; do not install anything |
| A finding can't be mapped to code | Mark it `ask`, never guess an edit |
| Legs disagree on a finding | Surface the consensus split; let the developer decide |
| Label toggled but no run starts | The workflow may filter the label event (branches filter, actor filters) — report the workflow's `on:` block and stop |
| Working tree dirty before Step 4 | Ask first: stash, commit separately, or proceed around the dirt; never sweep unrelated changes into a fix commit |

## Sample dialogues

> **Dev:** "address the review and re-run"
> **Agent:** finds PR #64 → marker at head ✓ → 2 findings (1 warning apply,
> 1 critical apply from the grok leg, agreed 2/2) → plan: fix both, commit as
> `fix(review): …`, push, then toggle `ready` off/on (workflow is
> label-gated, label-once) → "Apply the plan?"
> **Dev:** "all"
> **Agent:** applies, commits, pushes, toggles the label, confirms the new
> run started, hands back the watch command.
