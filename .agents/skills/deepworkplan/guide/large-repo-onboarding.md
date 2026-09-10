# DeepWorkPlan Guide — Onboarding a Large Repo as Its Own Deep Work Plan

> Part of the DeepWorkPlan methodology guide. The routing index is
> [`GUIDE.md`](GUIDE.md); read only the guide files your flow names.

## 15. Onboarding a Large Repo as Its Own Deep Work Plan

Making a repository AI-first (the `onboard` sub-skill) means analyzing the
**whole** codebase and **documenting all of it**: every `docs/` category, a
per-module `README.md` for each major module, and the full `.agents/` kit
(agents, skills, commands, catalogs). For a small or medium repo, the `onboard`
flow does this **inline** in one session — fast and correct.

For a **large** repo, doing it all inline is the wrong tool: it strains a single
context window, gives no per-artifact validation gate, can't be audited
task-by-task, and loses all progress if the session is interrupted. That is
exactly what Deep Work Plans exist to solve. So at scale, **onboarding becomes
its own Deep Work Plan** — the repo's first plan is literally "finish onboarding
myself," executed task-by-task with gates and full resumability. The methodology
dogfoods itself: onboarding uses the very loop it installs.

**When the `onboard` flow chooses the plan-driven path** (its Phase 2b decision):
more than ~8 major modules, a monorepo / multi-package workspace, an orchestrator
hub, ~15+ total artifacts to generate, or the developer asks. Otherwise it stays
inline (the typical case).

**Shape of the onboarding plan** (one task = one artifact, each with a gate):

- **Task 1** — `AGENTS.md` + `CLAUDE.md` up front, so every later task has the
  index and mandatory rules to anchor to.
- **One task per `docs/` category** — each gated on "real repo-specific content,
  no placeholders, real commands, links resolve."
- **One task per major module** — its `README.md` (responsibility, public
  surface, how it's tested). This is the part that scales worst inline.
- **One task for the `.agents/` kit** — agents + skills + commands + catalogs,
  gated on "catalog matches disk."
- **One task to install the skill + scaffold `.dwp/` and `tmp/`** and offer addons.
- **Mandatory final task** — the onboard Phase 8 conformance self-check (run
  `/dwp-verify`), folded into the spec-mandatory **Final Review** (security pass,
  final-state validation, skills reconciliation). The Executive Report is optional.

Each task reuses the **repo's real validation command** as its gate (lint,
`md`-check, link-check, tests). The plan is created with `/dwp-create`, refined
with `/dwp-refine`, executed with `/dwp-execute`, resumed with `/dwp-resume`, and
inspected with `/dwp-status` — the same loop as any other plan. The full task
shapes live in the onboard sub-skill's
`onboard/templates/onboarding-plan.md` reasoning aid.

> **The Phase 0 onboarding rules do not relax.** Non-destructive, idempotent, and
> **no-placeholders** move *into* each task's Acceptance Criteria and gate; they
> do not disappear. A plan-driven onboarding that ships a placeholder doc is the
> same failure as an inline one.

This is distinct from the **orchestrator plan** (§13): orchestrator plans
coordinate child DWPs across **multiple repos**; the onboarding plan completes
documentation work within **one** large repo. A large monorepo may use both — an
onboarding plan to document itself, then orchestrator plans for cross-package
features.

---
