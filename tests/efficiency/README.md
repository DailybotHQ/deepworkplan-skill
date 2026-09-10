# Efficiency evaluation pack (dev-only, never installed)

Reproducible fixtures, oracles and measurement for the token-efficiency upgrade
(ADR `docs/adr/0001-token-efficiency-architecture.md`). Nothing here ships to
users; downstream repositories never need it.

- `fixtures/` — nine immutable fixture repositories/plans (see `fixtures/ORACLES.md`).
- `measure-instruction-load.sh` — static per-file bytes and compulsory read set per flow.
- `../efficiency-fixtures.bats` — self-checks: fixtures exist, clean controls pass, seeded faults are detected at the intended boundary.

Reproduce: `bash tests/efficiency/measure-instruction-load.sh` and `bats tests/efficiency-fixtures.bats`.
Full protocol and arms: `docs/EVALUATION.md`.
