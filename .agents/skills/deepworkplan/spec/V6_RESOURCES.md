# V6 Resources — Envelope Reserves, Exhaustion and Host Capability Negotiation

> **Status: v6 line.** This document defines the v6 resource contract: the
> **host capability negotiation**, the **counter-source split**
> (journal-observable vs host-only), the **reserve** representation, the
> **exhaustion** grammar and dispatch hold, the **cancellation
> settlement**, and the **routing posture**. The design source is
> `docs/evaluations/v6/ARCHITECTURE_RFC.md` §8 (draft-4); the shipped
> implementation is `shared/resources.py` (Python 3.9+ stdlib, composing
> the envelope accounting of `shared/scheduler.py` and the record
> discipline of `shared/ledger.py` — it never duplicates either). The v5
> standard is untouched: these rules bind **v6 new plans only**.

All documents in this spec use RFC-2119 language. A limit the host cannot
meter is **advisory, not enforced**: enforcement parity across hosts is
never claimed.

## 1. Host capability negotiation

* The runtime host states its **abilities** as a closed set:
  `stop_agent`, `meter_spend`, `meter_tokens`, `meter_wall_clock`,
  `cancel_children`, `model_routing`, `subagents`, `telemetry`. Abilities
  are distinct from the contract's permission **grants** (§3.2 of the
  contract spec): a grant is authority, an ability is what the host can
  actually do.
* An unknown ability key MUST be refused — a capability is never invented.
* An unstated ability is `false`. The **minimal host** (no model
  switching, no subagents, no telemetry, no stop) is a supported degraded
  posture, never an error; every limit that needs the missing ability
  degrades to advisory with the missing ability named.

## 2. Counter sources

* **Journal-observable counters** (wall-clock span, gate retries,
  dispatch calls) are computed from the plan's own records; no host
  ability is required to enforce them.
* **Host-only counters** (spend, provider tokens) require the matching
  `meter_*` ability and an **observed** `resource_sample` from a host
  adapter (A1: only a host_adapter actor reading a real meter mints
  observed samples). A metered host with no sample on record enforces
  the **pending side only** — a missing counter is not free usage.
* A unit outside every known family MUST degrade to advisory with the
  unit named; a meter is never invented.

## 3. Reserves

* A limit MAY declare `reserve` (a number, `0 <= reserve <= limit`). The
  dispatchable ceiling is `limit - reserve`; a refusal fires when
  `spent + pending > limit - reserve`. Reserves exist so verification,
  retry and resume cannot be starved by ordinary work.
* The ceiling comparison is **runtime semantics** (it depends on the
  sibling `limit` value, which JSON Schema cannot express); both halves
  still reject a malformed (non-numeric, negative) reserve.

## 4. Exhaustion

* Hitting a limit MUST persist an **incomplete checkpoint** — the journal
  and snapshot already are that checkpoint — and stop dispatch. The stop
  is recorded as an observation with the grammar
  `LIMIT: exhausted <limit-id>: <detail>`; only a declared limit may be
  exhausted (an undeclared counter is never recorded).
* An exhaustion observation **can never satisfy an acceptance criterion**
  (the ledger counts only `gate_run` events); exhaustion structurally
  cannot mint completed evidence.
* Dispatch stays held until an explicit `LIMIT: recovered <id>` record;
  recovery is never silent.
* Advisory limits surface, never hold.

## 5. Cancellation settlement

* An in-flight reservation (an authorized adaptation's declared impact)
  settles **exactly once**: `RESERVATION: <key>: released` (the cancelled
  child never consumed the budget) or `RESERVATION: <key>: committed`.
* Identical replay is idempotent (content-keyed dedup). A second
  settlement with a **different** disposition is the double-charge
  ambiguity and MUST be refused, never arbitrated.
* Pending accounting subtracts released reservations; with zero
  settlements it equals the envelope core's pending exactly (drift-guarded
  by tests).

## 6. Routing posture

* The default posture is **fixed-model**. Model-tier switching requires
  BOTH the contract grant `model_routing` AND the host ability of the
  same name; each refusal names the missing side(s).
* Parallel dispatch requires the `agent_delegation` grant AND the host
  `subagents` ability; otherwise the posture is sequential-only.
* A routing posture is a permission statement, **never an efficacy
  claim**: switching being authorized says nothing about whether
  switching helps.
