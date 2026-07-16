---
name: ai-diff-reviewer-apply-review
description: Read the most recent AI Diff Reviewer review from the current branch's open PR, present the findings in the same format as the parent skill's local review flow (verdict → findings table → per-finding body → recommendation), and — with explicit consent — walk the developer through each finding to apply, defer, or skip. Multi-provider aware — when the repo runs a matrix of legs (anthropic, cursor, codex, claude-code), attributes each finding to its self-reviewed provider label and surfaces cross-leg consensus. Anchors on the latest ai-pr-reviewer-marker tracking comment and filters minimized (collapsed / outdated) comments per the repo's documented PR-review workflow. Read-only by default; edits to source files require an explicit yes per finding, never commits, never pushes. Use when the developer says "what did the CI review say?", "read the review on this PR", "apply the AI review's fixes", "walk me through the findings", "which findings blocked the merge?", "show me only the critical findings", or "the bot posted a review — help me address it".
version: "2.0.0"
documentation_url: https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/skills/ai-diff-reviewer/apply-review/SKILL.md
user-invocable: true
metadata: {"openclaw":{"emoji":"🔎","homepage":"https://github.com/DailybotHQ/ai-diff-reviewer","requires":{"anyBins":["git","gh"]}}}
allowed-tools: Bash, Read, Grep, Glob, Edit
---

# AI Diff Reviewer — Apply Review (sub-skill)

Companion to the [`ai-diff-reviewer`](../SKILL.md) skill. Where the
parent **runs** the review locally and [`open-pr`](../open-pr/SKILL.md)
**writes** the pull request, this sub-skill closes the loop: it
**reads** the review the CI Action posted back on the PR, presents
the findings in the same format the local review uses, and — with
explicit consent — walks the developer through each finding to
apply, defer, or skip.

The design philosophy mirrors the family's:

- **Parity of shape.** The output uses the same
  `verdict → findings table → per-finding body → notes → recommendation`
  structure the parent skill emits. A developer who has seen one of
  the two knows how to read the other. When the CI leg found *"SQL
  injection in `src/auth.ts:55`"*, the summary looks identical whether
  it was your local agent or CI that surfaced it.
- **Read-only by default.** Fetching + presenting the review never
  writes anything. Only when the developer explicitly asks to *"walk
  through"* or *"apply the fixes"* does the sub-skill open source
  files, and each individual apply still requires a yes.
- **Multi-provider aware.** This repo (and any consumer that opts
  into the 4-leg matrix) posts up to four independent reviews per PR,
  distinguished by `self-reviewed:<provider>` labels. The sub-skill
  reads all live legs, attributes each finding to its leg, and
  surfaces cross-leg consensus (*"agreed by 3/3 legs → strong signal;
  called by 1/3 → could be leg-specific"*).
- **Never commits, never pushes.** Applied fixes stay unstaged in the
  working tree. Commit + push is the developer's judgment call,
  matching [`open-pr`](../open-pr/SKILL.md)'s trust boundary.

The single source of truth for the workflow this sub-skill implements
is [`docs/PR_REVIEW_WORKFLOW.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/docs/PR_REVIEW_WORKFLOW.md).
This sub-skill is that doc, executable.

---

## When it fires

**Read + present the review (default flow) — triggers:**

- "What did the CI review say?"
- "Read the review on this PR"
- "Show me the review findings"
- "Did the bot approve or request changes?"
- "Which findings blocked the merge?"
- "The AI review just landed — summarize it"

**Walkthrough mode (apply/defer/skip per finding) — triggers:**

- "Apply the AI review's fixes"
- "Walk me through the findings"
- "Go through the review one finding at a time"
- "Help me address the critical findings"
- "Fix the review comments the bot left"

**Scope filters — triggers:**

- "Critical only" / "show me only the critical findings"
- "Warnings only" / "info-level only"
- "Just the ones from the `cursor` leg" (multi-leg attribution)
- "The findings we all three legs agreed on"

**Fall through** to a sibling skill when the developer:

- Wants a **local review** on uncommitted changes → parent
  [`ai-diff-reviewer`](../SKILL.md) skill (default review flow). This
  sub-skill reads reviews that already exist on the PR; the parent
  produces a new one locally.
- Wants to **install the CI action** → [`setup`](../setup/SKILL.md).
- Wants to **customize the reviewer** → [`generate-extension`](../generate-extension/SKILL.md).
- Wants to **author or refresh the PR body** → [`open-pr`](../open-pr/SKILL.md).
- Wants to read **human** reviewer comments (not the bot's) → defer;
  this skill filters to bot artefacts by design. `gh pr view --comments`
  covers human threads.

If the intent is ambiguous ("show me the review" on a repo where the
Action posted 4 legs, or on a PR with both bot findings and human
comments), ask ONE clarifying question before acting.

---

## Step 0 — Trust boundary

This sub-skill's reads and writes are enumerated below. **Nothing else
happens.**

**Reads (always allowed, no consent needed):**

- `git`: `git branch --show-current`, `git rev-parse HEAD`,
  `git status`, and `git show <marker-sha>:<path>` — the latter is
  Step 6b's **primary** pre-image source (used on every `apply`, not
  just the empty-`diffHunk` case) and is safe by construction:
  write-free, streamed to stdout, never touches the working tree,
  never creates or modifies a ref. Use it whenever the sub-skill
  needs SHA-pinned file content.
- `gh`: `gh pr view` for PR metadata, `gh api graphql` for reviews +
  comments. **Not** `gh pr diff` — it always emits current tip vs
  base with no way to pin a historical SHA, so it can't be used for
  pre-image or freshness checks (Step 6b covers this in detail); if
  the sub-skill needs SHA-pinned file content, use `git show`
  instead.
- Local files under the current git checkout, via `Read` / `Grep` /
  `Glob` — only for files a finding references.

**Writes (only under the per-finding consent contract in Step 6):**

- **Edit source files** — when the developer answers *"apply"* on a
  finding that has a `\`\`\`suggestion` block, the sub-skill reads the
  target file, replaces the exact lines the suggestion covers, and
  writes the file back. Never touches lines outside the suggestion's
  range.
- **Create `.review/deferred.md`** (0-byte if empty, otherwise a
  single-line-per-deferral list) — only when the developer answers
  *"defer"* on any finding AND is prompted-and-agrees to persist. If
  the developer prefers ephemeral deferrals, the file is not created.
- **Append `.review/deferred.md` to `.gitignore`** — only as a
  one-time follow-up the very first time `.review/deferred.md` is
  created in this repo, AND only when the developer accepts the
  separate consent prompt in Step 6c. Never modifies existing
  `.gitignore` rules; only appends one line (plus a labeled comment
  identifying this sub-skill as the source) after the existing
  content.

**It does not:**

- `git add`, `git commit`, `git push`, `git checkout`, or any
  history-rewriting operation.
- Post replies, resolve conversations, dismiss reviews, approve, or
  request changes on the PR — the sub-skill is read-only against
  the GitHub PR-review surface. Replies to individual threads are a
  separate concern (a future `respond-to-review` sub-skill).
- Call the LLM provider directly — it uses the coding agent that's
  already running you.
- Fabricate suggestions, expand suggestion blocks beyond what the bot
  wrote, or reason about "what the bot probably meant" when a
  suggestion is absent. If a finding has no suggestion, *"apply"* is
  not offered; the developer implements the fix themselves.
- Change any file outside the finding's `path:line` scope on
  *"apply"*. If a suggestion is malformed (e.g. the file no longer
  matches the expected context), the sub-skill refuses and surfaces
  the finding for manual application.

If the coding agent has broader powers (e.g. can run arbitrary bash),
those come from the harness, not this sub-skill.

---

## Step 1 — Detect context

Establish the mode (present vs. walkthrough vs. refuse) before
fetching anything from GitHub.

```bash
# Current branch + head SHA
HEAD_BRANCH="$(git branch --show-current)"
HEAD_SHA="$(git rev-parse HEAD)"
HEAD_SHORT="$(git rev-parse --short HEAD)"

# Repo slug (owner/repo)
REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || echo '')"

# PR for the current branch (if any)
PR_JSON="$(gh pr view --json number,url,state,headRefOid,labels,isDraft 2>/dev/null || true)"
PR_NUMBER="$(gh pr view --json number --jq '.number // empty' 2>/dev/null || true)"
```

`PR_NUMBER` is consumed by every subsequent `gh` / `gh api graphql`
invocation (Steps 2b, 3, 7). Extracted via `gh pr view --json …
--jq …` (not standalone `jq`) so the sub-skill's dependency set
stays `git` + `gh` — the two bins already declared in
`metadata.requires.anyBins`, matching sibling sub-skills. If the
`gh pr view` call fails (no open PR on this branch), `PR_NUMBER` is
empty and the mode table below routes to `refuse-soft`.

Decide the mode from the state:

| State | Mode | Skill behavior |
|---|---|---|
| On `main` / `master` / `develop` / `trunk` with no PR | **refuse** | Ask the developer to switch to a feature branch that has an open PR. |
| Detached HEAD | **refuse** | Ask the developer to check out a branch first. |
| `PR_JSON` empty (no PR for this branch) | **refuse-soft** | Point at [`open-pr`](../open-pr/SKILL.md): *"No open PR for `<branch>`. Open one first with the `open-pr` sub-skill, wait for CI to review, then re-run me."* |
| `PR_JSON` state is CLOSED or MERGED | **warn** | The review artefacts still exist and are readable — offer to read anyway ("this PR is closed / merged; want the historical review or should I stop?"). Do not proceed silently. |
| `PR_JSON` state is OPEN | **read** | Go to Step 2. |

**On `gh` missing or unauthenticated:** surface the exact remediation
(`brew install gh` or `gh auth login`) and stop. Do not attempt to
scrape the PR page via a browser — the sub-skill is designed for
`gh` + GraphQL and there is no fallback path.

---

## Step 2 — Fetch the review

This is the mechanical heart of the sub-skill. The GraphQL query below
is **adapted from** [`docs/PR_REVIEW_WORKFLOW.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/docs/PR_REVIEW_WORKFLOW.md#ready-to-copy-graphql-query)
— the selection set is extended (`createdAt`, `submittedAt`,
`startLine` for multi-line-suggestion apply) but the **filter rules
are the shared contract**: if the doc says *"skip `isMinimized ==
true`"*, this sub-skill does. If it says *"anchor on the most recent
marker"*, this sub-skill does. Divergence in the selection set is
allowed and expected as this sub-skill's needs evolve; divergence in
the filter rules is a bug — fix the doc, then re-sync here.

### 2a. Identify the bot login

The Action collapses prior artefacts belonging to the user its
`github-token` authenticates as. For consumers using
`secrets.GITHUB_TOKEN` (default), that's `github-actions[bot]`; for
consumers using a PAT / automation account, it's the PAT owner's
login. Hardcoding `github-actions[bot]` silently mis-filters every
PAT consumer — Step 2c drops the real review author and Step 2d
then fires the *"Missing (no marker found)"* branch even though a
live review exists on the PR.

Resolve the login in this order (first non-empty wins):

1. **`AIPRR_BOT_LOGIN` env var** — explicit override; always respected.
2. **The most recent non-minimized `<!-- ai-pr-reviewer-marker -->`
   comment's `author.login`** — authoritative and self-configuring
   across `github-actions[bot]`, PATs, and automation accounts. Read
   it from the `comments` collection you already fetch in Step 2b;
   pick the newest comment whose body starts with
   `<!-- ai-pr-reviewer-marker -->`.
3. **`gh api user --jq .login`** — a last-resort fallback only when
   no marker exists on the PR (a first-run install where CI hasn't
   posted anything yet).
4. **The literal string `github-actions[bot]`** — final default when
   even step 3 fails; a warning should be surfaced to the developer
   since this is almost always wrong for PAT consumers.

The Step 2b query already returns the top-level `comments` nodes
with `author.login`. To keep the sub-skill's runtime deps aligned
with `metadata.requires.anyBins` (`git` + `gh` only — **no**
standalone `jq`), issue a small dedicated `gh api graphql` call for
the marker-author read, using `gh`'s built-in `--jq` filter to
extract the login without shelling out to `jq`:

```bash
BOT_LOGIN="${AIPRR_BOT_LOGIN:-}"

if [ -z "$BOT_LOGIN" ]; then
  # Preferred: derive from the most recent non-minimized marker comment.
  # Uses gh's built-in --jq (no standalone jq dependency).
  BOT_LOGIN="$(gh api graphql \
    -F owner="${REPO%%/*}" -F repo="${REPO##*/}" -F number="$PR_NUMBER" \
    -f query='
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          comments(first: 100) {
            nodes { body isMinimized createdAt author { login } }
          }
        }
      }
    }' \
    --jq '[.data.repository.pullRequest.comments.nodes[]
           | select((.isMinimized | not)
                    and (.body | startswith("<!-- ai-pr-reviewer-marker -->")))]
           | sort_by(.createdAt) | reverse | .[0].author.login // empty' \
    2>/dev/null)"
fi

if [ -z "$BOT_LOGIN" ]; then
  # Fallback: current authenticated user (only accurate on first-run repos
  # where no marker exists yet). Warn the developer that this is a guess.
  BOT_LOGIN="$(gh api user --jq .login 2>/dev/null || echo 'github-actions[bot]')"
fi
```

`gh api graphql --jq` runs the filter inside `gh` itself — it does
not shell out to standalone `jq`, so this snippet stays inside the
`git` + `gh`-only dep constraint declared in `metadata.requires`.
Do NOT reintroduce a standalone `jq | ...` pipe here — the moment
you do, the primary marker-author path breaks on vanilla macOS /
minimal agents and the fallback (`gh api user`) mis-filters live
reviews for every PAT / automation-account consumer.

### 2b. Run the GraphQL query

```bash
gh api graphql -F owner="${REPO%%/*}" -F repo="${REPO##*/}" \
  -F number="$PR_NUMBER" -f query='
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      comments(first: 100) {
        nodes {
          id
          body
          isMinimized
          createdAt
          author { login }
        }
      }
      reviews(first: 100) {
        nodes {
          id
          body
          state
          isMinimized
          submittedAt
          author { login }
          commit { oid }
          comments(first: 100) {
            nodes {
              id
              body
              path
              line
              startLine
              diffHunk
              isMinimized
            }
          }
        }
      }
    }
  }
}'
```

`startLine` is `null` for single-line inline comments and non-null for
multi-line ones (e.g. a `\`\`\`suggestion\`\`\` block covering several
lines). When you later need the apply range for Step 6b, derive it as
`start = startLine or line`, `end = line` — the reviewer's `line`
field is the range end for multi-line comments and the anchor for
single-line ones. `originalLine` is the outdated-position field
(diff-relative for reviews that no longer point at the current file
state) and is **not** the multi-line-range start — do not use it here.

**`line: null` is a distinct case.** GitHub returns `line: null` (and
`startLine: null`) when the comment is anchored on a hunk that is no
longer present in the diff — the review was posted, the developer
force-pushed or rebased, and the anchor became orphaned. This shows
up precisely on the stale-review paths Step 2d allows after
acknowledgement. Because `[startLine or line, line]` would collapse
to `[null, null]` and every downstream comparison would either crash
or produce a bogus apply range, treat `line: null` as a **read-only**
finding:

- Include the finding in Step 4's presentation with a marker like
  `[⚠️ outdated anchor — apply disabled]`.
- In Step 6a's walkthrough, present the body normally.
- In Step 6's menu, **never offer `apply`** — only `defer`, `skip`,
  `discuss`, `stop`. Do not attempt to reconstruct a range from
  `originalLine` (it's diff-relative to a hunk that no longer
  exists; the numbers won't map cleanly onto today's file).
- In Step 3a's consensus scoring, group `line: null` findings only
  with other `line: null` findings on the same `path` — the range-
  overlap predicate is undefined for null ranges.

The `diffHunk` field carries the raw diff hunk the comment was
anchored on (the `-`, `+`, and context lines around the anchor). It
is used to render the surrounding patch when the developer needs
context — that display belongs in **Step 4's presentation table**
(next to the file/line) and/or **Step 6a's walkthrough banner** for
the current finding, NOT in Step 5 (which is only the top-level
routing menu: `done` / `walk through` / `critical only` / `warnings
and up` / `filter by leg` / `cancel`). `diffHunk` also serves as an
optional
consistency check inside Step 6b — but it is **not** the primary
source of the expected pre-image; that role belongs to
`git show <marker-sha>:<path>` (see Step 6b for the full
derivation). Note the GraphQL schema does **not** expose a `side`
field on `PullRequestReviewComment` — side-of-diff lives on
`PullRequestReviewThread.diffSide`. Step 6b sidesteps this by
reading the reviewed-commit file content directly, which is
independent of hunk sides. In practice this is safe because
`findings_to_gh_inline_comments()` in `scripts/reviewer.py` posts
anchors with `side: RIGHT` by default (the `"side": f.side or
"RIGHT"` line inside that function is the authoritative reference —
cite the function name, not a raw line number that will drift on
the next edit), so `line` / `startLine` refer to post-image file
positions that resolve cleanly
via `git show`. A rare `side: LEFT` anchor (removed-line comment)
will fail the `git show`-slice consistency check in Step 6b and
route to `skip / discuss`.

`BOT_LOGIN` is **not** a GraphQL variable — it's applied client-side
in Step 2c's filter. GitHub's GraphQL API rejects unused declared
variables (`variableNotUsed`), so declaring `$bot: String!` while only
using it in a follow-up `jq` filter fails the query outright. Keep
the login filter in Step 2c and the GraphQL selection set variable-free.

### 2c. Filter to live bot artefacts

Two collections come back — `comments` (top-level, includes tracking
markers) and `reviews` (with nested inline `comments`). Apply the
mandatory rules from [`docs/PR_REVIEW_WORKFLOW.md` § Mandatory rules](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/docs/PR_REVIEW_WORKFLOW.md#mandatory-rules):

1. **Filter out `isMinimized == true`** at every level (top-level
   comments, review bodies, inline review comments).
2. **Filter authors** to `$BOT_LOGIN` only.
3. **Anchor on the latest `<!-- ai-pr-reviewer-marker -->` comments** —
   plural when multiple legs ran. Each marker's body starts with the
   marker string; each carries the SHA its leg reviewed.

**IAR note.** The marker may contain an HTML-comment `IterationState`
JSON block and a short gen/round/policy annotation — ignore both when
collecting findings (they are telemetry, not review comments). The
inline comments you present are already post-IAR-dedup. If the
developer expected a finding that appeared in a local review but not
in CI, suggest applying `full-review-please` (the
`iteration-escape-label`, one-shot full review with state preserved)
or removing the `applied-label` then re-triggering for a full state
reset — see
[`docs/ITERATION_AWARENESS.md` § 8](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/docs/ITERATION_AWARENESS.md).

Emit the filtered set to your working context as a list of
`{leg_label, sha, review_body, inline_comments[]}` records.

### 2d. Anchor + freshness check

Tracking markers are top-level **issue comments** — they have no
`commit.oid`. The SHA source depends on the marker state (the H3 tells
you which one: `_Working…_` vs. `✅ done` / `🚫 done` vs. `❌ failed`):

- **Working markers** (`render_tracking_body_working()` in
  `scripts/reviewer.py`) — include a `Full SHA: \`<sha>\`` line in
  the body. Parse it. This is the in-flight case; a Working marker
  means the review is still running or its terminal transition
  failed.
- **Done and failed markers** (`render_tracking_body_done()` /
  `render_tracking_body_failed()`) — do NOT render `Full SHA:`; they
  only carry the 7-char short SHA in the H3 (`AI review for
  \`<7chars>\``). Resolve the full SHA by joining the marker to its
  matching non-minimized review via the provider marker (both carry
  `<!-- ai-pr-reviewer-provider: <id> -->`), then read the joined
  review's `commit.oid` — that is the **primary** SHA source for
  completed reviews (which is the common case). The 7-char prefix in
  the H3 is a useful cross-check but is ambiguous by itself.

If the joined review is missing when the marker says `done` or
`failed` (rare — the mid-flight transition raced), fall back to the
7-char H3 prefix and warn the developer that the review body could
not be paired.

Compare the resolved SHA against `HEAD_SHA`:

| Marker SHA | HEAD SHA | Interpretation |
|---|---|---|
| Matches HEAD | Matches | Review is for the current commit — proceed normally. |
| Matches HEAD's parent (marker == `HEAD~1`) | Matches | The developer has made **one commit locally** since the review; HEAD itself is a commit CI never saw. Warn: *"The review is for `<marker-sha>`, but you've committed `<HEAD>` since then. Findings may already be resolved by your local commit; CI will re-review once you push. Continue anyway?"* — proceed only after ack. Pre-image checks in Step 6b will still refuse silently-clobbering an already-edited line. |
| Older than HEAD's parent | New commits landed since the review | Warn: *"The review is for `<sha>`, but HEAD is `<newer>`. Reading anyway, but the findings may be stale — CI will likely re-review. Continue?"* |
| Newer than HEAD | Local branch is behind origin | Warn: *"Origin has `<sha>`, your local HEAD is `<older>`. Consider `git pull` before applying."* — proceed only after ack. |
| Missing (no marker found) | — | CI hasn't run yet OR the label-gate is missing OR all matrix legs' secrets are unset. See [`docs/PR_REVIEW_WORKFLOW.md` § "I don't see any live review"](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/docs/PR_REVIEW_WORKFLOW.md#i-dont-see-any-live-review) for the diagnosis table. Stop; do not proceed with an empty review. |

Only exact-HEAD is fully authoritative; every other row above
(including `marker == HEAD~1`) requires an explicit developer
acknowledgement before Step 4 presents findings or Step 6b applies
anything. This closes the "silent green light" case where a single
uncommitted-since-CI commit would otherwise be treated as
authoritative.

Never fabricate findings when the review is missing or stale.

### 2e. Extract per-finding severity

GitHub inline review comments carry `body` only —
`findings_to_gh_inline_comments()` in `scripts/reviewer.py` does
**not** prefix severity into the comment body, so severity is **not**
recoverable from the inline comment itself. The authoritative
per-finding severity lives in the **review summary body's findings
table**:

```markdown
### 2. Findings table

| # | Severity   | File                | Summary        |
|---|------------|---------------------|----------------|
| 1 | 🚨 critical | `src/auth.ts:55`   | SQL injection… |
| 2 | ⚠️ warning  | `src/cache.ts:120` | Unbounded key… |
```

For each inline comment produced by the leg, join to the summary
table by matching on `path:line`:

1. **Locate the findings table heading-agnostically.** Scan
   `review_body` for a Markdown table whose header row contains all
   of `Severity`, `File`, and `Summary` (case-insensitive, in any
   column order). The heading right above the table varies —
   `prompts/default.md` instructs models to emit it under
   `### 2. Findings table`, while the local review flow uses
   `## Findings`, and consumers with custom prompts may use anything —
   so anchoring on the header row (not the heading text) is the only
   reliable strategy.
2. Parse each row into `{severity, path, line, summary}`. The severity
   cell is `<emoji> <label>` (`🚨 critical`, `⚠️ warning`, `ℹ️ info`);
   normalise to the bare label. The `File` cell is typically
   backticked (`` `src/auth.ts:55` ``, matching what `prompts/default.md`
   emits) and may additionally be bold (`` **`src/auth.ts:55`** ``);
   **strip surrounding backticks AND surrounding `**` before splitting
   on `:`** — otherwise the join against the GraphQL `path` field
   (unquoted) misses every row and every finding falls to the `info`
   fallback below.
3. For each inline comment, look up a matching row. Because a
   multi-line inline comment carries a `startLine` (range start) and
   `line` (range end), while a summary table's `File` cell almost
   always cites a single line — usually the range **start** (e.g.
   `` `src/auth.ts:55` `` for a 55–58 suggestion), occasionally the
   end, occasionally an arbitrary line inside the range — the join
   must be range-aware, not exact-scalar:

   - Compute the comment's covered range as `[startLine or line, line]`.
     (For single-line comments where `startLine` is null, that
     collapses to `[line, line]`.)
   - A summary row matches when `row.path == comment.path` **and**
     `row.line ∈ [startLine or line, line]` (i.e. the row's cell
     falls anywhere inside the comment's covered range).
   - On match, set `comment.severity = row.severity`.

   The exact-scalar version this originally shipped with (matching
   only `row.line == comment.line`) silently downgrades every
   multi-line critical to `info` when the summary table cites
   `startLine`, and those findings then disappear from a
   `critical only` walkthrough — quiet severity downgrade.
4. On **no match** (the model posted an inline anchor the summary
   table doesn't reflect, a stale/reordered table, or no matching
   table found at all), default to `info` **and record that fact** —
   the walkthrough banner in Step 6a surfaces the finding as
   `[ℹ️ info (assumed — no summary row)]` so the developer knows the
   tier is a fallback, not a model call.

The tracking comment's *Highest severity: <tier>* line is an
**aggregate** across the whole review — useful for the review-level
headline but never a per-finding value. Do not infer severity from
inline-body tone or keywords ("this is critical because…"); use the
summary table join or the `info` fallback.

The severity attached here is what Step 4's presentation table shows
and what Step 5's `critical only` / `warnings and up` filters gate on.

---

## Step 3 — Attribute per leg

For consumer repos running a single provider (~95% of the population),
skip this step — there's one live review; every finding belongs to
"the review".

For repos running a multi-provider matrix (this repo, some enterprise
consumers), the mandatory rules require attributing each finding to
its leg via the `self-reviewed:<provider>` labels the Action applies
on success. Read the PR's labels:

```bash
gh pr view "$PR_NUMBER" --json labels --jq '.labels[].name' \
  | grep '^self-reviewed:'
```

Map each live tracking marker to its leg. The marker + review body
contain provider-specific hints emitted by `provider_marker()` in
`scripts/reviewer.py` — an HTML marker of the form
`<!-- ai-pr-reviewer-provider: <provider-id> -->` (`cursor`,
`claude-code`, `codex`, or `anthropic`) — grep for the marker prefix
`<!-- ai-pr-reviewer-provider:` and read the value on the same line.
The `self-reviewed:*` label list confirms which legs completed. When 3 live reviews are
present and only 2 `self-reviewed:*` labels are set, the third leg is
either mid-flight or its post-review label step raced — surface this
as a note, don't refuse.

### 3a. Consensus scoring

Group findings by overlapping `(path, range)` — where each finding's
range is `[startLine or line, line]` (the same range predicate Step
2e uses for the severity join). Two findings belong to the same group
when their paths match AND their ranges overlap at all — i.e.
`f1.start <= f2.end AND f2.start <= f1.end`. Exact scalar `(path,
line)` grouping silently misses multi-leg consensus when three legs
flag the same multi-line issue with slightly different anchors (e.g.
`55–58` from one leg, `line:55` from another, `56–59` from a third)
— those surface as three "single-leg" findings instead of the strong
signal the multi-leg design is built to expose. Keep the predicate
symmetric with Step 2e so the two flows agree on what "the same
finding" means.

| Findings grouped by overlapping `(path, range)` | Interpretation |
|---|---|
| All active legs called it | **Strong signal** — high confidence, agreed across legs. |
| Majority of active legs called it | **Consensus** — likely real, one leg missed it or filtered by extension. |
| Single leg called it | **Provider-specific** — could be a real finding one provider's training caught, or a leg-specific false positive. Present at nominal severity but note the single-leg source. |
| Two legs disagree on severity (`critical` vs. `info` at overlapping anchors) | **Split call** — surface both severities and both bodies; let the developer decide. |

Findings not shared across legs are still valid — they're just
weaker signal than the ones every leg agreed on. Do not silently
drop them.

---

## Step 4 — Present the review

Emit the findings in the parent skill's **exact format** so the
developer's mental model transfers cleanly. This is the parity
contract.

### 4a. Single-leg output (single-provider consumer)

The outer fence uses **four** backticks so the nested `` ``` `` in
the finding-body placeholder below renders as literal code, not a
premature fence close.

````markdown
## Verdict (from CI review on <PR URL>)
<one sentence — pulled verbatim from the review body's Verdict line
when present, otherwise inferred from the highest-severity finding.>

## Findings

| # | Severity | File | Summary |
|---|----------|------|---------|
| 1 | 🚨 critical | `src/auth.ts:55` | SQL injection in raw-string login query |
| 2 | ⚠️ warning  | `src/cache.ts:120` | Unbounded cache key cardinality |
| 3 | ℹ️ info     | `tests/utils.ts:12` | Helper could be reused from existing fixture |

### 1. `src/auth.ts:55` — 🚨 critical
<the finding body verbatim from the inline comment, including any
```suggestion block```>

### 2. `src/cache.ts:120` — ⚠️ warning
<...>

### 3. `tests/utils.ts:12` — ℹ️ info
<...>

## Notes (no inline anchor)
- <cross-cutting concerns, from the review body's Notes section>

**Recommendation:** approve / request-changes / comment-only
**Review SHA:** <sha> (matches HEAD ✓ | HEAD is 2 commits newer ⚠️)
````

### 4b. Multi-leg output (this repo + power consumers)

Add a **Legs** column to the findings table and a per-leg breakdown
at the bottom. Each leg's abbreviation (`A` = anthropic, `C` =
cursor, `CC` = claude-code, `CO` = codex) is derived from the
`self-reviewed:*` labels; document the mapping once at the top.

```markdown
## Verdict (consensus across <n> legs)
<one sentence describing the consensus — "Blocking security fix
needed" when ≥ 2 legs called a critical; "Approve — no blockers"
when all legs are info-or-none.>

Legs on this PR: A=anthropic (~), C=cursor (~), CC=claude-code (~), CO=codex (~).
Live reviews: <n>. Findings shown are the union across all legs.

## Findings

| # | Severity | File | Summary | Legs |
|---|----------|------|---------|------|
| 1 | 🚨 critical | `src/auth.ts:55` | SQL injection | A / C / CO |
| 2 | 🚨 critical | `src/cache.ts:120` | Unbounded cache key cardinality | A |
| 3 | ⚠️ warning  | `src/log.ts:44` | Log level normalization | A / C |
| 4 | ℹ️ info     | `tests/utils.ts:12` | Helper could be reused | C |
| 5 | ℹ️ info     | `docs/README.md:8` | Typo: "recieve" → "receive" | CO |

### 1. `src/auth.ts:55` — 🚨 critical  [A / C / CO — 3/3 consensus]
<the finding body from the leg with the most detailed suggestion,
followed by a "See also" bullet with the other legs' bodies collapsed
by default. When legs disagree meaningfully, surface both bodies in
full.>

### 2. `src/cache.ts:120` — 🚨 critical  [A — single-leg]
<body verbatim, with a note: "Only the anthropic leg called this
critical; other legs did not flag this path. Could be leg-specific
sensitivity or a real gap other providers' training missed.">

<... same shape for remaining findings ...>

## Notes (aggregated across legs)
- <deduplicated cross-cutting notes; if two legs said "the same"
  thing in Notes, show it once.>

**Recommendation:** request-changes (blocking on 2 critical findings,
1 with 3-leg consensus)
**Review SHA:** <sha> (matches HEAD ✓)
```

### 4c. Notes on formatting

- **Do not fabricate a Verdict line** if the review body doesn't have
  one. Infer it from the highest-severity finding, and mark the
  inference: *"Verdict (inferred from findings): …"*.
- **Preserve suggestion blocks verbatim.** If a finding has a
  `\`\`\`suggestion ... \`\`\`` block, keep the fence, keep the
  content, do not "clean up" whitespace.
- **Copy inline comment bodies exactly.** Reviewers wrote what they
  wrote; do not paraphrase.
- **Attach the review SHA + freshness marker** at the bottom of every
  presentation. It's the single most important context for whether
  the findings are actionable.

---

## Step 5 — Ask ONE routing question

After presenting the review, ask exactly one question to route the
next action. Default choice must be the safest one (do nothing).

```text
<n> finding(s) on your PR. What next?

  - done              → I've shown the summary; take it from here.
  - walk through      → I'll go finding-by-finding; you say apply/defer/skip.
  - critical only     → walk through, but only the <k> critical(s).
  - warnings and up   → walk through the ~<w> warning-or-critical findings.
  - filter by leg     → pick a specific leg (A / C / CC / CO) and walk its findings.
  - cancel            → stop. No walkthrough.
```

Response handling:

- **done** → go to Step 7 (summary + hand-off).
- **walk through** → go to Step 6 with all findings.
- **critical only** → go to Step 6 with `severity == critical` only.
- **warnings and up** → go to Step 6 with `severity in {critical, warning}`.
- **filter by leg** → ask which leg (A / C / CC / CO), then go to
  Step 6 with only that leg's findings.
- **cancel** → stop. Print nothing else.

If the developer's response is ambiguous, default to **done** (the
minimally-disruptive choice) — do not silently open a walkthrough.

---

## Step 6 — Walkthrough mode

For each finding in the filtered set, in severity order (critical
first, then warning, then info), present it in isolation with a
five-option prompt (`apply` is only shown when the finding carries a
`\`\`\`suggestion\`\`\`` block, so on findings without one the visible
menu collapses to four options).

### 6a. Per-finding presentation

The outer fence uses **four** backticks so the nested `` ``` ``
suggestion-block placeholder inside renders as literal code, not a
premature fence close.

````text
──────────────────────────────────────────────────────────
Finding <k> of <n>: <path>:<line>  [<severity emoji> <severity>]  [<legs>]

<finding body verbatim, wrapped ~80 chars>

<if there's a ```suggestion``` block:>
  Proposed fix:
    ```suggestion
    <content verbatim>
    ```
  This replaces lines <start>–<end> in <path> with the block above.

Options:
  - apply       → I'll edit <path> to replace lines <start>–<end> with
                   the suggestion. You'll see the diff and confirm again
                   before I write.  <-- only shown when a suggestion exists
  - defer       → I'll add this to `.review/deferred.md` (opt-in) so you
                   don't lose it. You handle it later.
  - skip        → move on; no action taken.
  - discuss     → surface the full body so you can copy it into a PR
                   comment reply. You handle the discussion in the UI.
  - stop        → end the walkthrough here; go to Step 7 summary.
──────────────────────────────────────────────────────────
````

### 6b. Handling `apply`

Only offered when the finding has a `\`\`\`suggestion` block AND the
path + line range is reachable in the current working tree.

1. **Read the target file**. If `path` doesn't exist in the working
   tree (e.g. renamed since the review), warn and skip: *"`<path>`
   isn't in the current tree — the file may have been renamed. Falling
   back to `skip`."*
2. **Verify the pre-image**. A GitHub `\`\`\`suggestion\`\`\`` block
   carries **only the replacement text** — not the lines it replaces.
   The apply step guards against silent-overwrite by first
   reconstructing what the reviewer actually saw, then comparing
   that to the current working tree.

   **Primary source: `git show <marker-sha>:<path>`.** This streams
   the file's exact content at the reviewed commit to stdout
   (write-free — never touches the working tree). Slice lines
   `start`–`end` from that stream (either read the whole stream and
   index into it, or pipe through `sed -n "${start},${end}p"`) —
   that is the expected pre-image. This works for every RIGHT-side
   comment (the default `findings_to_gh_inline_comments()` posts,
   per the `"side": f.side or "RIGHT"` fallback inside that function
   in `scripts/reviewer.py`), which is the ~100% case for
   AI Diff Reviewer output: the `line` / `startLine` fields refer to
   post-image file positions, so slicing the reviewed-commit file at
   those line numbers gives the anchor's actual pre-image content.

   Then compare that slice line-for-line against the working tree's
   `<path>` at lines `start`–`end`. If they match, proceed to
   preview (step 3 below). If they diverge (developer's already
   edited nearby, or a different SHA than the review anchored on),
   present the three-option mismatch menu — and NEVER fall through
   to the happy-path preview automatically:

   *"Lines `<start>`–`<end>` in `<path>` no longer match the file at
   the reviewed commit. Applying anyway may produce incorrect
   output. Options: `force` / `skip` / `discuss`."*

   - **`skip`** — take no action; advance to the next finding in
     Step 6 (identical to the top-level `skip` option).
   - **`discuss`** — surface the full finding body so the developer
     can copy it into a PR comment reply; advance to the next
     finding (identical to top-level `discuss`).
   - **`force`** — the escape hatch when the developer has *read*
     the divergence and wants to overwrite anyway (e.g. because
     their local edits are trivial reformatting and the suggestion
     still applies logically). Procedure:

     1. Print a second banner making the risk explicit: *"You're
        about to overwrite lines `<start>`–`<end>` in `<path>` even
        though the working tree differs from what the review saw.
        This may discard local edits. Type `yes force` to confirm,
        anything else to cancel."*
     2. Require the literal string `yes force` (not just `yes`, not
        `y`, not `apply`) — the exact-string requirement is the
        second, deliberately-annoying confirmation the guardrail
        depends on.
     3. On `yes force`: skip the pre-image check, jump straight to
        preview step 3, then on the preview's own `yes` write via
        the `Edit` tool. On anything else: cancel and re-present
        the original three-option mismatch menu.

     Once `force` is chosen and the write completes, log the fact
     in Step 7's summary (*"1 apply-with-force"* row) so the
     developer has an audit trail of which finding bypassed the
     safety check. `force` never becomes silent-default and never
     applies without both the mismatch banner AND the `yes force`
     literal.

   **Secondary consistency signal: `diffHunk`.** When present, cross-
   check the sliced pre-image against the `diffHunk`'s post-image
   side (`+` and context lines). If the slice does not appear inside
   the hunk's `+`/context region at all, the anchor is likely a rare
   LEFT-side (removed-line) comment, or the hunk header has drifted;
   refuse the apply and route to `skip / discuss` rather than
   attempt to reconstruct the LEFT-side pre-image via `@@` header
   arithmetic (out of scope for this sub-skill).

   **Failure modes and forbidden fallbacks.** If `git show
   <marker-sha>:<path>` fails (the marker SHA has been force-pushed
   away, the path was renamed in that commit, or the reviewed
   commit was garbage-collected), refuse the apply and route to
   `skip / discuss` — never silently overwrite. **Do not** use
   `git checkout <marker-sha> -- <path>` as a workaround: that
   overwrites `<path>` in the working tree with the historical blob,
   silently clobbering the developer's current file, defeating the
   pre-image safety check (the tree then trivially "matches" by
   construction), and contradicting Step 0's ban on `git checkout`.
   **Also do not** use `gh pr diff` as a fallback source of "expected
   content" — it always emits the PR's current tip vs base with no
   way to pin a specific SHA, so it would silently compare against
   today's tip instead of the reviewed commit and produce false
   matches. `git show` is the only SHA-pinned read-only path.
3. **Preview the change**. Show a compact 3-way diff:
   ```
   <path>:<start>–<end>
   
   - [existing line 1]
   - [existing line 2]
   + [suggestion line 1]
   + [suggestion line 2]
   
   Apply? (yes / no / edit)
   ```
4. **On yes** — use the `Edit` tool to write the file. Confirm:
   *"Wrote <path>. Not staged, not committed — that's your call. Run
   `git diff <path>` to review."*
5. **On no** — treat as `skip`; move to next finding.
6. **On edit** — ask what the developer wants to change in the
   suggestion, then re-run the preview. No silent partial writes.

### 6c. Handling `defer`

If `.review/deferred.md` does not exist, ask before creating it:

> *"I'll add this to `.review/deferred.md` so you can track it later.
> Heads-up: this file is **not** git-ignored by default in this repo —
> decide whether to commit it (deferrals shared with the team) or keep
> it private (personal notes). I can add `.review/deferred.md` to
> `.gitignore` if you'd like. Create? (yes / no)"*

If **yes**, `mkdir -p .review` and append a single line:

```
- PR #<n> · <path>:<line> · <severity> · <one-line summary> · reviewed at <marker sha>
```

Then, **only the first time the file is created in this repo**, offer
the ignore follow-up:

> *"Add `.review/deferred.md` to `.gitignore` so this file stays
> private? (yes / no)"*

On **yes** — check the repo's `.gitignore`; if `.review/deferred.md`
(or a `.review/` block covering it) isn't already there, append
`.review/deferred.md` on a new line with a preceding
`# Personal PR-review deferrals (managed by ai-diff-reviewer apply-review sub-skill)`
comment for future readers. Never modify existing `.gitignore` rules.
On **no** — proceed; the file stays tracked, and re-asking on future
deferrals is skipped.

If **no** (to the original create prompt), note the deferral in the
sub-skill's working memory only (ephemeral — lost when the session
ends). Continue.

### 6d. Handling `discuss`

Print the finding body one more time in a copy-pasteable block and
suggest: *"Open the finding on GitHub to reply:
`gh pr view <n> --web` and scroll to `<path>:<line>`, or use
`gh api` to post a review comment reply."* Do not attempt to post the
reply automatically — that's a future
[`respond-to-review`](https://github.com/DailybotHQ/ai-diff-reviewer/issues)
sub-skill's territory.

### 6e. Handling `skip` / `stop`

- **skip** — no-op. Move to next finding.
- **stop** — exit the walkthrough loop early. Go to Step 7 with
  whatever tally accumulated so far.

### 6f. Cost discipline

Cap the walkthrough at the same inline-comment cap the CI Action uses
(default 10 — see `max-inline-comments` in `action.yml` and
`DEFAULT_MAX_INLINE_COMMENTS` in `scripts/reviewer.py`). If the review
has more than 10 findings, present the first 10 and offer: *"10 more
findings not shown. `next 10` / `stop`?"*

Consumer repos that raised `max-inline-comments` above 10 in their
workflow will legitimately have more inline comments on a single
review — the "10" here is the default; when the actual review has
more, present in batches of 10 regardless of the CI cap.

---

## Step 7 — Summary + hand-off

After the walkthrough (or after `done` in Step 5), print a compact
summary:

```text
Walkthrough complete for PR #<n>:

  Applied:   <k> finding(s)
    - <path>:<line> — <one-line summary>
    - ...
  Deferred:  <m> finding(s)  [saved to `.review/deferred.md`]
    - <path>:<line> — <one-line summary>
    - ...
  Skipped:   <s> finding(s)
  Unaddressed: <u> finding(s)  [still open on the PR]

Next steps:
  - Review what got applied:   git diff
  - Stage + commit:            git add <paths> && git commit
  - Push:                      git push
  - Watch the re-review:       gh pr checks <n> --watch
```

**Optional next-step hint.** If the walkthrough deferred any critical
findings, add a nudge:

```text
Note: <k> critical finding(s) deferred, not applied. The CI Action
will re-flag them on the next push unless addressed or marked as
accepted in your review conversation.
```

If everything critical was applied and only info-level findings were
skipped, close with:

```text
Ready to push — critical findings addressed. The re-review should
come back clean or with only info-level notes.
```

---

## Guardrails — what this skill MUST NOT do

- **Never `git add`, `git commit`, `git push`.** Applied fixes stay
  unstaged. Commit + push is the developer's judgment.
- **Never edit source files outside a finding's `path:line` scope.**
  Suggestion blocks specify their range; the sub-skill honors that
  exactly. Adjacent lines are not touched.
- **Never *silently* apply a suggestion when the pre-image doesn't
  match.** Warn and offer `force / skip / discuss`; `force` is only
  reachable after a second explicit "yes" from the developer at the
  Step 6b menu. This matches the Step 6b menu's behavior — the
  guardrail forbids sneaking past a mismatch, not the developer's
  right to override it once they've seen the divergence.
- **Never fabricate findings.** If Step 2 returns an empty live set
  (no markers, or all minimized), stop and diagnose — do not invent
  reviews to be "helpful".
- **Never paraphrase inline comment bodies.** Copy them verbatim,
  including code fences, formatting, and language.
- **Never post replies, resolve conversations, dismiss reviews,
  approve, or request changes on the PR.** The sub-skill is read-only
  against the PR-review surface. A future `respond-to-review`
  sub-skill will handle those; do not preempt it.
- **Never automatically follow "See also" links.** If a review body
  points at an issue / RFC / doc, surface the link — don't fetch it.
- **Never bypass the `isMinimized` filter.** Collapsed comments are
  stale by construction; showing them would violate the parity
  contract with the workflow doc.
- **Never mix findings across two different marker SHAs.** If two
  markers exist for the same leg (shouldn't happen, but can if a
  collapse step failed), surface both and stop — do not auto-merge
  their findings.
- **Never bypass the Step 6 per-finding confirmation.** Even in a
  single-finding "obvious" case, always ask.

---

## Coordinating with other skills

- **[`../SKILL.md`](../SKILL.md) (parent — local review flow)** —
  produces the same output shape this sub-skill reproduces. If the
  developer wants to run a fresh review against local uncommitted
  changes (before pushing), route to the parent. This sub-skill reads
  reviews that already exist on the PR remote.
- **[`../open-pr/SKILL.md`](../open-pr/SKILL.md) (sibling — author
  the PR)** — natural predecessor. The recommended full loop is:
  *(1) run the local review (parent) → (2) address findings →
  (3) open the PR (open-pr) → (4) wait for CI review → (5) read +
  apply the CI review (this sub-skill) → (6) push fixes → (7)
  optionally refresh the PR body (open-pr edit mode).*
- **[`../setup/SKILL.md`](../setup/SKILL.md) (sibling — install the
  CI action)** — different phase of the lifecycle. If this sub-skill
  runs on a repo that has no `self-reviewed:*` labels and no
  `<!-- ai-pr-reviewer-marker -->` comments, and no CI workflow
  invoking the Action, the diagnosis is *"CI Action not installed"* —
  route to `setup`.
- **[`../generate-extension/SKILL.md`](../generate-extension/SKILL.md)
  (sibling — tailor the reviewer prompt)** — orthogonal to reading
  reviews, but if the same findings keep showing up across PRs and
  aren't real bugs (false positives), that's the signal to add
  overrides via `generate-extension`.

---

## Non-blocking rule

Reading and applying a review must **never block the developer's
primary work**. If `gh` is missing, unauthenticated, network is down,
the GraphQL API errors, or the review is stale/missing:

1. Print the diagnosis (from [`docs/PR_REVIEW_WORKFLOW.md` § Edge
   cases](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/docs/PR_REVIEW_WORKFLOW.md#edge-cases)
   when applicable) in one paragraph.
2. Print the exact remediation (`gh auth login`, `git pull`, "wait for
   CI to finish", etc.) once.
3. Do **not** retry automatically.
4. Do **not** enter a diagnostic loop.
5. End the turn.

This matches the parent skill and `open-pr`'s non-blocking discipline.

---

## Sample dialogues

### Dialogue A — Single-leg, read-only summary

```text
Developer: "read the CI review on my PR"

Skill:
  1. Detect:  branch=fix/oauth-callback, PR #214, state OPEN.
  2. Fetch:   1 live tracking marker at SHA a1b2c3d = HEAD. Bot login
              github-actions[bot] confirmed.
  3. Filter:  1 review body, 3 inline comments, all live (0 minimized).
              Attribute: no self-reviewed:* labels → single-leg setup.
  4. Present:

    ## Verdict (from CI review on PR #214)
    Ship it — one info finding on test coverage, nothing blocking.

    ## Findings
    | # | Severity | File               | Summary                       |
    |---|----------|--------------------|-------------------------------|
    | 1 | ℹ️ info  | src/auth/oauth.ts:88 | Consider adding a test for   |
    |   |          |                    | the Slack callback branch     |

    ### 1. `src/auth/oauth.ts:88` — ℹ️ info
    The fix covers Microsoft, GitHub Enterprise, and Google. Slack
    also hits this decoder in production but isn't covered by the 4
    added tests. Optional — not blocking.

    ## Notes
    - Suggestion block absent; discretion.

    **Recommendation:** approve
    **Review SHA:** a1b2c3d (matches HEAD ✓)

  5. "1 finding on your PR. What next?
       - done          → I've shown the summary.
       - walk through  → I'll go finding-by-finding (each finding then
                         offers apply / defer / skip / discuss / stop)."

Developer: "done"

Skill:
  7. Summary:
     - Applied:  0
     - Deferred: 0
     - Skipped:  0
     - Unaddressed: 1 info finding (optional)
     
     Ready to push — no blocking findings.
```

### Dialogue B — Multi-leg matrix, critical walkthrough

The outer fence uses **four** backticks so the nested `` ``` ``
suggestion block below renders as literal code, not a premature
fence close.

````text
Developer: "walk me through the critical findings"

Skill:
  1. Detect:  branch=feat/notif-prefs, PR #384, state OPEN.
  2. Fetch:   3 live tracking markers at SHA b3f0e12 = HEAD. All
              authored by github-actions[bot].
  3. Attribute: labels self-reviewed:anthropic, self-reviewed:cursor,
                self-reviewed:codex present. 5 total findings.
                Consensus: 1 critical agreed by A+C+CO (SQL inj),
                1 critical called by A only (unbounded cache).
  4. Present:

    ## Verdict (consensus across 3 legs)
    Blocking security fix needed — SQL injection agreed by all 3 legs.

    Legs on this PR: A=anthropic, C=cursor, CO=codex.
    Live reviews: 3. Findings shown are the union across all legs.

    ## Findings
    | # | Severity | File               | Summary                    | Legs      |
    |---|----------|--------------------|----------------------------|-----------|
    | 1 | 🚨 crit  | src/auth.ts:55     | SQL injection in login     | A/C/CO    |
    | 2 | 🚨 crit  | src/cache.ts:120   | Unbounded cache key card.  | A         |
    | 3 | ⚠️ warn  | src/log.ts:44      | Log level normalization    | A/C       |
    | 4 | ℹ️ info  | tests/utils.ts:12  | Helper could be reused     | C         |
    | 5 | ℹ️ info  | docs/README.md:8   | Typo: recieve → receive    | CO        |

    (bodies below…)

    **Recommendation:** request-changes (2 crits, 1 with 3-leg consensus)
    **Review SHA:** b3f0e12 (matches HEAD ✓)

  5. "5 findings. What next?"

Developer: "critical only"

Skill:
  6a. Finding 1 of 2:  src/auth.ts:55  🚨 critical  [A/C/CO]

      All three legs flagged raw-string interpolation of `email` and
      `password` into a SQL query. Proposed fix (from anthropic leg,
      most detailed):

      ```suggestion
      const user = await db.query(
        'SELECT id FROM users WHERE email = $1 AND password_hash = $2',
        [email, hashPassword(password)]
      );
      ```

      This replaces lines 55–58 in src/auth.ts.

      Options: apply / defer / skip / discuss / stop

Developer: "apply"

Skill:
  6a.1  Reading src/auth.ts... pre-image matches (lines 55–58 unchanged
        since review SHA b3f0e12).
        
        Preview:
          - const q = `SELECT id FROM users WHERE email = '${email}'`
          - const q2 = `${q} AND password_hash = '${hashPassword(password)}'`
          - const user = await db.query(q2);
          - if (!user) throw new AuthError('invalid');
          + const user = await db.query(
          +   'SELECT id FROM users WHERE email = $1 AND password_hash = $2',
          +   [email, hashPassword(password)]
          + );
          + if (!user) throw new AuthError('invalid');
        
        Apply? (yes / no / edit)

Developer: "yes"

Skill:
  6a.2  Wrote src/auth.ts. Not staged, not committed.

  6b. Finding 2 of 2:  src/cache.ts:120  🚨 critical  [A — single-leg]

      Only the anthropic leg flagged this. The other 2 legs saw the
      same lines but didn't call it critical — could be leg-specific
      sensitivity to unbounded caches, or a real gap.
      
      No suggestion block; anthropic's body:
      
        The cache key includes the raw request body which grows
        unbounded with unique payloads. Consider a bounded LRU
        (`lru-cache`) or hashing the key to fixed length.
      
      Options: defer / skip / discuss / stop

Developer: "defer"

Skill:
  6b.1  Create .review/deferred.md? (yes / no)
Developer: "yes"
  6b.2  Wrote .review/deferred.md:
        - PR #384 · src/cache.ts:120 · critical · Unbounded cache key
          cardinality · reviewed at b3f0e12

  7. Summary:
     - Applied:  1 finding (Finding 1 — SQL injection fix)
     - Deferred: 1 finding (Finding 2 — unbounded cache, saved to
                            .review/deferred.md)
     - Skipped:  0
     - Unaddressed: 3 findings (1 warning, 2 info — didn't walk them)

     Note: 1 critical finding deferred, not applied. The CI Action will
     re-flag it on the next push unless addressed or marked as accepted
     in your review conversation.

     Next steps:
       - Review what got applied:   git diff src/auth.ts
       - Stage + commit:            git add src/auth.ts && git commit
       - Push:                      git push
       - Watch the re-review:       gh pr checks 384 --watch
````

### Dialogue C — Stale review (CI still running)

```text
Developer: "read the review"

Skill:
  1. Detect:  branch=fix/typo, PR #199, state OPEN.
  2. Fetch:   1 live tracking marker at SHA 9a8b7c6. HEAD is 5f4e3d2
              (2 commits newer).
  4. Warn + present:

     ⚠️ The review is for 9a8b7c6, but your local HEAD is 5f4e3d2
     (2 commits ahead). CI is likely re-reviewing right now — the
     findings below may be stale. Continue?

Developer: "yes"

Skill:
  [presents the stale review with a "REVIEW SHA does NOT match HEAD"
   warning on every finding + at the bottom]

  5. "3 findings (all from the stale review at 9a8b7c6). What next?"

Developer: "cancel — I'll wait for CI"

Skill:
  7. Summary:
     - Applied:   0
     - Deferred:  0
     - Skipped:   0
     - Unaddressed: 3 (from stale review — waiting for CI to re-review)
     
     Next: `gh pr checks 199 --watch` and re-run me when the fresh
     review lands.
```

### Dialogue D — No CI review yet (Action not installed)

```text
Developer: "what did the review say?"

Skill:
  1. Detect:  branch=feat/foo, PR #77, state OPEN.
  2. Fetch:   0 tracking markers found. 0 reviews from github-actions[bot].
  Diagnosis (from docs/PR_REVIEW_WORKFLOW.md § "I don't see any live
  review"):

    Possibilities:
    - The workflow is still running (check gh pr checks 77).
    - The CI Action isn't installed on this repo (no
      .github/workflows/pr-review.yml — check with `ls
      .github/workflows/`).
    - All matrix legs' API-key secrets are unset on this repo (typical
      for fresh forks). Look for the ::notice:: in the Actions log.
    - The PR has label-gate set and is missing the gate label.

  → Which fits? If the Action isn't installed, the `setup` sub-skill
    can install it: "set up ai-diff-reviewer for this repo". If secrets
    are unset, add them at Settings → Secrets and re-run.

  [stops — does not fabricate a review]
```

---

## Notes

- **This is a read + apply skill, not a git skill.** It reads what's
  on the PR page and (with per-finding consent) writes source files.
  Commits, pushes, merges, and PR-conversation actions (reply,
  resolve, dismiss) are the developer's responsibility, and often the
  merge-queue's.
- **The workflow doc is the single source of truth.** If
  [`docs/PR_REVIEW_WORKFLOW.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/docs/PR_REVIEW_WORKFLOW.md)
  changes (new legs, different marker string, different label
  scheme), this sub-skill's Step 2 rules update in lockstep. Do not
  fork the diagnosis rules here.
- **The read-only default is deliberate.** Most sessions will `done`
  after Step 4 — the developer just wanted to know what the review
  said, and will apply fixes with their own hands. Walkthrough mode
  exists for the sessions where the developer explicitly wants the
  skill to help.
- **Multi-leg attribution matters more than it looks.** When 3/3
  legs agree on a finding, that's strong signal — this sub-skill
  makes that visible so the developer can prioritize accordingly.
  When 1/3 legs called something, it's still worth reading, but the
  attribution helps calibrate confidence.
- **Bugs, feature requests, and edge cases not covered here:**
  [`github.com/DailybotHQ/ai-diff-reviewer/issues`](https://github.com/DailybotHQ/ai-diff-reviewer/issues).
