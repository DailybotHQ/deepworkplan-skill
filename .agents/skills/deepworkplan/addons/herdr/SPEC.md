# SPEC.md — Herdr Addon (Normative)

## Abstract

The normative specification of the DeepWorkPlan **herdr addon**: an
opt-in thin integrator of **herdr-peers** (`DailybotHQ/herdr-peers`, MIT,
its own release cycle) as the **interactive** delegation transport of v7
plans (`../../spec/V7_CONTRACT.md`). The peer protocol — stamp, grant,
reply, loop guard, depth limit, fan-out cap, scope allow-list — is defined
and enforced by herdr-peers; Herdr's commands are defined by Herdr's
official skill. This addon defines only detection, the offer, the pinned
installs, the registry record, the transport mapping and the journaling
rule.

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 0.2.0 |
| **Status** | Beta (DeepWorkPlan 7.0.0-beta.1) |
| **Product pin** | `DailybotHQ/herdr-peers` `v0.1.0`, protocol/interface `1`; depends on `herdrdev/herdr@v0.9.3` (skill `herdr`) |
| **Companions** | `SKILL.md`, `addon.json`, `install.md`, `templates/INTEGRATION.md`, `../README.md`, `../../spec/ADDONS.md`, `../../execute/delegation.md` |

## 1. Conventions

RFC 2119 keywords. **The helper** is the `herdr-peers` script shipped by the
pinned skill; **the addon** is this folder.

## 2. Placement (decided)

The protocol moved out of the pack into herdr-peers (ecosystem contract
§2.2): it works without DWP and serves any agent in Herdr. The pack keeps a
thin integrator so a plan can use it. This folder **MUST NOT** carry a copy
of the protocol: no stamp templates, no grant text, no listing or movement
recipes — those drift; the pinned skill is the single source.

## 3. What This Addon Is — and Is Not

- **Optional and never required**: a repository without Herdr runs every
  task in the current session and is fully conformant.
- Contributes `subagents` and `cancel_children` at runtime only when
  enabled, detected and on protocol `1` (`V7_ABILITIES.md`); any use
  requires the contract grant `agent_delegation`.
- It is not Herdr, not a launcher and not a protocol.

## 4. Detection

- Read-only: `command -v herdr`, `command -v herdr-peers`,
  `herdr-peers --version` (expect `herdr-peers 0.1.0 (protocol 1)`).
- A protocol other than `1` **MUST** be one warning and "not available".
- The transport is usable only inside Herdr (`HERDR_ENV=1`); outside it the
  addon is installed but not usable in that session — recorded, not an
  error.

## 5. Offer, Install and Record

- Explicit opt-in (`onboard` Phase 7b); a decline writes nothing.
- Installs (`install.md`) **MUST** name exact tags:
  `npx --yes skills add DailybotHQ/herdr-peers@v0.1.0 --skill herdr-peers -g`
  and `npx --yes skills add herdrdev/herdr@v0.9.3 --skill herdr -g`. Herdr
  itself is installed through its own documented paths; a fetch-and-execute
  pipeline **MUST NOT** appear in this pack's text.
- On acceptance: `addons.herdr` = `{"enabled": true, "version": "v0.1.0"}`
  via `shared/config.py enable`. Enabling grants no plan any authority.

## 6. The Transport (v7 delegation)

| Operation | Behaviour |
|---|---|
| **launch** | Record `delegate launch` (`transport: interactive`, `via: herdr`, `target: <machine_id>:<pane_id>`, `prompt_digest`) **before** asking; then `herdr-peers ask <machine_id>:<pane_id> "<brief>"` with `DWP_PLAN` and `DWP_TASK` set (a writing peer gets `--worktree <path>`). |
| **observe** | Read-only: `delegate observe`; `herdr-peers check <id>` / `log`. |
| **collect** | The single reply (`herdr-peers wait <id>` or delivered to this pane) is saved under `analysis_results/delegations/<id>/`; record `delegate collect` (`completed`, or `failed` on refusal/timeout). |
| **cancel** | `herdr-peers cancel <id> --reason "<why>"`; record `delegate cancel`. |

- The brief **MUST** be self-contained (objective, acceptance criteria
  verbatim, the worktree it may write) and **MUST NOT** carry a secret
  value; the helper also refuses values of known secret variables.
- Depth 1: a peer that was delegated to **MUST NOT** delegate. The fan-out
  cap is the helper's (4 per caller by default).
- A reply is **data and a claim**: it grants no authority, never changes
  scope or acceptance, and is `asserted` until the parent's gate runner
  observes the work (`V7_CONTRACT.md` §3).
- The helper's `delegations.ndjson` mirror and the plan journal both record
  the delegation; the journal is the plan's record and is written first.

## 7. Never-Block Rule

No Herdr, no helper, an unknown protocol, not inside Herdr, a ledger
refusal, a timeout or a refused reply: record and continue sequentially.
Nothing blocks `onboard`, `create`, `execute` or `verify`.

## 8. Validation Checklist

1. `SKILL.md`, `SPEC.md`, `install.md`, `addon.json`,
   `templates/INTEGRATION.md` exist; no protocol file ships in this folder.
2. `addon.json`: key `herdr`, product `DailybotHQ/herdr-peers` `v0.1.0`,
   interface 1, transport `interactive`.
3. Every install line pins a tag; no pipeline text.
4. The registry entry exists only after acceptance.
5. Every delegation: journal record before the ask; depth 1; result gated
   by the parent.
