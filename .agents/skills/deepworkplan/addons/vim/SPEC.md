# SPEC.md — Vim Editor Addon (Normative)

## Abstract

This document is the **normative specification** of the DeepWorkPlan **vim
editor addon**: an opt-in capability that offers **DeepWorkPlan Vim** — the
terminal editor for Deep Work Plan (Neovim 0.12+) — to the person working a
repository, as an **optional, machine-level editor surface for agents and
humans**. The editor itself lives in its own public repository
(`DailybotHQ/deepworkplan-vim`, GPL-3.0) and versions independently of the
methodology pack; this addon is the **DWP-side integration contract only**:
what the onboarding flow detects, how it offers, the absolute consent gate
protecting an existing Neovim config, the documented install paths, and the
post-install validation.

The addon is governed by [`../README.md`](../README.md) and
[`../../spec/ADDONS.md`](../../spec/ADDONS.md): it is **never** required for
baseline AI-first conformance. Since 7.0.0 it is a **wired, thin
integrator**: `onboard` Phase 7b offers it as an explicit opt-in, and every
claim it makes about the editor is read from the product's machine-readable
surface (`addon/surface.json`, interface `1`) at the pinned tag
`deepworkplan-vim@v0.4.0`.

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 0.2.0 |
| **Status** | Beta (DeepWorkPlan 7.0.0-beta.1) |
| **Companions** | `SKILL.md`, `templates/INTEGRATION.md`, `../README.md`, `../../spec/ADDONS.md`, `../../spec/V7_ROADMAP.md` |
| **License** | MIT |

> This SPEC carries its **own** version line, independent of the DeepWorkPlan
> pack version. The pack's `SKILL.md` frontmatter `version:` field records
> the pack version at authoring time; this document's `Version` is the
> addon-spec version. They move separately.

## 1. Conventions

The RFC 2119 keywords (**MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**,
**MAY**, **OPTIONAL**) are interpreted as in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

Throughout, **the editor** means DeepWorkPlan Vim, the terminal editor for
Deep Work Plan (repository `https://github.com/DailybotHQ/deepworkplan-vim`,
GPL-3.0, CREDITS.md lineage preserved). **The addon** means this folder —
the integration contract inside the DeepWorkPlan pack. The addon is **not**
the editor and ships none of its code.

---

## 2. Placement Decision (recorded, not open)

The editor lives in its own public repository and this addon only integrates
it, per the placement decision recorded in
[`../../spec/V7_ROADMAP.md`](../../spec/V7_ROADMAP.md) ("Addon 2 —
DeepWorkPlan Vim"). Reasoning: the editor is a versioned product with its own
release cycle, installer and contributor environment; a methodology pack that
embedded it would couple every onboarded repo's documentation to an editor's
release cadence. The split mirrors how the AI Diff Reviewer is a named
external surface. What stays **inside** this addon is the part that must move
in lockstep with the plan autonomy and consent rules: detection, the offer,
the consent gate, and validation.

## 3. What This Addon Is — and Is Not

- The addon is an **optional editor capability**. It is not part of the
  AI-first baseline, not a review gate, and **never required for
  conformance**: a repository whose people use any other editor (or none) is
  fully conformant.
- It is **wired as an explicit opt-in**: `onboard` Phase 7b offers it; no
  other flow (`create`, `execute`, `refine`, `resume`, `status`, `verify`)
  invokes it, and none MAY require it. It provides no ability and requires
  no grant (its `addon.json` declares none).
- The addon provides: **detection** of the machine's Neovim state through
  the product's surface, an **offer** (never an imposition), a **guided
  install** through the editor's own documented, checksum-verified paths
  under the consent gate below, the **registry record** of an acceptance,
  and **validation** of the installed surface.
- **Two routes.** The full editor (available at the pinned tag) is the only
  installable route. The `deepworkplan.nvim` plugin for people who keep
  their own Neovim config is the **v7.1** route: the addon MAY name it to a
  person who declines because of their config, and MUST NOT offer to install
  it or claim it exists before it ships.
- Missing tooling is never a conformance failure, never a launch blocker,
  never a silent surprise: a machine without Neovim, below the 0.12 floor,
  or without the editor records the detection outcome and continues.

## 4. Detection and Offer

- Detection is **read-only**: `command -v nvim`, `nvim --version` (the
  editor requires **Neovim 0.12+**), a directory check of the config dir
  (`${XDG_CONFIG_HOME:-$HOME/.config}/nvim`, `DWP_VIM_DIR` when set,
  `%LOCALAPPDATA%\nvim` on Windows) and reading the installed
  `addon/surface.json`. The addon MUST NOT install, write, or touch anything
  to detect.
- The machine states are the product's own (`addon/surface.json` →
  `detect.states`), preceded by the Neovim checks:

  | State | Evidence | Meaning |
  |-------|----------|---------|
  | **no Neovim** / **below 0.12** | `command -v nvim` empty / version < 0.12 | informational offer only |
  | **absent** | config dir missing or empty | install allowed on acceptance |
  | **existing config** | config dir non-empty and lacks either identity file (`install.lua`, `lua/plugins.lua`) | a foreign config; never overwrite without consent |
  | **installed without surface** | both identity files, no `addon/surface.json` | a release older than v0.4.0: interface unknown, **not compatible** |
  | **installed** | both identity files and `addon/surface.json` | read `interface` and `version` from the file |

  When the evidence is inconclusive, the state MUST be treated as
  "existing config" so the consent gate governs — the safe direction.
- **Interface check.** An installed surface whose `interface` is not `1` is
  an unknown major: the addon MUST print exactly one warning line and treat
  the editor as **not available** — never an error of the repository, the
  plan, or the flow. The plugin's marker file
  (`detect.marker`) means "plugins bootstrapped"; its absence MUST NOT be
  read as "editor absent".
- The addon MUST present the editor **only as an offer**, stating what it is
  — **only** the features the pinned surface lists in `features[]` (at
  `v0.4.0`: the command index, VS Code gestures, the read-only plan browser,
  the markdown viewer, the consent-first installer) — and what it costs (a
  machine-level Neovim config, not a repo file). Declining MUST leave the
  repository fully conformant.
- In trust mode the addon MAY recommend the editor when Neovim ≥ 0.12 is
  detected, but it MUST still surface the offer and MUST NOT apply anything
  unasked.

## 5. The Consent Gate (absolute)

The consent invariant, from the frozen product contract:

> Non-interactive install onto an existing `~/.config/nvim` **aborts with
> instructions**; interactive asks; backups go to
> `~/.config/previous-deepworkplan-vim`.

- An existing Neovim config is **never overwritten without explicit
  consent** — the reconcile-don't-clobber rule, absolute for this addon.
- The addon MUST NOT auto-install onto an existing config in a
  non-interactive context (unattended onboard, CI, an agent running alone).
  Such a context **stops at instructions**: it records `install deferred:
  existing config, consent required` and prints what a human must run. It
  MUST NOT guess consent.
- In an interactive context the addon asks; on consent the editor's own
  installer takes the backup to `~/.config/previous-deepworkplan-vim`. The
  backstop lives in the installer, not in the agent's judgment.
- A no-config machine is the only state where install is not consent-gated
  by a *pre-existing* config — the offer acceptance itself is the consent.

## 6. Install Paths (the integration contract)

The addon points at the editor's **versioned, documented** paths at the
pinned tag. It MUST NOT vendor, mirror, re-implement, or "improve" the
installer; the source of truth is `install.sh` at the editor repository
root at the tag, with the website serving a byte-identical mirror. The
pinned surface (`install` block of `addon/surface.json` at `v0.4.0`) names
the script location, its SHA-256 and the steps.

- **macOS / Linux (canonical documented path):** the product's install
  page (`https://deepworkplan.com/vim`) — download the tag's `install.sh`
  to a local file, verify its SHA-256 against the pinned surface (stop on a
  mismatch — a mismatch MUST NOT be run), then run it with the ref pinned
  (`DWP_VIM_REF=v0.4.0 bash install.sh`): **three separate steps**. A one-line
  fetch-and-execute pipeline MUST NOT appear anywhere in this pack's
  text, even as an illustration of what not to do: lexical security
  scanners (Snyk E005 / Socket W012) flag the pipe shape wherever it
  appears, and a prior release FAILed on exactly that class (precedent
  `6a05ed9`). The product's own documentation owns its one-liner; pack
  copy describes the flow, it never spells the pipeline.
- **Windows (documented path — never piped PowerShell):**
  `winget install Neovim.Neovim`, then a `git clone --branch v0.4.0` of the
  repository into `%LOCALAPPDATA%\nvim`, then `lua install.lua`.
- **Manual (any OS):** `git clone --branch v0.4.0` into the config dir, then
  `lua install.lua`.

- **Who runs it.** The addon's default posture is to **point at the
  instructions**: it shows the documented steps for the person to run
  themselves. The agent MAY run the documented install itself only when
  **both** hold: the context is
  interactive, and the person explicitly accepted the install. Even then the
  installer's own consent gate (§5) is the absolute backstop, and the addon
  MUST re-detect afterwards and record the observed version.
- The addon MUST NOT pipe any installer in a non-interactive context, and
  MUST NOT construct alternative install commands beyond the documented
  paths above.

### 6.1 Registry record

On acceptance (installed now, or deferred with the person's agreement), the
addon records itself in the repository's addon registry —
`.dwp/config.json` → `addons.vim` = `{"enabled": true, "version":
"v0.4.0"}` (`../../spec/CONFIG.md`). The write reconciles an existing file
(other keys untouched) and never happens on a decline. The registry entry
is informative: the methodology reads nothing from it that could gate a
plan.

## 7. Post-Install Validation

After any install (by the person or, interactively, by the agent), the addon
validates the surface — all checks recorded, none blocking:

1. **Smoke:** Neovim starts headlessly (`nvim --headless +"qa"` exits 0).
2. **Command index present:** the `<Leader>hh` mapping named by the
   surface's `command_index` feature is live — probed headlessly via
   `maparg`, not assumed from file presence.
3. **Plan browser loadable:** the module behind `<Leader>P` (surface
   feature `plan_browser`) loads without error — a headless require probe;
   deep navigation stays manual.
4. **Surface read back:** the installed `addon/surface.json` reports
   `interface` `1` and the pinned `version`.
5. **Reconcile-not-clobber check:** if a config pre-existed, the backup
   exists at `~/.config/previous-deepworkplan-vim` and the recorded
   pre-existing files are reachable there; nothing outside `~/.config/nvim`
   and the backup directory changed.

A failed check is a recorded finding about the machine — never a repository
conformance failure.

## 8. Archetype Differences

The addon is archetype-agnostic (addon rule 4); the difference between the
archetypes is deliberately one line:

- **Editor install: identical for both.** The editor is a machine-level
  Neovim config; nothing about offering or installing it depends on the
  repository archetype.
- **Plan browser scope: the only difference.** The plan browser lists
  `.dwp/plans/` from the config dir and the current working directory. In an
  **individual repo**, that is the repo's own `.dwp/plans/`. In an
  **orchestrator hub**, it is the hub's `.dwp/plans/` — the child plans the
  hub coordinates. The integration reasoning MUST record which tree the
  browser will surface for this machine, so nobody is surprised; no addon
  behavior changes between archetypes.

## 9. Reconcile, Don't Clobber

- Applied to a machine with an existing Neovim config, the addon reconciles:
  it never deletes or overwrites; the editor's installer backs up the prior
  config to `~/.config/previous-deepworkplan-vim` under consent (§5).
- The addon MUST NOT touch repository plan state (`.dwp/`) beyond the
  reading the plan browser performs; it writes no repo files as part of the
  editor install.
- Any destructive change to an existing file requires explicit user approval
  (`AGENT_PROTOCOL.md`), and the addon MUST record what changed.

## 10. Never-Block Rule and Write Scope

- Detection failure, a declined offer, a deferred install, a failed smoke
  check: every one records the outcome and the flow continues. Nothing in
  this addon blocks `onboard`, `execute`, `create`, or `verify`.
- The addon ships no binaries, writes no secrets, changes no SSH or host
  trust files, and emits no telemetry. Its write surface is: the editor
  install itself (via the documented installer, under consent) and its own
  records of detection and validation outcomes.
- The addon MUST NOT claim, in any generated text, that: the editor is
  installed on any machine it has not validated; the v7.1 plugin exists; or
  that `vim.deepworkplan.com` is live. Feature claims MUST stay within the
  pinned surface's `features[]`; version numbers are observed, never
  invented.

## 11. Validation Checklist (the addon's fourth component)

The addon is correctly authored/applied when **all** hold:

1. `SKILL.md`, `SPEC.md`, `addon.json` and `templates/INTEGRATION.md` exist
   in the installed pack under `addons/vim/`; `SKILL.md` frontmatter
   validates (`name: deepworkplan-addon-vim`, `user-invocable: true`,
   quoted SemVer `version:`, `documentation_url`, `allowed-tools`).
2. Detection runs read-only and records one of the §4 states; no state
   installs anything by itself; an unknown interface major is one warning
   and "not available".
3. A non-interactive context with an existing config produces the abort
   record `install deferred: existing config, consent required` — never an
   install.
4. Any install used a documented path (§6) at the pinned tag with a
   verified checksum; a pre-existing config has a
   `~/.config/previous-deepworkplan-vim` backup.
5. Post-install probes pass: headless start, command-index mapping live, plan-browser
   module loads (§7) — or the failure is recorded and the flow continues.
6. No credential, host-trust file, or repository plan state was modified.

## 12. Versioning

This SPEC versions independently of the DeepWorkPlan pack (`0.2.0` here).
The editor product versions independently of both, through its own
repository's release flow; compatibility is decided by the product's
integer interface (`1`), the installed release by the tag the pack pins
(`v0.4.0`, bumped only with a parity-tested pack change). The pack records
the editor's observed version from the installed surface and `nvim
--version` at detection/validation time.

---

## 13. References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)
- `SKILL.md` (the onboarding hook + flow), `templates/INTEGRATION.md`
  (reasoning template)
- `../README.md` (addon mechanism), `../../spec/ADDONS.md` (concept +
  pointer), `../../spec/V7_ROADMAP.md` (the v7 wiring plan — non-normative)
- The editor repository: `https://github.com/DailybotHQ/deepworkplan-vim`
  (GPL-3.0; CREDITS.md lineage preserved)

---

*Part of the DeepWorkPlan methodology v5.0.0, MIT License, by [Dailybot](https://dailybot.com) / dailybotops.*
