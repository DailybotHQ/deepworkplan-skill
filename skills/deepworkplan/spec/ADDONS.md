# ADDONS.md — Opt-In Addon Mechanism

> **Version scope:** This is a retained v5.0.0 base document. The current
> v6 standard also requires the applicable `V6_*.md` extensions indexed in
> [README.md](README.md). Existing v5 plans keep this document’s recorded rules.

## Abstract

This document defines the **opt-in addon mechanism** for the DeepWorkPlan
methodology: a way to layer optional, self-contained capabilities onto a repository
during onboarding **without** making them part of the AI-first baseline. An addon is
**never required** for conformance; it is offered, accepted or declined, and — when
accepted — **reconciles** with the repo's existing setup rather than clobbering it.
One component is the declared exception: the **AI Diff Reviewer local review**
(§6.5) is part of the **required baseline** since standard 2.3.0 — the `onboard`
flow installs it by default and the Final Review's security pass runs it. Only
its CI surface (Flow B) remains optional.

This is a **concept + pointer** document. It defines the addon contract, discovery,
and the reconcile-don't-clobber rule, and names the **shipping addons**
(devcontainer support, Dailybot integration, dependency upgrade, design system
and the AI Diff Reviewer), pointing to their full
implementations. It does **not** contain any addon's implementation.

---

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 2.1.0 |
| **Status** | Stable |
| **Supersedes** | (net-new in v2; no v1 equivalent) |
| **Companions** | `DOCUMENTATION_STANDARD.md`, `DWP_SPECIFICATION.md`, `AGENT_PROTOCOL.md`, `ARCHETYPES.md` |
| **License** | MIT |

> **Divergence from v1.** v1 had **no addon concept** anywhere in the framework.
> The addon mechanism is **net-new in v2**, introduced to keep the core
> baseline lean while allowing optional capabilities (devcontainer support,
> then Dailybot integration) to be layered in. In 7.0.0 it gained the addon
> registry ([`CONFIG.md`](CONFIG.md)), descriptors (§7) and addon-provided
> abilities ([`V7_ABILITIES.md`](V7_ABILITIES.md)).

---

## 1. Conventions

The RFC 2119 keywords (**MUST**, **MUST NOT**, **SHOULD**, **MAY**, **OPTIONAL**,
etc.) are interpreted as in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 2. What an Addon Is

- An **addon** is a self-contained capability that the onboarding flow
  **MAY** layer onto a repository. Most addons are **optional**; the declared
  exception is the **AI Diff Reviewer local review** (§6.5), which is part of
  the required baseline since standard 2.3.0.
- An **optional** addon **MUST NOT** be required by the AI-first baseline
  (`DOCUMENTATION_STANDARD.md` §§2–7). A repository **MUST** be fully conformant
  with **zero optional addons** installed (the local-review baseline component
  is not an optional addon).
- Addons are **archetype-agnostic** (`ARCHETYPES.md`): one **MAY** be layered onto
  either an individual repo or an orchestrator hub.
- Addons live under the DWP skill at `skills/deepworkplan/addons/{addon-name}/`.

---

## 3. The Addon Contract

Each addon **MUST** ship all four of the following components:

| Component | Requirement | Purpose |
|-----------|-------------|---------|
| **Spec** | **MUST** | A normative description (RFC-2119) of what the addon provides and what "conformant to this addon" means. |
| **Reasoning templates** | **MUST** | Templates the agent fills by **reasoning** about the target repo's stack (not copy-paste), consistent with the reason-per-repo rule (`DOCUMENTATION_STANDARD.md` §7). |
| **Onboarding hook** | **MUST** | The integration point that lets the `onboard` flow offer the addon as an **optional** step. |
| **Validation step** | **MUST** | A check that confirms the addon was applied correctly (files exist, settings present, smoke check passes). |

An addon **MAY** additionally ship examples, per-stack presets, or migration notes.

---

## 4. Discovery by the `onboard` Flow

- The onboarding flow **MUST** discover available addons by enumerating
  `skills/deepworkplan/addons/`.
- For each discovered addon, the flow **MUST** present it to the user as an
  **opt-in** step and **MUST NOT** apply it without explicit acceptance — with
  two declared exceptions: the **AI Diff Reviewer local review** (§6.5, a
  required baseline component installed under the Phase 0 onboarding consent)
  and the **dependency-upgrade addon's near-default tier** (§6.3), whose
  **inert** `/lib-upgrade` delegator installs under that same onboarding
  consent **unless explicitly declined** while every upgrade stays explicit,
  gated work.
- If the user declines an addon, the flow **MUST** skip it and **MUST** still
  produce a baseline-conformant repository.
- When an addon is accepted, the flow **MUST** run the addon's onboarding hook and,
  on completion, the addon's validation step.

---

## 5. Reconcile, Don't Clobber

- When an accepted addon detects an **existing** setup it would touch (e.g. an
  existing `.devcontainer/` or `docker/`), it **MUST reconcile** with that setup —
  preserving working configuration and additively bringing it toward the addon
  standard.
- An addon **MUST NOT** blindly overwrite or delete existing files. Per
  `AGENT_PROTOCOL.md`, any destructive change to an existing file **MUST** be
  approved by the user first.
- The reconcile result **SHOULD** preserve repo-specific values that already work
  (ports, network names, environment flags, project identity) and **MUST** record
  what it changed.

---

## 6. Shipping Addons

Eight addon folders ship: seven are **optional** and **never
required**, and one is the local-review baseline. A repository is fully
conformant with **zero optional addons** installed. Of the seven optional
addons, the
**dependency-upgrade** addon (§6.3) is **near-default**: offered for every repo
with declared dependencies, with its **inert** `/lib-upgrade` delegator
installed under the onboarding consent **unless explicitly declined** (an
install runs no upgrade). The fifth, the
**AI Diff Reviewer** (§6.5), is a **required baseline component in its local
form**; only its CI surface is optional.

### 6.1 Devcontainer Support (first addon — thin integrator of devcontainer-kit)

- An optional addon at `skills/deepworkplan/addons/devcontainer/` that gives a
  repository a reproducible dev container through **devcontainer-kit**
  (`dck`; `https://github.com/DailybotHQ/devcontainer-kit`, MIT, its own
  release cycle) pinned at `v0.2.0` (interface `2`). The kit owns the
  Dockerfile template and its render (`dck init`, which reconciles and never
  clobbers), the pinned images and tools, the entrypoint, the launcher, SSH
  agent forwarding, Herdr registration and the `dck-dockerfile` skill; the
  addon owns detection, the offer, the stack → options reasoning, the
  registry record and validation.
- **Per-repository layout, no shared base image (devcontainer-kit
  `v0.2.0`):** the render produces `.devcontainer/devcontainer.json`,
  `docker/local/<service>/Dockerfile` (plus its entrypoint),
  `docker/local/docker-compose.yaml` and `dev.sh`. The Dockerfile starts from
  the official runtime image pinned by digest; the kit's GHCR base image is
  not required. The addon offers the skill through
  `npx --yes skills add https://github.com/DailybotHQ/devcontainer-kit/tree/v0.2.0 --skill dck-dockerfile -y`
  (repo-local), and the pack keeps no copy of the template.
- **Vendor-neutral (7.0.0):** the 1.x in-pack templates and their
  company-specific requirements are retired; no network, volume, CLI or
  profile file of any one organization is required. The Dailybot CLI layer
  appears only when the `dailybot` addon asks for it.
- Security defaults are the kit's and are never weakened by the addon:
  loopback-only ports, no privileged options or Docker socket, no host
  `~/.ssh` or `~/.gitconfig` mounts, agent forwarding instead of key copies,
  `0600` gitignored `.env` files.
- Full contract: [`SKILL.md`](../addons/devcontainer/SKILL.md),
  [`SPEC.md`](../addons/devcontainer/SPEC.md), `templates/INTEGRATION.md`.
- It is **never required**; each child DWP **MAY** include one optional task
  to adopt it and **MUST** skip it if declined.

### 6.2 Dailybot Integration (second addon)

- **Dailybot integration** is the **second** addon. Its full normative content
  (spec, reasoning template, onboarding hook, validation step) **MUST** live at:

  ```
  skills/deepworkplan/addons/dailybot/
  ```

- Scope: an **opt-in** connection to the developer's **Dailybot team**. When
  accepted, it offers (never forces) install of the **Dailybot agent skill**
  (`npx --yes skills add https://github.com/DailybotHQ/agent-skill/tree/v3.23.3 --skill dailybot -y`,
  currently **3.23.3**; or OpenClaw `openclaw skills install dailybot`) and/or
  the **Dailybot CLI** (`dailybot-cli >= 3.9.0`,
  via pip, Homebrew, or the Dailybot skill's SHA-256-verified installer flow —
  never a one-line remote-installer pipe); **defers all authentication** to the
  Dailybot skill's own
  consent flow (`shared/auth.md` — `dailybot login` or `DAILYBOT_API_KEY`); wires
  **four lifecycle events** (kickoff, significant task, blocked, completion) as
  **optional, best-effort, never-blocking** progress reports via the dailybot
  `report` sub-skill; and **MAY** commit deterministic hook enforcement
  (`dailybot hook` lifecycle hooks, CLI >= 3.9.0). The paired Dailybot skill
  exposes 17 capabilities (chat, check-ins, forms authoring, ask AI, per-repo API keys, and more);
  this addon wires only **report** into DWP execution.
- **Vendor-neutral guardrail:** the core DeepWorkPlan methodology has **zero**
  Dailybot dependency. This addon **MUST NOT** be auto-installed for everyone —
  the `onboard` flow recommends it only when the developer/team already uses
  Dailybot, and a repo with zero optional addons is fully conformant.
- The full implementation lives at
  `skills/deepworkplan/addons/dailybot/` — see its
  [`SKILL.md`](../addons/dailybot/SKILL.md)
  (onboarding hook), [`SPEC.md`](../addons/dailybot/SPEC.md)
  (RFC-2119 contract: opt-in install, deferred auth, optional reporting,
  never-block rule, vendor-neutral guardrail, validation), and
  `templates/INTEGRATION.md` (reasoning aid).

### 6.3 Dependency Upgrade (third addon)

- **Dependency upgrade** is the **third** addon. Its full normative content (spec,
  reasoning templates, onboarding hook, validation step, the `/lib-upgrade`
  delegator template) **MUST** live at:

  ```
  skills/deepworkplan/addons/dependency-upgrade/
  ```

- Scope: **package-manager agnostic**, **near-default** dependency upgrades.
  `onboard` **MUST** offer the addon for every repo with **declared
  dependencies** (any manifest or lockfile), and the `/lib-upgrade` delegator
  installs into the repo's `.agents/commands/` under the onboarding consent
  **unless explicitly declined** — the delegator is **inert**: installing it
  runs no upgrade, and an upgrade always runs as explicit, gated work. When
  invoked, the addon detects the repo's **real** package manager (npm/pnpm/yarn
  + ncu, pip/poetry/uv, cargo, go mod, bundler, composer, …), classifies
  upgrades by semver, upgrades in **safe batches**, runs the repo's **real**
  validation gate after each batch, **reverts** a failing batch, and
  summarizes. A declined offer installs **no** command and leaves a
  baseline-conformant repo.
- The full implementation lives at
  `skills/deepworkplan/addons/dependency-upgrade/` — see its
  [`SKILL.md`](../addons/dependency-upgrade/SKILL.md) (onboarding hook),
  [`SPEC.md`](../addons/dependency-upgrade/SPEC.md) (RFC-2119 contract: detection,
  semver classification, batched upgrade, validate-after-each-batch gate,
  revert-on-failure, reconcile-don't-clobber, validation), and `templates/`.

### 6.4 Design System (fourth addon)

- **Design system** is the **fourth** addon. Its full normative content (spec,
  reasoning templates, onboarding hook, validation step) **MUST** live at:

  ```
  skills/deepworkplan/addons/design-system/
  ```

- Scope: an **interface-surface-scoped**, **opt-in** capability that gives a repo a
  **`DESIGN.md`** — placed at **`docs/DESIGN.md`** alongside the repo's other specs
  (root only if the repo has no `docs/` tree) and **indexed from `AGENTS.md`** — a
  Markdown design-system file any coding agent reads to generate interface output
  consistent with the repo's **own** conventions. It covers three **profiles**,
  detected independently from real files and stacked into the same single file:
  **visual-ui** (rendered web/mobile/desktop UI), **cli-output** (styled terminal
  output: semantic colors, panels, spinners, prompts, TTY/`NO_COLOR` degradation),
  and **conversational** (chat/email messaging: voice & register, message anatomy,
  per-platform rendering). When accepted, it **reasons about the repo's actual
  design source** (CSS custom properties, a Tailwind config, token files, component
  styles — or a CLI display/theme module, or message-composition helpers) — **never**
  copying a brand file — documents each accepted profile's canonical sections,
  checks per-profile integrity (**WCAG AA** contrast; color never the sole carrier
  of meaning; plain-text fallbacks; token references resolve), and reconciles an
  existing `DESIGN.md` instead of clobbering it. A detected interface surface
  makes the evaluation and offer **mandatory** — never skipped, with a clear
  recommendation and the recorded detection rationale (even for an ambiguous
  signal) — while every detected profile still requires **explicit acceptance
  in both guided and trust modes** (addon SPEC §3.5). Visual UI is strongly
  recommended; CLI and conversational profiles are recommended. No
  design-system profile is auto-applied. When no interface surface of any kind
  is present (pure library, headless service, infra-only) the addon is **not**
  offered. It remains **never required** — a repo with zero optional addons is fully conformant.
- **Distinct from per-feature design docs:** this addon provides a **repo-level,
  persistent** design-system file; it is **not** a per-feature technical design
  document (the "requirements → design → tasks" `design.md` of tool-bound
  spec-driven workflows). DeepWorkPlan deliberately ships **no** separate
  per-feature design-doc archetype — a plan's README (Goal + Context), each task's
  Context and **Acceptance Criteria**, and the **validation gates** already fulfill
  that role; this addon fills the one gap that role does not cover: durable,
  repo-native **UI** design context.
- The full implementation lives at
  `skills/deepworkplan/addons/design-system/` — see its
  [`SKILL.md`](../addons/design-system/SKILL.md) (onboarding hook),
  [`SPEC.md`](../addons/design-system/SPEC.md) (RFC-2119 contract: frontend-scope
  gate, canonical sections, reason-don't-copy, reconcile-don't-clobber,
  accessibility & token integrity, pragmatic-reference posture, validation), and
  `templates/` (the `DESIGN.md` skeleton, per-stack presets, agent prompt guide).

### 6.5 AI Diff Reviewer (fifth addon — required local review, optional CI surface)

- **AI Diff Reviewer** is the **fifth** addon and the one declared exception to
  the opt-in rule. Its full normative content (spec, reasoning template,
  onboarding hook, validation step) **MUST** live at:

  ```
  skills/deepworkplan/addons/ai-diff-reviewer/
  ```

- **Required local review (baseline since standard 2.3.0).** The `onboard` flow
  **MUST** install the vendored coding-agent skill
  (`npx --yes skills add https://github.com/DailybotHQ/ai-diff-reviewer/tree/v3.3.0 --skill ai-diff-reviewer -y`
  — **tag-pinned**, both `--yes` and `-y` required) and bootstrap a
  repo-tailored extension file (`.review/extension.md`, via the upstream
  `generate-extension` sub-skill) as part of the baseline scaffolding
  (Phase 7a), under the same consent that covers the rest of the onboarding.
  A targeted harness upgrade reconciles the same two pieces when they are
  missing. The security pass of the mandatory DWP **Final Review** **MUST** run
  the upstream parent default flow ("Review my current branch") as a
  local-review pass and append its output to
  `analysis_results/SECURITY_REVIEW.md`; **verified** `critical` findings from a
  completed pass block completion until fixed or explicitly accepted (v3
  BC-07 — unverified critical claims arrive as annotated warnings, and an
  `incomplete`/`timeout` review is not a clean pass, BC-04). The local review
  runs through the developer's own coding agent — no CI provider, no secret,
  no external service.
- **Optional CI surface (Flow B).** Installing the CI Action
  (`.github/workflows/pr-review.yml`) stays an **explicit opt-in**: the addon
  offers it, never installs it unrequested, never defaults to it, and defers
  the workflow authoring to the upstream `setup` sub-skill (never inventing
  provider secrets). In Flow B it also surfaces the `apply-review` / `address-review`
  companions as optional developer-invoked conveniences during `execute`
  (never plan tasks; `address-review`, new in v3.1.1, commits and pushes).
- **Honest degradation, never a silent skip.** When the vendored skill or the
  extension file is missing at execution time, the security pass records a
  `local reviewer not installed` finding and names it in the completion report.
  Installation belongs to onboarding or an explicit addon invocation; Final
  Review never surprise-bootstraps it. An
  invocation error of a review that could start follows the never-block rule
  (warn once, record, continue). The conformance checker reports a missing
  local reviewer as a **failure** for a repository declaring standard 2.3.0 or
  newer and as a harness-version **finding** for a legacy repository. A
  developer **MAY** decline the reviewer; the decline is recorded as a declared
  exception in `AGENTS.md` and the repository is reported as non-conformant on
  that point until the reviewer is installed.
- **Vendor-neutral guardrail (narrowed, still binding).** No DWP flow — create,
  execute, refine, resume, status, verify or onboard — **MAY** require a
  commercial service, a CI provider or a provider secret. The required
  component is an MIT-licensed, tag-pinned skill installed through the
  checksummed `skills` CLI and executed by the agent itself.
- The full implementation lives at
  `skills/deepworkplan/addons/ai-diff-reviewer/` — see its
  [`SKILL.md`](../addons/ai-diff-reviewer/SKILL.md)
  (onboarding hook), [`SPEC.md`](../addons/ai-diff-reviewer/SPEC.md)
  (RFC-2119 contract: required local review, optional CI surface, deferred
  install/auth/wizard, security-pass wiring, optional `apply-review`
  companion, never-block rule for invocation, validation), and
  `templates/INTEGRATION.md` (reasoning aid).

> This `ADDONS.md` is the concept + pointer; it **MUST NOT** be treated as any
> addon's implementation.

---


### 6.6 Herdr (sixth addon — interactive delegation transport, thin integrator)

An optional addon integrating **herdr-peers** (`DailybotHQ/herdr-peers`,
MIT, its own release cycle) pinned at `v0.1.0` (protocol/interface `1`), as
the **interactive** transport of v7 delegation
([`V7_CONTRACT.md`](V7_CONTRACT.md)): one `herdr-peers ask` to a peer agent
in a [Herdr](https://herdr.dev) pane on any reachable machine, recorded in
the plan journal before the reply is relied on, the reply asserted until
the plan's own gates observe the work. `onboard` Phase 7b offers it as an
**explicit opt-in**; installs are the pinned skills
(`herdr-peers@v0.1.0`, Herdr's official `herdr@v0.9.3`).

Placement decision (revised for 7.0.0): the peer protocol — stamp, grant,
reply, loop guard, depth limit 1, fan-out cap, scope — moved out of the
pack into herdr-peers, which works without DWP; this folder is the
DWP-side integration only and carries **no copy** of it. It is **never
required**: a repository without Herdr runs every task in the current
session and stays fully conformant. Full contract:
[`SKILL.md`](../addons/herdr/SKILL.md), [`SPEC.md`](../addons/herdr/SPEC.md),
`install.md`, `templates/INTEGRATION.md`.

### 6.7 DeepWorkPlan Vim (seventh addon — optional terminal editor, thin integrator)

An optional addon offering **DeepWorkPlan Vim** — the terminal editor for
Deep Work Plan (Neovim 0.12+) — as a machine-level install for the person
behind the repo, never a repo requirement. The addon detects Neovim,
presents the editor strictly as an offer, guides the documented install
paths, and validates the installed surface; an existing Neovim config is
**never** overwritten without explicit consent (non-interactive installs
onto an existing config abort with instructions; backups go to
`~/.config/previous-deepworkplan-vim`). The editor is **never required**
and never a conformance gate: a repository without it stays fully
conformant.

Placement decision (recorded per the addon contract): the **editor itself**
lives in its own public repository
(`https://github.com/DailybotHQ/deepworkplan-vim`, GPL-3.0, versioned
independently of the pack); this folder is the DWP-side integration
contract only, a **thin integrator** pinned to the product tag
`deepworkplan-vim@v0.5.1`: detection, feature claims and the install steps
are read from the product's machine-readable surface (`addon/surface.json`,
interface `1`); an unknown interface major is one warning and "not
available", never an error. `onboard` Phase 7b offers it as an **explicit
opt-in**; no other flow invokes it. Two routes: the full editor (available
now) and the `deepworkplan.nvim` plugin (v7.1, not shipped — never offered
for install before it exists). The full
implementation lives at `skills/deepworkplan/addons/vim/` — see its
[`SKILL.md`](../addons/vim/SKILL.md) (detection + offer hook),
[`SPEC.md`](../addons/vim/SPEC.md) (RFC-2119 contract: consent gate,
install paths, validation), and `templates/INTEGRATION.md` (reasoning
template).

### 6.8 agentkit (eighth addon — headless delegation transport, thin integrator)

An optional addon integrating **coding-agents-kit** (`ak`;
`https://github.com/DailybotHQ/coding-agents-kit`, MIT, its own release
cycle) pinned at `v0.3.0` (interface `1`), as the **headless** transport of
v7 delegation ([`V7_CONTRACT.md`](V7_CONTRACT.md)): one `ak run` per
delegate, in a dedicated git worktree, recorded through `ledger.py
delegate`, its result asserted until the plan's own gates observe it.
`onboard` Phase 7b offers it as an **explicit opt-in**; the install is the
pinned tagged clone plus the kit's `install.sh`. Permissions are the
kit's: it launches agents in **autonomy by default**, and its opt-out —
`--ask` or `AGENTKIT_PERMISSIONS=ask`, set or inherited — always wins, even
over `--auto` and over an `auto` line in the kit's env file. The pack spells
no CLI permission flag, never passes `--auto`, passes `--ask` when a plan
records the opt-out, and never drops an inherited one; in short, the opt-out
always wins.
It is **never required**: without it every task runs in the current
session. Full contract: [`SKILL.md`](../addons/agentkit/SKILL.md),
[`SPEC.md`](../addons/agentkit/SPEC.md), `templates/INTEGRATION.md`.

## 7. Addon Descriptors (`addon.json`)

Every in-pack addon **MUST** ship `addons/<key>/addon.json`, a closed JSON
object published as
[`schema/addon-descriptor-v1.schema.json`](schema/addon-descriptor-v1.schema.json)
(`https://deepworkplan.com/schema/addon-descriptor/v1.json`) and validated
at runtime by `shared/config.py` (`descriptor_errors`; `config.py
descriptors` audits the whole set). Its `key` **MUST** equal the directory
name, which is also the addon's registry key in `.dwp/config.json`
([`CONFIG.md`](CONFIG.md) §3).

| Field | Meaning |
|---|---|
| `schema` | the descriptor schema URL (const) |
| `key` | the directory name |
| `product` | optional — the separate product a thin integrator pins: `repo` (`owner/name`), `tag` (exact `vX.Y.Z[-pre]`, never a branch or floating version), `interface` (integer major, when the product publishes one) |
| `detect` | read-only presence check: exactly one of `command` (an argv line with no shell metacharacters, run **without a shell**, bounded by a timeout; exit 0 = present) or `paths` (present when at least one listed file exists; repo-relative or `~/`-prefixed); optional `interface_from` (`json:<field>`, `regex:<pattern>`, `file-json:<path>#<field>`); optional `legacy_paths` beside `paths` — files that all exist when an older release is installed **without** its interface surface: that state is reported as "installed without surface" with one warning, never as absent (F-16) |
| `provides_abilities` | host abilities (the closed v6 set) the addon contributes at runtime **only** when enabled and detected with a compatible interface (`V7_ABILITIES.md`) |
| `requires_grants` | contract permissions its use requires (the closed v6 capability set) |
| `transport` | delegation addons only: `headless` or `interactive`; a transport addon **MUST** provide `subagents` and require `agent_delegation` |

The shipped set:

| key | product (pinned) | provides_abilities | requires_grants | transport |
|---|---|---|---|---|
| `agentkit` | `DailybotHQ/coding-agents-kit` `v0.3.0`, interface 1 | `subagents`, `cancel_children`, `model_routing` | `agent_delegation` | `headless` |
| `ai-diff-reviewer` | `DailybotHQ/ai-diff-reviewer` `v3.3.0` | — | — | — |
| `dailybot` | `DailybotHQ/agent-skill` `v3.23.3` | `telemetry` (reporting only, consent-gated) | — | — |
| `dependency-upgrade` | in-pack only | — | — | — |
| `design-system` | in-pack only | — | — | — |
| `devcontainer` | `DailybotHQ/devcontainer-kit` `v0.2.0`, interface 2 | — | — | — |
| `herdr` | `DailybotHQ/herdr-peers` `v0.1.0`, interface 1 | `subagents`, `cancel_children` | `agent_delegation` | `interactive` |
| `vim` | `DailybotHQ/deepworkplan-vim` `v0.5.1`, interface 1 | — | — | — |

A descriptor is **data**: the pack executes nothing it names except its
`detect.command`, and only for an addon the registry enables. A product
reporting an interface major other than the descriptor's is treated as
**not available** with one warning — never an error of the plan or the
repository. Descriptors never gate conformance: an addon whose descriptor
is absent or invalid contributes nothing, and the methodology runs
unchanged (`tests/standalone-methodology.bats`).

## 8. References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)
- `DOCUMENTATION_STANDARD.md` (§7 reason-per-repo), `AGENT_PROTOCOL.md` (approval gates), `ARCHETYPES.md`, `DWP_SPECIFICATION.md`
- `CONFIG.md` (the addon registry), `V7_ABILITIES.md` (addon-provided abilities), `V7_CONTRACT.md` (delegation), `V7_ROADMAP.md` (non-normative)
- Devcontainer addon implementation (`skills/deepworkplan/addons/devcontainer/`)
- Dailybot addon implementation (`skills/deepworkplan/addons/dailybot/`)
- Dependency-upgrade addon implementation (`skills/deepworkplan/addons/dependency-upgrade/`)
- Design-system addon implementation (`skills/deepworkplan/addons/design-system/`)
- AI Diff Reviewer addon implementation (`skills/deepworkplan/addons/ai-diff-reviewer/`)
- Herdr, agentkit and Vim integrators (`skills/deepworkplan/addons/{herdr,agentkit,vim}/`)

---

*Part of the DeepWorkPlan methodology v5.0.0, MIT License, by [Dailybot](https://dailybot.com) / dailybotops.*
