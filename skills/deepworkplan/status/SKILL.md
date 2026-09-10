---
name: deepworkplan-status
description: Report the status of a Deep Work Plan — completed tasks, what's left, current checkpoint, blockers and any Markdown/state/git inconsistency — from the compact state projection, without executing or modifying anything. Use when the developer asks for plan status or what remains.
version: "3.0.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob
---

# DeepWorkPlan — Status

Report the current state of one or more Deep Work Plans — progress, completed
tasks, current task, checkpoint, blockers, consistency — **without executing or
modifying anything**, and without loading the whole plan.

## Shared resources (read these)

- [`../shared/context.sh`](../shared/context.sh) — resolve `dwp_dir`.
- [`../shared/dwp-paths.md`](../shared/dwp-paths.md) — plans at
  `.dwp/plans/PLAN_{name}/`.
- **Guide (essential — read for this flow):** none. Status is a read-only report; it does not load the methodology guide.

## Parameter Support
- `/dwp-status {plan_name}` — check a specific plan.
- `/dwp-status latest` — check the most recently modified plan.
- `/dwp-status all` — check all plans.
- No parameter → interactive scope selection (Step 1).

Normalize the `PLAN_` prefix; validate that single plans exist under
`.dwp/plans/`. If not found, show available plans and ask the user to choose.

## Trust boundary (write scope)

This skill is **read-only by contract**. `allowed-tools` lists `Bash` (which
Trust Hub treats as write-capable in general) — here it is used exclusively
for read-only inspection. Status reads plan folders, progress checkmarks, and
`state.json`, and reports; it performs no writes of any kind.

**It MUST NOT:** modify tasks, progress, `state.json` or source files; "fix" a
plan while reporting on it; or write anywhere. If the status reveals an
inconsistency, report it and point at `refine`/`resume` — do not repair it
silently.

## Workflow

### Step 0 — Check for Parameters
`all` → scope "all", skip to Step 2. `latest` → most recent plan, scope "single",
skip to Step 2. Otherwise normalize the name, validate, scope "single", skip to
Step 2. No parameter → Step 1.

### Step 1 — Ask for Scope
List `PLAN_*` folders in `.dwp/plans/`; mark the most recently modified as
`latest`. Offer: a single plan (from a numbered list), all plans, or `latest`.
Accept a number, name, `all`, or `latest`.

### Step 2 — Gather Status Information (compact projection first)
For each plan:
1. **State first.** If `state.json` exists, read it: `status`, `completed_count`
   / `task_count`, `checkpoint`, `blocked`, `updated_at`/`updated_by`, and the
   per-task `status` list. This is the compact projection; it is enough for the
   summary.
2. **README index.** Read the README's goal, `Plan Status` line, task list
   (`[x]`/`[ ]`, any `(re-validate…)` markers), `**Standard:**` line and
   pre-approval note. When there is no `state.json`, the README is the only
   source and the report says so.
3. **Consistency check** (`../spec/PLAN_STATE.md` §5): compare README checkboxes
   with `state.json` task statuses and `completed_count`; compare `[x]` tasks
   that carry a `commit` with `git log --oneline -20`; note a `checkpoint` whose
   task is `[x]`, a `blocked` entry on a `[x]` task, or a `task_count` that
   differs from the number of task files. Every disagreement is a **finding**
   (which tasks, which direction, markdown is authoritative) — never an edit.
4. **Targeted detail only.** Read the last completed task's Completion & Log and
   the current `[ ]` task file's title/goal; run `git status`. Do not read every
   task file or every gate record.
5. Compute totals and progress %.

### Step 3 — Generate Status Report

**Single plan:** header with `Plan Status: PLAN_{name}` and location
`.dwp/plans/PLAN_{name}/`; standard (and whether pre-approved for unattended
execution); goal; progress (total / completed / pending / %); completed tasks;
pending tasks; current status (last completed, next task, checkpoint note,
uncommitted work, recent commits); **blocked** (reason, since, needs) if set;
**consistency findings** if any, with the suggested action (`resume` to
reconcile, `refine` to fix structure); notes from the README; last task log
summary; whether an Executive Report was requested/produced.

**All plans:** a one-line-per-plan summary (progress, status, blocked?, last
activity), then the single-plan detail block for each.

### Step 4 — Additional Information (optional)
Offer deeper detail for any plan: all task files and status, `git diff` for
uncommitted changes, full last-task completion log, the gate records of one
task, any blockers.

### Step 5 — Quick Actions
Suggest: resume (`/dwp-resume PLAN_{name}`), execute (`/dwp-execute PLAN_{name}`),
refine (`/dwp-refine plan PLAN_{name}`), or open a specific task file.

## Status Classifications
Not started (all `[ ]`, no commits) · In progress (mixed, recent activity) ·
Complete (all `[x]`) · Blocked (`state.json.blocked` set or the current task's
log has a blocker note) · Stale (no activity for a long time — optional) ·
**Inconsistent** (any Step 2.3 finding — reported alongside the classification).

## Important Notes
- **Read-only:** never executes or modifies plans; `git status` is reported, not
  committed. Cross-reference the README task list with `state.json` and git
  commits for accuracy; the markdown is authoritative when they disagree.
- **Cheap by design:** the compact projection plus the README index answer the
  question; task files and logs are read only for the targeted detail above.

## Error Handling
- Plan folder doesn't exist → report; list available plans; ask to select.
- README missing, or README says `Plan Status: materializing` → report a partial
  materialization; read `manifest.json` (intended title and `task_count`) and
  the README task list when present and list which intended files exist and
  which are missing; suggest `/dwp-refine` (complete or discard) or
  `/dwp-create`. Never report it as executable.
- `state.json` unreadable or invalid → report it as a finding; fall back to the
  README; suggest `/dwp-resume` (which regenerates it).
- No plans exist → report "No plans found in `.dwp/plans/`"; suggest
  `/dwp-create`.
