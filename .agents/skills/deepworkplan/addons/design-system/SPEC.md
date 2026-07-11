# SPEC.md — Design-System Addon (Normative)

## Abstract

This document is the **normative specification** of the DeepWorkPlan
**design-system addon**: an opt-in capability that gives a repository with a
**user-facing interface surface** a **`DESIGN.md`** — placed under **`docs/`**
alongside the repo's other specs and indexed from `AGENTS.md` — a Markdown
design-system file that any coding agent reads to generate interface output
**consistent with the repo's own conventions**. It defines the
**interface-surface gate** (RFC-2119) and its three **profiles** (visual UI,
CLI output, conversational), the **location + `AGENTS.md` discovery** rule, the
**canonical sections** a `DESIGN.md` MUST carry per profile, the
**reason-don't-copy** rule, the **reconcile-don't-clobber** behavior, the
**pragmatic-reference** posture toward the upstream convention, the
**onboarding hook**, and the **validation** step.

The addon is **stack-aware**: it reasons about the repo's **actual** design
source (CSS custom properties, a Tailwind config, design-token files, component
styles — or a CLI rendering layer, or message-composition conventions) rather
than copying a third-party brand file. It is governed by `../README.md` and
`methodology-spec/ADDONS.md`: it is **never** required for baseline AI-first
conformance — a repo with zero addons is fully conformant.

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 2.2.0 |
| **Status** | Stable |
| **Companions** | `SKILL.md`, `templates/DESIGN.md.md`, `templates/presets.md`, `templates/agent_prompt_guide.md`, `../README.md`, `methodology-spec/ADDONS.md` |
| **License** | MIT |

> **Divergence from 2.1.0.** Version 2.1.0 was **frontend/UI-scoped** and had a
> hard exclusion: a CLI or backend repo MUST have the addon skipped. Version
> 2.2.0 generalizes the gate to **interface surfaces** and introduces
> **profiles** (§3). The change is **additive and backwards compatible**: a
> `DESIGN.md` produced under 2.1.0 is a valid single-profile (`visual-ui`)
> `DESIGN.md` under 2.2.0, with **zero** migration required, and the visual
> profile's recommendation strength is unchanged.

## 1. Conventions

The RFC 2119 keywords (**MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**,
**MAY**, **OPTIONAL**) are interpreted as in
[RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

Throughout, **`DESIGN.md`** is the design-system file this addon produces (at
`docs/DESIGN.md` by default, §2); an **interface surface** is any boundary
where the product meets a person (a rendered visual UI, styled terminal
output, or messages the product sends on a chat/email platform); a
**profile** is the per-surface flavor of the addon (§3); a **token** is a
named design value — for a visual surface a color, a type size, a spacing
step, a radius, an elevation; for a CLI surface a semantic style (success,
error, warning, dim) or an output component; for a conversational surface a
voice rule or a message-shape convention; and the **design source** is the
repo's real origin of those values (a stylesheet, a Tailwind config, a token
file, the component styles, a CLI display/theme module, or
message-composition helpers and their docs).

---

## 2. What the Addon Provides

- The addon **MUST** produce a single **`DESIGN.md`** — a Markdown file,
  human-authorable and LLM-legible, that documents the repo's interface
  conventions so an agent generating interface output follows them instead of
  inventing statistically-common defaults. It **MUST** be version-controlled
  and reviewable in pull requests.
- The addon **MUST NOT** produce sibling files per surface (no `CLI_DESIGN.md`,
  no `CONVERSATION_DESIGN.md`): one repo, one `DESIGN.md`. Multiple accepted
  profiles stack as sections inside the same file (§4.1) — `DESIGN.md` is the
  canonical name agents discover.
- **Location (DWP-native default):** in a repo that follows the DWP documentation
  standard — specs/docs centralized under `docs/` and indexed by `AGENTS.md` —
  `DESIGN.md` **SHOULD** live at **`docs/DESIGN.md`**, alongside the other specs
  (`ARCHITECTURE.md`, `STANDARDS.md`, `PRODUCT_SPEC.md`, …), **not** scattered at
  the root. A repo with **no** `docs/` tree (or one mirroring the upstream
  root convention) **MAY** instead place it at the repo root (`./DESIGN.md`).
- **Discovery is by reference, not by physical location.** Wherever it lives, the
  addon **MUST** ensure `AGENTS.md` (and therefore `CLAUDE.md`) **references**
  `DESIGN.md` in its documentation index, so any agent discovers it the same way it
  discovers the rest of the `docs/` specs. The location matters less than the
  `AGENTS.md` pointer being present.
- The file **SHOULD** stay compact: roughly 2–5K tokens for a single-profile
  repo, and **SHOULD NOT** exceed roughly 8K tokens even when all three
  profiles apply — it must fit comfortably in an agent's context window
  alongside the task.
- The addon **MUST NOT** introduce a build dependency, a plugin, or an external
  source of truth; `DESIGN.md` is plain Markdown readable by any agent.

---

## 3. Interface-Surface Gate (the part the addon reasons about)

- The addon is **interface-surface-scoped**. It **MUST** be offered (and
  applied) only when the repo has at least one **user-facing interface
  surface**, detected as one or more of the **profiles** below.
- The agent **MUST** detect each profile from **real files** — never from the
  repo's name or archetype alone:

### 3.1 Profile: `visual-ui` — rendered visual interfaces

| Signal | Example evidence |
|--------|------------------|
| Stylesheet / tokens | `*.css`, `*.scss`, CSS custom properties, a `tokens.*` / `theme.*` file |
| Utility/theme config | `tailwind.config.*`, a Tailwind v4 `@theme` block in CSS, CSS-in-JS theme |
| UI components | `.jsx`/`.tsx`/`.vue`/`.svelte`/`.astro` components, a component library |
| Design assets | a brand/style guide doc, a design-tokens export, a Figma reference |

### 3.2 Profile: `cli-output` — styled terminal interfaces

| Signal | Example evidence |
|--------|------------------|
| CLI/TUI rendering library | `rich`, `textual`, `questionary` (Python); `chalk`, `ink`, `ora`, `prompts` (Node); `lipgloss`, `bubbletea` (Go); `colored`, `ratatui`, `indicatif` (Rust) |
| A deliberate rendering layer | a `display.*` / `output.*` / `ui.*` helper module that centralizes printing; semantic print helpers (`print_success`, `print_error`, …) |
| Output conventions doc | an output/display best-practices doc; documented spinner/panel/prompt patterns |
| Interactive prompts | a picker/menu/confirm layer (questionary, inquirer, survey) |

  A bare argument parser whose output is unstyled raw prints is a **weak**
  signal: the profile **SHOULD NOT** be offered when there is no deliberate
  rendering layer to document.

### 3.3 Profile: `conversational` — the product talks on a messaging surface

| Signal | Example evidence |
|--------|------------------|
| Chat-platform SDK | `slack-sdk`/Bolt, `discord.js`/`discord.py`, `botbuilder` (Teams), Google Chat / Telegram / WhatsApp SDKs |
| Message composition layer | helpers or templates that build outbound messages (reports, notifications, replies); stable message-id / edit semantics |
| Voice conventions | documented tone/brevity/brand-naming rules for outbound messages (e.g. in `AGENTS.md` or a skill doc) |
| Other messaging surfaces | transactional email templates, SMS, voice/IVR prompt flows |

### 3.4 The gate

- A repo with **no** interface surface of any kind — a pure library with no
  rendered output, a headless backend service, an infrastructure-only repo —
  **MUST** have this addon **skipped**; applying it there is a defect.
- A repo **MAY** match several profiles (a web app with an ops CLI; a Slack bot
  with an admin UI). Detection **MUST** evaluate each profile independently,
  and each detected profile is offered independently (§3.5); the accepted
  profiles compose into the single `DESIGN.md` (§4.1).
- The addon is **archetype-agnostic** (`ARCHETYPES.md`): it MAY be layered onto an
  individual repo or onto a sub-repo of an orchestrator hub. No archetype is
  excluded a priori — only the absence of any interface surface excludes a repo.
- **Backwards compatibility:** a `DESIGN.md` created before profiles existed is
  a valid single-profile `visual-ui` file. Re-running the addon on such a repo
  **MUST NOT** require restructuring it; new profiles are only **added** when
  detected and accepted (§6).

### 3.5 Recommendation Strength — per profile

This addon is **never** part of the zero-addon baseline (a repo with no addons
is fully conformant — `ADDONS.md` §2). When a profile's signal **is** detected,
its recommendation strength differs:

- **`visual-ui` — default-on when detected** (unchanged from 2.1.0):
  - In **trust mode**, the `onboard` flow **SHOULD apply** the profile
    automatically (generate `DESIGN.md`), the same way it applies other
    detected-and-applicable setup — the developer **MAY** still decline.
  - In **guided mode**, the flow **MUST** present it as a **strong
    recommendation** and ask before applying.
- **`cli-output` and `conversational` — recommend when detected**:
  - In **both** modes, the flow **MUST** present the detected profile as a
    recommendation and **MUST ask** before applying — it **MUST NOT** be
    auto-applied, even in trust mode. These profiles document conventions that
    are less universal than visual design tokens; the developer confirms the
    repo's rendering/voice layer is worth capturing.
- When a profile's signal is **not** detected, the flow **MUST NOT** offer that
  profile; when **no** profile is detected, the flow **MUST NOT** offer the
  addon at all (§3.4).
- Declining — any profile, or all of them — **MUST** always remain possible,
  and a declined addon **MUST** leave a fully baseline-conformant repo.
  "Default-on when detected" raises the *default* for the visual profile; it
  does **not** make the addon mandatory.

This keeps `design-system` in the **strongest conditional tier** among the
addons for visual repos — because a repo that *has* a design system almost
always benefits from capturing it as `DESIGN.md` — while the newer profiles
earn their way in explicitly.

---

## 4. Canonical Sections of `DESIGN.md`

### 4.1 Profile composition (one file, stacked sections)

- A **single-profile** `DESIGN.md` carries that profile's canonical sections at
  the top level — exactly the 2.1.0 shape for `visual-ui`.
- A **multi-profile** `DESIGN.md` **MUST** group each accepted profile's
  sections under one top-level heading per profile (e.g. `## Visual UI`,
  `## CLI output`, `## Conversational`), in any order that fits the repo.
- The file **MUST** carry exactly **one** Overview and exactly **one** Agent
  Prompt Guide for the whole file, regardless of profile count; Do's & Don'ts
  **MAY** be per profile or combined, as long as every profile's guardrails are
  present.
- Section titles MAY be adapted to the repo's voice; the substance MUST be
  present. Each section is **filled by reasoning about the design source**,
  never copied from a brand file or another product's conventions.

### 4.2 `visual-ui` canonical sections

1. **Overview / Atmosphere** — brand personality, emotional tone, the design's
   intent in one short paragraph.
2. **Color Palette & Roles** — semantic colors (primary, secondary, neutral,
   surface, accent, state colors) with values **and** their functional role; light
   and dark variants where the repo supports dark mode.
3. **Typography** — font families, the type scale (sizes/weights/line-heights), and
   when each level is used.
4. **Layout & Spacing** — the spacing scale (base unit + steps), grid/container
   strategy, and whitespace principles.
5. **Elevation & Depth** — shadow/surface hierarchy and how depth is expressed.
6. **Shapes** — border-radius scale and corner language; border/hairline treatment.
7. **Components** — the repo's key UI patterns (buttons, inputs, cards, nav, …)
   described in terms of the tokens above, including interaction states.
8. **Responsive Behavior** — breakpoints and touch-target expectations.
9. **Do's and Don'ts** — explicit guardrails for agent behavior, including
   **accessibility constraints** the repo enforces (see §7).
10. **Agent Prompt Guide** — a short "how to use this file" block telling a
    downstream agent to follow `DESIGN.md` and how to reference tokens.

### 4.3 `cli-output` canonical sections

1. **Output Voice & Intent** — how the tool talks in the terminal: terse or
   verbose, emoji policy, capitalization, error-message register.
2. **Semantic Colors & Styles** — the success/error/warning/info/highlight/dim
   roles mapped to the repo's **real** theme (the rich/chalk/lipgloss styles
   actually defined), never raw color names chosen ad hoc.
3. **Output Components** — the repo's rendering patterns: panels vs plain
   lines, tables, status spinners, progress bars, interactive prompts and
   pickers — named after the real helpers (`print_success`, `print_panel`, …).
4. **Layout Conventions** — blank-line policy, indentation, width handling,
   when to use a panel vs a one-liner.
5. **Degradation & Environment** — TTY vs piped output, `NO_COLOR`/forced
   color, narrow terminals, stdout-vs-stderr discipline, exit-code
   conventions, quiet/JSON output modes where they exist.
6. **Do's and Don'ts** — guardrails such as "all output goes through the
   display helper, never raw `print()` outside it" and the integrity rules
   of §7.
7. **Agent Prompt Guide** — shared with the file (§4.1).

### 4.4 `conversational` canonical sections

1. **Voice & Register** — tone, person, brevity targets, language policy, and
   **brand-naming rules** (exact product spellings) for outbound messages.
2. **Message Anatomy** — the envelope kinds the product sends (DM, channel
   post, thread reply, edit-in-place) and the structure of each: length
   targets, what a report leads with, what is never included.
3. **Platform Rendering** — how the same message renders per platform the repo
   **actually targets** (e.g. Slack `mrkdwn`, Discord markdown, Teams adaptive
   cards, Google Chat, email HTML/plain text). One section; per-platform rows.
4. **Do's and Don'ts** — guardrails such as audience rules (describe outcomes,
   never internals like plan IDs or file paths), brand-name spelling, and the
   plain-text-fallback rule of §7.
5. **Agent Prompt Guide** — shared with the file (§4.1).

- Values **SHOULD** be expressed as **named tokens** with human-readable usage
  notes; the file **MAY** additionally carry a machine-readable token block
  (e.g. front matter) when the repo already maintains structured tokens, but a
  Markdown-first table is sufficient and preferred for authorability.

---

## 5. Reason, Don't Copy

- Every value in `DESIGN.md` **MUST** be **derived from the repo's real design
  source** — the stylesheet, Tailwind config, token files, or component styles;
  the CLI display/theme module and its helpers; the message-composition layer
  and its documented voice rules — whatever actually exists.
- The addon **MUST NOT** paste a third-party brand's `DESIGN.md` (e.g. a catalog
  entry for Stripe, Linear, or any other product) into the target repo, and
  **MUST NOT** import another CLI's or bot's conventions wholesale. Reference
  catalogs are **inspiration for structure**, never the content.
- When a value is genuinely undefined in the repo, the addon **SHOULD** infer the
  most consistent value from existing usage and **MUST** flag it as inferred (so a
  human can confirm), rather than fabricate an unrelated value.

---

## 6. Reconcile, Don't Clobber

- If a `DESIGN.md` (or an equivalent design-token source) **already exists**, the
  addon **MUST** reconcile additively — preserving values that already work and
  bringing the rest toward the canonical-section shape.
- Adding a newly accepted profile to an existing `DESIGN.md` **MUST** be
  additive: append the new profile's sections (grouping per §4.1 when the file
  becomes multi-profile) without rewriting the existing profile's content.
- The addon **MUST NOT** overwrite or delete an existing `DESIGN.md` or token file
  wholesale. Per `AGENT_PROTOCOL.md`, any destructive change to an existing file
  **MUST** be approved by the developer first.
- The addon **MUST** record what it changed (added sections/profiles, reconciled
  values, inferred values flagged for confirmation).

---

## 7. Accessibility & Output Integrity

- The Do's and Don'ts **MUST** capture the repo's **real accessibility and
  integrity rules** when the repo documents them, so agents do not regress them.
- **`visual-ui`:** documented color pairings intended for text **SHOULD** meet
  **WCAG AA** contrast (4.5:1 normal, 3:1 large) and the addon **SHOULD**
  sanity-check the pairings it documents.
- **`cli-output`:** color **MUST NOT** be documented as the sole carrier of
  meaning (output must stay legible when piped or with `NO_COLOR`); where the
  repo honors `NO_COLOR`/TTY detection, the degradation rules **MUST** be
  documented (§4.3.5).
- **`conversational`:** every documented rich rendering (blocks, cards, HTML)
  **SHOULD** have a plain-text fallback noted for platforms or clients that
  strip formatting.
- Token references inside `DESIGN.md` **MUST** resolve — no orphaned or broken
  references: a component referencing an undefined token, a documented CLI
  helper that does not exist in the code, or a documented platform the repo
  does not actually target.

---

## 8. Pragmatic Reference, Not Hard Binding

- The addon **references** the emerging `DESIGN.md` convention (introduced by
  Google Stitch; popularized by community catalogs) as the **shape** to follow, but
  **MUST NOT** hard-bind to that convention's evolving/Alpha format details. The
  `cli-output` and `conversational` profiles extend that shape to non-visual
  surfaces while keeping the same file and discovery convention.
- DWP's `DESIGN.md` is **Markdown-first**; adopting any specific machine-readable
  token schema (e.g. W3C Design Tokens front matter) is **OPTIONAL** and applied
  only when it fits the repo.

---

## 9. Onboarding Hook + Optional `/design-system` Delegator

- The addon's onboarding hook (`SKILL.md`) is offered by `onboard` Phase 7b as an
  **opt-in** step, **only for repos with a detected interface surface** (§3),
  profile by profile (§3.5), and **MUST NOT** be applied without acceptance. A
  declined addon leaves a baseline-conformant repo.
- The addon **MAY** install a `/design-system` delegator command into the target
  repo's `.agents/commands/` (to regenerate/refresh `DESIGN.md` later; template:
  `templates/design-system-command.md`). Installing the command is **OPTIONAL**; a
  declined addon installs **no** command.

---

## 10. Relationship to Per-Feature Design Docs (positioning)

- This addon provides a **repo-level, persistent design-system file**. It is
  **distinct** from a **per-feature technical design document** (the
  "requirements → design → tasks" `design.md` of tool-bound spec-driven workflows).
- DeepWorkPlan deliberately does **not** ship a separate per-feature design-doc
  archetype: a DWP plan's README (Goal + Context), each task's Context and
  **Acceptance Criteria**, and the **validation gates** already fulfill the
  per-feature design role. This addon fills the one gap that role does not cover —
  durable, repo-native **interface** design context.

---

## 11. Validation Step (run after applying)

The addon is correctly applied when **all** hold:

1. The repo was confirmed to have at least one **interface surface** (§3), each
   applied profile's signal was **detected from real files**, and the addon was
   **skipped** for repos with no interface surface of any kind.
2. A `DESIGN.md` exists with all canonical sections **for each accepted
   profile** (§4) — at **`docs/DESIGN.md`** for a repo with a `docs/` tree
   (DWP-native default), or at the repo root for a repo without one (§2); no
   sibling per-surface files were created.
3. **`AGENTS.md` references `DESIGN.md`** in its documentation index (so agents
   discover it like the other `docs/` specs) (§2).
4. Every documented value is **traceable to the repo's real design source** (§5);
   no third-party brand file was pasted; inferred values are flagged.
5. An **existing** `DESIGN.md`/token source, if present, was **reconciled** (§6),
   not clobbered — including when a new profile was added to it; destructive
   changes were approved.
6. Per-profile integrity holds (§7): documented text color pairings meet
   **WCAG AA** (`visual-ui`); color is not the sole carrier of meaning and
   degradation rules are documented (`cli-output`); rich renderings note
   plain-text fallbacks (`conversational`); token references **resolve**
   (no orphans/broken refs) in every profile.
7. The file is Markdown-first and compact (§2); no build dependency was
   introduced.
8. New profiles (`cli-output`, `conversational`) were **asked about** before
   applying — never auto-applied, even in trust mode (§3.5).
9. If a `/design-system` delegator was offered and accepted, it exists in the
   repo's `.agents/commands/`; if declined, none was installed (§9).

---

## 12. References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)
- `SKILL.md` (the onboarding hook + flow), `templates/*` (reasoning aids)
- `../README.md` (addon mechanism), `methodology-spec/ADDONS.md` (concept + pointer)
- `AGENT_PROTOCOL.md` (approval gates), `ARCHETYPES.md` (archetypes)
- [W3C Design Tokens](https://www.w3.org/community/design-tokens/) (optional token schema)
- [NO_COLOR](https://no-color.org/) (CLI color-suppression convention)

---

*Part of the DeepWorkPlan methodology v2.1.0, MIT License, by [Dailybot](https://dailybot.com) / dailybotops.*
