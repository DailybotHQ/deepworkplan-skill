# addons/ — Opt-In Addon Mechanism

This directory ships **inside** the DeepWorkPlan skill
(`skills/deepworkplan/addons/`). The active set has seven **optional**
addons and one baseline addon. Optional addons that integrate a separate
product (herdr-peers, the coding-agents kit, the Vim editor) are thin
integrators pinned to a product tag.
Optional addons are **never** part of the AI-first baseline — one of them, **dependency
upgrade**, is **near-default**: offered for every repo with declared
dependencies, and its **inert** `/lib-upgrade` delegator installs under the
onboarding consent unless explicitly declined (an install runs no upgrade).
The fifth, the **AI Diff Reviewer local
review**, is a **required baseline component** since standard 2.3.0 (its CI
surface stays optional — see `ai-diff-reviewer/SPEC.md` §2). A repository is
fully conformant with **zero optional addons** installed. (Normative source:
`spec/ADDONS.md`.)

An **addon** is a self-contained, optional capability that the `onboard` flow
can layer onto a repo *after* the mandatory AI-first scaffolding
(`AGENTS.md` + `docs/` + per-module docs + `.agents/` + `.claude → .agents` +
`.cursor → .agents` + the DWP skill + `.dwp/`). Addons encode high-value best practices that the
audit found consistently across Dailybot repos but that a repo does **not** need
in order to be AI-first.

## The four rules every addon obeys

1. **Never required (one declared exception).** An optional addon MUST NOT be
   a precondition of baseline conformance; declining every optional addon
   still yields a fully AI-first repo. The AI Diff Reviewer's **local review**
   is the single declared exception: `spec/ADDONS.md` §6.5 places it in the
   baseline, and only its CI surface is opt-in.
2. **Reconcile, don't clobber.** When an accepted addon finds existing setup it
   would touch (an existing `.devcontainer/`, `docker/`, `.gitignore`,
   `.env.example`), it reconciles **additively** — preserving working values
   (ports, network names, env flags, project identity) and bringing the rest
   toward the addon standard. Any destructive change to an existing file
   requires explicit user approval (`AGENT_PROTOCOL.md`).
3. **Reason, don't copy-paste.** Like the rest of the methodology, an addon's
   templates are filled by **reasoning about the target repo's actual stack**,
   not by copying one reference repo's files verbatim. The *shape* is fixed; the
   *content* is adapted per repo. (One narrow exception: a piece so stable it is
   copied near-verbatim is explicitly flagged as such — e.g. the devcontainer
   AI-CLI persistence entrypoint.)
4. **Archetype-agnostic.** An addon MAY be layered onto either an individual
   repo or an orchestrator hub (`ARCHETYPES.md`); the addon's own spec says how
   each archetype differs.

## The addon contract — four mandatory components

Each addon is a subfolder here and MUST ship all four:

| Component | File(s) | Purpose |
|-----------|---------|---------|
| **Spec** | `SPEC.md` | RFC-2119 description of what the addon provides and what "conformant to this addon" means. |
| **Reasoning templates** | `templates/*` | Parameterized guides with placeholders + decision notes the agent fills by reasoning about the repo's stack — not literal copies of one repo. |
| **Onboarding hook** | `SKILL.md` (`user-invocable` when active) | The entry point the `onboard` flow calls to offer, then (if accepted) apply the addon. The staged Herdr candidate has this hook disabled until v7. |
| **Validation step** | A checklist inside `SPEC.md`/`SKILL.md` | Confirms the addon was applied correctly (files exist, settings present, smoke check passes). |

An addon MAY additionally ship per-stack presets, examples, or migration notes.

## How `onboard` discovers and applies addons

- **Discovery** — `onboard` installs the required AI Diff Reviewer local review
  in **Phase 7a**, then enumerates this directory (`../addons/`) and offers each
  optional addon in **Phase 7b**, after the core
  scaffolding (Phases 3–7).
- **Consent** — it never applies a signal-gated addon without user acceptance.
  In trust mode it MAY *recommend* the obviously-applicable ones, but still
  surfaces them. The **dependency-upgrade** addon is the one near-default
  exception: its **inert** `/lib-upgrade` delegator installs under the Phase 0
  onboarding consent unless explicitly declined, and no upgrade ever runs from
  an install.
- **Decline is safe** — declining an optional addon leaves a baseline-conformant repo; the required local-review baseline is handled separately in Phase 7a.
- **On accept** — `onboard` reads the addon's `SKILL.md`, runs its hook
  (reasoning about the detected stack), then runs its validation step.

## Addons

| Addon | Folder | Status |
|-------|--------|--------|
| Devcontainer support | [`addons/devcontainer/`](devcontainer/SKILL.md) | **Authored** — vendor-neutral thin integrator of devcontainer-kit (`dck`, pinned `v0.1.0`, interface 1): detect with `dck doctor --json`, offer, reason flavour/service/ports/layers from the real stack, `dck init` reconciles an existing layout (consented diffs, backups — never clobbered), optional Herdr container profile, validation. Loopback ports, agent forwarding, no privileged options. Never required. |
| Dailybot integration | [`addons/dailybot/`](dailybot/SKILL.md) | **Authored** — opt-in install of the Dailybot agent skill (**3.23.3**) / CLI (**>= 3.9.0**), auth **deferred** to the Dailybot skill's own consent flow, **four lifecycle events** (kickoff, significant task, blocked, completion) wired as optional best-effort reports via the `report` sub-skill, optional deterministic hook enforcement, and access to the full 17-capability Dailybot skill when invoked directly. The core methodology has **zero** Dailybot dependency. |
| Dependency upgrade | [`addons/dependency-upgrade/`](dependency-upgrade/SKILL.md) | **Authored** — **near-default**, **package-manager-agnostic** dependency upgrades: offered for every repo with declared dependencies, with the inert `/lib-upgrade` delegator installed under the onboarding consent unless explicitly declined (an install runs no upgrade). When invoked: detect the repo's real manager (npm/pnpm/yarn + ncu, pip/poetry/uv, cargo, go mod, bundler, composer…), classify by semver, upgrade in safe batches, run the repo's **real** validation gate after each batch, revert a failing batch, summarize. |
| Design system | [`addons/design-system/`](design-system/SKILL.md) | **Authored** — opt-in, **interface-surface-scoped** `DESIGN.md` at `docs/DESIGN.md` (indexed from `AGENTS.md`; root only if no `docs/` tree), covering three profiles in one file: **visual-ui** (design tokens from CSS vars / Tailwind config / token files / component styles; WCAG AA contrast), **cli-output** (semantic terminal styles, output components, TTY/`NO_COLOR` degradation), and **conversational** (voice & register, message anatomy, per-platform rendering with plain-text fallbacks). Reason about the repo's **real** design source — never a brand file — and reconcile an existing `DESIGN.md` instead of clobbering it. Offered by `onboard` **only when an interface surface is detected** — the offer is mandatory, not skippable, with the detection rationale recorded — and every profile (**visual-ui** strongly recommended) installs only after explicit acceptance, never auto-applied. |
| AI Diff Reviewer | [`addons/ai-diff-reviewer/`](ai-diff-reviewer/SKILL.md) | **Authored** — **required local review** (baseline since 2.3.0): tag-pinned install of the vendored `DailybotHQ/ai-diff-reviewer` skill (currently **v3.2.3**; workflows pin the moving `@v3`; marketplace listing "AI Diff Reviewer") plus a repo-tailored `.review/extension.md`, wired into the Final Review's security pass; the CI Action (Flow B — same prompt bytes as the local pass, methodology and severity parity) and the `apply-review` / `address-review` companions stay an explicit opt-in. |
| Herdr | [`addons/herdr/SKILL.md`](herdr/SKILL.md) | **Authored** — thin integrator, explicit opt-in offered in `onboard` Phase 7b, pinned to `herdr-peers@v0.1.0` (protocol/interface 1, detected with `herdr-peers --version`; Herdr's official skill pinned `herdrdev/herdr@v0.9.3`): the **interactive** delegation transport of v7 plans — one `herdr-peers ask` to a peer pane on any machine, recorded in the plan journal before it is relied on, the reply asserted until the plan's own gates observe the work. The peer protocol lives in herdr-peers; this folder carries no copy. Never required. |
| agentkit | [`addons/agentkit/SKILL.md`](agentkit/SKILL.md) | **Authored** — thin integrator, explicit opt-in offered in `onboard` Phase 7b, pinned to `coding-agents-kit@v0.1.1` (interface 1, detected with `ak doctor --json`): the **headless** delegation transport of v7 plans — one `ak run` per delegate in a dedicated git worktree, recorded through `ledger.py delegate`, result asserted until the plan's own gates observe it. Install by a clone of the exact tag + `install.sh`; the pack never adds a permission-bypass flag. Never required. |
| DeepWorkPlan Vim | [`addons/vim/SKILL.md`](vim/SKILL.md) | **Authored** — thin integrator, explicit opt-in offered in `onboard` Phase 7b, pinned to `deepworkplan-vim@v0.4.0` (interface 1, read from the product's `addon/surface.json`). Optional machine-level install of DeepWorkPlan Vim, the terminal editor for Deep Work Plan (Neovim 0.12+, GPL-3.0, its own repo `DailybotHQ/deepworkplan-vim`): detect it through the product's surface, offer — never impose — the editor, guide the documented install (macOS/Linux via the product's install page `https://deepworkplan.com/vim` — download, verify the pinned checksum, run, never a remote-installer pipe spelled in this pack's text; Windows `winget install Neovim.Neovim` + a tagged clone, never piped PowerShell), and validate the installed surface (command index, VS Code gestures, plan browser, markdown viewer). Two routes: the full editor now, the Neovim plugin in v7.1. An existing Neovim config is **never** overwritten without explicit consent — non-interactive installs onto an existing config abort with instructions; backups go to `~/.config/previous-deepworkplan-vim`. Never a conformance gate. |

> This README is the mechanism doc. The first addon, `addons/devcontainer/`, is
> the methodology's proof that the mechanism works; the second,
> `addons/dailybot/`, shows an addon can layer optional team visibility while
> keeping the methodology fully vendor-neutral; the third,
> `addons/dependency-upgrade/`, shows an addon can encode a recurring maintenance
> workflow that reasons about each repo's actual stack; the fourth,
> `addons/design-system/`, shows an addon can capture durable, repo-native
> interface design context — visual UI, CLI output, or conversational — for any
> repo with a user-facing surface; the fifth, `addons/ai-diff-reviewer/`, is
> the declared exception: its structured local review is part of the baseline
> every 2.3.0 repository ships (installed by `onboard`, run by the Final
> Review's security pass), while its CI-side merge gate with byte-identical
> parity stays opt-in — every repo remains conformant with zero optional
> addons installed.
