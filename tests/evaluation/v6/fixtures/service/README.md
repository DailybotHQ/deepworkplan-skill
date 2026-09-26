# Service fixture (v6 evaluation lab)

A minimal stateful HTTP service for testing whether gains extend to stateful
behavior where builds and visual output prove nothing. Python 3.9+ stdlib
only (`http.server` + `sqlite3` + `unittest`), per-run disposable database,
deterministic concurrency barriers instead of sleeps.

- Seed: [`seed/`](seed/) — `server.py` (the service), `tests/test_service.py`
  (behavioral suite), `README.md` (developer-facing interface + setup).
- Provenance, commands and check contract: [`seed/manifest.json`](seed/manifest.json).
- Public cases and mechanism taxonomy: [`CASES.md`](CASES.md).

## What every arm gets

```bash
python3 server.py                          # run the service (disposable LEDGER_DB)
python3 -m unittest discover -s tests -v   # behavioral suite over real HTTP
```

The lab driver validates the family with these commands in a disposable copy
(`lab.py validate --family service --execute-checks`): compile, boot the real
service in-process, and verify idempotent replay, refused transfers recording
nothing, unauthorized reads, stable pagination, barrier-aligned concurrent
duplicate delivery, and compatible schema evolution.

Fixture-local documentation only; shared integration (Task 8) owns anything
cross-family. Nothing sealed is stored in this tree.
