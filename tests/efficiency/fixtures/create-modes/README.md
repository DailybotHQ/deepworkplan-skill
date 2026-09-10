# Fixture: create-modes (Task 8 → replayed in Task 18)

Scenarios for the `create` flow. Each is run against a copy of `../isolated-change/` (a small repo with a documented scoped test command) unless stated.

| # | Invocation | Expected artifacts | Must hold |
|---|---|---|---|
| C1 | `/dwp-create <full context>` (guided) | `.dwp/drafts/PLAN_x_draft_refined.md` first; plan folder only after approval | draft carries tier + tasks with planned Touched Surface and gates |
| C2 | `/dwp-create <full context> trust` | **no** draft file; `.dwp/plans/PLAN_x/` with README last; README says pre-approved (trust); `manifest.json.spec_version == "2.3.0"` | quality ≥ C1 on the rubric; zero questions asked |
| C3 | `/dwp-create refined-draft x trust` | only the draft (explicit draft wins over trust) | no plan folder |
| C4 | `/dwp-create from PLAN_x_draft_refined.md` | plan folder from the draft; Step 3.7 check applied | identical task set to the draft |
| C5 | rerun `create` for a name whose folder is `partial-plan/` (task files, no README) | offer complete / discard; complete regenerates only missing files | no unrelated file overwritten |

Generated plan shape (all): `N.task_final_review.md` last and only final task; no `task_skills_agents_discovery` / `task_executive_report`; every code task has a Touched Surface; `analysis_results/SKILLS_CANDIDATES.md` present; every checklist has the skills-decision step.

## Refine scenarios (Task 9 → replayed in Task 18)

| # | Setup | Invocation | Must hold |
|---|---|---|---|
| R1 | copy of `../new-shape-plan/` | `/dwp-refine plan PLAN_new_shape_fixture` → add a task `before-final`, then reorder | Final Review stays last; README links/count, task ids and `state.json` regenerated and consistent; completed Task 1 entry keeps `commit`/`gates` |
| R2 | copy of `../legacy-plan-v217/` | `/dwp-refine plan PLAN_legacy_fixture` → edit Task 2 | legacy shape retained (three final tasks untouched); insert range `1..N-3`; no Final Review added; no migration suggested |
| R3 | copy of `../new-shape-plan/` with Task 2 expanded to two independent outcomes | split Task 2 | every requirement of the original lands in exactly one child; pointers updated; nothing summarized away |
| R4 | copy of `../legacy-plan-v217/` | `/dwp-refine migrate PLAN_legacy_fixture` | completed Task 1 untouched; unstarted legacy finals → single Final Review; Touched Surface added to unstarted code tasks; README `**Standard:** … (migrated from 2.2.0 …)` line; `manifest.json` byte-identical |
| R5 | draft from C1 | `/dwp-refine PLAN_x_draft_refined.md` → convert | plan per create Step 4.4; README last; no report task |
| R6 | copy of `../new-shape-plan/` | edit the acceptance criteria of completed Task 1 | refine lists the impact and, only on confirmation, marks Task 1 `[ ] (re-validate…)`, state `pending` with gates kept and evidence prefixed `invalidated by refine`; log appended, never rewritten |
