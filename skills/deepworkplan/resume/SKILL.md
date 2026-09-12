---
name: deepworkplan-resume
description: Resume interrupted Lite or Full Deep Work Plans from durable Markdown and state, including safe recovery of promotions without duplicating completed work or gates.
version: "5.1.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
---

# DeepWorkPlan — Resume

Safely continue an interrupted plan from where it stopped — no duplicated work,
strict order, continuing from the first `[ ]` task — from **repository
artifacts alone**: a different session, agent, model or harness must be able to
pick the plan up without the previous conversation.

## Shared resources (read these)

- [`../shared/context.sh`](../shared/context.sh) — resolve repo root, branch, and
  `dwp_dir`.
- [`../shared/dwp-paths.md`](../shared/dwp-paths.md) — plans at
  `.dwp/plans/PLAN_{name}/`.
- [`../shared/adaptation.md`](../shared/adaptation.md) — the two repository
  archetypes (relevant for orchestrator/child-DWP awareness).
- [`../shared/troubleshooting.md`](../shared/troubleshooting.md) — **conditional:**
  read only when something is already wrong (discovery failure, stale
  installation, missing test command, unsupported host capability,
  inconsistent plan state).
- [`../execute/SKILL.md`](../execute/SKILL.md) — the execution rules this flow
  resumes into (gate selection, repair/stop, task-local closure, Final Review,
  Dailybot golden rule; team-agents and orchestrator branches on demand).
- **Guide (essential — read for this flow):** none beyond what `../execute/SKILL.md` names ([`../guide/execution.md`](../guide/execution.md)).
- **Guide (conditional — read only when the trigger fires):** [`../guide/prompts.md`](../guide/prompts.md) §9 (resume rules and scenarios) when the interruption is unusual; [`../spec/PLAN_STATE.md`](../spec/PLAN_STATE.md) §5–§6 when the plan carries `state.json` and a desync, a takeover, or a standard question needs the normative rule. [`../guide/GUIDE.md`](../guide/GUIDE.md) is the routing index.

## Parameter Support

- `/dwp-resume {plan_name}` — resume directly (skip the menu).
- `/dwp-resume latest` — resume the most recently modified plan.
- `/dwp-resume {plan_name} trust` (or `auto`, or "run to the end") — resume
  unattended: no questions between tasks (`../execute/SKILL.md` *Autonomous mode*).
- No parameter → interactive selection (Step 1).

Normalize the `PLAN_` prefix; validate `.dwp/plans/PLAN_{name}/` and its
`README.md`. If not found, show available plans and ask the user to choose. A
folder without `README.md`, or whose README says `Plan Status: materializing`,
is a partial materialization (its `manifest.json` records the intended shape) —
point to `refine`; never execute it.

## Lite and promotion recovery

For v2 Lite plans, read the README's canonical task index, inline anchor record,
state locator and checkpoint before reading older history. A README checkbox wins
over state on desync. Do not treat missing task files as partial when the format
is Lite. Conversely, a `promotion` marker or `materialization: promoting` is a
hard recovery boundary: inspect its phase, preserve existing files and route to
`/dwp-refine promote` to complete the missing transaction step. Never execute
product work in a mixed representation.

An explicit execute/resume request can approve a ready plan's current scope
(Lite or Full). If a new requirement changes scope, criteria or gate, record
the checkpoint and use refine; do not promote or alter approvals implicitly.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`.

**Writes:** identical scope to `execute` (task outputs, `.dwp/` working state,
per-task commits after gates pass) — resume continues an interrupted plan, it
does not widen the boundary. Recorded state follows the **DWP Resume Protocol**
(`../spec/DWP_SPECIFICATION.md` §5.3): completed `[x]` tasks are **trusted as
recorded** — never re-validated unless the developer explicitly asks, `refine`
marked them `(re-validate: …)`, or the protocol's smoke test fails in a way that
implicates a completed task — while the **world** is smoke-tested (cheapest
standing validation) before anything is built on it.

**It MUST NOT:** re-run or "fix up" already-completed tasks unless the
developer asks, a `(re-validate…)` marker exists, or the §5.3 smoke test
implicates them; skip the post-interruption smoke test; repeat a commit, gate,
skill authoring, report or other external action that the evidence shows
already happened; migrate a legacy plan (that is `refine migrate`, on explicit
request only); push without instruction; or write outside the repo checkout and
`.dwp/`.

## Workflow

### Step 0 — Check for Parameters
If a parameter was given, resolve the plan (or `latest`), validate folder +
README under `.dwp/plans/`, note `trust`/`auto`, and skip to Step 2. Otherwise
go to Step 1.

### Step 1 — Identify Plan
List `PLAN_*` folders in `.dwp/plans/`; mark the most recently modified as
`latest`. Present a numbered menu (number / name / `latest`) and validate the
choice.

### Step 2 — Assess Current State (CRITICAL)

This step implements the **DWP Resume Protocol**
(`../spec/DWP_SPECIFICATION.md` §5.3) — the named ritual any resuming session
performs. It reads the **compact index first** and retrieves history **by
pointer**, never by replaying everything.

1. **Load the compact working index.** Read the plan README's task list (the
   small `[x]`/`[ ]` index, the `Plan Status` count, the `**Standard:**` line and
   the pre-approval note), the **Active context** block of `PROGRESS.md` (goal
   and invariants, active task and next action, unresolved blockers, current
   contracts and decisions in force, direct pointers to durable records), and —
   when present — `state.json`'s `status`, `checkpoint`, `blocked`, and the
   entries of the **active task and its named dependencies only** (not every
   gate of every task). Do **not** read every task file or the whole history by
   default; retrieve older records later, by pointer, when a step needs them.
2. **Gather actual evidence.** Run `git status`, `git log --oneline -10`, and
   `git diff` (if uncommitted changes exist). In a workspace without git, read
   `state.json`'s `checkpoint` instead (`../spec/PLAN_STATE.md` §4.4). Note the
   current revision.
3. **Reconcile Markdown, JSON and the workspace — before any work.** The
   markdown wins every disagreement (`../spec/PLAN_STATE.md` §5):
   - `state.json` vs README checkboxes disagree → regenerate `state.json` from the
     README (and git log), note the reconciliation in `PROGRESS.md`, continue.
   - `state.json.blocked` is set → surface it: that is why the plan stopped.
   - A `[x]` task with no matching commit where the plan commits, a checkpoint
     that names work the tree does not show, a summary that contradicts the
     files, or instructions in the working index that contradict the task file
     → **do not trust the summary or the flag alone**: inspect the files and the
     log, record the finding in `PROGRESS.md`, and treat the task as the
     evidence says (in doubt, as not completed). Never repeat a committed action.
   - A README `[ ]` marked `(re-validate: …)` → its implementation exists; only
     its gates are rerun (`../refine/SKILL.md` 3.7).
   - The plan declares a standard newer than this skill → report and stop.
4. **Find the resumption point** — the **first unchecked `[ ]` task** (a task
   `in_progress` in `state.json` with a checkpoint is the active one).
5. **Classify partial work at its interruption boundary.** Using the evidence
   from steps 2–3 and the active task's Completion & Log, decide **which single
   step is missing** and do only that (`../spec/PLAN_STATE.md` §5.1):

   | Interrupted… | Evidence to check | Then |
   |---|---|---|
   | before the gate ran | uncommitted changes; no gate record | finish the implementation if incomplete; run the gate **once** |
   | after the gate, before the commit | gate record present, `passes: true`, and inputs unchanged (fingerprint) | reuse the passing gate result; commit **once** |
   | after the commit, before the README/log update | commit exists in `git log`; README still `[ ]` | complete log → README → PROGRESS → `state.json`; do **not** re-commit |
   | between Markdown and `state.json` updates | README `[x]`, state stale | regenerate `state.json`; nothing else |
   | after an external action (report, push, PR, message) | the action's own evidence (report id, remote branch, PR URL in the log) | do **not** repeat it; record that it already happened |
   | mid-implementation with no checkpoint note | dirty tree only | review the diff against the task; incorporate valid partial progress, finish the rest |

   Changed inputs since a recorded gate (a later edit, a `refine`, a new
   revision) invalidate that gate → rerun it. Where the table resumes the
   tail of the update order, the `state.json` step may use the shipped
   updater (`../shared/update-state.py`) as a targeted, atomic mutation;
   only the reconcile-from-markdown row regenerates the whole file.
6. **Takeover from another agent or model.** If the checkpoint, log or
   `PROGRESS.md` was written by a different agent/model (`state.json.updated_by`,
   the log's wording) or the session is a fresh context: read the checkpoint
   **pointer** (`task`, `step`, `note`) and verify it against the files it names;
   detect contradictory instructions, stale state (revision changed), dirty work
   and missing evidence **before** continuing; record a one-line "takeover"
   entry in `PROGRESS.md` (who/what, revision, what was verified). Only then
   continue. The handoff artifact is the plan itself — nothing required may live
   only in a prior conversation, a proprietary task API, or a hook.
7. **Smoke-test before building:** run the repo's cheapest standing check (from
   `AGENTS.md` Quick Commands) to confirm the world still works before adding to
   it. A failing smoke test is investigated first.

### Step 3 — Report Resumption Status
Report, compactly: the plan's standard and pre-approval; completed `[x]` /
pending `[ ]` counts; the task to resume from and its interruption boundary
(Step 2.5) with the single next action; git state (uncommitted changes, recent
commits, last commit); reconciliation or takeover findings; any blocker. Location:
`.dwp/plans/PLAN_{name}/`.

### Step 4 — Handle Partial Work
Apply the Step 2.5 decision. Interactive: if the partial work is unclear or
unrelated, ask the user before proceeding. **Unattended:** unclear or unrelated
changes are a `../spec/AGENT_PROTOCOL.md` §7.3 boundary (reality diverged) —
record `state.json.blocked` with what was found and halt; do not guess and do
not discard work.

### Step 5 — Resume Execution
1. **NEVER redo `[x]` tasks** — trust the README, cross-check git commits (and
   the `(re-validate…)` exception above).
2. **NEVER skip `[ ]` tasks** — strict order; complete each fully.
3. **Continue from the first `[ ]` task** — open its file, read fully, address any
   logged blocker first.
4. **Complete the current task** under the standard **Execute** rules
   (`../execute/SKILL.md` Step 5): gate selected from the actual surface; repair
   in scope or stop; task-local closure (skills decision → log → README →
   PROGRESS → commit → `state.json`).
5. **Keep the working context bounded while executing.** On a stable run retain
   the already-loaded, unchanged context; re-read after a revision change, a
   handoff, a context compaction, or uncertainty. Retrieve older records
   **only** when a task's `Read Before Starting` names them, a decision cannot
   be found in the active-context block, or a pointer is stale or missing — and
   then verify what was retrieved rather than guess. Never drop an unresolved
   constraint or an active contract to save space.
6. **Continue** to the next `[ ]` task until done or paused — without asking
   whether to continue inside the plan's authorization.

> From here, the standard **Execute** rules apply
> (`../execute/SKILL.md`): the per-task significance Dailybot report, the
> plan-completion **milestone** golden rule, the Final Review (a)–(d) with the
> one-time Executive Report offer, and — for orchestrator plans — orchestrator
> task types (`create_child_dwp` / `integration_checkpoint` /
> `execute_child_dwp`), manifest checks, and team-agents parallel groups (real
> team agents, not subagents) with sequential fallback, each on demand. A
> **legacy** plan (three final tasks) resumes under its own shape — resume never
> migrates it.

### Step 6 — Handle Blockers
If a task log or `state.json.blocked` shows a blocker, read it, fix the issue
within the task's authorized scope, re-run only the affected validations; on
pass: clear `blocked`, mark `[x]`, commit, continue; on fail: log again, stop,
request help (unattended: halt with `blocked` updated).

### Step 7 — Progress Reporting
After resuming and completing a task, show the compact result of
`../execute/SKILL.md` Step 6 (`✓ Resumed and completed: Task N` …). On blocker:
`✗ Task N blocked` with the blocker, action taken, status, and next step.

## The handoff artifact (what every session leaves behind)

Before yielding — at the end of a task, at a checkpoint before a planned
interruption, or when halting — the executing session **writes** (never only
says): the task's Completion & Log (or its partial notes), the README
checkboxes, the `PROGRESS.md` **Active context** block with the exact next
action and the evidence pointers, and `state.json` (`checkpoint` `{task, step,
at, note}` or `blocked`). That is the whole handoff: a fresh agent, another
model, or another harness resumes from these files with Step 2.

## Important Notes
- Trust the task list (`[x]` done / `[ ]` pending); verify with git; read the
  active task's log and the compact index; retrieve history by pointer; never
  duplicate work; never skip; assess partial work at its boundary; stop on
  blockers.
- **Legacy plans:** execute as recorded; no automatic lifecycle migration.

## Error Handling
- Invalid plan structure → report; ask to fix (`refine`) or proceed with caution.
- Missing task file → report; ask whether to skip or create (unattended: blocker).
- Unclear git state → report findings; ask before proceeding (unattended: §7.3
  boundary).
- Contradictory checkpoint / summary vs files → trust the files; record; continue
  from the evidence.
- Unresolvable blocker → log in Completion & Log; report; wait for guidance.
