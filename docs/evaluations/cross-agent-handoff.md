# Cross-agent handoff trial

Can one coding agent pick up a Deep Work Plan another agent started, using only
what is written in the repository? This is the experiment that answers it, and
its limits.

## Why it matters

The methodology's central claim is that the plan lives in the repository, not in
a session. If that is true, a *different* agent — different vendor, different
model, no shared context — must be able to read `.dwp/plans/…`, the README
checkboxes, the task logs, `state.json` and the git history, and continue
correctly. If it is not true, the plan is just session notes.

## Setup

Two harnesses, two vendors:

| Role | Harness | Version |
| --- | --- | --- |
| Agent A / Agent B | Claude Code (Anthropic) | this session |
| Agent A / Agent B | Codex CLI (OpenAI) | `codex-cli` 0.153.4 |

Two isolated git fixtures, each a tiny Python repo exposing `add(a, b)`, with
the same request: add `mul` and `power`, cover both with unit tests, document
both, preserve `add`. Validation command: `python3 -m unittest discover -s tests -t .`

The pack under test is the candidate (`skills/deepworkplan/` on
`feat/token-efficiency-upgrade`), copied to a frozen path. Agents were told to
stay inside their fixture, use a fixture git identity, and never push.

**Bidirectional by design.** A single direction could be luck, or could reflect
one agent writing notes only it can read.

- **Round A — Codex → Claude Code.** Codex creates the plan and executes only
  task 1, then stops.
- **Round B — Claude Code → Codex.** Claude creates the plan and executes only
  task 1, then stops.

In each round the second agent was given no information about the first beyond
the repository itself.

## Round A — Codex hands off to Claude Code

**Agent A (Codex)** created `PLAN_calc_mul_power` and stopped after task 1, with
commit `5f4a218`. Its `state.json` checkpoint read:

> Intentional Agent A handoff after Task 1 commit 5f4a218. STOP this session.
> Next agent reads `2.task_add_power.md`; Tasks 2 and 3 are pending, with no
> work started.

**Agent B (Claude Code)** resumed from those artifacts alone: the checkpoint
named the next task, the README checkboxes and task log confirmed what was
already done, and `2.task_add_power.md` fully specified the work — including its
own touched-surface analysis and selected gate. It implemented `power`, added
six unit tests (positive, zero and negative exponents, negative base, fractional
base, and `ZeroDivisionError` propagation for `power(0, -1)`), documented it, ran
the validation command, and committed `2671c12`.

**Result: pass.**

| Check | Outcome |
| --- | --- |
| Second agent identified the correct resume point unaided | Yes — from the checkpoint plus README/task-log agreement |
| No completed work redone | Yes — `mul` untouched |
| Validation after handoff | `Ran 11 tests … OK`; `git diff --check` clean |
| Final source state | `add`, `mul`, `power` all present; three documented APIs |
| Commit authorship | `5f4a218` AgentA (Codex), `2671c12` AgentB (Claude Code) |
| Plan/state parity after cross-agent write | `state.json in sync with README (2 completed)` |

An unexpected but useful result: Codex, reading only the candidate pack, emitted
a plan declaring `spec_version: 2.3.0` with the **single mandatory Final Review**
— the exact lifecycle this upgrade introduces — and wrote in the task body
"This is the single mandatory Final Review under DWP spec 2.3.0." The lifecycle
change is discoverable by an independent harness from the pack alone.

## Round B — Claude Code hands off to Codex

**Agent A (Claude Code)** created `PLAN_calc_extension` (three tasks) and
executed only task 1.

Worth recording: task 1's first validation run **failed** —
`ImportError: Start directory is not importable` — because the fixture's
`tests/` directory had no `__init__.py`. The failure, the fix, and the passing
re-run are all written into the task log rather than replaced by a clean-looking
"passed", because a gate that failed before it passed is part of the evidence.

**Agent B (Codex)** resumed from the artifacts alone, continued from task 2, and
carried the plan to completion.

**Result: pass.**

| Check | Outcome |
| --- | --- |
| Second agent identified the correct resume point unaided | Yes — resumed at task 2, the first unchecked entry |
| No completed work redone | Yes — `mul` from task 1 left intact |
| Plan carried to completion | 3 / 3 tasks checked |
| Validation after handoff | test suite green; `add`, `mul`, `power` all present, three documented APIs |
| State projection written by the second agent | `state.json` → `completed_count: 3/3`, `updated_by: {"agent": "AgentB (Codex)", "model": "GPT-6"}` |

Note that the second agent correctly recorded *its own* identity in the state
projection rather than inheriting the author's — the artifact says who did what.

It also absorbed agent A's mid-task correction without confusion: task 1's log
documented a failed gate, a fix, and a passing re-run, and the resuming agent
treated task 1 as genuinely complete rather than re-running or re-doing it.

## What this establishes — and what it does not

**Established:** a plan written by one agent, in this pack's format, carries
enough state for a different agent from a different vendor to resume it
correctly without any shared session context, in both directions.

**Not established:**

- Any claim about agents not tested here. Two harnesses were exercised. Cursor,
  Windsurf, Copilot, Cline, Gemini, OpenCode and Antigravity have installation
  coverage only — see [the compatibility matrix](../COMPATIBILITY.md).
- Any efficiency, latency or token claim. These runs were behavioral; they were
  also executed concurrently on a shared host, so timings are meaningless here.
- Anything about large or long-horizon plans. The fixture is three tasks in a
  tiny repository, chosen so the handoff itself is the variable under test.

**Environment note.** Codex's internal sandbox (`bwrap`) cannot create user
namespaces in this container, so runs used
`--dangerously-bypass-approvals-and-sandbox`, the flag documented for
externally sandboxed environments. The container is the sandbox; each run was
confined to its fixture directory with `-C`.
