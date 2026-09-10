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
