---
name: ai-diff-reviewer-open-pr
description: Author a well-documented GitHub pull request — title and body — for the current branch. Reads the diff and commit trail, infers a Conventional Commits (or repo-native) title, drafts a structured body with the sections a good PR review actually needs (Summary, Changes, Test plan, Related issues, Screenshots when UI files changed, Breaking changes when applicable, Risks), merges with `.github/pull_request_template.md` when present (never overwrites), previews everything to the developer, and executes via `gh pr create` (new PR) or `gh pr edit` (refresh existing PR). Supports draft PRs, stacked PRs against non-default bases, and forks. Use when the developer says "open the PR", "create a pull request", "draft the PR title and description", "write the PR body", "update the PR description", "the PR body is a one-liner — rewrite it properly", or "make a draft PR for this branch".
version: "2.0.0"
documentation_url: https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/skills/ai-diff-reviewer/open-pr/SKILL.md
user-invocable: true
metadata: {"openclaw":{"emoji":"📝","homepage":"https://github.com/DailybotHQ/ai-diff-reviewer","requires":{"anyBins":["git","gh"]}}}
allowed-tools: Bash, Read, Grep, Glob
---

# AI Diff Reviewer — Open PR (sub-skill)

Companion to the [`ai-diff-reviewer`](../SKILL.md) skill. Where the parent
**reviews** the current branch's diff locally, this sub-skill takes the
next logical step: **authors a well-documented pull request** from the
same diff — title, body, and (on request) a draft opener.

The design philosophy is unopinionated where it can be, opinionated where
it needs to be:

- **Unopinionated:** the section shape adapts to your
  `.github/pull_request_template.md` when one exists. If your team already
  writes PRs with `## Rollout plan` and a `## Security review` checkbox,
  those survive intact.
- **Opinionated:** every PR gets a **Summary that leads with the outcome**,
  a **Test plan a reviewer can actually run**, and — when the diff
  signals it — a **Screenshots** prompt for UI changes and a **Breaking
  changes** callout for API changes. These are the sections whose absence
  reviewers complain about; the skill won't let them slip.

Nothing gets pushed. Nothing gets merged. The skill only ever writes the
PR **title + body** on the remote via `gh`, always after a single-yes
preview.

---

## When it fires

**Create a fresh PR** — triggers:

- "Open the PR", "open a pull request for this branch"
- "Create the PR", "create a pull request"
- "Draft the PR title and description"
- "I'm ready to push this for review — write the PR"
- "Make a draft PR" (adds `--draft`)

**Refresh / fix an existing PR** — triggers:

- "Update the PR description"
- "The PR body is a one-liner — rewrite it in the proper format"
- "Fix the PR title, it doesn't match the diff anymore"
- "Refresh the PR body — I pushed new commits"

**Fall through** to a sibling skill when the developer:

- Wants a **local review before pushing** → parent
  [`ai-diff-reviewer`](../SKILL.md) skill (default review flow). This
  sub-skill is the natural *next* step after that review.
- Wants to **install the CI action** → [`setup`](../setup/SKILL.md).
- Wants to **customize the review** → [`generate-extension`](../generate-extension/SKILL.md).
- Wants a **git commit message** (not a PR body) → defer; this skill
  writes PRs, not individual commits.

If the intent is ambiguous ("write the PR" on a branch that's not
pushed yet, or on a repo with no `origin` set), ask ONE clarifying
question before acting.

---

## Step 0 — Trust boundary

This skill writes **two things** on the remote, both only after an
explicit **yes** in the Step 6 preview:

- **The PR title** (via `gh pr create --title` or `gh pr edit --title`).
- **The PR body** (via `--body-file` so multi-line Markdown round-trips
  cleanly).

It does **not**:

- Push commits, force-push, rebase, cherry-pick, or rewrite git history.
- Auto-add reviewers, assignees, labels, milestones, or projects unless
  the developer explicitly asks and confirms. (`--assignee @me` is the
  one exception in create mode — always applied.)
- Auto-merge, auto-approve, or convert draft ↔ ready-for-review without
  explicit intent in the trigger.
- Touch any file in the working tree.
- Call the LLM provider directly, or send data anywhere besides the
  `gh` API calls it announces in the preview.

If the branch is not pushed, the skill surfaces the exact command
(`git push -u origin <branch>`) and stops. It **never** runs `git push`
itself.

---

## Step 1 — Detect context

Establish the mode (create vs. edit vs. refuse) before drafting anything.

```bash
# Current branch + head SHA
HEAD_BRANCH="$(git branch --show-current)"
HEAD_SHA="$(git rev-parse --short HEAD)"

# Base: prefer the tracked upstream's short name, fall back to the repo's
# default branch (asks gh; falls back to `main` if gh unavailable).
BASE="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null | sed 's|.*/||')"
if [ -z "$BASE" ]; then
  BASE="$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null || echo main)"
fi

# Repo slug (owner/repo)
REPO="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || echo '')"

# Does a PR already exist for the current branch?
PR_JSON="$(gh pr view --json number,url,title,body,isDraft,baseRefName,headRefName,state,author 2>/dev/null || true)"
```

Decide the mode from the state:

| State | Mode | Skill behavior |
|---|---|---|
| On `main` / `master` / `develop` / `trunk` with no PR | **refuse** | Ask the developer to switch to a feature branch first. |
| Detached HEAD | **refuse** | Ask the developer to check out a branch first. |
| `PR_JSON` non-empty and state is OPEN | **edit** | Load the existing title + body; go to Step 2 (edit path). |
| `PR_JSON` non-empty and state is CLOSED or MERGED | **refuse-soft** | Do not edit a closed/merged PR. Offer: (a) open a new PR from the same branch (create mode), or (b) reopen the closed one manually then re-run this skill. Never `gh pr reopen` automatically. |
| `PR_JSON` empty | **create** | Plan `gh pr create` against `<base>`; go to Step 2 (create path). |
| Working tree has uncommitted changes that look scope-relevant to the diff | **warn** | Show `git status --short`; ask "commit these first? (y/n)". Never `git add` on the developer's behalf. |

**On `gh` missing or unauthenticated:** surface the exact remediation
(`brew install gh` or `gh auth login`) and stop. Do not attempt to draft
the body — writing a PR body the developer has to manually paste is a
downgrade; use the non-blocking rule below instead.

---

## Step 2 — Read the diff and gather signals

Read enough diff to draft the sections; do not stuff the whole patch
into your working context.

### Create mode

```bash
git fetch origin "$BASE" --quiet 2>/dev/null || true

# Summaries first (cheap):
git diff --stat "origin/${BASE}...HEAD"
git log --oneline "origin/${BASE}..HEAD"

# Full patch second (may be large; read it, but do not paste it back):
git diff "origin/${BASE}...HEAD"
```

### Edit mode

```bash
gh pr diff "$PR_NUMBER" --patch
gh pr view "$PR_NUMBER" --json title,body,commits,files,isDraft,url
```

### Signal collection (both modes)

While reading the diff and commit trail, extract these **signals** —
they drive which optional sections appear in the body:

1. **Issue references.** Grep the commit messages for
   `(Closes|Fixes|Resolves|Refs) #\d+` (case-insensitive). Collect every
   unique reference; these go into the `## Related issues` section
   verbatim. If the diff title has a `(#123)`-style trailer, capture
   that too.
2. **Breaking-change markers.** Look for `BREAKING CHANGE:` in commit
   bodies (Conventional Commits marker), any commit subject with
   `!:` (e.g. `feat!:` or `refactor!:`), or diff removals in public API
   surface (exported functions, `action.yml` inputs, CLI flags,
   published HTTP routes). Any hit → `## Breaking changes` section is
   mandatory.
3. **UI signals.** Look at the file extensions in `git diff --name-only
   "origin/${BASE}...HEAD"`. If any of `.tsx`, `.jsx`, `.vue`, `.svelte`,
   `.astro`, `.css`, `.scss`, `.less`, `.html` are touched (excluding
   `docs/**`, `README*`, `CHANGELOG*`) → prompt for screenshots in the
   preview (opt-in — never fabricate).
4. **Migration signals.** File names matching
   `migrations?/`, `alembic/versions/`, `db/migrate/`, `prisma/migrations/`,
   `atlas.hcl`, or `*.sql` → `## Migrations` section is mandatory.
5. **Dependency signals.** Any of `package.json`, `package-lock.json`,
   `pnpm-lock.yaml`, `yarn.lock`, `requirements*.txt`, `pyproject.toml`,
   `Pipfile`, `Pipfile.lock`, `poetry.lock`, `Gemfile`, `Gemfile.lock`,
   `go.mod`, `go.sum`, `Cargo.toml`, `Cargo.lock`, `composer.json`,
   `composer.lock` touched → `## Dependencies` section auto-populated
   with what changed.
6. **Convention detection.** Read the last 20 merged PR titles to detect
   the repo's title convention *empirically* rather than assuming
   Conventional Commits:

   ```bash
   gh pr list --state merged --limit 20 --json title --jq '.[].title'
   ```

   If ≥ 60% of them match `^(feat|fix|docs|chore|refactor|test|ci|perf|style|build|revert)(\(.+\))?!?: `,
   use Conventional Commits (Step 4). Otherwise, use plain-sentence titles.
   Cache the observation for the preview — surface *"detected convention:
   Conventional Commits (14/20 recent PRs match)"* so the developer can
   override.

Emit these signals to your working context; do not print them to the
developer unless the preview needs them.

---

## Step 3 — Merge with the repo's PR template (when present)

GitHub renders `.github/pull_request_template.md` (or
`.github/PULL_REQUEST_TEMPLATE.md` — same file, different casing) into
the PR body input by default when a developer opens a PR in the UI. This
skill respects that convention:

```bash
TEMPLATE=""
for path in \
  .github/pull_request_template.md \
  .github/PULL_REQUEST_TEMPLATE.md \
  docs/pull_request_template.md \
  pull_request_template.md
do
  if [ -r "$path" ]; then TEMPLATE="$(cat "$path")"; break; fi
done
```

**Merge rules (never overwrite):**

| Template has | Skill's body has | Result in final body |
|---|---|---|
| `## Summary` | `## Summary` | Skill's Summary wins (it's diff-derived); heading kept. |
| `## Test plan` | `## Test plan` | Skill's Test plan wins; heading kept. |
| `## Checklist` (repo-specific tick boxes) | *(no equivalent)* | Preserved intact — appended at the end. |
| `## Rollout plan` (or any custom section) | *(no equivalent)* | Preserved intact — appended at the end. |
| `<!-- HTML comment instructions -->` | *(no equivalent)* | Stripped from the final body. Instructions are for the author, not the reviewer. |

Surface the merge outcome in the Step 6 preview: *"Merged with
`.github/pull_request_template.md`: preserved `## Checklist` and `##
Rollout plan`; the template's `<!-- comment -->` guidance was
stripped."* The developer can override any auto-merged section in the
`edit` branch of the confirmation.

If **no template exists**, use the default body template from Step 5.

---

## Step 4 — Draft the title

Title budget: **≤ 72 chars total** (GitHub truncates in list views
around 80). The body carries the rest.

### 4a. Convention detection (see Step 2)

If Step 2 detected Conventional Commits, use the format below. If not,
use a plain sentence — capitalized first word, no trailing period, ≤ 72
chars.

### 4b. Conventional Commits type inference

Infer `<type>` from the diff signals, in this precedence order (first
match wins):

| Diff signal | `<type>` |
|---|---|
| A commit subject already starts with `feat!:` / `fix!:` / `perf!:` (breaking change marker) | Preserve that type; add `!` marker on the PR title too. |
| Bug-fix language in commit messages (`fix:`, `fixes #`, `resolves #`, "bug", "hotfix") | `fix` |
| Only `docs/**`, `README*`, `CHANGELOG*`, or `*.md` files touched | `docs` |
| Only `.github/workflows/**`, `.github/actions/**`, CI configs (`.circleci/`, `.gitlab-ci.yml`, `azure-pipelines.yml`) touched | `ci` |
| Only test files touched (`tests/**`, `test/**`, `**/*.test.*`, `**/*_test.go`, `**/*_spec.rb`, `__tests__/**`) | `test` |
| Only dependency manifests + lockfiles touched (no source changes) | `chore(deps)` |
| Performance markers in commits (`perf:`, "optimize", "cache", "batch", "lazy", "debounce", "virtualization") | `perf` |
| Renames / moves / extractions without behavior change (large diff, small semantic change) | `refactor` |
| Only style-layer files touched (`.css`, `.scss`, Tailwind class-only changes, formatting-only commits) | `style` |
| Adds a new module / route / feature flag / schema field / CLI subcommand | `feat` |
| Everything else with user-visible behavior | `feat` |
| Everything else without user-visible behavior | `chore` |

### 4c. Scope

`<scope>` is the shortest identifier that names the touched surface:

- If the diff is concentrated (>70% of touched lines) in a single
  top-level directory, use that directory's basename: `auth`, `chat`,
  `billing`, `docs`, `reviewer`.
- If the change touches a single well-known concept across many
  directories (e.g. logging refactor), use that concept: `logging`,
  `i18n`.
- If no clear single scope dominates, **omit** the scope: `feat: …`
  rather than `feat(mixed): …`.

### 4d. Description

- Imperative mood, present tense (*"add", "fix", "rename"* — not "added"
  or "adds").
- No trailing period.
- Concrete over vague: `fix(auth): reject empty callback state` beats
  `fix(auth): handle edge case`.
- No `[WIP]`, no ticket numbers in the title (issue links go in the
  body). Draft state is expressed via `--draft`, not `[WIP]`.

### 4e. Examples

- `feat(reviewer): add per-repo severity overrides via extension file`
- `fix(auth): reject OAuth callback when state param contains slash`
- `docs(prompts): document local↔CI parity for extension files`
- `chore(deps): bump actions/checkout from v4 to v5`
- `feat!: rename api-key input to provider-api-key` *(breaking change)*

---

## Step 5 — Draft the body

The default body template — used when no PR template exists, or as the
starting point when one does. Every section explains **why it's here**
inline so the writing rules are self-enforcing.

```markdown
## Summary

<1–3 sentences. Lead with the OUTCOME (what ships and why), not the
mechanism. Plain English. No diff stats. No file paths. ≤ 280 chars.>

## Changes

<3–8 bullets naming the concrete edits. Each ≤ 15 words. Group by area
if there are multiple concerns. Example:
- Add `PromptExtensionLoader` that reads `.review/extension.md`
- Concatenate extension content to base prompt at boot
- Log the composed prompt's byte size at DEBUG for verifying parity
>

## Related issues

<Only present when Step 2 found issue references. Use GitHub's linking
keywords so the issues auto-close on merge:
- Closes #123
- Fixes #456
- Refs #789 (context only — not closed by this PR)
Omit the section entirely when there are none — never write "N/A".>

## Test plan

<3–8 imperative bullets grouped into named categories. Minimum 3 bullets.
Each bullet ≤ 15 words. A reviewer must be able to run each bullet
mechanically. Example:

**Happy path**
- Run `python3 -m unittest discover -s tests`
- Open a PR against `main` on a fork; confirm review comment appears

**Edge cases**
- Empty diff (no changes) → skill prints "nothing to review" and exits 0
- Base branch does not exist locally → falls back to `git merge-base`

**Regression**
- Existing `strictness: block-on-warning` behavior unchanged on PR #212
>

## Screenshots

<UI CHANGES ONLY. Only present when Step 2 detected touched UI files
AND the developer confirmed screenshots exist. Format:
- Before: [drag image or paste URL]
- After:  [drag image or paste URL]
Omit the section entirely when there are no UI changes — never write
"N/A".>

## Breaking changes

<MANDATORY when Step 2 detected a breaking-change signal
(`feat!:`, `BREAKING CHANGE:`, removed public API). 2-4 sentences with:
1. What breaks — the exact symbol / input / URL / behavior.
2. Who is affected — first-party consumers, third-party, both.
3. Migration path — the concrete steps a consumer takes to adapt.
Example:
- **What breaks:** the `api-key` input has been renamed to
  `provider-api-key` in `action.yml`.
- **Who is affected:** every consumer of `DailybotHQ/ai-diff-reviewer@v2`
  / `@v2.x` — YAML workflows will fail with "invalid input" at boot.
- **Migration:** rename the key in your workflow YAML:
  `with: { api-key: ... }` → `with: { provider-api-key: ... }`.
  No code changes required.
Omit the section entirely when there are no breaking changes.>

## Risks

<2-4 sentences with a 3-part structure: [failure mode] — [affected scope]
— [rollback plan]. Keep at the product / rollout level, not
implementation. ≤ 400 chars. For low-risk additive changes, use:
"Low risk — change is additive (no existing behavior modified). Affected:
[area]. Rollback: revert the PR; no data migration involved."
Always include a rollback plan — never write bare "None" or "Low risk"
without the mitigation.>

## Migrations

<Only present when Step 2 detected migration files. Format:
- `migrations/0042_add_notification_prefs` — adds 3 NULLABLE columns,
  online, reversible via `db migrate down`
- `migrations/0043_backfill_prefs` — batched data backfill, idempotent
Omit the section entirely when no migrations touched.>

## Dependencies

<Only present when Step 2 detected dependency changes. Format:
- Added: `zod@3.22.0` (schema validation for extension file parsing)
- Removed: `joi` (replaced by zod)
- Bumped: `actions/checkout@v4 → v5` (upstream security fix)
Omit the section entirely when no deps touched.>
```

### Writing rules (self-enforcing — apply them as you draft)

1. **Outcome first** — the Summary's first sentence is what the change
   does for the user, not how it does it. *"Ship per-team notification
   preferences"* not *"Refactor the NotificationSettings class."*
2. **Plain English over jargon** — translate to user impact. *"Reduce
   p95 checkout latency from 4.2s to 1.1s"* not *"Migrate to
   Prisma-native transactions."*
3. **Concrete beats vague** — quantify when possible. *"Low risk"* alone
   is noise; always include the mitigation.
4. **No file paths, diff stats, line counts, commit hashes** in the
   body. The GitHub PR diff has all of that one click away.
5. **No agent / tool attribution** (*"Claude built…", "Cursor
   generated…"*) — the team shipped it.
6. **Optional sections vanish when empty** — never `N/A`, never
   `TBD`, never a section with a single "None" bullet. Absence is
   information.
7. **Imperative mood in bullets** — *"Add", "Fix", "Rename"*, not
   *"Added", "Adds", "This adds"*.
8. **Two to four sentences per prose section** — one is too vague, five
   is a brain dump. Two to three is the sweet spot.
9. **No `@`-handles inside section bodies** — reviewer / assignee
   handles belong in GitHub's reviewer/assignee UI, not in the free-form
   body. The one exception: mentioning a *domain owner* for context
   (*"Coordinated with @security-team on the token handling"*) is fine
   and encouraged when the change crosses ownership boundaries.
10. **Preserve the repo's brand spelling** — grep for the product name in
    `README.md` and use that exact capitalization throughout the body.

---

## Step 6 — Preview + single confirmation

Show a tight, readable preview in this exact order — this is the
"look-once-yes-once" contract:

```text
About to <create | update> a pull request on <owner/repo>:

  Branch:      <head>  →  <base>
  Draft:       <yes | no>
  Convention:  <Conventional Commits | plain sentence>
               (detected: <n>/20 recent merged PRs match Conventional Commits)
  Title:       <the final title>

  Body (Markdown, sections in final order):
    ─────────────────────────────────────────────
    <full body — every section header + content, verbatim as it will be
    written; no truncation, no ellipsis>
    ─────────────────────────────────────────────

  PR template:      <detected at .github/pull_request_template.md | none>
  Merge decisions:  <"Preserved: ## Checklist, ## Rollout plan. Overrode:
                     ## Summary, ## Test plan (skill-anchored versions
                     used so they stay diff-derived)." | "N/A — no template">

  Sections included:
    ✓ Summary                         (mandatory)
    ✓ Changes                         (mandatory)
    ✓ Test plan                       (mandatory)
    ✓ Related issues                  (detected #123, #456)
    ✓ Breaking changes                (detected `feat!:` in commit 3f2c9a1)
    ✗ Screenshots                     (UI files touched: 4 — SKIPPED per your input)
    ✓ Risks                           (mandatory)
    ✗ Migrations                      (no migration files detected)
    ✓ Dependencies                    (detected package.json changes)

  Command:  <gh pr create --base <base> --head <branch> [--draft]
              --assignee @me --title "<title>" --body-file <tmpfile>
            | gh pr edit <n> --title "<title>" --body-file <tmpfile>>

  Confirm? (yes / edit / cancel)
```

Response handling:

- **yes** → Step 7.
- **edit** → ask which section(s) or field(s) to change (title, or a
  named body section). After the developer's edit, RE-RENDER the whole
  preview and ask again. No silent partial application.
- **cancel** → stop. Print nothing else.

**Edit mode addendum:** when refreshing an existing PR, also print a
compact **diff of the body** — the developer needs to see what's
changing, not just what will be written:

```text
  Body diff (current PR → proposed):
    ─────────────────────────────────────────────
    - fix bug in oauth callback
    + ## Summary
    + Fix OAuth callback failing when the `state` query param contains a
    + slash. Users hitting Microsoft / GitHub Enterprise were redirected
    + to /404 instead of completing sign-in.
    + …
    ─────────────────────────────────────────────
```

**Never skip confirmation.** A PR title + body is reviewer-visible,
consumer-visible, and often lifted verbatim into release notes.

---

## Step 7 — Execute via `gh`

Write the body to a temp file so multi-line content, code fences, and
HTML comments round-trip cleanly. Allow ≥ 30 s for either call
(`gh` can be slow on repos with many reviewers or protection rules).

### Create mode

```bash
BODY_FILE="$(mktemp -t ai-diff-reviewer-body.XXXXXX.md)"
printf '%s\n' "$BODY" > "$BODY_FILE"

CMD=(gh pr create
  --title "$TITLE"
  --body-file "$BODY_FILE"
  --base "$BASE"
  --head "$HEAD_BRANCH"
  --assignee @me)

# Add --draft only when the developer's trigger explicitly asked for it
# ("draft PR", "WIP PR", "--draft").
[ "$DRAFT" = "true" ] && CMD+=(--draft)

"${CMD[@]}"
rm -f "$BODY_FILE"
```

After success:

- Capture the PR URL from `gh pr create` stdout.
- Print the URL + a one-line "next step" hint (see Step 8).

### Edit mode

```bash
BODY_FILE="$(mktemp -t ai-diff-reviewer-body.XXXXXX.md)"
printf '%s\n' "$BODY" > "$BODY_FILE"

gh pr edit "$PR_NUMBER" \
  --title "$TITLE" \
  --body-file "$BODY_FILE"

rm -f "$BODY_FILE"
```

Never pass `--reviewer`, `--assignee` (other than `@me` in create mode),
`--label`, `--milestone`, or `--project` unless the developer's trigger
explicitly asked for them AND those choices appeared in the Step 6
preview.

---

## Step 8 — Surface the result + hand-off

**On success:**

```text
✓ <Created | Updated> PR #<n> — <title>
  <URL>

Next steps:
  - Review it in the browser:  gh pr view <n> --web
  - Watch CI as it runs:       gh pr checks <n> --watch
  - Read the CI review once it lands:  (see the `apply-review` sub-skill,
                                        or the trigger "read the CI review
                                        on my PR")
  - When CI is green:          gh pr merge <n> --squash --delete-branch
                               (or use the merge button on the PR page)
```

If the repo has the AI Diff Reviewer CI Action installed (detectable by
grepping `.github/workflows/` for `DailybotHQ/ai-diff-reviewer`), the
`apply-review` sub-skill is the natural next step after this PR is open:
CI will post its review within a few minutes, and `apply-review` will
read it back, present the findings in the same format as the local
review, and — with per-finding consent — help apply the fixes.

If the parent `ai-diff-reviewer` skill's local review flow ran earlier
in the same session and produced any 🚨 critical or ⚠️ warning findings,
append a soft nudge:

```text
  Note: the local review in this session found <n> critical / <m>
  warning findings. Consider addressing them before requesting review,
  or leave them noted in the PR description under a "Known issues"
  bullet in `## Risks`.
```

**On failure:** quote the `gh` error verbatim. Do NOT retry in a loop
(non-blocking rule). Common ones:

| `gh` error | Meaning | Skill's action |
|---|---|---|
| `not logged in` / `authentication required` | `gh` unauthenticated | Print `gh auth login`; stop. |
| `no commits between <base> and <head>` | Branch not pushed | Print `git push -u origin <branch>`; stop. |
| `pull request already exists for branch` | Race condition | Re-run Step 1 to load the just-created PR; switch to edit mode; re-preview. |
| `base <name> not found` | Typo'd base branch | Print `gh repo view --json defaultBranchRef`; ask developer for the correct base; re-preview. |
| `Resource not accessible by integration` | Fork PR without write access | Explain the limitation (fork PRs need `gh pr create --repo <upstream>` and the developer's own token); suggest the developer runs the command manually with the printed title + body. |
| Any 5xx from GitHub | Server-side | Stop. Print body draft to terminal so the developer can paste in the UI. Do not loop. |

---

## Guardrails — what this skill MUST NOT do

- **Never push commits, force-push, rebase, or rewrite history.** If the
  branch is not pushed, print `git push -u origin <branch>` and stop.
- **Never auto-merge, auto-approve, auto-request-review, or convert
  draft ↔ ready-for-review** without the developer saying so in the
  trigger AND confirming in the preview.
- **Never `gh pr reopen`** a closed PR. Offer to create a new PR from
  the current branch instead.
- **Never fabricate** issue references, CI URLs, screenshots, migration
  claims, or dependency changes. If a signal is unclear, ask ONCE or
  omit the section — never invent.
- **Never write `N/A`, `TBD`, `None`, or `-` as a placeholder** for an
  optional section. Omit the whole section (heading + body) together
  instead. Absence is information.
- **Never overwrite `.github/pull_request_template.md` sections
  silently** — Step 3 merge rules apply, and the merge decision is
  surfaced in the preview.
- **Never paste raw `git diff` output, `git diff --stat` output, file
  paths, line counts, or commit hashes** into the body. The GitHub diff
  has all of it one click away.
- **Never embed reviewer / assignee `@`-handles inside body sections.**
  Handles belong in GitHub's reviewer UI, not in prose.
- **Never open a PR from a protected branch** (`main`, `master`,
  `develop`, `trunk`). Refuse and ask the developer to switch first.
- **Never open a PR while the working tree has uncommitted scope-relevant
  changes.** Warn, show `git status --short`, and ask. Do not `git add`.
- **Never skip the Step 6 confirmation** — even on trivial edits, even
  in edit mode.

---

## Coordinating with other skills

- **[`../SKILL.md`](../SKILL.md) (parent — local review flow)** —
  natural predecessor. The recommended flow is: *(1) run the local
  review, (2) act on the findings, (3) open the PR.* The parent's Step
  4 output ("Verdict + Findings table + Recommendation") is exactly the
  input a developer needs to draft a good Summary + Test plan here.
- **[`../apply-review/SKILL.md`](../apply-review/SKILL.md) (sibling —
  read + apply the CI review on the PR)** — natural successor. Once
  this sub-skill has opened the PR and CI has posted its review, the
  `apply-review` sub-skill reads that review back locally and walks
  the developer through the findings. After they apply fixes and
  push, come back here in **edit mode** if the PR scope changed
  enough to warrant a body refresh.
- **[`../setup/SKILL.md`](../setup/SKILL.md) (sibling — install the CI
  action)** — different phase of the lifecycle. Runs once per repo when
  the reviewer is being introduced; this sub-skill runs once per PR.
  If the developer asks to open a PR on a repo that has no
  `.github/workflows/pr-review.yml`, this skill still authors the PR
  correctly — CI review is set up separately.
- **[`../generate-extension/SKILL.md`](../generate-extension/SKILL.md)
  (sibling — tailor the reviewer prompt)** — orthogonal. Extensions
  affect what the reviewer flags; this skill only reads the diff.

---

## Non-blocking rule

Authoring a PR title + body must **never block the developer's primary
work**. If `gh` is missing, unauthenticated, network is down, or the
API call errors:

1. Print the drafted title + body to the terminal in a copy-pasteable
   block. The developer can paste it into the GitHub UI themselves.
2. Print the exact remediation (`gh auth login`, `git push -u origin`,
   etc.) once.
3. Do **not** retry automatically.
4. Do **not** enter a diagnostic loop.
5. End the turn.

This matches the parent skill's non-blocking discipline.

---

## Sample dialogues

### Dialogue A — Create a fresh PR after a local review

```text
Developer: [after the parent skill just produced a review with 2 info
            findings and no blockers]
           "great, open the PR"

Skill:
  1. Detect:  branch=feat/notif-prefs, base=main, no PR yet, tree clean.
  2. Diff:    9 files, +412/-87, mostly under app/notifications/.
              Commits reference: Closes #341, Refs #201.
              Signals: UI (2 .tsx files), migration (1 file), deps (none).
              Convention: Conventional Commits (17/20 recent PRs match).
  3. Template: .github/pull_request_template.md present → merge.
              Preserved `## Checklist` intact; skill sections override
              the template's `## Summary` and `## Test plan`.
  4. Title:   feat(notifications): per-team notification preferences
  5. Body draft:
       ## Summary
       Ship per-team notification preferences so admins can mute Slack
       pings without losing email digests. Closes the #2 complaint from
       enterprise onboarding.

       ## Changes
       - Add `NotificationPrefs` model + REST endpoints
       - Wire the toggle UI into the team-settings page
       - Migrate legacy `notification_settings` rows to per-team scope

       ## Related issues
       Closes #341
       Refs #201

       ## Test plan
       **Happy path**
       - Mute Slack pings for one team; confirm email digest still arrives
       - Toggle off all channels; confirm no notifications for 24h

       **Edge cases**
       - Team with 0 members: toggle is disabled with a tooltip
       - Migration rollback on a team mid-toggle: no data loss

       **Regression**
       - Existing per-user preferences unaffected on PR #212's fixture

       ## Screenshots
       [prompted: does this UI change have before/after screenshots?
        developer: "not yet — I'll drop them in after opening"]
       (section omitted — will be added post-open)

       ## Risks
       Migration rewrites `notification_settings` (~2M rows).
       Low risk — backfill batches behind `notif_prefs_v2` flag;
       rollback is a single flag flip with zero data loss.

       ## Migrations
       - `0042_add_notification_prefs` — 3 NULLABLE columns, online, reversible
       - `0043_backfill_notification_prefs` — batched, idempotent

       (dependencies section omitted — none)
       (breaking changes section omitted — none)

       ## Checklist  [from repo template — preserved intact]
       - [ ] Migrations are reversible
       - [ ] Feature is behind a flag
       - [ ] Runbook is updated
  6. Preview → developer says "yes".
  7. gh pr create --title "..." --body-file <tmp> --base main
     --assignee @me
  8. ✓ Created PR #384 — feat(notifications): per-team notification preferences
     https://github.com/acme/backend/pull/384

     Next steps:
       - Review it in the browser: gh pr view 384 --web
       - Watch CI as it runs:      gh pr checks 384 --watch
```

### Dialogue B — Refresh a one-liner PR body

```text
Developer: "the PR description just says 'fix bug'. Rewrite it in the
           proper format."

Skill:
  1. Detect:  branch=fix/oauth-callback, PR #214 exists, state OPEN.
              Current title: "fix bug"; current body: "fix bug".
  2. Diff:    1 file, +6/-3 in src/auth/oauth.ts.
              Signals: no UI, no migration, no deps.
              Commit trail: "fix(auth): handle OAuth callback with slash
              in state param" — bug-fix language + Conventional Commits.
  3. Title:   fix(auth): reject OAuth callback when state param contains slash
  4. Body draft:
       ## Summary
       Fix OAuth callback failing when the `state` query param contains
       a slash. Users on Microsoft and GitHub Enterprise were being
       redirected to /404 instead of completing sign-in.

       ## Changes
       - Percent-decode `state` before splitting on `/` in the callback handler
       - Add 4 regression tests covering Microsoft, GitHub Enterprise,
         Google, and Slack callback URLs

       ## Test plan
       **Happy path**
       - Sign in via Microsoft; confirm dashboard loads
       - Sign in via GitHub Enterprise; confirm dashboard loads

       **Regression**
       - Confirm Google + Slack sign-in flows unchanged

       ## Risks
       Decoder change touches every OAuth login. Low risk — covered by
       4 new test cases; rollback is a one-line revert with no flag.
  5. Preview (with body diff, current → proposed).
  6. Developer says "yes".
  7. gh pr edit 214 --title "fix(auth): reject OAuth callback when
     state param contains slash" --body-file <tmp>
  8. ✓ Updated PR #214 — https://github.com/acme/backend/pull/214
```

### Dialogue C — Docs-only PR, most sections omitted

```text
Developer: "open a draft PR for this docs change"

Skill:
  1. Detect:  branch=docs/i18n-onboarding, base=main, no PR, tree clean.
              Draft mode: yes (developer said "draft PR").
  2. Diff:    4 .md files under docs/, no code.
              Signals: no UI, no migration, no deps, no breaking.
              Commits: "docs(i18n): onboarding checklist for new locales"
  3. Template: none present.
  4. Title:   docs(i18n): onboarding checklist for new locales
  5. Body draft:
       ## Summary
       Add a step-by-step onboarding checklist for teams adding a new
       locale. Consolidates guidance previously scattered across
       #278, #305, and Slack threads.

       ## Changes
       - Create `docs/i18n/onboarding-checklist.md` (~120 lines)
       - Cross-link from `docs/README.md`
       - Update `docs/i18n/README.md` navigation

       ## Test plan
       - Run `docs-site build`; confirm the new page renders without warnings
       - Follow the checklist end-to-end for a fake locale (`xx-YY`)

       ## Risks
       None — content-only change to `docs/`. Rollback: revert the PR.

       (all other sections omitted — none apply)
  6. Preview → yes.
  7. gh pr create --title "..." --body-file <tmp> --base main
     --draft --assignee @me
  8. ✓ Created draft PR #392 — docs(i18n): onboarding checklist for new locales
     https://github.com/acme/backend/pull/392
     (draft — flip to ready when you're happy: gh pr ready 392)
```

### Dialogue D — Breaking-change PR

```text
Developer: "open the PR — heads up, this renames an action input"

Skill:
  1. Detect:  branch=feat/rename-api-key-input, base=main, no PR.
  2. Diff:    action.yml (1 input renamed), scripts/reviewer.py
              (env-var read updated), README.md (input table updated).
              Signals: breaking change (removed public input surface),
              no UI, no migration, no deps.
              Commit: "feat!: rename api-key input to provider-api-key"
  3. Title:   feat!: rename api-key input to provider-api-key
              (marker `!` preserved from the commit)
  4. Body draft — includes MANDATORY Breaking changes section:
       ## Summary
       Rename `api-key` → `provider-api-key` in `action.yml` for clarity
       now that the reviewer supports multiple providers. The old name
       was ambiguous about which provider's key it referred to.

       ## Changes
       - Rename input in `action.yml`
       - Update env-var read in `scripts/reviewer.py`
       - Update the input table in `README.md`
       - Update every example workflow in `examples/`

       ## Breaking changes
       - **What breaks:** the `api-key` input is removed. Workflows
         pinning `DailybotHQ/ai-diff-reviewer@v2` will fail at boot with
         "invalid input `api-key`".
       - **Who is affected:** every consumer of `@v2.x` who upgrades —
         the change is major-bump-worthy (ships as the next major).
         Consumers who stay on their current major pin are unaffected
         until they upgrade.
       - **Migration:** rename the key in your workflow YAML:
         `api-key: ${{ secrets.X }}` → `provider-api-key: ${{ secrets.X }}`.
         No other changes required.

       ## Test plan
       ...

       ## Risks
       Any consumer on `@v2` who updates without reading the release
       notes will see a workflow failure on their next PR. Mitigation:
       the release notes lead with this breaking change, and the error
       message includes the migration hint.
  5. Preview → the skill highlights the mandatory Breaking changes
     section in the "Sections included" summary.
  6. yes → gh pr create ...
```

---

## Notes

- **This is a title + body skill, not a git skill.** It writes what
  goes on the PR page. Commits, pushes, and merges are the developer's
  (or the merge-queue's) responsibility.
- **The body is the source of truth reviewers see first.** Time invested
  here pays back on every reviewer, every CI comment thread, and every
  release note derived from PR history.
- **The skill's opinion is intentional and small.** Three mandatory
  sections (Summary, Test plan, Risks); everything else is conditional
  on the diff. If your team wants more (rollout plans, security review
  checkboxes), put those in your `pull_request_template.md` and the
  skill preserves them.
- **Bugs, feature requests, and template patterns to add to the default:**
  [`github.com/DailybotHQ/ai-diff-reviewer/issues`](https://github.com/DailybotHQ/ai-diff-reviewer/issues).
