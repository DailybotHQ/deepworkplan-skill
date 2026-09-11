# DeepWorkPlan — Onboard: the required local review and the optional addons (read in Phase 7a and 7b)

Verbatim from the main procedure. Five addons ship under `../addons/`. Four are
**opt-in**: a repository is fully conformant with zero optional addons, and none
of them is required to create or execute plans. The fifth — the **AI Diff
Reviewer local review** — is part of the baseline since standard 2.3.0
(`../spec/ADDONS.md` §6.5) and is installed in Phase 7a; only its CI surface is
optional. Read this file to run Phase 7a and to make the Phase 7b offer; never
enable an optional addon without the developer's explicit acceptance of that
addon's offer.

## Phase 7a — Install the AI Diff Reviewer local review (required)

Read [`../addons/ai-diff-reviewer/SKILL.md`](../addons/ai-diff-reviewer/SKILL.md)
and run its flow as a required step, under the Phase 0 onboarding consent:

1. **Reconcile, don't clobber.** Detect an existing vendored skill at
   `.agents/skills/ai-diff-reviewer/`, an extension file at one of the three
   recognized paths (`.review/extension.md` > `.github/ai-diff-reviewer/extension.md`
   > `.github/ai-pr-reviewer/extension.md`), a `.review/.skip-bootstrap`
   marker, and any existing `pr-review.yml`. Fill gaps only.
2. **Install the vendored skill, pinned:**
   `npx --yes skills add DailybotHQ/ai-diff-reviewer@v2.0.1 --skill ai-diff-reviewer -y`
   (both `--yes` and `-y` are required in non-TTY; never an unpinned ref, never
   a remote installer piped to a shell). Assert the vendored `SKILL.md` version
   equals the requested tag.
3. **Bootstrap the extension file** by handing off to the upstream
   `generate-extension` sub-skill ("generate a `.review/extension.md` for this
   repo"). The local review does not run without it.
4. **Flow A is the baseline.** Offer **Flow B** (the CI Action via the upstream
   `setup` sub-skill, `pr-review.yml`, provider secret set by the maintainer)
   as an explicit opt-in — never install it unrequested, never default to it.
5. **Record.** Note in `AGENTS.md` that the local review is installed and
   which flow is active. When the install cannot run here (sandbox, offline)
   or the developer declines, record the reason in the onboarding report and,
   for a decline, a declared exception in `AGENTS.md`; `verify` keeps reporting
   the gap until the reviewer is installed. Run the addon's validation step
   (SPEC §9).

## Phase 7b — Offer optional addons (opt-in)

After Phase 7a, **enumerate** the remaining addons under `../addons/` and offer
each as an **explicit opt-in** step. Optional addons are **never required** — a
repo is fully conformant with zero optional addons. In **trust mode**, you MAY
recommend the obviously-applicable ones, but still surface them.

Five addons ship today; the table lists all of them (the AI Diff Reviewer row
records its Phase 7a status). Offer the four optional ones independently:

| Addon | Folder | Recommend in trust mode when… |
|-------|--------|-------------------------------|
| **Devcontainer support** | [`../addons/devcontainer/`](../addons/devcontainer/SKILL.md) | the repo benefits from a reproducible isolated dev container (most repos with Docker/services). |
| **Dailybot integration** | [`../addons/dailybot/`](../addons/dailybot/SKILL.md) | the developer/team **already uses Dailybot** or asks for team progress reporting — **do NOT auto-install for everyone**. |
| **Dependency upgrade** | [`../addons/dependency-upgrade/`](../addons/dependency-upgrade/SKILL.md) | the repo has a lockfile + a dependency-heavy stack and wants safe, batched, validated upgrades — recommend only when a lockfile is present; **never auto-install for everyone**. |
| **Design system** | [`../addons/design-system/`](../addons/design-system/SKILL.md) | the repo has a **user-facing interface surface**, detected per profile: **visual-ui** (stylesheet with CSS custom properties, Tailwind config or `@theme` block, UI components, brand/style guide) is **default-on when detected** — in trust mode **apply** it (generate `DESIGN.md`), in guided mode **strongly recommend** and ask; **cli-output** (a CLI rendering library + a deliberate display layer) and **conversational** (a chat SDK or message-composition layer) are **recommended when detected, always asked, never auto-applied**. **Never offer for a repo with no interface surface** (pure library, headless service, infra-only). |
| **AI Diff Reviewer** | [`../addons/ai-diff-reviewer/`](../addons/ai-diff-reviewer/SKILL.md) | **not offered here — installed in Phase 7a** (required local review, baseline since 2.3.0). In Phase 7b only confirm the Flow B (CI Action) opt-in decision if it was left open; never install the CI surface unrequested. |

The first addon is **devcontainer support**
([`../addons/devcontainer/SKILL.md`](../addons/devcontainer/SKILL.md) +
[`SPEC.md`](../addons/devcontainer/SPEC.md)). If the developer accepts: read that
addon's `SKILL.md` and run its flow — match a preset in
`../addons/devcontainer/templates/presets.md` to the stack you detected in
Phase 1, then **reason out** a devcontainer adapted to that stack (base image,
user, `workspaceFolder`, supporting services from the app's real dependencies,
ports, public-vs-private secrets handling) while preserving the common skeleton
(AI-CLI persistence volumes for claude/codex/cursor/gh/dailybot + read-only
ssh/gitconfig mounts, `dailybot-project-network`, `DOCKER_DEV_ENV=vscode` →
`sleep infinity`, the `codecheck`/`check`/`fix`/`test` validation aliases, and
project-identity precedence per the addon SPEC §4). An **existing devcontainer
MUST be reconciled, not clobbered** — preserve working ports/network/identity and
only add missing skeleton pieces; back up and ask before any destructive change.
For a **public** repo, the addon also adds a secret-excluding `.dockerignore` and
keeps `.env.example` secret-free. After applying, run the addon's validation step
(SPEC §6). If declined, skip it and continue — the repo stays
baseline-conformant.

The second addon is **Dailybot integration**
([`../addons/dailybot/SKILL.md`](../addons/dailybot/SKILL.md) +
[`SPEC.md`](../addons/dailybot/SPEC.md)). Offer it **only when relevant** — the
developer or team already uses Dailybot, or explicitly wants team progress
reporting; in trust mode, recommend it **only** on that signal and **never
auto-install it for everyone**. If accepted: read that addon's `SKILL.md` and run
its flow — detect whether the Dailybot skill/CLI is already present
(reconcile-don't-clobber), offer the **opt-in** install paths (Dailybot agent
skill via `npx --yes skills add DailybotHQ/agent-skill@v3.10.3 --skill dailybot -y`
/ `npx --yes skills update dailybot -y` / OpenClaw `openclaw skills install dailybot`,
or the Dailybot CLI **>= 3.7.0** via pip / Homebrew / the skill's verified
installer flow), **defer
all authentication** to the Dailybot skill's own consent flow (`shared/auth.md`
— `dailybot login` or `DAILYBOT_API_KEY`; never reinvent or store credentials),
wire the **four lifecycle events** (kickoff, significant task, blocked,
completion) as optional progress reports via the dailybot `report` sub-skill,
and **MAY** offer deterministic hook enforcement (`dailybot hook`, CLI >=
3.7.0). The paired Dailybot skill (**3.10.3**) exposes 14 capabilities (chat,
check-ins, forms authoring, ask AI, per-repo API keys, and more); this addon wires only **report**
into DWP execution. Every report is strictly **best-effort and never blocks**
the work if Dailybot is absent, unauthenticated, or unreachable. The core
DeepWorkPlan methodology has **zero Dailybot dependency** — this addon is purely
optional team visibility.
After applying, run the addon's validation step (SPEC §8). If declined, skip it
and continue — the repo stays baseline-conformant.

The third addon is **dependency upgrade**
([`../addons/dependency-upgrade/SKILL.md`](../addons/dependency-upgrade/SKILL.md) +
[`SPEC.md`](../addons/dependency-upgrade/SPEC.md)). It is **package-manager
agnostic** — offer it when the repo has a lockfile and a dependency-heavy stack;
in trust mode recommend it **only** when a lockfile is present, and **never**
auto-install it for everyone. If accepted: read that addon's `SKILL.md` and run
its flow — detect the repo's real package manager (npm/pnpm/yarn + ncu,
pip/poetry/uv, cargo, go mod, bundler, composer…), classify upgrades by semver,
upgrade in safe batches, run the repo's **real** validation gate after each
batch, revert a failing batch, and summarize. **Only when accepted**, the addon
installs a `/lib-upgrade` delegator into the repo's `.agents/commands/`. After
applying, run the addon's validation step (SPEC §9). If declined, skip it — the
repo stays baseline-conformant and no command is installed.

The fourth addon is **design system**
([`../addons/design-system/SKILL.md`](../addons/design-system/SKILL.md) +
[`SPEC.md`](../addons/design-system/SPEC.md)). It is **interface-surface-scoped**
with per-profile strength (addon SPEC §3, §3.5) — during Phase 1 detection, check
each profile independently from **real files**: **visual-ui** (a stylesheet with
CSS custom properties, a Tailwind config or a Tailwind v4 `@theme {}` block, UI
components (`.tsx`/`.vue`/`.svelte`/`.astro`), a design-token file, or a
brand/style guide); **cli-output** (a CLI/TUI rendering library — rich, chalk,
ink, lipgloss, ratatui — **plus** a deliberate rendering layer such as a
`display.*`/`ui.*` helper module with semantic print helpers; a bare argument
parser with raw prints does NOT qualify); and **conversational** (a chat-platform
SDK — Slack, Discord, Teams, … — a message-composition layer, or documented
outbound-message voice rules). When **visual-ui** is detected, do not merely list
the addon: in **trust mode apply it automatically** (generate `DESIGN.md`,
developer may still decline), and in **guided mode present it as a strong
recommendation** and ask. When **cli-output** or **conversational** is detected,
**recommend it and ask in both modes — never auto-apply** those profiles. When
**no** profile is detected, **do not offer the addon** (a repo with no interface
surface must never get a `DESIGN.md`). Declining always leaves a
baseline-conformant repo. If accepted (or auto-applied): read that addon's
`SKILL.md` and run its flow — locate the repo's **real** design source per
accepted profile, **reason out** that profile's canonical sections of `DESIGN.md`
(visual-ui: colors & roles incl. dark mode, typography, layout & spacing,
elevation, shapes, components, responsive behavior; cli-output: output voice,
semantic colors & styles, output components, layout conventions, degradation &
environment; conversational: voice & register, message anatomy, platform
rendering — each plus do's & don'ts, with one shared Overview and one agent
prompt guide), and write it at **`docs/DESIGN.md`** (alongside the other specs
you generated in Phase 4 — root only if the repo has no `docs/` tree; multiple
accepted profiles stack as sections in the **same single file**, never sibling
files) — **never** copying a third-party brand file. Then **add a `DESIGN.md`
reference to the `AGENTS.md` documentation index** (and `CLAUDE.md`) so agents
discover it like the rest of `docs/`. An **existing `DESIGN.md`/token source MUST
be reconciled, not clobbered** — adding a new profile to an existing file is
additive. After applying, run the addon's validation step (SPEC §11: file at
`docs/DESIGN.md` or root with all sections per accepted profile, AGENTS.md
references it, values traceable to the real source, per-profile integrity —
WCAG AA contrast / degradation rules / plain-text fallbacks — token references
resolve, new profiles were asked about). If declined, skip it — the repo stays
baseline-conformant.

The fifth addon, **AI Diff Reviewer**
([`../addons/ai-diff-reviewer/SKILL.md`](../addons/ai-diff-reviewer/SKILL.md) +
[`SPEC.md`](../addons/ai-diff-reviewer/SPEC.md)), was installed in Phase 7a as
the required local review. Nothing is offered again here except the **Flow B**
CI surface when that question was left open: if the developer wants the CI PR
merge gate, hand off CI-workflow authoring to the upstream `setup` sub-skill
(never invent credentials — `CURSOR_API_KEY` / provider secrets are the
consumer's responsibility) and surface `apply-review` as an optional
developer-invoked companion during `execute`. The core DeepWorkPlan flows have
**zero dependency on a commercial service, CI provider or secret** — the
required local review runs through the developer's own coding agent. If Flow B
is declined, the repo stays on Flow A and is fully conformant.
