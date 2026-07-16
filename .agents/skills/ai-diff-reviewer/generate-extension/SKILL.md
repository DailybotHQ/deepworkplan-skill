---
name: ai-diff-reviewer-generate-extension
description: Generates a repo-tailored review-configuration file (`.review/extension.md` by default, or a full replacement `prompt-file` in advanced mode) by inspecting THIS codebase — stack, architecture, security surface, existing conventions, historical pain points — and producing concrete, code-anchored severity overrides. Uses the harness's Read/Grep/Glob tools to gather evidence before writing (12+ tool calls minimum). Default output extends the bundled AI Diff Reviewer prompt with project-specific rules; advanced mode replaces it entirely. Use when the developer says "customize the review for this repo", "generate review rules", "help me write my .review/extension.md", or when the local `ai-diff-reviewer` skill activates on a repo that has no extension file yet.
version: "2.0.0"
documentation_url: https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/skills/ai-diff-reviewer/generate-extension/SKILL.md
user-invocable: true
metadata: {"openclaw":{"emoji":"🎯","homepage":"https://github.com/DailybotHQ/ai-diff-reviewer","requires":{"anyBins":["git"]}}}
allowed-tools: Bash, Read, Grep, Glob
---

# AI Diff Reviewer — Generate Extension (sub-skill)

Companion to the [`ai-diff-reviewer`](../SKILL.md) skill. Where
`ai-diff-reviewer` **runs** the review, this sub-skill **bootstraps the
configuration** — turning "here's the default reviewer" into "here's a
reviewer that understands OUR stack, OUR conventions, and OUR history of
bugs."

**Two output modes:**

| Mode | File written | When |
|---|---|---|
| **Extension** (default) | `.review/extension.md` | Almost always — the recommended path. Layers repo-specific overrides ON TOP of the battle-tested default prompt. Cheap iteration; the default keeps improving upstream. |
| **Full replacement** (advanced) | `.github/prompts/pr-review.md` | Rare — teams that want total control, or whose codebase is so idiosyncratic (proprietary DSL, unusual paradigm) that the default is more noise than signal. Requires ongoing maintenance; you lose upstream improvements to the default. |

---

## Activation

- "Generate a `.review/extension.md` for this repo"
- "Customize the code review for our project"
- "Help me write repo-specific review rules"
- "Set up the AI reviewer for this codebase"
- "Tailor the reviewer to our stack"
- "Bootstrap the extension file"

The parent [`ai-diff-reviewer`](../SKILL.md) skill also routes to this
sub-skill in two situations:

1. **Explicit intent** — the developer asks for setup/customization
   instead of running a review (any of the triggers above).
2. **Automatic bootstrap** — the developer runs the review on a repo
   with no `.review/extension.md` and no `.review/.skip-bootstrap`
   marker, and answers **yes** at the Step 2.5 prompt in the parent
   skill. In this case, when this sub-skill finishes writing the file,
   control returns to the parent skill's Step 2 which layers the fresh
   extension onto the base prompt and continues the review.

Both entry paths run the same Discovery + Write flow below. **Do not
skip Discovery** just because the invocation came from the bootstrap
offer — the whole value of the extension is the file-anchored
Discovery evidence, not the file itself.

---

## Step 0 — Confirm mode with the developer

If the developer hasn't specified, ask ONE clarifying question:

> **Two modes available:**
> - **Extension** (recommended) — I'll write `.review/extension.md` with
>   overrides that LAYER on top of the shipped default prompt. Small
>   file (~50-150 lines), easy to iterate, benefits from upstream
>   improvements.
> - **Full replacement** (advanced) — I'll write
>   `.github/prompts/pr-review.md` — a complete standalone prompt that
>   REPLACES the default. Large file (~200-500 lines), full control,
>   requires maintenance.
>
> Which one? (Default: **extension**.)

Record the choice. If the developer just says "go ahead" or answers
ambiguously, default to **extension**.

---

## Step 1 — Discovery (mandatory, ≥ 12 tool calls)

Before writing anything, spend real tool calls learning the repo.
Skimping here produces a generic file that could belong to any repo —
which is the failure mode. Cover ALL five areas:

### 1a. Technology stack

Read whichever of these apply to this repo:

- `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `.nvmrc`
- `pyproject.toml`, `requirements*.txt`, `poetry.lock`, `Pipfile`
- `go.mod`, `go.sum`
- `Cargo.toml`, `Cargo.lock`
- `Gemfile`, `Gemfile.lock`
- `pom.xml`, `build.gradle`, `build.sbt`
- `composer.json`, `mix.exs`, `deno.json`

Identify: primary language + version, web framework, ORM/DB, testing
tool, linter/formatter/type-checker, auth library, runtime target.

### 1b. Architecture & implementation

Read `README.md`, `docs/ARCHITECTURE.md`, `AGENTS.md`,
`CONTRIBUTING.md`, then walk 2 levels of the source tree with `glob`
and `grep`. Identify:

- Shape: monolith / monorepo / microservices / library / CLI / hybrid.
- Layering: MVC? hexagonal? domain-driven? layered? flat?
- HTTP entry point (routes / handlers / controllers) — WHERE.
- Domain-logic location.
- Shared utilities location.
- DI / IoC framework (if any).
- Migration story (Alembic / knex / ActiveRecord / Prisma / etc.).
- Async model (promises / async-await / coroutines / actors / queues).

### 1c. Security surface

Grep for these patterns and note WHERE they live:

- Auth / session / JWT / OAuth / cookies.
- Input parsing (form / query / body / GraphQL / gRPC endpoints).
- File uploads + downloads.
- Outbound HTTP / webhook code.
- `subprocess`, `os.system`, `child_process`, shell exec, `eval`, `exec`.
- SQL query construction — parameterized vs string-concatenated.
- Secret handling (env vars, secret managers, config files).
- CSRF / CORS / rate-limit / CSP config.
- Cryptography (hashing algorithm, signing, encryption, PRNG).
- Serialization (`pickle`, `yaml.load` without `SafeLoader`, `unserialize`).

For each pattern found, remember the file path — you'll reference it
by name in the output.

### 1d. Existing quality standards

Look for:

- `.pre-commit-config.yaml`, `.husky/`, `lefthook.yml`
- `.github/workflows/*.yml` (existing CI checks)
- `CODEOWNERS`, `RULES.md`, `STYLE_GUIDE.md`
- `docs/STANDARDS.md`, `docs/DEVELOPMENT_GUIDELINES.md`
- `.editorconfig`, linter config files

Identify: lint/format rules, test-coverage floor, commit convention
(Conventional Commits / gitmoji), prohibited patterns already codified
(e.g. "no `console.log` on `main`", "no `print` in production code").

### 1e. Historical pain points

Skim `CHANGELOG.md` and — if you have `gh` CLI access —
`gh issue list --state closed --limit 30` and
`gh pr list --state merged --limit 20 --label bug`. Anything that hit
production twice is a candidate for **always `critical`**.

---

## Step 2 — Compose the output

### Extension mode (`.review/extension.md`)

Target: ~50-150 lines. Structure:

```markdown
# Review overrides for <repo-name>

<Optional one-paragraph context: what this repo does, why it's tricky,
what "good review" looks like here.>

## Severity overrides for this codebase

- **Always `critical`:** <concrete, code-anchored pattern>. Example:
  `SELECT * FROM users` in a request path → PII exposure (RFC-014).
- **Always `critical`:** <another>. Cite the file(s) where this class
  of code lives.
- **Escalate to `warning`:** <a pattern default treats as `info` but
  matters more here>. Cite files.
- **De-escalate to `info`:** <a pattern default treats as `warning` we
  chose to accept — reference the ADR / RFC that decided it>.

## Don't comment on

- Formatting in `apps/legacy/*` — scheduled rewrite per RFC-018.
- Missing tests in `experiments/` — intentionally exploratory.
- <Other project-specific noise sources>.

## Repo-specific conventions

- **Money handling:** use `Decimal` (Python) / `bignumber.js` / etc.,
  NEVER `float`. Files: `src/billing/*`.
- **Auth headers:** always through `middleware/auth.ts`, never
  hand-rolled. Any handler that reads `req.headers.authorization`
  directly is `warning`.
- **DB migrations:** must be reversible; irreversible migrations need
  an explicit `# noqa: irreversible` comment + RFC link.
- <Add 3-8 more, all tied to specific files or modules>.

## Test-strategy expectations

- New handlers in `src/api/*` require a matching integration test
  under `tests/api/*`.
- New database migrations require a rollback test.
- <Other test conventions>.
```

### Full-replacement mode (`.github/prompts/pr-review.md`)

Target: 200-500 lines. Follow the 7-section structure from the source
meta-prompt (kept upstream in
[`examples/prompts/generate-custom-prompt-meta.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/examples/prompts/generate-custom-prompt-meta.md)
for reference):

1. Role & mission (name the stack).
2. Tool schema summary (describe `read_file` / `grep` / `glob` /
   `post_inline_comment` / `submit_review` — don't redefine, don't
   embed JSON schema).
3. How to think about each finding (read → hypothesize → verify →
   assign severity → comment with WHY).
4. Severity definitions (`critical` / `warning` / `info`, each with
   ≥ 2 concrete, code-anchored examples from THIS repo).
5. Project-specific overrides (the section that earns its keep — ≥ 5
   overrides).
6. Style & tone (polite, specific, factual, no sycophancy).
7. Comment format (2–5 sentences, WHY first, cite line, suggest fix).

See [`examples.md`](examples.md) for condensed samples pulled from the
`examples/prompts/` full-replacement worked examples
(`python-strict.md`, `security-focused.md`, `typescript-strict.md`).

---

## Step 3 — Generation rules (both modes)

1. **English only** even if the codebase is in another language — the
   LLM operates in English.
2. **Concrete over abstract.** Every override must reference a real
   file, module, or pattern you SAW during Discovery. "Anywhere handling
   money uses `Decimal`" is good; "financial precision matters" is bad.
3. **No secrets in the output.** Never echo an env var, token, or
   credential value. Reference their NAMES if needed (e.g.
   "`STRIPE_SECRET_KEY` is loaded via `config/secrets.py`") but never
   the values.
4. **No content that could apply to any other repo.** If a section
   would survive copy-paste to a different codebase unchanged, delete
   or rewrite it.
5. **No YAML frontmatter, no HTML comments in the output** — the LLM
   reads raw markdown. Start with `# ` (h1) and go from there.
6. **Do not embed the tool schema JSON.** Describe the tools; the
   runtime injects the actual schema.

---

## Step 4 — Quality gate (self-check before writing the file)

Verify:

- [ ] Extension mode: ≥ 5 severity overrides, ≥ 3 "don't comment on",
      ≥ 3 repo-specific conventions.
- [ ] Full-replacement mode: all 7 sections present; each severity
      level has ≥ 2 code-anchored examples.
- [ ] The output names the repo's language, framework, and 1–2
      distinctive libraries by name.
- [ ] No content that would survive unchanged in a different repo.
- [ ] No secrets, tokens, or credentials in the text.
- [ ] English only, well-structured markdown, one h1 at the top.

If any check fails, go back to Discovery — don't ship a mediocre
extension.

---

## Step 5 — Write the file

Confirm the target path with the developer, then write it:

**Extension mode:**
```bash
mkdir -p .review
# Write the composed content to .review/extension.md via the harness's file-write tool.
```

**Full-replacement mode:**
```bash
mkdir -p .github/prompts
# Write to .github/prompts/pr-review.md via the harness's file-write tool.
```

If a file already exists at the target path, ASK before overwriting.
Offer to append to an existing extension file instead (adding new
overrides at the bottom, preserving what's there).

---

## Step 6 — Explain the next steps

After writing, tell the developer:

**For extension mode:**

1. Review the diff: `git diff .review/extension.md`
2. Optional — reference the same file from CI so local and CI stay in
   sync:
   ```yaml
   # .github/workflows/pr-review.yml
   - uses: DailybotHQ/ai-diff-reviewer@v2
     with:
       api-key: ${{ secrets.ANTHROPIC_API_KEY }}
       github-token: ${{ secrets.GITHUB_TOKEN }}
       prompt-extension-file: .review/extension.md
   ```
3. Test the extension locally by running the `ai-diff-reviewer` skill
   ("review my current branch") on a PR-shaped diff. If a rule fires
   too aggressively or misses a case, come back and refine.
4. Commit with a message like:
   `chore(review): add repo-tailored .review/extension.md`

**For full-replacement mode:**

1. Review the diff: `git diff .github/prompts/pr-review.md`
2. Reference the file in your workflow with `prompt-file:` (NOT
   `prompt-extension-file:` — this is the full replacement):
   ```yaml
   - uses: DailybotHQ/ai-diff-reviewer@v2
     with:
       api-key: ${{ secrets.ANTHROPIC_API_KEY }}
       github-token: ${{ secrets.GITHUB_TOKEN }}
       prompt-file: .github/prompts/pr-review.md
   ```
3. **Also update the local skill's prompt** to match: copy the same
   file into `.review/extension.md` OR configure the local skill to
   read from `.github/prompts/pr-review.md` — otherwise local and CI
   will drift.
4. Expect 2-3 iterations of feedback before the prompt feels dialed in.

---

## Notes

- **Discovery is the bulk of the value.** Two skills producing the
  same extension for the same repo aren't fungible if one skimped on
  Discovery — the concrete file-anchored overrides are what turns a
  generic reviewer into a senior teammate.
- **Extension is a living document.** After the first review batch,
  come back and add "Don't comment on" entries for false positives,
  and add "Always `critical`" entries for anything the reviewer
  missed. A `tune` sub-skill for this iterative refinement is on the
  roadmap.
- **The 3 stack-flavored worked examples** in
  [`examples/prompts/`](https://github.com/DailybotHQ/ai-diff-reviewer/tree/main/examples/prompts)
  (`python-strict.md`, `security-focused.md`, `typescript-strict.md`)
  are copy-paste-ready full-replacement prompts. Reference them in
  Discovery as a smell-check: "would this override look at home in
  those examples?"
