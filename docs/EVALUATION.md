# Evaluation — reproducing the efficiency and quality evidence

Contributor-facing guide for the evaluation pack under `tests/efficiency/`
(design: `adr/0001-token-efficiency-architecture.md`). Nothing here is installed
or required by downstream users.

## What is measured, and what is not

| Measure | How | Status |
|---|---|---|
| Instruction bytes per flow — the **entry bundle** loaded at t0 | `bash tests/efficiency/measure-instruction-load.sh` | **measured** (filesystem bytes; `/4` is a labeled estimate) |
| Instruction bytes per named **end-to-end path** (entry plus the companions its triggers load, unique files, repeats disclosed) | same command; paths declared in `tests/efficiency/paths.tsv` | **measured** (same units, same limits) |
| Total context a real session consumes | — | **not measured, and neither column above bounds it** — see below |
| Seeded-fault detection at the intended boundary | `bats tests/efficiency-fixtures.bats` + agent replays | **measured** |
| Lifecycle guarantees end to end, with injected faults | `bats tests/reliability-acceptance.bats` (protocol: `tests/reliability/PROTOCOL.md`) | **measured**, deterministic — no agent involved |
| The v5 lifecycle driven by a fresh agent context | live runs scored by `tests/reliability/oracles/score-acceptance.py` | **measured per run**; an existence proof, never a rate |
| Gate wall-clock, retries, duplicate commands, interruptions, confirmations | recorded per replay from the agent trace | **measured** when the replay runs |
| Live tokens (input/output/cached/reasoning) | provider counters only, with `source` | **unavailable** unless the harness exposes counters; never estimated after the fact |

### The entry bundle is not a cap on a run

The entry bundle is what a flow reads before it starts; the path total is what
its named triggers add. Neither bounds the context a real session consumes.
Both exclude the repository's own files the agent reads (`AGENTS.md`,
`docs/TESTING_GUIDE.md`, the source under review, the plan folder), tool
output, the plan files a flow writes and re-reads, re-reads after a compaction
or handoff, the agent's own output, and anything the host injects — and in a
real run those dominate. A smaller entry bundle is a smaller starting read, not
a demonstrated live-session saving, and no fixed byte-to-token ratio, monetary
figure or amortization argument may be derived from either column. The script
prints these exclusions and this limit with every run;
`bats tests/context-accounting.bats` fails if it stops doing so.

Measured paths and phases are declared in `tests/efficiency/paths.tsv`, which
is checked against each flow's own `## Shared resources` tiers so the
measurement cannot drift from the contract. A read whose trigger always fires
(the Final Review companions on every `create`, for instance) stays counted on
the paths it fires on: moving an inevitable read behind a label is not a
reduction, and the suite asserts it did not happen.

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

## Portability and adoption evidence

Efficiency is only one axis. Two other claims are load-bearing for this
methodology, and each has its own write-up with its own stated limits:

| Claim | Evidence | Bounded by |
|---|---|---|
| A plan written by one agent can be resumed correctly by a different agent from a different vendor | [`evaluations/cross-agent-handoff.md`](evaluations/cross-agent-handoff.md) — bidirectional, Claude Code ↔ Codex CLI | Two harnesses only. The other seven supported agents have **installation** coverage, not behavioral: [`COMPATIBILITY.md`](COMPATIBILITY.md) |
| An existing repository upgrades in place without losing handwritten rules, custom skills or in-flight plans | [`evaluations/adoption-pilot.md`](evaluations/adoption-pilot.md) — three fixtures, checksum-verified, idempotent | Constructed fixtures, not a third-party production repo; only the Python fixture has a runnable toolchain here |
| Lite plans remain executable and may promote without weakening state contracts | [`evaluations/lite-plan-lifecycle.md`](evaluations/lite-plan-lifecycle.md) — conformance and schema fixtures | Structural coverage only; no cross-harness recommendation-quality claim |
| The v5 reliability guarantees, their guard cost and the instruction accounting behind them | [`evaluations/v5-reliability.md`](evaluations/v5-reliability.md) — entry bundles and end-to-end paths against `6bf7830` | Static instruction surface only; no live-agent, token or cost claim |

Neither is an efficiency claim, and neither may be cited as one. The handoff runs
were executed concurrently on a shared host, so their timings are meaningless.

## Snapshot efficiency results

The [efficiency evaluation](evaluations/token-efficiency.md) separates the
declared mandatory instruction inventory, historical self-reported replays,
instrumented paired observations and command-only seeded-fault experiments.
Its [records](evaluations/token-efficiency-data/protocol.json) pin the source
revisions and describe deviations from the ideal back-to-back protocol.

Reproduce the recorded aggregates with:

```bash
python3 tests/efficiency/summarize-paired.py
```

The summarizer rejects missing pairs and retains nonzero commands and incomplete
outcomes. It does not certify a live-token, billing or latency claim. Concurrent
runs, uninstrumented provider settings and a small fixture require narrower
conclusions. Three repetitions do not remove these limitations. A static
read-list reduction is not a measured live-session saving.
