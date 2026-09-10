# Fixture: resume-scenarios (Task 11 → replayed in Task 18)

Interruption-boundary and staleness scenarios, each on a copy of an existing fixture. The oracle is always: **exactly one missing step is completed; nothing is repeated; zero questions unattended**.

| # | Base | Setup (after `git init && git add -A && git commit`) | Resume must |
|---|---|---|---|
| S1 | `../interrupted-plan/` | as its README (work uncommitted, no gate record) | run the gate once, commit once, mark `[x]` |
| S2 | `../interrupted-plan/` | additionally record a passing gate in `state.json` for Task 2 with the current tree fingerprint | reuse the gate (inputs equivalent), commit once — **no rerun** |
| S3 | `../interrupted-plan/` | commit the Task 2 work (`feat: add math helper`) but leave README `[ ]` and no log | detect the commit in `git log`; complete log → README → PROGRESS → state; **no second commit** |
| S4 | `../new-shape-plan/` | set README Task 1 `[x]` but `state.json` Task 1 `pending` | regenerate `state.json` from the README; record the reconciliation; continue at Task 2 |
| S5 | `../interrupted-plan/` | add a `PROGRESS.md` line claiming "Task 2 committed" with no such commit | distrust the summary; treat Task 2 per the evidence (uncommitted); record the contradiction |
| S6 | `../interrupted-plan/` | set `state.json.updated_by.model` to a different model and a checkpoint pointing at `instructions:1` | perform the takeover check (verify pointer vs files, revision, dirty work), record a takeover entry, then continue |
| S7 | `../long-history-plan/` | as its README | reach Task 51 and honor D-7 via the task's pointer to entry 7, without reading all 50 entries (trace shows bounded reads) |
| S8 | `../legacy-plan-v217/` | as its README | resume Task 2 under the legacy shape; no migration; full-suite gate as written |
| S9 | `../new-shape-plan/` | mark Task 1 `[ ] (re-validate: requirements changed by refine on 2026-09-01)` with state `pending` and evidence prefixed `invalidated by refine` | rerun only Task 1's gates; do not re-implement; re-mark `[x]` |
