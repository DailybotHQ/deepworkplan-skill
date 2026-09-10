# Evaluation — reproducing the efficiency and quality evidence

Contributor-facing guide for the evaluation pack under `tests/efficiency/`
(design: `adr/0001-token-efficiency-architecture.md`). Nothing here is installed
or required by downstream users.

## What is measured, and what is not

| Measure | How | Status |
|---|---|---|
| Instruction bytes per flow (compulsory read set) | `bash tests/efficiency/measure-instruction-load.sh` | **measured** (filesystem bytes; `/4` is a labeled estimate) |
| Seeded-fault detection at the intended boundary | `bats tests/efficiency-fixtures.bats` + agent replays | **measured** |
| Gate wall-clock, retries, duplicate commands, interruptions, confirmations | recorded per replay from the agent trace | **measured** when the replay runs |
| Live tokens (input/output/cached/reasoning) | provider counters only, with `source` | **unavailable** unless the harness exposes counters; never estimated after the fact |

## Arms and protocol

- **Baseline arm:** v2.17.1 at commit `eaf54994ac5894b74849f1b8d2b6137df8d83e30`, in a git worktree:
  `git worktree add /tmp/dwp-baseline eaf54994ac5894b74849f1b8d2b6137df8d83e30`.
- **Candidate arm:** the head under evaluation.
- Both arms run **back-to-back in the same session, harness and model settings** on fresh
  copies of the same fixture (cold), then once warm; at least three paired runs for any
  quantitative live claim; failures and retries are counted, never excluded.
- Oracles and scoring are pre-registered in `tests/efficiency/fixtures/ORACLES.md` and are
  changed only there, with a reason, before rerunning both arms.

## Fixtures

See `tests/efficiency/fixtures/*/README.md`. Code fixtures use Python `unittest` with no
dependencies so scoped invocation (`python3 -m unittest tests.test_x`) is real. Plan
fixtures are copied to a temp directory and `git init`-ed by their README's reset command.

## Behavioral replays (Task 18 protocol)

Structural checks cannot establish behavioral claims. The behavioral evidence in
this repository comes from **agent replays**: a fresh agent context, given only
the installed skill pack and one isolated workspace copied from
`tests/efficiency/fixtures/`, running a real flow end to end and writing an
`EVAL_REPORT*.json` with the evidence its oracle needs.

Rules that make a replay count:

- **Isolation.** One workspace per scenario under a scratch root (never the
  repository under test); the agent may read only the pack under evaluation and
  its own workspace; no network.
- **Arms.** The *candidate* arm reads `skills/deepworkplan/` at the revision
  under test; the *baseline* arm reads a pinned export of the previous release
  (`git archive <tag> skills/deepworkplan`), same prompt, same workspace shape,
  back-to-back in the same session.
- **Unattended.** The replay may not ask a question. A procedure step that would
  require one is recorded verbatim in the report and the replay stops there —
  that is a finding, not a pass.
- **Evidence, not narration.** Each report carries the commands run with exit
  codes, the files read with byte counts, the git commits, and the specific
  fields its oracle scores. `tests/efficiency/score-replays.py` reads the reports
  and prints PASS / FAIL / **UNVERIFIED** — a missing field scores UNVERIFIED,
  never PASS.
- **Seeded faults.** Fault fixtures ship a `seeded-fault.patch`; the oracle names
  the boundary that must catch it (scoped test, widened consumer test, runtime
  test on a config-only diff, integration test at a seam). Catching it later than
  the intended boundary is a FAIL.

Run: `python3 tests/efficiency/score-replays.py <scratch-root> [--json out.json]`.
