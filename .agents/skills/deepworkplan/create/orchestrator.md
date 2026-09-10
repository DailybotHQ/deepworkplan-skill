# DeepWorkPlan — Create: orchestrator branch (read only when Step 2.6 fires)

This file is read **only** when the `create` flow detects an orchestrator plan
(`SKILL.md` Step 2.6). It carries the orchestrator-specific gathering steps and
the additions to materialization, verbatim from the main procedure. Everything
else (requirements analysis, task anatomy, quality check) is in `SKILL.md`.

## Gathering — orchestrator detection and questions

**2.6 Orchestrator detection (automatic).** After 2.3–2.4, auto-detect an
**orchestrator plan** when: the work spans 2+ sub-repositories with independent
feature work, or the user explicitly mentions child DWPs / orchestrator /
"create plans in each repo". If detected, offer the choice between an
**orchestrator plan** (creates child DWPs per repo, each following its own
`AGENTS.md`) and a **direct multi-project plan**. See `../guide/orchestrator.md` §13 and
`../shared/adaptation.md` (orchestrator-hub archetype).

**2.7–2.9 (orchestrator only):** ask for target repositories (note each repo
root — for an orchestrator hub this is `repositories/{repo}/`), dependency order,
and execution mode (Distributed / Sequential with Output Handoff / Sequential
basic). Default to Distributed.

## Materialization — orchestrator additions

**Orchestrator additions (orchestrator plans):**
- README **Child DWP Plans** table (`# | Repository | Child Plan | Status |
  Depends On`), an **Execution Mode** subsection, and **Dependency Rules**.
- **ORCHESTRATOR_MANIFEST.md** at `.dwp/plans/PLAN_{name}/ORCHESTRATOR_MANIFEST.md`
  (template in `../guide/orchestrator.md` §13.8): Shared Context, Child DWP Registry,
  Dependency Graph, Output Contracts, Execution State.
- Task files: direct design tasks first (if hybrid); then `create_child_dwp`
  tasks in dependency order (template
  `../examples/ORCHESTRATOR_TASK_TEMPLATE_create_child_dwp.md`); optional
  `integration_checkpoint` tasks
  (`../examples/ORCHESTRATOR_TASK_TEMPLATE_integration_checkpoint.md`);
  `execute_child_dwp` tasks for Sequential-with-Output-Handoff mode
  (`../examples/ORCHESTRATOR_TASK_TEMPLATE_execute_child_dwp.md`); then the
  Final Review last (`{N}.task_final_review.md`). Each `create_child_dwp` task instructs the agent to
  navigate to the target repo, read its `AGENTS.md`, and create a child DWP at
  `repositories/{repo}/.dwp/plans/PLAN_{child}/` using that repo's conventions.
