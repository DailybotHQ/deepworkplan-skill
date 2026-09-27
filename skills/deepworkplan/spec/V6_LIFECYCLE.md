# V6 Lifecycle — Generation Detection, Materialization, Flow Wiring

> **Status: v6 line.** This document defines how the v6 execution contract
> (`V6_CONTRACT.md`), context selection (`V6_CONTEXT.md`) and resource
> controls (`V6_RESOURCES.md`) are wired into the pack's flows: how a
> plan's generation is detected, how a v6 plan is created and
> materialized, what the execute loop does, which surfaces stay
> read-only, and how v6 and v5 coexist. The design source is
> `docs/evaluations/v6/ARCHITECTURE_RFC.md` (decisions A2–A3, A9, A12,
> D2-10b, D3-1–D3-2, D3-6, §9–§10). It binds **v6 new plans only**; the
> v5 standard is untouched.

All documents in this spec use RFC-2119 language. Where this document and
a shipped helper disagree, that drift is a defect in one of them, never a
feature.

## 1. Generation detection (normative)

A plan folder under `.dwp/plans/` is **v6** if and only if it carries a
`manifest.json` whose `contract` pointer resolves, a `contract.json`, or a
`contracts/` revision chain. Detection MUST be by these artifacts, never
by skill version alone: an installed v6 pack can hold v5 plans, and a v5
pack can encounter a v6 plan folder copied in.

- The v6 flows (`create/v6.md`, `execute/v6.md`) MUST route on this
  detection and nothing else.
- A v1/v2/v5 plan MUST keep its recorded lifecycle (RFC §9.2); no flow
  MAY migrate it to v6 silently. Migration, when it exists at all, is an
  explicit user-initiated act with its own recorded authority.
- A runner that does not implement the v6 loop MUST report a detected v6
  plan as unsupported and stop (D2-10b) — approximating the contract with
  v5 bookkeeping is the failure this rule exists to prevent.

## 2. Activation (normative)

A new plan is created under v6 only when (a) the pack's line is 6+ or
(b) the developer explicitly requested the v6 candidate. An explicit
candidate request overrides a 5.x line; a 5.x line never overrides an
explicit request. Absent both, `create` composes the recorded v5 flow —
v6 is never produced silently and never presented as the default.

## 3. Materialization order (normative — A12)

A v6 plan is materialized by `shared/ledger.py materialize` in exactly
this order — **manifest → contract → approval** — each step idempotent
and resumable:

1. **`manifest.json`** — the identity manifest with the contract pointer
   (`schema/plan-manifest/v6.json`), written FIRST so a plan's v6-ness is
   discoverable even if materialization is interrupted before the
   contract lands.
2. **`contract.json`** — the validated, content-addressed contract
   stamped into the plan folder.
3. **`approval` journal event** — the first journal event, citing the
   contract id and the plan-markdown digest (D3-1/D3-2), actor human.

The approval event is the ONLY thing that opens the task-start gate. A
hand-copied contract without it is refused at `start`; a manifest whose
pointer does not match the materializing contract is refused rather than
rewritten. Refusals that MUST hold:

- A folder with an existing non-v6 manifest is never rewritten (§9.2).
- A materialization never rewrites a stamped contract — a different
  contract is a revision (§5).
- A folder with no plan markdown is not approvable and materialization
  refuses it.

The mechanisms (`plan_authorship`, `pre_authorization`) are mode-uniform
(A2–A3): guided and trust plans gate identically; what differs is the
recorded authority, never the checks.

## 4. The execution boundary (normative — A9, D3-6)

Declared invariants are evaluated at execution boundaries — task start,
gate run and completion — through the shipped helpers, never re-implemented
in flow prose:

- Dispatch comes from `shared/scheduler.py ready`; the core is read-only
  and refuses any task whose declared invariants were never evaluated or
  were evaluated only before the current task start.
- `observed` gate evidence is minted ONLY by `shared/ledger.py gate`; an
  appended `gate_run` without a runner binding is refused.
- Task completion is DERIVED (every `gate_intent` criterion satisfied
  in-window — the same zero-test predicate the scheduler selects by),
  never declared: `complete` refuses (and records the refusal) while any
  criterion lacks accepted evidence, and the snapshot's task status is a
  projection of that derivation.

## 5. Amendment (normative)

A change to a materialized plan's scope, acceptance criteria, permissions
or envelope is a **contract amendment**, not a task edit: author the
revised contract, record it as a new revision under `contracts/` (chain
rules in `V6_CONTRACT.md` §1), obtain a fresh approval citing the new
contract id, and invalidate the evidence of affected criteria (re-run,
never trust prior results). The manifest's pointer is provenance and is
never edited; the live contract is the highest revision under
`contracts/`. Task-level markdown edits (wording, notes, task splits
inside granted authority) go through the recorded refine flow unchanged.

## 6. Read-only surfaces (normative)

`status` and `verify` never write for v6 plans. Their v6 reports are
produced by pure commands — `ledger.py inspect`, `scheduler.py ready`,
`resources.py report|routing|hold`, `outcomes.py receipt`,
`contract_v6.py validate-contract|validate-journal` — plus reading the
generated projections and the human markdown. A finding (torn tail,
missing approval, projection disagreement) is reported with its suggested
repair; the repair itself belongs to the mutating flows. Rendering views
(`views.py render`) writes and therefore belongs to execute/refine, not
status.

## 7. Coexistence (normative)

v5 and v6 plans MAY coexist in one `.dwp/plans/`. Each plan runs under
its own generation for its whole life; no flow upgrades, downgrades or
approximates across generations. The pack's version line governs only
which generation NEW plans get (§2) — never what existing plans become.
