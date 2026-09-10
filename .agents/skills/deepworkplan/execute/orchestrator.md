# DeepWorkPlan — Execute: orchestrator branch (read only when Step 2.1 detected an orchestrator plan)

Verbatim from the main procedure, with predecessor context aligned to the optional Executive Report.

## Orchestrator Task Types

Orchestrator navigation generalizes across the two archetypes (see
`../shared/adaptation.md`):
- **Orchestrator-hub archetype** — the hub coordinates sub-repos under
  `repositories/{repo}/`. Navigate with `cd repositories/{repo_name}` to operate
  in a child repo, and return to the hub root (resolve it via
  `../shared/context.sh` — e.g. the git toplevel) between tasks. Child plans live
  at `repositories/{repo}/.dwp/plans/PLAN_{child}/`.
- **Individual-repo archetype** — the repo resolves its own root via
  `../shared/context.sh`; there is no `repositories/` layer. Child-DWP task types
  rarely apply here.

**`create_child_dwp` tasks:** navigate to the target repo; read its `AGENTS.md`
(validation commands, test patterns, commit format, stack); install/confirm
DeepWorkPlan there if missing (it ships its own guide/examples); create the child
DWP at `{child_repo_root}/.dwp/plans/PLAN_{feature}_{repo_short}/` using that
repo's conventions and validation commands (NOT the hub's), including a parent
plan reference; return to the hub root and mark the child `[x] Created` in the
orchestrator README's Child DWP Plans table. In **Sequential** mode also execute
the child DWP immediately (committing in that repo) and mark `[x] Created /
[x] Executed`; in **Distributed** mode create only.

**`integration_checkpoint` tasks:** read the checkpoint criteria and all created
child DWPs; verify integration points (API contracts, data model field
names/types, naming, error handling) across repos; report each pass/fail; fix
blockers or flag for the user.

**`execute_child_dwp` tasks:** verify execution readiness from
`ORCHESTRATOR_MANIFEST.md` (all predecessors `[x] Executed`, outputs listed) — if
any predecessor is missing, STOP and report BLOCKED. Load the predecessors' durable outputs as context (their README completion
summary, `PROGRESS.md`, `analysis_results/SECURITY_REVIEW.md`, and an Executive
Report only if one was produced — it is optional); navigate to the target repo; execute the child DWP using that
repo's validation commands; commit there; return to the hub and register outputs
in the manifest (mark `[x] Executed`, add a Completed Output Reference) and update
the README to `[x] Created / [x] Executed`.

## Orchestrator Plan Completion
Report per mode (Distributed: all child DWPs created and ready, with the
dependency order and per-repo execute commands; Sequential / Sequential with
Output Handoff: all created and executed, with outputs and the fully-updated
manifest path). The same Dailybot milestone golden rule applies — describe what
the feature achieved across repos, never "N child DWPs executed."

## Orchestrator notes and errors

- **Orchestrator navigation:** always return to the hub root between tasks (hub
  archetype). Orchestrator tracking updates are committed in the hub; child plan
  files live in each sub-repo's gitignored `.dwp/`.
- **Manifest:** read it at the start of orchestrator execution; update it after
  each `execute_child_dwp`. Verify predecessors before any `execute_child_dwp`.
- Target repo not found / no `AGENTS.md` → report; for missing `AGENTS.md`,
  create a minimal child DWP with generic validation and note it.
- Predecessor not executed (`execute_child_dwp`) → BLOCKED; list what's missing;
  do not proceed.
- Manifest missing but `execute_child_dwp` exists → warn; fall back to the
  README's Child DWP Plans table and the predecessors' durable outputs; log the
  limitation.
