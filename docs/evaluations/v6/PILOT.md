# v6 baseline pilot — methods and launch boundary

Purpose: validate the experiment apparatus and estimate baseline success and
variance on development cases BEFORE any v6 comparative result exists
(preregistration, `partitions.baseline_pilot`). Design of record:
[`tests/evaluation/v6/protocol/design.json`](../../../tests/evaluation/v6/protocol/design.json).
This pilot is development-only; its numbers are never v6 evidence.

## Frozen design (Task 10, 2026-09-26)

Three sub-campaign configs (the lab driver is single-seed per campaign), each
4 public development cases × arms A/B × 2 strata × 2 repeats = 32 starts;
96 planned starts total:

| Config | Cases | Seed |
| --- | --- | --- |
| `baseline-pilot-astro.json` | AC-2, AC-3, AC-5, AC-6 | `fixtures/astro/seed` |
| `baseline-pilot-service.json` | SC-2, SC-4, SC-5, SC-9 | `fixtures/service/seed` |
| `baseline-pilot-legacy.json` | LC-1, LC-2, LC-3, LC-6 | `fixtures/legacy/seed` |

- Arms: **A no-DWP** (no pack, nothing DWP-visible) and **B latest-v5** (the
  frozen v5.5.4 snapshot; full onboarding/create cost is included in arm B's
  cost, with an already-onboarded track recorded separately).
- Strata: `claude-code` and `codex-cli` CLI launches, pinned per block;
  randomized arm order with a recorded seed; randomized block order.
- Every attempted start is inventoried (including failures and replacements);
  scoring uses the frozen oracles only.

## Launch boundary (recorded 2026-09-26)

The pilot is a PAID campaign and the preregistered resource envelope is
UNSET: the runner refuses all three configs (`validate` exits 1 with the
envelope refusal — proven in `analysis_results/gates/task10-boundary-gates.log`).
`design.json resource_envelope` stays UNSET until the developer approves the
caps proposed in the owning plan's `RESOURCE_PROPOSAL.md` (8.00 USD/start,
4,000 USD total) or supplies an applicable existing budget. Additionally, the
post-freeze launch-preparation items, as of 2026-09-26:

1. ~~real-CLI launch wrappers~~ — DONE (`tests/evaluation/v6/adapters_launch/`,
   proven by real per-CLI canaries);
2. ~~prompt materialization~~ — DONE (the driver writes TASK.md into each
   workspace; pack-carrying arms receive the documented method overlay);
3. calibration of the remaining pilot oracles — IN PROGRESS (AC-1/SC-9/LC-3
   and AC-6 are calibrated; the other pilot cases are being calibrated to
   the same matrix before they may score);
4. ~~codex session-log counter extraction~~ — DONE
   (`adapters/codex_usage.py`: per-turn records only, totals ignored to
   avoid double counting; input reported as fresh input, excluding cached).

## When unblocked, the sequence is

`prepare` (each family) → preflight (validate all three configs; envelope
gate passes) → `run` per sub-campaign (attempt inventory, randomized order,
canaries) → `score` → `analyze` → variance/power notes into
`LAB_READINESS.md`. New runs after any apparatus repair are labeled
separately and never pooled with incompatible designs.
