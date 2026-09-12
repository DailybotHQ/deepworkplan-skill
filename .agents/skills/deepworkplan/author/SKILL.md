---
name: deepworkplan-author
description: Author or update reusable skills, agents, and commands in the current repo — reason about the repo's .agents/ layout, follow the Open Agent Skills frontmatter contract, and keep the .agents/docs/ catalog in sync. Use when a developer wants to create or evolve the repo's agent kit (skills, agents, commands), or runs /skill-create or /agent-create.
version: "4.0.3"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
---

# DeepWorkPlan — Author

Author and maintain the current repository's **agent kit**: reusable **skills**, **agents**, and
**commands**. Reason about the repo — never copy a generic kit. This sub-skill is also the executor of
the **skills reconciliation** the Final Review performs (DWP spec 2.3.0 §6.1) — and, in a plan created
under an earlier lifecycle, of that plan's separate "Skills & Agents Discovery" task.

---

## Read scope

- **Guide (essential — read for this flow):** [`../guide/skills-integration.md`](../guide/skills-integration.md) §11 — how skills and agents are referenced from plans and tasks.
- **Guide (conditional — read only when the trigger fires):** none. [`../guide/GUIDE.md`](../guide/GUIDE.md) is the routing index.

## Concepts

- **Skill** — a reusable, parameterized *procedure* invoked in-session (e.g. `/fix-lint`). Encodes
  "how to do X". Lives in `<skills-dir>/<name>/SKILL.md`.
- **Agent** — a specialized *worker definition* (role, model tier, tools, system prompt) dispatched to
  handle a class of tasks (e.g. `reviewer`, `executor`). Encodes "who does X". Lives in
  `<agents-dir>/<name>.md`.
- **Command** — a thin slash-command entry point that routes to a skill or agent. Logic stays in the
  skill/agent; the command is a delegator.

| Need | Create |
|------|--------|
| A repeatable procedure run in-session | Skill |
| A persistent role with its own model tier / tools | Agent |
| A shortcut to invoke a skill or agent | Command |

## Frontmatter fields (cross-agent)

The tool-agnostic core every harness reads: **`name`** (kebab-case, English, unique) and
**`description`** (one line, starts with a verb — harnesses use it for relevance scoring).
Everything else is a **per-harness opt-in**: keep only the keys the host repo's neighboring
files already use, and never require a key the repo does not use.

| Field | Applies to | Meaning |
|-------|-----------|---------|
| `name` | skill / agent | kebab-case identifier; the registry/harness address |
| `description` | skill / agent | one line, starts with a verb; used for relevance scoring |
| `version` | skill | quoted SemVer (`"1.0.0"`) — quote it so YAML keeps it a string |
| `documentation_url` | skill | canonical docs URL; replaces the legacy `homepage` (some harnesses treat `homepage` as a re-fetch source — never use it) |
| `user-invocable` | skill | `true` makes `/<name>` a slash command where the harness supports it |
| `allowed-tools` | skill | tool allowlist (e.g. `Bash, Read, Grep, Glob, Edit, Write`) where the harness enforces one |
| `model` | agent | abstract tier (`light` / `standard` / `heavy`) — never a vendor model ID (see "Model tiers") |
| `tools` | agent | the agent's tool list; keep it as narrow as the role allows |

Do not invent harness features: if a field is not already used in this repo (or documented by the
target harness), leave it out rather than guessing a key name.

---

## Step 0 — Detect the repo layout (do NOT assume)

Before authoring anything, discover where this repo keeps its kit. Do not hardcode any single repo's
conventions.

1. Find the agent root: look for `.agents/`, then `.claude/` or `.cursor/` (often symlinks to `.agents/`), then any
   `AGENTS.md` / `CLAUDE.md` at the repo root for documented paths.
2. Within it, locate `skills/`, `agents/`, `commands/`, and a catalog under `docs/`.
3. Inspect 1-2 existing skills/agents to learn the repo's **local conventions** (frontmatter keys it
   uses, naming, body structure, whether commands are thin delegators). Match them.

```bash
ls -d .agents .claude 2>/dev/null
ls .agents/skills .agents/agents .agents/commands .agents/docs 2>/dev/null
ls AGENTS.md CLAUDE.md 2>/dev/null
```

If the repo has no `.agents/` layout yet, route the developer to the **onboard** sub-skill first
(`onboard/SKILL.md`) — onboarding scaffolds the directories this sub-skill writes into.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`.

**Writes:** new or updated files **only** under the repo's `.agents/` kit —
`skills/*/SKILL.md`, `agents/*.md`, `commands/*.md`, `docs/` catalogs — plus the
catalog index entries that keep them discoverable. Broad additions (a new skill
family, restructuring the kit) are proposed to the developer before creation.

**It MUST NOT:** edit files outside `.agents/` (a skill's *content* may
document anything; this sub-skill writes only kit files), weaken the frontmatter
conventions (`name`, quoted `version:`, `documentation_url`, `user-invocable`,
`allowed-tools`, kebab-case), delete an existing skill/agent/command without
explicit approval, or commit/push.

---

## Flows

Pick the flow that matches the developer's intent.

### A. Create a skill

1. **Audit fit** — confirm a real, repeatable workflow exists (see "Repo-fit rubric" below). Skip
   generic skills that do not match an actual workflow.
2. **Name it** — kebab-case, English, unique. Check for collisions in the skills dir.
3. **Scaffold** — copy `templates/SKILL_TEMPLATE.md` into `<skills-dir>/<name>/SKILL.md`. Adapt the
   frontmatter to the repo's local convention (keys it already uses).
4. **Fill** — one-procedure focus; clear Goal, When-to-use, Steps, Validation.
5. **Keep commands thin** — if it needs a slash command, add a delegator (see Flow C).
6. **Catalog** — update the repo's catalog under the docs dir (see "Keep the catalog in sync").
7. **Validate** — naming, structure, frontmatter, and that any command is thin.

### B. Create an agent

1. **Confirm a recurring role** with distinct model/tools needs (not just a one-off procedure → that
   is a skill).
2. **Name it** — kebab-case, English, unique.
3. **Scaffold** — copy `templates/AGENT_TEMPLATE.md` into `<agents-dir>/<name>.md`.
4. **Choose a model tier** — reason about it (see "Model tiers" below). Do NOT hardcode vendor model
   IDs inside the agent body; keep the abstract tier and map it in repo config.
5. **Fill** — Role, Inputs, Process, Output, escalation rules.
6. **Catalog** — update the catalog under the docs dir.
7. **Validate** — naming, structure, tier chosen with justification.

### C. Create a command (thin delegator)

1. Confirm the target skill or agent exists.
2. Scaffold from `templates/COMMAND_TEMPLATE.md` into `<commands-dir>/<cmd>.md` — a ~20-line
   delegator: read the target skill/agent fresh and follow it, passing along args. Do NOT embed
   logic — logic lives in the skill/agent so updates propagate.
3. Reference the new command in the catalog / commands reference.

### D. Update an existing skill / agent / command

1. Read the existing file and the repo's conventions first.
2. Make the smallest change that satisfies the request; preserve frontmatter the repo relies on.
3. Keep delegators thin; keep skills single-procedure.
4. Update the catalog if name, description, or surface changed.

### E. Evaluate the catalog (skills reconciliation)

This is the flow the **Final Review** invokes for its skills-reconciliation pass. A plan
created under the pre-2.3.0 lifecycle invokes the same flow from its separate
"Skills & Agents Discovery" task; the procedure is identical either way.

1. Enumerate every skill (`<skills-dir>/*/SKILL.md`) and agent (`<agents-dir>/*.md`).
2. For each, capture name, one-line description, and model tier (if any).
3. Cross-check against the repo's catalog under the docs dir: flag missing entries, stale
   descriptions, orphaned commands, and duplicates.
4. Reconcile: update the catalog so it matches reality. Report drift found and fixed.

---

## Repo-fit rubric (before creating)

Gather: stack & tooling (languages, frameworks, package manager, test runner, linter); workflows (how
code is built, tested, reviewed, released); pain points (repetitive manual steps); the existing kit
(avoid duplicates). Then:

- Create a **skill** for a repeatable procedure people do by hand.
- Create an **agent** for a recurring role with distinct model/tools needs.
- Create a **command** only as a thin entry point.
- Skip anything generic that does not match a real workflow.

Anti-patterns to avoid: generic kits that do not match the repo; fat commands with embedded logic;
duplicates of existing skills/agents; agents pinned to vendor model IDs in their bodies.

---

## Model tiers (for agents)

Skills inherit the session model; agents may pin an abstract tier.

| Tier | Use for | Examples |
|------|---------|----------|
| **light** | Mechanical, well-specified, low-judgment tasks | formatting, lint fixes, renames, list/status commands |
| **standard** | Most engineering work; moderate reasoning | feature work, refactors, test writing, reviews |
| **heavy** | High-judgment, architectural, ambiguous tasks | architecture, security audits, complex planning |

How to choose: default to **standard**; drop to **light** only if mechanical and well-specified; raise
to **heavy** only for deep reasoning or high blast radius. Keep tiers abstract — map them to concrete
model IDs in the repo's runtime/config, in one place, never inside skill bodies.

---

## Keep the catalog in sync

After any create/update, reconcile the repo's catalog (commonly under the docs dir, e.g. a
skills/agents catalog and a commands reference). Add or update the row for the affected skill/agent/
command: name, one-line description, tier (agents), and the command that invokes it. The catalog must
always match what is on disk.

---

## Templates

- `templates/SKILL_TEMPLATE.md` — skill scaffold.
- `templates/AGENT_TEMPLATE.md` — agent scaffold.
- `templates/COMMAND_TEMPLATE.md` — thin-delegator command scaffold.

Reference them by these relative paths. Adapt the frontmatter to the host repo's local convention
(keep only the per-harness opt-in keys neighboring files already use — `version`,
`documentation_url`, `user-invocable`, `allowed-tools`; see "Frontmatter fields").

---

## Validation

- Names are kebab-case, English, unique.
- Frontmatter matches the repo's convention; descriptions are a single line starting with a verb.
- Skills are single-procedure; agents declare a justified tier (no hardcoded vendor model IDs).
- Commands are thin delegators with no embedded logic.
- The catalog under the docs dir reflects every change.

---

## Notes

- Reason about the repo; never copy a generic kit.
- Propose before creating when scope is broad — confirm the short list with the developer first.
- All references inside the skill are relative; nothing outside the skill root is required at runtime.
