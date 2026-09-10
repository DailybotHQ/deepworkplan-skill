# DeepWorkPlan Guide — Structure, Naming and Lifecycle

> Part of the DeepWorkPlan methodology guide. The routing index is
> [`GUIDE.md`](GUIDE.md); read only the guide files your flow names.

## 1. Top-Level Folder Structure

All deep-work plan **outputs** (plans and drafts) live under a single gitignored
`.dwp/` directory at the repository root. The methodology guide and example
prompts ship **inside the DeepWorkPlan skill** (`skills/deepworkplan/guide/` and
`skills/deepworkplan/examples/`), not under `.dwp/` — they are reference content,
not per-run output.

```text
.dwp/                                          ← gitignored output root
├─ drafts/                                      ← create-flow refined drafts workspace
│   └─ PLAN_{plan_title}_draft_refined.md       ← single refined draft (see §1.2)
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
      ├─ 1.task_{task_title}.md            ← task 1 (detailed, single-task focus)
      ├─ 2.task_{task_title}.md            ← task 2
      ├─ ...
      └─ N.task_final_review.md            ← MANDATORY: the single final task
```

> Plans created under earlier versions end with `N-2.task_security_review.md`,
> `N-1.task_skills_agents_discovery.md` and `N.task_executive_report.md`; that
> shape stays conformant and is executed as recorded (`spec/DWP_SPECIFICATION.md` §6.5).

> The guide (`guide/GUIDE.md` routing index plus its flow-scoped files) and example prompt templates
> (`examples/CREATE_PLAN.md`, `examples/PROMPTS_TEMPLATE.md`, the
> `examples/ORCHESTRATOR_TASK_TEMPLATE_*.md` files, etc.) live inside the
> installed skill so the runtime agent can read them in any repo.

### 1.1. Git ignore rule

The `.dwp/` directory (containing `drafts/` and `plans/`) is **disposable** and
should be git-ignored in its entirety.

Add (or ensure) in `.gitignore`:

```gitignore
.dwp/
```

**Important:**
Everything under `.dwp/` is **temporary execution work**, not permanent
repository content. The stable methodology documentation lives inside the
DeepWorkPlan skill (`guide/`, `examples/`).

### 1.2. Single-step refined draft (vs the legacy two-step)

DeepWorkPlan v2 produces **one** reviewable draft artifact: the **refined
draft**, written directly to `.dwp/drafts/PLAN_{name}_draft_refined.md`. There is
**no** separate raw-draft file. This replaces the legacy two-step flow that first
generated `PLAN_{name}_draft.md` and then refined it into
`PLAN_{name}_draft_refined.md`. See `create/SKILL.md` for the create flow and
`refine/SKILL.md` for editing the refined draft in place.

---

> **Mode-aware since spec 2.3.0.** Guided mode writes the refined draft above and materializes after approval. Materialization is resumable at any point: `manifest.json` first, then a README skeleton with the intended task list and `Plan Status: materializing`, then `analysis_results/PLAN_ANALYSIS.md`, then the task files; the status line is flipped to `0/N completed` as the last write (`spec/DWP_SPECIFICATION.md` §3). **Trust mode materializes `.dwp/plans/PLAN_{name}/` directly** — no draft file — while still running the requirements analysis and a plan-quality check; the approved outline lives in the plan README, and a plan created with `trust` is pre-approved for unattended execution (`spec/DWP_SPECIFICATION.md` §3). Explicit `refined-draft` / `from-refined-draft` requests still produce a draft in either mode.

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
