# DeepWorkPlan Guide — Structure, Naming and Lifecycle

> Part of the DeepWorkPlan methodology guide. The routing index is
> [`GUIDE.md`](GUIDE.md); read only the guide files your flow names.

## 1. Top-Level Folder Structure

All deep-work plan **outputs** live under a single gitignored
`.dwp/` directory at the repository root. The methodology guide and example
prompts ship **inside the DeepWorkPlan skill** (`skills/deepworkplan/guide/` and
`skills/deepworkplan/examples/`), not under `.dwp/` — they are reference content,
not per-run output.

```text
.dwp/                                          ← gitignored output root
└─ plans/                                        ← generated, per-plan folders
   └─ PLAN_{plan_title}/
      ├─ README.md                         ← plan overview, task index
      ├─ PROMPTS.md                        ← ready-to-use prompts for this plan
      ├─ PROGRESS.md                       ← running progress summary (updated each task)
      ├─ manifest.json                     ← plan identity, written FIRST (intended task count; never edited)
      ├─ state.json                        ← live state projection (rewritten at protocol points)
      ├─ analysis_results/                 ← analysis outputs & reports
      │   ├─ PLAN_ANALYSIS.md              ← the recorded requirements analysis (written before any task file)
      │   ├─ SKILLS_CANDIDATES.md          ← task-local skills decisions (ledger, by stable ID)
      │   ├─ SECURITY_REVIEW.md            ← written by the Final Review (security pass + final-state validation)
      │   └─ EXECUTIVE_REPORT.md           ← OPTIONAL — generated only on request after completion
      ├─ 1.task_{task_title}.md            ← task 1 — FULL plans only
      ├─ 2.task_{task_title}.md            ← task 2 — FULL plans only
      ├─ ...
      └─ N.task_final_review.md            ← MANDATORY: the single final task
```

> A **Lite** plan has the same folder minus the `N.task_*.md` files: its task
> records live inline in `README.md` behind `{#task-N}` anchors, and the Final
> Review is the last of them (`spec/LITE_PLANS.md`).

> Plans created under earlier versions end with `N-2.task_security_review.md`,
> `N-1.task_skills_agents_discovery.md` and `N.task_executive_report.md`; that
> shape stays conformant and is executed as recorded (`spec/DWP_SPECIFICATION.md` §6.5).

> The guide (`guide/GUIDE.md` routing index plus its flow-scoped files) and example prompt templates
> (`examples/CREATE_PLAN.md`, `examples/PROMPTS_TEMPLATE.md`, the
> `examples/ORCHESTRATOR_TASK_TEMPLATE_*.md` files, etc.) live inside the
> installed skill so the runtime agent can read them in any repo.

### 1.1. Git ignore rule

The `.dwp/` directory (containing `plans/`) is **disposable** and
should be git-ignored in its entirety.

Add (or ensure) in `.gitignore`:

```gitignore
.dwp/
```

**Important:**
Everything under `.dwp/` is **temporary execution work**, not permanent
repository content. The stable methodology documentation lives inside the
DeepWorkPlan skill (`guide/`, `examples/`).

### 1.2. Lite-first plan materialization

New plans start as ready, executable **Lite** folders under `.dwp/plans/`. Lite keeps the normal README, manifest, state,
prompts, progress and analysis folders, but stores small task records inline in
the README. Guided creation asks whether to retain Lite or promote it to Full;
trust creation makes that decision from the recommendation or an explicit
boundary option. `lite` and `full` may be combined with `trust`/`auto` at either
edge of the command context. `LITE_PLANS.md` is authoritative.

### 1.3. Drafts were removed in 2.4.0

There is no draft artifact and no `.dwp/drafts/` directory. Earlier versions
staged a **refined draft** at `.dwp/drafts/PLAN_{name}_draft_refined.md` for
review before materializing a plan; the Lite plan replaces it, and is already
executable rather than merely reviewable. The `refined-draft`,
`from-refined-draft` and `from` create parameters, and refine's draft workflow,
are gone. A `.dwp/drafts/` folder left by an earlier version is inert — DWP
neither reads nor writes it, and the developer may delete it.

---

> **Lite-first since spec 2.4.0.** Guided and trust modes materialize a ready
> Lite folder, run the same requirements analysis and quality check, then retain
> Lite or promote safely to Full.

## 2. Naming Conventions

### 2.1. Plan folders

Each plan folder must be named:

```text
PLAN_{plan_title}
```

Where:

- `{plan_title}` is:
  - Lowercase
  - Snake case
  - Short and descriptive

**Examples:**

- `PLAN_ui_showcase_expansion`
- `PLAN_refactor_checkin_engine`
- `PLAN_docs_reorganization`
- `PLAN_ai_dev_kit_cleanups`

### 2.2. Task files

Each task file inside a plan folder is named:

```text
1.task_{task_title}.md
2.task_{task_title}.md
3.task_{task_title}.md
```

Where:

- The **numeric prefix** defines the **strict execution order**.
- `{task_title}` is a short description of the task focus.

**Examples:**

- `1.task_create_buttons_component_page.md`
- `2.task_add_integration_tests_for_checkins.md`
- `3.task_update_checkins_docs.md`

Agents must **not** change the order or numbering once created.

---

## 3. Purpose of This System

This system exists to:

- Break a large objective into **small, atomic tasks**
- Ensure the agent works on **only one task at a time**
- Provide a **plan-level overview** (`PLAN/README.md`)
- Provide **per-task deep prompts** (`N.task_*.md`)
- Support **long-running / deep-work sessions** (multi-hour / overnight)
- Avoid clutter in the main repo (plans are temporary)
- Make execution auditable and reproducible

---

## 10. Cleanup and Lifecycle

- Plan folders under `.dwp/plans/` are **temporary**.
- After a plan is fully executed and merged:
  - The folder may be archived or deleted.
  - Any important learnings should be summarized in a more permanent doc if needed.
- The main repo remains clean and lightweight.

---
