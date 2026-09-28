# Migrating to DeepWorkPlan v6

This note is the non-bot-owned migration record for the v6 candidate.
It does **not** edit `CHANGELOG.md`, frontmatter `version:` fields, or
git tags (those stay bot-owned). Empirical superiority is **not**
claimed here: confirmation (Tasks 25–26) has not run.

## What changes for already-onboarded repositories

- **Existing v5/v2 plans keep working.** Execute detects generation by
  plan shape (`contract.json` / `contracts/` chain vs Full/Lite v5
  files). A 5.x plan is never silently migrated mid-flight.
- **New plans from a 6.x pack line default to the v6 contract.**
  `create` Step 0.3 opens the v6 loop when the pack's `version:` line is
  6+ (or the developer explicitly asks for a v6 plan). A 5.5.4 pack line
  never reaches that gate — measured in Task 22's r1 ablation drain.
- **`.dwp/plans/` and slash-command names are unchanged.** `DWP_DIR` /
  `DWP_AGENT_TOOL` remain the public overrides (`shared/context.sh`).
- **Onboarding symlink instruction** pins `.claude` / `.cursor` links at
  the repository root and verifies `readlink` (Task 21 defect T21-6 /
  r2 repair R2-2).

## What operators should do

1. Install or upgrade the pack through the documented channel
   (`npx skills add …` or `setup.sh`). Do not hand-edit `version:`.
2. Leave in-flight v5 plans on v5 until they complete or are explicitly
   refined/migrated.
3. For a new body of work, run `/dwp-create` (or `create`) on a 6.x
   pack so the v6 contract, journal, and views attach.
4. If evaluation workspaces sit inside another git work tree, set
   `DWP_DIR` to the workspace-local `.dwp` (the pack's documented
   override; evaluation harness repair #15).

## What this release does not claim

- No GO on hidden cases, long-horizon, or external replication.
- Ablation variants were not finished (Claude weekly/monthly 429 until
  2026-10-03). Architecture default is **retain** every v6 increment.
- Token/USD ratios in `DEVELOPMENT.md` are development-r1 observations
  with lane caveats, not a launch claim.

## Breaking-change PR body (draft, unused until a release PR)

```
feat(skill)!: ship the v6 execution contract on a 6.x pack line

New plans from this pack use the v6 contract (journal, scheduler,
outcome verification, generated views). Existing v5 plans keep
shape-based execution. Slash commands and `.dwp/plans/` are unchanged.
See docs/evaluations/v6/MIGRATION.md.
```
