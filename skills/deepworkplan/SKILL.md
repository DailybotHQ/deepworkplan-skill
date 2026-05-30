---
name: deepworkplan
description: DeepWorkPlan — turn any repo AI-first and run Deep Work Plans. Routes to create, execute, refine, resume, status, and repo-onboarding sub-skills based on intent. Use when the developer wants to plan, execute, or manage structured multi-task work, or make a repository AI-agent-ready.
version: "2.0.1"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"🧠","homepage":"https://deepworkplan.com","requires":{"anyBins":["git","bash"]}}}
---

# DeepWorkPlan — Methodology Skill (Router)

The **DeepWorkPlan** skill turns any repository "AI-first" — `AGENTS.md` +
`docs/` + per-module docs + `.agents/` (with the `.claude → .agents` symlink) —
and runs structured **Deep Work Plans**: multi-task plans an AI agent drafts,
refines, executes task-by-task, and resumes. All plan and draft outputs land in
a gitignored `.dwp/` directory at the repo root (`.dwp/plans/`, `.dwp/drafts/`).

Source of truth: <https://deepworkplan.com>. License: MIT.

## What it does

This is the **router**. It does not run any flow itself — it maps the
developer's intent to the right sub-skill and tells the agent to read that
sub-skill's `SKILL.md` and execute it there.

---

## For the agent — routing rules

When the developer wants to plan, execute, or manage structured work, or make a
repo AI-agent-ready, match the intent below and **read that sub-skill's
`SKILL.md` to execute it**. Do not answer directly — each sub-skill carries the
full step-by-step flow.

| Developer says… | Route to |
|------------------|----------|
| "create a plan", "new deep work plan", "/dwp-create" | **Create** → read [`create/SKILL.md`](create/SKILL.md) |
| "execute the plan", "run the plan", "/dwp-execute" | **Execute** → read [`execute/SKILL.md`](execute/SKILL.md) |
| "refine the draft", "modify the plan", "/dwp-refine" | **Refine** → read [`refine/SKILL.md`](refine/SKILL.md) |
| "resume", "continue the interrupted plan", "/dwp-resume" | **Resume** → read [`resume/SKILL.md`](resume/SKILL.md) |
| "plan status", "what's left", "/dwp-status" | **Status** → read [`status/SKILL.md`](status/SKILL.md) |
| "make this repo AI-first", "onboard this repo", "set up AGENTS.md + docs + .agents" | **Onboard** → read [`onboard/SKILL.md`](onboard/SKILL.md) |

If the intent is ambiguous between planning and managing existing work, ask the
developer which they mean before routing.

### Normative specification (ships with the skill)

The methodology's authoritative standard lives at [`spec/`](spec/README.md) —
five RFC-2119 documents (`DOCUMENTATION_STANDARD`, `DWP_SPECIFICATION`,
`AGENT_PROTOCOL`, `ARCHETYPES`, `ADDONS`). It ships inside the skill so an agent
reads the standard **locally** — no network needed. The `onboard` flow and
`shared/adaptation.md` reference it as the standard to produce. The public,
rendered version lives at https://deepworkplan.com/spec.

### Shared resources used by every sub-skill

- [`shared/context.sh`](shared/context.sh) — detect repo root, branch, and agent
  tool; resolve the `.dwp/` output location.
- [`shared/dwp-paths.md`](shared/dwp-paths.md) — the `.dwp/plans/` +
  `.dwp/drafts/` output convention and how to override it.
- [`shared/adaptation.md`](shared/adaptation.md) — the reasoning-over-copy-paste
  principle and the two repository archetypes (individual repo vs orchestrator
  hub).

### Opt-in addons

The [`addons/`](addons/README.md) area holds **opt-in** capabilities the
`onboard` flow can layer onto a repo. Addons are never part of the AI-first
baseline — a repo is fully conformant with zero addons. The first addon is
devcontainer support.
