# DWP v6 Architecture RFC — bounded adaptive execution with verified outcomes

| Field | Value |
| --- | --- |
| Status | Proposed (reviewed draft; not yet normative) |
| Version | draft-1 (2026-09-26) |
| Elaborates | `PLAN_v6_verified_autonomy` `analysis_results/ARCHITECTURE.md` (planning proposal; a local gitignored planning input — this RFC is its version-controlled successor) |
| Normative successor | A future `spec/` revision produced by the implementation tasks; this RFC is not normative until that revision exists |
| Baseline | DWP spec 5.0.0 (the frozen v5 runner; this plan does not migrate itself) |

RFC-2119 language is used prospectively: it describes what the v6 specification
will require. Nothing here changes the installed v5 pack's behavior; the v5
contracts remain in force for every plan that has not migrated.

## 1. Product outcome and summary

An agent executing a v6 plan can select and revise its execution strategy
**within an authorized outcome contract**, prove relevant observable behavior
rather than narrate it, recover from interruption at the recorded write and
publication boundaries, and spend a
declared amount of effort **without misrepresenting incomplete work**.

Three mechanisms, one local core:

- **A. Bounded adaptive execution** — the contract names outcomes, acceptance,
  invariants, scope, permissions and a resource envelope; a scheduler proposes
  adaptations; a deterministic core authorizes or refuses each proposal.
- **B. Observable outcome verification** — acceptance claims point at evidence
  of behavior, with negative controls for important changed behavior.
- **C. A small executable core** — stdlib-only Python helpers that validate
  contracts, apply idempotent state transitions, compute evidence invalidation,
  render deterministic views, and report resource posture honestly.

DWP's portable local-first distribution, readable plans, and markdown-first
auditability are retained. Deterministic machinery is added only where it
replaces fragile model bookkeeping or checks a boundary prose cannot.

## 2. V5 guarantee inventory and v6 disposition

Every v5 guarantee the inventory must answer for, and where it lands in v6.
Sources: `spec/PLAN_STATE.md`, `shared/state_contract.py` enforcement,
`execute/SKILL.md`, `refine/SKILL.md`, the testing guide's contracts.

| # | V5 guarantee (mechanism) | V6 disposition |
| --- | --- | --- |
| 1 | Markdown is the human source of truth; JSON is a derived projection; markdown wins every desync (PLAN_STATE §5) | **Retained.** v6 adds generated *views* of the record, marked as generated and reconciled through the amendment path — never silently rewritten over a human edit (§4.4) |
| 2 | Atomic state writes (temp file + rename; a crashed write never truncates) (PLAN_STATE §2) | **Retained and extended** to the v6 snapshot and journal rolls (§4.3) |
| 3 | Update order: task log → README → PROGRESS → commit → state; crash leaves state *stale*, never *ahead* (PLAN_STATE §5.1) | **Retained verbatim** as the v6 write order |
| 4 | Guarded state updates: closed gate objects, boolean `passes`, completion requires latest passing gates with command/exit/evidence; retries supersede per command; cooperative lock; `--expected-sha256` (PLAN_STATE "Guarded state updates") | **Retained** as the deterministic authorization core; the v6 updater validates the same closed-object discipline on the v6 schema generation (§4.2) |
| 5 | Evidence truth: five evidence states; non-execution phrases in passing evidence are contradictions; `invalidated by refine` history never passes; `log=` pointers must resolve inside the plan folder; zero-selection detection (state_contract.py) | **Retained** and carried onto journal evidence items (§4.5, §11) |
| 6 | Checkpoint/blocker records; terminal checkpoint literal `done`; unattended runs must populate `blocked` (PLAN_STATE §4.4) | **Retained** with the same literals and semantics |
| 7 | Schema versioning by URL with closed objects; v5 stays a generation snapshot; declared migration is the only standard change; `manifest.json` is immutable creation provenance (PLAN_STATE §2, §6) | **Retained**; v6 adds new schema-URL generations for the new artifacts rather than editing v5 shapes (§9.1) |
| 8 | Locator integrity: unique locators, kind agrees with plan format, value shape matches identity (state_contract.py) | **Retained**; v6 task records additionally carry stable IDs independent of presentation order (§4.1) |
| 9 | Read tiers and instruction accounting: entry bundle + end-to-end paths, guarded bounds (tests, paths.tsv) (testing guide) | **Retained**; v6 flows keep the same accounting discipline; new helpers are executed, not read as instructions, so they cost no bundle bytes |
| 10 | Activation contract: intent-to-flow routing, by-name invocation, trust is not a flow selector (activation-contract tests) | **Retained**; existing slash commands and delegators keep their names and semantics (§9.2) |
| 11 | Trust boundary, consent checkpoints, injection resistance (untrusted content is data) (execute SKILL "Trust boundary") | **Retained verbatim**; v6 adaptations live strictly inside the contract's recorded authorization |
| 12 | Pack portability: only `skills/deepworkplan/` ships; Python 3.9+ stdlib only; Bash 3.2 shell interfaces; no network at runtime; missing Python reports UNVERIFIED (packaging-reliability) | **Retained**; the v6 core is stdlib Python helpers inside the pack (§10) |
| 13 | Public surface preservation: skill names, slash commands, `.dwp/plans/` convention, `DWP_DIR`/`DWP_AGENT_TOOL` overrides, `setup.sh` flags | **Retained**; the major-version rationale is the changed new-plan execution/state contract, documented in §9.3 |
| 14 | Dogfood mirror byte-identity and release-bot-owned versions/changelog | **Unchanged repo procedure**; not a runtime contract of the pack itself |
| 15 | External-action receipts: evidenced by id/URL/branch at action time; never re-sent on assumption; a missing receipt is investigated against the service's actual state (PLAN_STATE §5.1) | **Retained**; receipts enter the journal as `imported` evidence items with provenance |
| 16 | Evidence reuse requires an unchanged world: recorded fingerprint vs current `HEAD` + dirty/generated state; changed inputs force a rerun (PLAN_STATE §5.1) | **Retained**; the same freshness rule governs generated views and summaries (§7); see the "Evidence validity" row of the guarantee matrix |
| 17 | Verified publication: completion is a transaction with a `FINALIZATION.json` receipt, a `.finalizing.json` recovery marker, and UNVERIFIED (never completed) without Python (PLAN_STATE "Verified plan publication") | **Retained**; the v6 terminal transition additionally emits journal events, and validates the completed projection exactly as v5 — the receipt contract is unchanged |

## 3. The outcome and authority contract

### 3.1 Artifact and identity

One `contract.json` per plan, next to `state.json`, conforming to a new
`plan-contract/v6.json` schema URL. The contract is **immutable once
execution starts**: its identity is the SHA-256 of its canonical bytes
(`contract_id`), and every record produced under it cites that id. A changed
contract is a **new contract revision** with a `parent_contract_id` — never an
in-place edit — so evidence, invalidation and audit chains survive strategy
changes. Materialization writes it before the first task, in the same spirit
as `manifest.json` (written once, provenance forever). The canonical form is
UTF-8 JSON with sorted keys and no insignificant whitespace
(`json.dumps(sort_keys=True, separators=(",", ":"))`); `contract_id` is the
SHA-256 of those bytes, so preview, migration and the helpers all compute the
same identity. A revision is a **new file** — prior revisions are retained in
the plan folder under `contracts/` (for example
`contracts/contract-rev2.json`), each citing its `parent_contract_id` — never
an in-place edit. Like the v5 state layer, the contract is **REQUIRED** for
unattended and non-git plans and **RECOMMENDED** for interactive git plans:
the PLAN_STATE §2.1 optionality matrix, extended.

### 3.2 Required content

| Section | Fields |
| --- | --- |
| Outcome | desired outcome statement; success definition; explicit out-of-scope list |
| Acceptance | criteria with stable IDs (`AC-*`), each naming an **observable** check (behavior, interface, stored state) and its evidence class |
| Invariants | global conditions that must hold at every boundary; violation is a stop, not an adaptation |
| Scope | allowed paths; allowed command classes; forbidden operations (destructive, outward-facing) |
| Authorization | source of authority (who/what approved), timestamp, boundaries of pre-approval; consent checkpoints carried verbatim |
| Permissions | tool/host capabilities granted, and explicitly those NOT granted |
| Dependencies | external systems, credentials required (names only, never secrets), pinned inputs |
| Resource envelope | dispatch limits, wall-clock budget, tool-policy limits, and a spend ceiling **only where the host can enforce it** (declared `enforced` or `advisory`, §8) |
| Tasks | stable IDs (`T-<slug>`), titles, prerequisite outcome IDs, planned touched surface, selected gate intent |

### 3.3 Allowed adaptations (closed enumeration)

The contract enumerates exactly which adaptations a scheduler may propose:

1. **Split** a task into subtasks whose union cannot exceed the parent's scope;
2. **Reorder** among tasks whose prerequisites are satisfied;
3. **Insert** an in-scope discriminating experiment when evidence is insufficient to proceed;
4. **Change strategy** for reaching a criterion, without touching the criterion itself;
5. **Retry** a failed gate with a changed approach, within retry caps.

Any proposal outside this enumeration is refused by the authorization core;
routing every adaptation through the core is the flow's instruction contract,
and the guarded writer refuses invalid state transitions regardless. An
adaptation may **never** delete a
requirement, weaken or substitute acceptance (a substituted check is a revised
criterion and follows the amendment path), expand scope or permissions, spend
beyond the envelope, or mark an unexecuted scenario complete. Each adaptation
record names: trigger observation, evidence artifact, hypothesis/uncertainty,
chosen action and rationale, affected task/criterion IDs, the authority
(§3.2 Authorization), evidence invalidated/preserved, and resource impact.
Private chain-of-thought, invented confidence percentages and deliberation
logs are not part of the record.

### 3.4 Amendment path

Contract revisions and criterion changes use the v5 amendment record shape
(`refine/SKILL.md` 3.7): original criterion verbatim, observed finding,
disposition, revised criterion, reason, authority, affected tasks, evidence
invalidated/preserved. Amendments are appended, never backdated; the guarded
writer refuses closure on invalidated evidence. Deferrals require recorded
user or developer authority; an unmeetable mandatory criterion is a blocker,
never completed work.

## 4. The execution record: snapshot + append-only journal

### 4.1 Source-of-truth decision

One authoritative structured record per plan, composed of:

- **`state.json` (v6 schema URL)** — the deterministic *snapshot* projection:
  task statuses, latest gate records, checkpoint, blocker, resource ledger
  totals, and per-event-type journal sequence positions (the read-only checker
  uses them to verify that snapshot-cited journal items exist). Same
  closed-object discipline, same guarded-writer rules as v5.
- **`journal.ndjson`** — the append-only *event log*: one closed JSON object
  per line (`gate_run`, `observation`, `adaptation`, `amendment`,
  `intervention`, `resource_sample`, `view_render`, `reconciliation`,
  `journal_repair`; the full catalog is an implementation-task deliverable,
  §14.1). Events are never edited
  or deleted; a correction is a later event. Superseded and failed evidence
  stays available; event identity survives task splits and reorders because
  events cite stable task/criterion IDs, never list positions.

The journal is the memory; the snapshot is the projection the guarded writer
maintains at protocol points. `state.json` remains the artifact checkers,
dashboards and resume logic read first — v5 tooling patterns carry over —
while the journal answers "what happened and why" without overwriting history.

### 4.2 Why snapshot + journal (crash/concurrency comparison)

| Option | Crash behavior | Concurrency | History | Rejected/selected because |
| --- | --- | --- | --- | --- |
| Single JSON, atomic rename (v5 shape alone) | Rename is atomic; no partial state | Single writer + cooperative lock (sufficient: one plan is executed by one agent at a time) | Only latest values; decisions/observations lost or squeezed into prose | **Insufficient alone** — adaptation audit and evidence identity need an append-only record |
| Snapshot + NDJSON journal (selected) | A crash loses at most the last unwritten event line; snapshot stays rename-atomic and is the recovery root | Single writer + cooperative lock; readers see either the old or the new complete snapshot | Complete, ordered, diffable plain text | **Selected** — plain-text, stdlib, no daemon, audit-preserving |
| SQLite (stdlib module) | Transactional; robust | Best concurrent readers/writers | Queryable | **Rejected for v6** — binary blob is not diffable or grep-auditable in a plan folder, breaks the "readable plans" product property, and buys concurrency a single-actor plan does not need. Revisited only if multi-writer evidence appears in ablations |
| Event-sourcing everything (every tool call an event) | — | — | — | **Rejected** — heavyweight; "avoid making every shell command a heavyweight event" (planning proposal); events are recorded at named protocol points and at meaningful observations |

The journal is size-bounded by design: events are one line each, rolls are
optional at campaign boundaries, and full narrative stays in task logs where
it belongs today.

### 4.3 Write discipline

- The snapshot is rewritten only by the guarded updater, atomically, at the
  v5 protocol points (materialization, task start, gate runs, completion,
  checkpoint, blocked).
- Journal appends go through a shipped stdlib helper — the
  `update-state.py` pattern: cooperative `.lock` directory, closed event
  objects, and a provenance stamp (helper identity, `contract_id`) applied at
  write time. This makes §4.5's trust labels mechanically meaningful for
  helper-mediated writes. As with the v5 lock, **no protection is claimed
  against editors that bypass the writer**; read-time structural checks and
  the read-only checker report what the records can show.
- A torn final line (crash mid-append) is repaired on the next writer open:
  the incomplete tail is truncated and an explicit `journal_repair` event
  records the byte offset and cause — the append-only rule binds *complete*
  events. The snapshot, never the journal, is the recovery root.
- Write order per boundary stays: task log → README → PROGRESS → commit →
  snapshot; journal appends happen at the moment of the observation they
  record, before the snapshot that summarizes them.

### 4.4 Deterministic views and the human-edit rule

`README.md` and `PROGRESS.md` remain human documents. Generated views (a
task table, a resource ledger, an evidence index) are written to explicitly
named generated files carrying the `contract_id`, a source snapshot digest
and a render timestamp. If a human edits a generated view, the next render
**refuses to overwrite silently**: it reports the divergence and offers the
v5 reconciliation choice — import the human change as an amendment or keep
the generated view with the human file preserved under a distinct name.
Direct edits to `README.md`/`PROGRESS.md` are reconciled markdown-wins, as in
v5. Under the journal, reconciliation regenerates the snapshot from the
markdown and appends a `reconciliation` event; prior journal items are
retained as history — the journal never discards. The v5 "stale, never ahead"
property therefore scopes to the journal→snapshot direction.

### 4.5 Trust labels on evidence

Every journal evidence item carries one label:

1. **observed** — produced by the deterministic runner/checker itself;
2. **imported** — from a matched external source (CI run, service log), with provenance;
3. **asserted** — stated by an agent without independent establishment.

Acceptance criteria declare which classes they accept. Checksums establish
byte identity, not semantic truth; a receipt cannot prove a feature works
unless an accepted evaluator checked it. The helper validates evidence
*structure and provenance*; it cannot prove arbitrary product semantics —
that limit is stated in the record format and must not be papered over.

## 5. Scheduler proposals vs deterministic authorization

- The **scheduler** (model-driven) proposes: next task, adaptation, retry,
  insertion. Its output is a *proposal object* — never a direct write.
- The **authorization core** (deterministic helper) is a pure function:
  `authorize(contract, record, proposal) → accept | refuse(reason)`. It
  checks prerequisite outcomes, scope, permissions, envelope remaining,
  retry/adaptation caps, invariant status, and the closed adaptation
  enumeration. Every refusal is itself a recorded event with the reason.
- **Measured observations** (gate runs, resource samples) are recorded by the
  deterministic helpers themselves, which stamp `observed` provenance at
  write time (§4.3); agent assertions enter as `asserted`. An acceptance
  criterion that requires `observed` evidence is satisfied only by
  helper-stamped items; a hand-written line claiming `observed` is a writer
  bypass — reported by the checker where the records allow, and named
  honestly in the format's limits rather than claimed impossible.

Blocked work may permit safe independent in-scope work; a global invariant
failure or exhausted envelope stops dispatch. Starvation protection: ready
task selection uses oldest-blocked-wait aging. Caps: maximum adaptations per
task, maximum retries per gate, both declared in the contract. Handoff
conditions (fresh context, cross-host resume) are explicit contract fields.

## 6. Observable outcome verification

- Every acceptance claim points to **evidence of behavior**: a regression
  test that fails on the original defect, a detected safe mutation, a
  rejected invalid input, or an interface-level check that discriminates a
  known-broken implementation. Which negative control applies is decided at
  contract authoring per criterion; minor prose/cosmetic changes are exempt.
- Fresh-context evaluation is used where the host supports it; it reduces
  shared conversational assumptions but does not guarantee statistically
  independent errors — recorded as such, never as independence evidence.
- A second model or reviewer adds cost and must earn inclusion per campaign;
  no unconditional reviewer duplication.
- Diff review stays owned by the upstream AI Diff Reviewer; v6 supplies
  accumulated scope and consumes explicit review states, and does not fork
  its severity rubric.
- Zero-selection, truncated output, and missing-tool results are failures —
  the v5 rules carry forward unchanged.

## 7. Context selection and cost accounting

- A per-task **context manifest** is derived from the record: applicable
  authorization and repository rules, the task's touched-surface mapping,
  current acceptance and unresolved constraints, valid evidence pointers, and
  the precise next action. History loads by trigger, as in v5 read tiers.
- Summaries and stale-able artifacts carry the fingerprint of the inputs they
  summarize; a fingerprint mismatch invalidates the summary (freshness check),
  and missing impact mappings widen inspection rather than guess.
- Four quantities stay distinct and separately reported: static instruction
  bytes, provider tokens (where the host exposes them), derived monetary cost
  (only from real rates, never bytes-to-money substitution), and wall-clock
  time. Missing data is exposed as missing, not imputed.
- Model routing is optional and separate from fixed-model efficacy claims;
  campaigns pin model settings per stratum.

## 8. Resources and capability negotiation

- The contract's resource envelope declares, per limit, whether it is
  **enforced** (a host adapter can actually stop the agent) or **advisory**
  (the agent is instructed and reports, but nothing can stop it).
- A prompt-only skill cannot enforce a hard provider spending cap or prevent
  arbitrary tool access; the core therefore reports posture honestly:
  enforced limits are checked at dispatch; advisory limits are surfaced in
  every checkpoint and completion record. Enforcement parity across hosts is
  never claimed — each host adapter names what it enforces.
- Host adapters are optional, live under the pack's addon/adapter layout, and
  degrade to advisory when absent. Exhaustion of an enforced limit persists
  incomplete state (checkpoint + blocked record) rather than fabricating
  completion.

## 9. Compatibility, migration, rollback

### 9.1 Records and schemas

- New artifacts (`contract.json`, `journal.ndjson`, v6 `state.json`) use new
  schema-URL generations; the published v1/v2/v5 schemas stay byte-unchanged;
  v6 state is a new generation, not a mutation of v5 shapes (closed objects
  force this — the same rule that produced v2/v5).
- Existing v5 (and older) plans retain their recorded lifecycle, source of
  truth and tooling until an explicit migration.

### 9.2 Preserved surfaces

Skill names, slash-command set, `.dwp/plans/PLAN_{name}/` layout, `DWP_DIR`/
`DWP_AGENT_TOOL` overrides, `setup.sh` flags and resulting symlink names are
preserved. The v6 reader accepts v5 plans read-only; it never rewrites them.

### 9.3 Migration

Migration is explicit (`migrate`-style request), one-directional, and
performs: preview → backup → integrity check → stable-ID and evidence mapping
(v5 task numbers become `T-*` ids; gate records become journal items with
provenance "migrated") → interruption recovery at each step, in the shape of
the existing promotion-recovery contract. A failed or interrupted migration
leaves the v5 plan recoverable — resume the migration from its recorded
phase marker or restore the backup — and resumable under v5. Rollback after
a completed migration means restoring the backup; the journal records the
migration event either way.

### 9.4 The major, concretely

The major version is justified by the changed **new-plan execution and state
contract**: plans materialized under v6 carry the outcome contract, the
journal, and scheduler/authorization semantics that v5 runners do not
implement. That is a behavior change to the public plan format — the honest
major rationale. Frontmatter package versions and the changelog remain
release-bot owned; nothing in this RFC hand-edits them.

## 10. Packaging and portability

- The v6 core ships inside `skills/deepworkplan/` as stdlib Python 3.9+
  helpers and Bash 3.2-compatible shell entry points; no contributor files,
  no network calls, no database service, no required cloud.
- Helper inventory (`TRUST.md` self-audit) extends mechanically; the pack
  still runs from an exported copy with no repository checkout.
- Instruction accounting applies to new flow text: helpers are executed, not
  loaded, and flow read tiers keep their guarded bounds.

## 11. Deterministic guarantee matrix

| Boundary | Positive control | Negative/fault control | Kind |
| --- | --- | --- | --- |
| Authorization | In-scope adaptation accepted | Scope/acceptance/permission expansion refused | Runtime invariant |
| Dependency scheduling | Ready task selected | Cycle, missing prerequisite, starvation | Runtime invariant |
| Evidence validity | Equivalent-input reuse accepted | Dirty input/toolchain change invalidates evidence | Runtime invariant |
| Test reality | Nonempty passing assertions | Zero tests, truncated output, missing binary | Runtime invariant |
| Completion | Verified outcome closes | Narrative-only claim or missing acceptance refuses | Runtime invariant |
| Recovery | Resume from durable checkpoint | Crash at each write/publication boundary | Runtime invariant |
| Persistence | Idempotent replay | Duplicate/concurrent/corrupt submissions | Runtime invariant |
| Resource limits | Dispatch within supported limit | Exhaustion persists incomplete state | Host control where enforced; instruction contract where advisory |
| Context | Relevant complete constraints delivered | Stale summaries, deleted files, missing mappings | Runtime invariant + instruction contract |
| Compatibility | Historical plan continues | Silent migration or dropped evidence refused | Runtime invariant |
| Packaging | Exported pack runs alone | Missing Python reports UNVERIFIED | Runtime invariant |

Runtime invariants are implemented and tested in the deterministic core;
host controls are enforced only where a host adapter exists; instruction
contracts are taught in flow text (contract presence, never model obedience);
empirical claims are made only by the evaluation campaigns, never by this
RFC.

## 12. Alternatives considered

- **Keep v5's single `state.json` and add prose conventions for adaptation** —
  rejected: adaptation audit and evidence identity are exactly the fragile
  model bookkeeping v6 exists to remove.
- **SQLite record store** — rejected for v6 (§4.2); revisitable on evidence.
- **Distributed event platform / cloud orchestrator** — rejected: violates the
  portability and local-first product properties for a need single-plan
  execution does not have.
- **Mandatory fresh-model verification of every task** — rejected: cost must
  earn inclusion per criterion; negative controls give discrimination without
  unconditional duplication.

## 13. Non-goals (deferred with reasons)

Cross-project permanent memory; autonomous modification of global skills;
broad agent swarms; vendor-specific model preferences; a cloud orchestration
service. A later proposal may add any of these if ablation evidence shows the
need; v6 already changes foundational behavior enough to require isolation
and compatibility discipline.

## 14. Open questions for implementation tasks

1. Exact v6 schema shapes (field-level) — owned by the contract/schema task,
   including the journal event object catalog.
2. Journal roll and truncation policy for very long campaigns — bounded by
   the measurement tasks' data.
3. Which host adapters ship in the first release vs remain documented
   interfaces — decided by the resource/capability task with the campaigns'
   host evidence.
4. Deterministic-view file naming and layout inside the plan folder — owned
   by the ledger task.

## 15. References

- `skills/deepworkplan/spec/PLAN_STATE.md` (v5 state layer, guarded updates,
  evidence truth, migration)
- `skills/deepworkplan/shared/state_contract.py` (enforced evidence semantics)
- `skills/deepworkplan/execute/SKILL.md`, `skills/deepworkplan/refine/SKILL.md`
  (flow contracts, amendment records)
- `PLAN_v6_verified_autonomy` `analysis_results/ARCHITECTURE.md` and
  `EVALUATION_PROTOCOL.md` (local gitignored planning inputs; the sanitized,
  version-controlled record is this directory, and campaign evidence is
  exported here by the implementation tasks)
- `docs/evaluations/v6/DECISIONS.md` (decision log for this RFC)
- `PLAN_v6_verified_autonomy` `analysis_results/ARCHITECTURE_REVIEW.md` (the
  local gitignored record of the independent design review; its findings and
  dispositions are incorporated in this draft-1 text)
