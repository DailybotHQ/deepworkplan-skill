---
description: Check for a newer DeepWorkPlan skill and, only on explicit acceptance, install it and re-run onboarding (provided by the installed `deepworkplan` skill)
---

# /dwp-upgrade — provided by the `deepworkplan` skill

> Thin alias. The flow lives in the installed `deepworkplan` skill — this file
> only routes to it, so there is a single source of truth and no drift.

## What to do

Route this invocation to the **upgrade** sub-skill of the installed `deepworkplan`
skill and follow it: read `.agents/skills/deepworkplan/upgrade/SKILL.md` and execute
its flow. The check phase is **read-only** (documents the channel it consults and
exits clean when offline); the download and re-onboarding run only after explicit
acceptance. Plans under `.dwp/` are never migrated or rewritten by an upgrade, and
any local adaptations are diffed and preserved before anything is overwritten.

> Other agents: invoke the skill's `deepworkplan-upgrade` sub-skill directly
> (`/deepworkplan-upgrade` in Claude Code, `#deepworkplan-upgrade` elsewhere). This
> `dwp-upgrade` file is the shorter, conventional alias.
