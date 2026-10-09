---
name: deepworkplan-addon-vim
description: Optional DeepWorkPlan addon that offers DeepWorkPlan Vim, the terminal editor for Deep Work Plan (Neovim 0.12+, its own repository DailybotHQ/deepworkplan-vim pinned at v0.5.1), as a machine-level install for the person behind a repository - a thin integrator that reads the product's own addon/surface.json (interface 1) to detect the editor, offers it (never imposes it) from onboard Phase 7b, guides the product's documented, checksum-verified install under an absolute consent gate, and validates the installed surface. Two routes - the full editor today, the Neovim plugin in v7.1. Never required, never a conformance gate, and an existing Neovim config is never overwritten without explicit consent.
version: "7.0.1"
documentation_url: https://deepworkplan.com/kit/vim
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"⌨️","homepage":"https://deepworkplan.com/kit/vim"}}
---

# DeepWorkPlan — Vim Editor Addon

Offer **DeepWorkPlan Vim** — the terminal editor for Deep Work Plan — to the
person working a repository: a machine-level Neovim config (Neovim 0.12+)
that puts the plan surface in the editor. This is an **opt-in addon**, never required
for a repo to be AI-first, the editor is **never** a
conformance gate, and an existing Neovim config is **never** overwritten
without explicit consent.

This addon is a **thin integrator**. The editor is its own product
(`https://github.com/DailybotHQ/deepworkplan-vim`, GPL-3.0, versioned
independently); everything this addon claims about it is read from the
product's machine-readable surface, `addon/surface.json`, at the pinned tag
— never guessed, never restated from memory.

| Pin | Value |
|-----|-------|
| Product | `DailybotHQ/deepworkplan-vim` |
| Tag | `v0.5.1` |
| Interface | `1` (read from `addon/surface.json` → `"interface"`) |
| Registry key | `vim` (`.dwp/config.json` → `addons.vim`) |

## Read these first (all relative inside the skill)

- [`SPEC.md`](SPEC.md) — the normative (RFC-2119) contract: surface-driven
  detection, the offer, the absolute consent gate, the verified install,
  post-install validation, never-block rule.
- [`templates/INTEGRATION.md`](templates/INTEGRATION.md) — reasoning
  guidance (NOT copy-paste): the detection states, the consent branch table,
  per-OS install, smoke probes, reconcile-not-clobber.
- `../README.md` — the addon mechanism (opt-in, reconcile-don't-clobber,
  the four mandatory components).

## When this runs

- **`onboard` Phase 7b** offers it as an explicit opt-in (see
  `../../onboard/addons.md`), after the core AI-first scaffolding.
- **Direct invocation** on an already-onboarded repository.
- Nothing else: `create`, `execute`, `refine`, `resume`, `status` and
  `verify` never require it, and a repository without it is fully
  conformant.

## Two routes

1. **The full editor (available now, v0.5.1).** The whole DeepWorkPlan Vim
   config: command index, VS Code gestures, the read-only plan browser, the
   markdown viewer, the consent-first installer. This is what the offer
   installs.
2. **The Neovim plugin (v7.1, not shipped).** A `deepworkplan.nvim` plugin
   for people who keep their own Neovim config, carved from the product's
   self-contained `lua/dwp/` modules. It does not exist yet: name it as the
   route for someone who declines the full editor because of their config,
   never offer an install of it, never claim it is available.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`. The
write scope is deliberately tiny — most of this addon is reading and
talking:

- **Before consent: read-only.** Detection is `command -v`, `--version`,
  directory inspection and reading `addon/surface.json`. Nothing is
  installed to detect.
- **Writes (only after explicit acceptance):** the editor install itself,
  through the product's documented installer (SPEC §6) — never a hand-rolled
  file merge — the `addons.vim` entry in `.dwp/config.json` that records the
  acceptance, and the addon's own records of detection and validation
  outcomes.
- **It MUST NOT:** overwrite or delete an existing Neovim config (the
  installer's consent-gated backup to `~/.config/previous-deepworkplan-vim`
  is the only sanctioned transition), install onto an existing config in a
  non-interactive context (record `install deferred: existing config,
  consent required` and print the instructions instead), run an installer
  whose checksum did not match the pinned surface, construct install
  commands beyond the documented paths, touch the target repo's `.dwp/`
  plan state beyond the plan browser's reading, or block any DWP flow when
  Neovim or the editor is absent.

## The flow

### Step 0 — Detect (read-only, surface-driven)

`command -v nvim` → `nvim --version` (floor **0.12**) → inspect the config
dir (`${XDG_CONFIG_HOME:-$HOME/.config}/nvim`, or `DWP_VIM_DIR` when set) →
classify with the product's own states (`addon/surface.json` → `detect`):
**absent**, **existing config** (foreign — lacks either identity file
`install.lua` / `lua/plugins.lua`), **installed without surface** (a release
older than v0.4.0 — interface unknown, treat as not compatible; the
descriptor's `legacy_paths` make `resources.py` report it with one warning,
never as absent), or
**installed** (read `interface` and `version` from the installed
`addon/surface.json`). An `interface` other than `1` is an unknown major:
one warning line, the addon is treated as **not available** — never an
error of the repository or the plan. Record the state; no state installs
anything by itself.

### Step 1 — Offer (never impose)

Present the editor with the features the pinned surface lists
(`features[]` — only those) and its actual cost (a machine-level config,
not a repo file). Declining is a complete answer — the repo stays fully
conformant. In trust mode, recommend only on a detected Neovim ≥ 0.12, and
still surface the offer.

### Step 2 — Consent gate (absolute)

Run the consent branch table (`templates/INTEGRATION.md` §3). Interactive +
existing config → ask explicitly, naming the backup. Non-interactive +
existing config → **stop at instructions**, record the deferral. The
backstop is the installer's, never the agent's judgment.

### Step 3 — Install (documented paths, point-don't-run by default)

Show the person the product's documented install at the pinned tag
(surface `install.steps`): download `install.sh` from the tag to a local
file, verify its SHA-256 equals the pinned `install.script.sha256` (stop on
a mismatch), then run it with the ref pinned (`DWP_VIM_REF=v0.5.1 bash
install.sh`) — three separate steps, never a remote-installer pipe spelled
in this pack's text. Windows and manual paths are a tagged `git clone` then
`lua install.lua` (Windows first `winget install Neovim.Neovim`), never
piped PowerShell. Run the installer yourself only in an interactive context
with explicit acceptance, then re-detect and record the observed version.

### Step 4 — Record and validate

On acceptance, record the addon in the repository registry —
`.dwp/config.json` → `"addons": {"vim": {"enabled": true, "version":
"v0.5.1"}}` (`../../spec/CONFIG.md`; reconcile an existing file, never
clobber it) — then run the headless smoke start, the command-index mapping
probe and the plan-browser module probe. Every outcome is recorded, none
blocks. A failed check is a finding about the machine, never a repo
conformance failure.

## Failure-mode guardrails

- **Never required, never blocking.** No Neovim, below floor, declined,
  deferred, unknown interface, failed smoke: record and continue.
  `onboard`, `execute`, `create`, and `verify` always succeed regardless.
- **Consent is absolute.** No guessed consent, no non-interactive install
  onto an existing config, no self-made reconcile merge.
- **Honest claims.** Never claim the editor is installed on a machine it
  was not validated on, that the v7.1 plugin exists, or a feature the
  pinned surface does not list. Versions are observed, never invented.
- **Reconcile, don't clobber.** The prior config survives at
  `~/.config/previous-deepworkplan-vim`; nothing outside the config dir and
  that backup changes; the repo's plan state is read-only to this addon.

## Validation checklist (component 4 — mirrored from SPEC §11)

The addon is correctly applied when all hold:

1. `SKILL.md`, `SPEC.md`, `addon.json` and `templates/INTEGRATION.md` exist
   under `addons/vim/`; this frontmatter validates.
2. Detection ran read-only and recorded one of the surface states.
3. A non-interactive context with an existing config produced the
   `install deferred: existing config, consent required` record — never an
   install.
4. Any install used a documented path at the pinned tag with a verified
   checksum; a pre-existing config has a `~/.config/previous-deepworkplan-vim`
   backup.
5. Post-install probes passed (headless start · command index live · plan
   browser loads) or the failure is recorded and the flow continued.
6. No credential, host-trust file, or repository plan state was modified;
   the only repository write is the `addons.vim` registry entry.
