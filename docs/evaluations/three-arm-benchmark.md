# Three-arm fresh-agent benchmark: with and without the DWP harness

This is the public summary of the only DWP evaluation that measured provider tokens. It is published because public copy called it "a public evaluation" while its full record stayed in a private working folder (ADR 0006). Read it with its limits; it is **one workload (n = 1)**.

## Protocol

- **Arms:**
  - **0**: no DWP (control);
  - **A**: DWP skill v2.17.1;
  - **B**: a v5 pre-release build, byte-pinned at install.
- **Fixture:** fresh clones of one small Astro template repository, the same baseline for every arm. Two features (task 1 and task 2) were built per arm.
- **Agents:** every phase ran as one fresh-context coding agent driven by a frozen prompt, word for word identical across arms. The protocol was frozen before any arm ran.
- **Metrics:**
  - harness-reported session tokens (model input and output, plus cache reads);
  - wall time;
  - bytes read;
  - blind quality judging;
  - external acceptance checks.

  Every number below comes from per-run ledgers. Runs voided by infrastructure faults (rate limits, a dead session) were excluded and disclosed.

## The decisive finding: the flows were never entered

After a faithful onboarding in each skill arm, **no fresh agent given a goal-shaped feature prompt entered the DWP flows** (n = 5 across both versions): no plan was created, no `.agents/` file was read, and every feature was built directly. Every comparison below is therefore on the **direct-build path**, not a measurement of planned DWP work. The current pack routes only explicit planning intents by design (ADR 0006), so flow entry is a decision to invoke, not something the harness does on its own.

## Token and time results (create phases, the path that ran)

| Arm / feature | Model input | Model output | Cache read | Bytes read | Wall (s) |
| --- | --- | --- | --- | --- | --- |
| 0 (no DWP) / task 1 | 74,969 | 40,946 | 2,953,664 | 71,646 | 500.0 |
| 0 (no DWP) / task 2 | 58,929 | 24,933 | 2,543,680 | 61,664 | 290.4 |
| A (v2.17.1) / task 1 | 79,544 | 26,709 | 3,851,328 | 59,254 | 448.1 |
| A (v2.17.1) / task 2 | 76,868 | 44,063 | 2,892,032 | 52,318 | 367.7 |
| B (v5 pre-release) / task 1 | 66,896 | 22,954 | 2,890,432 | 69,744 | 472.4 |
| B (v5 pre-release) / task 2 | 63,938 | 27,254 | 2,929,536 | 58,246 | 448.5 |

**Per feature** (input plus output tokens), the direction is **mixed**:
- **Task 1:** both DWP arms used fewer tokens than the control (A −8.3%, B −22.5%).
- **Task 2:** the control was cheapest (B +8.7%, A +44.2% above it).
- Bytes read were lower in both DWP arms on both tasks.

**All-in**, with the one-time onboarding of the harness counted:
- The skill arms' onboarding cost 314,028 / 94,608 (A) and 370,146 / 108,812 (B) input / output tokens.
- **Task-1 totals:** A **514,889** and B **568,808**, against **115,915** for the control, about **4.4–4.9×**.
- Onboarding dominates at this size because the flows that would amortize it were never entered.

**Wall time:** v5 was slower than v2.17.1 on every counted wall (onboarding +26.1%; create phases +5.4% and +22.0%).

## Quality

- **Blind judging** (five dimensions): B 4.00, A 2.80, control 4.20.
- **External checks:** both skill arms passed the identical checks on both features.
- **Documentation:** both DWP arms' direct builds kept the repository documentation in sync; the control touched no docs.

## What this does and does not support

- **Supported, scoped:** in this one small workload, agents with the DWP harness installed read fewer bytes per feature, and the v5 harness's sessions used less model input and output than v2.17.1's.
- **Not supported:** "working without DWP consumes more tokens". The per-feature direction is mixed, and all-in the control wins because onboarding never amortized.
- **Unmeasured:**
  - plan quality and live resume (no plan existed);
  - any multi-session, parallel or long-horizon effect;
  - any comparison against a native plan mode.

## Limits

- One workload, two features, one model family. The skill versions are earlier than the current pack.
- The routing finding (no flow entry) makes every DWP-specific claim untested by this run.
- The honest unit for DWP's token cost is a **break-even count**: one-time onboarding, divided by the per-feature saving **when the flows are entered**, weighted by how often they are entered. This run does not measure that.

The study that could answer these questions is preregistered in `docs/evaluations/v8-evidence/PREREGISTRATION.md`.
