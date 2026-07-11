# DeepWorkPlan Methodology Specification — v2.2.0

> The canonical normative standard for an **AI-first autopilot repository** and the
> **Deep Work Plan (DWP)** workflow. Version **2.2.0**. This v2 spec **supersedes**
> the v1 baseline specs in `PLAN_build_deepworkplan_brand/.../deepworkplan/spec/`
> (and the upstream `repo-ready/` and `opensource` drafts). Reconciled from that
> baseline plus the 6 (+1) new ideas per `../RECONCILIATION.md`.

All documents use RFC-2119 normative language (MUST / SHOULD / MAY / MUST NOT) and
are grounded in an audit of 6 Dailybot repositories (~90% common structure, ~10%
reason-per-repo). All three archetypes — individual repo (the default case),
orchestrator hub, and agent workspace — are addressed throughout.

## Documents

| Document | Defines |
|----------|---------|
| [`DOCUMENTATION_STANDARD.md`](DOCUMENTATION_STANDARD.md) | Repo structure: `AGENTS.md` (index + mandatory rules + quick commands), `CLAUDE.md → AGENTS.md`, the 10 `docs/` categories, per-module nested docs, `.agents/` layout, `.claude → .agents` and `.cursor → .agents` symlinks, and the reason-per-repo 10%. |
| [`DWP_SPECIFICATION.md`](DWP_SPECIFICATION.md) | The DWP workflow: single-step refined-draft create flow, `.dwp/` output, the 9-section task anatomy (+ optional Delta section), validation/completion, the DWP Resume Protocol, proportional rigor tiers, the three mandatory final tasks, orchestrator + team-agents support. |
| [`AGENT_PROTOCOL.md`](AGENT_PROTOCOL.md) | Cross-agent behavior: the supported agents (interactive + autonomous platforms), the `/` vs `#` command mapping, shared `.agents/` reading, progress reporting, and the interactive vs **unattended** execution profiles. |
| [`ARCHETYPES.md`](ARCHETYPES.md) | The three archetypes (individual repo, orchestrator hub, agent workspace), the classification heuristic, and how onboarding differs. |
| [`PLAN_STATE.md`](PLAN_STATE.md) | The machine-readable plan state layer: `manifest.json` + `state.json`, gate records, outcome records, checkpoint/blocked state, reconciliation rules, and the published [JSON Schemas](schema/). |
| [`ADDONS.md`](ADDONS.md) | The opt-in addon mechanism + contract (reconcile-don't-clobber); devcontainer as the first addon (pointer to Task 6). |

## Key v2 Divergences from v1 (see `../RECONCILIATION.md`)

1. Distribution: WebFetch framework repo → **installed skill pack** (idea #2).
2. Output path: `.agent_commands/.../results/` → gitignored **`.dwp/`** (idea #3).
3. Create flow: two-step draft → **single refined draft** (idea #4).
4. **`.claude → .agents`** and **`.cursor → .agents`** directory symlinks + canonical `.agents/` (idea #1).
5. **Two archetypes** made first-class (idea #5).
6. **Per-module `README.md` + `docs/`** formalized as normative (idea #6).
7. **Opt-in addons** mechanism, devcontainer first (idea #7).
8. Version **1.0.0 → 2.0.0** (major, breaking).

## Minor revisions in 2.2.0 (additive, no breaking changes)

- **Machine-readable plan state layer** (`PLAN_STATE.md`, net-new):
  `manifest.json` + `state.json` as a derived projection of the plan markdown,
  with published JSON Schemas (`schema/`), per-task validation-gate records
  (`passes` flags), outcome records (episodic memory), checkpoint and blocked
  state, and markdown-wins reconciliation. RECOMMENDED for new plans; REQUIRED
  for unattended execution and for workspaces without git.
- **Proportional rigor tiers** (`DWP_SPECIFICATION.md` §11): micro / standard /
  deep. A plan folder MUST NOT be created for a trivial single-file change; the
  tier changes the packaging, never the gates.
- **Delta section** (`DWP_SPECIFICATION.md` §5.0.1): optional
  ADDED / MODIFIED / REMOVED behavior contract for brownfield tasks.
- **The DWP Resume Protocol** (`DWP_SPECIFICATION.md` §5.3): the resume ritual
  promoted to a named, citable six-step protocol (re-anchor → checkpoint →
  reconcile → inspect the seam → smoke-test → continue atomically).
- **Agent workspace archetype** (`ARCHETYPES.md` §4): the long-lived home of an
  autonomous agent (OpenClaw, Hermes, cloud agents) as a third archetype; git
  RECOMMENDED rather than assumed, with `state.json` carrying recovery state.
- **Execution profiles** (`AGENT_PROTOCOL.md` §7): interactive vs unattended —
  pre-approved plans, bounded authority, stop conditions, scheduled
  continuation. OpenClaw and Hermes join the supported-agents table.
- **Automated conformance** (`verify/conformance.sh`): the verify sub-skill
  gains a mechanical, CI-friendly checker (exit 0/1) covering repo structure,
  plan well-formedness, and state-layer desync.

## Minor revisions in 2.1.0

- **Test & validation discipline made first-class** (minor, additive): tasks that
  add or change product behavior MUST carry automated test coverage in their
  acceptance criteria and run the repo's tests + lint/type-check in their
  validation gate (`DWP_SPECIFICATION.md` §5.1.1); onboarding MUST define a real
  or proposed test/lint toolchain so every future plan has an objective gate
  (`DOCUMENTATION_STANDARD.md` §3.3).

---

*DeepWorkPlan methodology v2.2.0, MIT License, by [Dailybot](https://dailybot.com) / dailybotops.*
