# v6 evaluation results — INCONCLUSIVE (confirmation not run)

Date: 2026-09-27. Plan `PLAN_v6_verified_autonomy` stopped at Task 26.
This file is **not** a confirmation result set. Denominators below are
absolute. Missing campaigns are named, never zero-filled.

## Confirmation, long-horizon, external

| Campaign | Planned | Run | Reason |
|---|---:|---:|---|
| Sealed three-arm confirmation | 1080 starts | 0 | Task 25 freeze `blocked`; no `confirmation.json` |
| Long-horizon / interruption / handoff | 72 campaigns | 0 | inherits Task 26 block |
| External replication | 72 starts | 0 | inherits Task 26 block |

Stops (not reduced n): Claude `429 Weekly/Monthly Limit Exhausted`
reset **2026-10-03 04:48:05**; restricted custodian not live.

Intention-to-treat analysis of confirmation is **undefined** (n=0).

## Development r1 (Task 21) — measured, not confirmation

Arm C only vs frozen pilot A/B. 3 families × 4 cases × 2 strata × 2
repeats = 48 cells. Commit `dd545fd`. Oracle identity
`oracle-commitments-4ebff28.json`.

Published in `DEVELOPMENT.md` / `CANDIDATE_SELECTION.md`: 38 PASS / 8 FAIL
/ 2 ERROR on last-record arm C. Those counts are development, not G5.

## Ablations (Task 22) — measured routing, incomplete variants

| Cell | Treatment | Status | Calibrated verdict |
|---|---|---|---|
| SC-5 | full r2 | completed | PASS |
| SC-9 | full r2 | completed | PASS |
| LC-1 | full r2 | completed | FAIL (caller JSON mode / LC-1b) |
| AC-2 | full r2 | timeout 2700 s | ineligible (progress-positive) |
| remaining 26/30 | variants + reviewer | `provider_refused` or empty inventory | not scored |

Manipulation: r1 drain 0 v6 journals (pack line 5.5.4). r2 full-arm 4/4
`spec_version` 6.0.0. SC-9 wrote 4 events of **type** `control_pair`, each
with `verdict=control_unavailable` (old_leg.available=false, D3-3 dirty
fingerprint; new_leg.outcome=PASS). That is not a discriminating close
(old FAIL, new PASS).

Invoiced (ledger scope): development live $77.90 + ablation drain $1.78
+ r2 $18.49 ≈ **$98.17**. Headroom vs $300 remains; provider cap bound.

## Joint GO rule

Never applied. No confirmation sample. Development/ablation numbers are
not substituted for it.
