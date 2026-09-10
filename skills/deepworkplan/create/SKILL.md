---
name: deepworkplan-create
description: Create a Deep Work Plan. Gather context, analyze requirements, and materialize a single final plan under .dwp/plans/ — guided mode stages a refined draft in .dwp/drafts/ for review; trust mode materializes directly. Use when the developer wants a new structured multi-task plan.
version: "2.17.1"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
---

# DeepWorkPlan — Create

Create a new Deep Work Plan through a smooth, unified flow: the developer
provides information once, you run the **requirements analysis**, and then —
depending on the mode — either stage a **single refined draft** for review
(guided) or **materialize the plan directly** under `.dwp/plans/PLAN_{name}/`
(trust). The plan's substance is composed **once**.

> **Single-step (vs legacy):** there is **no separate raw-draft file**. The only
> reviewable draft artifact is `.dwp/drafts/PLAN_{name}_draft_refined.md`, and it
> exists only in guided mode or on explicit request
> (`../spec/DWP_SPECIFICATION.md` §3).

## Philosophy

The goal is a delightful, smooth experience. The user provides information once;
the system handles all intermediate steps (analysis, draft or direct
materialization, quality check) automatically — and never generates an artifact
nobody asked for.

## Shared resources (read these)

- [`../shared/context.sh`](../shared/context.sh) — resolve repo root, branch,
  agent tool, and the `.dwp/` output location (`dwp_dir`).
- [`../shared/dwp-paths.md`](../shared/dwp-paths.md) — the `.dwp/plans/` +
  `.dwp/drafts/` output convention.
- [`../shared/adaptation.md`](../shared/adaptation.md) — reasoning-over-copy-paste
  and the two repository archetypes (individual repo vs orchestrator hub).
- **Guide (essential — read for this flow):** [`../guide/authoring.md`](../guide/authoring.md) (plan README structure §4, task-file anatomy §5 incl. the Touched Surface, test and security discipline §5.3–§5.4) and [`../guide/structure.md`](../guide/structure.md) (folders §1, naming §2, lifecycle §10).
- **Guide (conditional — read only when the trigger fires):** [`orchestrator.md`](orchestrator.md) (this directory) plus [`../guide/orchestrator.md`](../guide/orchestrator.md) if Step 2.6 detects an orchestrator plan; [`team-agents.md`](team-agents.md) (this directory) plus [`../guide/team-agents.md`](../guide/team-agents.md) **only if Step 2.10 finds parallelizable tasks** (the host merely *having* team agents is not a trigger); [`addon-augmentations.md`](addon-augmentations.md) (this directory) if the target repo has an installed addon that augments the Final Review; [`../guide/prompts.md`](../guide/prompts.md) §7 when composing prompt text; [`../guide/skills-integration.md`](../guide/skills-integration.md) §11 when a task references skills or agents; [`../guide/execution.md`](../guide/execution.md) §6.1 when writing the Final Review task. Do not read other guide files for this flow; [`../guide/GUIDE.md`](../guide/GUIDE.md) is the routing index, consulted only when a section is not named above.
- [`../examples/CREATE_PLAN.md`](../examples/CREATE_PLAN.md) — prompt patterns.
- [`../examples/PROMPTS_TEMPLATE.md`](../examples/PROMPTS_TEMPLATE.md) — the
  `PROMPTS.md` template for each plan.
- The target repository's `docs/TESTING_GUIDE.md` (`../spec/DOCUMENTATION_STANDARD.md` §3.4) — the documented full and scoped validation commands and the source-to-test mapping that every generated gate is selected from.
- **Spec (conditional — read the named sections only when the trigger fires):** [`../spec/DWP_SPECIFICATION.md`](../spec/DWP_SPECIFICATION.md) §11 when the rigor tier is borderline and §5.0.2 when a Touched Surface is genuinely ambiguous; [`../spec/PLAN_STATE.md`](../spec/PLAN_STATE.md) §3–§4 **and** [`../spec/schema/`](../spec/schema/) when writing the state layer in Step 4.4 item 7. The step text below is self-sufficient for the ordinary case — read these only when it is not.

## Parameter Reference

| Input | Classification | Mode | Behavior | Example |
|-------|---------------|------|----------|---------|
| (none) | — | guided | Ask for name, then ask questions; analyze; stage the refined draft for review; materialize on approval | `/dwp-create` |
| `{short text}` | **name-only** | guided | Extract name, ask questions immediately; then as above | `/dwp-create improve error handling` |
| `{long text}` | **full-context** | guided | Infer name; analyze the provided context; stage the refined draft for review; materialize on approval | `/dwp-create Refactor auth to use JWT across all services. Currently using sessions...` |
| `trust` or `auto` | — | trust | Ask for name, then ask questions; analyze; **materialize the plan directly** (no draft file, no confirmations); the plan is pre-approved for unattended execution | `/dwp-create trust` |
| `{short text} trust` | **name-only** | trust | Extract name, ask questions; then as above | `/dwp-create improve-error-handling trust` |
| `{long text} trust` | **full-context** | trust | Infer name; analyze; materialize directly | `/dwp-create Refactor auth... trust` |
| `refined-draft {name}` | — | refined-draft-only | Produce ONLY the refined draft (no final plan) — works in either mode | `/dwp-create refined-draft my_plan` |
| `from-refined-draft {file}` | — | from-refined-draft | Build the final plan from an existing refined draft | `/dwp-create from-refined-draft PLAN_x_draft_refined.md` |
| `from {file}` | — | from-refined-draft | Alias for `from-refined-draft` | `/dwp-create from PLAN_x_draft_refined.md` |

> **Name format:** users type names in any format; you auto-convert to
> `snake_case` internally. **Explicit draft parameters win** over the ordinary
> trust default: `refined-draft … trust` still produces a draft.

## Modes

### Guided Mode (default)
- Collects information from the user; runs the requirements analysis (Step 3).
- Creates the **refined draft** → shows it for review.
- Asks for confirmation before creating the final plan.
- User can request adjustments before final generation.

### Trust Mode (`trust` or `auto`)
- Collects information from the user; runs the **same** requirements analysis
  (Step 3) and the **same** plan-quality check (Step 4.5).
- **Materializes the final plan directly** — no draft file is written. Trust
  waives the intermediate *review*, never the *analysis* or the quality check.
- Records the plan as **pre-approved for unattended execution**
  (`../spec/AGENT_PROTOCOL.md` §7.2): the developer's `trust` instruction is
  the approval.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`.

**Writes:** plan artifacts under the gitignored `.dwp/` directory only —
`.dwp/drafts/` when a draft is produced, `.dwp/plans/PLAN_{name}/` for the
materialized plan (README, task files, analysis outputs, state layer). "Trust
mode" skips intermediate confirmations of **plan content**, not of the write
boundary, and grants no permission the plan does not list.

**It MUST NOT:** modify source files (that is `execute`'s job), write outside
`.dwp/`, read or include secrets in plan content, install anything, make network
calls, or materialize a plan whose tasks lack acceptance criteria and validation
gates. Ordinary `create` never requires a source edit, an install, or the network.

## Unified Workflow

### Step 0 — Parse Parameters & Determine Mode

**0.1 Detect trust mode:** if the LAST word is `trust` or `auto`, remove it and
set `trust_mode = true`; otherwise `false`.

**0.2 Detect special modes (check FIRST word):**
- `refined-draft` → `mode = "refined-draft-only"`, remaining text = plan name.
- `from-refined-draft` or `from` → `mode = "from-refined-draft"`, remaining text
  = refined-draft file path.
- Otherwise → continue to input classification (0.3).

**0.3 Classify remaining input:**

| Condition | Classification | What to do |
|-----------|---------------|------------|
| No remaining text | **no input** | Go to Step 1, then Step 2 (ask for name + all info) |
| ≤10 words AND no complete sentences AND no line breaks | **name-only** | Convert to snake_case → plan name. Go to Step 1, then Step 2 (skip name question) |
| >10 words OR detailed sentences OR line breaks | **full-context** | Infer plan name → snake_case. Go to Step 1, then Step 3 (use provided context) |

**Name auto-conversion to snake_case:** lowercase; replace hyphens/spaces with
`_`; strip everything but `a-z0-9_`. Examples: `improve Feature X` →
`improve_feature_x`, `add-stripe-payments` → `add_stripe_payments`.

> **CRITICAL:** when input is **name-only**, NEVER explore the codebase or
> research the topic before asking questions. The name only says what to CALL the
> plan, not what to DO. Go directly to Step 2.

**Routing by mode:**
- `from-refined-draft` → skip to Step 4.3.
- `refined-draft-only` → gather info, analyze, create only the refined draft,
  skip final plan creation (in either trust or guided mode).
- `no input` / `name-only` → Step 1, then Step 2.
- `full-context` → Step 1, then Step 3.

### Step 1 — Quick Introduction

Show a brief intro matching the mode: in **guided** mode, that you will analyze
the requirements, stage a refined plan for review, and then generate the final
executable plan; in **trust** mode, that you will analyze the requirements and
materialize the final executable plan directly (no draft, no confirmations), and
that the plan will be pre-approved for unattended execution.

### Step 2 — Gather Information (Conversational)

> **Skip the *questions* (2.1–2.5) for `full-context` input.** Steps **2.6** and
> **2.10** are detections, not questions: they run in **every** mode. For
> full-context input (and for `from-refined-draft`), skip 2.1–2.5 and run 2.6 and
> 2.10 at the start of Step 3 against the provided context, then continue.

Collect, conversationally:
- **2.1 Plan name** (skip if already extracted) — auto-convert to snake_case, add
  `PLAN_` prefix internally.
- **2.2 Objective** — one or two sentences.
- **2.3 Context** — where the changes live, constraints/rules, tech notes.
- **2.4 Tasks** — at least 2; if only 1, suggest breaking it down.
- **2.5 Guidelines (optional)** — branch/commit format, coverage target, whether
  an Executive Report is wanted at completion (records an explicit prior request
  per `../spec/DWP_SPECIFICATION.md` §6.3), etc.

**2.6 Orchestrator detection (automatic — trigger only).** After 2.3–2.4 (or, for
full-context input, at the start of Step 3), an
**orchestrator plan** is indicated when the work spans 2+ sub-repositories with
independent feature work, or the user explicitly mentions child DWPs /
orchestrator / "create plans in each repo". **If, and only if, this fires:**
read [`orchestrator.md`](orchestrator.md) (this directory) and follow its
gathering steps (2.6 choice, 2.7–2.9). Otherwise skip it entirely.

**2.10 Team-agents detection (automatic — runs in every mode, including when
Step 2 was skipped; non-orchestrator plans; trigger only).** Analyze whether 2+
tasks touch different files/modules
with no data dependencies and would benefit from parallel execution. This is NOT
opt-in — but the **only** trigger is the analysis's answer, never the host's
capabilities. **If, and only if, 2+ tasks are parallelizable:** read
[`team-agents.md`](team-agents.md) (this directory) and follow its steps (2.10
configuration, and 2.11 parallel research if that step's own trigger — 2+ repos
or several independent modules with context missing — also fires). If not
parallelizable: add nothing, mention nothing, read nothing, even when the host
supports team agents.

### Step 3 — Requirements Analysis (both modes, before any file is written)

> **First, if Step 2's questions were skipped** (full-context input or
> `from-refined-draft`): run the two detections now, against the provided
> context — **2.6 orchestrator** and **2.10 team-agents** — and read their
> on-demand files only if a trigger fires. A detection is never skipped merely
> because no questions were asked.

This step is what the draft used to carry implicitly. It runs in **every** mode
and is the substance of the plan; the mode only decides whether it is first
staged as a draft (guided) or materialized directly (trust).

- **3.1 Proportional rigor (`../spec/DWP_SPECIFICATION.md` §11).** Confirm the
  work warrants a plan. A trivial single-concern change is **micro** tier — in
  **guided** mode say that a plan is disproportionate, offer to state goal +
  acceptance criteria + validation gate inline, and do that instead. In **trust**
  mode the developer has already asked for a plan and there is nobody to answer:
  **do not stop to ask.** Record the micro judgment and the inline alternative in
  the plan README's Plan Variables (`Rigor: micro — a plan is arguably
  disproportionate; inline alternative: …`) and materialize the plan anyway; the
  developer sees the note and can discard it. Otherwise choose `standard` or
  `deep` and record why (in the draft in guided mode; in the plan README in trust
  mode). A borderline call is recorded, never asked.
- **3.2 Requirement inventory.** List every user requirement and constraint
  (from Steps 2–2.5 or the full-context input). Each one will need an **owning
  task** and an **observable acceptance criterion**.
- **3.3 Task decomposition (`../spec/DWP_SPECIFICATION.md` §6.4).** Each task is
  one coherent outcome with a bounded write surface, concrete inputs and outputs,
  and resumable sub-steps. Split when distinct outcomes carry different failure
  modes or independent evidence that would otherwise hide behind one checkbox;
  keep tightly coupled edits together; keep resumable sub-steps inside a larger
  cohesive task rather than exploding it. There is **no** task-count quota and
  no ritual of a separate task per minor edit. Preserve full detail — this
  analysis never shortens a requirement to save space.
- **3.4 Dependency order and prerequisites.** Order tasks so every prerequisite
  artifact (a decision, a file, a contract) exists before the task that consumes
  it; record, per task, its owned surface, prerequisite artifacts, and expected
  outputs (these become the task's Context, Read Before Starting, and Outputs).
- **3.5 Validation selection (`../spec/DWP_SPECIFICATION.md` §5.0.2, §5.1).**
  For each behavior-changing task, derive the **planned Touched Surface**, the
  affected consumers, and the **risk class** (isolated / seam / shared-core /
  unknown), and select runnable gates from the repository's documented commands
  and mapping (`docs/TESTING_GUIDE.md`): the tests of the changed behavior plus
  affected consumers; integration/contract checks **inside** any task that changes
  a real seam; a widening to the full suite for shared/core, configuration,
  schema, dependency or toolchain changes or when impact cannot be bounded. Where
  the repository documents **no** scoped invocation, the task's gate is the full
  suite by rule — and note in the README that the repository's harness can be
  upgraded (`../spec/DOCUMENTATION_STANDARD.md` §3.5). Do **not** paste a generic
  full-suite command into every task: full validation of the **final state** is
  the Final Review's job (§5.1.3).
- **3.6 Test and security discipline.** Bake the **test discipline**
  (`../guide/authoring.md` §5.3) into every behavior-changing task: its
  Acceptance Criteria require unit-first automated coverage for the new/changed
  behavior (fast, isolated, observable behavior; integration at real seams; no
  ratio or count quota), and its Validation runs the selected tests plus
  lint/type-check/format. Where related work is substantial, prefer a dedicated
  `N.task_add_tests_for_{feature}.md` task right after the implementation task.
  Likewise, for any task that touches auth, input handling, secrets/config,
  network surface, or dependencies, bake the **security discipline** into it
  (`../guide/authoring.md` §5.4); where the security-sensitive work is
  substantial, prefer a dedicated `N.task_security_hardening_{feature}.md` task
  placed after the implementation tasks and **before** the comprehensive-tests
  task, so findings are fixed before tests encode the behavior and become
  regression test cases rather than rework.
- **3.7 Requirements → tasks → gates check.** Before leaving this step, confirm:
  every requirement from 3.2 has an owning task and an observable acceptance
  criterion; prerequisites are available in order; every task is cohesive,
  independently verifiable, and fully detailed; every behavior-changing task has
  a planned Touched Surface and a non-empty, runnable gate. Fix gaps here, not
  after materialization.

### Step 4 — Draft or Materialize (by mode)

#### 4.1 Guided Mode — Refined Draft and Review

Show a **2-step** progress UI:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creating your plan...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/2] Drafting refined plan...
```

**Write the refined draft** — one file, directly (no raw draft first):
- Resolve `dwp_dir` via `../shared/context.sh`; ensure `<dwp_dir>/drafts/` exists.
- Compose a professional, complete plan prompt following
  `../examples/CREATE_PLAN.md` from the Step 3 analysis: objective, context
  (enriched with parallel research if `team-agents.md` ran), the tier and why,
  well-formed tasks with their planned Touched Surface and gates, guidelines.
  Expand every section with full detail and clarity in one pass.
- Write **only**: `.dwp/drafts/PLAN_{name}_draft_refined.md`.

```
[1/2] Drafting refined plan... ✓
[2/2] Preparing for review...
```

Present a summary (objective, tier, task count + list, location, constraints)
and the path `→ .dwp/drafts/PLAN_{name}_draft_refined.md`, then offer:
1. Looks good, create the final plan → Step 4.4.
2. Make adjustments → ask what to change, **edit the refined draft in place**,
   show the menu again.
3. Show the full refined draft → display it, then re-show the menu.
4. Stop here → completion message for the draft phase.

#### 4.2 Trust Mode — Direct Materialization

No draft file. Show a **2-step** progress UI and go straight to Step 4.4:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creating your plan... (trust mode)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/2] Analyzing requirements... ✓
[2/2] Materializing plan...
```

The approved objective, context, tier, and task outline are captured in the plan
README (§1, §2, §4), so nothing reviewable is lost. The README's Plan Variables
record `Pre-approved for unattended execution: yes (trust)`.

#### 4.3 From-Refined-Draft Mode

- Validate the file exists in `.dwp/drafts/`. If not found, list available
  refined drafts and ask the user to choose.
- Read it; extract plan name, objective, context, tier, tasks, guidelines; run
  Step 3.7 (requirements → tasks → gates check) against it.
- Skip to Step 4.4.

#### 4.4 Create Final Plan

Follow `../guide/authoring.md` (§4–§5) and `../guide/structure.md` (§1–§2).

**Before writing:** resolve `dwp_dir`; if `.dwp/plans/PLAN_{name}/` already
exists, see *Error Handling — plan exists / partial materialization*. Never
overwrite files that are not part of this plan.

**Write order (resumable at any point):** `manifest.json` → `README.md`
**skeleton** (goal, context, variables, guidelines and the full task list with
titles and links, with `Plan Status: materializing`) → `analysis_results/PLAN_ANALYSIS.md`
(the Step 3 record) → task files in order → `PROMPTS.md` → `PROGRESS.md` →
`analysis_results/SKILLS_CANDIDATES.md` → `state.json` → **flip the README to
`Plan Status: 0/N completed`** as the last write. From the second write onward,
the plan's intended shape is on disk in human-readable form; from the third, any
agent can regenerate a missing task file faithfully. A folder whose README is
missing, still says `materializing`, or links a task file that does not exist is
a **partial materialization**: `create` and `refine` complete or discard it,
`execute` and `resume` never run it.

Create:

1. **Folder + `manifest.json` (first write):** create `.dwp/plans/PLAN_{name}/`
   and immediately write `manifest.json` — plan identity: name, title, archetype,
   rigor tier, `spec_version` **"2.3.0"**, `task_count` = the number of task files
   this materialization will write (Final Review included), creating agent —
   atomically (write-temp-then-rename), valid against
   `../spec/schema/plan-manifest.schema.json` (closed schema), written once,
   never edited after.
1b. **README skeleton (second write):** write `README.md` with everything in
   item 8 except the final status: the Task List names **every** intended task
   with its future filename and link, and the status line reads
   `Plan Status: materializing` (no count). This is the resumable record of the
   plan's shape; it is flipped in item 9 and never left as `materializing` on a
   finished plan.
1c. **`analysis_results/PLAN_ANALYSIS.md` (third write):** the Step 3 record —
   requirement inventory, tier and why, task decomposition with each task's
   owned surface, prerequisites and outputs, the planned Touched Surface, risk
   class and selected gate per behavior-changing task, and the mode. Compact
   (aim under ~600 words); it lets a fresh agent regenerate a missing task file
   without re-deriving the plan, and gives `refine` the original reasoning.
2. **User-defined task files** — `N.task_{title}.md`, each with the ten-section
   anatomy (`../spec/DWP_SPECIFICATION.md` §5): Context; Read Before Starting;
   Goal; **Touched Surface** (planned surface, affected consumers, risk class,
   test mapping used, selected gate and reason — from Step 3.5; `not applicable
   — <reason>` for pure prose/research); Instructions (with re-anchoring);
   Acceptance Criteria (incl. the unit-first coverage expectation from 3.6);
   Outputs; Validation (the selected, runnable gates — scoped where documented,
   the full suite as fallback, integration checks where the task changes a seam;
   never a zero-test selector); Rollback (optional); Execution Checklist;
   Completion & Log. The Execution Checklist **MUST** include, before the
   validation step: *"Skills decision: record `none` / `update` / `create` /
   `defer` in the log; append any real candidate to
   `analysis_results/SKILLS_CANDIDATES.md` by stable ID `T{N}-{seq}`; do any
   warranted in-scope authoring now"* (`../spec/DWP_SPECIFICATION.md` §6.2). The
   Completion & Log template **MUST** carry a `Skills disposition:` line and a
   `Gate record:` line (command, cwd, scope/reason, revision or fingerprint,
   result, evidence path).
3. **The Final Review task** — `{N}.task_final_review.md`, **last**, the single
   mandatory final task (`../spec/DWP_SPECIFICATION.md` §6.1;
   `../guide/execution.md` §6.1). Its instructions, in order: **(a) security
   pass** — review the plan's full accumulated diff for hardcoded secrets,
   injection risks, unsafe input handling, new attack surface, and
   auth/permission changes; audit dependencies the plan introduced (best-effort,
   with the ecosystem's audit tooling where available); verify `docs/SECURITY.md`
   still reflects reality and update it when the plan changed secrets handling,
   the auth model, or data boundaries; write `analysis_results/SECURITY_REVIEW.md`
   even when clean; a critical finding blocks completion until fixed or
   explicitly accepted by the user. **(b) Final-state validation** — run the
   repository's complete applicable test, lint, type-check and format suites on
   the final state (§5.1.3); fixes made during review invalidate affected results,
   which are rerun. **(c) Skills reconciliation** — confirm every task log has a
   disposition and every `SKILLS_CANDIDATES.md` entry has one; finish any open
   warranted authoring before (b) is final; no whole-plan rediscovery, no second
   report. **(d) Completion** — report deliverables, evidence, limitations and
   PR links; **offer the Executive Report once** (generate only on request; an
   explicit request recorded in the plan guidelines counts); send the completion
   report through the configured channel regardless of the answer.

   **Local review step (required):** read
   [`addon-augmentations.md`](addon-augmentations.md) (this directory) and add
   its AI Diff Reviewer post-existing-checks step to the Final Review task's
   security pass — it applies to every 2.3.0 plan. When the target repo lacks
   `.agents/skills/ai-diff-reviewer/` or an extension file at one of the three
   recognized paths, the step's degradation clause (record a `local reviewer
   not installed` finding, install when authorized, otherwise carry the
   finding) applies at execution time; do not omit the step.

4. **PROMPTS.md** — from `../examples/PROMPTS_TEMPLATE.md`, replacing
   `{PLAN_NAME}` with the plan name. The template is written for **you**, so
   strip its authoring scaffolding before writing the file: drop the
   "Instructions for Agents Creating This File" block and the closing
   "For agents:" note, and drop or repoint its relative links (they resolve from
   `examples/`, not from inside a plan folder). What ships is the copy-paste
   prompts only.
5. **PROGRESS.md** — a **bounded working index** (`../spec/PLAN_STATE.md` §5.1;
   `../guide/execution.md`): goal and constraints; active task and next action;
   unresolved blockers; current contracts and decisions still in force; direct
   pointers to durable records (task logs, `analysis_results/`). Soft budget
   ~1,000 words for routine carry-forward; completed detail lives in task logs
   and is retrieved by pointer — never discard an unresolved constraint to fit.
6. **analysis_results/** — the folder, plus `SKILLS_CANDIDATES.md` with a
   two-line header (purpose; entry shape `T{task}-{seq} · pattern · evidence ·
   disposition`). No other placeholder files.
7. **`state.json` (RECOMMENDED, `../spec/PLAN_STATE.md`; REQUIRED for unattended
   runs and for workspaces without git)** — the initial projection: every task
   `pending`, empty gates, `task_count` equal to the manifest's. Atomically
   (write-temp-then-rename); valid against `../spec/schema/plan-state.schema.json`
   (no extra fields — the schema is closed). `manifest.json` was written in item 1
   and is not touched here.
8. **README.md** (content — written as the skeleton in item 1b) — Goal; Context; Plan Variables (incl. `Standard: DWP
   spec 2.3.0`, the tier and why, and in trust mode `Pre-approved for unattended
   execution: yes (trust)`); Global Guidelines (incl. an explicit Executive
   Report request if the user made one); Task List with `[ ]` checkboxes + links
   (the Final Review last); Execution Rules; Skills & Agents Used; Plan Status /
   Notes; Analysis Outputs table (`SKILLS_CANDIDATES.md` — every task;
   `SECURITY_REVIEW.md` — Final Review; `EXECUTIVE_REPORT.md` — optional, on
   request); Quick Reference to `PROMPTS.md`. Add the note: *"Every plan ends
   with a single Final Review (security pass, final-state validation, skills
   reconciliation). Skills decisions are made inside each task; the Executive
   Report is optional and offered at completion. Auto-generated by
   `/dwp-create`."*
9. **Flip the README status (last write):** replace `Plan Status: materializing`
   with `Plan Status: 0/N completed` where N equals `manifest.task_count` and
   the number of task files on disk. Only now is the plan complete.

**Conditional branches:** if Step 2.6 fired, apply the **orchestrator
additions** in [`orchestrator.md`](orchestrator.md); if Step 2.10 fired, apply
the **team-agents metadata** and, for 5+ user task files where team agents are
available, the **accelerated generation** in [`team-agents.md`](team-agents.md).
Neither branch changes the sequential path: every task must work sequentially,
and the Final Review is always sequential.

#### 4.5 Plan-Quality Check (both modes — before reporting success)

Verify, and fix before continuing:
- **Requirements → tasks → gates** (Step 3.7) hold for the materialized files.
- Tasks are atomic, ordered, numbered `1..N` without gaps; the Final Review is
  task `N` and the only final task; every README link resolves.
- Every task has Acceptance Criteria and a Validation gate; every
  behavior-changing task has a Touched Surface with a risk class and a non-empty,
  runnable selection (no zero-test selector); tasks that change a seam carry an
  integration/contract check; the unit-first coverage expectation is in the
  Acceptance Criteria (`../guide/authoring.md` §5.3).
- Every task's checklist has the skills-decision step; `SKILLS_CANDIDATES.md`
  exists; `PROMPTS.md`, `PROGRESS.md` and `analysis_results/PLAN_ANALYSIS.md`
  exist; `manifest.json` validates and its `task_count` equals the task files
  written; `state.json` (when present) validates and agrees with the task files;
  the README no longer says `materializing` and every task link resolves.
- No placeholder text (`[TODO`, `[TBD`, `{...}` left unfilled) remains.

### Step 5 — Completion & Execute Option

For a full plan, report success and the location
`.dwp/plans/PLAN_{name}/` (in trust mode, state that it is pre-approved for
unattended execution), then offer: (1) execute now → run the **Execute**
sub-skill (`../execute/SKILL.md`); (2) review the README first, then ask again;
(3) done for now → tell them to run `/dwp-execute {name}` later (or
`/dwp-execute {name} trust` to run to the end without questions).

**Dailybot kickoff (only when the Dailybot addon is wired — best-effort,
non-blocking):** after the plan is materialized and approved, send a **regular**
(non-milestone) kickoff report via the dailybot `report` sub-skill — "Starting:
\<what is being built and why it matters\>" — per the addon's lifecycle event
model (`../addons/dailybot/SPEC.md` §5.1). One kickoff per plan; skip silently
if Dailybot is absent, unauthenticated, or `.dailybot/disabled` exists. Never
block on this.

For `refined-draft-only` mode, report the single refined draft saved at
`.dwp/drafts/PLAN_{name}_draft_refined.md` and the next step: run
`/dwp-create from PLAN_{name}_draft_refined.md` to build the final plan.

### Step 6 — Execute Plan (Optional)

If the user chose to execute, hand off to the **Execute** sub-skill
(`../execute/SKILL.md`): read the plan README, check git status, start from the
first `[ ]` task, execute sequentially, validate, commit per task, report.

## Error Handling

- **Plan name already exists (complete plan — has `README.md`):** offer a
  different name / overwrite (explicit confirmation, even in trust mode — it is
  a destructive action) / cancel.
- **Partial materialization found (folder exists and its `README.md` is missing,
  says `Plan Status: materializing`, or links a task file that does not exist):**
  read `manifest.json` (intended `task_count`, title) and the README task list
  when present, and report which intended files exist and which are missing;
  offer to **complete** it — regenerate only the missing files from
  `analysis_results/PLAN_ANALYSIS.md` (or, when that record is also missing,
  from the manifest, the README task list and the existing task files, rebuilding
  Step 3 for the gaps; in guided mode ask only for what no file states, in trust
  mode derive it and say so in the README), leave existing task files and the
  manifest untouched, then flip the status line — or **discard** it (explicit
  confirmation, even in trust mode). Never overwrite unrelated files. A folder
  with neither a manifest nor a README is handled the same way with the intended
  count unknown.
- **Name auto-converted:** show an informational notice (not an error).
- **Refined draft not found (from-refined-draft):** list available refined drafts
  in `.dwp/drafts/` and ask the user to choose.
- **Insufficient tasks (<2):** in **guided** mode, ask the user to break the work
  down. In **trust** mode there is nobody to ask: if the work is genuinely one
  atomic change, that is the **micro** tier — record it per Step 3.1 (the Plan
  Variables note plus the inline alternative) and materialize the one user task
  plus the Final Review. Never invent filler tasks to reach a count.
- **No documented validation commands in the target repo:** proceed with the
  full-suite fallback on every behavior-changing task and say so in the README;
  suggest onboarding or the harness upgrade (`../spec/DOCUMENTATION_STANDARD.md`
  §3.5). Never invent a scoped command.

## Important Notes

- **Git ignore:** everything under `.dwp/` is git-ignored.
- **Single artifact:** the only draft file is `PLAN_{name}_draft_refined.md` in
  `.dwp/drafts/` — there is no separate raw draft, and in trust mode there is no
  draft at all.
- **One final task:** `{N}.task_final_review.md`. Never generate
  `task_skills_agents_discovery` or `task_executive_report` files for a new plan
  (plans from earlier versions that have them are executed as recorded —
  `../spec/DWP_SPECIFICATION.md` §6.5).
- **Reference:** follow `../guide/authoring.md` and `../guide/structure.md`; orchestrator → `../guide/orchestrator.md` §13; team agents → `../guide/team-agents.md` §14.
- **Archetypes:** orchestrator support assumes the orchestrator-hub archetype
  (sub-repos under `repositories/`); an individual repo creates standard plans.
  See `../shared/adaptation.md`.
