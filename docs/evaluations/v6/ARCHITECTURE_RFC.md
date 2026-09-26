# DWP v6 Architecture RFC — bounded adaptive execution with verified outcomes

| Field | Value |
| --- | --- |
| Status | Proposed (red-teamed draft; not yet normative) |
| Version | draft-3 (2026-09-26) |
| Elaborates | `PLAN_v6_verified_autonomy` `analysis_results/ARCHITECTURE.md` (planning proposal; a local gitignored planning input — this RFC is its version-controlled successor) |
| Normative successor | A future `spec/` revision produced by the implementation tasks; this RFC is not normative until that revision exists |
| Baseline | DWP spec 5.0.0 (the frozen v5 runner; this plan does not migrate itself) |

RFC-2119 language is used prospectively: it describes what the v6 specification
will require. Nothing here changes the installed v5 pack's behavior; the v5
contracts remain in force for every plan that has not migrated.

Incorporated reviews. draft-1 applied the independent design review
(`analysis_results/ARCHITECTURE_REVIEW.md`, F1–F11). draft-3 applies the
D2 delta review (`analysis_results/ARCHITECTURE_REDTEAM_D2.md`, D2-1–D2-10:
the draft-1 sentences the A1 fix invalidated are excised, the §11 matrix
rows carry their modes, approval-record binding, reconciled authority,
migration contract synthesis and the control-pair old-leg rule are
specified). draft-2 applied the
adversarial red-team (`analysis_results/ARCHITECTURE_REDTEAM.md`, findings
A1–A13, buried capabilities B1–B5, upgrades U1–U5):

- **A1** — the core is designated gate executor; `observed` means *executed*, not *mediated* (§4.5, §5).
- **A2/A3** (via U1) — the contract is REQUIRED for every v6 new plan; approval is bound to content-addressed bytes, scaling by plan mode (§3.1).
- **A4** — reconciliation-completions close on recorded `reconciled` authority, never silently on evidence classes (§4.4).
- **A5** — envelope metering source named per limit; commit-plus-pending accounting; command classes rescoped to declared gate commands (§3.2, §5, §8).
- **A6** (via U2) — negative controls gain mechanical residency: helper-executed counterfactual replay pairs (§6).
- **A7** — migrated gate records are `asserted`, never `observed`; observed-only criteria do not inherit completion (§9.3).
- **A8** (via U5) — single-writer is a designed boundary; team agents map onto per-worker child plans; the checker refuses concurrent execute sessions (§4.2, §9).
- **A9** — invariant evaluation boundaries defined; purity preserved by injecting status through the record (§5).
- **A10** — journal durability posture: export command, archetype-named single-copy risk, roll constraint (§4.3).
- **A11** — starvation aging gets clock, threshold and action (§5).
- **A12** — interlocks specified as implementation requirements (§14).
- **A13** — `intervention` events adopt the evaluation protocol's category taxonomy (§4.1).
- **U3/B1/B4** — audit surfaces ship: refusals-and-interventions view and completion profile (§4.4). **U4/B2** — dead-end digest in the context manifest (§7). **B3** — approval diffs (§3.1). **B5** — journal replay against candidate contract revisions (§6).

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
| 17 | Verified publication: completion is a transaction with a `FINALIZATION.json` receipt, a `.finalizing.json` recovery marker, and UNVERIFIED (never completed) without Python (PLAN_STATE "Verified plan publication") | **Retained**; the v6 terminal transition additionally emits journal events, and validates the completed projection under the same receipt contract as v5, extended to the v6 projection (reconciled closures and control_pair evidence the v5 validator does not model) |

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
an in-place edit.

Unlike the v5 state layer (whose equivalent artifact is optional for interactive
git plans), the contract is **REQUIRED for every v6 new plan**: the
authorization core is undefined without one — there is nothing to authorize
against, no closed adaptation enumeration to check, and the §11 Authorization
row has no subject. A v6 plan without a contract is a materialization failure,
not a mode. What scales by plan mode instead is the **approval** record (U1):

- **Interactive git plans** — the plan markdown the developer reviewed is the
  consented artifact; the contract is its generated projection. The execute
  flow renders the contract in its plan-review step, so a human can compare
  the projection against the plan before the first task starts.
- **Unattended and non-git plans** — approval cites the recorded
  pre-authorization (the AGENT_PROTOCOL §7 pattern). Because a
  pre-authorization written before materialization cannot name bytes that do
  not exist yet, the citing record is written **at materialization**, under
  the create-time approval's authority.
- **Both modes write the same approval record at materialization** (this is
  what makes the first-task-start refusal rule mode-uniform, D2-3): a
  journal event of type `approval` (D3-7) carrying `{authority,
  mechanism, contract_id, plan digest}`, where *mechanism* is
  `plan_authorship` (interactive: authority = the session user) or
  `pre_authorization` (unattended/non-git: authority = the recorded
  pre-authorization); migration re-uses `pre_authorization` — the recorded
  pre-authorization is the migration request (§9.3, D3-2). The guarded writer refuses the first
  task-start transition when the record is missing or cites bytes other
  than the live `contract_id`. Because identity is content-addressed, any
  later regeneration that drifts from the approved bytes is a new revision
  requiring the amendment path (B3); the drift comparison runs at
  task-start authorization, where the live `contract_id` is re-derived.
- Contract **revisions** (§3.4) always require explicit recorded authority —
  plan authorship never carries over to a revision.

The v5 optionality matrix survives unchanged for v5 plans; v6 changes only new
plans (§9.1–9.2).

### 3.2 Required content

| Section | Fields |
| --- | --- |
| Outcome | desired outcome statement; success definition; explicit out-of-scope list |
| Acceptance | criteria with stable IDs (`AC-*`), each naming an **observable** check (behavior, interface, stored state) and its evidence class |
| Invariants | global conditions that must hold at every boundary; violation is a stop, not an adaptation |
| Scope | allowed paths; allowed command classes; forbidden operations (destructive, outward-facing) |
| Authorization | source of authority (who/what approved), timestamp, boundaries of pre-approval; consent checkpoints carried verbatim; the binding *mechanism* (`plan_authorship` or `pre_authorization`, §3.1). The citing approval record itself is the materialization-time journal event of §3.1, never contract content — a record inside the contract cannot cite the contract's own content-addressed `contract_id` (D3-1) |
| Permissions | tool/host capabilities granted, and explicitly those NOT granted |
| Dependencies | external systems, credentials required (names only, never secrets), pinned inputs |
| Resource envelope | dispatch limits, wall-clock budget, tool-policy limits, and a spend ceiling **only where the host can enforce it** (declared `enforced` or `advisory`, §8); each enforced limit names its metering source (host adapter reading real spend — asserted samples are advisory-only, §8) |
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
  uses them to verify that snapshot-cited journal items exist; after a
  reconciliation regenerates the snapshot from markdown (§4.4), positions the
  journal cannot support are recorded as `regenerated`, never fabricated).
  Same
  closed-object discipline, same guarded-writer rules as v5.
- **`journal.ndjson`** — the append-only *event log*: one closed JSON object
  per line (`gate_run`, `approval`, `observation`, `adaptation`,
  `amendment`, `intervention`, `resource_sample`, `control_pair`,
  `view_render`, `reconciliation`, `journal_repair`; the full catalog is an
  implementation-task deliverable, §14.1). The `approval` event is the
  §3.1 materialization-time approval record; the guarded writer's
  first-task-start refusal scans for it by type. `intervention` events carry the
  evaluation protocol's four intervention categories as a closed `category`
  field (`missing_intent`, `new_authority`, `environment_repair`,
  `engineering_rescue`; TELEMETRY.md is the enumeration's source of record,
  D3-11), so campaign extraction and product records share one taxonomy (A13);
  `control_pair` events record counterfactual replay legs (§6). Events are
  never edited
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

The selection's single-writer premise is a **designed boundary, not a silent
regression** of v5's team agents and orchestrator child plans (spec §8–§9, A8):
v6 new-plan records are single-writer; the checker refuses concurrent execute
writers on one plan (the cooperative lock detects concurrent writers; concurrent sessions that never write simultaneously are caught at write time by the position check, not by the lock); parallel
work maps onto per-worker **child plans** (U5): intra-repo parallelism
(the §9 team-agent regression) runs as **sibling plans under the same
`.dwp/plans/`**, each worker its own contract and journal scoped to §9's
declared file ownership, the parent aggregating through the §8
orchestrator tracking-table shape — which otherwise governs the cross-repo
hub — and never writing the children's paths (D3-8).
v5-shaped plans keep v5 team-agent semantics untouched (§9.1–9.2).

### 4.3 Write discipline

- The snapshot is rewritten only by the guarded updater, atomically, at the
  v5 protocol points (materialization, task start, gate runs, completion,
  checkpoint, blocked).
- Journal appends go through a shipped stdlib helper — the
  `update-state.py` pattern: cooperative `.lock` directory, closed event
  objects, and a provenance stamp (helper identity, `contract_id`) applied at
  write time. This makes §4.5's trust labels mechanically meaningful for
  helper-**executed** records; a helper-mediated write — a helper writing
  down a result it did not execute — carries `asserted`, never `observed`
  (§4.5). As with the v5 lock, **no protection is claimed
  against editors that bypass the writer**; read-time structural checks and
  the read-only checker report what the records can show.
- A torn final line (crash mid-append) is repaired on the next writer open:
  the incomplete tail is truncated and an explicit `journal_repair` event
  records the byte offset and cause — the append-only rule binds *complete*
  events. The snapshot, never the journal, is the recovery root.
- **Durability posture (A10):** the journal is the plan's memory and `.dwp/`
  is conventionally gitignored, so the core ships an **export** command
  (journal + snapshot + contract chain to a destination the operator names),
  offered at campaign boundaries and at completion; in the agent-workspace
  archetype (no git) the plan folder is the only copy, and the onboarding
  text names that risk with the export command beside it. Rolls may not
  discard snapshot-cited positions (§14).
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
property therefore scopes to the journal→snapshot direction. A task that
reaches `completed` through reconciliation closes with **recorded authority
`reconciled`** in the §3.2 sense — the `reconciliation` event carries the
trigger, the editor whose change won, a timestamp and the re-derived
`contract_id`, not a bare mechanism label. Reconciliation restores record
consistency; it does not manufacture evidence (D2-4): a criterion that
declares an evidence class closes on `reconciled` only under amendment
authority (§3.4) — otherwise the task's criterion downgrades to `blocked`
with the reconciliation recorded, and the completion profile below shows
which closure mechanism every criterion used (A4). Snapshot regeneration
enforces the v5 row-4 gate-completeness check on completed tasks: a
completed task whose gates did not survive reconciliation is a
reconciliation case, never a silent pass.

Generated views include the **audit surfaces** (U3): a
refusals-and-interventions view (every refused proposal and intervention
event, by class, with reasons and proposal pointers — the refusal ledger is a
trust surface, B1) and, at completion, a **completion profile** (per
criterion: the closing mechanism — the evidence item with its trust label and
pointer, or `reconciled` authority — B4). Both are pure projections of
journal and snapshot under the D12 generated-view discipline: labeled records
of recorded proposals, no aggregation into indices or ratings — "0 refusals"
records that nothing was proposed, not that nothing would have been refused.

### 4.5 Trust labels on evidence

Every journal evidence item carries one label:

1. **observed** — the record was produced by a shipped helper that **itself
   executed** the command or check (declared cwd, environment, timeout and
   captured outputs under the core's control, §5); a helper that only writes
   down a model-reported result mediates a write, not an execution, and the
   item is `asserted` with the mediation named (A1);
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
  Purity holds because everything it consumes is **in the record** (A9):
  invariant status is the latest helper-executed invariant evaluation the
  record carries — invariants are evaluated at defined boundaries (task
  start, gate run, completion), never inside `authorize()`, and a stale or
  failed invariant makes `authorize()` refuse (a stop, not an adaptation).
  *Stale* means: the invariant was last evaluated at a journal position
  earlier than the current task's starting position — the task-start
  boundary re-evaluates it before authorizing, and the boundary's own
  evaluation event is recorded at or after the task-start event (so
  mid-task proposals never see their own boundary's evaluation as stale;
  D3-6).
  Envelope accounting is **commit-plus-pending** (A5): the check totals
  recorded spend plus dispatched-not-yet-completed work — each pending
  proposal contributes its declared resource impact, or the last measured
  cost of the same task shape when undeclared — so two sequentially
  authorized proposals cannot jointly overshoot an enforced limit.
- **Measured observations** (gate runs, resource samples) are `observed`
  only when the core's runner **executed** them — the executor rule above
  (A1, §4.5). A helper writing down a result it did not execute mediates a
  write, not an execution: that item is `asserted` with the mediation
  named, exactly like an agent assertion. An acceptance criterion that
  requires `observed` evidence is satisfied only by runner-executed items;
  a hand-written line claiming `observed` is a writer bypass — reported by
  the checker where the records allow, and named honestly in the format's
  limits rather than claimed impossible.
- **The core is the gate executor** (A1): gate commands run through a shipped
  stdlib runner helper — subprocess with the declared cwd, environment,
  timeout and captured outputs — which is what makes `observed` mean
  *executed* rather than *mediated* (§4.5). On hosts where a command cannot
  run through the runner (interactive-only tooling), the flow records the
  result as `asserted` with the mediation named; the §11 matrix labels those
  rows' mode accordingly instead of implying an execution that never
  happened.

Blocked work may permit safe independent in-scope work; a global invariant
failure or exhausted envelope stops dispatch. Starvation protection: ready
task selection uses oldest-blocked-wait aging — the clock is journal event
timestamps, the threshold is contract-declared (with a default), and the
action is a recorded priority boost in selection, itself a journal event
(A11). Caps: maximum adaptations per
task, maximum retries per gate, both declared in the contract. Handoff
conditions (fresh context, cross-host resume) are explicit contract fields.

## 6. Observable outcome verification

- Every acceptance claim points to **evidence of behavior**: a regression
  test that fails on the original defect, a detected safe mutation, a
  rejected invalid input, or an interface-level check that discriminates a
  known-broken implementation. Which negative control applies is decided at
  contract authoring per criterion; minor prose/cosmetic changes are exempt.
- A declared regression or discrimination control has **mechanical
  residency** (U2, closing A6): the core executes both legs itself and
  records the observed `control_pair`. The **old leg is materialized
  deterministically** (D2-6): a worktree at the recorded starting
  fingerprint carrying only the gate's declared check artifacts from the
  working tree — declared as an explicit `check_artifacts` path list on the
  v6 gate record's `control_pair` event (the v5 gate object has no such
  field, so the declaration is v6 surface; D3-4). Exactly the listed files
  travel back; product files stay at their starting state; and user dirty state is never reverted (§2 row 16). The
  new leg runs against the working tree. A worktree materializes a
  revision only, and the fingerprint's dirty component (§2 row 16:
  revision plus dirty state) is a comparison string, not replayable state —
  so when the recorded starting fingerprint carries a non-empty dirty
  component, the pair likewise records `control=unavailable`, never a
  misrepresented clean old tree (D3-3). On non-git hosts the old leg
  cannot be materialized from a fingerprint alone — the pair records
  `control=unavailable`, never a synthesized old-tree result. The control
  passes only on
  (old: FAIL, new: PASS). (PASS, PASS) is recorded as **non-discriminating**,
  never rounded up to a pass; an unavailable leg records
  `control=unavailable`. The lab's own calibration matrix
  (pristine=FAIL / known_good=PASS / broken=FAIL) is exactly this pair
  check; the AC-6 cosmetic stubs and the AC-2 green-build sabotage are
  caught by pair discrimination and by nothing weaker. Helper-executed legs
  carry the `observed` label (§4.5), which anchors A1 for this leg.
- Because `authorize()` is pure over the record, a journal also **replays
  against a candidate contract revision with zero execution** (B5): "this
  amendment would have refused N recorded adaptations" is a projection the
  amendment path offers, so a developer sees a revision's teeth before
  approving it.
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
- The manifest carries a derived **dead-end digest** (U4, surfacing B2):
  failed gates with causes, refused or abandoned strategy changes, and
  inserted experiments with their discriminating results — each a recorded
  event with a pointer, never advice or probabilities. Stale entries age out
  under the same fingerprint invalidation that governs summaries; the target
  is the protocol's sustained-completion question (stop retrying known-dead
  approaches), measured by the interruption increments the lab blueprint
  already defines.
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
- Each enforced limit names its **metering source** (A5): a host adapter
  reading real provider meters, or asserted samples. `authorize()` never
  enforces on asserted meter data — an asserted meter degrades the limit to
  advisory, and the record says so.
- "Allowed command classes" are decidable only for **declared gate commands**
  that the core validates and executes (§5); arbitrary shell (`bash -c`,
  environment indirection) is undecidable, and is therefore **detection plus
  reporting, never prevention** — the guarantee matrix labels those rows'
  mode honestly instead of claiming a boundary no prompt can hold (A5).
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
performs: preview → backup → integrity check → **contract synthesis** →
stable-ID and evidence mapping (v5 task numbers become `T-*` ids; gate
records become journal items with provenance "migrated" labeled `asserted`
— agent-invoked history is a claim, not a helper execution, and criteria
that do not accept `asserted` evidence do not inherit completion from
migration — the migrated label names the bar (the criterion's
accepted-evidence set), not one specific set (D3-5): the preview lists them as **re-evidence criteria** together
with the task that will re-run their gates and the envelope those re-runs
draw on, and they close when new helper-executed evidence lands, A7) →
interruption recovery at each step, in the shape of
the existing promotion-recovery contract. **Contract synthesis (D2-5):**
because §3.1 and §14.5 refuse post-migration execution without a
contract, the migration itself synthesizes one from the mapped plan —
outcome, acceptance criteria (with their evidence classes), invariants,
scope and remaining envelope — and writes the materialization-time
`approval` journal event (§3.1) citing the synthesized `contract_id`, with
mechanism `pre_authorization` and the migration request as the recorded
pre-authorization (D3-2). A plan whose completed tasks now hold
re-evidence criteria is `blocked`-by-default at those criteria, not
completed; the preview states this. A failed or interrupted migration
leaves the v5 plan recoverable — resume the migration from its recorded
phase marker or restore the backup — and resumable under v5. Rollback after
a completed migration means restoring the backup; the journal records the
migration event either way.

Reverse compatibility, one line (D2-10): a v6 plan opened by a v5 runner is
**unsupported** and refuses with a clear error naming the contract pointer —
the spec §6.5 unknown-format pattern, never a guessed legacy parse.

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
| Authorization | In-scope adaptation accepted | Scope/acceptance/permission expansion refused; first task-start without an approval record citing the live `contract_id` bytes refused | Runtime invariant (mode-uniform approval record, §3.1) |
| Dependency scheduling | Ready task selected | Cycle, missing prerequisite, starvation | Runtime invariant |
| Evidence validity | Equivalent-input reuse accepted | Dirty input/toolchain change invalidates evidence | Runtime invariant (structural); execution trust follows §4.5 labels |
| Test reality | Nonempty passing assertions | Zero tests, truncated output, missing binary; non-discriminating control pair (PASS, PASS) | Runtime invariant where the gate command runs through the core's runner; detection + reporting where it cannot (§5) |
| Completion | Verified outcome closes | Narrative-only claim or missing acceptance refuses | Runtime invariant |
| Recovery | Resume from durable checkpoint | Crash at each write/publication boundary | Runtime invariant |
| Persistence | Idempotent replay | Duplicate/concurrent/corrupt submissions | Runtime invariant |
| Resource limits | Dispatch within supported limit | Exhaustion persists incomplete state | Host control where enforced; instruction contract where advisory |
| Context | Complete constraints structurally delivered | Stale summaries, deleted files, missing mappings | Runtime invariant (structural presence) + instruction contract (relevance) |
| Compatibility | Historical plan continues | Silent migration or dropped evidence refused | Runtime invariant |
| Packaging | Exported pack runs alone | Missing Python reports UNVERIFIED | Runtime invariant |

Runtime invariants are implemented and tested in the deterministic core;
host controls are enforced only where a host adapter exists; instruction
contracts are taught in flow text (contract presence, never model obedience);
empirical claims are made only by the evaluation campaigns, never by this
RFC. Every row is testable for every v6 new plan because the contract is
always present (§3.1); a row whose control depends on host metering or on a
command that cannot run through the core's runner carries that mode in the
row itself (§5, §8) — no row implies an enforcement the host does not have.

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
   including the journal event object catalog (with the `approval` event of
   §3.1, `intervention.category` from TELEMETRY.md's taxonomy, and the
   `control_pair` shape with its `check_artifacts` declaration, §4.1/§6).
2. Journal roll and truncation policy for very long campaigns — bounded by
   the measurement tasks' data.
3. Which host adapters ship in the first release vs remain documented
   interfaces — decided by the resource/capability task with the campaigns'
   host evidence.
4. Deterministic-view file naming and layout inside the plan folder — owned
   by the ledger task (including the audit surfaces of §4.4).
5. Interlocks specified as implementation requirements (A12): `T-*` ids are
   minted by the guarded writer with collision refusal, never by the
   scheduler; journal rolls may not truncate below the highest
   snapshot-cited position (or the snapshot re-cites post-roll) —
   `regenerated` positions (§4.1) are views, not journal positions, and are
   ignored for roll bounding, forcing nothing; a crash
   between manifest and contract leaves a plan whose v6-ness is discoverable
   through the manifest's contract pointer — the writer materializes the
   contract before the first task and refuses execution without it.
6. Context-manifest derivation rules — which record fields produce which
   manifest sections, and the dead-end digest's inclusion window (§7) —
   owned by the context task.

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
  dispositions were incorporated in the draft-1 text)
- `PLAN_v6_verified_autonomy` `analysis_results/ARCHITECTURE_REDTEAM.md` and
  `ARCHITECTURE_REDTEAM_D2.md` (the local gitignored records of the
  adversarial red-team and its draft-2 delta review; findings A1–A13,
  capabilities B1–B5 and upgrades U1–U5 are incorporated in draft-2, the
  delta findings D2-1–D2-10 in this draft-3, and the red-team's own
  citations of the lab's oracle-calibration evidence are
  the empirical grounding for §6's control pairs)
