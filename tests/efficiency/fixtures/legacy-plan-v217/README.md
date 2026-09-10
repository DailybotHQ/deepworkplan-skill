# Fixture: legacy-plan-v217

**Proves:** a plan created under the v2.17 shape (three mandatory final tasks: security review → skills & agents discovery → executive report; no Touched Surface; unbounded PROGRESS.md) remains **conformant** under the new checker and is **executed under its own shape** — never retrofitted mid-flight.

**Layout:** `.dwp/plans/PLAN_legacy_fixture/` with 2 user tasks (1 done) + the 3 legacy final tasks, `manifest.json` (`spec_version` 2.2.0), `state.json`, `PROGRESS.md`, `PROMPTS.md`.

**Reset:** copy to a temp dir, `git init && git add -A && git commit -qm fixture`.

**Expected outcomes (see ../ORACLES.md):** `conformance.sh` → PASS (legacy shape accepted); `Touched Surface` absent → **finding**, not failure; an executor resumes at Task 2 and runs the plan's own full-suite gate (fallback rule) without adding/removing final tasks.
