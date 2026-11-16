# Preregistration: does DWP Lite's record layer add value over plan mode plus a one-page contract?

Status: **registered design, not run.** Running it is a separate, budgeted plan. This document is frozen before any arm runs. Any change after the first run is an amendment, dated and listed at the end, and the analysis reports both versions.

Why it exists: ADR 0006 states that no method, DWP included, has a paired long-horizon comparison against plan mode. The one token measurement DWP has (`../three-arm-benchmark.md`) never entered the flows, so it compared direct builds. This study is the smallest one whose result could change what DWP claims.

## 1. Hypotheses

- **H1 (primary).** On substantial, interrupted brownfield tasks, DWP Lite produces more **accepted changes per human-attention minute** than native plan mode plus an equally reviewed one-page contract.
- **H2.** DWP Lite's observed gates and journal **detect seeded faults** more often before acceptance.
- **H3 (cost).** The difference in **provider tokens per accepted change** is reported separately for the one-time onboarding (as a break-even count) and the per-task cost. No direction is assumed.

## 2. Arms (phase 1)

| Arm | Setup | What is held equal |
| --- | --- | --- |
| **P: plan mode + contract** | The host's native plan mode, plus a one-page contract the human reviews: goal, acceptance criteria, validation command, stop rule | Model, host, repository, task text, human review budget, handoff conditions |
| **D: DWP Lite** | The DWP skill installed and onboarded. The flows are **invoked explicitly** (`/dwp-create`, `/dwp-execute`, `/dwp-resume`), because the earlier benchmark showed agents do not enter them unaided | The same |

Both arms receive the same human approvals at the same points. The contract in arm P is reviewed with the same depth as the plan in arm D.

## 3. Tasks

- Substantial brownfield changes in existing repositories, at least 3 hours of agent work each: a feature across modules, a migration with a schema change, and a refactor with behavior preservation.
- **Each task is interrupted at a pre-registered point.** The session ends and a different agent (another vendor where possible) resumes it in the same working copy.
- **Seeded faults:** each task carries 2 faults the acceptance tests must catch: a wrong check and a skipped criterion. The faults are planted by a person outside the study team before the run, and their list is sealed.

## 4. Repeats and power

- Each task × arm runs **at least 5 times** with independent sessions.
- **Equivalence margin:** ±20% on the primary outcome.
- **Analysis:** two one-sided tests at α = 0.05, with the per-task variance estimated from a 2-run pilot. The pilot is excluded from the analysis.
- **Interpretation rule:**
  - A **sufficiently powered** result within the margin **rules out** the incremental benefit of the record layer for these tasks.
  - An underpowered null is **inconclusive** and is reported as such.
  - Neither outcome says anything about whether the procedure exists. "The residue pays" and "the procedure exists" are separate claims.

## 5. Oracle

- A **blind independent oracle** accepts or rejects each change: hidden acceptance tests written before the run by someone outside the study team, plus a reviewer who does not know the arm.
- Agent-authored gates are **not** the oracle; they are part of what is measured.

## 6. Metrics

| Metric | Definition |
| --- | --- |
| Accepted change | The oracle accepts it (hidden tests pass, and the blind reviewer approves) |
| Human-attention minutes | Time a human spends reading plans, approving, resolving questions and reviewing diffs, logged per interaction |
| Provider tokens per accepted change | Harness-reported input + output; onboarding is reported **separately** as a one-time cost, together with the break-even count |
| Flow-entry probability | Share of sessions in arm D that actually used the flows as invoked |
| Seeded-fault detection | Faults caught before acceptance ÷ faults planted |
| Resume correctness | The resuming agent continues the intended task without rework, as judged by the oracle |
| Wall time | Reported, with no hypothesis attached |

## 7. Cost ceiling

- **Budget cap:** a fixed provider spend and a fixed number of starts, both set before the pilot. They are sized against the earlier preregistered design, which ran 0 of 1,080 starts because the provider capped it.
- **If the cap is hit, the report says "not run" for the remaining cells.** It never says "inconclusive in DWP's favor" and never extrapolates.

## 8. Phase 2 (a new registration, not this one)

The arms below are added only after phase 1 reports:
- pair or augmented coding (a human at the wheel);
- Superpowers-style agent TDD;
- BMad straight-to-build;
- Kiro dependency waves;
- final-gate-only;
- DWP Full;
- parallel writers.

## 9. Amendments

None.
