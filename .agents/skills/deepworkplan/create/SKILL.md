---
name: deepworkplan-create
description: Create a Deep Work Plan for short or long work. Detect planning intent, materialize a compact Lite proposal first, then retain Lite or expand to Full task files when needed. Supports guided and trust handoff without executing product work.
version: "4.0.3"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
---

# DeepWorkPlan — Create

Create a new Deep Work Plan through a smooth, unified flow: the developer
provides information once, you run the **requirements analysis**, and materialize
a Lite plan folder under `.dwp/plans/PLAN_{name}/`. Guided mode presents that
proposal for review; trust chooses its ready representation without a review.
Both modes return control to the developer to execute later.

> **Lite-first (v2.4):** `create` writes no draft file and no `.dwp/drafts/`
> directory. A Lite plan is a complete proposal, not a partial Full plan — it is
> the reviewable artifact the refined draft used to be, except that it is already
> executable. The `refined-draft` / `from-refined-draft` commands were removed in
> 2.4.0; see `../spec/LITE_PLANS.md`.

## Lite-first command grammar

Parse boundary options before interpreting the remaining text. `trust` and
`auto` select trust mode; `lite` and `full` express an optional format
preference. Each may be a contiguous token at the beginning or end, in either
order: `/dwp-create trust lite add retry`, `/dwp-create add retry lite trust`,
`/dwp-create trust add retry`, and `/dwp-create add retry full` are equivalent
forms. Remove all recognized boundary options before classifying context.

Repeated identical options are harmless. `lite` plus `full` is an explicit
conflict: report it rather than guessing. `--` ends option parsing; everything
after it is literal context. Do not scan the middle of context, quotations or
code for option words. `trust` with no context asks for the goal. The resulting
plan is handed off; create never modifies product source or calls execute.

## Lite-first lifecycle

Write `manifest.json`, `README.md`, `PROGRESS.md`, `PROMPTS.md`, appropriate
`analysis_results/` and `state.json` using the v2 schemas. A Lite README has
one shared rules section and compact anchored task records (`#task-N`) containing
goal, touched surface, acceptance criteria, validation and completion evidence.
It includes an inline Final Review. It does not create task files or boilerplate
solely to meet a task count. `materializing`, `ready` and `promoting` are distinct
from review approval and execution status.

Guided mode writes a `pending` proposal, shows the observed signals and format
recommendation, and lets the developer retain Lite, promote Full, edit, or stop.
Trust records the same rationale, chooses Lite or Full, marks it ready and
pre-approved, and returns the execute command. An explicit Full preference wins;
an explicit Lite preference is retained only if compact records can express every
requirement and gate. Unknown scope triggers discovery, not an automatic Full
classification. Small planning work is a valid Lite plan; never route it to an
inline non-DWP alternative merely because it is small.

## Philosophy

The goal is a delightful, smooth experience. The user provides information once;
the system handles all intermediate steps (analysis, materialization
materialization, quality check) automatically — and never generates an artifact
nobody asked for.

## Shared resources (read these)

- [`../shared/context.sh`](../shared/context.sh) — resolve repo root, branch,
  agent tool, and the `.dwp/` output location (`dwp_dir`).
- [`../shared/dwp-paths.md`](../shared/dwp-paths.md) — the `.dwp/plans/` +
  `.dwp/plans/` output convention.
- [`../shared/adaptation.md`](../shared/adaptation.md) — reasoning-over-copy-paste
  and the two repository archetypes (individual repo vs orchestrator hub).
- **Guide (essential — read for this flow):** [`../guide/authoring.md`](../guide/authoring.md) (plan README structure §4, task-file anatomy §5 incl. the Touched Surface, test and security discipline §5.3–§5.4) and [`../guide/structure.md`](../guide/structure.md) (folders §1, naming §2, lifecycle §10).
- **Guide (conditional — read only when the trigger fires):** [`orchestrator.md`](orchestrator.md) (this directory) plus [`../guide/orchestrator.md`](../guide/orchestrator.md) if Step 2.6 detects an orchestrator plan; [`team-agents.md`](team-agents.md) (this directory) plus [`../guide/team-agents.md`](../guide/team-agents.md) **only if Step 2.10 finds parallelizable tasks** (the host merely *having* team agents is not a trigger); [`addon-augmentations.md`](addon-augmentations.md) (this directory) **always when composing the Final Review** (required local-review step on every 2.3.0 plan — do not gate this read on whether the target already has the reviewer installed); [`../guide/prompts.md`](../guide/prompts.md) §7 when composing prompt text; [`../guide/skills-integration.md`](../guide/skills-integration.md) §11 when a task references skills or agents; [`../guide/execution.md`](../guide/execution.md) §6.1 when writing the Final Review task. Do not read other guide files for this flow; [`../guide/GUIDE.md`](../guide/GUIDE.md) is the routing index, consulted only when a section is not named above.
- [`../examples/CREATE_PLAN.md`](../examples/CREATE_PLAN.md) — prompt patterns.
- [`../examples/PROMPTS_TEMPLATE.md`](../examples/PROMPTS_TEMPLATE.md) — the
  `PROMPTS.md` template for each plan.
- The target repository's `docs/TESTING_GUIDE.md` (`../spec/DOCUMENTATION_STANDARD.md` §3.4) — the documented full and scoped validation commands and the source-to-test mapping that every generated gate is selected from.
- **Spec (conditional — read the named sections only when the trigger fires):** [`../spec/DWP_SPECIFICATION.md`](../spec/DWP_SPECIFICATION.md) §11 when the rigor tier is borderline and §5.0.2 when a Touched Surface is genuinely ambiguous; [`../spec/PLAN_STATE.md`](../spec/PLAN_STATE.md) §3–§4 **and** [`../spec/schema/`](../spec/schema/) when writing the state layer in Step 4.4 item 7. The step text below is self-sufficient for the ordinary case — read these only when it is not.

## Parameter Reference

Boundary options (`trust`/`auto`, `lite`/`full`) are parsed first (Step 0.1) and
removed before the remaining text is classified. Every ordinary row below
materializes a **Lite plan folder** — no draft file is written.

| Input | Classification | Mode | Behavior | Example |
|-------|---------------|------|----------|---------|
| (none) | — | guided | Ask for name, then ask questions; analyze; materialize the Lite plan; present it with the format recommendation for review | `/dwp-create` |
| `{short text}` | **name-only** | guided | Extract name, ask questions immediately; then as above | `/dwp-create improve error handling` |
| `{long text}` | **full-context** | guided | Infer name; analyze the provided context; materialize the Lite plan and present it for review | `/dwp-create Refactor auth to use JWT across all services. Currently using sessions...` |
| `trust` or `auto` | — | trust | Ask for name, then ask questions; analyze; materialize the chosen representation directly (no review, no confirmations); the plan is pre-approved for unattended execution | `/dwp-create trust` |
| `{text} trust` / `trust {text}` | **name-only** or **full-context** | trust | Same, with the context preserved from either boundary | `/dwp-create trust fix the settings label` |
| `lite` (either boundary) | — | unchanged | Format **preference**: retain Lite unless a compact record cannot carry a required requirement or gate — then explain why Full is needed | `/dwp-create lite rename this setting` |
| `full` (either boundary) | — | unchanged | Format **preference**: an explicit Full wins; the same folder is materialized and then expanded to task files (Step 4.0 → 4.4) | `/dwp-create redesign the auth flow full` |
| `lite` **and** `full` | — | — | Conflict: report it and ask which one; never silently pick one, including in trust | `/dwp-create lite full ...` → error |
| `--` | — | unchanged | Ends option parsing; everything after it is literal context | `/dwp-create trust -- full rewrite of the parser` |

> **Name format:** users type names in any format; you auto-convert to
> `snake_case` internally.

> **Removed in 2.4.0:** `refined-draft`, `from-refined-draft` and its `from`
> alias. There is no draft artifact and no `.dwp/drafts/` directory — the Lite
> plan replaces them. If a repo still has a `.dwp/drafts/` folder from an earlier
> version, DWP neither reads nor writes it; the developer may delete it. To build
> a plan from an old draft's content, paste that content as the create context.

## Modes

### Guided Mode (default)
- Collects information from the user; runs the requirements analysis (Step 3).
- **Materializes the Lite plan** (Step 4.0) → shows it with the format
  recommendation and the observed signals behind it.
- Asks the developer to retain Lite, promote to Full, edit, or stop. The plan
  stays `Approval: pending` until they choose.
- Never expands to Full without that explicit choice.

### Trust Mode (`trust` or `auto`)
- Collects information from the user; runs the **same** requirements analysis
  (Step 3) and the **same** plan-quality check (Step 4.5).
- **Materializes the chosen representation directly** — Lite, or Full when the
  rubric or an explicit `full` says so; never author both representations. Trust waives the intermediate *review*, never the *analysis*, the
  *quality check*, or the *execution handoff*.
- Records the plan as **pre-approved for unattended execution**
  (`../spec/AGENT_PROTOCOL.md` §7.2): the developer's `trust` instruction is
  the approval. `trust` authorizes the planning decisions — it never calls
  execute.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`.

**Writes:** plan artifacts under the gitignored `.dwp/` directory only —
`.dwp/plans/PLAN_{name}/` for the
materialized plan (README, task files, analysis outputs, state layer). "Trust
mode" skips intermediate confirmations of **plan content**, not of the write
boundary, and grants no permission the plan does not list.

**It MUST NOT:** modify source files (that is `execute`'s job), write outside
`.dwp/`, read or include secrets in plan content, install anything, make network
calls, or materialize a plan whose tasks lack acceptance criteria and validation
gates. Ordinary `create` never requires a source edit, an install, or the network.

## Unified Workflow

### Step 0 — Parse Parameters & Determine Mode

**0.1 Parse boundary options:** before special modes or input classification,
consume contiguous `trust`/`auto`, `lite` and `full` tokens from either boundary
in either order. `trust_mode` is true when `trust` or `auto` occurred; record a
single format preference when `lite` or `full` occurred. Repeated identical
options are valid. A `lite`/`full` conflict is an error. Stop parsing at `--`;
all following text is literal context. Never inspect ordinary context words.

**0.2 Classify remaining input:**

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
- `no input` / `name-only` → Step 1, then Step 2.
- `full-context` → Step 1, then Step 3.

### Step 1 — Quick Introduction

Show a brief intro matching the mode: in **guided** mode, that you will analyze
the requirements, stage a refined plan for review, and then generate the final
executable plan; in **trust** mode, that you will analyze the requirements and
materialize the final executable plan directly (no confirmations), and
that the plan will be pre-approved for unattended execution.

### Step 2 — Gather Information (Conversational)

> **Skip the *questions* (2.1–2.5) for `full-context` input.** Steps **2.6** and
> **2.10** are detections, not questions: they run in **every** mode. For
> full-context input, skip 2.1–2.5 and run 2.6 and
> 2.10 at the start of Step 3 against the provided context, then continue.

Collect, conversationally:
- **2.1 Plan name** (skip if already extracted) — auto-convert to snake_case, add
  `PLAN_` prefix internally.
- **2.2 Objective** — one or two sentences.
- **2.3 Context** — where the changes live, constraints/rules, tech notes.
- **2.4 Tasks** — one bounded task is valid for Lite; split only when outcomes,
  risks or gates genuinely differ. Never invent padding to reach a count.
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
parallelizable: write the **sequential declaration** into the plan README — one
agent-neutral line, `Execution: sequential — {short rationale: shared surface /
collision risk / single-session audit trail}` — and read nothing else for this
detection, even when the host supports team agents. The decision is never
silent in either direction; never fabricate parallel groups to fill the section.

### Step 3 — Requirements Analysis (both modes, before any file is written)

> **First, if Step 2's questions were skipped** (full-context input or
> full-context input): run the two detections now, against the provided
> context — **2.6 orchestrator** and **2.10 team-agents** — and read their
> on-demand files only if a trigger fires. A detection is never skipped merely
> because no questions were asked.

This step runs in **every** mode
and is the substance of the plan; the mode only decides whether it is first
reviewed before execution (guided) or handed off directly (trust).

- **3.1 Proportional rigor (`../spec/DWP_SPECIFICATION.md` §11).** Confirm the
  work warrants a plan. A trivial single-concern change is **micro** tier and is
  a first-class Lite plan: record a concise goal, gate and Final Review rather
  than routing the developer out of DWP. Otherwise choose `standard` or
  `deep` and record why in the plan README. A borderline call is recorded, never asked.
- **3.2 Requirement inventory.** List every user requirement and constraint
  (from Steps 2–2.5 or the full-context input). Each one will need an **owning
  task** and an **observable acceptance criterion**.
- **3.3 Task decomposition (`../spec/DWP_SPECIFICATION.md` §6.4).** One task,
  one objective: a task may perform several steps that serve its single
  granular objective, and must never bundle several objectives — prefer N
  tasks with one objective each over fewer tasks carrying several. Each task
  is one coherent outcome with a bounded write surface, concrete inputs and
  outputs, and resumable sub-steps. Split when a task serves several
  objectives with different failure modes, evidence or authorization that
  would otherwise hide behind one checkbox; keep tightly coupled edits that
  serve the same objective together. There is **no** task-count quota, no
  ritual of a separate task per minor edit, and no padding to inflate the
  count. Preserve full detail — this analysis never shortens a requirement
  to save space.
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

### Step 4 — Materialize (Lite first), then expand only if needed

#### 4.0 Lite-first materialization (the normal path — both modes)

Every ordinary create request lands here. There is **one plan identity and one
folder** from proposal through completion: Lite and Full describe the *task
representation*, not two different products. `create` never modifies product
source and never calls execute.

**Before writing:** resolve `dwp_dir` via `../shared/context.sh`. If
`.dwp/plans/PLAN_{name}/` already exists, see *Error Handling — plan exists /
partial materialization*.

**Decide the representation before the second write.** Apply *Format selection*
below to the Step 3 analysis, together with any explicit `lite`/`full`
preference, and then branch — a task contract is authored **once**, never
inline and then again as a file:

| Mode | Chosen format | What to materialize |
| --- | --- | --- |
| guided | Lite | The Lite representation below. This is the reviewable proposal. |
| guided | Full | The Lite representation below, as the compact proposal to review, recording that Full expansion is required before execution. Expanding on the developer's approval is Step 4.4 — that expansion **is** the approval action, not a rewrite of settled work. |
| trust | Lite | The Lite representation below. |
| trust | Full | **Skip to Step 4.4** for this same folder. Nobody reviews a trust plan, so writing the Lite representation on the way to Full would author every task twice and buy nothing. Write `plan_format: "full"` in the manifest and go. |

**Write order for a Lite plan (resumable at any point):**

1. **`manifest.json` (first write)** — immutable creation identity, written once
   and never edited: `schema` =
   `https://deepworkplan.com/schema/plan-manifest/v2.json`, `spec_version`
   **"4.0.0"**, `name`, `title`, `archetype`, `rigor`, `created_at`,
   `created_by`, `task_count` (the creation count, Final Review included) and
   **`plan_format`** (`"lite"`, or `"full"` when an explicit `full` preference or
   the rubric already decided Full). Atomic (write-temp-then-rename); valid
   against `../spec/schema/plan-manifest-v2.schema.json` — the schema is closed.
   A later change of live task count **never** rewrites this file.
2. **`README.md` skeleton (second write)** — everything in *Lite README anatomy*
   below except the status line, which reads `Plan Status: materializing`.
3. **`analysis_results/`** — the folder, plus `SKILLS_CANDIDATES.md` with the
   two-line header. Write `PLAN_ANALYSIS.md` only when the Step 3 evidence
   warrants a separate record; a small Lite plan does not need one, and an empty
   analysis file is busywork, not rigor.
4. **`PROMPTS.md`** — from `../examples/PROMPTS_TEMPLATE.md`, stripped of its
   authoring scaffolding (see Step 4.4 item 4).
5. **`PROGRESS.md`** — the bounded working index (`../spec/PLAN_STATE.md` §5.1).
6. **`state.json`** — `schema` =
   `https://deepworkplan.com/schema/plan-state/v2.json`, `plan`, `updated_at`,
   `status: "pending"`, `completed_count: 0`, `task_count`, **`format`**
   (`"lite"` — this branch only writes Lite; a Full plan's state is written by
   Step 4.4), **`materialization`** (`"ready"` once every file above is on
   disk), **`approval`** (`"pending"` in guided mode, `"pre_approved"` in trust —
   the same value the README's `Approval` row shows), `promotion: null`, and one
   `tasks[]` entry per task:
   `{ "id": N, "locator": { "kind": "inline", "value": "#task-N" }, "title": …,
   "status": "pending", "gates": [] }`. Atomic; valid against
   `../spec/schema/plan-state-v2.schema.json` — closed schema, so evidence rides
   in the gate `evidence` string, not in new fields.
7. **Flip the README status (last write)** — replace `Plan Status: materializing`
   with `Plan Status: 0/N completed`. Only now is the plan materialized.

A folder whose `README.md` is missing or still says `materializing` is a
**partial materialization**: `create` and `refine` complete or discard it;
`execute` and `resume` never run it. That is a different thing from a finished
Lite plan awaiting review — a complete proposal is not a corrupt plan.

**Lite README anatomy.** One shared rules section, then compact anchored task
records. Do not paste the ten-section task template into the README.

```markdown
# Plan: {Title}

## 1. Goal            ## 2. Context            ## 3. Global Guidelines

## Plan Variables
| Variable | Value |
| --- | --- |
| Standard | DWP spec 4.0.0 |
| Plan Format | Lite |
| Materialization | ready |
| Approval | pending            ← guided; `pre-approved (trust)` in trust mode |
| Rigor | micro \| standard \| deep |
| Pre-approved for unattended execution | no \| yes (trust) |

## Format Decision
Observed signals (task count, touched modules, risk/seams, reversibility,
external coordination, validation cost, ambiguity) → recommendation + why.
One concise record here; machine state is derived from it, never duplicated.

## 4. Task List
- [ ] Task 1: {title} — [#task-1](#task-1)
- [ ] Task N: Final Review — [#task-N](#task-N)

## 5. Execution Rules        ## 6. Skills & Agents Used
## 7. Plan Status / Notes    → `Plan Status: 0/N completed`

## Task 1 {#task-1}
**Goal** · **Touched Surface** (planned surface, risk class, test mapping,
selected gate and why) · **Acceptance Criteria** · **Validation** (a runnable
command) · **Completion log** (status, skills disposition, gate record).

## Task N: Final Review {#task-N}
The same mandatory Final Review — security pass, final-state validation, skills
reconciliation — kept concise and inline. Its evidence lands in
`analysis_results/SECURITY_REVIEW.md`.
```

**Anchor rules.** Each `{#task-N}` occurs **exactly once**; IDs are contiguous
`1..N`; the Task List checkbox line is the canonical index and the only thing
that defines completion. Checkboxes inside fenced examples are **not** progress.
A locator is `inline` (a README anchor) or `file` (one Full task file) — never a
path with `..`, an absolute path, or a missing target.

**Lite is not ungated.** Every task keeps scoped acceptance criteria, a runnable
validation gate, a completion log and a state entry. One bounded task plus the
Final Review is a valid plan; never pad to reach a count.

**Format selection.** Choose Lite when the shared rules plus compact task records
carry every requirement and gate. Choose Full when instruction detail,
dependencies or contracts cannot fit a reviewable compact record — risk alone
argues for *stronger gates*, not necessarily longer task prompts, and unresolved
scope calls for discovery, not an automatic Full. Record the signals and the
reason; this is auditable judgment, not a claim that every model decides alike.
An explicit `full` wins. An explicit `lite` is honored unless a requirement or
gate would be lost — then say exactly which one, and why Full is required.

**Then, by mode:**

- **Guided** — present the materialized Lite proposal, the recommendation and
  the signals behind it, then offer: (1) retain Lite → Step 4.5; (2) expand to
  Full → Step 4.4, writing task files for the same task IDs; (3) edit → adjust
  and re-present; (4) stop. `Approval` stays `pending` until they choose. When
  the recommendation is Full, say so plainly: the proposal is reviewable but the
  plan is not executable as Lite until it is expanded.
- **Trust** — the format was already chosen and materialized once, per the
  branch table above. Record `Pre-approved for unattended execution: yes (trust)`
  and `Approval: pre-approved (trust)`, then go to Step 4.5 and hand off with
  `/dwp-execute PLAN_{name}`. Never invoke execute.

Promotion **after** creation is not this step: it is `/dwp-refine promote`
(`../refine/SKILL.md` Step 5), which writes a recoverable marker first.
`../spec/LITE_PLANS.md` is normative for representation, promotion and recovery.

> Steps 4.1–4.3 were the refined-draft flows. They were removed in 2.4.0; the
> numbering below is unchanged so existing cross-references keep resolving.

#### 4.4 Create Final Plan (Full representation)

Reached from Step 4.0 when the format is Full — by the rubric, or by an explicit
`full` preference, or by a guided promote choice. The folder, `manifest.json` and
the analysis written in Step 4.0 are **reused**, not recreated: this step adds
the task files and switches the README to the task-file representation for the
same task IDs. It is never an entry point of its own.

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
   rigor tier, `spec_version` **"4.0.0"**, `plan_format` **"full"**, `task_count`
   = the number of task files this materialization will write (Final Review
   included), creating agent — atomically (write-temp-then-rename), valid against
   `../spec/schema/plan-manifest-v2.schema.json` (closed schema), written once,
   never edited after. When Step 4.0 already wrote the manifest, keep it: only a
   manifest created with `plan_format: "lite"` that has **not** yet been
   materialized may be written with `"full"` here. Plans created under 2.3.0 and
   earlier keep their v1 schema URL and remain conformant.
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
   explicit request recorded in the plan guidelines counts); where a reporting
   channel is configured (`AGENT_PROTOCOL.md` §5), send the completion report
   best-effort; otherwise skip it.

   **Local review step (required):** read
   [`addon-augmentations.md`](addon-augmentations.md) (this directory) and add
   its AI Diff Reviewer post-existing-checks step to the Final Review task's
   security pass — it applies to every 2.3.0 plan. When the target repo lacks
   `.agents/skills/ai-diff-reviewer/` or an extension file at one of the three
   recognized paths, the step's degradation clause (record a `local reviewer
   not installed` finding) and carry it into the completion report. Installation
   belongs to onboarding or an explicit addon invocation; Final Review never
   surprise-bootstraps it. Do not omit the step.

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
   `pending`, empty gates, `task_count` equal to the manifest's, `format: "full"`,
   `materialization: "ready"`, `approval` (`"pending"` guided / `"pre_approved"`
   trust), `promotion: null`, and one `locator` per task —
   `{ "kind": "file", "value": "N.task_….md" }`. Atomically
   (write-temp-then-rename); valid against
   `../spec/schema/plan-state-v2.schema.json` (no extra fields — the schema is
   closed). Existing v1 plans keep `file` and their v1 schema URL. `manifest.json` was written in item 1
   and is not touched here.
8. **README.md** (content — written as the skeleton in item 1b) — Goal; Context; Plan Variables (incl. `**Standard:** DWP
   spec 4.0.0` and `**Plan Format:** Full`, the tier and why, and in trust mode `Pre-approved for unattended
   execution: yes (trust)`); Global Guidelines (incl. an explicit Executive
   Report request if the user made one); Task List with `[ ]` checkboxes + links
   (the Final Review last); Execution Rules; Skills & Agents Used; Plan Status /
   Notes; Analysis Outputs table (`SKILLS_CANDIDATES.md` — every task;
   `SECURITY_REVIEW.md` — Final Review; `EXECUTIVE_REPORT.md` — optional, on
   request); Quick Reference to `PROMPTS.md`. Add the note: *"Every plan ends
   with a single Final Review (security pass, final-state validation, skills
   reconciliation). Skills decisions are made inside each task; the Executive
   Report is optional and offered at completion. Auto-generated by
   `/dwp-create`."* For a **long Full plan** (20 or more task files), the
   README also carries the optional **Stage Gates** table
   (`../guide/authoring.md` §4.3) — one named checkpoint per coherent phase,
   placed adjacent to Execution Rules. Lite plans never carry it, and shorter
   Full plans omit it by default.
9. **Flip the README status (last write):** replace `Plan Status: materializing`
   with `Plan Status: 0/N completed` where N equals `manifest.task_count` and
   the number of task files on disk. Only now is the plan complete.

**Conditional branches:** if Step 2.6 fired, apply the **orchestrator
additions** in [`orchestrator.md`](orchestrator.md); if Step 2.10 fired, apply
the **team-agents metadata** and, for 5+ user task files where team agents are
available, the **accelerated generation** in [`team-agents.md`](team-agents.md).
Neither branch changes the sequential path: every task must work sequentially,
and the Final Review is always sequential.

#### 4.5 Plan-Quality Check (both modes and both formats — before reporting success)

**For a Lite plan**, verify and fix before continuing:
- **Requirements → tasks → gates** (Step 3.7) hold for the task records.
- Task IDs are contiguous `1..N`; each `{#task-N}` anchor occurs exactly once;
  every Task List link resolves to its anchor; the Final Review is task `N` and
  the only final task.
- Every task record has a Goal, a Touched Surface, Acceptance Criteria, a
  runnable Validation gate and a completion-log placeholder. No task was padded
  in to reach a count.
- `manifest.json` validates against the v2 manifest schema with
  `plan_format: "lite"`; `state.json` validates against the v2 state schema, its
  `task_count` and `completed_count` agree with the records, every locator is
  `inline` pointing at that task's anchor, and its `approval` matches the README's
  `Approval` row.
- The README carries the Format Decision, `Plan Format`, `Materialization` and
  `Approval`, no longer says `materializing`, and no placeholder text remains.
- **No file under `.dwp/drafts/` was written.**

**For a Full plan**, verify and fix before continuing:
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

For a **Lite** plan, report success and the location `.dwp/plans/PLAN_{name}/`,
state the format and why it was chosen, and name the execute command. In guided
mode the plan is still `Approval: pending` — say so, and that executing it is
what approves its current scope. In trust mode state that it is ready and
pre-approved for unattended execution. Then offer: (1) execute now → run the
**Execute** sub-skill (`../execute/SKILL.md`); (2) review the README first, then
ask again; (3) done for now → `/dwp-execute {name}` later (or
`/dwp-execute {name} trust` to run to the end without questions); (4) promote to
Full instead → `/dwp-refine promote {name}`. **Return control either way**:
`create` finishes by handing off, never by starting the work — including in
trust mode.

For a **Full** plan, report success and the location
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
- **Single artifact:** the plan folder is the only thing `create` produces.
  There is no draft file and no `.dwp/drafts/` directory in 2.4.0.
- **One final task:** `{N}.task_final_review.md`. Never generate
  `task_skills_agents_discovery` or `task_executive_report` files for a new plan
  (plans from earlier versions that have them are executed as recorded —
  `../spec/DWP_SPECIFICATION.md` §6.5).
- **Reference:** follow `../guide/authoring.md` and `../guide/structure.md`; orchestrator → `../guide/orchestrator.md` §13; team agents → `../guide/team-agents.md` §14.
- **Archetypes:** orchestrator support assumes the orchestrator-hub archetype
  (sub-repos under `repositories/`); an individual repo creates standard plans.
  See `../shared/adaptation.md`.
