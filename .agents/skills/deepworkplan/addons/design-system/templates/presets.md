# Reasoning presets — where a repo's design source lives

Match the row(s) for the **detected stack** as a *starting checklist* for **where to
read** the repo's real design values, then verify every assumption against the
actual files. **Detected reality wins** — a repo may combine several sources
(and several profiles, `SPEC.md` §3).

> These presets tell you **where to look**, not **what to write**. The values you
> document come from the repo (`SPEC.md` §5), never from this file or a brand catalog.

---

# Profile: `visual-ui`

## Tailwind (v3 config or v4 `@theme`)

- **Tokens:** `tailwind.config.{js,ts,cjs,mjs}` → `theme` / `theme.extend`
  (`colors`, `fontFamily`, `fontSize`, `spacing`, `borderRadius`, `boxShadow`,
  `screens`). For **Tailwind v4**, read the `@theme { --color-…; --font-…; --spacing-…; }`
  block inside the global CSS instead of a JS config.
- **Dark mode:** `darkMode` strategy + `dark:` variants in components.
- **Breakpoints:** `theme.screens` (or `@theme` `--breakpoint-*`).
- **Components:** utility classes in the components reveal real button/input/card patterns.

## CSS variables / vanilla / SCSS

- **Tokens:** `:root { --… }` (and a `.dark`/`[data-theme]` block) in the global
  stylesheet — colors, spacing, radius, shadows, font stacks.
- **Type scale:** heading/body rules; `clamp()` for fluid type.
- **Breakpoints:** `@media (min-width: …)` query values.
- **SCSS:** `$variables` / `@use` token partials (`_tokens.scss`, `_variables.scss`).

## Component library / design tokens

- **Tokens:** a `tokens.{json,ts,js}` / `theme.{ts,js}` export, a Style
  Dictionary / W3C design-tokens file, or a theme provider (`createTheme`, MUI
  theme, Chakra theme, styled-components `ThemeProvider`).
- **Components:** the library's component source + stories (Storybook) show variants
  and states; map these to the Components section.
- **Reference syntax:** if the repo already uses `{path.to.token}`-style refs, mirror
  that in `DESIGN.md`; otherwise plain named tokens are fine.

## Brand / style guide + accessibility rules

- **Brand doc:** any `BRAND*.md`, `STYLE*.md`, or design doc — use for the Overview
  / atmosphere and intent.
- **Accessibility:** contrast targets and approved/forbidden colors are often in
  `AGENTS.md` / `CLAUDE.md` / an accessibility doc — these feed the Do's & Don'ts.

---

# Profile: `cli-output`

## Python CLI (rich / textual / questionary)

- **Theme & styles:** a central display module (`display.py`, `console.py`,
  `output.py`) — a `rich.theme.Theme`, semantic print helpers
  (`print_success`, `print_error`, `print_panel`, …), `Console` configuration.
- **Components:** `Panel`, `Table`, `Status`/spinner wrappers, `Progress`,
  `questionary`/`inquirer` prompt and picker wrappers.
- **Degradation:** `Console(no_color=…)` / `NO_COLOR` handling, TTY checks
  (`sys.stdout.isatty()`), `--quiet`/`--json` flags, stderr usage in error helpers.
- **Conventions doc:** any display/output best-practices doc under `docs/`.

## Node CLI (chalk / ink / ora / prompts)

- **Theme & styles:** a shared `colors.*`/`log.*`/`ui.*` helper wrapping `chalk`
  (or `picocolors`/`kleur`); `ink` components for TUI layouts.
- **Components:** `ora` spinners, `cli-table*`, `boxen` panels,
  `prompts`/`inquirer`/`enquirer` wrappers.
- **Degradation:** `chalk.level` / `FORCE_COLOR` / `NO_COLOR`, `process.stdout.isTTY`,
  `--json` output modes, stderr discipline.

## Go CLI (cobra / lipgloss / bubbletea)

- **Theme & styles:** `lipgloss.Style` definitions (often a `styles.go`/`ui/`
  package); cobra command output helpers.
- **Components:** `bubbletea` models for interactive flows, spinner/table
  components (`bubbles`), confirm/select prompts (`survey`, `huh`).
- **Degradation:** `lipgloss` profile detection, `NO_COLOR`, `-o json`-style flags.

## Rust CLI (clap / colored / indicatif / ratatui)

- **Theme & styles:** `colored`/`owo-colors` usage centralized in an output
  module; `clap` help styling.
- **Components:** `indicatif` progress/spinners, `comfy-table`, `dialoguer`
  prompts, `ratatui` TUI views.
- **Degradation:** `NO_COLOR`/`CLICOLOR` handling, `is_terminal` checks, `--json`.

> **Weak-signal rule (`SPEC.md` §3.2):** a bare argument parser with raw
> unstyled prints is NOT a `cli-output` surface — don't offer the profile when
> there is no deliberate rendering layer to document.

---

# Profile: `conversational`

## Slack (slack-sdk / Bolt)

- **Voice & helpers:** the message-composition layer (report/notify helpers,
  block builders); documented tone/brand-naming rules in `AGENTS.md` or skill docs.
- **Rendering:** `mrkdwn` (`*bold*`, `_italic_`), Block Kit blocks; note the
  `text` plain fallback every block message should carry.
- **Envelopes:** DM vs channel vs thread (`thread_ts`), edit-in-place
  (`chat.update` + stored message ids).

## Discord (discord.js / discord.py)

- **Rendering:** standard markdown (`**bold**`), embeds; plain-content fallback.
- **Envelopes:** channel messages, replies, ephemeral interaction responses.

## Microsoft Teams (botbuilder)

- **Rendering:** Adaptive Cards JSON + the plain-text `text` fallback.
- **Envelopes:** personal vs channel scope, reply chains, activity updates.

## Google Chat / Telegram / WhatsApp

- **Rendering:** per-platform markup subset (Google Chat formatting, Telegram
  MarkdownV2/HTML, WhatsApp limited styling) + plain fallback.

## Email / SMS / voice

- **Rendering:** HTML template + plain-text part (email); length limits (SMS);
  prompt scripts and re-prompt rules (voice/IVR).
- **Voice:** transactional register, sender identity, subject conventions.

> For every platform: document **only** the platforms the repo actually targets
> (`SPEC.md` §7) — a documented platform with no code targeting it is a broken
> reference.

---

## Cross-check before writing

1. Did you read the **actual** design source (not a guess) for each accepted profile?
2. `visual-ui`: are **dark-mode** values captured if the repo supports dark mode? Do the **breakpoints** match the real config?
3. `cli-output`: are the **degradation** behaviors (TTY/pipe, `NO_COLOR`, stderr, exit codes) the ones the code really implements?
4. `conversational`: are the documented **platforms** exactly the ones the repo targets, each with a plain-text fallback?
5. Are the **accessibility/integrity** rules reflected in Do's & Don'ts?
6. Are any **inferred** values flagged for human confirmation?
