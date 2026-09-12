# DeepWorkPlan — Create: team-agents branch (read only when Step 2.10 fires)

This file is read **only** when the `create` flow's always-on detection
(`SKILL.md` Step 2.10) finds parallelizable tasks, or when Claude Code team
agents are available to accelerate generation or research. Team-agents metadata
is always additive: every plan must also work sequentially, and nothing required
lives only in a team-agents section.

## Gathering — team-agents detection and parallel research

**2.10 Team-agents detection (automatic — always runs, non-orchestrator plans).**
Always analyze whether 2+ tasks touch different files/modules with no data
dependencies and would benefit from parallel execution. This is NOT opt-in.
The parallelization decision is **always declared in the plan README** — never
silent, in either direction.
- If parallelizable: in **guided** mode, inform the user (do not ask) and add the
  team-agents configuration; in **trust** mode, do it silently. Team-agents
  metadata is always additive and backward compatible (other agents ignore it).
- Auto-assign parallel groups (tasks with no cross-dependencies), teammate roles
  (derived from task content), and default model `sonnet`. Each parallel group
  may name what it **starts after** (a task, a prior group, or a barrier);
  plans with parallel groups **also list their sequential tasks explicitly** in
  the groups table (corpus shape: `Sequential tasks: …` rows). Setup/integration
  and the Final Review (the single mandatory final task) are **always
  sequential** — exempt from parallel groups in every plan.
- If not parallelizable: write an explicit, agent-neutral **sequential
  declaration** into the plan README — one line, corpus shape:
  `Execution: sequential — {short rationale: shared surface / collision risk /
  single-session audit trail}`. Never leave the decision silent, and never
  fabricate parallel groups to fill the section.

**Step 2.11 — Parallel Research Phase (Claude Code only, automatic).** Before
materialization, if the plan spans 2+ repos or several independent modules and context
isn't already provided, spawn **research teammates** (`subagent_type: "Explore"`,
one per repo/area) to read each `AGENTS.md`, identify relevant files, contracts,
and validation commands, then synthesize their findings into enriched context for
the plan. Skip for simple/single-module plans or full-context input.
Fallback: research sequentially if team agents are unavailable. In trust mode,
run silently.

## Materialization — team-agents metadata

**Team-agents metadata (when Step 2.10 detected parallelizable tasks):** add a
"Team Agents Configuration (Claude Code Only)" section to the README (Parallel
Task Groups + Teammate Roles tables) and a "Team Agents Metadata (Claude Code
Only)" section to each parallel task file (Parallel Group / Teammate Role / Can
Run With / Blocks / Files Owned). Use `../examples/TEAM_AGENTS_TASK_TEMPLATE.md`.
The Parallel Task Groups table carries an optional **Starts after** column (the
task, group, or barrier a group starts after) and lists sequential tasks
explicitly (Sequential rows naming their tasks). Rules: never put required info
inside team-agents sections; every task must work
sequentially; the Final Review is always sequential; file ownership between
parallel tasks must not overlap — two tasks in one group owning the same file
is a conflict even when their logical changes are independent.

**Sequential declaration (when Step 2.10 found no parallelizable groups):** add
one line to the plan README (near the task list, where a Team Agents
Configuration section would sit): `Execution: sequential — {short rationale}`.
The rationale is one clause naming the real cause (shared surface, collision
risk, single-session audit trail). This line is agent-neutral — every agent
reads it as the plan's parallelization decision; execute/SKILL.md Step 2.2
treats it as a made decision, not a missing one.

## Accelerating generation with team agents

**Accelerate generation with team agents (Claude Code only, automatic):** for
5+ user-defined task files, the lead creates README/PROMPTS/PROGRESS/
analysis_results + the Final Review task file, then spawns teammates (1 per
2–3 task files) to write user task files in parallel (no file overlap), verifies
all files, and cleans up. Fallback: generate sequentially.
