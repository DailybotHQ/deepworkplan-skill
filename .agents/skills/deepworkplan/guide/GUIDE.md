# DeepWorkPlan — Methodology Guide (GUIDE.md)

### How to Create Deep-Work Task Execution Plans (outputs under `.dwp/`)

The repository is the harness: versioned files travel with the code. **Spec-first, loop-closed: the repository is the harness and the plan runs itself to done.** Spec-first is one work episode: the plan is written before code with acceptance criteria. It lives as exportable, git-ignored `.dwp/plans/` working state, resumable by any agent in the repository, not as a maintained specification.
**Loop engineering** registers a lead and succession; a human starts the optional daemon, whose prompts add no authority. It supports takeover, granted appointment, `plan-event-v1`, `fleet-v1`, and prompt-lead queue starts. The plan runs within its recorded authority and gates. DWP measures the instruction bytes each flow loads; it has not shown a general saving in provider tokens. The method works alone.

---

> **Addressing a section: by its number, not by a heading level.** "Read
> §6.1" means the section numbered 6.1 at whatever level the file uses
> (`## 6.1.` sits beside `## 6.`). Extracting `### 6.1` would match nothing,
> exit **zero**, and read **empty** — a silent no-read. If a section
> extraction comes back empty, that is a defect to report, never a blank
> section.

This file is the routing index; each flow loads only what it needs
(`spec/DWP_SPECIFICATION.md` §5).
Do not read every guide file up front; load only what your current flow needs.

## How to read this guide (by flow)

| Your flow | Read (essential) | Read only when triggered |
|-----------|------------------|--------------------------|
| **Create** a plan | [`authoring.md`](./authoring.md) (README + task-file templates, test & security discipline), [`structure.md`](./structure.md) (folders, naming, lifecycle) | [`orchestrator.md`](./orchestrator.md) if the plan spans sub-repositories; [`team-agents.md`](./team-agents.md) if parallel groups were detected; [`prompts.md`](./prompts.md) when writing `PROMPTS.md`; [`skills-integration.md`](./skills-integration.md) when referencing skills/agents in tasks; the flow file `../create/v6.md` + `../spec/V6_CONTRACT.md` when creating a new plan |
| **Execute** / **resume** a plan | [`execution.md`](./execution.md) (agent rules, per-task commits, completion tracking, final review) | [`orchestrator.md`](./orchestrator.md) for orchestrator plans; [`team-agents.md`](./team-agents.md) for parallel groups; [`orchestration-at-scale.md`](./orchestration-at-scale.md) for a lead running agents in panes across accounts; [`swarm.md`](./swarm.md) for capacity checks, handoff packets and lead succession; [`prompts.md`](./prompts.md) §9 for resume scenarios; the flow file `../execute/v6.md` when the plan folder is v6 by its artifacts (`../spec/V6_LIFECYCLE.md` is normative); a v6 resume loads `../resume/v6.md`; v5 → v6 migration is refine 3.2a (`../shared/migrate_v6.py`) |
| **Refine** a plan | [`authoring.md`](./authoring.md), [`structure.md`](./structure.md) | as for Create |
| **Onboard** a repository | [`structure.md`](./structure.md) | [`large-repo-onboarding.md`](./large-repo-onboarding.md) when the repository is large enough to be its own plan; `../onboard/v6.md` (bounded-autonomy records) for v6 plans — `../spec/V6_LIFECYCLE.md` §10 is normative |
| **Verify** / **status** | [`structure.md`](./structure.md) §1–§2 | — |
| **Upgrade** the installed skill | [`structure.md`](./structure.md) §1–§2 (what lives where) | the `upgrade` sub-skill itself (`../upgrade/SKILL.md`) — check is read-only, download needs explicit acceptance, `.dwp/` is never migrated |
| **Author** skills/agents | [`skills-integration.md`](./skills-integration.md) | — |

## Section map (every section of the original guide, in original order)

| Section | Now in |
|---------|--------|
| ## 1. Top-Level Folder Structure | [`structure.md`](./structure.md) |
| ## 2. Naming Conventions | [`structure.md`](./structure.md) |
| ## 3. Purpose of This System | [`structure.md`](./structure.md) |
| ## 4. Plan-Level README Structure (`{PLAN_NAME}/README.md`) | [`authoring.md`](./authoring.md) |
| ## 5. Task File Structure (`N.task_{task_title}.md`) | [`authoring.md`](./authoring.md) |
| ## 6. Agent Execution Rules (Critical Behavior) | [`execution.md`](./execution.md) |
| ## 6.1. Mandatory Final Tasks → now **6.1. Final Review, Task-Local Skills and the Optional Report** (spec 2.3.0 lifecycle) | [`execution.md`](./execution.md) |
| ## 6.1. Final Review, Task-Local Skills and the Optional Report | [`execution.md`](./execution.md) |
| ## 🔄 Multi-Project Commit Workflow | [`execution.md`](./execution.md) |
| ## ⚠️ CRITICAL: Task Completion Tracking (MANDATORY) | [`execution.md`](./execution.md) |
| ## 7. How to Instruct an Agent to Generate a New Plan | [`prompts.md`](./prompts.md) |
| ## 8. How to Instruct an Agent to Execute a Plan | [`prompts.md`](./prompts.md) |
| ## 9. How to Resume an Interrupted Plan (CRITICAL) | [`prompts.md`](./prompts.md) |
| ## 10. Cleanup and Lifecycle | [`structure.md`](./structure.md) |
| ## 11. Skills & Agents Integration (MANDATORY) | [`skills-integration.md`](./skills-integration.md) |
| ## 13. Orchestrator Plans (Core Hub Only) | [`orchestrator.md`](./orchestrator.md) |
| ## 14. Team Agents Execution Mode (Claude Code Only) | [`team-agents.md`](./team-agents.md) |
| ## 15. Onboarding a Large Repo as Its Own Deep Work Plan | [`large-repo-onboarding.md`](./large-repo-onboarding.md) |
| ## 16. Orchestration at Scale | [`orchestration-at-scale.md`](./orchestration-at-scale.md) |
| ## 17. Swarm Autonomy | [`swarm.md`](./swarm.md) |
| ## 12. Summary | this file (below) |

Section numbers and headings are preserved inside each file, so a reference such
as "GUIDE §5.3" still means "section 5.3" — now found in [`authoring.md`](./authoring.md).
A reference of the form `guide/GUIDE.md §N` from an earlier version resolves
through this table.

---

## 12. Summary

This guide defines how an agent should:

- Create plans under `.dwp/plans/{PLAN_NAME}/`; `plan_paths.py` allocates
  numbered names. Existing unnumbered plans keep their names.
- Split work into ordered, single-focus task files
- Execute tasks sequentially, with strong validation and logging
- Resume interrupted plans without duplicating work
- Keep everything temporary and isolated from the main repository
- Leverage existing skills and agents for higher-quality, more consistent plans (see section 11)
- Onboard a large repo as its own Deep Work Plan — documenting docs/, per-module docs, and the `.agents/` kit task-by-task with gates and resumability (see section 15)
- Create orchestrator plans that generate child DWP plans in sub-repositories for complex multi-repo features (see section 13)
- Propagate global context to child DWPs via the Orchestrator Context Manifest (see section 13.8)
- Pass outputs between child DWPs using the inter-child output passing protocol (see section 13.9)
- **Hand off** child DWPs for execution by separate agent sessions inside each target repo (orchestrator agents never execute children inline — see §13.0) with dependency-aware execution modes and readiness gates (see section 13.10)
- Optionally enable parallel task execution via team agents as a progressive enhancement for Claude Code (see section 14)
- Run many agents at once — lanes in panes, on chosen accounts and vendors (see section 16)
- Keep a swarm running past one account's limit — capacity checks, handoff packets, lead succession (see section 17)
- Generate task files in parallel via team agents (see section 14.8)

Use this as the **authoritative specification** whenever an agent is asked to:

- Generate a new plan
- Prepare detailed per-task prompts
- Run long, focused, multi-task deep-work sessions
- Resume interrupted execution safely and efficiently
- Create orchestrator plans that coordinate child DWPs across repositories
- Hand off child DWPs for execution with dependency checking and predecessor output handoff (orchestrator never runs children inline — §13.0)
- Create team-agent-aware plans with parallel task groups (Claude Code only)
