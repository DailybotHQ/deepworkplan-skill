# A v6 Plan — Minimal Worked Example

A v6 plan is **two authored artifacts + one guarded sequence**. Allocate the
folder with `shared/plan_paths.py` before authoring; this example uses the
first ID in a new repository. This
example shows the smallest honest shape; the normative rules live in
[`../spec/V6_CONTRACT.md`](../spec/V6_CONTRACT.md) (contract + journal)
and [`../spec/V6_LIFECYCLE.md`](../spec/V6_LIFECYCLE.md) (detection,
materialization, activation, amendments, coexistence).

```
.dwp/plans/PLAN_001_ship_feature_x/
├── README.md          # the human plan (what the approval digests)
├── 1.task_implement.md
├── 2.task_final_review.md
├── manifest.json      # WRITTEN BY materialize — contract pointer
├── contract.json      # WRITTEN BY materialize — stamped, content-addressed
├── journal.ndjson     # first event: the approval
└── ...                # state.json / views/ / gates/ are generated later
```

## 1. The markdown (authored)

`README.md` carries the goal, the task list and the execution rules — the
recorded create flow's shape, unchanged. Task files declare their
objective, `Touched Surface`, `Read Before Starting`, `Acceptance Criteria`
with `AC-*` ids, and `Validation` gates. The last task is the Final Review.

## 2. The contract draft (authored, outside the plan folder)

```json
{
  "schema": "https://deepworkplan.com/schema/plan-contract/v6.json",
  "spec_version": "6.0.0",
  "plan": "PLAN_001_ship_feature_x",
  "revision": 1,
  "created_at": "2026-09-26T12:00:00Z",
  "title": "Ship feature X under the v6 contract",
  "outcome": {
    "statement": "Feature X ships with verified behavior.",
    "success_definition": "Both acceptance criteria hold on observed evidence.",
    "out_of_scope": ["publicity", "release tagging"]
  },
  "acceptance": {
    "criteria": [
      { "id": "AC-tests-pass", "statement": "The suite passes.",
        "observable_check": "the repo's test command exits 0",
        "accepted_evidence": ["observed"] },
      { "id": "AC-human-review", "statement": "A human reviewed the diff.",
        "observable_check": "review sign-off recorded",
        "accepted_evidence": ["asserted"] }
    ]
  },
  "tasks": [
    { "id": "T-implement", "title": "Implement feature X",
      "prerequisites": [], "touched_surface": ["src/feature_x.py"],
      "gate_intent": [
        { "criterion": "AC-tests-pass", "check": "pytest -q" }] },
    { "id": "T-final-review", "title": "Final Review",
      "prerequisites": ["T-implement"], "touched_surface": ["src/", "tests/"],
      "gate_intent": [] }
  ],
  "invariants": [
    { "id": "INV-no-publication",
      "statement": "No pushes, tags or publication during this plan." }],
  "scope": {
    "allowed_paths": ["src/", "tests/"],
    "allowed_command_classes": ["python3", "pytest"],
    "forbidden_operations": ["publish", "force-push"] },
  "resource_envelope": {
    "limits": [
      { "id": "spend_usd", "unit": "USD", "limit": 40,
        "enforcement": "enforced",
        "metering_source": "host adapter: usage.total_cost_usd" },
      { "id": "wall_clock_h", "unit": "hours", "limit": 6,
        "enforcement": "advisory" } ] },
  "scheduling": {
    "max_retries_per_gate": 1, "max_adaptations_per_task": 2,
    "starvation_threshold_events": 24,
    "handoff": { "fresh_context": "context pressure at 60%",
                 "cross_host_resume": "custodian seal broken" } },
  "permissions": {
    "granted": ["gate_command_exec", "fs_write_repo_scope", "git_operations"],
    "not_granted": ["network_access", "agent_delegation"] },
  "authorization": {
    "authority": "the developer who asked for the plan",
    "mechanism": "plan_authorship",
    "boundaries": "This contract governs feature X only.",
    "consent_checkpoints": ["GO before the release commit"],
    "timestamp": "2026-09-26T12:00:00Z" },
  "dependencies": [
    { "kind": "pinned_input", "name": "python3", "detail": ">= 3.9" } ]
}
```

Validate it before proposing:
`python3 ../shared/contract_v6.py validate-contract draft.json`.

## 3. Materialization (guarded — the helper writes, never your hands)

```bash
python3 ../shared/ledger.py --plan .dwp/plans/PLAN_001_ship_feature_x \
  materialize --contract draft.json --authority sergio \
  --mechanism plan_authorship
# OK: materialized PLAN_001_ship_feature_x contract <cid> (manifest, contract,
#     approval seq 1)
```

From here the v6 execute loop runs the plan:
`ready` selects, `start` opens the attempt and records the fingerprint,
`gate` mints observed evidence, `complete` is refused until every
criterion holds, `project` + `views.py render` regenerate the
projections, `receipt` recomputes the outcome from the records.

**What never happens:** the contract edited in place after approval (a
change is a revision under `contracts/` with fresh authority — refine),
a manifest pointer rewritten, a v5 plan migrated silently, or a task
closed on narrative.
