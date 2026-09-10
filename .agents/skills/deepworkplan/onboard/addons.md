# DeepWorkPlan — Onboard: optional addons (read only in Phase 7b)

Verbatim from the main procedure. Addons are **opt-in**: a repository is fully
conformant with zero addons, and none is required to create or execute plans.
Read this file only to make the Phase 7b offer; never enable an addon without
the developer's explicit acceptance of that addon's offer.

## Phase 7b — Offer optional addons (opt-in)

After the core AI-first scaffolding, **enumerate** the available addons under
`../addons/` and offer each as an **explicit opt-in** step. Addons are **never
required** — a repo is fully conformant with zero addons. In **trust mode**, you
MAY recommend the obviously-applicable ones, but still surface them.

Five addons ship today; enumerate **all** and offer each independently:

| Addon | Folder | Recommend in trust mode when… |
|-------|--------|-------------------------------|
| **Devcontainer support** | [`../addons/devcontainer/`](../addons/devcontainer/SKILL.md) | the repo benefits from a reproducible isolated dev container (most repos with Docker/services). |
| **Dailybot integration** | [`../addons/dailybot/`](../addons/dailybot/SKILL.md) | the developer/team **already uses Dailybot** or asks for team progress reporting — **do NOT auto-install for everyone**. |
| **Dependency upgrade** | [`../addons/dependency-upgrade/`](../addons/dependency-upgrade/SKILL.md) | the repo has a lockfile + a dependency-heavy stack and wants safe, batched, validated upgrades — recommend only when a lockfile is present; **never auto-install for everyone**. |
| **Design system** | [`../addons/design-system/`](../addons/design-system/SKILL.md) | the repo has a **user-facing interface surface**, detected per profile: **visual-ui** (stylesheet with CSS custom properties, Tailwind config or `@theme` block, UI components, brand/style guide) is **default-on when detected** — in trust mode **apply** it (generate `DESIGN.md`), in guided mode **strongly recommend** and ask; **cli-output** (a CLI rendering library + a deliberate display layer) and **conversational** (a chat SDK or message-composition layer) are **recommended when detected, always asked, never auto-applied**. **Never offer for a repo with no interface surface** (pure library, headless service, infra-only). |
| **AI Diff Reviewer** | [`../addons/ai-diff-reviewer/`](../addons/ai-diff-reviewer/SKILL.md) | the developer/team wants structured local code review on the DWP Final Review's security pass and/or a CI PR merge gate — **do NOT auto-install for everyone**; always ask Flow A (local-only) vs Flow B (dual-surface), never default. |

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

The fifth addon is **AI Diff Reviewer**
([`../addons/ai-diff-reviewer/SKILL.md`](../addons/ai-diff-reviewer/SKILL.md) +
[`SPEC.md`](../addons/ai-diff-reviewer/SPEC.md)). Offer it **only when relevant** —
the developer or team wants structured code-review quality on DWP work, a local
pre-push review, and/or a CI PR merge gate; in trust mode recommend it **only**
on that signal and **never auto-install it for everyone**. If accepted: read
that addon's `SKILL.md` and run its flow — **ask Flow A (local-only) vs Flow B
(dual-surface) explicitly and NEVER default** (matches the upstream skill's
ambiguity tie-break); detect whether the vendored skill / extension file /
`pr-review.yml` already exist (reconcile-don't-clobber); offer the **opt-in**
vendored-skill install via
`npx --yes skills add DailybotHQ/ai-diff-reviewer@v2.0.0 --skill ai-diff-reviewer -y`
(**tag-pinned**; both `--yes` and `-y` required); in Flow B hand off CI-workflow authoring to
the upstream `setup` sub-skill (never invent credentials — `CURSOR_API_KEY` /
provider secrets are the consumer's responsibility); wire the security pass of
the mandatory DWP **Final Review** to run the upstream parent default flow as an
additive local-review pass; and (Flow B only) surface `apply-review` as an optional
developer-invoked companion during `execute`. Every **local** augmentation is
strictly **best-effort and never blocks** the work if the skill or extension is
absent or the local review invocation errors — an unset CI provider secret does
**not** skip the local security pass (Flow B CI/gate only). The core
DeepWorkPlan methodology has **zero AI Diff Reviewer dependency** — this addon
is purely optional review quality. After applying,
run the addon's validation step (SPEC §9). If declined, skip it and continue —
the repo stays baseline-conformant.
