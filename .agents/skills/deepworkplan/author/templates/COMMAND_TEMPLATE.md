---
description: <one line — what this command delegates to; start with a verb>
---

# /<cmd> — provided by the <skill-or-agent> skill

> Thin delegator. The flow lives in the target skill or agent — this file only
> routes to it, so there is a single source of truth and no drift.

## What to do

1. Read `<skills-dir>/<name>/SKILL.md` (or `<agents-dir>/<name>.md`) fresh and
   route to the procedure it defines.
2. Follow that procedure exactly, passing along any arguments. Do not improvise
   and do not embed logic here — logic stays in the skill/agent so updates
   propagate to every entry point.

## Notes

- <One or two constraints worth restating at invocation time (e.g. read-only,
  consent-gated, batched) — nothing else.>
- Other agents: invoke the target skill or agent directly if this alias is not
  present in your harness.
