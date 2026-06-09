---
description: Verify repo/plan conformance against the DWP spec (read-only) (provided by the installed `deepworkplan` skill)
---

# /dwp-verify — provided by the `deepworkplan` skill

> Thin alias. The flow lives in the installed `deepworkplan` skill — this file
> only routes to it, so there is a single source of truth and no drift.

## What to do

Route this invocation to the **verify** sub-skill of the installed `deepworkplan`
skill and follow it: read `.agents/skills/deepworkplan/verify/SKILL.md` and execute
its flow. This is a **read-only** conformance check (repo onboarding state or a
plan against the spec) — it reports findings and never mutates files.

> Other agents: invoke the skill's `deepworkplan-verify` sub-skill directly
> (`/deepworkplan-verify` in Claude Code, `#deepworkplan-verify` elsewhere). This
> `dwp-verify` file is the shorter, conventional alias.
