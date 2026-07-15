# SPEC.md — Dailybot Addon (Normative)

## Abstract

This document is the **normative specification** of the DeepWorkPlan **Dailybot
addon**: an opt-in capability that connects an AI-first repository to the
developer's **Dailybot team** so DWP work — especially a **plan completion** —
surfaces to humans as a standup-style **progress/milestone report**. It defines
**what the addon installs/configures** (all opt-in), how it **defers
authentication** to the Dailybot skill's own consent flow, how the **optional
progress-report step** is wired into DWP execution, the **never-block** rule, the
**reconcile-don't-clobber** behavior, and the **vendor-neutral guardrail**.

The addon is governed by [`../README.md`](../README.md) and
[`methodology-spec/ADDONS.md`](../../spec/ADDONS.md): it is **never** required for
baseline AI-first conformance.

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 2.3.0 |
| **Status** | Stable |
| **Companions** | `SKILL.md`, `templates/INTEGRATION.md`, `../README.md`, `methodology-spec/ADDONS.md`, `../../spec/PLAN_STATE.md` |
| **License** | MIT |

> **Additive in 2.2.0.** Reporting grows from a single completion hook into a
> **plan lifecycle event model** (§5.1): kickoff, significant task, blocked, and
> completion — with the report's `--json-data` payload derived from the plan's
> machine-readable state layer (`PLAN_STATE.md`). All events remain opt-in,
> conditional, and non-blocking; the completion milestone is unchanged.
>
> **Additive in 2.3.0.** Version gates align with the Dailybot agent skill **3.10.3**
> and `dailybot-cli` **>= 3.7.0** (unified floor — hooks, chat, authoring, the
> browse/read surface, and the per-repo `.dailybot/env.json` auth added in CLI 3.7.0 ship together). §3.5 documents the paired skill's full
> capability surface; this addon still wires only the `report` sub-skill.

## 1. Conventions

The RFC 2119 keywords (**MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**,
**MAY**, **OPTIONAL**) are interpreted as in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

Throughout, the **Dailybot skill** is the official agent skill pack
([`DailybotHQ/agent-skill`](https://github.com/DailybotHQ/agent-skill)); the
**Dailybot CLI** is its companion binary
([`DailybotHQ/cli`](https://github.com/DailybotHQ/cli), PyPI `dailybot-cli`).

---

## 2. Vendor-Neutral Guardrail (the rule that frames everything)

- The **core DeepWorkPlan methodology MUST have zero dependency on Dailybot.**
  It is vendor-neutral, MIT, and agent-agnostic. A repository **MUST** be fully
  conformant to the AI-first baseline (`DOCUMENTATION_STANDARD.md` §§2–7) and to
  the DWP specification with **zero** addons — including this one.
- This addon **MUST NOT** be presented as a precondition for using DWP, and the
  `onboard` flow **MUST NOT** auto-install it for everyone. It is offered, and
  applied only on explicit acceptance.
- Declining this addon **MUST** still produce a baseline-conformant repo.
- The addon's value is **purely additive team visibility** for developers/teams
  who already use Dailybot.

---

## 3. What the Addon Installs / Configures (all OPT-IN)

When accepted, the addon **MAY** install or configure the following — each only
with explicit acceptance, and each reconciled if already present (§7):

### 3.1 The Dailybot agent skill (recommended path)

- The addon **SHOULD** offer the **Dailybot agent skill** as the primary path,
  because it brings its own install/consent/auth flow and the `report`
  sub-skill. Supported install methods (the addon **MUST** offer, not force):
  - `npx skills add DailybotHQ/agent-skill` (cross-agent, recommended), **or**
  - OpenClaw native: `openclaw skills install dailybot`, **or**
  - `git clone https://github.com/DailybotHQ/agent-skill.git` + run its `setup.sh`.

### 3.2 The Dailybot CLI (the underlying bridge)

- The Dailybot CLI is the bridge the skill uses. The Dailybot skill installs it
  on first use via **its own SHA-256-verified consent flow**, so the addon
  **SHOULD NOT** install the CLI separately when the skill is being installed.
- When the developer explicitly wants the CLI directly, the supported paths
  are, **in preference order**:
  - `pip install 'dailybot-cli>=3.7.0'` (Python 3.10+), **or**
  - `brew install dailybothq/tap/dailybot` (macOS), **or**
  - The Dailybot skill's **verified installer flow** (macOS / Linux /
    Windows) — documented in the skill's `shared/auth.md` as a three-step
    `download → verify SHA-256 sidecar (optional cosign) → execute` sequence.
    The addon **MUST** point at that flow and **MUST NOT** substitute a
    one-line remote-installer pipe (any variant of "fetch from the network
    and execute in one command") — that pattern is unverifiable at the
    reader's terminal and is flagged as a critical delivery-vector risk by
    every mainstream security auditor (Snyk rule E005, Socket W012).
- The addon **MUST NOT** reimplement the verified installer; it points at the
  Dailybot skill's flow.

### 3.3 Optional repo identity

- The addon **MAY** commit a repo identity so every contributor and agent signs
  reports under the same name: `.dailybot/profile.json` (or the
  gitignore-friendly `.dailybot_example/profile.json` template the CLI
  documents).
- A `key` (credential) field in that file is a **hard error** — the addon
  **MUST NOT** write credentials anywhere.
- The same file **MAY** carry the committed report policy that the hook layer
  (§3.4) honors: `"report": {"min_interval_minutes": <n>, "nudge": true|false}`.

### 3.4 Optional harness hook enforcement

- When `dailybot-cli` is **>= 3.7.0** (the unified floor for the current skill
  pack, currently **3.10.3**), the addon **SHOULD** offer — and **MAY**, with
  explicit acceptance, commit — repo-level harness hook configs whose entries
  invoke the `dailybot hook` lifecycle commands (`session-start`, `activity`,
  `post-commit`, `stop`, `dismiss`), e.g. Claude Code `.claude/settings.json`
  (or `.agents/settings.json` where `.claude → .agents`),
  Cursor `.cursor/hooks.json` (or via `.cursor → .agents`).
- The hook templates, output dialects, anti-noise gates, auto-activation triggers
  (`report/triggers.md`), and uninstall path are owned by the Dailybot skill's
  `report/hooks.md` — the addon **MUST** defer to it and **MUST NOT** duplicate
  or diverge from those templates.
- The addon **MUST NOT** write hook configs without explicit acceptance, and
  **MUST** merge into existing config files — never overwrite (§7). Existing
  `dailybot hook` entries **MUST** be preserved, not duplicated.
- When the CLI is below 3.7.0, the addon **MUST** skip this offer (the §5
  wiring stands alone) and **MAY** suggest `dailybot upgrade` once.
- The committed `.dailybot/profile.json` **MAY** include
  `"report": {"mode": "continuous"}` for research/docs-heavy repos so non-commit
  work is nudged sooner (Dailybot skill `report/hooks.md` § Per-repo controls).

### 3.5 Paired Dailybot skill — full capability surface (informational)

The Dailybot agent skill (currently **3.10.3**, source
[`DailybotHQ/agent-skill`](https://github.com/DailybotHQ/agent-skill)) exposes
**14 coordinated sub-skills**: report, ask, messages, email, chat,
conversations, health, check-ins (complete + authoring), kudos (give + browse),
teams (list/resolve + `me`/`org`/`user get`), forms (lifecycle + authoring),
workflows (read-only list/get), report channels, and per-repo API keys
(`.dailybot/env.json` via `dailybot env`). **This addon wires only the
`report` sub-skill** into DWP plan execution (§5). The other capabilities are
available when the developer invokes the Dailybot skill directly — the addon
**MUST NOT** wire them into DWP execution unless the developer explicitly asks.

---

## 4. Authentication — DEFER, Do Not Reinvent

- The addon **MUST** defer all authentication to the Dailybot skill's own
  consent flow (`shared/auth.md`): `dailybot login` (email OTP) or
  `DAILYBOT_API_KEY` / `dailybot config key=...`, including the CLI install
  consent and the HTTP fallback.
- The addon **MUST NOT** prompt for email, OTP, or API keys itself, **MUST NOT**
  bypass or weaken that flow, and **MUST NOT** store any credential in any file
  it creates.
- If the developer declines authentication, the addon **MUST** skip reporting and
  continue — auth issues **MUST NOT** block the primary work (§6).

---

## 5. The Integration Value — The Plan Lifecycle Event Model

This is the "why": when present, the **full DWP plan lifecycle surfaces to the
developer's Dailybot team** as standup-style agent updates — what is starting,
what is progressing, what is stuck, and what shipped.

### 5.1 The four lifecycle events

The addon **MUST** wire a clearly-**optional** report step into the repo's DWP
execution documentation (the generated `AGENTS.md` reporting section and/or
`docs/AI_AGENT_COLLAB.md`) describing these events. Every event is conditional
(§5.3) and non-blocking (§6).

| Event | Trigger | Level | Requirement |
|-------|---------|-------|-------------|
| **Kickoff** | A plan is materialized and approved (`create` Step 5), or its first `execute` turn begins | regular | **SHOULD** |
| **Significant task** | A task that is independently significant completes — a feature, a bug fix, a major refactor (`execute` Step 5). Intermediate setup tasks are **not** reported. | regular | **MAY** |
| **Blocked** | The plan halts on a stop condition and `state.json.blocked` is populated (`AGENT_PROTOCOL.md` §7.3, `PLAN_STATE.md` §4.4) — typical of unattended runs | regular, with `blockers` populated | **SHOULD** |
| **Completion** | All tasks `[x]`; the plan finishes (`execute` Step 7) | **milestone** | **SHOULD** |

- The **kickoff** report describes *what is being built and why it matters*
  ("Starting: …"), giving the team forward visibility — never "created
  PLAN_x with N tasks".
- The **blocked** report is the unattended profile's escalation made human: the
  team sees *what is stuck and what it needs* in the standup channel instead of
  discovering a silent overnight halt. Its content **MUST** come from
  `state.json.blocked` (`reason`, `needs`).
- A plan **completion** is the only **milestone**; every other event is a
  regular report. A plan **MUST NOT** emit more than one kickoff and one
  completion report.

### 5.2 Payload — derived from the plan state layer

The report command shape is
`dailybot agent update "<message>" [--milestone] --json-data
'<completed/in_progress/blockers>' --metadata '<repo/branch/model>'`.

- When the plan carries the machine-readable state layer (`PLAN_STATE.md`),
  `--json-data` **SHOULD** be derived from `state.json`: `completed` from the
  completed tasks (phrased as outcomes, not task numbers), `in_progress` from
  the task currently `in_progress`, and `blockers` from `state.json.blocked`.
  The state layer is the single source the payload is projected from — the
  addon **MUST NOT** invent a second progress-tracking mechanism.
- Without the state layer, the payload is derived from the plan README's
  checkbox list. The message and payload **MUST** still follow the writing
  rules below.
- Report content **MUST** follow the dailybot `report` writing rules: describe
  **what was built and why**, in English, 1–3 sentences, never "completed a
  plan", never file paths / git stats / branch names / plan IDs.

### 5.3 How the events are emitted

- Every event is **conditional**: it fires **only** when the Dailybot skill/CLI
  is present and authenticated. The addon **MUST** document the detection check
  (e.g. `command -v dailybot`, or the skill installed at
  `~/.<agent>/skills/dailybot/`) and that the report routes through the dailybot
  `report` sub-skill, not a hand-rolled API call.
- The addon **MUST NOT** change the DWP `create`/`execute` public surface; it
  only adds optional, conditional reporting hooks described in the repo's docs.
- The addon **SHOULD** respect Dailybot's per-repo opt-out
  (`.dailybot/disabled`): if present, no report is sent — for any event.
- **Synergy with hook enforcement (§3.4):** a successful
  `dailybot agent update` — any lifecycle event — resets the Dailybot hook
  ledger, so the two layers never double-report. The hooks are the
  deterministic backstop for a missed lifecycle event; a hook reminder
  mid-plan **MUST** be answered with either a lifecycle-appropriate report or
  `dailybot hook dismiss`, never ignored silently.

---

## 6. Never-Block Rule (mandatory)

- Reporting **MUST NOT** block the developer's primary work or DWP `execute`.
- If the Dailybot skill/CLI is **absent**, **unauthenticated**, the network is
  **down**, or any command **errors**, the addon's wired step **MUST**: warn
  briefly once, continue the primary task, **not** retry automatically, and
  **not** enter a diagnostic loop. This mirrors the Dailybot skill's own
  non-blocking guarantee.
- Plan execution **MUST** succeed regardless of whether the report was sent.
- The `dailybot hook` commands (§3.4) read only local state and always exit
  `0` by contract, so installing hook enforcement cannot violate this rule;
  the hooks also honor `.dailybot/disabled` and the committed report policy.

---

## 7. Reconcile, Don't Clobber

- The addon **MUST** detect existing setup before acting: an already-installed
  Dailybot skill, a `dailybot` CLI on PATH, a committed `.dailybot/profile.json`
  / `.dailybot_example/profile.json`, an existing report step in the repo's
  DWP docs, or harness hook configs already carrying `dailybot hook` entries.
- Where a piece already exists, the addon **MUST** preserve it and only fill
  gaps — it **MUST NOT** reinstall, re-prompt auth, overwrite a working identity,
  or duplicate the report step.
- Any destructive change to an existing file **MUST** be approved by the user
  first (`AGENT_PROTOCOL.md`); the addon **MUST** record what it changed.

---

## 8. Conformance + Validation Step

A repo is **conformant to this addon** when **all** hold (after acceptance):

1. The Dailybot skill **or** CLI is available (installed via one of the §3
   opt-in paths), **or** the addon recorded why it could not install here
   (sandbox/CI) without failing onboarding.
2. Authentication was **deferred** to the Dailybot skill's `shared/auth.md` — no
   email/OTP/API-key prompting and **no credential** written by this addon.
3. The repo's DWP execution docs describe the **optional, conditional,
   non-blocking** lifecycle events (§5.1): kickoff, significant task, blocked,
   and the **milestone** on plan completion — all via the dailybot `report`
   sub-skill, with payloads derived from the plan state layer where present.
4. If a repo identity was committed, it is credential-free (no `key` field) and
   resolves consistently for all contributors/agents.
5. Existing skill/CLI/identity/report-step were **reconciled**, not clobbered.
6. The vendor-neutral guardrail holds: nothing in the repo implies DWP **requires**
   Dailybot; the repo is still baseline-conformant.
7. **Smoke test (best-effort):** if the CLI is present and authenticated,
   `dailybot status --auth` succeeds; otherwise note why. Never fail onboarding
   on this.

---

## 9. References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)
- `SKILL.md` (the onboarding hook + flow), `templates/INTEGRATION.md` (reasoning aid)
- `../README.md` (addon mechanism), [`../../spec/ADDONS.md`](../../spec/ADDONS.md) (concept + pointer)
- Dailybot skill: [`DailybotHQ/agent-skill`](https://github.com/DailybotHQ/agent-skill)
  — `SKILL.md` (currently **3.10.3**), `shared/auth.md`, `TRUST.md`,
  `report/SKILL.md`, `report/hooks.md`, `report/triggers.md`
- Dailybot CLI: [`DailybotHQ/cli`](https://github.com/DailybotHQ/cli), PyPI `dailybot-cli`
  — minimum **>= 3.7.0**; `docs/AGENT_HOOKS.md` (the `dailybot hook` command group
  + report ledger)
- [`../../spec/PLAN_STATE.md`](../../spec/PLAN_STATE.md) (the state layer the payloads derive from), `../../spec/AGENT_PROTOCOL.md` §7 (unattended profile + stop conditions)

---

*Part of the DeepWorkPlan methodology v2.3.0, MIT License, by [Dailybot](https://dailybot.com) / dailybotops.*
