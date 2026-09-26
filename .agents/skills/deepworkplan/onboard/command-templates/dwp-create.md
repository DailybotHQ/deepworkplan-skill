---
description: Create a deep work plan for short or long work — materializes an executable Lite plan, promoted to Full task files only when needed (provided by the installed `deepworkplan` skill)
---

# /dwp-create — provided by the `deepworkplan` skill

> Thin alias. The flow lives in the installed `deepworkplan` skill — this file
> only routes to it, so there is a single source of truth and no drift.

## What to do

Route this invocation to the **create** sub-skill of the installed `deepworkplan`
skill and follow it: read `<skill-path>/deepworkplan/create/SKILL.md` and execute
its flow. Ordinary requests — at any scale, including a single small fix —
materialize an executable **Lite** plan under `.dwp/plans/PLAN_{name}/`; no
draft file is written — the Lite plan is the reviewable artifact. `trust`/`auto`
skips the review and `lite`/`full` override the recommendation, at either edge of
the request. Plan output lands in this repo's
gitignored `.dwp/` — never the legacy
`.agent_commands/agent_deep_work_plans/results/` path.

> Other agents: invoke the skill's `deepworkplan-create` sub-skill directly
> (`/deepworkplan-create` in Claude Code, `#deepworkplan-create` elsewhere). This
> `dwp-create` file is the shorter, conventional alias.
