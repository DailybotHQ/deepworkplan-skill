# Fixture: new-shape-plan

**Proves:** the target shape — one mandatory Final Review task last, `Touched Surface` in code-changing tasks, `analysis_results/SKILLS_CANDIDATES.md` present — passes the upgraded conformance checker; and the **old** (v2.17) checker rejects it (documented forward-incompatibility, not a bug).

**Reset:** copy to a temp dir, `git init && git add -A && git commit -qm fixture`.

**Expected outcomes (see ../ORACLES.md):** new checker → PASS with zero findings; old checker → FAIL on missing `skills_agents_discovery` / `executive_report` (expected).
