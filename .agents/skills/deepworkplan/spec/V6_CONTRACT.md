# V6 Contract and Journal Record — Normative Surfaces

> **Status: v6 line.** This document defines the machine-readable record
> surfaces of the v6 methodology line: the outcome and authority contract
> (`contract.json`) and the append-only execution journal
> (`journal.ndjson`). The design source is
> `docs/evaluations/v6/ARCHITECTURE_RFC.md` (draft-4, decisions D13–D16);
> this document is the normative restatement for implementers. The
> published machine forms are
> [`schema/plan-contract-v6.schema.json`](schema/plan-contract-v6.schema.json)
> and [`schema/journal-event-v6.schema.json`](schema/journal-event-v6.schema.json);
> the shipped runtime validator is `shared/contract_v6.py` (Python 3.9+
> stdlib, never executes gates). The v5 standard is untouched: v1/v2/v5
> schema bytes never change, v5 plans keep their recorded lifecycle and
> tooling (§9.1–9.2), and these rules bind **v6 new plans only**.

All documents in this spec use RFC-2119 language. Where this document and a
schema disagree, the schema's machine contract wins for validation and a
fix MUST reconcile both; where this document and the runtime validator
disagree, that drift is a defect in one of them, never a feature.

## 1. The contract (`contract.json`)

One contract per plan, next to `state.json`, conforming to
`https://deepworkplan.com/schema/plan-contract/v6.json`.

**Identity.** The contract's identity is the SHA-256 of its canonical
bytes: `json.dumps(body, sort_keys=True, separators=(",", ":"))` encoded
UTF-8, where `body` is the document **without** its `contract_id` field.
`contract_id` MUST be computed by `shared/contract_v6.py::
compute_contract_id` (preview, migration and the guarded writer all call
the same function, so identity cannot fork). Every record produced under
the contract cites that id.

**Immutability.** Once execution starts the contract is immutable. A
changed contract is a NEW revision — a separate file under `contracts/`
citing `parent_contract_id` — never an in-place edit. A revision MUST
change substantive content (chain metadata alone is not a revision), MUST
cite its parent, and revisions MUST be contiguous (`revision = parent
revision + 1`). Contract revisions always require explicit recorded
authority; plan authorship never carries over to a revision.

**Required presence.** The contract is REQUIRED for every v6 new plan. A
v6 plan without a contract is a materialization failure, not a mode. What
scales by plan mode is the approval record (§2, `approval`), which is
mode-uniform in shape and written at materialization in both modes.

**Content.** The schema's `required` list is normative. Semantics a schema
cannot express are enforced by the runtime validator and are binding:

- Stable IDs — criteria `AC-*`, invariants `INV-*`, tasks `T-<slug>` —
  MUST be unique. Event identity survives task splits and reorders because
  records cite these ids, never list positions.
- The task graph MUST be a DAG: dangling prerequisite references and
  cycles are invalid graphs and MUST be refused.
- Every `gate_intent.criterion` MUST reference a declared criterion.
- `permissions.granted` and `permissions.not_granted` MUST be disjoint
  subsets of the closed capability set
  (`gate_command_exec`, `fs_write_plan_scope`, `fs_write_repo_scope`,
  `git_operations`, `network_access`, `host_adapter_metering`,
  `agent_delegation`, `context_export`). Names outside the set are
  unsupported capabilities and MUST be refused.
- `authorization.mechanism` is exactly `plan_authorship` (interactive git
  plans; the reviewed plan markdown is the consented artifact) or
  `pre_authorization` (unattended and non-git plans; migration re-uses it
  with the migration request as the recorded pre-authorization — there is
  no third value). The contract names the mechanism only; the citing
  record is the materialization-time `approval` journal event — a record
  inside the contract cannot cite the contract's own content-addressed id.
- `resource_envelope.limits[]`: `limit` MUST be a number ≥ 0 (malformed
  values are refused with the limit id named); an `enforced` limit MUST
  name its `metering_source` (a host adapter reading real spend — asserted
  samples are advisory-only and degrade the limit to advisory). Advisory
  limits carry no enforcement claim. Envelope accounting is
  commit-plus-pending: a pending proposal contributes its declared
  resource impact, or the last measured cost of the same task shape when
  undeclared, so two sequentially authorized proposals cannot jointly
  overshoot an enforced limit.
- Each criterion declares `accepted_evidence` — which trust classes
  (§3) may close it. A criterion that does not accept `asserted` never
  inherits completion from migration or reconciliation.
- Every criterion MUST be closable. For a criterion a task's
  `gate_intent` declares, `observed` is minted by its gate and `asserted`
  by a human sign-off (§3); `imported` only by a migration.
  `validate-contract` and `materialize` refuse a draft criterion that
  accepts neither `observed` nor `asserted` (an already-recorded contract
  keeps loading). A regression/discrimination control closes through its
  pair. A criterion no task declares has no evidence path and closes only
  by reconciliation with amendment authority — `validate-contract` warns.

**Allowed adaptations (closed enumeration).** The contract's scheduler may
propose exactly: `split`, `reorder`, `insert`, `change_strategy`,
`retry`. An adaptation may never delete a requirement, weaken or
substitute acceptance (a substituted check is an amendment, and the
adaptation object has no field that can carry criterion content), expand
scope or permissions, spend beyond the envelope, or mark an unexecuted
scenario complete. Criterion changes use the amendment record (original
criterion verbatim, observed finding, disposition, revised criterion,
reason, authority, affected tasks, evidence invalidated/preserved).

## 2. The journal (`journal.ndjson`)

The append-only event log: one closed JSON object per line, conforming to
`https://deepworkplan.com/schema/journal-event/v6.json`. Events are never
edited or deleted; a correction is a later event. The full catalog
(RFC §14.1) is:

| Type | Carries | Notes |
|---|---|---|
| `task_start` | `task` | Fixes the task's starting journal position (stale-invariant and aging reference). |
| `approval` | `authority`, `mechanism`, `plan_digest` | The §3.1 materialization-time approval record; the guarded writer's first-task-start refusal scans for it by type. `contract_id` rides the envelope. |
| `gate_run` | `command`, `cwd`, `env`, `timeout_seconds`, `exit_code`, `trust` | Declared execution context; `evidence_path` required for `observed`/`imported`. |
| `observation` | `statement`, `trust` | A meaningful observation at a protocol point. |
| `adaptation` | closed-§3.3 `kind`, proposal fields, `decision`, `reason` | `reason` required when `decision=refused`. `resource_impact.declared` is the pending contribution. |
| `amendment` | §3.4 shape incl. `authority` | Recorded user or developer authority required. |
| `intervention` | closed `category`, `description`, `question` | Taxonomy: `missing_intent`, `new_authority`, `environment_repair`, `engineering_rescue` (source of record `docs/evaluations/v6/TELEMETRY.md`). |
| `resource_sample` | `source`, `limit_id`, `value`, `unit`, `trust` | Missing data is exposed as missing, never imputed. |
| `control_pair` | `criterion`, `check_artifacts`, `starting_fingerprint`, `old_leg`, `new_leg`, `verdict` | Counterfactual replay leg; rules below. |
| `selection` | `task`, `priority_boost`, `aging` | The recorded starvation priority boost; `aging` required when boosted. |
| `refusal` | `subject`, `stage`, `reason` | Every refusal is itself a recorded event. |
| `view_render` | `view`, `snapshot_digest` | Generated-view discipline (§4.4 of the RFC). |
| `reconciliation` | `trigger`, `editor`, `authority` | Authority is §3.2 content, not a mechanism label. |
| `journal_repair` | `byte_offset`, `cause` | Torn-tail truncation record; the append-only rule binds complete events only. |

Envelope: every event carries `schema`, `type`, `seq` (≥ 1, strictly
increasing down the file — gaps are legal history after rolls;
regressions are corruption), `ts` (the scheduler's clock), `plan`,
`contract_id`, and `actor` (`helper` / `agent` / `host_adapter` /
`human`).

## 3. Trust labels

Evidence-carrying types only (`gate_run`, `observation`,
`resource_sample`, `control_pair`) carry `trust`:

1. **observed** — a shipped helper itself executed the check (declared
   cwd, environment, timeout, captured outputs). The runtime validator
   refuses `observed` on an actor that only mediates a write (`agent`): a
   helper writing down a model-reported result mediates, not executes,
   and the item MUST be `asserted`.
2. **imported** — from a matched external source, with provenance
   (`evidence_path` required).
3. **asserted** — stated without independent establishment.

**Human sign-off and the authority marker.** `ledger.py --plan <dir>
signoff --criterion <AC> --evidence-path <artifact> --authority <who>
[--task <T>]` records a human sign-off: a `gate_run` with `trust:
asserted`, actor kind `human` and the command `signoff (asserted, not
executed)`, citing the artifact it rests on (path + digest). It closes a
criterion only when that criterion accepts `asserted`; an observed-only
criterion refuses it. It is bound to the task whose `gate_intent` declares
the criterion and counts only inside that task's evidence window (its
`task_start`); the intent's `check` then describes the human check and is
not executed. Any other human-actor record (`append --actor-kind
human`, e.g. an amendment approval) MUST carry an explicit marker:
`--human-note <file>` (the note the human wrote, recorded by path and
digest) or an interactive confirmation on a terminal. **Trust limit:** the
ledger cannot authenticate a person. The marker makes the claim explicit
and auditable; it does not make it observed — a sign-off stays `asserted`
in every receipt (mechanism `signoff`).

Checksums establish byte identity, not semantic truth; the validator
checks structure and provenance and cannot prove arbitrary product
semantics — that limit is stated here and MUST NOT be papered over.

**Control pairs.** Verdict arithmetic is binding: `discriminating` ⟺
(old leg FAIL, new leg PASS). (PASS, PASS) is recorded
`non_discriminating`, never rounded up. (FAIL, FAIL) records
`non_discriminating` with `new_leg.outcome=FAIL` preserved. A non-empty
`dirty` component in the starting fingerprint, or an unavailable old leg,
records `control_unavailable` — an unavailable old leg carries no
outcome, never a synthesized old-tree result. The old leg carries exactly
the declared `check_artifacts` paths back to the starting-fingerprint
worktree; the declaration is the whitelist.

## 4. Validation (two halves, one contract)

- **Runtime half** — `shared/contract_v6.py`: closed-object, graph,
  identity, enumeration and verdict semantics. Ships in the pack; CLI:
  `validate-contract`, `validate-journal`, `compute-id`, `self-test`.
- **Independent half** — `scripts/check-schema-contract.py` (contributor
  side, jsonschema): validates the same committed fixtures
  (`tests/fixtures/v6/`) against the published schemas, reproduces
  `contract_id` with its own canonicalization, and asserts both halves
  agree on every probe. Semantics a schema cannot express (graph
  integrity) are runtime-only and marked so.
- `tests/v6-contract.bats` is the regression suite, including pinned
  SHA-256 of the historical v1/v2/v5 schema bytes (they never change when
  v6 files ship) and a pack-purity guard (no bytecode inside the shipped
  pack).

## 5. Compatibility

Mixed-era documents are refused, never guessed into a legacy parse: a
document declaring a v1/v2/v5 schema URL is outside this reader. Existing
plans retain their recorded lifecycle, source of truth and tooling until
an explicit migration, which synthesizes a contract, writes the
`approval` event under `pre_authorization`, and maps v5 history as
`asserted` evidence (criteria that do not accept `asserted` are
re-evidence criteria and close only on new helper-executed evidence).
