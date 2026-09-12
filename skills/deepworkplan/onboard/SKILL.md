---
name: deepworkplan-onboard
description: Make any repository AI-first — reason (never template) an adapted AGENTS.md, docs/, per-module docs and .agents/ kit from the real repo, discover and verify its full and scoped validation commands and source-to-test mapping, install the DeepWorkPlan skill, and, for a repository onboarded under an earlier version, perform a targeted, non-destructive, idempotent harness upgrade. Use when the developer wants to onboard or upgrade a repository for AI agents.
version: "4.0.3"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
---

# DeepWorkPlan — Onboard

Turn the **target repository** into an **AI-first autopilot repo**: a codebase
whose `AGENTS.md`, `docs/`, per-module docs, `.agents/`, `.claude → .agents` and
`.cursor → .agents` symlinks, and gitignored `.dwp/` give *any* AI agent (Claude Code, Cursor, OpenAI
Codex, Gemini, Copilot, Cline, Windsurf, OpenClaw) enough structured context to
work reliably without per-session human hand-holding.

> ## The one rule that overrides everything: REASON, do not copy-paste
>
> This flow is **not** a template copier and **not** a scaffolder. Its entire
> value is that you **inspect the actual target repo** — its real languages,
> frameworks, package manager, build/test/lint commands, folder layout, test
> convention, deployment shape — and then **generate artifacts adapted to that
> repo**. The *shape* of the output is fixed (the ~90%: `AGENTS.md`, the `docs/`
> categories, per-module docs, `.agents/`, the symlinks, `.dwp/`); the *content*
> is reasoned per repo (the ~10%: validation commands, paths, stack-specific
> skills, example plans).
>
> **An empty doc, a generic stub, a placeholder command, or a doc copied
> verbatim from this skill or another repo is a FAILURE.** Never write
> `<your test command here>`. Never write `npm test` unless you confirmed the
> repo uses npm and has a `test` script. Find the *real* command and write it.
> If you cannot determine a real value, ask the developer — do not guess and do
> not leave a placeholder.

## Shared resources — READ THESE FIRST

- [`../shared/context.sh`](../shared/context.sh) — resolve the target repo root,
  branch, agent tool, and the `.dwp/` output location (`dwp_dir`). Run it; do
  not reinvent detection.
- [`../shared/adaptation.md`](../shared/adaptation.md) — the
  reasoning-over-copy-paste principle and the two archetypes. This sub-skill is
  its deep elaboration.
- [`../shared/dwp-paths.md`](../shared/dwp-paths.md) — the `.dwp/` output
  convention you scaffold in Phase 7.
- [`presets/README.md`](presets/README.md) — the per-stack **reasoning guides**
  spanning backend/API (Django, FastAPI, Rails, Spring Boot, Laravel, NestJS),
  frontend (Vue/Vite, Next.js, SvelteKit, Nuxt, Angular, Astro/Svelte), mobile
  (React Native, Flutter, Swift/iOS), and systems/infra (Go, Rust, Terraform,
  TypeScript Lambda, Node/TS service, Python package/CLI), plus a `generic`
  fallback and the orchestrator-hub note. See `presets/README.md` for the full
  index. Read the matching preset in Phase 1 and use it in Phases 3–6.
  **Presets are reasoning aids, not templates.**
- **Guide (essential — read for this flow):** [`../guide/structure.md`](../guide/structure.md) (the `.dwp/` layout and naming you scaffold).
- **Guide (conditional — read only when the trigger fires):** [`../guide/large-repo-onboarding.md`](../guide/large-repo-onboarding.md) §15 when the repo is large enough for the plan-driven path (Phase 2b); [`../guide/orchestrator.md`](../guide/orchestrator.md) §13 for an orchestrator hub (child-DWP capability); [`../guide/authoring.md`](../guide/authoring.md) §4–§5 when emitting an onboarding plan's task files. Do not read other guide files for this flow; [`../guide/GUIDE.md`](../guide/GUIDE.md) is the routing index, consulted only when a section is not named above.
- **Spec (conditional — read the named sections when the trigger fires):** [`../spec/DOCUMENTATION_STANDARD.md`](../spec/DOCUMENTATION_STANDARD.md) §3.4 (the required content of `TESTING_GUIDE.md`) when writing or reconciling the testing guide, and §3.5 (install / onboard / upgrade, provenance, legacy-vs-declared) when the repository was onboarded before. The Phase 4 and Phase 0 text below is self-sufficient for the common case.
- [`addons.md`](addons.md) (this directory) — **read in Phase 7a and Phase 7b**: Phase 7a installs the required AI Diff Reviewer local review; Phase 7b offers the four optional addons (dependency upgrade is near-default for repos with declared dependencies; the rest are signal-gated opt-ins). No optional addon is required for a repository to use DWP.
- [`templates/onboarding-plan.md`](templates/onboarding-plan.md) — the
  **reasoning aid** for the plan-driven path (Phase 2b): the shape of a "finish
  onboarding myself" Deep Work Plan a **large** repo emits instead of generating
  everything inline. A template to reason from, **never** to copy verbatim.

> **Ship purity:** every path this flow references is relative inside
> `skills/deepworkplan/` (`../shared/*`, `presets/*`, `../guide/*.md`,
> `../addons/*`). Never reference any absolute host path or any
> `.agent_commands/...` path. The output you write lives in the **target repo**,
> at paths relative to its root.

---

## The generated outcome (what success looks like in the target repo)

When this flow finishes, the target repo contains:

1. **`AGENTS.md`** — index + mandatory rules + a Quick Commands block with the
   repo's **real, runnable** commands; plus `CLAUDE.md → AGENTS.md`.
2. **`docs/`** — the standard categories, each filled with **real**
   repo-specific content (real commands, real module names, real test pattern):
   `PRODUCT_SPEC.md` (the non-technical product/why doc — **required for every
   repo, libraries included**), `ARCHITECTURE.md`, `STANDARDS.md`,
   `TESTING_GUIDE.md`, `DEVELOPMENT_COMMANDS.md`, `SECURITY.md`, `PERFORMANCE.md`,
   `AI_AGENT_ONBOARDING.md`, `AI_AGENT_COLLAB.md`, optional
   `PR_REVIEW_WORKFLOW.md` / `ECOSYSTEM_CONTEXT.md`, and a `docs/README.md`
   index.
3. **Per-module nested docs** — a `README.md` (and a `docs/` subfolder for
   complex modules) inside each major source module discovered in recon.
4. **`.agents/`** — reasoned `agents/`, `commands/`, `skills/`, `docs/`
   (`skills_agents_catalog.md` + `COMMANDS_REFERENCE.md`), `settings.json`, and
   the `.claude → .agents` and `.cursor → .agents` symlinks. Skills/agents/commands are
   **stack-appropriate**, not generic boilerplate.
5. **DeepWorkPlan skill installed** + a gitignored **`.dwp/`** scaffold
   (`.dwp/plans/`, with a README and a `.gitignore` rule).
6. **A verified testing map** in `docs/TESTING_GUIDE.md` — the full and scoped
   validation commands (one scoped selection actually run where the toolchain
   is runnable), the source-to-test mapping, consumer policy, blind spots,
   escalation paths and fallback, plus the unit-first posture — so every future
   plan can select its gates instead of guessing (`../spec/DOCUMENTATION_STANDARD.md` §3.4).
7. **A recorded standard and a first usable outcome** — the provenance line
   `DWP standard: 4.0.0 (onboarded YYYY-MM-DD; skill x.y.z)` in `AGENTS.md`, and
   a `.dwp/onboard/REPORT.md` that names the verified command and mapping, the
   installed skill identity and version, the active capability limits (what
   could not be verified and why), and the next useful action.

Plus the required **AI Diff Reviewer local review** (Phase 7a: vendored skill +
`.review/extension.md`) and, from Phase 7b, the **optional addons** the
developer accepted or did not decline (the near-default dependency-upgrade
delegator installs under the onboarding consent unless explicitly declined;
the signal-gated opt-ins install only when accepted — the first is
devcontainer).

---

# The flow — Phases 0–8

Run the phases in order. Write your working notes to `.dwp/onboard/RECON.md` as
you go so generation is auditable and resumable. Treat every "detect" step as
**reason about the real repo**, never assume.

After recon and the archetype decision, **Phase 2b** picks the onboarding
*strategy*: generate everything **inline** in this session (small/medium repos —
the default), or, for a **large** repo, **emit a Deep Work Plan that completes
the onboarding task-by-task** with per-artifact gates and full resumability (the
recommended path at scale). The phase descriptions below are written for the
inline path; on the plan-driven path the **same work** runs as plan tasks.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`. Onboarding
mutates the target repository — non-destructively and by explicit design:

**Writes (Phase 0 consent covers the onboarding offer; per-file rules below):**

- `AGENTS.md` (+ the `CLAUDE.md` symlink), the reasoned `docs/` tree, per-module
  docs, and `.agents/` (skills/commands/agents/catalog) — **reconciled** with
  anything that already exists; replacing or deleting existing content requires
  asking the developer first.
- A `.dwp/` directory and a one-time **append** to `.gitignore` (never a
  rewrite).
- On the plan-driven path, plan artifacts under `.dwp/` as `create` defines.

**Writes include:** with Phase 0 consent, Phase 7a may run the tag-pinned
`npx --yes skills add DailybotHQ/ai-diff-reviewer@v2.0.1 --skill ai-diff-reviewer -y`
install into `.agents/skills/ai-diff-reviewer/` and bootstrap the repo-tailored
`.review/extension.md`; decline or offline failure is recorded as a declared
exception.

**It MUST NOT:** overwrite or delete existing files without explicit approval,
commit or push (commits happen only when the developer asks or a plan task's
gate defines them), touch files outside the repo, read or commit secrets, or
enable any optional addon without the developer's explicit acceptance of that
addon's offer (the required local reviewer of Phase 7a is covered by the
Phase 0 consent; a decline is recorded as a declared exception).

## Phase 0 — Preconditions & consent

1. **Resolve context.** Run `bash ../shared/context.sh` to get `repo_root`,
   `branch`, `agent_tool`, and `dwp_dir`. All target-repo paths below are
   relative to `repo_root`.
2. **Detect fresh-empty vs existing.** Decide which case you are in:
   - **Fresh-empty** — little/no source, no VCS history, no `AGENTS.md` /
     `CLAUDE.md` / `docs/` / `.agents/`. You generate from a clean slate (still
     reasoning from whatever signals exist — e.g. a single `package.json`).
   - **Existing** — real source code and/or any of the above already present.
     You must be **idempotent and non-destructive** (see below).
   - **Existing and previously onboarded → harness upgrade.** `AGENTS.md`
     and/or `.agents/` already exist **and** the repository's guidance predates
     the installed skill's requirements: no `DWP standard:` provenance line, a
     provenance line from a non-current series (older than the 4.x this skill implements, or a 2.x line while upgrading), or a
     `docs/TESTING_GUIDE.md` without the scoped-invocation / mapping / posture
     content of `../spec/DOCUMENTATION_STANDARD.md` §3.4. In this case run the
     **targeted upgrade** (§3.5) instead of a full re-onboarding: recon only what
     the upgrade needs (Phase 1's testing discovery), then reconcile **only** the
     missing or outdated pieces — the §3.4 sections of `TESTING_GUIDE.md`, the
     testing rule and labeled scoped variants in `AGENTS.md` (Phase 3), the
     scoped variants in `DEVELOPMENT_COMMANDS.md`, the `.agents/commands/dwp-*`
     delegators and `skill-create`/`agent-create` (Phase 6, refreshed from
     `command-templates/`), the required AI Diff Reviewer local review (Phase 7a —
     vendored skill + extension file, when missing), the catalog pointers, and
     the provenance line —
     leaving every handwritten section, custom skill, existing command and
     in-flight plan intact (in-flight plans keep their recorded shape; they are
     never migrated here — that is `refine migrate`, on explicit request). Report
     a **per-file summary** of what was added or changed, **and name what the
     upgrade deliberately did not create**: a repository that was never fully
     onboarded can still be missing baseline harness pieces (`.agents/agents/`,
     `.agents/docs/`, `CLAUDE.md`, `docs/SECURITY.md`) that a targeted upgrade
     is not entitled to invent. Say which ones remain and that a full onboarding
     is the way to close them — never imply the upgrade made the repository
     conformant when a conformance run would still report findings. Running the
     upgrade a second time **MUST** change nothing. `upgrade` / "upgrade the harness"
     forces this path; the flow selects it automatically when the signals above
     are present.
3. **Non-destructive rule (existing repos).** You **MUST NOT** clobber a
   hand-written `AGENTS.md`, `CLAUDE.md`, `docs/`, `.agents/`, or `.gitignore`.
   For each artifact that already exists: prefer to **merge/augment**; if a
   destructive change is unavoidable, **back it up** (e.g. `AGENTS.md.bak`) and
   **ask the developer first**. Re-running the flow on an
   already-onboarded repo MUST be safe — detect what already conforms and only
   fill gaps.
4. **Consent before writing.** This flow mutates the developer's repo. Present
   the **planned change set at a high level** (archetype guess, detected stack,
   the list of files/folders you intend to create or modify) and get explicit
   confirmation before writing anything.
5. **Honor dry-run / plan-only.** If the developer passes `--dry-run`, says
   "just show me the plan", or declines to write, produce the full plan (recon +
   intended change set) **without writing** any repo files. You MAY still write
   `.dwp/onboard/RECON.md` as the plan artifact, after telling them.

## Phase 1 — Repo reconnaissance (REASON, don't assume)

Inspect the real repo and record findings in `.dwp/onboard/RECON.md`. This is
the **highest-value** phase — everything downstream is reasoned from here.

Detect, by reading actual files (not by habit):

- **Languages & frameworks.** Manifests:
  `pyproject.toml` / `poetry.lock` / `requirements.txt` / `setup.cfg`,
  `package.json` / `pnpm-lock.yaml` / `yarn.lock` / `package-lock.json`,
  `go.mod`, `Cargo.toml`, `Gemfile`, `composer.json`, `pom.xml`, `*.csproj`.
  Framework signatures: `manage.py`+`settings.py` → Django; `vite.config.*` +
  `vue`/`react` in deps → Vue/React + Vite; `astro.config.*` → Astro;
  `next.config.*` → Next; Express/Fastify imports → Node service; Lambda
  handlers / `serverless.yml` / `template.yaml` → serverless; a `console_scripts`
  / `[project.scripts]` entry + Click/Typer/argparse → Python CLI.
- **Build / test / lint / typecheck commands — the crown jewels.** Read the
  manifest scripts (`package.json` `scripts`, `pyproject.toml` tool config),
  `Makefile`, `Taskfile.yml`, `tox.ini`, CI workflows (`.github/workflows/*`,
  `.gitlab-ci.yml`), and any `docker.sh` / `docker-compose.yml`. Capture the
  **exact** commands (e.g. `pnpm run eslint:check`, `pnpm run type:check`,
  `codecheck -f` *inside Docker*, `poetry run pytest`, `ruff check`,
  `npm run biome:check`, `astro check`). Note any command that runs **only in
  CI** or **only inside a container** — flag it as such (this matters for the
  Quick Commands block and the Phase 8 smoke test).
  **Testing discovery (the part every future gate depends on).** Establish, by
  reading configuration and running `--version` where cheap: the package
  manager(s) and workspace boundaries (monorepo packages, their own scripts);
  the installed test/lint/type-check tools and their **versions** where flag
  behavior depends on them; the **test layers** present (unit / integration /
  e2e — where each lives and how each is run); the **source-to-test
  relationship** (co-located, mirrored tree, naming convention, markers,
  package boundary); whether the runner supports **scoped invocation** by
  file, directory, package, marker or name filter; any **affected-tests
  tooling** (`--changed`, `--findRelatedTests`, `testmon`, a task graph) and
  its blind spots (dynamic loading, templates, fixtures, generated inputs,
  configuration); the **working directory** each command runs from; and which
  paths/packages are shared or core (a change there widens validation) and
  which configuration/schema/dependency/toolchain files always trigger the full
  run. Then **verify one genuine scoped selection where the toolchain is
  runnable**: run the scoped command against a real path of this repo and
  confirm it selects a **non-empty, relevant** set (record the selected /
  executed count and the exit status). A command that exits 0 having selected
  nothing is **not** verified — fix the selector or record the pattern as
  unverified. Where the toolchain cannot run here (Docker-only, CI-only, missing
  tool), record the pattern as **proposed / unverified** with the reason and a
  real fallback — never as verified. **If the repo has no test
  and/or no lint/type-check command at all, do not just record the absence** —
  flag it as a gap to be closed in Phase 4 by *proposing* a stack-appropriate
  toolchain (per `../spec/DOCUMENTATION_STANDARD.md` §3.3). Validation gates are
  the backbone of reliable Deep Work Plans; a repo with no way to validate its
  behavior is not yet AI-first.
- **Package manager.** Infer from the **lockfile that actually exists**
  (`pnpm-lock.yaml` → pnpm, `poetry.lock` → poetry, etc.), never from habit.
- **Folder layout & modules.** Find the source roots (`src/`, `app/`, `lib/`,
  `pkg/`, `cmd/`, `pages/`, `components/`) and the major sub-modules within them.
  These become the per-module docs in Phase 5.
- **Test convention.** File naming (`*_test.py`, `*.spec.ts`, `*.test.ts`),
  framework (pytest / jest / vitest / playwright / go test), and where tests
  live (co-located vs `tests/`). If **no tests exist**, note that — Phase 4 will
  *propose* a convention and framework reasoned from the stack rather than
  leaving testing undefined.
- **Deployment / runtime shape.** Containerized? Serverless? Static site?
  Long-running service? Library/package? This informs `ARCHITECTURE.md` and
  `PERFORMANCE.md`.
- **Existing conventions to carry forward.** Read any current `README`,
  `CONTRIBUTING`, `.editorconfig`, linter/formatter config, and the existing
  commit-message style (`git log`). **Carry these forward**; do not override a
  working convention with a generic one.

Then **load the matching preset** from `presets/` (one per common stack across
backend, frontend, mobile, and systems/infra — see `presets/README.md` for the
full index — or `generic` if nothing matches). Use it as a **reasoning
checklist**, and explicitly verify each preset
assumption against what you actually found — **detected reality wins over preset
assumptions**.

Write `.dwp/onboard/RECON.md` with: detected stack, package manager, exact
validation commands (flagged CI/Docker-only where relevant) with their working
directory, the **testing map** (layers, mapping rule, scoped patterns and the
verified-run evidence or the unverified/proposed marking, affected-test tooling
and blind spots, shared/core paths and full-run triggers, fallback), source
roots + major modules, test convention, deployment shape, carried-forward
conventions, and which preset you used.

**Also record a scale count** (the evidence the Phase 2b decision reads, so the
inline-vs-plan choice is mechanical, not guessed):

- `major_modules` — the number of major source modules you'll write per-module
  docs for (Phase 5).
- `planned_artifacts` — a rough total of files to generate: `AGENTS.md` (1) +
  the `docs/` categories (~10) + one per-module `README.md` + the `.agents/` kit.
  Estimate it: `≈ 11 + major_modules` for a typical repo.

Record both numbers explicitly in `.dwp/onboard/RECON.md`. Phase 2b thresholds
are stated against these counts.

## Phase 2 — Archetype decision

Classify the repo using `../spec/ARCHETYPES.md` signals (summarized in
`presets/README.md`):

| Signal | Indicates orchestrator hub |
|--------|---------------------------|
| A `repositories/` (or equivalent) folder of multiple independent repos | strong |
| No single primary application stack at root; root is mostly markdown/coordination | strong |
| Sub-repos git-ignored / tracked separately | moderate |
| Cross-project standards, a repo navigation index, or orchestrator manifests | moderate |
| Root `AGENTS.md` indexes *other repos'* `AGENTS.md` | moderate |

- **Default to `individual repo`** (the 99% case) unless a clear majority of
  signals say hub.
- A monorepo with **one** build/stack is an **individual repo with modules**
  (handled by per-module docs), **not** a hub.
- If signals are **ambiguous**, present your assessment + evidence and **ask the
  developer** before proceeding.

Record the decision and the evidence in `.dwp/onboard/RECON.md`. Every phase
below branches on this decision where noted.

## Phase 2b — Onboarding strategy: inline vs plan-driven (scale decision)

Onboarding a repo means analyzing the **whole** codebase and **documenting all
of it**: every `docs/` category, a per-module `README.md` for each major module,
and the full `.agents/` kit (agents, skills, commands, catalogs). For a small or
medium repo, generating all of that **inline** in this session (Phases 3–8) is
the right, fast default.

For a **large** repo, doing it all inline is the wrong tool: it strains a single
context window, gives no per-artifact validation gate, can't be audited
task-by-task, and loses all progress if the session is interrupted. That is
**exactly** the problem Deep Work Plans solve. So for a large repo, **onboarding
becomes its own Deep Work Plan** — the repo's first plan is "finish onboarding
myself," executed task-by-task with gates and full resumability. This is the
methodology dogfooding itself: the onboarding uses the very loop it installs.

**Decide the strategy from the recon counts (mechanical, not a guess).** Read the
`major_modules` and `planned_artifacts` numbers you recorded in Phase 1. Choose
**plan-driven** when a clear majority of these hold (or the developer asks):

- `major_modules` **> 8** (each needs its own per-module doc, Phase 5).
- `planned_artifacts` **≥ 15** (docs + per-module docs + `.agents/`).
- A monorepo / multi-package workspace, or an orchestrator hub.
- The work plainly won't fit one focused session, or must survive across
  sessions/agents.

Otherwise stay **inline** (the typical case) — run Phases 3–8 directly. State the
counts and the resulting choice in `.dwp/onboard/RECON.md` so the decision is
auditable; if the counts sit right at the boundary, present them and let the
developer break the tie.

**The plan-driven path:**

0. **Resume, don't regenerate (idempotency check).** Before building a new plan,
   look for an in-progress onboarding plan: `ls .dwp/plans/PLAN_onboard_*`. If one
   exists, **do not start over** — read its `PROGRESS.md`, report status, and hand
   off to `/dwp-resume` to continue from the first open task. Only generate a new
   plan when none exists. (This honors the Phase 0 idempotency rule for the
   plan-driven path and matches the `verify` sub-skill's in-progress note.)
1. Still complete **Phase 1 recon** and **Phase 2 archetype** here — the recon
   (`.dwp/onboard/RECON.md`) is the analysis the plan is built from. Never skip
   it.
2. Generate **`AGENTS.md` + `CLAUDE.md` (Phase 3) up front** (or as task 1) so
   the plan's tasks have the index and mandatory rules to anchor to.
3. Instead of generating the rest inline, **materialize a Deep Work Plan** under
   `.dwp/plans/` whose atomic tasks are reasoned from recon — see
   [`templates/onboarding-plan.md`](templates/onboarding-plan.md) for the shape
   (a **reasoning aid**, not a copy-paste). Typical decomposition:
   - one task **per `docs/` category** (Phase 4), each gated on "no placeholders
     + real commands + links resolve";
   - **one task per major module** for its `README.md` (Phase 5) — the part that
     scales worst inline;
   - one task for the **`.agents/` kit** (agents + skills + commands + catalogs,
     Phase 6), gated on "catalog matches disk";
   - one task to **install the skill + scaffold `.dwp/` and `tmp/`** (Phase 7);
   - the **Phase 8 self-check folded into the plan's single mandatory Final
     Review** (security pass, final-state validation, skills reconciliation —
     `../spec/DWP_SPECIFICATION.md` §6.1); skills decisions are task-local and
     the Executive Report is optional.

   Each task carries explicit **Acceptance Criteria** and a runnable
   **validation gate** (the repo's real lint / `md`-check / test).
4. Hand off to the normal loop: adjust the plan with `/dwp-refine` if needed,
   then `/dwp-execute` it task-by-task. It is resumable with `/dwp-resume` and
   inspectable with `/dwp-status`.

> The Phase 0 rules — non-destructive, idempotent, **no placeholders**, consent —
> apply **identically** on the plan-driven path. They move into each task's
> Acceptance Criteria and gate rather than disappearing. A plan-driven onboarding
> that ships a placeholder doc is the same failure as an inline one.

Record the chosen strategy (inline vs plan-driven) and its evidence in
`.dwp/onboard/RECON.md`.

## Phase 3 — Generate `AGENTS.md` + `CLAUDE.md` symlink

Reason the content from Phase 1; do not template it.

**`AGENTS.md` (plain UTF-8 markdown, NO frontmatter)** is a **compact entry
point** (`../spec/DOCUMENTATION_STANDARD.md` §2.4.1): the mandatory constraints
and quick commands inline, everything else one direct link away in the focused
`docs/` guide or module doc that owns it. Brevity comes from linking, never from
dropping an invariant an agent needs to act safely; no word cap hides required
context. It MUST serve three roles:

1. **Index** — a documentation index table linking every `docs/` file you will
   create (Phase 4), each with a one-line description; plus an annotated
   repo-structure tree (≥2 levels) reflecting the **real** layout from recon.
   Link only files that will exist.
2. **Mandatory rules** — English-only; conventional commits
   (`type(scope): description`) with the repo's **real** scopes derived from its
   domains; the repo's **real** test pattern + coverage expectation **and the
   validation rule** (gates are selected from a change's touched surface using
   `docs/TESTING_GUIDE.md`'s mapping, with the documented fallback to the full
   suite); its error/
   logging conventions; repository-boundary rules (where the agent may/may not
   commit); and a progress-reporting + "never block work on reporting" note.
3. **Quick Commands** — a table of the **detected** install / test / lint /
   type-check / build / validate commands, verbatim, with the **scoped variant
   next to the full one where the toolchain supports it**, each labeled
   (`full` / `scoped`). **Mark** any command that
   runs only in CI or only inside a container (e.g. "must run **inside** the
   Docker container"), and any scoped pattern that is proposed/unverified.
4. **Provenance** — one line, `DWP standard: 4.0.0 (onboarded YYYY-MM-DD;
   skill x.y.z)` (on upgrade: `…; upgraded YYYY-MM-DD; skill x.y.z`), so a
   checker and a future agent can tell which standard the repository declares
   (`../spec/DOCUMENTATION_STANDARD.md` §3.5).

**Orchestrator-hub additions** (only if Phase 2 said hub): add the sub-project
navigation index link (e.g. `repositories/README.md`) and each sub-project's
`AGENTS.md`; the **multi-project commit workflow** (commit inside each sub-repo,
never from the hub root); and **child-DWP** language per `../guide/orchestrator.md`
(orchestrator §).

**`CLAUDE.md`.** Create the symlink `ln -s AGENTS.md CLAUDE.md`. If the target
filesystem/host does not support symlinks, fall back to a one-line `CLAUDE.md`
containing exactly `@AGENTS.md`, and note the fallback in `.dwp/onboard/REPORT.md`.
Never duplicate `AGENTS.md` content into `CLAUDE.md`.

> **Existing-repo note:** if `AGENTS.md` already exists and is hand-written,
> merge your index/commands/rules into it rather than overwriting; back up +
> ask before any destructive change (Phase 0).

## Phase 4 — Generate `docs/`

Produce the standard categories, **each adapted** from recon — an empty or
generic doc is a failure. The conformance floor (all **MUST**):
`PRODUCT_SPEC.md`, `ARCHITECTURE.md`, `STANDARDS.md`, `TESTING_GUIDE.md`,
`DEVELOPMENT_COMMANDS.md`, `SECURITY.md`, `AI_AGENT_ONBOARDING.md`,
`AI_AGENT_COLLAB.md`. **SHOULD**: `PERFORMANCE.md`, plus optional
`PR_REVIEW_WORKFLOW.md` and `ECOSYSTEM_CONTEXT.md`. Always add a
`docs/README.md` master index.

Each doc must contain **real** content:

- `PRODUCT_SPEC.md` — the non-technical product/why doc: the problem the repo
  solves, who it is for, its key capabilities/features, success criteria, and
  explicit non-goals. It **MUST read plainly enough that anyone — a person or an
  agent, technical or not — can understand what this repository is and why it
  exists at a glance**; that is the whole point of the document. Reason it from
  the README, package description, public API, and any roadmap/issues — never a
  generic stub. **Required for every repo, including libraries, CLIs, and
  internal tools**: if there are no end users, frame the product as its
  consumers (who calls this API, and why they choose it). This is the *why*; the
  docs below are the *how*.
- `ARCHITECTURE.md` — the real components, data flow, and deployment shape from
  recon; an annotated diagram of the actual module layout.
- `STANDARDS.md` — the repo's real coding conventions, naming, import order,
  error/logging patterns, and forbidden anti-patterns (carry forward existing
  linter config).
- `TESTING_GUIDE.md` — the **real** test framework + file-naming pattern +
  coverage expectation, and the required content of
  `../spec/DOCUMENTATION_STANDARD.md` §3.4, all from Phase 1's testing map:
  **(commands)** the full-suite command(s) and the full lint/format/type-check
  commands; the **scoped invocation pattern(s)** (by file, directory, package,
  marker/name filter) each with **one concrete example from this repository**,
  its working directory, the tool version where flags depend on it, and the
  expected evidence of a correct run (the verified selected/executed count) —
  a pattern copied from tool docs without a repository example is not enough;
  scoped lint/format/type-check **only where genuinely supported** (say plainly
  when a project-wide check is the real option or the cheaper one); when the
  full suite is cheap, recommend it over elaborate selection. **(mapping)** the
  source-to-test mapping rule; the dependent-consumer policy (the affected-tests
  tool or documented consumer list, and what to do when none exists); the known
  blind spots (dynamic loading, templates, fixtures, generated inputs,
  configuration, migrations); the escalation paths (which paths/packages are
  shared or core; which config/schema/dependency/toolchain changes always trigger
  the full run); and an explicit **fallback statement** ("run `<full command>`")
  for whatever scoping cannot cover. **(posture)** where each test layer lives
  and how it runs; **unit-first behavioral coverage** as the base — fast,
  deterministic tests of observable behavior and meaningful boundaries, covering
  errors, edge cases and regressions, with mocks at useful boundaries and
  **no** assertions on internal call sequences; **real-seam integration** (which
  contracts, persistence, routing, serialization, auth or wiring seams carry
  integration/contract tests, and that a change to such a seam adds them);
  **useful end-to-end** coverage (few, high-value flows); deterministic
  fixtures and meaningful assertions. Teach this as a default cost/risk
  strategy — **no** ratio quotas, no test-count targets, no universal
  millisecond promise, no fake isolation, and no blanket rewrite of the existing
  suite. Keep **current capabilities** and any **proposed** setup in clearly
  separate sections so nobody mistakes a proposal for a verified command.
  **If the repo has no test/lint setup, do NOT write "no tests" or leave it
  empty** — *propose* a
  stack-appropriate setup (recommended framework + runner, test file convention,
  where tests live, a sensible initial coverage target, and the lint /
  type-check / format tooling — **including the scoped invocation pattern the
  proposed runner supports**, so the repo is efficient by construction), sized
  proportionately to the repo's conventions and maturity, document it as the
  **target** (marked proposed, never verified), and surface it to the
  developer. Do not install tools silently and do not invent a runnable gate;
  obey the repo's dependency policy and the Phase 0 consent. When non-destructive and the developer consents, scaffold a
  minimal runnable baseline (the test/lint scripts + at least one real smoke
  test). See `../spec/DOCUMENTATION_STANDARD.md` §3.3. This is essential, not
  cosmetic: it is what gives every future Deep Work Plan a real validation gate.
- `DEVELOPMENT_COMMANDS.md` — the authoritative, **verbatim** command reference
  (install/test/lint/type-check/build/run), expanding the AGENTS.md Quick
  Commands, with the **scoped variants** of test/lint/type-check listed next to
  the full ones and each labeled full or scoped (and proposed/unverified where
  applicable); flag CI/Docker-only commands.
- `SECURITY.md` — the real secrets-handling location/convention, auth model,
  sensitive-data boundaries, and what agents MUST NOT write into docs.
- `PERFORMANCE.md` — performance-critical paths/budgets relevant to the runtime
  shape (skip or keep brief for trivial repos).
- `AI_AGENT_ONBOARDING.md` — a concrete first-session checklist for *this* repo
  (clone → install with the real PM → run the real validation → where things
  live).
- `AI_AGENT_COLLAB.md` — handoff, ownership, and conflict-avoidance rules.
- (optional) `PR_REVIEW_WORKFLOW.md`, `ECOSYSTEM_CONTEXT.md` — add when the repo
  uses PRs / sits in a multi-repo ecosystem. `ECOSYSTEM_CONTEXT.md` is **MUST**
  for an orchestrator hub.
- `docs/README.md` — a one-paragraph scope statement + a table linking every
  guide you created. **MUST** exist for a hub.

The preset for the detected stack lists the **doc emphases** that matter for
that stack — apply them.

## Phase 5 — Generate per-module nested docs

For each **major** source module found in Phase 1 (a folder representing a
distinct feature/bounded concern), create a `README.md` inside that folder
describing: the module's responsibility, key files / public surface, and how
it's tested. For a **complex or high-velocity** module (3+ interconnected
concerns), add a `docs/` subfolder with deeper guides, entered via a `README.md`.
A trivial/stable module needs only its `README.md`. Link each module's docs from
its own `README.md`; surface the most significant ones in the root `AGENTS.md`
index. (Reference `../spec/DOCUMENTATION_STANDARD.md` §4 for the per-module rule; which
modules count as "major"/"complex" is reasoned per repo.)

## Phase 6 — Generate `.agents/` + agent directory symlinks

Create the canonical cross-agent config directory. **All content must be
cross-agent** (readable by Cursor/Codex/Gemini/Copilot as personas/procedures),
and **stack-appropriate**, not generic boilerplate.

- **`.agents/agents/`** — reasoned worker personas. Baseline roles: `reviewer`,
  `architect`, `executor`, `debugger`, `qa`, `perf-optimizer`,
  `security-auditor`, plus any **stack-specific** role the preset suggests
  (e.g. a Django `migration-author`, a Vue `component-author`). Each persona
  must be described well enough that a non-Claude agent can read it.
- **`.agents/commands/`** — the six short DWP commands (`dwp-create`,
  `dwp-execute`, `dwp-refine`, `dwp-resume`, `dwp-status`, `dwp-verify`) plus stack-relevant
  ones (`code-review`, `pr`, `commit`, `branch`). **The `dwp-*` commands MUST be
  thin delegators, NOT copies of the flow.** Each is a short file (frontmatter
  `description:` + a body) that routes the invocation to the matching sub-skill
  of the installed `deepworkplan` skill — e.g. `/dwp-create` → the skill's
  `create` sub-skill, `/dwp-resume` → `resume`, etc. Do NOT re-author the
  command flow content (the skill owns it; duplicating it causes drift). This
  gives users the familiar short `/dwp-create` / `/dwp-resume` aliases while the
  single source of truth stays in the skill. (The skill's own sub-skills are
  already `user-invocable`, so `/deepworkplan-create` etc. also work; the
  `dwp-*` files are the shorter, conventional aliases.) Copy and adapt the
  ready delegator templates at [`command-templates/`](command-templates/) —
  one per `dwp-*` command — fixing the `<skill-path>` to where the skill is
  installed in the target repo. The same directory also ships `skill-create.md`
  and `agent-create.md` — thin delegators that route `/skill-create` and
  `/agent-create` to the **author** sub-skill so the onboarded repo can evolve
  its own kit (create/update skills, agents, commands). Copy and adapt these two
  alongside the `dwp-*` templates, fixing the same `<skill-path>`.
- **`.agents/skills/`** — **stack-appropriate** skills chosen by reasoning (use
  the preset's "skills to generate" list as a starting point, then verify
  against the repo's real needs), plus the DeepWorkPlan skill installed here
  (Phase 7).
- **`.agents/docs/`** — `skills_agents_catalog.md` and `COMMANDS_REFERENCE.md`,
  generated to **match what you actually created** (no phantom entries).
- **`.agents/settings.json`** — a sane harness-config baseline (sensible
  permissions; no secrets). `.agents/README.md` — a short entry point.
- **`.claude → .agents` and `.cursor → .agents` symlinks** — `ln -s .agents .claude` and
  `ln -s .agents .cursor`. Same symlink fallback as Phase 3 if unsupported (a tool-native pointer; document it).

> **Existing-repo note:** if `.agents/` (or per-tool `.claude/` / `.cursor/`)
> config already exists, reconcile into `.agents/` and add the `.claude` and
> `.cursor` symlinks only if absent; never delete existing personas/commands without asking.
> On a **harness upgrade** (Phase 0), refresh the `dwp-*`, `skill-create` and
> `agent-create` delegators from `command-templates/` (they are thin and owned
> by the skill), leave every other command, agent and skill as-is, and update
> only the catalog entries that point at refreshed files.

## Phase 7 — Install the DeepWorkPlan skill + scaffold `.dwp/`

1. **Make the DeepWorkPlan skill available** to the target repo via one of (offer
   the developer the choice; recommend the first):
   - `npx --yes skills add DailybotHQ/deepworkplan-skill@<tag> --skill deepworkplan -y`
     — **pin the latest published tag** from the repo's Releases (check it;
     never write a tag you did not verify; both `--yes` and `-y` are required
     in non-TTY)
   - OpenClaw: `openclaw skills install deepworkplan` (registry-managed pin)
   - or symlink the local skill pack into `.agents/skills/deepworkplan/`.

   Do not offer unpinned clone-and-run variants or moving refs (`@main`,
   `@latest`) — executing whatever a remote ref currently holds is an
   unverifiable dependency (no version, no checksum, no rollback; the shape
   Snyk W012 flags).
2. **Scaffold the gitignored output area** (per `../shared/dwp-paths.md`):
   create `.dwp/plans/` with a `README.md` placeholder,
   and add `.dwp/` to the repo's `.gitignore` (append the rule
   non-destructively — do not rewrite the file). `.dwp/` is the only DWP output
   location; it **replaces** any pre-v2 DWP output tree (see
   `../shared/dwp-paths.md` for the contrast). If an older DWP output tree
   exists, note it for migration (do not delete without asking).
3. **Scaffold the `tmp/` scratch area** (per `DOCUMENTATION_STANDARD.md` §2.6):
   create a root-level `tmp/` with a `.gitkeep`, add `tmp/` to the repo's
   `.gitignore` (append non-destructively), and note the convention in
   `AGENTS.md` — a gitignored freeform scratch space for ephemeral/throwaway
   work (exploratory output, data exports, inter-agent prompt handoffs), kept
   distinct from the **structured** `.dwp/` plan output. If `tmp/` already
   exists, leave it as-is.

## Phase 7a — Install the AI Diff Reviewer local review (required)

The local review is part of the baseline since standard 2.3.0
(`../spec/ADDONS.md` §6.5). When the core flow is done (Phases 3–7), read
[`addons.md`](addons.md) (this directory) Phase 7a and run the
[`../addons/ai-diff-reviewer/SKILL.md`](../addons/ai-diff-reviewer/SKILL.md)
flow: pinned install of the vendored skill into `.agents/skills/ai-diff-reviewer/`,
extension bootstrap at `.review/extension.md` (upstream `generate-extension`),
Flow A as the baseline and Flow B offered as an explicit opt-in. Reconcile what
already exists. When the install cannot run here (sandbox, offline) or the
developer declines, record the gap in the report and, for a decline, as a
declared exception in `AGENTS.md` — never silently. A **harness upgrade**
(Phase 0) reconciles the same two pieces when missing.

## Phase 7b — Offer optional addons (trigger only)

The remaining addons are optional; **no optional addon is required for a
repository to use DWP**. After Phase 7a, read [`addons.md`](addons.md) (this
directory) Phase 7b and make the offer it describes: three addons are
signal-gated opt-ins that install only on explicit acceptance; the fourth —
dependency upgrade — is **near-default** for every repo with declared
dependencies: its **inert** `/lib-upgrade` delegator installs under the
Phase 0 onboarding consent **unless explicitly declined**, and no upgrade ever
runs from an install. On a **harness
upgrade** (Phase 0) do not re-offer addons the repository already declined or
already has; mention only new ones, briefly.

## Phase 8 — Self-check / validation (mandatory)

See the dedicated section below.

---

# Phase 8 — Self-check / validation (run in the TARGET repo)

After generating, run this checklist in the target repo. On any failure,
**fix-then-recheck** before reporting done. On the **plan-driven path**
(Phase 2b), this checklist **is the plan's mandatory final task** — run it after
the plan's other tasks complete, gating the whole onboarding before reporting
done.

1. **`AGENTS.md` exists** and contains a Quick Commands block whose commands are
   **real and runnable** (not placeholders). Spot-check that referenced commands
   exist in the manifest/Makefile/scripts.
2. **`CLAUDE.md` resolves to `AGENTS.md`** — the symlink points at `AGENTS.md`,
   or `CLAUDE.md` contains exactly `@AGENTS.md`.
3. **`docs/` has the standard categories**, each non-empty and repo-specific
   (the eight MUST files at minimum — `PRODUCT_SPEC` included — plus
   `docs/README.md`). Grep for leftover
   placeholder markers (`<...>`, "TODO", "your command here") and fix any.
   **`TESTING_GUIDE.md` MUST describe either a real test/lint setup or a concrete
   *proposed* one (§3.3)** — never empty, never "no tests" — **and MUST carry
   the §3.4 content**: full and scoped commands with a repository example and
   the verified-run evidence (or an honest proposed/unverified marking with a
   fallback), the mapping rule, consumer policy, blind spots, escalation paths,
   the fallback statement, and the unit-first posture with current and proposed
   kept apart. `AGENTS.md` carries the `DWP standard:` provenance line and
   labeled scoped variants in Quick Commands.
4. **Every major source module has a `README.md`** (and complex modules have a
   `docs/`).
5. **`.agents/`** has `agents/`, `commands/`, `skills/`, `docs/`, `settings.json`
   and `.claude → .agents` + `.cursor → .agents` symlinks (or documented fallback);
   `skills_agents_catalog.md` and `COMMANDS_REFERENCE.md` **match** what was
   actually created (no phantom entries). **The six `dwp-*` commands exist** in
   `.agents/commands/` (`dwp-create`, `dwp-execute`, `dwp-refine`, `dwp-resume`,
   `dwp-status`, `dwp-verify`) and are thin delegators (no leftover `<skill-path>`
   placeholder, no copied flow body).
6. **DeepWorkPlan skill is discoverable** and `.dwp/` exists, is gitignored
   (`git check-ignore .dwp` confirms), and has `plans/`. **`tmp/`
   exists and is gitignored** (`git check-ignore tmp` confirms). **The AI Diff
   Reviewer local review is installed**: `.agents/skills/ai-diff-reviewer/SKILL.md`
   exists and an extension file is present at a recognized path
   (`.review/extension.md` preferred) — or the report and `AGENTS.md` record
   the declared exception / the reason the install could not run here.
7. **Smoke test — run the repo's OWN detected validation command once** to
   confirm recon was accurate (e.g. the lint or test command). If it cannot run
   (e.g. Docker required and unavailable, network-gated CI command), **note why**
   in the report instead of silently skipping. If the repo had **no** validation
   toolchain and you proposed (and scaffolded) one, run the proposed test/lint
   command to confirm the baseline is real; if you only documented the proposal
   without scaffolding, note it as a recommended follow-up in the report.
8. **Archetype-specific:** if orchestrator hub, confirm the sub-repo navigation
   index + multi-project commit workflow are documented and `ECOSYSTEM_CONTEXT.md`
   exists.
9. **Objective conformance gate — run `/dwp-verify`.** This checklist mirrors the
   `verify` sub-skill; close the loop by actually running it (read
   [`../verify/SKILL.md`](../verify/SKILL.md) and execute its repository checks)
   for an independent **CONFORMANT / NOT CONFORMANT** verdict. This dogfoods
   `verify` and turns the manual checklist into a reproducible gate. Treat a
   `NOT CONFORMANT` verdict as a Phase 8 failure: **fix-then-recheck** before
   reporting done. (On the plan-driven path, `/dwp-verify` is exactly the final
   task's gate.)
10. **Write the onboarding report** to `.dwp/onboard/REPORT.md` summarizing: the
   archetype chosen + evidence, the detected stack + package manager, the exact
   validation commands captured, the full list of files/folders generated or
   modified (on an upgrade: the **per-file summary** of what was added or
   changed), addons accepted/declined, the smoke-test result, any symlink
   fallback used, and **any items deferred to the developer** (e.g. ambiguous
   modules, a command that couldn't be smoke-tested) — plus the **first usable
   outcome**: the verified scoped command and mapping (or the honest gap), the
   installed skill identity and version, the active capability limits, and the
   next useful action (`/dwp-create …`, or what to fix first).
11. **Upgrade idempotency (harness upgrade only):** run the upgrade reconciliation
   a second time; it MUST report no changes. If it does not, fix the cause
   before reporting done.

Report a concise summary to the developer: archetype, stack, what was generated,
the smoke-test result, and any deferred items — pointing them at
`.dwp/onboard/REPORT.md` for the detail.

---

## Modes & invocation

- `/deepworkplan-onboard` (or "make this repo AI-first", "onboard this repo",
  "set up AGENTS.md + docs + .agents") — full guided flow (consent before
  writing).
- `--dry-run` / "just show me the plan" — recon + planned change set, **no
  writes** (Phase 0.5).
- `trust` / `auto` — proceed without per-step confirmations, but still get the
  one consent gate in Phase 0 before the first write and still surface addons.
- `upgrade` / "upgrade the harness" / "bring this repo to the current DWP
  standard" — force the **targeted harness upgrade** (Phase 0): reconcile only
  what the newer standard requires, preserve everything handwritten, report
  per file, idempotent. Selected automatically when a previously onboarded repo
  predates the installed standard.
- `plan` / "onboard this as a deep work plan" — force the **plan-driven path**
  (Phase 2b) regardless of size: do recon + `AGENTS.md`, then emit an onboarding
  Deep Work Plan and hand off to `/dwp-execute`. The flow **auto-selects** this
  path for large repos even without the flag.

## Failure-mode guardrails (do not violate)

- **No placeholders ship.** If a real value is unknowable, ask — never write
  `<...>` or a generic guess into `AGENTS.md` / `docs/`.
- **No clobbering.** Existing hand-written artifacts are merged/backed-up/asked
  about, never silently overwritten.
- **No phantom catalog entries.** `.agents/docs/` must reflect exactly what
  exists.
- **No stack mismatch.** If the preset and the real repo disagree, the **real
  repo wins** — re-derive from recon.
- **Idempotent.** Re-running on an onboarded repo only fills gaps; it does not
  duplicate or churn working files. A harness upgrade run twice changes nothing
  the second time.
- **No invented scoped commands.** A scoped pattern is either verified against
  a real path of this repository (non-empty selection recorded) or marked
  proposed/unverified with a real fallback. Never label a supported feature
  unavailable to avoid checking, and never label an unchecked pattern verified.
- **No required optional addons.** The core outcome (Phases 3–8) never depends
  on an optional addon; those are offered, not assumed. The one required
  component beyond the core scaffolding is the AI Diff Reviewer local review
  (Phase 7a), installed pinned and recorded honestly when it cannot be.
