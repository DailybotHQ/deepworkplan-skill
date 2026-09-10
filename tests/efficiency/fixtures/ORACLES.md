# Evaluation oracles (pre-registered — written before any candidate change)

Every fixture below has a fixed expected outcome. Tasks 18–20 replay these; a
candidate that changes an expectation must change it **here first**, with a reason,
and rerun both arms. Seeded faults live in each fixture's `seeded-fault.patch`.

Conventions: **scoped** = the command an agent derives from the task's Touched
Surface; **affected** = scoped widened to consumers; **full** = discover all tests.

| Fixture | Clean control | Seeded fault | Must be detected by | Falsifies |
|---|---|---|---|---|
| `isolated-change` | full ✓ scoped ✓ | `src/greeter.py` | **scoped** `tests.test_greeter` (fails) | L2 if scoped misses it |
| `shared-core-change` | all ✓ | `src/core.py` (imported by 2 consumers) | **affected** widening: `tests.test_report` fails; `tests.test_core` alone still passes | L2 if a core change is validated by `test_core` only |
| `config-change` | ✓ | `config/limits.json` (no `.py` touched) | runtime tests (`tests.test_limits` fails); prose-only checks miss it | effect-based classification |
| `integration-seam` | ✓ | `src/server.py` response key | **integration** `tests.test_integration` fails; mocked unit `tests.test_client` passes | seam rule (§2.8 ADR) |
| `no-toolchain` | n/a | — | onboarding output: `docs/TESTING_GUIDE.md` with full cmd, scoped pattern, mapping rule, pyramid posture, all marked *proposed*; `AGENTS.md` created; nothing else touched | onboarding proposal rule |
| `interrupted-plan` | — | interruption between implementation and gate/commit | resume: evidence inspected first; gate run **once**; commit **once**; Task 2 `[x]`; no re-implementation; **zero questions** | recovery contract |
| `legacy-plan-v217` | — | — | new checker **PASS** (legacy shape accepted); missing Touched Surface → **finding**; executor runs the plan's own full gate (fallback), does not add/remove final tasks | compatibility row 1 |
| `long-history-plan` | ✓ | — | Task 51 uses integer cents (D-7 honored); resume trace reads entry 7 via the task's pointer, **not** all 50 entries by default | L5 |
| `new-shape-plan` | ✓ | — | new checker **PASS**, zero findings; **old** (v2.17) checker FAIL on missing discovery/report tasks (expected forward-incompatibility) | compatibility row 4 |

## Scoring (fixed)

- **Must-pass (hard gate):** every "Must be detected by" cell above; zero mid-plan questions in `interrupted-plan` and in the Task 18 20-step run; no duplicate commit/gate in `interrupted-plan`.
- **Quality score (0–3 each, per created plan on `isolated-change` + `shared-core-change`):** detailed acceptance criteria present; validation commands runnable and correctly scoped; task ordering and scope sane; recovery information (Touched Surface, Read Before Starting) present. Reported per arm; candidate must not score lower than baseline on any axis.
- **Fluency counters (per run):** avoidable confirmations; redundant reads of unchanged files; repeated gates on equivalent inputs; recovery steps after interruption; time to first validated task.
- **Cost counters (per run):** instruction bytes loaded (mandatory, static); gate wall-clock (mandatory); retries; tokens **only** from provider counters with `source` recorded, else `unavailable`.

## Arms

- **Baseline arm:** skill at `eaf54994ac5894b74849f1b8d2b6137df8d83e30` (v2.17.1), checked out in a git worktree.
- **Candidate arm:** the final head of `feat/token-efficiency-upgrade`.
- Both arms run in the **same session/harness/model settings, back-to-back**, on fresh copies of the same fixture (cold) and once more warm; at least three paired runs for any quantitative live claim; failures and retries included.

| `create-modes` (C1–C5) | — | — | see `create-modes/README.md`: trust = no draft + README last + spec_version 2.3.0 + zero questions; explicit draft wins; partial folder → complete/discard, nothing unrelated overwritten | L4, §3 |
| `resume-scenarios` (S1–S9) | — | interruption boundaries, stale/contradictory state, takeover, re-validate marker | exactly one missing step completed; no repeated gate/commit/report; bounded reads (S7); legacy untouched (S8) | recovery contract, L5 |

## Fixture corrections (Task 16) — recorded per the immutability rule

- Plan fixtures gained the `Plan Status: X/N completed` line the checker requires (the fixture READMEs said it in prose only).
- `new-shape-plan` Task 3 now names the Final Review's three parts (security pass, final-state validation, skills reconciliation) — the checker verifies objective structure, not the filename.
- A task file without a `## Validation` heading gained one. Oracles unchanged.
