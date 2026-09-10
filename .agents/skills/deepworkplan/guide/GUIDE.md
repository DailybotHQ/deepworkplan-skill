# DeepWorkPlan — Methodology Guide (GUIDE.md)

### How to Create Deep-Work Task Execution Plans (outputs under `.dwp/`)

This guide defines the **official structure and workflow** for creating _agent deep work plans_.

These plans are designed so that an AI agent (Cursor, Claude, etc.) can:

- Work for **many hours** (including overnight)
- Focus on **one task at a time**
- Follow a **clear, ordered execution plan**
- Keep everything **modular, auditable and disposable**

Use this document whenever you need to generate a new deep-work plan.

---

This file is the **routing index** of the methodology guide. The guide's content
is unchanged; it is split into flow-scoped files so an agent loads only what its
current flow needs (`spec/DWP_SPECIFICATION.md` §5). The design rationale is
maintained in the contributor-only repository ADR, not shipped in the pack.
Nothing here is compressed — every section that existed in
the single-file guide exists verbatim in exactly one file below.

## How to read this guide (by flow)

| Your flow | Read (essential) | Read only when triggered |
|-----------|------------------|--------------------------|
| **Create** a plan | [`authoring.md`](./authoring.md) (README + task-file templates, test & security discipline), [`structure.md`](./structure.md) (folders, naming, lifecycle) | [`orchestrator.md`](./orchestrator.md) if the plan spans sub-repositories; [`team-agents.md`](./team-agents.md) if parallel groups were detected; [`prompts.md`](./prompts.md) when writing `PROMPTS.md`; [`skills-integration.md`](./skills-integration.md) when referencing skills/agents in tasks |
| **Execute** / **resume** a plan | [`execution.md`](./execution.md) (agent rules, per-task commits, completion tracking, final review) | [`orchestrator.md`](./orchestrator.md) for orchestrator plans; [`team-agents.md`](./team-agents.md) for parallel groups; [`prompts.md`](./prompts.md) §9 for resume scenarios |
| **Refine** a plan | [`authoring.md`](./authoring.md), [`structure.md`](./structure.md) | as for Create |
| **Onboard** a repository | [`structure.md`](./structure.md) | [`large-repo-onboarding.md`](./large-repo-onboarding.md) when the repository is large enough to onboard as its own plan |
| **Verify** / **status** | [`structure.md`](./structure.md) §1–§2 | — |
| **Author** skills/agents | [`skills-integration.md`](./skills-integration.md) | — |

Do not read every file by default. Each sub-skill's "Shared resources" section
names its essential files and its conditional triggers.

## Section map (every section of the original guide, in original order)

| Section | Now in |
|---------|--------|
| ## 1. Top-Level Folder Structure | [`structure.md`](./structure.md) |
| ## 2. Naming Conventions | [`structure.md`](./structure.md) |
| ## 3. Purpose of This System | [`structure.md`](./structure.md) |
| ## 4. Plan-Level README Structure (`PLAN_{plan_title}/README.md`) | [`authoring.md`](./authoring.md) |
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
| ## 12. Summary | this file (below) |

Section numbers and headings are preserved inside each file, so a reference such
as "GUIDE §5.3" still means "section 5.3" — now found in [`authoring.md`](./authoring.md).
A reference of the form `guide/GUIDE.md §N` from an earlier version resolves
through this table.

---

## 12. Summary

This guide defines how an agent should:

- Create deep-work plans under `.dwp/plans/PLAN_{plan_title}/`
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
- Accelerate plan creation itself by generating task files in parallel via team agents (see section 14.8)

Use this as the **authoritative specification** whenever an agent is asked to:

- Generate a new plan
- Prepare detailed per-task prompts
- Run long, focused, multi-task deep-work sessions
- Resume interrupted execution safely and efficiently
- Create orchestrator plans that coordinate child DWPs across repositories
- Hand off child DWPs for execution with dependency checking and predecessor output handoff (orchestrator never runs children inline — §13.0)
- Create team-agent-aware plans with parallel task groups (Claude Code only)
