# Fixture: config-change

**Proves:** a non-code change (a JSON config file) alters behavior; classification must be by *effect*, not file extension — treating it as prose and skipping runtime tests is the failure mode.

**Stack:** Python 3 `unittest` (no dependencies) so scoped invocation is real:
full suite `python3 -m unittest discover -s tests -v`; scoped `python3 -m unittest tests.test_limits -v`.

**Reset:** the fixture is immutable in git. Copy to a temp dir, then apply the seeded fault:
`cp -r <this dir> "$TMP" && cd "$TMP" && patch -p1 < seeded-fault.patch`

**Expected outcomes (see ../ORACLES.md):** clean control: pass. Seeded fault (in `config/limits.json` only — no `.py` touched): `tests.test_limits` FAILS. An agent that classifies `.json` as prose and runs only link/schema checks misses it.
