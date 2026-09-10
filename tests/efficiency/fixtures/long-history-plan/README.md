# Fixture: long-history-plan

**Proves:** bounded working context still recovers an old decision on cold resume. `PROGRESS.md` has 50 historical task entries; decision **D-7** (money as integer cents) is recorded only in entry 7. Task 51 (the active task) depends on D-7 without naming it in plain words.

**Reset:** copy to a temp dir; run `resume` on `PLAN_long_history_fixture`.

**Expected outcomes (see ../ORACLES.md):** the agent implements Task 51 using integer cents (D-7 honored) **without** reading all 50 entries by default — it retrieves entry 7 by dependency/topic (the task's `Read Before Starting` points at it), and the resume trace shows a bounded read, not a full-history replay. Losing D-7 (using floats) is the failure.
