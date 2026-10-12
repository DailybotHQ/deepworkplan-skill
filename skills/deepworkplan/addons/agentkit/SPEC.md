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
| **Version** | 0.2.0 |
| **Status** | Stable — autonomy by default (coding-agents-kit `v0.2.0` and later) |
| **Product pin** | `DailybotHQ/coding-agents-kit` `v0.6.1`, interface `1` |
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
- The addon **SHOULD** report the doctor's `permissions` field (`auto` or
  `ask`), so the developer knows how a delegate will launch before granting
  delegation.

## 4. Offer, Install and Record

- The offer is an explicit opt-in (`onboard` Phase 7b); declining is
  complete and writes nothing.
- The documented install is the pinned tagged clone plus the kit's
  installer:
  `git clone --branch v0.6.1 https://github.com/DailybotHQ/coding-agents-kit` then
  `./coding-agents-kit/install.sh` (Windows: `install.ps1`). A
  fetch-and-execute pipeline **MUST NOT** appear anywhere in this pack's
  text. The addon **MUST NOT** install coding-agent CLIs on its own.
- On acceptance the addon **MUST** record `addons.agentkit` =
  `{"enabled": true, "version": "v0.6.1"}` through `shared/config.py
  enable`. Enabling grants no plan any authority.

## 5. The Transport (v7 delegation)

Each delegate is exactly one `ak run` in exactly one dedicated git
worktree:

| Operation | Behaviour |
|---|---|
| **launch** | Create the worktree on a dedicated branch; record `delegate launch` (prompt digest) **before** starting; start `ak run <kind> @<profile> --cwd <worktree> --timeout <seconds> --output-format json [--ask] -- "<prompt>"` (`--ask` when the plan records the opt-out; always for a read-only delegate, whose `--cwd` is the repository), stdout redirected to the delegation's result file. |
| **observe** | Read-only: `delegate observe` and whether the process is alive. |
| **collect** | Parse the single JSON object; `exit` 0 → `completed`, any other → `failed`; record `delegate collect` with `result_path`. Integration of the worktree diff and the task's gates happen in the parent session. |
| **cancel** | SIGTERM to `ak run` (the kit kills the process tree and exits 5); record `delegate cancel`. |

- The prompt **MUST** carry the task objective and acceptance criteria and
  name the worktree as the only writable location; it **MUST NOT** carry a
  secret value.
- **Permissions are the kit's.** From `v0.2.0` the kit launches every agent
  in autonomy by default: `ak` adds the CLI's own autonomy flag, which
  lives only in the kit's `providers.toml`. The opt-out is `--ask` or
  `AGENTKIT_PERMISSIONS=ask`, set by the developer (in the environment or
  the kit's env file) or inherited from an opted-out session; it always wins — over `--auto` on the same command and over an
  `AGENTKIT_PERMISSIONS=auto` line in the kit's env file. Autonomy is meant
  for disposable or sandboxed environments, such as a dev container.
- The addon **MUST NOT** spell a CLI autonomy flag, and **MUST NOT** pass
  `--auto` (it is the default, so it adds nothing but a way to look past an
  opt-out). It **MUST** pass `--ask` when the plan records the developer's
  opt-out for its delegates, and it **MUST NOT** remove or override an
  inherited `AGENTKIT_PERMISSIONS=ask`. A read-only delegate always gets
  `--ask` (next rule).
- **Read-only intent means ask.** A read-only delegate (research, review,
  analysis — no worktree, `"worktree": null`, `--cwd` is the repository
  itself) **MUST** always be launched with `--ask`, whatever the plan
  records: it runs in the developer's checkout, where autonomy would
  approve any write without a prompt, and the ledger only sees a tree
  change after the fact. Writing delegates keep the kit's autonomy default
  inside their dedicated worktree, and the developer's opt-out still wins
  for them.
- Granting `agent_delegation` on a host (not in a container) accepts
  autonomous delegates confined by their dedicated worktree, which is not a
  sandbox. The addon **MUST** say so when the grant is asked for, and
  offer the opt-out. A delegate in ask mode has no terminal to answer
  prompts, so it may stop at its first permission prompt; `--timeout`
  bounds it.
- `--timeout` **SHOULD** always be set; exit 4 (timeout) and 5 (cancelled)
  are terminal `failed`/`cancelled` outcomes, never retried blindly.
- Exit 3 (CLI not installed / not logged in) is a recorded `failed`
  delegation; the task then runs in the parent session.
- `result_text` is the agent's claim: the delegation result is `asserted`
  until the parent's gate runner observes it (`V7_CONTRACT.md` §3).

## 5.1. Accounts and Lanes (kit `v0.5.0` and later)

- Account choice **MUST** come from the kit: `ak usage --json` and
  `ak pick <kind> [--count N]`, at most once per batch and on request —
  **never** in a loop or on a timer. A lane **MUST** run on an account the
  developer holds; accounts **MUST NOT** be rotated to get past a limit.
- `ak profiles --json` (`profiles-v1`) and `ak pick … --json` (`pick-v1`)
  are read-only inputs; the addon records the chosen profile in the plan's
  lane table and in `delegate launch`, never a credential.
  Its Claude login kind (`file`, `keychain`, `none`, `unknown`; kit
  `v0.5.1`) reports presence only; a `none` login is not
  usable for a lane until the developer logs in.
- `CLAUDE_CODE_OAUTH_TOKEN[_<SUFFIX>]` and every provider key are handled by
  **name** only; the addon **MUST NOT** read, print or forward a value.
- Failover (limit, exit 3, exit 4): exclude the account for the batch
  (`--exclude @p`), re-pick and relaunch **once**; a second failure goes to
  the developer.
- A pane lane **MAY** be launched with `--trust-cwd` for its own folder. The
  addon sends no keystrokes. Claude's per-profile bypass-permissions
  acknowledgement is a one-time developer step when the profile is created;
  no agent answers it (`../../guide/orchestration-at-scale.md` §16.5).

## 5.2. Capacity and Leases (kit `v0.6.0` and later)

- An agent's own capacity **MUST** come from `ak capacity --self --json`
  (`capacity-v1`) through `../../shared/swarm.py capacity`, at task
  boundaries only (`../../guide/swarm.md` §17.3); the kit's cache makes that
  cheap. A missing kit, an older kit, exit 3 or an unrecognized record
  **MUST** be reported as capacity *unknown*, never as *ok*.
- `AGENTKIT_CAPACITY_CAP` **MAY** be used only to lower a reading (drills).
- A lead **SHOULD** lease each lane's account (`ak lease … --owner <addr>`)
  and pick with `--owner`; a Codex profile **MUST NOT** carry two writers.
  Leases grant nothing; they are records.
- Work **MUST** move only within the developer's declared account pool and
  each vendor's terms (`../../spec/AGENT_PROTOCOL.md` §7.5, C7 when it is
  exhausted).

## 6. Never-Block Rule

Absence, detection failure, an unknown interface, a ledger refusal or a
failed delegate records the outcome and continues sequentially. Nothing
here blocks `onboard`, `create`, `execute` or `verify`.

## 7. Versioning

This SPEC versions independently. Compatibility is decided by the kit's
interface integer (`1`); the installed release by the pinned tag
(`v0.6.1`), moved only by a parity-tested pack change. The default
permission posture is behaviour, not interface: the kit carries it in its
minor version (`v0.2.0`), and SPEC 0.2.0 describes it.

## 8. Validation Checklist

1. `SKILL.md`, `SPEC.md`, `addon.json`, `templates/INTEGRATION.md` exist;
   `addon.json` validates with key `agentkit`, product
   `DailybotHQ/coding-agents-kit` `v0.6.1`, interface 1, transport
   `headless`.
2. Detection is read-only; interface 1 or one warning.
3. Install used the pinned tagged clone; no pipeline anywhere in the text.
4. The registry entry exists only after acceptance.
5. Each delegate: recorded launch before start, no autonomy flag spelled
   by the addon, result gated by the parent; a writing delegate in its own
   worktree (`--ask` when the plan records the opt-out), a read-only one
   always with `--ask`.
