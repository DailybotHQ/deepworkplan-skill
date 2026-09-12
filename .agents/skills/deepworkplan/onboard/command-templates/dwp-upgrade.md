---
description: Check for a newer DeepWorkPlan skill and upgrade only with explicit consent (provided by the installed `deepworkplan` skill)
---

# /dwp-upgrade — provided by the `deepworkplan` skill

> Thin alias. The flow lives in the installed `deepworkplan` skill — this file
> only routes to it, so there is a single source of truth and no drift.

## What to do

Route this invocation to the **upgrade** sub-skill of the installed `deepworkplan`
skill and follow it: read `<skill-path>/deepworkplan/upgrade/SKILL.md` and execute
its flow. The check phase is **read-only**; nothing installs without your explicit
acceptance, and `.dwp/` plan history is never migrated by an upgrade.

> Other agents: invoke the skill's `deepworkplan-upgrade` sub-skill directly
> (`/deepworkplan-upgrade` in Claude Code, `#deepworkplan-upgrade` elsewhere).
> This `dwp-upgrade` file is the shorter, conventional alias.
