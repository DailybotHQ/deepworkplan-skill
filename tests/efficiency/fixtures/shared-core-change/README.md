# Fixture: shared-core-change

**Proves:** a change in a widely-imported core module breaks a *consumer's* test that path-scoped selection would not run; validation must widen to affected consumers (or the full suite).

**Stack:** Python 3 `unittest` (no dependencies) so scoped invocation is real:
full suite `python3 -m unittest discover -s tests -v`; scoped `python3 -m unittest tests.test_formatter -v`.

**Reset:** the fixture is immutable in git. Copy to a temp dir, then apply the seeded fault:
`cp -r <this dir> "$TMP" && cd "$TMP" && patch -p1 < seeded-fault.patch`

**Expected outcomes (see ../ORACLES.md):** clean control: all pass. Seeded fault (in `src/core.py`, which `formatter` and `report` import): scoped `tests.test_core` still PASSES (the fault is only observable through a consumer); `tests.test_report` FAILS. A gate that ran only `test_core` would falsely pass — the oracle requires the affected-consumer widening to catch it.
