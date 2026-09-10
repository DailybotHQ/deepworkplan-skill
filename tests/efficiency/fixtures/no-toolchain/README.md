# Fixture: no-toolchain

**Proves:** onboarding a repository with source code but **no tests, no lint, no AGENTS.md and no docs/** must *propose* a unit-first toolchain with a scoped invocation pattern from the start — and must not claim scoped-test readiness it cannot verify.

**Contents:** two small modules, no `tests/`, no config.

**Reset:** copy to a temp dir; run the `onboard` flow of the skill under evaluation against the copy.

**Expected outcomes (see ../ORACLES.md):** the generated `docs/TESTING_GUIDE.md` names a concrete full command, a concrete scoped pattern, the path→test mapping rule and the pyramid posture, all marked *proposed* (not verified) until a first test exists; `AGENTS.md` is created; no file outside the onboarding surfaces is modified.
