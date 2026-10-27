# ADR 0006 — Methodology identity and positioning after the 2026 methodology debate

Status: Accepted (2026-10-27). It governs the 7.x hardening series and every public description of DWP.

## Context

In October 2026, practitioners argued that spec-driven development (SDD) was "dead" and that something called ODD replaced it. The question for DWP was whether its own loop *is* SDD, whether it needs a new name, and what it should improve.

A structured debate answered it. A ten-seat panel of coding agents from three providers researched the state of the art. A second, fresh panel then audited that research and decided. The process used ranked ballots (Borda and Condorcet), anonymized cross-examination, a stress test and an independent cross-review. The lead never voted. The fresh panel narrowed 18 of the first panel's 19 "established" findings and killed none. The recurring failure was narrow evidence stretched into field-wide claims, and that lesson shapes this ADR.

## Decision

1. **Identity.** DWP's planning step is **spec-first** in Böckeler's sense, for one work episode: the plan is written before the code, with acceptance criteria. All ten seats agreed. The plan is **not** spec-anchored and **not** spec-as-source. The whole is a distinct procedure: authority rules, evidence classes, an append-only journal, resume, one writer per path. Helpers enforce it **cooperatively**; it is not a sandbox. DWP claims **no measured advantage** over plan modes, ExecPlans, Kiro, Organic ODD, BMad or Superpowers.
2. **Name.**
   - Keep "Deep Work Plan".
   - Coin no new "-driven development" term, adopt no ODD, and reject "Agentic Driven Development" (it names the actor, not the method).
   - **Demote SDD; do not retire it:** it survives as "spec-first, per episode" in comparisons and search text.
   - The tagline "DeepWorkPlan is spec-driven development where the repository itself becomes the harness" is replaced. It came last on every ballot. The replacement keeps "the repository is the harness" and is chosen by a bilingual comprehension test.
3. **Durability, stated precisely.**
   - The **repository is the harness**: `AGENTS.md`, `docs/`, `.agents/` and the skill are versioned and travel with the code.
   - A **plan** lives in the repository's working copy. Any agent working there can resume it, including several agents on one plan.
   - Plans are working state, not committed files. **A fresh clone starts without them unless one is exported.**

   The earlier wording ("durable source of truth", "version-controlled plans") was imprecise rather than false in intent. The spec glossary now names the three properties: session-durable, host-portable by export, not repo-durable.
4. **Evolution.** No v8 for now. A 7.x hardening series makes text and code agree, with no new mandatory step, field or default:
   - micro-tier reconciliation;
   - a control pair that works on dirty trees;
   - non-breaking §5.1.4 and `parallel_safe` warnings;
   - verbatim intent;
   - review prompts;
   - the published three-arm benchmark;
   - a read-only compliance audit;
   - a preregistered study design.

## Dissent kept on record

- **"One pack among several"** (two seats ranked it first). BMad, Superpowers, GSD Core and AWS AI-DLC also plan, gate and resume. DWP's distinguishing record layer is agent-authored and unmeasured.
- **Spec-first in the lead sentence** (three seats), for search continuity. The comprehension test includes such a candidate.
- **Control pair by default:** five seats wanted it now; five wanted a repair and a pilot first. This series repairs it and warns; the default is deferred (below).

## Deferred, with triggers

None of these ships until its trigger fires in a separately approved plan. Each would be a breaking change, so a major version.

| Candidate | Why it is breaking | Trigger that reopens it |
| --- | --- | --- |
| Enforce §5.1.4 by default: a behavior-changing criterion closes only with a discriminating control pair or a recorded seeded-defect failure | Hardens gates for existing plans | The compliance audit shows the §5.1.4 warning firing on most finished plans, **and** a pilot shows the repaired control pair available and discriminating at acceptable cost |
| A validated portable checkpoint for interrupted plans (logs, revision, dirty state), resumable on another machine | Changes the `.dwp/` state convention | A cold-clone recovery test at journal boundaries fails today and the checkpoint makes it pass |
| Lighter micro and Lite plans, without the v7 contract and journal | Changes default flow behavior | The study or an opt-in usage census shows ceremony cost dominating small plans, with no loss of the guarantees the audit checks |
| Routing that intercepts goal-shaped prompts | Reverses the explicit-invocation design | A current-version routing test shows a high miss rate on explicit planning intents **and** a low false-positive rate on ordinary edits |
| An opt-in local usage census | New data collection (opt-in, local) | Wanted to size the triggers above, after a privacy review |

## Evidence the decision rests on, and its limits

- **Plans help, and bad plans hurt more than none.** One SWE-agent study of 21,120 trajectories found that a standard plan improves issue resolution and that a subpar plan hurts more than no plan. It says nothing about multi-day work.
- **The SDD null result measures something narrow.** An observational study of 88,052 pull requests found no defect or rework reduction for "spec" artifacts, but those artifacts were mostly ticket references, and no repository in the sample committed SDD-tool output.
- **DWP's only token measurement is narrow too:** n = 1 and an older version. It was mixed per feature, and about 4.4–4.9× the no-harness control all-in, dominated by one-time onboarding with the flows never entered. See `docs/evaluations/three-arm-benchmark.md`.
- **No method, DWP included, has a paired long-horizon study against plan mode.** The preregistered design is `docs/evaluations/v8-evidence/PREREGISTRATION.md`.

## Consequences

- Public copy (this repository's README, the website in 17 languages, `llms.txt`, structured data) uses one wording ledger for durability, identity and efficiency. Token claims carry their units.
- The spec, `create` and the ledger are aligned in this series. The compliance audit measures whether finished plans follow the rules, so the next roadmap cannot re-propose rules the pack already ships.
