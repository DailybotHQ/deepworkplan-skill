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

New plan folders use the forward-only `PLAN_<id>_<slug>` naming policy in
`shared/dwp-paths.md`. That policy applies at creation and does not classify a
plan's generation. Existing unnumbered v5 or v6 folders remain valid in their
original locations; no lifecycle flow renames them.

- The v6 flows (`create/v6.md`, `execute/v6.md`) MUST route on this
  detection and nothing else.
- A v1/v2/v5 plan MUST keep its recorded lifecycle (RFC §9.2); no flow
  MAY migrate it to v6 silently. Migration, when it exists at all, is an
  explicit user-initiated act with its own recorded authority.
- A runner that does not implement the v6 loop MUST report a detected v6
  plan as unsupported and stop (D2-10b) — approximating the contract with
  v5 bookkeeping is the failure this rule exists to prevent.

**Contract generations of the record layer (7.0.0 line).** A plan detected
as v6 above carries one of two contract generations, named by the
contract's `schema` URL and mirrored by its manifest and every journal
event:

| Generation | Contract | Journal events | Manifest | Adds |
|---|---|---|---|---|
| v6 | `plan-contract/v6` | `journal-event/v6` | `plan-manifest/v6` | — |
| v7 | `plan-contract/v7` | `journal-event/v7` | `plan-manifest/v7` | `tasks[].parallel_safe`, the `delegation` event ([`V7_CONTRACT.md`](V7_CONTRACT.md)) |

Both generations run through the same loops and helpers and project into
the same `plan-snapshot/v6` shape. A plan never changes generation: a v6
plan keeps v6 forever, and a journal mixing generations is refused.

## 2. Activation (normative)

With the current 7.x pack, new plans use the v7 contract generation by
default (§1 table); an explicit `v6` request materializes a v6 contract. A
developer's explicit v6 request also selects this flow when an older pack
provides it.
A 5.x pack without that request follows its recorded v5 flow. Existing
plans are selected by their artifacts (§1), regardless of installed pack
version; no existing plan changes generation during selection.

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
- **Every declared invariant is plan-scoped** (F-03): it holds across the
  whole plan and is evaluated at each boundary — an observation
  `INV-<id>: pass` or `INV-<id>: fail: <reason>`. `complete` refuses (and
  records the refusal) while any invariant's latest evaluation is
  missing, older than the task's start, or a failure. A property that
  only some tasks must hold is an acceptance criterion of those tasks,
  never an invariant.
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
`contracts/`.

`python3 shared/ledger.py --plan <dir> amend --contract <draft> --authority
<who> --note <reason> --human-note <file>` is that sequence as one guarded,
resumable verb (F-12). The draft is the revised contract (a copy of the
live one, edited; the next `revision` and `parent_contract_id` are
derived); it MUST keep the plan and its generation and pass the draft
checks (`V6_CONTRACT.md` §2). The order is normative: the revision is
staged as `contracts/.contract.rN.json.pending` (invisible to the
loader); the `amendment` event lists the revised criteria in
`evidence_invalidated` — their earlier gate runs never satisfy them
again; a fresh `approval` cites the new contract id (human actor, with
the authority marker of `V6_CONTRACT.md` §3); only then does an atomic
rename switch the live contract. Re-running the same amendment after an
interruption resumes at the first missing step without duplicate events;
a different draft is refused while one is pending. Task-level markdown edits (wording, notes, task splits
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

## 8. v5 migration (normative — one-directional, explicit)

A v5 plan keeps running under the v5 contract forever (§7); the ONLY thing
that turns it into a v6 plan is `shared/migrate_v6.py`, run on purpose
through `refine`. Migration MUST follow this sequence, and each step is
idempotent and recorded in `migration_v5/PHASE.json` so an interruption at
any point recovers by running the command again:

1. **preview** — integrity check (folder/state identity, known statuses,
   well-formed gates) and the full mapping: task *N* → `T-NN-<slug>`,
   criterion `AC-tNN-<slug>`, one per v5 task, prerequisites mirroring the
   v5 sequential order. A completed task whose gates all recorded
   `passes=true`, exit 0 and a **resolving** evidence pointer closes via
   an `imported` criterion; anything weaker — a failed gate, a missing or
   dangling pointer, an in-progress task, no gates — is a **re-evidence
   criterion**: bar `observed`, blocked by default until the gates re-run
   under v6 (D3-5). The preview names the recorded assumptions (gate cwd
   and timeout are not v5 fields; imported records carry the repository
   root and the executor default) and refuses lossy inputs. No v5 byte is
   touched.
2. **backup** — `manifest.json` + `state.json` copied under
   `migration_v5/backup/` with recorded digests. The manifest swap never
   happens before this exists.
3. **contract** — the synthesized contract is deterministic (timestamps
   anchor to the v5 state's `updated_at`, never the wall clock), validates
   under `contract_v6.py`, and takes the conservative posture: scope
   records-only, no capabilities granted, an advisory unmetered envelope —
   substantive work after migration goes through an amendment (§5).
4. **manifest swap** — the v6 pointer manifest replaces the v5 manifest.
   This is the **single sanctioned rewrite of another generation's
   manifest** in the whole system (§3's refusal is what makes this
   exception safe).
5. **journal** — a `pre_authorization` approval citing the v5 source
   digest (the preview + records ARE the recorded pre-authorization,
   D3-2), one fingerprint-less `task_start` per non-pending task (v5 kept
   no fingerprint; control pairs stay honestly unavailable), every v5
   gate record imported through `Writer.migrated_gate` — `imported` with
   the source digest when the pointer resolves, `asserted` history when it
   does not, `observed` never — and a migration `observation`.
6. **projection** — `state.json` becomes the v6 snapshot; statuses are
   derived (imported-closed tasks `completed`, re-evidence tasks
   `in_progress` at their blocked criteria, pending tasks `pending`).

**rollback** restores the v5 pair byte-identically from the verified
backup and removes the v6 artifacts. It MUST refuse — until `--force` —
when the journal carries more events than the migration minted:
post-migration v6 work is real history, not debris. The reverse migration
(v6 → v5) does not exist; a v6 plan under the v5 runner (the v5
finalization in `verify/plan_contract.py`) is refused naming the contract
pointer (D2-10), while the read-only verifier judges it by its v6 records.

## 9. Cross-agent and cold resume (normative)

The journal is the truth; `state.json` and `views/` are reprojections. A
resuming host MUST recover in this order — inspect (read-only), validate
(read-only), `project`, `render --reconcile` with recorded authority — and
MUST treat stale fingerprints (dirty files, moved workspace, different
revision) as invalidated evidence to re-run, never as reusable results.
Because `.dwp/` is gitignored, a second host has nothing until the sender
exports the bundle (`ledger.py export --dest`: journal, snapshot,
contract chain, and every cited evidence artifact — a dangling cited
pointer is recorded missing, never dropped); a missing `state.json` on the
receiving host is expected and rebuilt by `project`. The journal is never
replayed as conversation context: resumption goes back through the execute
v6 loop with its per-task context manifest.

## 10. Onboarding guidance (normative)

Onboarding a repository that will run v6 plans (§2's activation rule)
adds four records to the generated guidance, taught by the trigger-gated
[`../onboard/v6.md`](../onboard/v6.md) and reconciled under the same
non-destructive rules as every other generated section:

1. a **capability declaration** using exactly the closed ability set of
   `shared/resources.py` — unstated is `false`, an unmeterable limit is
   advisory with the missing ability named, `telemetry` is opt-in, and
   the minimal host is supported;
2. **authority boundaries** drawn from the repository's real approval
   rules — never boilerplate;
3. an **outcome/test mapping** citing the repository's own runnable
   commands — never an invented or aspirational check;
4. **concise working context** — entry-point budget discipline; nothing
   here expands routine per-task reads.

A v5-only repository MUST receive none of these sections. Upgrading a
harness reconciles; it never re-onboards from scratch and never converts
an existing plan across generations (§8). A second pass with unchanged
inputs MUST produce no diff.
