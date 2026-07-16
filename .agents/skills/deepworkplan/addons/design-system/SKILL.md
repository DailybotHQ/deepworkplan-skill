---
name: deepworkplan-addon-design-system
description: Optional DeepWorkPlan addon that gives a repo with a user-facing interface surface a DESIGN.md (under docs/, indexed from AGENTS.md) — a Markdown design-system file any coding agent reads to generate interface output consistent with the repo's OWN conventions. Covers three profiles detected independently from real files — visual-ui (rendered web/mobile/desktop UI), cli-output (styled terminal output — semantic colors, panels, spinners, prompts, TTY/NO_COLOR degradation), and conversational (chat/email messaging — voice and register, message anatomy, per-platform rendering). Reasons about the repo's ACTUAL design source (CSS custom properties, Tailwind config, token files, component styles, a CLI display/theme module, or message-composition helpers) rather than copying a brand file; checks contrast (WCAG AA), color-is-not-the-only-carrier, plain-text fallbacks, and token integrity. The visual-ui profile is default-on when detected (applied in trust mode, strongly recommended in guided mode); cli-output and conversational are recommended when detected and always asked about, never auto-applied. Never offered for a repo with no interface surface (pure library, headless service, infra-only); never required for baseline conformance; reconciles an existing DESIGN.md instead of clobbering it. Use when the developer wants agents to produce on-brand, consistent interface output — visual UI, terminal output, or outbound messages.
version: "2.17.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"🎨","homepage":"https://deepworkplan.com"}}
---

# DeepWorkPlan — Design-System Addon

Give a repo with a **user-facing interface surface** a **`DESIGN.md`** — living
under **`docs/`** alongside the repo's other specs and **indexed from
`AGENTS.md`** — so any human or AI agent generates interface output that matches
the repo's **own** conventions, instead of the unstyled, statistically-common
defaults an agent falls back to with no guidance. "Interface surface" is plural
(`SPEC.md` §3): a rendered **visual UI**, styled **CLI output**, or a
**conversational** surface (the product talks on chat/email) each count, as
independent **profiles** that stack into the same single `DESIGN.md`. This is an
**opt-in addon** — it is **never** required for a repo to be AI-first, and it is
**only** for repos with at least one real interface surface.

> ## The rule that overrides everything: REASON about the repo's source, then write
>
> A `DESIGN.md` is only useful if it reflects **this** repo. The first job is to
> **read the repo's real design source** — its stylesheet, CSS custom properties,
> Tailwind config, token files, and component styles; or its CLI display/theme
> module and print helpers; or its message-composition layer and documented voice
> rules (see `SPEC.md` §3–§5 and `templates/presets.md`) — then document those
> values. **Never paste a third-party brand's `DESIGN.md`** (a Stripe/Linear/etc.
> catalog entry) and never import another CLI's or bot's conventions wholesale:
> reference catalogs are inspiration for *structure*, never content.

## Read these first (all relative inside the skill)

- [`SPEC.md`](SPEC.md) — the normative (RFC-2119) contract: interface-surface
  gate + the three profiles, canonical sections per profile, reason-don't-copy,
  reconcile-don't-clobber, accessibility & output integrity,
  pragmatic-reference posture, validation step.
- [`templates/DESIGN.md.md`](templates/DESIGN.md.md) — the annotated `DESIGN.md`
  skeleton (each canonical section per profile + how to fill it from the repo).
  The *shape* is fixed; the *content* is reasoned per repo.
- [`templates/presets.md`](templates/presets.md) — per-stack **reasoning presets**
  (Tailwind, CSS-variables/vanilla, component-library/design-tokens, CLI
  rendering layers, conversational platforms) — where to find the design source
  in each stack. A *starting checklist*, not an answer key — **detected reality
  wins**.
- [`templates/agent_prompt_guide.md`](templates/agent_prompt_guide.md) — the
  "Agent Prompt Guide" block to embed so downstream agents know how to follow
  `DESIGN.md`.
- [`templates/design-system-command.md`](templates/design-system-command.md) — the
  **optional** `/design-system` delegator this addon MAY install into the target
  repo's `.agents/commands/` (only when accepted and wanted).
- `../README.md` — the addon mechanism (opt-in, reconcile-don't-clobber, contract).

## When this runs

- From **`onboard` Phase 7b** — after the core AI-first scaffolding. Profiles
  carry different strengths (`SPEC.md` §3.5): when a **visual UI** surface is
  detected the profile is **default-on** (`onboard` applies it in trust mode and
  strongly recommends it in guided mode); when a **CLI output** or
  **conversational** surface is detected the profile is **recommended and always
  asked about** — never auto-applied. When no interface surface is detected the
  addon is **not** offered. Either way the developer may decline and the repo
  stays baseline-conformant.
- **Directly** — `/deepworkplan-addon-design-system` on an already-onboarded repo
  to create or refresh `DESIGN.md` (or add a newly relevant profile to it), or
  via the installed `/design-system` delegator if one was added.

## The flow

### Step 0 — Consent + interface-surface gate
1. Confirm the developer wants a `DESIGN.md` (skip silently if declined — the repo
   stays baseline-conformant).
2. **Detect the repo's interface surfaces, profile by profile** (`SPEC.md` §3):
   - `visual-ui` — stylesheets / CSS custom properties, a Tailwind config or
     `@theme` block, UI components (`.tsx`/`.vue`/`.svelte`/`.astro`), or a
     token/brand source.
   - `cli-output` — a CLI/TUI rendering library (rich, chalk, ink, lipgloss,
     ratatui, …) plus a **deliberate rendering layer** (a `display.*`/`ui.*`
     helper, semantic print helpers, documented output patterns). Skip the
     profile for a bare argument parser with raw unstyled prints.
   - `conversational` — a chat-platform SDK (Slack, Discord, Teams, …), a
     message-composition layer, or documented outbound-message voice rules.
3. If **no** profile is detected, **stop** and tell the developer this addon
   does not apply. Otherwise, offer each detected profile per its strength
   (§3.5): apply/strongly-recommend `visual-ui`; **ask** before `cli-output` and
   `conversational`, even in trust mode.

### Step 1 — Locate the design source (the part you MUST reason about)
Find where each accepted profile's design values actually live, using
`templates/presets.md`:

- **Tailwind** → `tailwind.config.*` or a Tailwind v4 `@theme {}` block in CSS:
  theme colors, font families, spacing, radius, screens.
- **CSS variables / vanilla** → `:root { --… }` custom properties in the global
  stylesheet; spacing/size scales; media-query breakpoints.
- **Component library / design tokens** → a `tokens.*` / `theme.*` export, a
  design-tokens JSON, or a Storybook/theme file.
- **CLI rendering layer** → the `display.*`/`output.*`/`ui.*` helper module, its
  semantic styles and print helpers, spinner/panel/prompt wrappers, and any
  output best-practices doc.
- **Message composition layer** → the helpers/templates that build outbound
  messages, their envelope kinds (DM/channel/thread/edit), and any documented
  voice/brand-naming rules (often in `AGENTS.md` or a skill doc).
- **Brand/style guide** → any `BRAND*.md` / `STYLE*.md` doc, plus accessibility
  rules documented in `AGENTS.md`/`CLAUDE.md`.

A repo MAY combine sources (a Tailwind config + a brand doc + a CLI display
module). Read all that exist; **the real files win** over any preset assumption.

### Step 2 — Reason out each canonical section, per accepted profile
Using `templates/DESIGN.md.md`, fill each accepted profile's sections from its
design source (`SPEC.md` §4):

- **`visual-ui`** — Overview/atmosphere · Color palette & roles (light + dark) ·
  Typography · Layout & spacing · Elevation & depth · Shapes/radius · Components
  (in terms of the tokens) · Responsive behavior · Do's & don'ts (incl. the
  repo's accessibility rules).
- **`cli-output`** — Output voice & intent · Semantic colors & styles (success/
  error/warning/info/highlight/dim mapped to the real theme) · Output components
  (panels, tables, spinners, progress, prompts — named after the real helpers) ·
  Layout conventions · Degradation & environment (TTY vs pipe, `NO_COLOR`,
  stdout/stderr, exit codes) · Do's & don'ts.
- **`conversational`** — Voice & register (tone, brevity, brand naming) ·
  Message anatomy (envelope kinds + structure) · Platform rendering (only the
  platforms the repo actually targets) · Do's & don'ts.

One Overview and one Agent prompt guide serve the whole file (§4.1). Express
values as **named tokens with usage notes**; add a machine-readable token block
only if the repo already maintains structured tokens. Flag any value you had to
**infer** so a human can confirm it.

### Step 3 — Write or reconcile `DESIGN.md`, then index it in `AGENTS.md`
- Choose the location (`SPEC.md` §2): if the repo has a `docs/` tree (DWP-native),
  write **`docs/DESIGN.md`** alongside the other specs; if it has no `docs/` tree,
  write `./DESIGN.md` at the root. **Never** create sibling per-surface files
  (`CLI_DESIGN.md`, `CONVERSATION_DESIGN.md`) — one repo, one `DESIGN.md`.
- If no `DESIGN.md` exists → write it at the chosen location. A single accepted
  profile keeps its sections at the top level; multiple accepted profiles get
  one top-level heading per profile (§4.1).
- If one already exists → **reconcile additively** (`SPEC.md` §6): keep working
  values, add missing canonical sections — and when adding a **new profile** to
  an existing file, append its sections (grouping per §4.1) without rewriting
  the existing content. Ask before any destructive change.
- **Index it in `AGENTS.md`** (and therefore `CLAUDE.md`): add a reference to
  `DESIGN.md` in the documentation index so agents discover it like the other
  `docs/` specs. This pointer — not the physical location — is what guarantees
  discovery (`SPEC.md` §2).

### Step 4 — Validate (the gate)
Run the validation step (`SPEC.md` §11):
- `DESIGN.md` exists at the chosen location (`docs/DESIGN.md` or root) with all
  canonical sections **for each accepted profile**, and **`AGENTS.md` references
  it**; no sibling per-surface files were created.
- Every documented value traces to the real design source (spot-check a few
  against the stylesheet/config/display module/message helpers); inferred
  values flagged.
- Per-profile integrity (`SPEC.md` §7): text-color pairings meet **WCAG AA**
  (`visual-ui`); color is not the sole carrier of meaning and degradation rules
  are documented (`cli-output`); rich renderings note plain-text fallbacks
  (`conversational`); token references resolve (no orphans/broken refs).
- New profiles were **asked about** before applying — never auto-applied.
- File is Markdown-first and compact (~2–5K tokens single-profile, ≤ ~8K
  multi-profile); no build dependency added.

### Step 5 — (Optional) install the `/design-system` delegator
If the developer wants a one-command refresh later, install a `/design-system`
delegator into the repo's `.agents/commands/` (template:
`templates/design-system-command.md`) that re-runs this addon. Skip if not wanted —
a declined command leaves a baseline-conformant repo.

## Failure-mode guardrails

- **Never required, never blocking.** If the developer declines, stop cleanly.
- **Interface surfaces only.** Skip for repos with no interface surface of any
  kind (pure library, headless service, infra-only) — applying it there is a defect.
- **Ask before new profiles.** `cli-output` and `conversational` are never
  auto-applied, even in trust mode; only `visual-ui` is default-on when detected.
- **Reason about the source.** Document the repo's real values; never paste a
  brand file or another product's conventions.
- **One file.** Profiles stack inside `DESIGN.md`; never create per-surface siblings.
- **Reconcile, don't clobber.** Preserve a working `DESIGN.md`; ask before destructive edits.
- **Protect integrity.** Capture the repo's contrast rules (visual), degradation
  rules (CLI), and plain-text fallbacks (conversational); don't document failing patterns.
- **Reference, don't hard-bind.** Follow the convention's shape, not its Alpha format details.
