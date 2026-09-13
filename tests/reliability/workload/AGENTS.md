# AGENTS.md — ledger workload

A deliberately tiny Python package used as a frozen acceptance workload for the
DWP reliability evaluation. It is a **fixture**: never depend on it at runtime.

## Project overview

`src/ledger.py` is an append-only ledger in integer cents. `tests/` is plain
`unittest` with no third-party dependencies, so scoped invocation is real.

## Quick Commands

```bash
python3 -m unittest discover -s tests -t . -v   # full suite
python3 -m unittest tests.test_ledger -v        # scoped: the ledger module
```

## Rules

- Amounts are **integer cents**. Never introduce floats.
- Every behavior change needs a test that fails before the fix and passes after.
- English only. No new dependencies — the standard library is the whole toolchain.

## Known defect (the work)

`Ledger.transfer` records an overdrawing transfer instead of refusing it: a
transfer larger than the source balance leaves the source negative. A transfer
that would overdraw the source must raise `ValueError` and record **nothing**
(no partial entry).
