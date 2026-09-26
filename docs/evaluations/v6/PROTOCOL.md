# v6 experiment preregistration — arms, decision rules, resources

Preregistered 2026-09-26 by `PLAN_v6_verified_autonomy` Task 3, **before any
comparative pilot**. The machine-readable record is
[`tests/evaluation/v6/protocol/design.json`](../../../tests/evaluation/v6/protocol/design.json);
this document is its readable companion. Every threshold here is a **target**,
never a result; the operative bar is frozen by Task 24 before any confirmation
outcome exists. This protocol follows the house rule set by
[`tests/reliability/PROTOCOL.md`](../../../tests/reliability/PROTOCOL.md):
changing an expectation means changing it here first, with a reason.

It incorporates the standing lessons of
[`token-efficiency.md`](token-efficiency.md): the earlier instrumented
comparison was never completed and produced no claim — partial, unequally
progressed runs measure how far each got, not how efficiently it worked. This
design therefore preregisters exclusions, censoring, denominators and
retention of failed/aborted attempts before the first run.

## Questions and estimands

| ID | Claim | Unit of analysis | Denominator |
| --- | --- | --- | --- |
| Q1 | v6 raises independently accepted completion vs latest v5 at equal resource ceiling | task case (repeats/copies/tests are not new tasks) | all eligible attempted cases, intention-to-treat; ineligible/incomplete reported separately |
| Q2 | v6 lowers attributable cost per accepted result | task case | accepted outcomes in the same workload; undefined if none — never zero |
| Q3 | v6 sustains completion and lowers intervention on interrupted, evolving projects | storyline/campaign (six increments) | all scheduled campaigns, aborts retained |
| Q4 | Mechanisms account for gains; overheads known | ablation cell | all ablation runs incl. control |

Primary outcomes are product behavior assessed outside the actor. DWP
conformance and honest completion are separate guardrail outcomes. Full
estimand fields: `design.json` `estimands`.

## Arms and fairness

- **A no-DWP** — the agent's normal planning, notes, tests and tools; never
  crippled; only treatment contamination is stripped. A no-DWP actor never
  needs a plan or DWP receipt to succeed.
- **B latest-v5** — the frozen v5.5.4 snapshot (`tests/evaluation/v6/baselines/`),
  never the dogfood, never mutable main.
- **C v6 candidate** — the frozen candidate pack.

Model/host/tools/reasoning settings and useful starting information are
constant within each block. Cold-adoption and already-onboarded costs are
reported as separate tracks; setup is never amortized over an invented
workload. Reviewer policy: packages-as-delivered primary, matched-reviewer
sensitivity cells, and every residual reviewer difference recorded as an
attribution limit.

## Partitions (planned envelopes, not approved bills)

| Partition | Envelope | Purpose |
| --- | --- | --- |
| Baseline pilot (Task 10) | 12×2×2×2 = 96 starts | validate apparatus; estimate variance; power the design |
| v6 development | ≤3 bounded rounds, development cases only | repair mechanisms |
| Ablations | full v6 + 3 one-component-removed + reviewer sensitivity | contribution and overhead |
| Confirmation (Task 25) | 60 distinct cases ×3×2×3 = 1,080 starts | powered heldout comparison |
| Long horizon (Task 26) | 6 storylines ×3×2×2 = 72 campaigns ×6 increments | sustained behavior |
| External (Task 27) | 3 repos ×2 tasks ×3×2×2 = 72 starts | bounded transfer evidence |

The 1,080-start confirmation has only 60 task clusters. Power comes from a
pilot-based simulation of the **complete joint GO decision** (≥0.80 GO
probability under a justified alternative with room beyond the thresholds; see
`design.json` `power_rule`). Clustering dominating ⇒ add genuinely distinct
cases, not repeats. Boundary alternatives (a true +10-point gain; a true 0.80
cost ratio) sit exactly on the thresholds and do not yield high GO probability
by sample size alone. A baseline above 90% accepted leaves under ten points of
headroom — if the bar is unattainable, that is disclosed and the launch is
blocked or relabeled exploratory.

## Launch bar (targets)

| Endpoint | Target | Evidence required |
| --- | --- | --- |
| Accepted vs v5 | ≥ +10 points | estimate meets target; multiplicity-adjusted 95% LB > 0 |
| Accepted vs no-DWP | positive | adjusted 95% LB > 0 |
| Cost/accepted vs v5 | ≥ 20% lower (≤ 0.80) | estimate ≤ 0.80; adjusted 95% UB < 1.00 |
| Engineering rescue | 30% lower where baseline ≠ 0 | absolute rate + ratio with uncertainty |
| Long-horizon retention | ≥ +10 points vs v5 | campaign-cluster analysis; else inconclusive |
| Critical regressions / false completion | zero observed in mandatory checks | denominator + interval bound published |
| Simple-task overhead | ≤ 10% median vs v5 | task-stratified; never hidden by aggregates |

Mandatory GO conditions, inconclusive semantics, and the honest-failure rule
(GO / NO_GO / INCONCLUSIVE are distinct; NO_GO blocks the verified-upgrade
claim but preserves the work) are preregistered in `design.json`. Any headline
autonomy claim carries its own preregistered test; failing it removes the
claim and never moves the primary bar.

## Inference discipline

Stratified paired cluster bootstrap at task level (all repeats/arms of a
sampled task stay together), verified by simulation; Holm adjustment for the
mandatory superiority claims with compatible intervals — implemented and
tested, never claimed from unadjusted intervals; frozen-seed randomized arm
order; explicit cache policy; predefined exclusion/replacement/timeout/
cap-exhaustion/missing-usage/outage rules; intention-to-treat primary with
predeclared sensitivity analyses; **no early stopping for favorable results**;
absolute counts, per-family and per-host results always reported.

## Isolation, blinding, anti-contamination

Implementer, holdout custodian, evaluator and analysis roles are separated by
actual contexts and **enforced access**. The custodian authors sealed prompts,
hidden tests and reference solutions outside implementer and actor reach;
scorers run outside both. Telling an unrestricted agent not to read a file is
not a sealed evaluation: benign sentinels and access checks must prove
isolation before final cases are authored. **If the host cannot enforce this
separation, the confirmation campaign is blocked and runs are labeled
exploratory.** Current-host reality recorded at preregistration time: no
container isolation and no second enforced OS user are available, so
confirmation launch requires an enforced-process solution (separate
accounts/hosts/sandbox) — this boundary is recorded in `design.json`
(`isolation.current_host_reality`) rather than assumed away.

Confirmation families are distinct behavioral mechanisms — a new seed on the
same solution pattern is a repeat, not a holdout. The candidate never evolves
during a confirmation campaign; a fix creates a new identity and a fresh
untouched partition. Subjective raters are blind to arm labels; acceptance
stays public, test implementations stay hidden; rewarding DWP terminology or
richer self-reports is prevented.

## Metrics and cost definitions

**Accepted outcome** = external behavioral acceptance + required
regression/invariant checks on the artifact. **Cost per accepted outcome** =
total attributable actor/reviewer/evaluator/setup/retry/resume cost over the
eligible attempted workload ÷ accepted outcomes in it (undefined if none —
never zero). Provider counters are the token source with input/output/cache/
reasoning semantics preserved; missing counters are unknown, never imputed;
filesystem bytes are never converted to tokens or money. Monetary figures
state invoiced vs dated-list-rate estimates. Wall-clock, build/test time,
retries, churn, interventions (by category), scope violations, stale evidence
and completion-claim accuracy are captured. No latency comparison across
contending processes. Asking correctly for missing authorization is not a
quality failure; silence is not automatically autonomy.

## Resources and the authorization boundary

The developer authorized planning in trust mode and supplied **no monetary
ceiling**. The projected costs live in the plan's
`analysis_results/RESOURCE_PROPOSAL.md`, generated by
[`cost_calculator.py`](../../../tests/evaluation/v6/protocol/cost_calculator.py)
from the dated-rate assumptions in
[`cost_assumptions.example.json`](../../../tests/evaluation/v6/protocol/cost_assumptions.example.json)
— planning estimates, not invoices, not authorization. The exact future ask:
approve numeric **per-run** and **total** caps (or supply an applicable
existing budget). Until then `design.json` `resource_envelope.status` stays
`UNSET`, the tool's `gate` mode exits nonzero, and paid launches are refused —
deterministic laboratory preparation (Tasks 4–9) needs no envelope and
proceeds. The G2 pilot (Task 10) is a deliberate prerequisite for core
implementation (Tasks 11–20): missing resources stop that boundary with the
concrete proposal in hand, never a silent skip. No account, subscription or
infrastructure is purchased silently.

## Provenance and retention

Every run records campaign/case/arm/repetition, source/pack/reviewer/oracle
hashes, exact host/model config, randomization order, environment lockfiles,
permissions, counters, timestamps, caps, artifacts, scores and terminal
status. All scheduled attempts are retained, including aborts — deleting an
inconvenient run is how an evaluation lies. Raw evidence stays in the plan's
`analysis_results/lab/`; sanitized replayable exports land under contributor
docs/tests. No secrets, no private model reasoning, no unnecessary personal
data.
