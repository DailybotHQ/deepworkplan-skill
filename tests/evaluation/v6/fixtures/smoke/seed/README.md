# Smoke seed fixture

Minimal deterministic seed for the lab driver's smoke campaign: two small
files with no build step and no dependencies. The campaign task is to produce
`solution.txt` containing `done`. Fixture content is deliberately trivial —
its job is to prove the orchestration (identical initial hashes across arms,
distinct workspaces, canaries, scoring), not to be an interesting workload.
