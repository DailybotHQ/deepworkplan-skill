# dwp-paths.md — The `.dwp/` Output Convention

> Source of truth for **where Deep Work Plan outputs live**. Every DeepWorkPlan
> sub-skill reads this to resolve plan paths.

## The convention

All plans live under a single gitignored repo-root directory, `.dwp/`:

```
.dwp/
└── plans/      ← PLAN_{name}/ directories (the plans)
```

- A plan lives at `.dwp/plans/PLAN_{name}/`, Lite or Full alike.
- `create` writes the plan folder directly. There is no separate draft artifact
  and no `.dwp/drafts/` directory: the Lite plan **is** the reviewable artifact
  (`../spec/LITE_PLANS.md`). Both were removed in 2.4.0. A `.dwp/drafts/` folder
  left over from an earlier version is inert — DWP neither reads nor writes it.
- Every artifact a plan produces — analysis outputs, gate logs, generated
  reports — lives inside **that plan's own folder**, under
  `.dwp/plans/PLAN_{name}/analysis_results/`. Temporary or analysis results
  **MUST NOT** be written to the repository root or to ad-hoc folders elsewhere
  in the repo: the plan folder is the single home for a plan's working
  artifacts, so a plan can be inspected, archived, or deleted as one unit.

## Default location & override

- **Default:** `<repo-root>/.dwp/`, where `<repo-root>` is the git toplevel (or
  the current directory outside a git work tree). `shared/context.sh` resolves
  this and emits it as the `dwp_dir` field.
- **Override:** set the `DWP_DIR` environment variable to an absolute path to
  relocate the output directory (e.g. for monorepos that keep outputs elsewhere,
  or CI sandboxes). `context.sh` honors `DWP_DIR` when present.

## `.dwp/` is gitignored

`.dwp/` **MUST** be added to the repository's `.gitignore`. Plans are
working artifacts, not tracked source. (Orchestrator hubs follow the same rule:
child plans live at `repositories/{repo}/.dwp/plans/PLAN_{child}/`, also
gitignored.)

## Workspace persistence and transfer

Because `.dwp/` is gitignored, **a fresh `git clone` carries no plan data**.
That is by design — plans are working state, not source — and it has one
consequence a resuming agent MUST state plainly: a checkout without `.dwp/`
has nothing to resume, and progress is never fabricated from commits alone.

**Same workspace.** The plan folder on disk is the whole recovery surface;
`resume/SKILL.md` Step 2 (assess, reconcile, classify the interruption
boundary) needs nothing else.

**Transfer to a new machine (explicit, manual).** The minimum handoff
manifest — everything a resumed session needs, nothing it can reconstruct:

1. **The complete plan folder** `.dwp/plans/PLAN_{name}/`: README, task
   files, `PROGRESS.md`, `manifest.json`, `state.json`, and
   `analysis_results/` **including every gate log cited by a `log=` evidence
   pointer** (a dangling pointer is a conformance finding, not reusable
   evidence).
2. **Repository revision(s)** the state cites — `git rev-parse HEAD` per
   repository, checked out on arrival.
3. **Required dirty work**: any uncommitted changes the checkpoint names,
   re-created or carried over (patch, stash bundle, or copy).
4. **Evidence pointers** to external-action receipts (report ids, PR URLs)
   recorded in the task logs — the receipts themselves live in their
   services and are investigated there when absent.

On arrival: restore the folder at the same relative path, check out the
recorded revision, re-create the dirty work, then run the read-only checker
(`verify/plan_contract.py`) before resuming. **Missing-artifact behavior:**
report what is missing and stop at that boundary — never reconstruct history
from memory or guess at absent evidence.

**No infrastructure.** There is no daemon, no auto-upload, and no automatic
unignoring of `.dwp/`, and none may be implied: preservation is a deliberate
copy (archive the plan folder, or move it with the workspace) performed by a
human or an agent acting on explicit instruction.

## Contrast with the legacy path

`.dwp/` **replaces** the legacy DWP output tree:

| Concept | Legacy path | New path |
|---------|-------------|----------|
| Plans | `.agent_commands/agent_deep_work_plans/results/plans/PLAN_{name}/` | `.dwp/plans/PLAN_{name}/` |

The legacy `.agent_commands/agent_deep_work_plans/results/` tree **MUST NOT** be
used by repos onboarded to DeepWorkPlan v2; migration moves any existing plans
into `.dwp/`.
