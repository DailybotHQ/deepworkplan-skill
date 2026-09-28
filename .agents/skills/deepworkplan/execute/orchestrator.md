# DeepWorkPlan — Execute: orchestrator branch (read only when Step 2.1 detected an orchestrator plan)

## Repository and execution boundaries

Preserve the v2 hand-off rule (`../guide/orchestrator.md` §13.0): the hub
creates child plans and coordinates their separate target-repository sessions;
it never executes child product work inline. A direct multi-project plan is a
different, explicitly chosen workflow. Sequential describes dependency order,
not permission to merge repository contexts. Host-supported independent sessions
may be used only when authorized; otherwise emit the hand-off and checkpoint.

Resolve and retain the absolute hub root before entering a child. Record each
child's actual repository root and plan directory in `ORCHESTRATOR_MANIFEST.md`;
`repositories/{repo}/` is a convention, not a hardcoded requirement. Read the
child's `AGENTS.md` and testing map. Do not carry a hub `DWP_DIR` into the child:
resolve in a subshell with `unset DWP_DIR`, or set an explicitly recorded
child-specific override. Return to the saved hub root; resolving the git root
while still inside a child would return the child, not the hub.

The only child writes by the hub are authorized plan creation under that child's
resolved `.dwp/`. Product edits, gates and commits belong to the child's session.
Hub tracking is also gitignored when under `.dwp/`: do not force-add plan state
or invent an empty commit. Commit only validated, owned tracked hub changes when
there are any and the plan authorizes commits.

## Orchestrator Task Types

**`create_child_dwp`:** inspect the target repo and create its child plan using
its real conventions and gates, with parent reference, input dependencies and
expected outputs. Do not install a skill, onboard a child or invent a generic
gate to hide missing prerequisites. Use the available local DWP pack; if the
child needs onboarding, record the missing commands/context and run onboarding
only when authorized. Mark `[x] Created` only after checking the child's plan
structure. Creation never means execution. Distributed mode stops at created,
ready plans; Sequential modes hand children off in their recorded order.

**`integration_checkpoint`:** compare child contracts, field names, types,
errors and expected outputs. Record each criterion and its supporting evidence.
This checks planned integration, not runtime integration: the latter is a gate
in the responsible child or a separately authorized integration task after the
children complete. A printed message or file-presence check cannot prove a
working API seam.

**`execute_child_dwp`:** use the v2 hand-off template in
`../examples/ORCHESTRATOR_TASK_TEMPLATE_execute_child_dwp.md`:

1. Read the manifest and mode. Runtime-dependent Sequential / Output Handoff
   children require completed predecessors plus their declared output artifacts.
   Contract-Parallel children require the frozen shared contract and sibling
   plans; Fully Parallel children have no predecessor output dependency. Never
   remove a real runtime dependency merely to run in parallel.
2. Verify readiness from the child README, checkpoint, gate evidence and actual
   files, not a parent checkbox alone. Read predecessor logs/security review and
   the Executive Report only if requested and produced (legacy required reports
   retain their original contract). Missing evidence is a blocker.
3. Emit a target-root execution prompt carrying the child's resolved plan path,
   authorization, mode, predecessor pointers and completion evidence expected.
   Checkpoint while waiting for the user or authorized separate session. Do not
   busy-poll, execute the child inline, or mark a hand-off as completed work.
4. After completion is reported, verify the child's top-level completion status,
   README and task evidence, applicable closing review, and declared artifacts.
   A nested completed task in JSON is not a completed plan. Missing, failed or
   unavailable validation is not success. Register `[x] Executed` and output
   references only after the evidence agrees; preserve its recorded lifecycle.

## Recovery and completion

Read the manifest on entry and resume; reconcile it with child evidence before
repeating any hand-off. Reuse a completed child's outputs without re-executing
its tasks. New orchestrator plans require the manifest. For a legacy plan that
never carried one, use its README dependency table and durable outputs only when
they establish the same readiness facts; log the limitation, and block if they
cannot establish them. Never silently migrate a legacy plan.

Distributed parent completion means plans created and ready, not feature
implementation complete. Sequential / Output Handoff completion requires all
children executed, outputs registered, and the parent's own applicable Final
Review (or legacy ending) passed. The parent reviews the aggregate cross-repo
contracts and evidence; child source reviews and validation remain per repo.
Optional Dailybot reporting still requires authorization and never blocks work.
