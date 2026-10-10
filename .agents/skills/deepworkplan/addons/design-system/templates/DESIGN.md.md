# Reasoning template — `DESIGN.md` skeleton

This is the **annotated skeleton** the addon fills by **reasoning about the target
repo's real design source** (stylesheet, Tailwind config, token files, component
styles — or a CLI display/theme module, or message-composition helpers). The
*shape* below is fixed; every *value* is derived from the repo — see `SPEC.md`
§4–§5. Replace each `> how to fill` note with real content and delete the notes.
Keep the result compact (~2–5K tokens single-profile, ≤ ~8K multi-profile) and
Markdown-first.

> **Do not** paste a third-party brand's `DESIGN.md` here, and do not import
> another CLI's or bot's conventions wholesale. Reference catalogs are
> inspiration for structure only.

**Profile composition (`SPEC.md` §4.1):** a repo with **one** accepted profile
keeps that profile's sections at the top level (for `visual-ui` that is exactly
the pre-profile shape). A repo with **several** accepted profiles groups each
profile's sections under one top-level heading (`## Visual UI`, `## CLI output`,
`## Conversational`). Either way the file carries exactly **one** Overview at the
top and exactly **one** Agent prompt guide at the end.

---

## Shared sections (always exactly one of each)

```markdown
# DESIGN.md — {Project} design system

> Interface-design context for AI coding agents. When generating or editing any
> user-facing output in this repo — UI, terminal output, outbound messages —
> follow this file. Prefer the named tokens below over ad-hoc values.

## Overview
> how to fill: one short paragraph — product personality, tone, the design's
> intent, and WHICH interface surfaces this file covers. Pull from the
> brand/style guide if one exists; otherwise infer and flag it.

<!-- …profile sections (below) go here… -->

## Agent prompt guide
> how to fill: see templates/agent_prompt_guide.md — a short "how to use this
> file" block for downstream agents, covering every profile in the file.
```

---

## Profile: `visual-ui` sections

```markdown
## Colors
> how to fill: read the real palette (Tailwind theme colors / CSS `--` vars / token
> file). List SEMANTIC roles + values + usage. Include dark-mode variants if the repo
> supports dark mode. Note which pairings are for text (and their contrast).

| Token | Value (light) | Value (dark) | Role / usage |
|-------|---------------|--------------|--------------|
| `color.bg` | `#…` | `#…` | Page background |
| `color.text` | `#…` | `#…` | Primary body text |
| `color.accent` | `#…` | `#…` | Primary actions / links |
| `color.muted` | `#…` | `#…` | Secondary text (must meet WCAG AA) |
| … | | | |

## Typography
> how to fill: real font families + the type scale (size / weight / line-height) and
> when each level is used. Source: font config + heading/body styles.

| Level | Family | Size / weight / line-height | Used for |
|-------|--------|-----------------------------|----------|
| Display | `…` | `…` | Hero / h1 |
| Heading | `…` | `…` | h2–h4 |
| Body | `…` | `…` | Paragraphs |
| Mono | `…` | `…` | Code |

## Layout & spacing
> how to fill: base spacing unit + steps, container/grid strategy, whitespace rules.

- Spacing scale: `{base}` → `{steps}`
- Container / grid: `…`
- Whitespace principle: `…`

## Elevation & depth
> how to fill: shadow/surface hierarchy, how depth is expressed (or "flat, hairline
> rules instead of shadows" if that's the system).

## Shapes
> how to fill: border-radius scale + corner language; border/hairline treatment.

## Components
> how to fill: the repo's key UI patterns described IN TERMS OF the tokens above,
> with interaction states. Cover the components that actually exist.

- **Button (primary):** bg `color.accent`, text `…`, radius `…`, states: hover `…`, focus `…`, disabled `…`
- **Input:** …
- **Card / surface:** …
- **Nav / header:** …

## Responsive behavior
> how to fill: real breakpoints (from the config) + touch-target expectations.

| Breakpoint | Min width | Notes |
|------------|-----------|-------|
| sm | `…` | |
| md | `…` | |
| lg | `…` | |

## Do's and Don'ts
> how to fill: explicit guardrails INCLUDING the repo's accessibility rules
> (approved/forbidden colors, contrast targets). Pull from AGENTS.md / CLAUDE.md.

- DO use the tokens above; DO keep text contrast at WCAG AA (4.5:1 / 3:1).
- DON'T introduce new colors/fonts outside this file.
- DON'T `{repo-specific forbidden patterns}`.
```

---

## Profile: `cli-output` sections

```markdown
## Output voice & intent
> how to fill: how the tool talks in the terminal — terse vs verbose, emoji
> policy, capitalization, error-message register. Source: existing output +
> any display best-practices doc.

## Semantic colors & styles
> how to fill: the repo's REAL theme — the styles its rendering library
> (rich/chalk/lipgloss/…) actually defines. Map role → style → usage; never
> invent ad-hoc colors.

| Role | Style (real) | Used for |
|------|--------------|----------|
| success | `…` (e.g. green bold) | completed operations |
| error | `…` | failures (stderr) |
| warning | `…` | recoverable issues |
| info | `…` | neutral status |
| highlight | `…` | emphasis (names, counts) |
| dim | `…` | secondary detail |

## Output components
> how to fill: the repo's rendering patterns, NAMED AFTER the real helpers in
> the display module (`print_success`, `print_panel`, spinners, tables,
> interactive prompts/pickers). Cover what actually exists, with when-to-use.

- **`{helper}`** — `…` (when to use)
- **Status spinner** — wraps `…` (e.g. HTTP calls)
- **Interactive prompt / picker** — `…`

## Layout conventions
> how to fill: blank-line policy, indentation, width handling, panel vs
> one-liner decision rule.

## Degradation & environment
> how to fill: TTY vs piped output, NO_COLOR / forced color, narrow terminals,
> stdout-vs-stderr discipline, exit-code conventions, quiet/JSON modes — only
> the behaviors the repo really implements.

## Do's and Don'ts
> how to fill: the integrity guardrails (SPEC §7) + repo rules, e.g.:

- DO route all output through `{display module}`; DON'T raw-`print()` outside it.
- DON'T use color as the only carrier of meaning (piped / NO_COLOR output must stay legible).
- DON'T `{repo-specific forbidden patterns}`.
```

---

## Profile: `conversational` sections

```markdown
## Voice & register
> how to fill: tone, person, brevity targets, language policy, and EXACT
> brand-name spellings for outbound messages. Source: message helpers + any
> documented voice rules (AGENTS.md, skill docs).

## Message anatomy
> how to fill: the envelope kinds the product sends (DM, channel post, thread
> reply, edit-in-place) and the structure of each — length targets, what a
> message leads with, what is never included.

| Envelope | Structure | Notes |
|----------|-----------|-------|
| DM | `…` | |
| Channel post | `…` | |
| Thread reply | `…` | |
| Edit-in-place | `…` | stable message-id semantics |

## Platform rendering
> how to fill: ONLY the platforms the repo actually targets — how the same
> message renders on each (Slack mrkdwn, Discord markdown, Teams adaptive
> cards, Google Chat, email HTML/plain). Note the plain-text fallback.

| Platform | Rendering | Fallback |
|----------|-----------|----------|
| `…` | `…` | `…` |

## Do's and Don'ts
> how to fill: audience guardrails + integrity rules (SPEC §7), e.g.:

- DO describe outcomes for the audience; DON'T expose internals (plan IDs, file paths, tool names) unless the audience is technical by design.
- DO spell brand names exactly as documented above.
- DON'T document a rich rendering without its plain-text fallback.
```

---

## After filling

Run the validation step (`SPEC.md` §11): all sections present for each accepted
profile; values traceable to the repo; inferred values flagged; per-profile
integrity holds (WCAG AA pairings / degradation rules / plain-text fallbacks);
token references resolve; one Overview + one Agent prompt guide; file compact
and Markdown-first; no per-surface sibling files.
