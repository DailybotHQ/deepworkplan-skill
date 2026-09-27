# v6 claims map — supported / unsupported / inconclusive

Each row is a claim someone might read into this candidate. Backing
kinds follow `GUARANTEES.md`. Empirical rows cannot be GO without
confirmation.

| Claim | Kind | Status | Evidence |
|---|---|---|---|
| v6 journal/scheduler/outcomes/ledger refuse unauthorized completion | Deterministic invariant | **supported** | `tests/v6-*.bats` (595/595 this session, Task 23 re-gate) |
| Pack is self-contained; dogfood byte-identical | Host/packaging | **supported** | `refresh-dogfood-skill.sh` 149 files; `CANDIDATE_MANIFEST.json` tree_digest `e8d44eeb…` |
| Create routes new plans to v6 only on pack line 6+ | Taught + measured | **supported** | r1 ablation drain: 0 v6 journals on 5.5.4; r2 6.0.0: 4/4 finished full-arm plans v6-shape |
| v6 increases independently accepted completion vs latest v5 (Q1) | Empirical | **inconclusive** | confirmation n=0 |
| v6 reduces cost per accepted result (Q2) | Empirical | **inconclusive** | confirmation n=0; development token/USD ratios are lane-caveated observations |
| v6 improves sustained interrupted work (Q3) | Empirical | **inconclusive** | Task 27 not run |
| One-factor ablation identifies removable complexity (Q4) | Empirical | **inconclusive** | variants not scored; default **retain-all** |
| Reviewer-only arm is not the methodology | Empirical | **inconclusive** | reviewer inventories empty/partial |
| Hidden-case GO | Empirical | **unsupported as a current claim** | sealed cases never unsealed |
| Slash commands / `.dwp/plans/` unchanged | Compatibility | **supported** | `MIGRATION.md`; public surface not renamed |

No row here is a publication GO.
