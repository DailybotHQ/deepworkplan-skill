---
name: deepworkplan-addon-agentkit
description: Optional DeepWorkPlan addon that integrates coding-agents-kit (the `ak` command, DailybotHQ/coding-agents-kit pinned at v0.3.0, interface 1) as the headless delegation transport - a thin integrator that detects the kit through `ak doctor --json`, offers it (never imposes it) from onboard Phase 7b, documents the install from a clone of the pinned tag plus the kit's install.sh, records the acceptance in the .dwp/config.json addon registry, and maps a v7 plan's delegation operations (launch, observe, collect, cancel) onto one `ak run` per delegate in a dedicated git worktree. Never required, never a conformance gate. The kit launches agents in autonomy by default and its opt-out (--ask or AGENTKIT_PERMISSIONS=ask) always wins; the pack spells no CLI autonomy flag, never passes --auto, and passes --ask when a plan records the opt-out.
version: "7.1.1"
documentation_url: https://deepworkplan.com/kit/agentkit
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"🧰","homepage":"https://deepworkplan.com/kit/agentkit","requires":{"anyBins":["git"]}}}
---

# DeepWorkPlan — agentkit Addon (headless delegation transport)

Integrate **coding-agents-kit** — one command surface (`ak`) for every
terminal coding agent (claude, codex, cursor, opencode, pi, cline, grok and
their provider variants, multiple accounts through profiles) — as the
**headless** transport a v7 plan may use to delegate a `parallel_safe`
task. This is an **opt-in addon**, never required for a repo to be
AI-first and never a conformance gate: without it every task runs in the
current session exactly as before.

This addon is a **thin integrator**. The kit is its own product
(`https://github.com/DailybotHQ/coding-agents-kit`, MIT, works without
DWP); everything this addon relies on is the kit's frozen **interface 1**
(`ak run`, `ak env`, `ak doctor --json`, the exit codes) at the pinned tag.

| Pin | Value |
|-----|-------|
| Product | `DailybotHQ/coding-agents-kit` |
| Tag | `v0.3.0` (autonomy by default since `v0.2.0`; `classic` and `providers` alias presets) |
| Interface | `1` (`ak doctor --json` → `"interface": 1`) |
| Registry key | `agentkit` (`.dwp/config.json` → `addons.agentkit`) |
| Transport | `headless` — provides `subagents`, `cancel_children`, `model_routing`; requires the `agent_delegation` grant |

## Read these first (all relative inside the skill)

- [`SPEC.md`](SPEC.md) — the normative contract: detection, offer,
  install, the transport mapping, the permission rules.
- [`templates/INTEGRATION.md`](templates/INTEGRATION.md) — reasoning
  guidance for one delegate end to end (worktree, prompt, run, collect).
- `../../execute/delegation.md` — when a plan may delegate at all.

## When this runs

- **`onboard` Phase 7b** offers it as an explicit opt-in when the developer
  wants a plan to hand bounded tasks to other coding agents.
- **`execute`** uses it only through `delegation.md`, only on a v7 plan whose
  contract grants `agent_delegation`, only for a `parallel_safe` task (or a
  read-only delegate), and only when `resources.py abilities` shows
  `addon:agentkit` as a `subagents` source.
- Direct invocation, to install or check the kit.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`. The
write scope is bounded:

- **Before consent: read-only.** Detection is `command -v ak` and
  `ak doctor --json` (key **names** only, never values).
- **Writes (only after explicit acceptance):** the kit install through its
  own pinned installer, the `addons.agentkit` registry entry, and — during a
  delegation — a dedicated git worktree for the delegate plus the collected
  result under the plan's `analysis_results/delegations/<id>/`.
- **It MUST NOT:** spell a CLI autonomy flag (they stay in the kit's
  `providers.toml`) or pass `--auto` (autonomy is already the kit's
  default) — `--ask`, the opt-out, is the one flag it passes, and only when
  the plan records it; drop or override an `--ask` /
  `AGENTKIT_PERMISSIONS=ask` opt-out; read, print or write any provider key
  value; let a delegate write outside its worktree; install a coding-agent
  CLI unasked (`ak install` is the developer's call); run a delegate the
  ledger refused; or treat a delegate's result as evidence.

## Permissions (the kit's, never the pack's)

Since `v0.2.0` the kit launches every agent in **autonomy by default**: `ak`
adds the CLI's own autonomy flag, kept only in the kit's `providers.toml`.
The **opt-out always wins**: `--ask` on the command, or
`AGENTKIT_PERMISSIONS=ask` set by the developer (in the environment or the
kit's env file) or inherited from an opted-out session, suppresses the flag even when the same command says `--auto` and
even when the kit's env file says `AGENTKIT_PERMISSIONS=auto`. Autonomy is
meant for disposable or sandboxed environments, such as a dev container.

For delegation this means: a plan that grants `agent_delegation` on a host
accepts autonomous delegates confined to their own worktree, which is not a
sandbox. Say so when asking for the grant and offer the opt-out. When the
plan records it, launch each delegate with `ak run --ask …`; a delegate in
ask mode has no terminal, so it may stop at its first prompt, and
`--timeout` bounds it.

## The flow

### Step 0 — Detect (read-only)

`command -v ak` → `ak doctor --json` → read `interface` (must be `1`;
anything else is one warning and "not available"), `permissions` (`auto`
or `ask` — how delegates will launch), the installed kinds and whether each
is logged in (file presence only), and the profile names. No state installs
anything.

### Step 1 — Offer (never impose)

Explain what it adds — a plan may hand a bounded `parallel_safe` task to
another coding agent, in its own worktree, and verify the result with its
own gates — and what it costs: a machine-level install, provider accounts
you already have, per-plan consent (`agent_delegation`), and agents that run
in autonomy unless you opt out (`--ask` / `AGENTKIT_PERMISSIONS=ask`).
Declining is a complete answer.

### Step 2 — Install (pinned; point-don't-run by default)

```
git clone --branch v0.3.0 https://github.com/DailybotHQ/coding-agents-kit
./coding-agents-kit/install.sh
```

(Windows: the same tagged clone, then `.\coding-agents-kit\install.ps1`.)
The installer touches no network, installs no CLI and never overwrites the
env file. Run it yourself only interactively and with explicit acceptance;
re-detect afterwards.

### Step 3 — Record

`python3 ../../shared/config.py enable agentkit --version v0.3.0 --repo <repo>`.
Delegation still needs each plan's contract to grant `agent_delegation` —
enabling the addon grants nothing.

### Step 4 — Transport (during execute)

One delegate = one `ak run` in one dedicated worktree
(`templates/INTEGRATION.md`):

| Operation | Mapping |
|-----------|---------|
| launch | `git worktree add <wt> -b dwp/<plan>/<delegation_id>`; record `ledger.py delegate launch` (with `prompt_digest`); start `ak run <kind> [@profile] --cwd <wt> --timeout <s> --output-format json [--ask] -- "<prompt>"` in the background, stdout to the result file (`--ask` only when the plan records the opt-out) |
| observe | `ledger.py delegate observe`; the background process is alive or has exited |
| collect | on exit read the one JSON object (`exit` 0 → `completed`, otherwise `failed`); `ledger.py delegate collect` with `result_path`; integrate the worktree's diff; run the task's gates here |
| cancel | send SIGTERM to `ak run` (the kit kills the whole process tree, exit 5); `ledger.py delegate cancel` |

## Failure-mode guardrails

- **Never required, never blocking.** Not installed, not logged in, unknown
  interface, refused by the ledger: run the task in this session.
- **The result is a claim.** `result_text` is what the agent said; only the
  plan's own gate runner turns the work into `observed` evidence.
- **Secrets stay names.** Provider keys are environment variable names; the
  kit never prints values and neither does this addon.

## Validation checklist (component 4 — mirrored from SPEC §8)

1. `SKILL.md`, `SPEC.md`, `addon.json`, `templates/INTEGRATION.md` exist;
   the descriptor pins `DailybotHQ/coding-agents-kit` `v0.3.0`, interface 1,
   transport `headless`.
2. Detection is read-only and reports `interface` 1, or one warning.
3. Install used the pinned tagged clone + `install.sh`; nothing piped.
4. The registry entry exists only after acceptance.
5. Every delegate ran in its own worktree, with no autonomy flag spelled
   by the addon (`--ask` when the plan records the opt-out), and its result
   was gated here.
