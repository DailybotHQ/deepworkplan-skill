---
name: deepworkplan
description: DeepWorkPlan — turn any repo AI-first and run Deep Work Plans. Routes to create, execute, refine, resume, status, verify, upgrade, and repo-onboarding sub-skills based on intent. Use when the developer wants to plan, execute, manage, or verify structured multi-task work, or make a repository AI-agent-ready.
version: "5.5.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"🧠","homepage":"https://deepworkplan.com","requires":{"anyBins":["git","bash"]}}}
---

# DeepWorkPlan — Methodology Skill (Router)

Models matter; context matters more. The **DeepWorkPlan** skill turns any
repository into a structured environment — context, guardrails, and a durable
plan — where any coding agent executes reliably on short or long work. It makes
the repository "AI-first" — `AGENTS.md` + `docs/` + per-module docs + `.agents/`
(with the `.claude → .agents` and `.cursor → .agents` symlinks) — and runs structured **Deep Work
Plans**: Lite plans for bounded work and Full task-file plans for longer work;
an AI agent creates, refines, executes task-by-task,
and resumes. All plan output lands in a gitignored `.dwp/` directory
at the repo root (`.dwp/plans/`).

Source of truth: <https://deepworkplan.com>. License: MIT.

## Start here (first run)

This skill is a self-sufficient entry point: whether a developer arrives from
<https://deepworkplan.com/init.md> or simply installs this skill, the setup plan
is the same — and it lives here, so no network is required.

**If the repository is not yet AI-first** — there is no root `AGENTS.md` and no
`.agents/` directory — the recommended first action is to **onboard it**, even if
the developer's request was vague ("set this up", "make this repo AI-first", or a
plain install). Before routing anywhere else:

1. **Read the standard locally.** Read [`spec/`](spec/README.md) (five RFC-2119
   documents) and [`shared/adaptation.md`](shared/adaptation.md). The overriding
   rule is **REASON, do not copy-paste**: this skill is the reusable engine; what
   you produce must be adapted to *this* repository, never templated.
2. **Run onboarding.** Read [`onboard/SKILL.md`](onboard/SKILL.md) and execute it.
   It is **non-destructive**: detect existing `AGENTS.md`, `docs/`, `.agents/`, or
   `CLAUDE.md`, reconcile rather than overwrite, and ask the developer before
   replacing anything. The result: `AGENTS.md` + `CLAUDE.md` symlink, a reasoned
   `docs/` tree, per-module docs, a `.agents/` kit, and a gitignored `.dwp/` — the
   repository becomes the agent harness.
3. **Verify conformance.** Read [`verify/SKILL.md`](verify/SKILL.md) and run it to
   confirm, objectively, that the repository now meets the standard (AGENTS.md with
   real commands, the `.agents/` catalog, the gitignored `.dwp/`, and so on).
4. **Then plan and execute.** With the harness in place, create and execute Deep
   Work Plans (below) — long-horizon, gated, resumable work an agent can run
   autonomously for hours.

**If the repository is already AI-first but its harness predates this skill** —
`AGENTS.md` / `.agents/` exist, yet there is no `DWP standard:` provenance line,
the provenance line is from a non-current series (older than the 5.x this skill
implements — 2.x and 4.x are historical series, `spec/DWP_SPECIFICATION.md`
§6.5), or
`docs/TESTING_GUIDE.md` lacks the scoped-invocation and mapping content the
standard requires, or its agent rules lack the working principles described
in `spec/DOCUMENTATION_STANDARD.md` §2.3.1 (equivalent wording counts) —
**offer the targeted harness upgrade** before routing.
Say in one line what is out of date, then run
[`onboard/SKILL.md`](onboard/SKILL.md) in `upgrade` mode (Phase 0), which
reconciles **only** the missing or outdated pieces, leaves every handwritten
section, custom skill and in-flight plan untouched, and changes nothing on a
second run. When the developer instead wants the **skill itself** current
(newer published version, or a fresh init pass end-to-end), route to
[`upgrade/SKILL.md`](upgrade/SKILL.md): it checks the latest published tag,
downloads only on explicit acceptance, and re-runs onboarding as a fresh init —
`.dwp/` plans are never migrated. An in-flight plan keeps its recorded
lifecycle; migrating one is a separate, explicit `refine migrate`. If the
developer declines, route by intent as normal.

> **Unattended runs record the gap; they never stop to offer.** Under
> `trust`/`auto` or a pre-approved plan, that offer is the confirmation
> authorization already removed. So do **not** ask: **write it down where the
> work will see it** (a plan flow's README notes and `PROGRESS.md`; otherwise
> the flow's own report) and route by intent. A stale harness is a recorded
> finding like any missing optional tool (`spec/AGENT_PROTOCOL.md` §7.2) —
> never a question, and never a silent omission either.

> **A partially AI-first repository takes this same branch.** The branches
> above are the clean cases; real repositories land in between (an `AGENTS.md`
> with no `.agents/`, an `.agents/` with no provenance line, docs without a
> testing guide). Any repository with **some** of the harness and not the rest
> counts as out-of-date harness, not as a fresh one: reconcile through
> `onboard` in `upgrade` mode, which adds only what is absent. Never re-onboard
> from scratch over a repository that already carries part of the harness —
> that is the one path that can overwrite handwritten work.

**If the repository is already AI-first and current**, skip onboarding and route
by intent **silently** — do not announce the detection or the routing decision
(no "the repo is already AI-first" / "routing to the create sub-skill"
preamble). Just begin the matched sub-skill's flow directly.

## What it does

This is the **router**. It does not run any flow itself — it maps the
developer's intent to the right sub-skill and tells the agent to read that
sub-skill's `SKILL.md` and execute it there.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash` because the
sub-skills this router delegates to need them; the router itself only **reads**
(the repo tree, the local `spec/`, `shared/`, and sub-skill files). Writes happen
inside the delegated sub-skill, each of which declares its own trust boundary:

- **Onboard** writes `AGENTS.md`, `docs/`, per-module docs, `.agents/`, and
  appends to `.gitignore` — reconciling with, never clobbering, what exists,
  and asking before replacing anything.
- **Create / refine** write plan artifacts under the gitignored `.dwp/`
  directory only.
- **Execute / resume** write task outputs, progress, and per-task commits —
  gated by each task's validation, never committing secrets, never pushing
  without the developer's instruction.
- **Addons** install or configure anything only after the developer explicitly
  accepts the offer, always via pinned, verified install paths.

It MUST NOT: make network calls in the core flow, read or commit credentials,
run installers unprompted, or write anywhere outside the surfaces above. The
full guarantees and a runnable self-audit live in
[`TRUST.md`](TRUST.md).

---

## For the agent — routing rules

When the developer wants to plan, execute, or manage structured work, or make a
repo AI-agent-ready, match the intent below and **read that sub-skill's
`SKILL.md` to execute it**. Do not answer directly — each sub-skill carries the
full step-by-step flow.

| Developer says… | Route to |
|------------------|----------|
| "create a plan", "plan this small fix", "organize this work", "new deep work plan", "/dwp-create" | **Create** → read [`create/SKILL.md`](create/SKILL.md) |
| "execute the plan", "run the plan", "/dwp-execute" | **Execute** → read [`execute/SKILL.md`](execute/SKILL.md) |
| "modify the plan", "change the scope", "/dwp-refine" | **Refine** → read [`refine/SKILL.md`](refine/SKILL.md) |
| "resume", "continue the interrupted plan", "/dwp-resume" | **Resume** → read [`resume/SKILL.md`](resume/SKILL.md) |
| "plan status", "what's left", "/dwp-status" | **Status** → read [`status/SKILL.md`](status/SKILL.md) |
| "verify", "is this repo AI-first?", "check conformance", "/dwp-verify" | **Verify** → read [`verify/SKILL.md`](verify/SKILL.md) |
| "make this repo AI-first", "onboard this repo", "set up AGENTS.md + docs + .agents" | **Onboard** → read [`onboard/SKILL.md`](onboard/SKILL.md) |
| "upgrade DWP", "update the skill", "is there a newer version?", "/dwp-upgrade" | **Upgrade** → read [`upgrade/SKILL.md`](upgrade/SKILL.md) |
| "create/update a skill or agent", "evolve the kit", "/skill-create", "/agent-create" | **Author** → read [`author/SKILL.md`](author/SKILL.md) |

If the intent is ambiguous between planning and managing existing work, ask the
developer which they mean before routing.

**Activation rules that hold for every row of the table:**

- **Ordinary direct edits never become plans silently.** "Fix this bug",
  "rename this function", "update the README" are done directly — a Deep Work
  Plan starts only when the developer asks for a plan (or picks a flow
  explicitly). The routing table maps *requested* flows; it is not an
  interception policy.
- **Trust is not a flow selector.** `trust` / `auto` authorizes unattended
  continuation *within* the flow the developer requested; it never widens a
  read-only request into execution, and it never turns a direct edit into a
  plan.
- **Status and verify stay read-only.** They report; they never execute tasks
  or mutate files — regardless of how they are invoked.
- **Hosts without slash commands use the same flows by name.** Invoke the
  sub-skill as `#deepworkplan-create` or in plain text ("run
  deepworkplan-create"); the flows themselves are plain file reads, edits and
  shell commands (`shared/troubleshooting.md` §5 states the capability
  fallbacks). Flow discovery is local: the pack and the repo's `.agents/`
  index live on disk — nothing routes through a network service.

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
- [`shared/dwp-paths.md`](shared/dwp-paths.md) — the `.dwp/` output
  convention (plans under `.dwp/plans/`) and how to override it.
- [`shared/adaptation.md`](shared/adaptation.md) — the reasoning-over-copy-paste
  principle and the two repository archetypes (individual repo vs orchestrator
  hub).
- [`shared/troubleshooting.md`](shared/troubleshooting.md) — read **only when
  something is already wrong**: discovery failure, stale installation, missing
  test command, unsupported host capability, inconsistent state.

### Addons — one required local review, four opt-in

The [`addons/`](addons/README.md) area holds the capabilities the `onboard`
flow layers onto a repo. The **AI Diff Reviewer local review** is part of the
baseline since standard 2.3.0 (installed by `onboard` Phase 7a, run by every
Final Review; its CI surface stays optional). The other four addons are
**opt-in** and never part of the AI-first baseline — a repo is fully conformant
with zero optional addons. The first optional addon is devcontainer support.
