# V6 Context Selection — The Per-Task Context Manifest

> **Status: v6 line.** This document defines the v6 context contract: the
> per-task **context manifest**, the **dead-end digest**, the **freshness
> check** for stale-able artifacts, and the **four-quantity** accounting
> rule. The design source is `docs/evaluations/v6/ARCHITECTURE_RFC.md`
> §7 (draft-4, question Q6 resolved here); the shipped implementation is
> `shared/context_manifest.py` (Python 3.9+ stdlib, read-only derivation
> over the plan's records — it takes no lock and writes nothing except the
> files you name with `--out`). The v5 standard is untouched: these rules
> bind **v6 new plans only**, and the v5 read tiers remain the loading
> discipline the manifest's triggers reference. The manifest document's
> shape is published as
> [`schema/context-manifest-v6`](schema/context-manifest-v6.schema.json).

All documents in this spec use RFC-2119 language. The manifest is a
**derived view**: it is recomputed from `contract.json` (or the live
`contracts/` revision) plus the full journal (archived + live) every time,
never stored as state — so it can never drift from the records it
summarizes, and it MUST NOT be hand-edited or committed as plan state.

## 1. Derivation (Q6)

Every section of the manifest is derived from named record sources. The
manifest MUST NOT invent content, must not read outside the plan directory
and its repository root, and must not import environment or cross-project
state.

| Section | Derived from |
|---------|--------------|
| `identity` | plan name, live `contract_id`, contract revision, helper identity string |
| `authorization` | approval events citing the live contract (authority, mechanism), verbatim, **including consent checkpoints** |
| `repository_rules` | the contract's `scope` and boundary `invariants` with their current evaluation state (`pass`/`fail`/`stale`/`unevaluated`) — never silently re-evaluated |
| `acceptance` | the task's `gate_intent` criteria with per-criterion closure state recomputed by the outcome rules (V6_CONTRACT §6) |
| `touched_surface` | the task's declared files with their current content hashes; a missing file MUST surface as missing and widen discovery, never as an assumed value |
| `evidence` | valid in-window evidence pointers (each pointer MUST resolve on disk; a dangling pointer is reported, not kept) |
| `dead_ends` | the digest of §3 |
| `freshness` | the current inputs fingerprint (§4) |
| `history_triggers` | the explicit triggers under which history beyond this manifest is loaded (§6) |
| `next_action` | the ladder of §2 |

`as_of` is the last record's sequence and timestamp — the manifest is
anchored to the records, never to the wall clock, and deriving twice from
the same records MUST produce identical bytes.

## 2. Mandatory sections and the next-action ladder

`authorization`, `repository_rules` and `acceptance` are **mandatory
sections**. A caller MAY only exclude optional sections (`history_triggers`);
requesting a manifest without a mandatory section MUST be refused — context
pruning can never hide the acceptance or authorization boundary.

The `next_action` ladder is ordered, and the manifest names exactly one
step with a concrete command:

1. **approval** — no approval event cites the live contract yet;
2. **start** — approved but the task has no `task_start`;
3. **authority** — the records show a blocked state needing human authority;
4. **control** — an open criterion declares a `regression`/`discrimination`
   control: it closes ONLY on an executed, in-window, discriminating
   `control_pair`. A passing ordinary gate run MUST NOT be presented as
   closing a controlled criterion (ladder honesty);
5. **evidence** — criteria remain that close on ordinary accepted evidence;
6. **complete** — every criterion of the task is closed; the step names the
   completion transaction.

## 3. The dead-end digest (U4)

The digest collects, each as a recorded event with a pointer (never advice,
never probabilities): **failed gates** (nonzero exit, with cause log),
**refusals** (latest per subject+stage), **refused adaptations**, and
**non-discriminating controls**. Invalidation is **retention-biased**: an
entry leaves the digest (or is marked, never deleted) ONLY on proven record
facts —

* the same run fingerprint later produced a passing gate (the approach
  stopped failing);
* a newer duplicate refusal supersedes an older one for the same subject
  and stage;
* a control was recorded under a `contract_id` that a later revision
  superseded — the entry is retained but marked `aged_out`.

A mere surface change MUST NOT silently drop a dead end. The digest is
capped (last 50 entries by sequence) and the cap is stated in the output.

## 4. Freshness

Any stale-able artifact (summary, digest, cached finding) carries the
**fingerprint of the inputs it summarizes** — sha256 over the task's
declared touched-surface file hashes bound to the contract id. The
freshness check compares that recorded fingerprint against the current one:

* match → `fresh`;
* mismatch → `stale` (and the CLI exits 1): changed inputs invalidate the
  summary; stale facts are never silently inherited;
* an artifact with no recorded fingerprint is **stale by construction** —
  an unattributable summary is not evidence of anything.

Reuse identity covers the DECLARED inputs only: an undeclared input
(a flag file outside the touched surface) is invisible to the fingerprint,
and forcing an honest re-run is the caller's `reuse=False` decision.

## 5. Four-quantity accounting

Instruction load and cost are reported as **four distinct quantities**:
static **instruction bytes** (measured manifest + bundle file bytes),
**provider tokens** (only where a host metering sample recorded them),
derived **monetary cost** (only from recorded real-rate samples), and
**wall-clock time** (from the event timestamp span). A missing quantity is
exposed as `missing` with its reason — never imputed, and **bytes are
never converted to tokens or money**. Model routing claims are separate
from these quantities and never implied by them.

## 6. History by trigger only

Beyond the manifest, detailed history loads ONLY on explicit triggers
(the v5 read tiers): a recorded handoff, or an amendment affecting this
task. With no trigger, the manifest alone is the task's context.
Cross-project learning and broad permanent memory stay OUT of the v6 core:
only verified plan-local knowledge (the records above) is included.
