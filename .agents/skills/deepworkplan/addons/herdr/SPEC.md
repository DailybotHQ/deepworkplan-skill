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
| **Version** | 0.3.0 |
| **Status** | Stable (DeepWorkPlan 7.0.0) |
| **Product pin** | `DailybotHQ/herdr-peers` `v1.1.0`, protocol/interface `1`; depends on `herdrdev/herdr@v0.9.3` (skill `herdr`) |
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
  `herdr-peers --version` (expect `herdr-peers 1.1.0 (protocol 1)`).
- A protocol other than `1` **MUST** be one warning and "not available".
- The transport is usable only inside Herdr (`HERDR_ENV=1`); outside it the
  addon is installed but not usable in that session — recorded, not an
  error.

## 5. Offer, Install and Record

- Explicit opt-in (`onboard` Phase 7b); a decline writes nothing.
- Installs (`install.md`) **MUST** name exact tags:
  `npx --yes skills add https://github.com/DailybotHQ/herdr-peers/tree/v1.1.0 --skill herdr-peers -g -y`
  and `npx --yes skills add https://github.com/herdrdev/herdr/tree/v0.9.3 --skill herdr -g -y`. Herdr
  itself is installed through its own documented paths; a fetch-and-execute
  pipeline **MUST NOT** appear in this pack's text.
- On acceptance: `addons.herdr` = `{"enabled": true, "version": "v1.1.0"}`
  via `shared/config.py enable`. Enabling grants no plan any authority.

## 6. The Transport (v7 delegation)

| Operation | Behaviour |
|---|---|
| **launch** | Record `delegate launch` (`transport: interactive`, `via: herdr`, `target: <machine_id>:<pane_id>`, `prompt_digest`) **before** asking; then `herdr-peers ask <machine_id>:<pane_id> "<brief>"` with `DWP_PLAN` and `DWP_TASK` set (a writing peer gets `--worktree <path>`). |
| **observe** | Read-only: `delegate observe`; `herdr-peers check <id>` / `log`. |
| **collect** | The single reply (`herdr-peers wait <id>` or delivered to this pane) is saved under `analysis_results/delegations/<id>/`; record `delegate collect` (`completed`, or `failed` on refusal, timeout or an ask closed `unroutable`, with that reason). |
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

## 6.1. Lanes (orchestration at scale)

- A long-lived lane is one peer per repository or workstream, addressed
  `<machine>:<pane>` from a fresh `herdr-peers list`, on the host, in a
  registered dev container or on another machine. Work **MUST** be assigned
  only by the lead; lanes **MAY** ask each other for information and
  coordination. The protocol limits (depth 1, fan-out cap, scope) are
  unchanged at any scale.
- No agent following this addon sends keystrokes to a pane, with one
  exception (`../../guide/orchestration-at-scale.md` §16.5): folder trust
  for a pane the lead launched itself, when `--trust-cwd` was unavailable.
  Every other first-run screen — a permission acknowledgement above all —
  is read, recorded and escalated to the developer.
- The lead **MUST** name a lane's pane in its brief and tell the lane to pass
  `--pane <pane>` on every helper call; a Codex lane cannot learn its pane
  from `HERDR_PANE_ID` (its commands run from a shared per-profile server).
- A Codex lane inside a dev container also needs `HERDR_PEERS_SELF` (the
  container's machine id as the host's catalog saves it) for asks to other
  machines; devcontainer-kit `v0.3.3` and later exports it in the
  container's login shells. With an older kit the lead's brief **MUST** name
  the value.
- Since herdr-peers `v0.2.3`, runtime state (self cache, log, reply copies)
  lives per Herdr server under `$XDG_STATE_HOME/herdr-peers/<server>/`
  (falling back to `~/.local/state/herdr-peers/<server>/`), never in the
  checkout, so a checkout bind-mounted into a container does not share the
  host's state. `herdr-peers log` shows the current server's records;
  `log --all-machines` shows every server's in a shared log. A reply that
  cannot be delivered is recorded as `unroutable` and closes the ask with
  that reason; `wait` accepts only a reply from the peer that was asked.
  During a mixed-version rollout `wait` still accepts a `v0.2.2` reply stamp
  without `from`, records the sender as unverified and warns until that
  peer is upgraded; the lead **SHOULD** upgrade every machine to the pin.
- The lead **SHOULD** set `DWP_PLAN` and `DWP_TASK` so the helper mirrors
  every ask and reply into the plan.

## 6.2. Notices and Leadership (herdr-peers `v0.3.0` and later)

- One-way messages **MUST** be sent as notices (`herdr-peers notify`), never
  as asks; a notice **MUST NOT** be answered, and it grants nothing.
- A lead **SHOULD** claim its plan (`herdr-peers lead claim --plan P
  --succession …`) and change leadership only through `lead handover` or,
  for a deputy, `lead takeover`; lanes address the lead as `lead`. A lead
  notice is accepted only under the fencing rules of `../../guide/swarm.md`
  §17.7; merges, tags and releases are performed only by the current-epoch
  lead.
- A `usage_limit` screen **MUST NOT** be keyed; it triggers a handoff.

## 6.3. Native Debates (herdr-peers `v1.1.0`)

- The native debate sub-skill (`debate.md`) lets a lead run a panel of
  peers for a chosen purpose (decide, research, stress-test, verify,
  generate) through formats such as classic rounds, claim-by-claim
  cross-exam, red team then defenders, a blind fresh-context challenge and
  a replication panel. The lead never votes and **MUST NOT** vote.
- `herdr-peers debate tally`, `claims`, `anon`, `filings` and `panel`, plus
  the sixteen templates under `templates/debate/`, support counting, claim
  ledgers (a quorum, not a verification), anonymization, filing
  completeness and panel proposals. These helpers do not send messages or
  provision agents.
- `debate panel` **MAY** propose agentkit-backed seats, ranked by quota,
  when agentkit `v1.0.1` or later is installed, and recommends it when it is
  absent. Agentkit remains optional, and launching agents still requires
  the human consent defined by herdr-peers.
- `reply` and `notify` retry delivery to a blocked peer (`--wait-blocked`);
  each ask still gets exactly one reply.
- This feature is additive: protocol/interface `1` is unchanged.

## 6.4. Decision Debates (the default decision mode)

With this addon in use, a plan settles each **consequential decision**
through a herdr-peers *decide* debate instead of one agent's judgment. The
method — briefs, rounds, formats, ballots, counting, the lead's contract —
is herdr-peers' own `debate.md`; this section defines only when a plan uses
it and how the plan records it.

1. **Consequential decision.** A decision **is** consequential when all
   hold: at least two viable options lead to materially different
   outcomes; it is hard to reverse, or it shapes several tasks or
   consumers; and nothing in the repository, its docs, the plans or prior
   decisions settles it. Every other decision stays the agent's own record
   (`../../spec/AGENT_PROTOCOL.md` §7.5).
2. **Trigger, in two halves.** *At plan time* a plan **MAY** list a
   debate only when this addon is enabled, `config.py show` resolves
   `decisions.debate` to `auto` (`../../spec/CONFIG.md` §3b), and the
   developer accepts the `agent_delegation` grant for the plan; a plan
   created without the plan-time trigger **MUST NOT** list debates. *At run
   time* a listed debate **MUST NOT** start unless the approved plan lists
   it, the contract grants `agent_delegation`, the session is inside
   Herdr, and `herdr-peers --version` reports `1.1.0` or later on protocol
   `1`.
3. **Planned as a decision task.** `create` turns each consequential
   decision it can foresee into a decision task ordered before its
   consumers, naming the question verbatim, the options, the criteria, the
   shape and the seat cap; the plan's "Decision debates" section lists them
   for approval. That approval is the human consent herdr-peers requires
   before agents are launched; trust mode records it as part of the
   pre-authorization. A debate **MUST NOT** be opened on a question the
   approved plan does not list. A consequential decision that surfaces
   mid-task meets C3 (`../../spec/AGENT_PROTOCOL.md` §7.5): the agent
   escalates it with its investigation and a recommendation, and a debate
   for it needs a refine amendment the developer approves.
4. **Shape.** Quick (3–4 seats, one round and the lead's synthesis) by
   default; Standard only for a decision the plan marks high-stakes; never
   Deep by default. The seat cap is stated in the plan and **MUST NOT** be
   exceeded; more than 4 open asks needs the helper's recorded
   `--fanout N --reason`.
5. **Lead and seats.** The executing agent is the lead and **MUST NOT**
   vote. Each seat is a **read-only** delegation (`worktree` null) recorded
   with `ledger.py delegate launch` before its brief is sent and collected
   after its filing (§6). Depth 1 holds: a seat never delegates.
6. **Deliverable.** `analysis_results/debates/<topic>/DECISION.md`, the
   herdr-peers deliverable with the counted verdict and the dissent, ending
   with one line the plan owns, `decision: <the choice>` (the decision
   task's gate reads that line, never herdr-peers' own format), plus
   the plan's decision record in `PROGRESS.md` "Decisions": the options,
   the choice, why, how to reverse it, the panel's providers and the
   dissent.
7. **Authority.** The verdict is **data and a recommendation**: it grants
   no authority, widens no scope, changes no acceptance criterion and stays
   `asserted`. The decision task closes only on its own gate.
8. **Never block.** When the trigger fails, a seat is refused, the panel
   misses its quorum, or the debate times out, the decision task closes
   with the agent's own decision record naming why the debate did not run
   (`debate: not run — <reason>`, then `decision: <the choice>`). A split verdict on a question that
   changes the plan's outcome is escalated as C3 (irreducible ambiguity)
   with the debate attached as the investigation.

## 7. Never-Block Rule

No Herdr, no helper, an unknown protocol, not inside Herdr, a ledger
refusal, a timeout, a refused reply or an ask closed `unroutable`: record and
continue sequentially.
Nothing blocks `onboard`, `create`, `execute` or `verify`.

## 8. Validation Checklist

1. `SKILL.md`, `SPEC.md`, `install.md`, `addon.json`,
   `templates/INTEGRATION.md` exist; no protocol file ships in this folder.
2. `addon.json`: key `herdr`, product `DailybotHQ/herdr-peers` `v1.1.0`,
   interface 1, transport `interactive`.
3. Every install line pins a tag; no pipeline text.
4. The registry entry exists only after acceptance.
5. Every delegation: journal record before the ask; depth 1; result gated
   by the parent.
6. A decision debate runs only under the §6.4 trigger, within the plan's
   seat cap, with a lead that never votes, and falls back to the agent's
   own decision record without blocking.
