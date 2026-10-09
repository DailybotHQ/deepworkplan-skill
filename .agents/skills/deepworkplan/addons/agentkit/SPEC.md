# SPEC.md — agentkit Addon (Normative)

## Abstract

This document is the normative specification of the DeepWorkPlan
**agentkit addon**: an opt-in thin integrator of **coding-agents-kit**
(`ak`), used as the **headless** delegation transport of v7 plans
(`../../spec/V7_CONTRACT.md`). The kit is a separate product with its own
repository, license and release cycle; this addon is the DWP-side
integration contract only: detection, the offer, the pinned install, the
registry record and the mapping of the four delegation operations onto
`ak run`.

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 0.1.0 |
| **Status** | Beta (DeepWorkPlan 7.0.0-beta.1) |
| **Product pin** | `DailybotHQ/coding-agents-kit` `v0.1.1`, interface `1` |
| **Companions** | `SKILL.md`, `addon.json`, `templates/INTEGRATION.md`, `../README.md`, `../../spec/ADDONS.md`, `../../spec/V7_ABILITIES.md`, `../../execute/delegation.md` |

## 1. Conventions

RFC 2119 keywords (**MUST**, **MUST NOT**, **SHOULD**, **MAY**). **The
kit** is coding-agents-kit; **the addon** is this folder.

## 2. What This Addon Is — and Is Not

- An **optional** delegation transport. It is **never required**: a
  repository without it is fully conformant and every plan runs
  sequentially in the current session.
- It contributes the abilities `subagents`, `cancel_children` and
  `model_routing` **only** at runtime, only when enabled in the registry,
  detected and on interface `1` (`V7_ABILITIES.md`). It requires the
  contract grant `agent_delegation` for any use.
- It does not implement agents, profiles or provider keys — the kit does.

## 3. Detection

- Detection **MUST** be read-only: `command -v ak`, then `ak doctor --json`.
- The `interface` field **MUST** equal `1`; any other value is one warning
  and the addon is **not available** — never an error.
- The addon **MUST NOT** read or print provider key values; `ak doctor`
  reports key **names** only.

## 4. Offer, Install and Record

- The offer is an explicit opt-in (`onboard` Phase 7b); declining is
  complete and writes nothing.
- The documented install is the pinned tagged clone plus the kit's
  installer:
  `git clone --branch v0.1.1 https://github.com/DailybotHQ/coding-agents-kit` then
  `./coding-agents-kit/install.sh` (Windows: `install.ps1`). A
  fetch-and-execute pipeline **MUST NOT** appear anywhere in this pack's
  text. The addon **MUST NOT** install coding-agent CLIs on its own.
- On acceptance the addon **MUST** record `addons.agentkit` =
  `{"enabled": true, "version": "v0.1.1"}` through `shared/config.py
  enable`. Enabling grants no plan any authority.

## 5. The Transport (v7 delegation)

Each delegate is exactly one `ak run` in exactly one dedicated git
worktree:

| Operation | Behaviour |
|---|---|
| **launch** | Create the worktree on a dedicated branch; record `delegate launch` (prompt digest) **before** starting; start `ak run <kind> [@profile] --cwd <worktree> --timeout <seconds> --output-format json -- "<prompt>"`, stdout redirected to the delegation's result file. |
| **observe** | Read-only: `delegate observe` and whether the process is alive. |
| **collect** | Parse the single JSON object; `exit` 0 → `completed`, any other → `failed`; record `delegate collect` with `result_path`. Integration of the worktree diff and the task's gates happen in the parent session. |
| **cancel** | SIGTERM to `ak run` (the kit kills the process tree and exits 5); record `delegate cancel`. |

- The prompt **MUST** carry the task objective and acceptance criteria and
  name the worktree as the only writable location; it **MUST NOT** carry a
  secret value.
- The addon **MUST NOT** add `--auto` (or any CLI permission-bypass flag)
  by default. `--auto` **MAY** be used only when the developer opted into
  autonomy for that plan explicitly (recorded in the plan) **and** the
  delegate runs in an isolated worktree or container; the kit's own
  opt-in remains the only place a bypass flag is spelled.
- `--timeout` **SHOULD** always be set; exit 4 (timeout) and 5 (cancelled)
  are terminal `failed`/`cancelled` outcomes, never retried blindly.
- Exit 3 (CLI not installed / not logged in) is a recorded `failed`
  delegation; the task then runs in the parent session.
- `result_text` is the agent's claim: the delegation result is `asserted`
  until the parent's gate runner observes it (`V7_CONTRACT.md` §3).

## 6. Never-Block Rule

Absence, detection failure, an unknown interface, a ledger refusal or a
failed delegate records the outcome and continues sequentially. Nothing
here blocks `onboard`, `create`, `execute` or `verify`.

## 7. Versioning

This SPEC versions independently. Compatibility is decided by the kit's
interface integer (`1`); the installed release by the pinned tag
(`v0.1.1`), moved only by a parity-tested pack change.

## 8. Validation Checklist

1. `SKILL.md`, `SPEC.md`, `addon.json`, `templates/INTEGRATION.md` exist;
   `addon.json` validates with key `agentkit`, product
   `DailybotHQ/coding-agents-kit` `v0.1.1`, interface 1, transport
   `headless`.
2. Detection is read-only; interface 1 or one warning.
3. Install used the pinned tagged clone; no pipeline anywhere in the text.
4. The registry entry exists only after acceptance.
5. Each delegate: own worktree, recorded launch before start, no `--auto`
   without the recorded opt-in, result gated by the parent.
