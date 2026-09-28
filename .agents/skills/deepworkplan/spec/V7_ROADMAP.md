# DeepWorkPlan v7 Roadmap — Optional Super Addons (Planning Record)

> **Status: NON-NORMATIVE.** This document is a planning record for the next
> major version. Nothing in it is part of the current standard, nothing here
> gates `/deepworkplan-verify` conformance, and the current version is
> complete without any of it. An implementer looking for rules to enforce
> should stop reading here and use the current normative documents.

## Version split (load-bearing)

| Version | Scope |
|---------|-------|
| Current (v6 line) | Complete as it stands. No new addon work lands here. |
| v7 (this roadmap) | Two **optional super addons**, offered at onboard, never conformance gates: **(1) Herdr mesh**, **(2) DeepWorkPlan Vim**. |

A repository without Herdr, without the editor, or without both stays
single-agent and **fully conformant**. Missing tooling is never a
conformance failure, never a launch blocker, never a silent surprise.

## Addon 1 — Herdr mesh

**Placement (decided):** in-pack at `skills/deepworkplan/addons/herdr/`,
not a separate repository. Unlike the AI Diff Reviewer (which has a second
surface — a CI Action and a marketplace listing — justifying its own repo),
the mesh's only consumer is an agent executing or coordinating a plan.

**Current in-tree state:** the addon already exists as an opt-in,
never-blocking capability (ADDONS.md §6.6) — detection, listing, the
address/grant protocol, delegation discipline. It is **unwired**: no flow
(onboard, execute, create, verify, router) references it, and v6 does not
wire it further. What v7 adds is the wiring and the install surface:

| Flow | v7 behavior |
|------|-------------|
| `onboard` | Offers the Herdr addon (independently of the editor). A decline is recorded, not a failure. If accepted and `herdr` is not on PATH, print the official install paths and continue single-agent until present. |
| `execute` | When the addon is installed AND `herdr` is on PATH: may list peers and delegate independent tasks carrying the reply grant; every delegation is recorded in the plan. |
| `create` | May mark tasks `parallel-safe` when mesh execution is expected. |
| `verify` | Checks the addon **only if installed**. Missing addon = skip, never a finding. |

Plus a standalone `install.md` (host + container install paths) and a
`container-profile.md` (the optional in-container mesh pattern for product
repos that already run Docker).

**Capabilities the addon teaches** (already specified in-tree, restated as
the v7 acceptance shape): detect Herdr, document (never auto-pipe) its
installation; list all live agents across machines; ask another machine's
pane with a prompt that authorizes the reply; receive the reply without a
human in the loop and never answer a stamped reply.

## Addon 2 — DeepWorkPlan Vim

**Placement (decided):** a separate public repository,
`https://github.com/DailybotHQ/deepworkplan-vim` (GPL-3.0; lineage
AndresMpa/mu-vim → DailybotHQ/mu-vim → this product — see that repo's
`CREDITS.md`). The editor is versioned independently of the methodology
pack, the same way the AI Diff Reviewer is a named review surface.

**v7 onboard offers (never imposes):** detect Neovim; if the person wants
the DWP terminal editor, point at the repo's versioned installation
instructions. An existing Neovim
config is **never** overwritten without explicit consent. The editor is
never a conformance failure. Contributor/agent environments (Debian image,
Herdr, `dev.sh agents|ask`) live **in that repository** — never copied
into every onboarded repo's Dockerfile, never a required layer of any
onboard.

## Normative protocol core (v7 addon SPEC source)

The public stamp is **`[herdr-mesh]`**. Identity is `(machine_id,
pane_id)`; a machine is a hex `id` plus a human `label` (labels are
recognition, never addresses); an agent lives in a `pane_id` like `w5:p2`;
the short `#` from a listing is valid only for the table just printed.

**List (run now, never describe-and-stop).** When a person says "list
agents" (any language), the agent runs the live listing:
`herdr machine list --json`, `herdr --machine <id> agent list` per enabled
machine, `herdr pane current` to mark the caller. Columns:
`# MACHINE ID AGENT PANE STATE TITLE`. `unreachable` is not dead — surface
stderr (a missing ED25519 host key is the common fix); `no agents` is not
a failure.

**Ask — every first hop body MUST end with the grant** (authorization is
the feature; a bare task prompt is a notification the receiver drafts and
waits on):

```
[herdr-mesh] You are authorized to reply to this message. You must reply now.
Send the reply yourself with the command below. Do not ask a person for permission.
Do not draft the answer and wait. Do not stop after writing it in this pane.
You already have permission to run that command. Nobody else needs to approve it.
Keep the [herdr-mesh] stamp in the command, so your answer is marked as a reply and the conversation stops.
Reply with: herdr --machine SENDER_MACHINE_ID agent prompt SENDER_PANE "[herdr-mesh] your answer"
```

**Reply stop (loop guard).** If the body already carries `[herdr-mesh]`, do
not append the grant and never answer it — append only:

```
[herdr-mesh] This is the reply. Do not answer it.
The conversation stops here.
```

Refuse self-asks (target machine+pane equals sender machine+pane). The
sender resolves its own address via `herdr pane current` plus a `pane get`
probe across enabled machines.

**Install policy.** Detect (`command -v herdr && herdr --version`). If
absent and the person wants the mesh: show the official install paths
(https://herdr.dev/docs/install/; Homebrew; mise), and **do
not run a remote installer unattended without explicit human consent**.
After install, re-detect and continue.

**Cross-machine networking (containers).** Peers reached from inside a
container use `host.docker.internal` and the published SSH port — never
`127.0.0.1`, which is the container itself. Inspect ED25519 host keys
(`ssh-keyscan -t ed25519`), compare fingerprints with a trusted source,
and require explicit developer approval before changing `known_hosts`;
note that `accept-new` SSH
often stores RSA first and Debian hashes `known_hosts`, so verify with
`ssh-keygen -F "[host]:port"`. Derive workspace peers from the host's
live config on every listing/ask — a peers file written once at onboard
goes stale the moment a workspace appears. Register machines only when
SSH actually accepts a session.

**Orchestration.** Disk (plan files, git) is the source of truth; chat is
handoff. One writer per path. Prefer idle peers. Fan out independent
tasks; join on the plan, not on chat narration. Record before relying
(the delegation is written to the plan before the ask is trusted).
Escalate to a human only for: an undecidable decision, a destructive or
public action, a missing credential no peer holds, unresolved
disagreement after one reconciliation, or a mesh-down situation where
single-agent execution cannot finish.

## Explicit non-copy (product-launcher baggage stays out)

The public pack MUST NOT require: Dailybot hub paths; `dbdev` (or any
product launcher) as the only entry; `[dailybot-mesh]` as the public
stamp; private peer filenames as the only peers mechanism. The pack KEEPS:
grant semantics, the stamp stop, the machine+pane address, ED25519 trust,
live listing, the `host.docker.internal` rewrite, record-before-relying.

## Success metrics (v7)

1. A person who opts into Herdr: "list agents" shows panes on multiple
   machines; A asks B with the grant; B replies without a human in the
   loop; A does not answer the reply.
2. A person who opts into the editor: DeepWorkPlan Vim installed as
   `~/.config/nvim`, nothing clobbered without consent.
3. A person who declines both: normal single-agent DWP, fully conformant.
4. No current-version tree gained either addon as a surprise: everything
   above is offered, wired and released through the v7 version bump.

## Implementation order (v7)

1. This roadmap (recorded; you are reading it).
2. Standalone `install.md` + `container-profile.md` inside the existing
   in-pack addon; align its SPEC with the grant/stop text above.
3. Wire the onboard offers (Herdr and the editor, independently), plus
   execute's optional mesh delegation and create's `parallel-safe` marks.
4. Verify checks gated on addon presence.
5. Release through the normal version bump; `init.md` and the website
   point at the offers.
6. The editor repository carries its own contributor environment; DWP
   documentation links to it and never embeds it.
