# Fixture: interrupted-plan

**Proves:** resume after an interruption **between** implementation and validation/commit continues correctly — no duplicated commit, no duplicated gate, no lost work, no question to the user.

**State on disk:** Task 1 completed and committed. Task 2 is `in_progress` in `state.json` with a checkpoint note; `src/mathx.py` is written but **uncommitted** and its test exists; README still shows Task 2 `[ ]`; the task log is empty. This is exactly the window the resume protocol must handle.

**Reset:** copy to a temp dir, `git init && git add -A && git commit -qm fixture`, then `git rm -q --cached src/mathx.py tests/test_math.py && git commit -qm 'simulate: task 2 work uncommitted'` — the two files stay in the working tree as untracked work.

**Expected outcomes (see ../ORACLES.md):** resume inspects evidence first (git status shows the untracked work; state says in_progress), runs the gate **once**, commits **once**, marks Task 2 `[x]`, and proceeds to Task 3 — and does not re-implement `mathx.py`.
