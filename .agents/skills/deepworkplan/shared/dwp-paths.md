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

## Contrast with the legacy path

`.dwp/` **replaces** the legacy DWP output tree:

| Concept | Legacy path | New path |
|---------|-------------|----------|
| Plans | `.agent_commands/agent_deep_work_plans/results/plans/PLAN_{name}/` | `.dwp/plans/PLAN_{name}/` |

The legacy `.agent_commands/agent_deep_work_plans/results/` tree **MUST NOT** be
used by repos onboarded to DeepWorkPlan v2; migration moves any existing plans
into `.dwp/`.
