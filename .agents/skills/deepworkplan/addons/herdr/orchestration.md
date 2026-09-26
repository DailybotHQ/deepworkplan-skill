# orchestration.md — delegating plan work across the mesh

How `execute` uses the mesh: delegate independent tasks, record the
delegation, join on the plan.

## 1. What may be delegated

Only tasks the plan marks safe to run in parallel (or that the orchestrator
verifies are independent): no shared writable paths with any active task, no
dependency on an unfinished sibling, acceptance criteria expressible without
the orchestrator's private context. When in doubt, do not delegate.

## 2. The brief (self-contained by construction)

Each peer receives, in ONE prompt: the workspace path (already prepared),
the task objective with its acceptance criteria, the standing constraints
that touch it, the reply grant (templates.md), and nothing else — no plan
index, no other cases, no orchestrator context. If the brief would not make
sense to a stranger standing in that workspace, the task is not ready to be
delegated.

## 3. Record before relying

Before the prompt is sent, the orchestrator appends to the plan's
delegation record: peer address, task id, workspace, brief hash, sent-at
time, reply grant id. The record is the orchestrator's memory: a pane that
dies mid-task is reconstructed from disk + record, not from chat.

## 4. Join on the plan

Replies update the delegation record and the task state; the orchestrator
reconciles when its delegated set is done (or on a peer's escalation),
validates the artifacts with the same oracles it applies to its own work,
and continues the plan. It does not stop to narrate hops. Failing artifacts
are re-worked, re-delegated, or escalated — never accepted because a peer
said done.

## 5. One writer per path

Before delegating, the orchestrator checks the task's touched paths against
every active delegation. Two writers on one path is an orchestrator defect,
not a peer defect: re-plan, then delegate.

## 6. Choosing peers

Prefer idle over working; `done` is free; `blocked` deserves a title read
before any ask. Providers do not matter to routing — only workspace fit and
state do. A peer that failed the same kind of task this round is not
reassigned the same task without a changed brief.

## 7. Launching when the mesh is empty

If the plan benefits from a peer and none is available: start one
(`herdr agent start`, provider + cwd per the task), re-run discovery to
learn its address, record the launch as a delegation. Launch failure or a
missing provider is recorded and the orchestrator continues single-agent —
launching is an optimization, never a dependency.

## 8. Failure, retries, and honesty

Two attempts per delegation; then record, escalate if the escalation
contract applies, and continue with the rest. A peer's `done` is never
accepted as evidence: artifacts pass the same oracles as everything else.
Nondeterministic failures (races, rate limits) are re-run after the pacing
note in the orchestrator's log, not in a tight loop.
