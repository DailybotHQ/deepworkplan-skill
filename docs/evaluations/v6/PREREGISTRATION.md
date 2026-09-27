# v6 confirmation preregistration — BLOCKED

Frozen 2026-09-27T21:26Z as Task 25. **No confirmation outcomes exist.**
This file locks the *decision to not launch*, not a launchable design.

## Status

**BLOCKED / exploratory-not-authorized.** Two independent stop conditions:

1. Claude API `429 Weekly/Monthly Limit Exhausted`, reset
   `2026-10-03 04:48:05` (ablation service-reviewer SC-5 log).
2. Restricted custodian for sealed cases is not live on this host
   (`LAB_READINESS.md`; PROGRESS.md: user preparing
   `dwp-v6-custodian/{sealed,work,outbox}`).

The planning envelope (60 cases × 3 arms × 2 strata × 3 repeats = 1,080
starts) is **not** reduced retroactively. It remains the target when both
stops clear. Until then no confirmation.json is registered as launchable.

## Locked decisions (for a future unblocked freeze)

- Candidate: `skills/deepworkplan/` tree_digest
  `e8d44eebf27a710a29c1b88a58e75521fa5db42e29566910d1fe1a917c04d66e`
  (`analysis_results/CANDIDATE_MANIFEST.json`).
- Comparator: latest stable v5 at Task 1 freeze (v5.5.4) unless Task 25
  is re-run and a newer v5 exists.
- Architecture: retain-all v6 increments (Task 22).
- Joint GO rule, power, and caps: `analysis_results/POWER_AND_BUDGET.md`
  (planning figures only).
- Hidden cases: selected only by the restricted custodian; this working
  tree must not author them.

## What is forbidden

- Launching confirmation, long-horizon, or external campaigns from this
  freeze.
- Lowering n, arms, or GO thresholds to fit the remaining Claude cap.
- Treating development-r1 or ablation-r2 scores as confirmation.
