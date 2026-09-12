# Lite and Full Plan Lifecycle

| Field | Value |
| --- | --- |
| Version | 4.0.0 |
| Status | Stable |

## Representation and lifecycle

Each plan has one folder and immutable creation manifest. `lite` stores compact,
executable task records in the README; `full` stores detailed task files. Lite is
not a partial Full plan: it has stable task IDs, anchors, touched surface,
acceptance criteria, gates, completion evidence and a Final Review.

Format, materialization, approval and execution are independent. Format is
`lite` or `full`; materialization is `materializing`, `ready` or `promoting`;
approval is `pending`, `approved` or `pre_approved`; execution is `pending`,
`in_progress`, `blocked` or `completed`. Guided create writes a reviewable
pending proposal. Trust materializes a ready pre-approved format and returns
control. Create and promotion never execute product work. An explicit execute or
resume request approves the ready plan's current scope; record that approval
before starting work. Without that request, a pending proposal is not executable.
Unresolved promotions always require recovery before product work.

## Creation and selection

`/dwp-create` serves planning intent at every scale. Small bounded work uses
Lite; a direct edit, explanation, status, resume or explicit no-plan request
keeps its intended route. `lite`/`full` are format preferences; `trust`/`auto`
are interaction options. Boundary options can appear at either end in any order:

```text
/dwp-create trust fix the label
/dwp-create lite trust fix the label
/dwp-create fix the label trust lite
/dwp-create fix the migration full trust
```

No preference requests an explainable recommendation. An explicit Full wins.
An explicit Lite is honored when compact task records carry all requirements and
gates; otherwise DWP records why Full is required. Identical options repeat
idempotently; conflicting formats are an error. `--` ends option parsing.
Selection records observed scope, dependencies, required instruction detail,
unknowns and rationale; it is an auditable judgment, not a cross-model guarantee.

## Promotion and compatibility

Promotion is representation-only: it writes intent, destination tasks, validates
coverage, switches authoritative README/state, then clears the marker. Execute
and resume stop while a marker remains. Unchanged task IDs and evidence persist;
new scope follows refine and invalidates affected evidence. Full-to-Lite is not
automatic. v1 Full and legacy plans retain their recorded shape. v1 schemas stay
closed; Lite uses v2 schema URLs with typed inline/file locators. Creation format
lives in the immutable v2 manifest. Mutable format, materialization, approval and
promotion live in `state.json`, which is the machine-readable authority; the
README carries the same facts in human-readable form and wins on task-completion
desync. `approval` is optional in the v2 state schema so that a plan written
before it was recorded still validates: when it is absent, treat the README's
`Approval` row as the value, and `pending` when neither is present. The refined
draft, the `.dwp/drafts/` directory and the `refined-draft` /
`from-refined-draft` / `from` parameters were removed in 2.4.0; `create` writes
the plan folder and nothing else.
