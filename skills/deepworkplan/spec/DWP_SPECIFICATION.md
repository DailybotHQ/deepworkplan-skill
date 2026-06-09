# DWP_SPECIFICATION.md — Deep Work Plan Specification

## Abstract

This document specifies the **Deep Work Plan (DWP)** workflow: a framework-agnostic,
agent-agnostic methodology for AI coding agents to execute complex, multi-step work
reliably over hours or days. A Deep Work Plan is a directory of markdown files — a
plan overview, per-task instruction files, a running progress log, and utility
prompts — that together hold all state an agent needs to begin, continue, and
complete a body of work. Plans are single-task focused, validation-first,
git-native, and resume-safe.

The DWP system in v2 is delivered as an **installable skill** (`deepworkplan`,
modeled on the `dailybot` skill in `repositories/agent-skill`), not an embedded
per-repo folder. Its outputs land in a gitignored **`.dwp/`** directory at repo
root. This document is implementation-independent; `deepworkplan` is the reference
implementation.

This specification applies to **all three archetypes** (`ARCHETYPES.md`): the
individual repo (the default case), the orchestrator hub, and the agent
workspace. Archetype-specific behavior is called out inline, especially in §8
(orchestrator) and §10 (state layer, required where git is absent).

---

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 2.2.0 |
| **Status** | Stable |
| **Supersedes** | `PLAN_build_deepworkplan_brand/.../deepworkplan/spec/DWP_SPECIFICATION.md` (v1.0.0) |
| **Companions** | `DOCUMENTATION_STANDARD.md`, `AGENT_PROTOCOL.md`, `ARCHETYPES.md`, `ADDONS.md`, `PLAN_STATE.md` |
| **License** | MIT |

> **Additive in 2.2.0.** Four additive capabilities, no breaking changes:
> (1) the **machine-readable plan state layer** (`manifest.json` + `state.json`,
> §10, normatively defined in `PLAN_STATE.md`); (2) **proportional rigor tiers**
> (micro / standard / deep, §11); (3) the optional **Delta section** in the task
> anatomy for brownfield behavior changes (§5); and (4) §5.3 is promoted to the
> named, citable **DWP Resume Protocol**. Existing 2.1.0 plans remain conformant.

> **Divergence from v1 (overview).** Three breaking changes drive the major bump:
> (1) the **create flow is single-step** — one refined draft, dropping the v1
> draft → refined two-step (`RECONCILIATION.md` divergence #3); (2) plan output
> relocates to **`.dwp/`** at repo root, replacing
> `.agent_commands/agent_deep_work_plans/results/plans/` (divergence #2); (3) the
> system is an **installed skill**, not an embedded folder (divergence #1). The
> task anatomy, validation gates, completion protocol, mandatory final tasks,
> orchestrator, and team-agents model are **kept** from v1 with path/flow edits.

---

## 1. Conventions and Terminology

### 1.1. RFC 2119 Keywords

The keywords **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be
interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

### 1.2. Terms

| Term | Definition |
|------|-----------|
| **Plan** | A directory of markdown files specifying an objective and its tasks. Named `PLAN_{snake_case_name}/`. |
| **Task** | An atomic unit of work, defined in `{N}.task_{title}.md`. |
| **Refined draft** | The single reviewable artifact produced by `create`, written to `.dwp/drafts/`. |
| **Plan README** | The `README.md` inside a plan; source of truth for "what is done". |
| **Mandatory final tasks** | The two tasks every plan ends with: Skills & Agents Discovery, then Executive Report. |
| **Orchestrator plan** | A plan in an orchestrator hub that creates and coordinates **child DWPs** in sub-repos. |
| **`.dwp/`** | The gitignored repo-root output directory: `.dwp/plans/`, `.dwp/drafts/`. |

---

## 2. The `.dwp/` Output Convention

- A repository using the DWP workflow **MUST** locate all plans and drafts under a
  single repo-root directory named `.dwp/`:

  ```
  .dwp/
  ├── plans/      ← PLAN_{name}/ directories (executed plans)
  └── drafts/     ← {name}_draft_refined.md (the create-flow artifact)
  ```

- `.dwp/` **MUST** be git-ignored (added to the repo's `.gitignore`). Plan
  execution artifacts are working state, not tracked deliverables.
- The legacy `.agent_commands/agent_deep_work_plans/results/` tree **MUST NOT** be
  used by v2 plans. On migration, existing plans **MUST** be relocated or archived,
  and **MUST NOT** be blind-deleted (`ORCHESTRATOR_MANIFEST.md` key decision).
- A plan **MUST** be located at `.dwp/plans/PLAN_{name}/`.

> **Divergence from v1.** v1's normative spec mandated
> `.agent_commands/agent_deep_work_plans/results/plans/PLAN_{name}/` even though the
> v1 `dwp-create` command and INIT hint already used `.dwp/`. v2 makes the spec and
> the commands consistent on `.dwp/` (`RECONCILIATION.md` divergence #2).

---

## 3. The Single-Step Refined-Draft Create Flow

- The `create` flow **MUST** produce exactly **one** artifact for user review: a
  **refined draft** written to `.dwp/drafts/{name}_draft_refined.md`.
- The flow **MUST NOT** produce an intermediate non-refined draft as a separate
  reviewable step. The legacy `[1/3] Creating draft → [2/3] Refining draft`
  sequence is removed.
- The flow **SHOULD** gather information, then directly synthesize the refined
  draft; the user reviews and approves that single artifact before the plan is
  materialized into `.dwp/plans/PLAN_{name}/`.
- The refined draft **MUST** contain enough structure (goal, context, variables,
  task outline, archetype) for the user to approve or request changes in one pass.

> **Divergence from v1.** v1's `dwp-create` was explicitly two-step. v2 collapses
> it to a single refined draft (`RECONCILIATION.md` divergence #3; this very plan's
> own refined draft is the worked example).

---

## 4. Plan Folder Structure

A conformant plan directory **MUST** contain:

```text
.dwp/plans/PLAN_{name}/
├── README.md                              ← overview, task list, rules, status (source of truth)
├── PROMPTS.md                             ← copy-paste execute / resume / status prompts
├── PROGRESS.md                            ← running narrative, one entry per completed task
├── analysis_results/                      ← task-produced artifacts (MAY start empty)
│   └── EXECUTIVE_REPORT.md                ← written by the final mandatory task
├── 1.task_{title}.md                      ← first user-defined task
├── …
├── {N-1}.task_skills_agents_discovery.md  ← mandatory: second-to-last
└── {N}.task_executive_report.md           ← mandatory: last
```

- Plan names **MUST** follow `PLAN_{snake_case_name}` (lowercase, underscore-separated, 2–5 words).
- `README.md`, `PROMPTS.md`, `PROGRESS.md`, and `analysis_results/` **MUST** all be present.
- At least one user-defined task plus the two mandatory final tasks **MUST** be present.

The plan `README.md` **MUST** contain: title + goal; context; plan variables (if
the tasks reference `{{...}}`); global guidelines; a task list with checkboxes and a
`Plan Status: X/N completed` count; execution rules; and an analysis-outputs table.
The checkbox list is the resume checkpoint: `[x]` means complete-and-committed, and
the agent **MUST** trust `[x]` marks without re-verifying.

---

## 5. Task File Anatomy — The 9 Sections

Each `{N}.task_{title}.md` **MUST** contain the following nine sections. Heading
text **MAY** vary; the semantic content **MUST** be present and in this order.

| # | Section | Requirement |
|---|---------|-------------|
| 1 | **Title** — `# Task {N}: {Title}` | **MUST** |
| 2 | **Context** — task-specific background; the agent **MUST** be able to start from this section alone. | **MUST** |
| 3 | **Read Before Starting** — files the agent **MUST** read first, each with why it matters (including re-anchoring to the plan README §Goal). | **MUST** |
| 4 | **Goal** — 1–2 sentences, unambiguous and testable. | **MUST** |
| 5 | **Instructions** — numbered, concrete steps, including an explicit **re-anchor** step (re-read the plan README §Goal at task start). Vague steps **MUST NOT** appear. | **MUST** |
| 6 | **Acceptance Criteria** — a verifiable checkbox list; the task **MUST NOT** be marked complete until every box can honestly be checked. | **MUST** |
| 7 | **Outputs** — table of files the task produces with paths (under `analysis_results/` or source). | **MUST** when the task produces artifacts |
| 8 | **Validation** — the stack-specific commands that **MUST** pass before completion; a task with no automated command **MUST** carry a specific manual checklist. | **MUST** |
| 9 | **Execution Checklist** + **Completion & Log** — the procedural walk-through plus the post-task log the agent fills (status, timestamp, summary, outputs, validation results, notes). The log **MUST NOT** retain placeholder values after completion. | **MUST** |

A task **MAY** additionally include a **Rollback** section (RECOMMENDED for
migrations, breaking changes, infra, or deployment), a **Team Agents Metadata**
section when it participates in a parallel group (§9), and a **Delta** section
(§5.0.1, RECOMMENDED for brownfield behavior changes).

### 5.0.1. The Delta Section (brownfield changes)

Most real work modifies existing behavior rather than creating new behavior. A
task that changes how an existing system behaves **SHOULD** carry a **Delta**
section describing the change as an explicit before/after contract, using three
list headings:

- **ADDED** — behavior that exists after the task and did not before.
- **MODIFIED** — behavior that exists in both, stated as `was: … → now: …`.
- **REMOVED** — behavior that existed before and is intentionally gone after.

Each entry **MUST** be observable behavior (an endpoint's response, a CLI flag, a
UI state, a default value) — not an implementation detail. The Delta section is
the reviewer's diff at the *behavior* level: acceptance criteria verify the
ADDED/MODIFIED entries, and the REMOVED entries are the explicit license to
delete — anything not listed as REMOVED **MUST** keep working, and the task's
validation gate (existing tests staying green, §5.1.1) is what enforces it.

> **Divergence from v1.** v1 specified the same content across ~11 numbered
> subsections (Title, Context, Read Before Starting, Goal, Instructions,
> Acceptance Criteria, Outputs, Validation, Rollback, Execution Checklist,
> Completion & Log). v2 consolidates to a **9-section canonical anatomy** —
> folding Rollback into optional and merging Execution Checklist with Completion &
> Log — and makes the **re-anchoring** step explicit inside Instructions
> (`RECONCILIATION.md` §"Specs"). Content parity is preserved.

### 5.1. Validation Gates

A task **MUST NOT** be marked complete unless every command in its Validation
section has been run and passed. On any failure the agent **MUST** stop, report the
command + output + suspected cause, **MUST NOT** mark the task complete, and **MUST**
await guidance. Validation commands **MUST** be runnable shell commands, deterministic,
and scoped; they **MUST NOT** require human judgment to interpret. The concrete
commands are repo-specific (see `DOCUMENTATION_STANDARD.md` §7) and **MUST** be
reasoned about per repo.

When the repository has a test, lint, or type-check toolchain (per
`DOCUMENTATION_STANDARD.md` §7), a task that changes product behavior **MUST** run
the relevant suite as part of its validation gate. "It builds" or "the file
exists" is **NOT** a sufficient gate for a behavior change.

### 5.1.1. Test Discipline — New and Changed Behavior

Tests are a first-class part of the loop, not an optional add-on: they are what
makes the code a Deep Work Plan ships **reliable** and verifiable. Whenever a task
implements new core functionality or materially changes existing behavior, the
agent **MUST**:

- Include, in the task's **Acceptance Criteria**, automated test coverage for the
  new or changed behavior (the happy path plus the meaningful edge/error cases),
  following the repository's test convention and coverage expectation
  (`DOCUMENTATION_STANDARD.md` §2.3, §3.1).
- Include, in the task's **Validation**, the repository's relevant **tests** *and*
  its **lint / type-check / format** checks — the full code-quality check the repo
  defines (e.g. `codecheck`, `npm run test && npm run lint`, `pytest && ruff check`),
  not the build alone.
- Keep existing tests **green**: if a behavior change breaks a test that covers the
  affected code, the agent **MUST** update that test to reflect the intended new
  behavior — it **MUST NOT** delete, skip, or weaken a test merely to force the gate
  to pass.

Pure-documentation, configuration, or research tasks are **exempt** from creating
tests but still **MUST** run whatever validation gate the repo defines. The *depth*
of testing is **proportional** to the size of the change and the repository's
maturity (`SHOULD` scale, not `MUST` reach a fixed number); what is non-negotiable
is that a behavior change ships with the coverage and the green checks the
repository's standard calls for. Where the repository has **no** test or lint
toolchain, the agent **MUST NOT** silently skip this discipline — it surfaces the
gap and relies on the toolchain established or **proposed** during onboarding
(`DOCUMENTATION_STANDARD.md` §3.1, §7).

### 5.2. Task Completion Protocol

After passing validation and before advancing, the agent **MUST**, in order:
(1) mark the task `[x]` in the plan README; (2) increment the `Plan Status` count;
(3) fill the task's Completion & Log with no placeholders; (4) add a 3–5 bullet
entry to `PROGRESS.md`; (5) commit (where the plan commits) with
`{type}({scope}): {description} - Task {N} of PLAN_{name}`; (6) where the plan
carries the state layer (§10), rewrite `state.json` atomically — task `completed`,
gate records, outcome record, commit hash. The agent **MUST** then verify the
README mark, the status count, the filled log, the PROGRESS entry, and a clean git
state before proceeding.

The six steps form one logical transaction. An agent interrupted mid-protocol
**MUST NOT** start the next task; on its next turn it **MUST** finish or unwind
the partial completion first (the README mark and the `Plan Status` count
disagreeing, or a filled log with an unmarked checkbox, are the desync signals —
see `PLAN_STATE.md` §5 for reconciliation).

### 5.3. The DWP Resume Protocol

Resume **MUST** be possible from only the plan's files plus the git log, with
**no external state**. (In a workspace without git — `ARCHETYPES.md` §4 — the
plan's `state.json` is REQUIRED and stands in for the git log.)

A resuming agent — a new session, a different agent, a scheduled daemon turn, or
a cloud session waking — **MUST** perform this ritual, in order:

1. **Re-anchor.** Read the plan README: §Goal, global guidelines, the task list.
2. **Locate the checkpoint.** Find the first `[ ]` task in the README; read the
   git log and `git status` (or `state.json`'s `checkpoint` where git is absent).
3. **Reconcile state.** Where `state.json` exists, compare it against the README
   checkboxes; on desync, regenerate it from the markdown before continuing
   (`PLAN_STATE.md` §5).
4. **Inspect the seam.** Read the resume-point task's Completion & Log and the
   last `PROGRESS.md` entry — the previous session's last verified ground.
5. **Smoke-test.** Run the repository's cheapest standing validation (the smoke
   or quick-check command from `AGENTS.md` Quick Commands) to confirm the world
   still works *before* building on it. A failing smoke test is investigated
   first, not built upon.
6. **Continue atomically.** Execute exactly the next task; do not batch ahead.

The agent **MUST** trust `[x]` marks and **MUST NOT** re-validate completed tasks
unless the user explicitly requests it, or step 5's smoke test fails in a way
that implicates a completed task.

---

## 6. Mandatory Final Tasks

Every conformant plan **MUST** end with exactly two mandatory tasks, in this order:

### 6.1. Task N-1 — Skills & Agents Discovery

- **MUST** review `PROGRESS.md` for patterns used two or more times across the plan.
- **MUST** check the existing `.agents/` skills/agents catalog for duplicates.
- **MUST** decide, per pattern, whether to create a new skill/agent, update an
  existing one, or record a finding.
- **MUST** write `analysis_results/SKILLS_AGENTS_DISCOVERY.md`, even when the
  conclusion is "no new skills warranted."

### 6.2. Task N — Executive Report

- **MUST** produce `analysis_results/EXECUTIVE_REPORT.md`, a stakeholder-ready
  summary covering at minimum: executive summary, plan overview, deliverables
  table, product impact, technical details, QA/verification guide, key decisions
  and trade-offs, risks/open questions, next steps.

Both final tasks **MUST** run sequentially after all other tasks (including any
parallel groups) and **MUST NOT** be placed in a parallel group.

---

## 7. Archetype Behavior in Plans

- For the **individual repo** (99% case), a plan operates entirely within one
  repository; all validation, commits, and outputs stay in that repo.
- For the **orchestrator hub**, a plan **MAY** be an orchestrator plan (§8) that
  spawns child DWPs in sub-repos. The hub plan **MUST NOT** commit sub-project code
  from the hub root; each sub-repo commits independently.
- An onboarding agent **MUST** determine the archetype (per `ARCHETYPES.md`) before
  deciding whether orchestrator capabilities apply.

---

## 8. Orchestrator Plans (optional capability)

The orchestrator mode is an **optional** capability primarily for the orchestrator
hub archetype. A repository **MAY** use it; an individual repo typically does not.

- An orchestrator plan **MUST** include, in the parent plan, a child-DWP tracking
  table (repository, child plan name, status) and an `ORCHESTRATOR_MANIFEST.md`
  carrying the shared cross-repo context, dependency graph, and output contracts
  (so each child inherits global decisions without re-deriving them).
- Each target sub-repo **MUST** have a dedicated `create_child_dwp` task in the
  parent plan that: navigates into the sub-repo, reads that sub-repo's `AGENTS.md`,
  creates `repositories/{repo}/.dwp/plans/PLAN_{child}/` with all required files,
  and ensures the child's tasks use **that sub-repo's** validation commands.
- Child DWPs **MUST** reference `ORCHESTRATOR_MANIFEST.md` and **MUST** follow this
  specification independently. They **MAY** be created and executed in
  **Distributed**, **Sequential-with-handoff**, or **Sequential-basic** mode.
- After all child plans complete, the parent plan **SHOULD** include an integration
  checkpoint task.

> **Divergence from v1.** Kept from v1 §10 with the path update
> `repositories/{repo}/.dwp/plans/` (was `.../.agent_commands/.../results/plans/`),
> per `RECONCILIATION.md` divergence #2. This plan and its `ORCHESTRATOR_MANIFEST.md`
> are the live worked example.

---

## 9. Team Agents (optional capability)

Team-agents metadata is an **OPTIONAL**, additive extension for agents that support
parallel execution (currently Claude Code only). Plans **MUST** function correctly
when executed sequentially; team-agents metadata is purely additive.

- A plan using team agents **SHOULD** declare Parallel Task Groups in its README
  (group → task numbers → teammates → description).
- A participating task **SHOULD** carry a Team Agents Metadata section (parallel
  group, role, file ownership, concurrency, blocks).
- Tasks in the same parallel group **MUST NOT** write to the same files (declared
  file ownership). The mandatory final tasks (§6) **MUST** remain sequential.

Non-Claude agents **MUST** ignore team-agents metadata and execute every task
sequentially (see `AGENT_PROTOCOL.md`).

---

## 10. Machine-Readable Plan State (optional layer)

A plan **MAY** carry the machine-readable state layer — `manifest.json` (static
identity) and `state.json` (live per-task state, validation-gate records, outcome
records, checkpoint, blocked state) — normatively defined in **`PLAN_STATE.md`**
with published JSON Schemas in [`schema/`](schema/).

- The markdown plan remains the source of truth; the JSON layer is a **derived
  projection**, regenerated at the protocol points of §5.2 and reconciled on
  resume (§5.3 step 3).
- The layer is **RECOMMENDED** for new plans, **REQUIRED** for unattended
  execution (`AGENT_PROTOCOL.md` §7) and for agent workspaces without git
  (`ARCHETYPES.md` §4).

---

## 11. Proportional Rigor — Plan Tiers

Rigor **MUST** be proportional to the work. Ceremony on trivial changes is a
methodology failure, not extra safety. Every piece of work falls in exactly one
tier, declared in the manifest's `rigor` field when the state layer is present:

| Tier | When | Form |
|------|------|------|
| **micro** | A single atomic change: one concern, roughly one sitting, no coordination — a bug fix, a copy change, a config tweak. | **No plan folder.** The agent states the goal, the acceptance criteria, and the validation gate inline in conversation, executes, validates, commits. |
| **standard** | Multi-step work with real scope: a feature, a refactor, a migration within one repo. The default tier. | A full plan per §4–§6: plan folder, 9-section tasks, mandatory final tasks. |
| **deep** | Long-horizon work spanning parallel groups, child repositories, or multiple unattended sessions. | A standard plan plus the orchestrator (§8) and/or team-agents (§9) capabilities, and the state layer (§10). |

- An agent asked to "create a plan" for micro-tier work **MUST** say that a plan
  is disproportionate and offer the inline form instead. A plan folder **MUST
  NOT** be created for a trivial single-file change.
- Micro-tier work still keeps the non-negotiables: an explicit goal, a
  validation gate that runs and passes (§5.1), and test discipline for behavior
  changes (§5.1.1). The tier changes the *packaging*, never the *gates*.
- When scope grows mid-flight — a micro task uncovers real scope, a standard
  plan sprouts sub-repos — the agent **MUST** stop and promote the work to the
  next tier rather than stretching the current one.
- Tier selection is part of plan creation: the `create` flow **SHOULD** state
  the chosen tier and why in the refined draft.

---

## 12. References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)
- `DOCUMENTATION_STANDARD.md`, `AGENT_PROTOCOL.md`, `ARCHETYPES.md`, `ADDONS.md`, `PLAN_STATE.md`
- `../RECONCILIATION.md` (divergences #1–#3 drive this spec), `../../ORCHESTRATOR_MANIFEST.md`
- [Conventional Commits](https://www.conventionalcommits.org/)

---

*Part of the DeepWorkPlan methodology v2.2.0, MIT License, by [Dailybot](https://dailybot.com) / dailybotops.*
