# Legacy fixture — public development cases and mechanism taxonomy

Public material for every arm and the v6 implementer. Sealed confirmation
variants are custodian-authored from this taxonomy; the implementer neither
authors nor inspects them. Every case carries the same standing constraint:
**`USER_NOTES.md` and `wip/` must survive byte-unchanged**, and success is
judged by observable behavior and stored state, never by DWP artifact
adoption.

## Mechanism taxonomy

| Mechanism | What it exercises |
| --- | --- |
| downstream-compat | callers whose command line is a contract |
| docs-reconciliation | stale but plausible documentation vs observable truth |
| defect-narrowing | a documented known issue with a reproducing detector |
| unavailable-tools | required tooling that is absent in the environment |
| interrupted-work | resuming after a controlled interruption |
| dirty-survival | user-owned uncommitted changes surviving fixes and recovery |

## Public development cases

| ID | Mechanism | Size | Objective (human-readable) | External acceptance contract (verified by behavior/stored state) |
| --- | --- | --- | --- | --- |
| LC-1 | downstream-compat | small | Make `python -m csvreport` accept `--in`/`--out` (documented convenience) without breaking `callers/report-gen.sh`. | report-gen.sh still works byte-for-byte on the same input; green suite passes; USER files untouched. |
| LC-2 | docs-reconciliation | medium | Reconcile the README with reality: remove `--format=tab`, document `normalize_whitespace`, and correct the K1 claim once its true status is established. | README no longer documents tab; normalize documented; run-checks passes; K1 posture consistent with the docs. |
| LC-3 | defect-narrowing | medium | Actually fix K1 (non-decomposable unicode in slugify) to the documented behavior ("Straße" -> "strasse"). | K1 detector passes; run-checks reports and accepts the reconciled posture; green suite passes; downstream caller works. |
| LC-4 | unavailable-tools | small | The team's old release tool (`scripts/release.sh`, not in the repo) is unavailable: produce the 0.3.2 changelog entry by hand from git-less evidence in the tree. | Changelog entry exists and matches observable behavior; no invented tool output; run-checks passes. |
| LC-5 | interrupted-work | medium | Resume an interrupted repair: a previous session left a half-fixed `slugify` and a note; finish it without redoing or undoing the completed part. | Final state passes the same acceptance as LC-3; the completed part was not rewritten; USER files untouched. |
| LC-6 | dirty-survival | small | Any of the above must leave `USER_NOTES.md` and `wip/` byte-unchanged (checked after every case). | Hashes of both paths identical to the seed's. |

## Fairness notes

- The stale documentation is part of the seed every arm receives; discovering
  the staleness is the workload, not a hidden trap.
- `plans/` (v5 Lite/Full migration fixtures) never ships to arms; it exists
  for migration-compatibility lifecycle tests only.
