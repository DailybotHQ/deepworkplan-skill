# Reliability acceptance pack (dev-only, never installed)

The frozen workload, oracles and protocol behind the v5 reliability acceptance
evidence. Nothing here ships to users; downstream repositories never need it.

- [`PROTOCOL.md`](PROTOCOL.md) — the protocol, **written and committed before
  the first run**: workload, the two required live runs, isolation rules, what
  counts as flow entry, the pre-registered oracles A1–A8, the deterministic
  fault scenarios F1–F8, the arms, and the limitations stated up front.
- `workload/` — the frozen workload: a tiny Python package with plain
  `unittest` tests, no dependencies, its own `AGENTS.md`, and one seeded defect
  stated plainly (`Ledger.transfer` records an overdraw instead of refusing it).
  Its four existing tests **pass** before the work, so "make the suite green" is
  not a shortcut past the defect.
- `oracles/score-acceptance.py` — scores one run directory against A1–A8. It
  reads the **artifacts**, not the agent's narration: a claim the files do not
  support scores FAIL, and a missing field scores UNVERIFIED, never PASS. A3
  calls the fixed code; A4 reverts the fix and requires the run's own suite to
  fail, then restores it and requires a pass.
- `evidence/` — the sanitized, committed result of each run: `META.json`,
  the scored oracle output, and the run's own report. Raw logs, prompts and
  absolute paths stay in the plan folder, outside this repository.
- `../reliability-acceptance.bats` + `../reliability_acceptance_test.py` — the
  deterministic scenarios F0–F8, replayable in CI with no agent and no host
  capability.

## Reproduce

```bash
bats tests/reliability-acceptance.bats                        # deterministic F0-F8
python3 tests/reliability/oracles/score-acceptance.py <run>    # score a live run
```

A live run needs a fresh agent context and an isolated workspace; see
`PROTOCOL.md`. The deterministic scenarios need neither and are **not** a
substitute for the live evidence — the protocol says so explicitly, and the
published record labels the two separately.

## What this pack refuses to be

No baseline arm, no v2 comparison, no other methodology, no completion rate and
no quality percentage. A passing live run is an existence proof that the
lifecycle can be driven correctly from the repository alone — not a measurement
of how often an arbitrary model does so.
