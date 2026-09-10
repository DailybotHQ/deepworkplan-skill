# Fixture: integration-seam

**Proves:** a contract change at a real seam is invisible to unit tests that mock the collaborator; only an integration test that wires the real parts catches it.

**Stack:** Python 3 `unittest` (no dependencies) so scoped invocation is real:
full suite `python3 -m unittest discover -s tests -v`; scoped `python3 -m unittest tests.test_client -v`.

**Reset:** the fixture is immutable in git. Copy to a temp dir, then apply the seeded fault:
`cp -r <this dir> "$TMP" && cd "$TMP" && patch -p1 < seeded-fault.patch`

**Expected outcomes (see ../ORACLES.md):** clean control: pass. Seeded fault (server changes its response key from `total` to `sum`): unit `tests.test_client` (mocked server) still PASSES; integration `tests.test_integration` FAILS. The oracle requires an integration/contract test at this seam.
