# AGENT_PROTOCOL.md — Cross-Agent Behavior Specification

## Abstract

This document specifies the cross-agent behavior required of any AI coding agent
operating in a DeepWorkPlan-conformant repository: which agents are supported, how
each invokes commands, how all agents read the same shared configuration, and what
progress-reporting behavior is expected. It is the normative companion to
`DOCUMENTATION_STANDARD.md` (what structure exists) and `DWP_SPECIFICATION.md` (how
plans execute).

The governing principle is **one source of truth, many agents**: `AGENTS.md` and
the `.agents/` directory are agent-neutral and shared; each agent reaches them
through its own native convention. The protocol applies to **both archetypes**
(`ARCHETYPES.md`).

---

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 2.2.0 |
| **Status** | Stable |
| **Supersedes** | `PLAN_build_deepworkplan_brand/.../deepworkplan/spec/AGENT_PROTOCOL.md` (v1.0.0) |
| **Companions** | `DOCUMENTATION_STANDARD.md`, `DWP_SPECIFICATION.md`, `ARCHETYPES.md`, `ADDONS.md`, `PLAN_STATE.md` |
| **License** | MIT |

> **Additive in 2.2.0.** Two additions, no breaking changes: (1) **autonomous
> agent platforms** (OpenClaw, Hermes — daemon-style agents that load skills via
> the AgentSkills standard) join the supported-agents table; (2) the new
> **Execution Profiles** section (§7) specifies unattended execution — bounded
> authority, mandatory state layer, stop conditions, and scheduled continuation —
> for plans that run for hours without a human watching.

> **Divergence from v1 (overview).** v1's `AGENT_PROTOCOL.md` governed the
> *initialization* flow under an "agent-as-runtime, WebFetch on demand" model
> (model tiers, token-budget announcement, WebFetch-failure recovery). v2 reframes
> the protocol around an **installed skill** and a **shared `.agents/` surface**:
> the six supported agents, the `/` vs `#` command mapping, shared reading, and
> cross-agent progress reporting. The model-capability, approval-gate, validation,
> and privacy expectations from v1 are kept by reference and condensed
> (`RECONCILIATION.md` divergences #1, #2; "INIT/router" change row).

---

## 1. Conventions

The RFC 2119 keywords (**MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, **MAY**,
**REQUIRED**, **OPTIONAL**) are interpreted as in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 2. Supported Agents

This methodology **MUST** support the following AI coding agents. Any future
agent that reads markdown and can execute tool calls **MAY** be added without a
breaking change.

| Agent | Native config convention | Command prefix |
|-------|--------------------------|----------------|
| **Claude Code** | `.claude/` (symlinked to `.agents/`), `CLAUDE.md` (symlinked to `AGENTS.md`) | `/` (native) |
| **Cursor** | `.cursor/rules/*.mdc` referencing `AGENTS.md` | `#` or plain text |
| **OpenAI Codex** | `.codex/` / `CODEX.md` referencing `AGENTS.md` | `#` or plain text |
| **Google Gemini** | `.gemini/` referencing `AGENTS.md` | `#` or plain text |
| **GitHub Copilot** | `.github/copilot-instructions.md` referencing `AGENTS.md` | `#` or plain text |
| **Antigravity** | `.antigravity/` referencing `AGENTS.md` | `#` or plain text |
| **OpenClaw** | Natively scans `<workspace>/.agents/skills/` (AgentSkills standard) | plain text |
| **Hermes** | AgentSkills-standard skill loading; reads `AGENTS.md` | plain text |

The first six are **interactive coding agents** (a human in the session). OpenClaw
and Hermes are **autonomous agent platforms** — long-lived daemons with scheduled
turns — and typically execute plans under the **unattended profile** (§7) inside
an **agent workspace** (`ARCHETYPES.md` §4).

- Every supported agent **MUST** treat `AGENTS.md` as the single source of truth
  for repository conventions; a per-agent config file **MUST** reference it and
  **MUST NOT** duplicate its content (`DOCUMENTATION_STANDARD.md` §2.5).
- A model used to run DeepWorkPlan work **MUST** be reasoning-capable
  (inspecting many files, stack detection, self-validation, failure recovery);
  speed/cost-tier models **SHOULD NOT** be used for plan creation or repo onboarding.

---

## 3. Command Invocation Mapping (`/` vs `#`)

Commands live as markdown procedure files in `.agents/commands/` and are catalogued
in `.agents/docs/COMMANDS_REFERENCE.md`.

- **Claude Code** **MUST** invoke commands with the native `/` prefix
  (e.g. `/dwp-create`, `/dwp-execute`).
- **Cursor, Codex, Gemini, Copilot, and other non-Claude agents** **MUST** invoke
  commands with the `#` prefix (e.g. `#dwp-create`) or as plain text
  (e.g. "run dwp-create"). These CLIs intercept `/` as their own system prefix, so
  `/` **MUST NOT** be assumed available outside Claude Code.
- When a user's message begins with `#{command}` (or names a command), the agent
  **MUST** treat it as a command invocation.

On any command invocation, an agent **MUST**:

1. **Look up** the command (without its prefix) in `.agents/docs/COMMANDS_REFERENCE.md`
   to find its procedure file.
2. **Read** that procedure file completely.
3. **Follow** its steps exactly.
4. **MUST NOT** improvise, skip steps, or substitute remembered behavior — the
   procedure file is the spec.

> **Divergence from v1.** v1 documented the `/` vs `#` distinction inside per-agent
> adapter manifests. v2 makes it a **single normative mapping** in this protocol and
> ties it to the shared `.agents/commands/` + `COMMANDS_REFERENCE.md` surface
> (`RECONCILIATION.md` "adapters" change row).

---

## 4. Shared `.agents/` Reading

- All supported agents **MUST** read the same configuration content from `.agents/`
  (agents, commands, skills, docs, settings), each through its own convention:
  Claude Code via the `.claude → .agents` symlink (`DOCUMENTATION_STANDARD.md` §6),
  others via their referencing config files.
- `.agents/` content **MUST** be authored agent-neutral. An agent **MUST NOT**
  introduce agent-specific divergence into shared files; agent-only settings (e.g.
  Claude Code's `settings.json` harness config) **MUST** be ignored by agents that
  do not consume them.
- The DWP skill (`.agents/skills/deepworkplan/`) and any other skill packs **MUST**
  be consumable by every supported agent through the skill's own `SKILL.md` router.

---

## 5. Progress Reporting

- Agents **SHOULD** report progress after significant work (a feature, a bug fix, a
  completed DWP plan, a migration, or substantial multi-commit work), framed as what
  the human accomplished. Trivial, read-only, or rolled-back work **SHOULD NOT** be
  reported.
- Reporting **MUST NOT** block or delay the actual work: if the reporting channel
  fails, times out, or is unreachable, the agent **MUST** log the issue and continue.
  Progress reporting is important but secondary.
- This expectation applies cross-agent. The mechanism is repo-specific (e.g. the
  Dailybot repos use the `dailybot` skill) and is therefore part of the
  reason-per-repo 10% (`DOCUMENTATION_STANDARD.md` §7).

---

## 6. Preserved v1 Expectations (by reference)

The following v1 behaviors are **kept** and apply during onboarding and plan
execution: read-before-action repository analysis; explicit user approval before
**destructive** actions (overwriting or deleting existing files); validation before
marking work complete (`DWP_SPECIFICATION.md` §5.1); and privacy — an agent **MUST
NOT** exfiltrate source/secrets and **MUST NOT** write literal secret values into
generated documentation. See `RECONCILIATION.md` non-divergences.

---

## 7. Execution Profiles

Every plan executes under exactly one of two profiles. The profile changes *who
watches*, never *what gates apply* — validation discipline
(`DWP_SPECIFICATION.md` §5.1) is identical in both.

### 7.1. Interactive (default)

A human is present in the session. The agent proposes, the human approves the
refined draft, the agent executes task-by-task, and ambiguity is resolved by
asking. Everything in this protocol so far describes the interactive profile.

### 7.2. Unattended

The plan runs with no human watching — an autonomous platform's scheduled turn,
a cloud session, an overnight run. Unattended execution is **opt-in per plan**
and **MUST** satisfy all of the following:

- **Pre-approved plan.** The refined draft was approved by a human before any
  unattended turn. An agent **MUST NOT** create *and* execute a plan unattended
  in one breath; plan approval is the human control point.
- **State layer REQUIRED.** The plan **MUST** carry `manifest.json` and
  `state.json` (`PLAN_STATE.md` §2.1) so any later session — agent or human —
  can read exact progress without replaying a transcript.
- **Bounded authority.** The agent's authority is the plan: it **MUST NOT**
  expand scope, **MUST NOT** perform destructive or outward-facing actions the
  plan does not explicitly authorize (force-pushes, deletions outside listed
  paths, publishing, messaging third parties), and **MUST NOT** stretch a task's
  instructions to cover discovered-but-unplanned work — discovered work is
  recorded for the next `refine`, not improvised.
- **One atomic task per turn, gates always.** Each turn runs the DWP Resume
  Protocol (`DWP_SPECIFICATION.md` §5.3), executes at most the next task,
  passes its validation gate, completes per §5.2, and yields. A failing gate is
  a stop condition, never a "continue anyway".

### 7.3. Stop Conditions and Escalation

An unattended agent **MUST** halt the plan — populate `state.json.blocked`
(`PLAN_STATE.md` §4.4) with the task, the reason, and what it needs, then stop —
when any of these occur:

1. A validation gate fails and the fix is not already within the task's scope.
2. The task requires an approval, credential, or decision the plan did not
   pre-authorize.
3. Reality diverges from the plan's assumptions (missing file, changed API,
   conflicting concurrent work, §5.2 desync that reconciliation cannot resolve).
4. Two consecutive turns make no verifiable progress on the same task.

Halting is success, not failure: the blocked record is the escalation message.
The platform's notification channel (heartbeat report, progress report per §5)
**SHOULD** surface it; the human (or a `refine` session) unblocks, and the next
scheduled turn resumes normally.

### 7.4. Scheduled Continuation

On platforms with scheduling (OpenClaw heartbeat/cron, Hermes cron, cloud-agent
wake), continuation **MUST** be expressed as: *wake → run the DWP Resume
Protocol → if `blocked`, report and yield → else execute the next atomic task →
update the state layer → yield.* The plan, not the session, is the unit of
continuity; a plan **MUST** survive the platform restarting, the model changing,
or a different agent picking up the next turn.

---

## 8. References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)
- `DOCUMENTATION_STANDARD.md` (§§2.5, 5, 6, 7), `DWP_SPECIFICATION.md` (§§5.1–5.3), `ARCHETYPES.md` (§4), `ADDONS.md`, `PLAN_STATE.md`
- `../RECONCILIATION.md` — Task 1 carry-forward and divergences
- [AgentSkills standard](https://agentskills.io)
- Audited live references: Core Hub `CLAUDE.md` "Slash Commands (All Agents)" + `.agents/docs/COMMANDS_REFERENCE.md`; `repositories/agent-skill` multi-agent `setup.sh`

---

*Part of the DeepWorkPlan methodology v2.2.0, MIT License, by [Dailybot](https://dailybot.com) / dailybotops.*
