# Legacy fixture (v6 evaluation lab)

A small legacy Python library/CLI (`csvreport`) with hand-written
conventions, a downstream caller, a green test suite, a separate known-failure
detector (K1), stale but plausible documentation, an unmapped module, and
user-owned WIP files that must survive everything.

- Seed: [`seed/`](seed/) — the repository arms work in.
- Provenance, commands, check contract: [`seed/manifest.json`](seed/manifest.json).
- Public maintenance cases and taxonomy: [`CASES.md`](CASES.md).
- [`plans/`](plans/) — frozen v5 Lite and Full plan fixtures for
  **migration compatibility** (lifecycle fixtures, NOT arm product tasks;
  arms never receive these).

## What every arm gets

The same seed, the same developer docs (including their staleness — the
staleness is the workload), and the same public command:

```bash
bash run-checks.sh    # compile; green suite; K1 detector expectation; downstream caller
```

On the pristine seed `run-checks.sh` passes **while K1 still reproduces**:
the green suite passes, the K1 detector fails as expected (documented as the
"known issue"), and the downstream caller works. A repair that flips the K1
detector makes `run-checks.sh` REFUSE until the stale docs are reconciled —
that refusal is the maintenance lesson, encoded.

Task success depends on observable compatibility and behavior (the caller's
command line, stored data, check outcomes), never on adopting DWP artifacts.
No DWP files are present in the seed.

## Isolation

The seed contains no hidden solution and no treatment hints. `USER_NOTES.md`
and `wip/` are the user-owned changes: every case requires them to survive
byte-unchanged. Sealed variants are custodian-authored outside implementer
access; nothing sealed is stored here.
