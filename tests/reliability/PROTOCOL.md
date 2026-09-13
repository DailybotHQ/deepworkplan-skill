# v5 reliability acceptance protocol (frozen before any run)

Pre-registered protocol for the live, fresh-context acceptance runs and the
deterministic fault scenarios that back them. **Written and committed before
the first run.** Changing an expectation means changing it *here first*, with a
reason, and re-running the affected scenario — never adjusting the oracle after
seeing a result.

Nothing under `tests/` is installed; downstream users never need it.

## What this protocol is for, and what it refuses to be

It answers one question: **does the v5 lifecycle actually work end to end when a
fresh agent drives it from the repository alone?** It is not a comparison. There
is no v2 arm, no no-DWP arm, no other methodology and no "quality percentage".
Those are out of scope by decision, not by omission.

## The workload (frozen)

`workload/` — a tiny Python package (`src/ledger.py`) with plain `unittest`
tests, no dependencies, and its own `AGENTS.md` naming the real commands. It
carries one seeded defect, stated plainly in its `AGENTS.md`:

> `Ledger.transfer` records an overdrawing transfer instead of refusing it. A
> transfer that would overdraw the source must raise `ValueError` and record
> nothing.

The workload's four existing tests all pass before the work: the defect is a
missing behavior, not a red suite, so "make the tests pass" is not a shortcut
past it.

## The two required live runs

| Run | Flow | What it must exercise |
|---|---|---|
| **L1 — clean Lite lifecycle** | `create` (Lite) → `execute` → completion → `verify` | A real generated plan; the defect fixed; a test that fails before the fix; a conformant terminal plan |
| **L2 — Full lifecycle with interruption** | `create` (Full) → `execute` (interrupted) → **fresh context** → `resume` → completion → `verify` | Everything in L1, plus a controlled interruption and a resume that repeats nothing already done |

L2's interruption is **controlled**, not simulated in prose: the first session is
stopped after a task's work is on disk, and a **second agent with no
conversation carryover** is given only the workspace and the pack.

## Isolation and authorization (narrow, by design)

- One disposable workspace per run, created under a scratch root, `git init`-ed.
  Never the repository under test.
- The agent may read the pack under evaluation and its own workspace. Nothing
  else.
- **No pushes, no PRs, no messages, no installers, no network.** A run that
  needs any of them is a finding, not a pass.
- The runs are unattended: a step that would require a question is recorded
  verbatim and the run stops there. That is a finding, not a pass.

## Flow entry — what counts, and what does not

A run counts only if the agent **entered the flows**. Two independent signals
are required, and the artifact one is decisive:

1. **Artifact:** a plan folder exists with the shape only `create` writes —
   `README.md` with a task index and a `Plan Status:` line, `manifest.json`,
   `PROGRESS.md`, `state.json`, `analysis_results/` — and it passes the shipped
   read-only conformance checker.
2. **Report:** `ACCEPTANCE_REPORT.json` lists the pack files the agent actually
   read, by path, with byte counts.

Hand-writing a plan folder and calling it `create`, or implementing the change
directly and back-filling a plan, fails oracle A1. **Invocation by name**
(reading `skills/deepworkplan/SKILL.md` and routing from it) is a legitimate
entry path — it is the documented fallback for hosts without slash commands —
and is recorded as such in `META.json`.

## Oracles (pre-registered, artifact-derived)

`oracles/score-acceptance.py` evaluates these against the run directory. It
reads the **artifacts**, not the agent's narration: a report that claims a pass
the files do not show scores FAIL, and a missing field scores **UNVERIFIED**,
never PASS.

| ID | Oracle | How it is decided |
|---|---|---|
| A1 | The agent entered the flows | Plan folder has the created shape; the report names pack files read |
| A2 | The terminal plan is conformant | The shipped checker exits 0 on the plan folder |
| A3 | The defect is actually fixed | The oracle calls `transfer` overdrawing: it must raise `ValueError` **and** record nothing |
| A4 | A test encodes the fixed behavior | The oracle **reverts the source fix** and requires the run's own suite to fail; restores it and requires a pass. A test that passes either way is not coverage |
| A5 | The terminal state is coherent | `state.json` status `completed`, `completed_count == task_count`, every task carries a gate record with `exit_code: 0`, README has no unchecked box |
| A6 | Completion was a transaction | A `FINALIZATION.json` receipt exists and no `.finalizing.json` marker remains |
| A7 | Resume repeated nothing (L2) | No two commits carry the same task id; commit count does not exceed completed tasks plus the allowed plan-file commits; no gate record was re-run after its task's commit |
| A8 | The run asked nothing | The report's `questions_asked` is empty; a non-empty list is a finding, recorded, not smoothed over |

A3 and A4 are the reason this protocol exists: they are behavioral, they run
the code, and neither can be satisfied by text.

## Deterministic fault scenarios

`bats tests/reliability-acceptance.bats` runs the lifecycle guarantees against
the shipped helpers directly — no agent, no host capability, fully replayable in
CI. Each has a **clean control** that must pass and an **injected defect** that
must be refused at the named boundary:

| ID | Injected | Must be refused by |
|---|---|---|
| F1 | A gate record marked passing whose log admits the command did not run | the guarded writer (`state_contract.py`) |
| F2 | A gate selection that executed zero tests | the guarded writer |
| F3 | Malformed / truncated `state.json` | the read-only checker, without destroying the file |
| F4 | Evidence invalidated by a later `refine` | the writer, until the gate is re-run |
| F5 | A task marked completed whose log still says pending | the writer and the checker |
| F6 | A `log=` pointer that dangles or escapes the plan folder | the writer and the checker |
| F7 | A completion interrupted after the marker, before the receipt | `finalize_plan.py` recovery |
| F8 | Unrelated dirty work in the tree at closure | recorded, never silently committed or discarded |

## Arms, and the one that does not exist

- **Candidate arm:** the branch head under evaluation, fingerprinted in
  `META.json` (`pack_revision`, `pack_sha256`).
- There is **no baseline arm.** Comparing against v2 is out of scope for this
  protocol, so no such number may be computed from these runs.

## Limitations, stated before the results

- **One host.** The live runs use fresh contexts on the available host. Two
  processes of the same host are **not** cross-vendor evidence and are never
  labelled as such. Cross-vendor evidence remains the earlier, separate record
  in `docs/evaluations/cross-agent-handoff.md`.
- **One workload, small.** Nothing here generalizes to a large repository, a
  costly test suite, or a long-history plan.
- **A pass is an existence proof, not a rate.** These runs show the lifecycle
  can be driven correctly from the repository. They do not establish how often
  an arbitrary model does so, and no percentage may be derived from them.
- **No timing claims.** The runs share a host with other work; wall-clock
  numbers from them would be meaningless and are not recorded as results.
- **Unavailable is not passed.** If the host cannot produce a genuine fresh
  context, the live evidence is recorded as **blocked/unavailable**. The
  deterministic scenarios are not a substitute for it and may never be reported
  as if they were.
