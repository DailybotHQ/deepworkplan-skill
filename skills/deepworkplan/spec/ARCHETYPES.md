# ARCHETYPES.md — Repository Archetypes

## Abstract

This document defines the **three archetypes** the DeepWorkPlan methodology
recognizes — the **individual repo** (the default case), the **orchestrator
hub**, and the **agent workspace** — the heuristic an onboarding agent uses to
classify a target, and how onboarding differs between them. Every other spec
(`DOCUMENTATION_STANDARD.md`, `DWP_SPECIFICATION.md`, `AGENT_PROTOCOL.md`,
`ADDONS.md`, `PLAN_STATE.md`) forks its requirements on the archetype determined
here.

---

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 2.2.0 |
| **Status** | Stable |
| **Supersedes** | (net-new in v2; no v1 equivalent) |
| **Companions** | `DOCUMENTATION_STANDARD.md`, `DWP_SPECIFICATION.md`, `AGENT_PROTOCOL.md`, `ADDONS.md`, `PLAN_STATE.md` |
| **License** | MIT |

> **Additive in 2.2.0.** The **agent workspace** (§4) joins as a third archetype:
> the long-lived home of an autonomous agent (an OpenClaw workspace, a Hermes
> service directory, a scheduled cloud agent's persistent volume). The harness
> elements are the same as a repo's; git becomes RECOMMENDED rather than assumed.
> The two 2.1.0 archetypes are unchanged.

> **Divergence from v1.** v1 defined a **single** conformance model; it mentioned
> monorepos in passing and buried orchestrator behavior inside the DWP spec's §10.
> v2 promotes the two archetypes to a **first-class axis** that every spec forks on
> (`RECONCILIATION.md` divergence #5, idea #5).

---

## 1. Conventions

The RFC 2119 keywords (**MUST**, **MUST NOT**, **SHOULD**, **MAY**, etc.) are
interpreted as in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 2. The Individual Repo (99% case)

- An **individual repo** is a single codebase with one primary stack, its own
  validation commands, and per-module documentation. It is the **default**
  archetype.
- An onboarding agent **MUST** assume the individual archetype **unless** the repo
  is clearly an orchestrator hub (§4).
- An individual repo **MUST** satisfy `DOCUMENTATION_STANDARD.md` §§2–7: `AGENTS.md`
  (index + mandatory rules + quick commands), the `docs/` categories, per-module
  nested docs, `.agents/`, and the `.claude → .agents` symlink.
- Its DWP usage **MUST** stay within the single repository; orchestrator capability
  (`DWP_SPECIFICATION.md` §8) is typically unused.
- Live examples: all five Dailybot product repos — `api-services`, `web-app`,
  `chatbot-functions`, `discord-gateway`, `dailybot.com`
  (`ORCHESTRATOR_MANIFEST.md` registry: "All 5 repos are the individual archetype").

---

## 3. The Orchestrator Hub

- An **orchestrator hub** is a documentation/coordination repository that
  orchestrates work across multiple sub-repositories.
- A hub **MUST** additionally provide, beyond the §§2–7 baseline:
  - a **sub-project navigation index** (e.g. `repositories/README.md`) linked from
    the root `AGENTS.md` (`DOCUMENTATION_STANDARD.md` §2.2);
  - **`ECOSYSTEM_CONTEXT.md`** and a **cross-project standards** guide
    (`DOCUMENTATION_STANDARD.md` §3.1);
  - explicit **repository-boundary rules** in `AGENTS.md`: the hub **MUST NOT**
    commit sub-project code from the hub root; each sub-repo commits independently
    (`DOCUMENTATION_STANDARD.md` §2.3);
  - the **orchestrator DWP** capability — plans that spawn **child DWPs** in
    sub-repos via an `ORCHESTRATOR_MANIFEST.md` (`DWP_SPECIFICATION.md` §8).
- A hub's sub-repositories are typically git-ignored at the hub level (tracked
  independently); the hub tracks only its own docs, coordination files, and a
  navigation index.
- Live example: this **Core Hub** — its `repositories/` boundary rules,
  `repositories/README.md` index, and the orchestrator DWP that created this very
  plan and its `ORCHESTRATOR_MANIFEST.md`.

---

## 4. The Agent Workspace

- An **agent workspace** is the long-lived working home of an autonomous agent —
  an OpenClaw workspace, a Hermes service directory, a personal-assistant daemon's
  data directory, or a cloud agent's persistent volume. It is a *workspace*, not
  necessarily a git repository, and its primary "product" is the agent's ongoing
  work rather than one codebase.
- The insight that makes this archetype possible: **the harness is a workspace,
  not specifically a repo.** Every harness element the methodology defines for a
  repository has a direct workspace equivalent:

| Harness element (repo) | Agent-workspace equivalent |
|------------------------|---------------------------|
| `AGENTS.md` (rules, quick commands) | The workspace's standing context (e.g. `AGENTS.md` itself, or the platform's standing-orders file) |
| `docs/` (durable knowledge) | Workspace knowledge files / memory documents |
| `.agents/` (skills, agents, commands) | The platform's skill directory — OpenClaw natively scans `<workspace>/.agents/skills/` |
| `.dwp/` (plans, drafts) | `.dwp/` in the workspace root — unchanged |
| git log (state, resumability) | `state.json` per plan (`PLAN_STATE.md`), REQUIRED here |

- An agent workspace **MUST** provide `AGENTS.md`, `.agents/`, and `.dwp/` at the
  workspace root. The `docs/` categories of `DOCUMENTATION_STANDARD.md` **SHOULD**
  be adapted to what the workspace actually is (a workspace has no test pyramid;
  it has tools, schedules, channels, and memory conventions worth documenting).
- **Git is RECOMMENDED, not REQUIRED.** Where git is absent, every plan **MUST**
  carry the machine-readable state layer (`PLAN_STATE.md` §2.1): `state.json`'s
  checkpoint, gate records, and per-task `commit`-equivalent timestamps carry the
  recovery information the git log carries in a repository.
- Plans in an agent workspace typically run **unattended** (`AGENT_PROTOCOL.md`
  §7): a scheduled heartbeat or cron turn resumes the open plan via the DWP
  Resume Protocol (`DWP_SPECIFICATION.md` §5.3), executes the next atomic task,
  updates the state layer, and yields. The plan — not the session — is the unit
  of continuity.
- A workspace plan **MAY** target external repositories (the agent clones, works,
  and commits there); each such repository is then its own individual-archetype
  target with its own validation commands, exactly like a child DWP
  (`DWP_SPECIFICATION.md` §8).

---

## 5. Classification Heuristic

An onboarding agent **MUST** classify the target before generating docs.

First, **agent workspace**: classify as an agent workspace when the target is the
working directory of an autonomous agent platform — signals: a platform identity /
standing-context file set (e.g. OpenClaw's `SOUL.md`, `HEARTBEAT.md`, `MEMORY.md`;
a daemon's config + memory tree), no primary application stack, and content that
is predominantly the agent's own state. Any one strong platform signal suffices.

Otherwise, it **MUST** classify the repo as an **orchestrator hub** when a clear
majority of the following signals hold; otherwise it **MUST** classify it as an
**individual repo**:

| Signal | Indicates hub |
|--------|---------------|
| A `repositories/` (or equivalent) folder containing multiple independent repos | strong |
| No single primary application stack at the root; the root is mostly markdown/coordination | strong |
| Sub-repos are git-ignored / tracked separately from the root | moderate |
| Presence of cross-project standards, a repo navigation index, or orchestrator manifests | moderate |
| Root `AGENTS.md` indexes *other repos'* `AGENTS.md` files | moderate |

- When signals are ambiguous, the agent **MUST** present its assessment and the
  evidence to the user and ask for confirmation before proceeding (consistent with
  `AGENT_PROTOCOL.md` approval behavior).
- A repo **MUST NOT** be classified as a hub solely because it is a monorepo; a
  monorepo with one build/stack is an **individual repo** with multiple modules
  (handled by per-module docs, `DOCUMENTATION_STANDARD.md` §4).

---

## 6. How Onboarding Differs

| Aspect | Individual repo | Orchestrator hub | Agent workspace |
|--------|-----------------|------------------|-----------------|
| Baseline `AGENTS.md` + `.agents/` | **MUST** | **MUST** | **MUST** |
| `docs/` standard categories + symlinks | **MUST** | **MUST** | **SHOULD**, adapted (§4) |
| Sub-project navigation index | n/a | **MUST** | n/a |
| `ECOSYSTEM_CONTEXT.md` | **SHOULD** | **MUST** | **MAY** |
| Cross-project standards guide | **MAY** | **MUST** | **MAY** |
| Repository-boundary rules in `AGENTS.md` | **SHOULD** (if vendored deps exist) | **MUST** (commit-from-sub-repo rule) | **MUST** when plans target external repos |
| Orchestrator DWP / child-DWP capability | typically unused | **MAY** / expected | **MAY** (external-repo work) |
| `ORCHESTRATOR_MANIFEST.md` pattern | n/a | **MUST** when running orchestrator plans | **MUST** when coordinating external repos |
| Per-module nested docs | **MUST** for major modules | applies to the hub's own modules; sub-repo modules are documented in each sub-repo | n/a |
| Machine-readable state layer (`PLAN_STATE.md`) | RECOMMENDED | RECOMMENDED | **MUST** without git; **MUST** for unattended runs |
| Validation commands | one repo's stack (reason per repo) | the hub's own (often docs-only); each child DWP uses **its** sub-repo's commands | per plan: the workspace's own checks, plus each target repo's commands |

- Onboarding an individual repo is the **lean** path: classify → reason about the
  stack-specific 10% (`DOCUMENTATION_STANDARD.md` §7) → generate baseline structure.
- Onboarding a hub is **additive**: do the baseline, then layer the hub-only
  structure above, and wire the orchestrator capability.
- Onboarding an agent workspace is **adaptive**: keep the platform's own files
  authoritative (never clobber `SOUL.md`-class identity files), add the DWP
  surface (`AGENTS.md` reference, `.agents/`, `.dwp/`), and document the
  workspace's tools, schedules, and memory conventions instead of a build stack.
- Addons (`ADDONS.md`) are archetype-agnostic and **MAY** be layered onto any of
  the three.

---

## 7. References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)
- `DOCUMENTATION_STANDARD.md` (§§2.2, 2.3, 3.1, 4, 8), `DWP_SPECIFICATION.md` (§§7, 8), `AGENT_PROTOCOL.md`, `ADDONS.md`
- `../RECONCILIATION.md` (divergence #5), `../../ORCHESTRATOR_MANIFEST.md` (archetype registry)
- Audited live references: the Core Hub (`repositories/`, `repositories/README.md`, this orchestrator plan) and the five individual product repos

---

*Part of the DeepWorkPlan methodology v2.2.0, MIT License, by [Dailybot](https://dailybot.com) / dailybotops.*
