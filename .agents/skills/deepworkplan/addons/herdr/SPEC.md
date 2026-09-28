# SPEC.md — Herdr Mesh Addon (normative)

Status: proposed for v7; unwired in v6. RFC 2119 keywords describe the
proposed protocol and do not activate v6 flow hooks.

## 1. Placement decision (recorded, not open)

The Herdr integration lives inside DeepWorkPlan at
`skills/deepworkplan/addons/herdr/` and in no other repository. Reasoning:
AI Diff Reviewer warrants a separate repo because it has a second surface (a
CI Action, a marketplace listing, a prompt that must stay byte-identical to
that Action, and users who run no DWP plan). The Herdr protocol has exactly
one consumer — an agent executing or coordinating a plan — and must stay in
lockstep with the plan autonomy rules; a second repository would drift, and
there is no second surface to justify one. If a non-DWP audience later needs
the protocol, extract `protocol.md` then and leave this addon as the
integrator. The addon is GENERIC: it names `herdr` on PATH (or a detected
wrapper taking the same address) and never a product, launcher, or vendor.

## 2. What this addon is

An **optional environment capability proposed for v7**. It is not a review
gate, not part of the AI-first baseline, and never required for conformance.
The v6 `onboard`, `execute`, `create`, and `verify` flows do not invoke it.
A repository with no Herdr runs single-agent and is fully conformant.

## 3. Identity and addressing

- A machine has a hex id and a human label. The label is NOT an address.
- An agent lives in a pane; the pane id (e.g. `w5:p2`) is stable for that
  conversation.
- The address of an agent is `(machine_id, pane_id)`.
- A short row number from a listing is valid only for that listing. NEVER
  store it; NEVER use it as a reply address.
- `herdr pane current` is how a session learns its own pane. Refuse to ask a
  pane to reply to itself.

## 4. Discovery

MUST run as the session's own user (catalogs and `known_hosts` are
per-user). `machine list` failures are surfaced with Herdr's own error text
(SSH host keys, ports and catalog mounts are the operator's environment);
unreachable machines are reported and skipped — the rest of the mesh
continues. `no agents` is a valid, healthy answer.

## 5. Transport and the reply grant

Transport: `herdr --machine <machine_id> agent prompt <pane_id> <body>`. The
body is the whole instruction. Every delegation body MUST carry the reply
grant (templates.md): authority to answer, an order to answer now, the
stamped reply command with the SENDER's address, and the prohibition set
(no person-asking, no draft-and-wait, no stop-in-own-pane). Return hops —
bodies already containing the stamp — are marked as replies with an
order NOT to answer; the conversation stops. A new question is a new ask
with a fresh grant.

## 6. Delegation discipline

- One writer per path; never delegate files another agent is writing.
- Self-contained briefs: workspace, task, acceptance, grant — the peer needs
  nothing from the orchestrator's context.
- Delegations are recorded in the plan BEFORE the orchestrator relies on
  them; disk is the source of truth, chat replies are handoffs.
- Join on the plan: reconcile, validate, continue. No per-hop narration to
  the human.
- Prefer idle peers; `done` is free; read a `blocked` peer's title first.
- Launching peers (§4 of SKILL.md) is recorded like any delegation and is
  never a dependency: launch failure → continue with available peers.

## 7. Escalation contract

Escalate to the human ONLY when: a material decision cannot be inferred
from the repo, the plan, or a peer; the action is destructive or public
(force-push, deleting shared work, publishing, contacting anyone outside
the mesh, changing credentials); a required credential or tool is missing
and no peer has it; peers disagree after one reconciliation attempt; or the
mesh is down and the plan cannot proceed single-agent. Everything else is
mesh work.

## 8. Safety envelope

Inside Herdr (pane current succeeds): safe = read own pane, list machines
and agents, send granted prompts, read workspace/tab labels. Without an
explicit, plan-recorded delegation of that pane: closing the human's panes,
stealing focus, renaming machines, and killing another agent's session are
FORBIDDEN. A session without a pane id cannot receive replies — it says so
and continues single-agent.

## 9. Never-block rule and write scope

Detection failure, empty mesh, unreachable machines, launch failure: every
one records the outcome and the plan continues single-agent. This addon
ships no binaries, runs no remote installers, writes no secrets into
prompts (grant bodies name addresses and stamps, never credentials), and
touches no files outside the plan's own delegation records and workspaces.
Adding an SSH host key is an operator action that requires separate explicit
approval and verification against a trusted source; it is never part of an
automatic retry.

## 10. Reconcile, don't clobber

The addon never modifies the plan's task files or another agent's
delegation records; it appends its own delegation and reply notes. Edits to
generated views follow the plan's amendment path. A peer's written
artifacts are judged by the same oracles as the orchestrator's own work.

## 11. Proposed validation checklist

- `SKILL.md`, `SPEC.md`, `templates/grant.md`, and the referenced protocol
  companions exist in the installed pack.
- If the binary is present, `herdr --version` succeeds; if absent, record
  `mesh unavailable` and continue single-agent.
- A live mesh returns stable machine and pane IDs. Every sent prompt carries
  the reply grant, and every delegation is recorded under the current plan.
- No credential, SSH trust file, or unrelated workspace file was changed.
