# ADR 0003 — Guard state writes and verify terminal publication

Status: Accepted for implementation in v5 reliability closure.

## Decision and limits

Keep published v1/v2/v5 schemas immutable. Add semantic validation around the
existing projection, not a new serialization format. Markdown owns intent;
contradictory workspace/evidence is investigated, never overridden by a checkbox.
The writer validates input shape and proposed output semantics before replacement.
A gate record is an assertion supplied by the caller; tools cannot prove the
caller actually ran it or that its acceptance criteria were sufficient.

## Transition table

| Operation | Requirement | Result |
|---|---|---|
| Start/resume | ready, approved plan; valid task; no unrelated active blocker | in_progress |
| Block | explicit reason/needs, task and timestamp | blocked task and global status; recoverable checkpoint |
| Complete task | nonempty latest applicable gates; consistent success; no zero-test evidence; blocker explicitly resolved | completed with preserved first timestamp |
| Retry gate | same command identity with new evidence; other commands retained | latest result supersedes only that command |
| Skip | records omitted work, not acceptance | never makes a required plan completed; refine must resolve scope |
| Reopen | explicit refine decision and reason | pending/in_progress, prior evidence retained in logs and invalidated |
| Complete plan | all required tasks completed, no active blocker, terminal checkpoint, full conformance | completed |

Historical blockers live in logs; only the active blocker lives in state.
Do not auto-clear unrelated blockers or silently permit pre-existing failures:
record any user-accepted exception via refine and preserve original evidence.

## Non-circular finalization

A completion helper checks a candidate projection together with already-authored
Markdown and existing product/acceptance evidence before publishing state. The
candidate does not contain a fabricated success record of that invocation.
After publishing, independently verify actual artifacts read-only. Record that
check externally as a receipt; it is not a prerequisite gate for its own record.
The Final Review's gate records refer to completed source/acceptance checks.
A failed actual-artifact check prevents a completion announcement and leaves an
explicit recoverable failure marker. A repeated invocation verifies the existing
state and must not duplicate a commit, gate or external action.

Atomic state replacement is not a multi-file transaction. Use a cooperative
single-writer lock and stale-input check; interrupted Markdown/JSON writes are
reconciled using candidate validation and workspace evidence. Never claim safety
against non-cooperating concurrent editors. A crash leaves a detectable boundary,
not proof that all side effects rolled back.

## Evidence and scope amendments

Require original criterion, reason, user/plan authority, revised criterion and
invalidated consumers in a durable amendment. Fixing a broken invocation may
preserve intent; replacing an impossible experiment with an easier one changes
scope. Unexecuted scenarios are never checked as performed. Semantic review stays
explicit where prose cannot be verified mechanically.

## Test strategy

Real subprocess rejection tests assert unchanged state bytes. Independent schema
and lifecycle oracles check positive and negative controls. Fault injection covers
publication boundaries; fresh agent trials prove observed flow use, not universal
agent compliance. Runtime remains stdlib-only and all helpers ship inside the pack.
