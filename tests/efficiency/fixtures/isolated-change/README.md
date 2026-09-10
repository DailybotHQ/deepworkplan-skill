# Fixture: isolated-change

**Proves:** a change confined to one module is fully covered by that module's scoped tests; the scoped gate is sufficient and the full suite adds no signal.

**Stack:** Python 3 `unittest` (no dependencies) so scoped invocation is real:
full suite `python3 -m unittest discover -s tests -v`; scoped `python3 -m unittest tests.test_greeter -v`.

**Reset:** the fixture is immutable in git. Copy to a temp dir, then apply the seeded fault:
`cp -r <this dir> "$TMP" && cd "$TMP" && patch -p1 < seeded-fault.patch`

**Expected outcomes (see ../ORACLES.md):** clean control: full and scoped both pass. Seeded fault (in `src/greeter.py`): scoped `tests.test_greeter` FAILS (detected at the intended boundary); `tests.test_math` unaffected.
