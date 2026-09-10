---
name: deepworkplan-refine
description: Refine a Deep Work Plan draft or modify an existing final plan — add, edit, split or reorder tasks, update the README, convert a draft, or explicitly migrate a legacy plan — keeping README links, task IDs, dependencies and the state layer synchronized and never silently rewriting completed work. Use when the developer wants to adjust scope, tasks, or details of a draft in .dwp/drafts/ or a plan in .dwp/plans/.
version: "2.17.1"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
---

# DeepWorkPlan — Refine

Polish a **refined draft** or modify an **existing final plan** (add / edit /
split / reorder tasks, update the README, convert a draft to a plan, or — only
on explicit request — migrate a legacy plan to the current standard).

> **Single-step change (vs legacy):** there is exactly one draft artifact — the
> **refined draft** at `.dwp/drafts/PLAN_{name}_draft_refined.md`. Refining a
> draft **edits it in place** (or converts it into a final plan). The legacy
> distinction where "refine the draft" produced a separate `_refined` file from a
> raw draft is gone, and the old three-option "Refine / Convert / Both" collapses
> to **Edit in place** or **Convert to plan**. In trust mode there may be no draft
> at all (`../create/SKILL.md` Step 4.2); refine then works on the plan.

## Shared resources (read these)

- [`../shared/dwp-paths.md`](../shared/dwp-paths.md) — drafts at `.dwp/drafts/`,
  plans at `.dwp/plans/PLAN_{name}/`.
- [`../shared/context.sh`](../shared/context.sh) — resolve `dwp_dir`.
- **Guide (essential — read for this flow):** [`../guide/authoring.md`](../guide/authoring.md) (plan README §4, task-file anatomy §5 incl. the Touched Surface, mandatory elements) and [`../guide/structure.md`](../guide/structure.md) (§1–§2 naming and folders).
- **Guide (conditional — read only when the trigger fires):** [`../guide/orchestrator.md`](../guide/orchestrator.md) / [`../guide/team-agents.md`](../guide/team-agents.md) only for plans that use them; [`../guide/execution.md`](../guide/execution.md) §6.1 when editing the Final Review (or a legacy plan's final tasks). Do not read other guide files for this flow; [`../guide/GUIDE.md`](../guide/GUIDE.md) is the routing index, consulted only when a section is not named above.
- **Shared contract (conditional — read the named steps only when the trigger fires):** [`../create/SKILL.md`](../create/SKILL.md) Steps 3.5–3.7 and 4.4–4.5 when converting a draft, adding or splitting a task, completing a partial materialization, or migrating — the **one** contract for task anatomy, gate selection, the Final Review, the ledger, the write order and the plan-quality check (refine never has a second template); [`../spec/PLAN_STATE.md`](../spec/PLAN_STATE.md) §5–§6 when the plan carries `state.json` (regeneration, evidence invalidation) or on `migrate` (the declared-migration line).
- [`../examples/CREATE_PLAN.md`](../examples/CREATE_PLAN.md) — prompt patterns for
  professional rewriting.

## Parameter Support

| Parameter | Description | Example |
|-----------|-------------|---------|
| (none) | Interactive — choose draft or plan | `/dwp-refine` |
| `{draft_filename}` | Refine a specific refined draft | `/dwp-refine PLAN_x_draft_refined.md` |
| `latest` | Refine the most recent refined draft | `/dwp-refine latest` |
| `plan {plan_name}` | Modify an existing final plan | `/dwp-refine plan auth_refactor` |
| `plan latest` | Modify the most recent plan | `/dwp-refine plan latest` |
| `migrate {plan_name}` | **Explicit** migration of a legacy plan (three final tasks) to the current standard — the only way a plan changes standard | `/dwp-refine migrate auth_refactor` |

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`.

**Writes:** edits confined to the target plan's files under `.dwp/drafts/` or
`.dwp/plans/PLAN_{name}/` — task content, ordering, the README's task list and
counts, `PROGRESS.md`, and the **regenerated** `state.json` — kept mutually
consistent. Deleting a completed task, dropping the Final Review (or a legacy
plan's final tasks), or invalidating completed evidence requires explicit
developer confirmation. `manifest.json` is **never** rewritten
(`../spec/PLAN_STATE.md` §2).

**It MUST NOT:** touch source files, write outside `.dwp/`, weaken a task's
acceptance criteria or validation gate without saying so in the diff summary,
change a plan's standard without an explicit `migrate` request, or commit/push
anything (refinement output stays uncommitted working state).

## Workflow

### Step 0 — Determine Target Type
- No parameters → Step 1 (interactive).
- A draft filename / `latest` → Step 2 (Draft Workflow).
- `plan {name}` / `plan latest` → Step 3 (Plan Workflow).
- `migrate {name}` → Step 4 (Explicit Migration).

### Step 1 — Interactive Selection
Ask whether to refine **a draft** (polish or convert to a final plan) or **an
existing final plan** (add / edit / split / reorder tasks, adjust context). Route
to Step 2 or Step 3. Mention `migrate` only if the selected plan is legacy.

## Draft Workflow

### Step 2 — Select and Refine the Refined Draft

**2.1 Select.** If not specified, list `*.md` files in `.dwp/drafts/` (excluding
README) and let the user pick by number, filename, or `latest`.

**2.2 Read** the refined draft fully: objective, context, tier, tasks, plan name,
structure.

**2.3 Choose action:**
1. **Edit the refined draft in place** — improve/polish the prompt; rewrite
   professionally following `../examples/CREATE_PLAN.md`; expand and detail all
   sections; **save back to the same** `.dwp/drafts/PLAN_{name}_draft_refined.md`
   (no new `_refined` file).
2. **Convert to a final plan** — extract plan info; run the requirements →
   tasks → gates check (`../create/SKILL.md` Step 3.7); create the plan folder
   and all files exactly as `../create/SKILL.md` Step 4.4 does (ten-section task
   files with Touched Surface and selected gates, the single
   `{N}.task_final_review.md` last, `PROMPTS.md`, the bounded `PROGRESS.md`
   index, `analysis_results/SKILLS_CANDIDATES.md`, `manifest.json` with
   `spec_version` "2.3.0" + `state.json`, README **last** with the Analysis
   Outputs section and the Final Review note); run the plan-quality check
   (Step 4.5); then offer to execute via the **Execute** sub-skill
   (`../execute/SKILL.md`). No report task is ever generated.

## Plan Workflow

### Step 3 — Select and Modify a Final Plan

**3.1 Select.** If not specified, list `PLAN_*` folders in `.dwp/plans/`; pick by
number, name, or `latest`. Normalize the `PLAN_` prefix.

**3.2 Read and classify.** Read the plan README, the task files, `PROGRESS.md`,
and — when present — `manifest.json` and `state.json`. Establish:
- **The plan's standard** (`../spec/PLAN_STATE.md` §6.1): a declared
  `**Standard:**` line in the README wins; otherwise `manifest.spec_version`;
  otherwise (no manifest) the shape of its files. **New shape** = a single
  `{N}.task_final_review.md` last. **Legacy shape** = three final tasks
  (`security_review` → `skills_agents_discovery` → `executive_report`). Refine
  **retains the plan's shape**; only Step 4 changes it.
- **Partial materialization**: a folder whose `README.md` is missing, says
  `Plan Status: materializing`, or links a task file that does not exist is an
  interrupted `create`. Read `manifest.json` and the README task list to report
  the intended shape against what exists; offer to **complete** it (regenerate
  only the missing files from `analysis_results/PLAN_ANALYSIS.md` per
  `../create/SKILL.md` Step 4.4, leaving existing task files and the manifest
  intact, then flip the status line) or **discard** it (explicit confirmation).
  Never overwrite unrelated artifacts.
- Objective, context, guidelines, tasks and their `[x]`/`[ ]` status, and any
  in-progress checkpoint.

**3.3 Show current state** — objective, standard (new / legacy), the task list
with status, and the location `.dwp/plans/PLAN_{name}/`.

**3.4 Choose modification:** Add task(s) / Edit task / Split task / Reorganize /
Update README / View task details / Done.

**3.5 Execute modifications**

**Final-task protection (lifecycle-aware, applies throughout):**
- **New shape:** the **Final Review** must remain the **last** task. It **CANNOT
  be deleted or reordered**, but it **CAN be edited** (e.g. to add plan-specific
  review criteria). If the user tries to delete or move it, explain: "The Final
  Review is the mandatory final task. It can be edited but not deleted or
  reordered."
- **Legacy shape:** Security Review stays third-to-last, Skills & Agents
  Discovery second-to-last, Executive Report last; same rule — editable, never
  deleted or reordered — unless the user runs an explicit `migrate` (Step 4).
- Insert positions are therefore `1..N-1` for a new-shape plan and `1..N-3` for a
  legacy plan; `before-final` always means "immediately before the first final
  task of this plan's shape".

- **Add task(s):** ask for the insert position (a number in the range above,
  `before-final`, or `after {k}`), gather task details, create the task file with
  the full standard structure (`../create/SKILL.md` Step 4.4 item 2: ten sections
  incl. Touched Surface, selected gates, the skills-decision checklist step, the
  `Skills disposition:` / `Gate record:` log lines), renumber subsequent files,
  and run **3.6 Synchronize**.
- **Edit task:** show current content; apply changes to title / instructions /
  acceptance criteria / Touched Surface / validation / everything. Final tasks are
  editable. Then run **3.7 Invalidate affected evidence** and **3.6 Synchronize**.
- **Split task (unfinished, oversized):** split task `k` into two or more tasks
  `k, k+1, …` such that **every requirement, acceptance criterion, constraint and
  reference of the original lands in exactly one child** — nothing is dropped or
  summarized. Distribute the original's Touched Surface, Read Before Starting
  pointers and Outputs to the child that owns them; a child that consumes another
  child's output names it in Read Before Starting. Carry any already-recorded
  evidence (a partial Completion & Log, a checkpoint, a passing gate) into the
  child that owns that work, verbatim, and leave a one-line pointer in the other
  children. A `[x]` task is never split without explicit confirmation (it is
  completed work). Renumber and run **3.6 Synchronize**.
- **Reorganize:** move / merge / delete. Renumber files as needed and **always
  keep the plan's final task(s) last**. Warn before deleting a completed `[x]`
  task (explicit confirmation). Merging keeps every requirement of both tasks.
- **Update README:** objective / context / global guidelines / execution rules
  (including an explicit Executive Report request, which the Final Review honors).
- **View task details:** display the full task file.
- **Done:** run **3.6 Synchronize** once more, report modifications (what was
  added / edited / split / reordered, which evidence was invalidated and why),
  and offer to execute/resume via the **Execute** (`../execute/SKILL.md`) or
  **Resume** (`../resume/SKILL.md`) sub-skill.

**3.6 Synchronize (after every modification — the plan must never be left
inconsistent):**
- README: task list entries, links (`N.task_{title}.md`), the `Plan Status:
  X/N` count, the Analysis Outputs table, and any Team Agents Configuration
  tables (Parallel Task Groups / roles) that name task numbers.
- Task files: numbers in file names and titles; `Read Before Starting`
  references to renumbered tasks; Team Agents Metadata (`Can Run With`,
  `Blocks`); `Blocks`/`Depends` wording that names a task.
- `PROGRESS.md`: the active task / next action, and a dated entry describing
  the refinement (what changed, what was invalidated).
- `state.json` (when present): **regenerate it from the markdown**
  (`../spec/PLAN_STATE.md` §5) — one entry per task file, ids and files matching
  the disk, `task_count` = current number of task files, `completed_count` =
  README `[x]` count. Entries of completed tasks keep their `completed_at`,
  `commit`, `gates` and `outcome` (re-keyed if renumbered). Write atomically.
  `manifest.json` is **not** touched: its `task_count` is the count at creation;
  the live count is `state.json.task_count`.
- Never leave a README `[x]` for a task file that no longer exists, or a task
  file with no README entry.

**3.7 Invalidate affected evidence (when requirements change):** when an edit
changes a task's acceptance criteria, scope, Touched Surface or gate — or
changes an upstream task whose outputs a **completed** task consumed — list the
affected completed tasks and, with the user's explicit confirmation, mark them
for re-validation: README checkbox back to `[ ]` with a `(re-validate:
requirements changed by refine on YYYY-MM-DD)` note, `state.json` entry status
`pending` with its gate records **kept** and their `evidence` prefixed
`invalidated by refine YYYY-MM-DD:`, and an **appended** "Invalidated" note in
the task's Completion & Log. Completed logs, commits and outcome records are
**never deleted or rewritten** — the executor re-runs the gates and re-marks the
task (`../spec/PLAN_STATE.md` §5.1). Without confirmation, record the concern in
`PROGRESS.md` and change nothing.

## Explicit Migration

### Step 4 — Migrate a Legacy Plan (only on `migrate {name}`)

Migration is the **only** way a plan changes standard, and it happens **only**
when the developer asks for it explicitly (`../spec/DWP_SPECIFICATION.md` §6.5,
`../spec/PLAN_STATE.md` §6.1). Never suggest it as a side effect of another edit.

1. **Classify** (Step 3.2). If the plan is already at the current standard, say
   so and stop.
2. **Preserve completed work.** Any `[x]` task — including a legacy final task
   that has already run — is left exactly as it is. Only **unstarted** tasks may
   take the new shape.
3. **Reshape the ending.** If none of the three legacy final tasks has started,
   replace them with a single `{N}.task_final_review.md` (content per
   `../create/SKILL.md` Step 4.4 item 3, incl. the security pass, final-state
   validation, skills reconciliation, completion and report offer). If the
   Security Review already ran, keep it and replace only the two unstarted
   closing tasks with the Final Review's remaining parts (b)–(d). Record the
   decision in `PROGRESS.md`.
4. **Add the new-shape elements** to unstarted tasks and to the plan: a Touched
   Surface (planned surface, risk class, selected gate — derived from
   `docs/TESTING_GUIDE.md`, or the full-suite fallback where the repository
   documents no scoped invocation) on every unstarted behavior-changing task; the
   skills-decision checklist step and the `Skills disposition:` / `Gate record:`
   log lines; `analysis_results/SKILLS_CANDIDATES.md`; the Analysis Outputs
   table rows; the Final Review note in the README.
5. **Declare it.** Add to the README Plan Variables the line
   `**Standard:** DWP spec 2.3.0 (migrated from A.B.C on YYYY-MM-DD — <reason>)`
   and a dated entry in `PROGRESS.md`. Leave `manifest.json` untouched (creation
   provenance).
6. **Synchronize** (Step 3.6) and report: what was reshaped, what was preserved,
   what the executor will do differently from here.

## Important Notes
- **Preserve completed work:** never alter `[x]` tasks unless explicitly asked;
  invalidation (3.7) marks them for re-validation, it does not rewrite them.
- **Renumber carefully:** keep task file numbers, README references, dependency
  pointers, team-agents metadata and `state.json` ids in sync (3.6).
- **Maintain consistency:** task files follow the standard structure
  (`../guide/authoring.md` §5; the shared contract in `../create/SKILL.md`).
- **One shape per plan:** refine keeps the plan's standard; `migrate` is the only
  exception and is explicit.
- **No mandatory report:** refine never adds an Executive Report task; it may
  record an explicit report request in the README guidelines.
- **Git ignore:** everything under `.dwp/` is git-ignored.
- **One draft artifact:** refining a draft edits
  `PLAN_{name}_draft_refined.md` in place; there is no separate raw draft.

## Error Handling
- Draft/plan not found → list available options and let the user select.
- Partial materialization (no `README.md`, `Plan Status: materializing`, or a dangling task link) → offer complete / discard (3.2).
- Task number out of range → show the valid range for this plan's shape and re-ask.
- Deleting or splitting a completed `[x]` task → confirm explicitly first.
- Plan has work in progress (a checkpoint or an `in_progress` task) → warn about
  impact; suggest finishing the current task first; never edit the in-progress
  task's evidence.
- `migrate` on a plan already at the current standard → report and stop.
