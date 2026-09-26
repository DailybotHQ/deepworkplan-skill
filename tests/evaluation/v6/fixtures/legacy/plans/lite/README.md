# Plan: csvreport docs reconciliation (lite migration fixture)

A frozen **v5 Lite plan shape** used only for migration-compatibility
lifecycle tests. Not an arm task; not executed by campaigns.

**Standard:** DWP spec 5.0.0
**Plan Format:** Lite
Materialization: ready
Approval: pending

## Task List

- [ ] Task 1: Inventory stale README claims — (immutable anchor: #task-1)
- [ ] Task 2: Correct the K1 change-log entry — (immutable anchor: #task-2)
- [ ] Task 3: Document normalize_whitespace — (immutable anchor: #task-3)

## Task 1 — Inventory stale README claims (#task-1)

Compare README.md claims against observable behavior; list every mismatch in
the task log.

## Task 2 — Correct the K1 change-log entry (#task-2)

Rewrite the 0.3.1 entry to state K1's true status.

## Task 3 — Document normalize_whitespace (#task-3)

Add the missing API documentation for `normalize_whitespace`.
