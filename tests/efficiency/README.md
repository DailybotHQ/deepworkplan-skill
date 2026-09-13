# Efficiency evaluation pack (dev-only, never installed)

Reproducible fixtures, oracles and measurement for the token-efficiency upgrade
(ADR `docs/adr/0001-token-efficiency-architecture.md`). Nothing here ships to
users; downstream repositories never need it.

- `fixtures/` — nine immutable fixture repositories/plans (see `fixtures/ORACLES.md`).
- `measure-instruction-load.sh` — static per-file bytes, the **entry bundle** per
  flow, and the **end-to-end paths** declared in `paths.tsv`, with repeated reads,
  phase triggers, exclusions and the limits of the numbers printed alongside them.
- `paths.tsv` — the named end-to-end read paths (phase, literal trigger, file).
  Guarded by `../context-accounting.bats`: every file must exist and must be
  declared in the governing flow's `## Shared resources` tiers.
- `../efficiency-fixtures.bats` — self-checks: fixtures exist, clean controls pass, seeded faults are detected at the intended boundary.

Reproduce: `bash tests/efficiency/measure-instruction-load.sh`,
`bats tests/efficiency-fixtures.bats` and `bats tests/context-accounting.bats`.
Results and their limits: `docs/evaluations/v5-reliability.md`.
Full protocol and arms: `docs/EVALUATION.md`.
