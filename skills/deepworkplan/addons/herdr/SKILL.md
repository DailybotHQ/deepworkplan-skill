---
name: deepworkplan-addon-herdr
description: Proposed DeepWorkPlan addon for discovering and coordinating a Herdr agent mesh across machines. The addon ships as an unwired v7 candidate; v6 onboarding, creation, execution, and verification do not activate it. A repository without Herdr stays fully conformant and runs single-agent.
version: "5.5.4"
documentation_url: https://deepworkplan.com
user-invocable: false
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"🕸️","homepage":"https://deepworkplan.com"}}
---

# DeepWorkPlan — Herdr Mesh Addon

Turn a Deep Work Plan into **parallel work across a mesh of coding agents**
on the developer's own machines. Peers may run different providers; the
protocol is text delivered to their panes, so their vendor does not matter.
A repository **without** Herdr runs single-agent exactly as before and stays
fully conformant — **this addon is an environment capability, never a
requirement, never part of the AI-first baseline, and never a conformance
gate.**

**Current release status:** this is a proposed v7 integration. The v6
`create`, `execute`, `onboard`, and `verify` flows do not invoke it. The
protocol below is retained for the v7 implementation and must not be treated
as an active v6 onboarding step.

## Trust boundary and write scope

Read-only discovery may inspect the Herdr catalog and current pane. When v7
activates this addon, consented delegation may append records to the current
plan and send prompts to explicitly selected peers. It MUST NOT write
credentials or host trust files, run remote installers, silently replace
existing files, close another person's pane, or emit telemetry. Changing SSH
host trust requires a separate, explicit developer approval after the key has
been checked against a trusted source.

Placement decision (recorded in `SPEC.md` §1): this lives inside DeepWorkPlan
because its only consumer is an agent executing or coordinating a plan, and
it must stay in lockstep with the plan's autonomy rules. Read
[`protocol.md`](protocol.md) for the normative wire protocol,
[`orchestration.md`](orchestration.md) for delegation rules,
[`movement.md`](movement.md) for the safe-command subset, and
[`templates.md`](templates.md) for the grant/reply stamp templates.

## 0. Install — if Herdr is missing

On activate, check `command -v herdr` and `herdr --version`; record present
or absent.

- **Present** → continue to §1 (detection), then orchestrate.
- **Absent** and the developer wants this addon → give the OFFICIAL install
  paths, show the command, and STOP there until they install it. **Do not
  pipe an installer into a shell. Do not run the installer. Point at the
  docs.** Pick one path; do not mix them:

  | Path | Command (show, do not run) | Updates |
  | --- | --- | --- |
  | Docs | `https://herdr.dev/docs/install/` | — |
  | Homebrew | `brew install herdr` | `brew upgrade herdr` |
  | mise | `mise use -g herdr` | — |
  | Releases | `https://github.com/herdrdev/herdr/releases` | — |

  After they install, verify with `herdr --version` and `herdr status`. A
  missing binary is **not** a conformance failure: the repository keeps
  running single-agent until Herdr is actually on `PATH`.

## 1. Detection — is there a mesh?

Run, in order, and stop at the first failure with the recorded outcome
**"mesh unavailable: <reason>"** — then continue single-agent. Never block a
plan on this:

```bash
herdr --version                       # 1. binary present on PATH?
herdr machine list --json             # 2. machines answered? (JSON array)
herdr pane current                    # 3. THIS session inside a Herdr pane?
```

- Binary missing, or step 2 errors → `mesh unavailable` (surface Herdr's own
  error text verbatim — SSH host keys, ports and catalogs are the
  operator's environment; do not invent fixes inside DWP).
- `[]` or `no agents` is a VALID answer: the mesh is up and empty.
- No pane id for this session (step 3) → this session can send but **cannot
  receive a reply**; say so and continue single-agent. Never pretend a reply
  will arrive.
- Run discovery as the session's own user — catalogs and `known_hosts` are
  per-user; a root shell usually sees an empty mesh.

If the mesh is empty and the plan benefits from peers, see §4 (launch).

## 2. Discovery — list the live mesh

When the person asks for the agents — any phrasing, any language ("list the
Herdr agents", "who is available", "show the mesh") — **run the listing now
and print the live table**. The full
procedure, the table format, the state glossary, and the unreachable
diagnoses are [`listing.md`](listing.md): a first-class flow, not a
description. Quick form:

```bash
herdr machine list --json                                   # enabled machines
herdr --machine <machine_id> agent list                     # per machine
```

Present one row per agent: **machine label, machine id, provider, pane id,
state, title**. `no agents` = the machine answered and nobody is running
there. `unreachable` = the Herdr client could not complete the call — report
Herdr's error text and continue with the machines that answered. A partial
mesh is still the mesh.

**Identity is `(machine_id, pane_id)`.** Human labels and short row numbers
get truncated, renamed, and renumbered when agents appear or disappear: a
row number is valid only for the list just printed — never store it, never
reply to it.

## 3. Sending — the grant is the feature

```bash
herdr --machine <machine_id> agent prompt <pane_id> <body>
```

The body is the **whole instruction**; the receiver's provider does not
matter. A bare prompt makes the receiver draft an answer and wait for its
human — so the sender **appends the reply grant** ([`templates.md`](templates.md)):
permission to answer, an order to answer now, the stamped reply command
carrying **the sender's machine id and pane id**, and a prohibition on
asking a person, drafting-and-waiting, or stopping inside its own pane.
Without the grant, a mesh is a notification system; with it, agents close
the loop alone.

## 4. Launch — an empty mesh is not a dead end

`herdr agent start` runs a supported interactive agent in an existing pane.
Discover the exact flags on the installed version (they vary):

```bash
herdr agent start --help
herdr agent explain          # detection state of a pane
```

To grow the mesh: pick an enabled machine, start the provider the task
needs with `cwd` set to the workspace the task will run in, then re-run
discovery (§2) to learn the new agent's `pane_id`. Record the launch in the
plan like any delegation. If `start` fails or the provider is missing,
record it and continue with the peers you have — launching is an
optimization, never a dependency.

## 5. Orchestration — delegate, record, join on the plan

Full rules: [`orchestration.md`](orchestration.md). Short form:

1. Delegate only **independent** tasks; **one writer per path**.
2. Send a self-contained brief whose prompt already carries the grant.
3. **Record the delegation in the plan before relying on it** — disk is the
   source of truth; a chat reply is a handoff, not a record.
4. **Join on the plan, not on the chat**: when replies are in, reconcile,
   validate, continue. Do not narrate each hop to the human.
5. Prefer idle peers; `done` is free; read a `blocked` peer's title before
   asking it anything.

## 6. Autonomy and escalation

Agents discover peers, delegate, ask peers for facts or reviews, and answer
peers **without asking the human**. Escalate only when: a material decision
cannot be inferred from repo/plan/peer; the action is destructive or public;
a required credential or tool is missing and no peer has it; peers disagree
after one reconciliation attempt; or the mesh is down and the plan cannot
proceed single-agent.

## 7. Safety — the moving-in-Herdr subset

Safe: reading panes, listing machines/agents, sending a granted prompt,
describing workspace/tab labels. **Not safe without an explicit,
plan-recorded delegation of that pane:** closing the human's panes, stealing
focus, renaming machines, killing another agent's session. Details:
[`movement.md`](movement.md).

## 8. Stamps and loop prevention

The stamp token is **`[herdr-mesh]`**. First hop: the sender appends the
grant (which contains the stamp) to the body. Return hop: a body already
carrying the stamp is a reply — mark it as such and instruct the sender not
to answer it; the conversation stops. A new question is a **new ask with a
fresh grant**, never a reply-to-a-reply. The grant and stop-line texts in
[`templates.md`](templates.md) §1–§2 are **normative — use them verbatim,
filling only the sender's machine id and pane id. A mesh message sent
without the grant is a bug in this addon.**

## 9. Wiring into the flows

There is no v6 flow wiring. The proposed v7 hooks for `create`, `execute`,
`onboard`, and `verify` are recorded in `../../spec/V7_ROADMAP.md`. Their
presence here does not authorize v6 to delegate work or offer installation.
Herdr is not part of the AI-first baseline.

## 10. Proposed validation gate

Before v7 enables a hook, confirm the addon files and grant template exist;
check `command -v herdr` and `herdr --version` without installing anything;
record an absent or unreachable mesh and continue single-agent. For a live
mesh, confirm discovery returns a machine ID and pane ID, and that delegation
records stay within the plan. No host trust file is changed by this check.
