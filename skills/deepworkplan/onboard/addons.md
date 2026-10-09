# DeepWorkPlan — Onboard: the required local review and the optional addons (read in Phase 7a and 7b)

Verbatim from the main procedure. Eight active addons ship under `../addons/`.
Seven are **optional**: a repository is fully conformant with zero optional addons, and none
of them is required to create or execute plans. One of the seven — **dependency
upgrade** — is **near-default**: offered for every repo with declared
dependencies, and its **inert** `/lib-upgrade` delegator installs under the
Phase 0 onboarding consent **unless explicitly declined** (an install runs no
upgrade). The other six are signal-gated opt-ins. The eighth — the **AI Diff
Reviewer local review** — is part of the baseline since standard 2.3.0
(`../spec/ADDONS.md` §6.5) and is installed in Phase 7a; only its CI surface is
optional. Read this file to run Phase 7a and to make the Phase 7b offer; never
enable a signal-gated addon without the developer's explicit acceptance of that
addon's offer, and never let an install — near-default included — execute an
upgrade.

## Phase 7a — Install the AI Diff Reviewer local review (required)

Read [`../addons/ai-diff-reviewer/SKILL.md`](../addons/ai-diff-reviewer/SKILL.md)
and run its flow as a required step, under the Phase 0 onboarding consent:

1. **Reconcile, don't clobber.** Detect an existing vendored skill at
   `.agents/skills/ai-diff-reviewer/`, an extension file at one of the three
   recognized paths (`.review/extension.md` > `.github/ai-diff-reviewer/extension.md`
   > `.github/ai-pr-reviewer/extension.md`), a `.review/.skip-bootstrap`
   marker, and any existing `pr-review.yml`. Fill gaps only.
2. **Install the vendored skill, pinned:**
   `npx --yes skills add https://github.com/DailybotHQ/ai-diff-reviewer/tree/v3.3.0 --skill ai-diff-reviewer -y`
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

## Phase 7b — Offer optional addons (trigger only)

After Phase 7a, offer the seven active optional addons in the table below.
Six active addons are
**explicit opt-ins** — signal-gated, installed only on the
developer's explicit acceptance. The seventh, **dependency upgrade**, is
**near-default**: offered for every repo with declared dependencies, with its
inert `/lib-upgrade` delegator installed under the Phase 0 onboarding consent
**unless explicitly declined** (an install runs no upgrade). Optional addons
are **never required** — a
repo is fully conformant with zero optional addons. In **trust mode**, you MAY
recommend the obviously-applicable ones, but still surface them.

**Record each acceptance in the addon registry** (`../spec/CONFIG.md`):
after the developer accepts an addon's offer and its flow ran, run
`python3 ../shared/config.py enable <key> [--version <pinned-tag>] --repo <repo>`
— `<key>` is the addon's directory name. The writer reconciles an existing
`.dwp/config.json` (other keys untouched) and refuses rather than clobbers a
file it cannot parse. A **decline writes nothing** (absent = not enabled);
an explicit "turn it off" is `config.py disable <key>`. The registry only
records what the repository opted into — no flow requires an entry, and a
repository with no file stays fully conformant.

Eight active addons ship today; the table lists all of them (the AI Diff Reviewer row
records its Phase 7a status). Offer the seven optional ones independently:

| Addon | Folder | Recommend in trust mode when… |
|-------|--------|-------------------------------|
| **Devcontainer support** | [`../addons/devcontainer/`](../addons/devcontainer/SKILL.md) | the repo benefits from a reproducible isolated dev container (most repos with Docker/services). |
| **Dailybot integration** | [`../addons/dailybot/`](../addons/dailybot/SKILL.md) | the developer/team **already uses Dailybot** or asks for team progress reporting — **do NOT auto-install for everyone**. |
| **Dependency upgrade** | [`../addons/dependency-upgrade/`](../addons/dependency-upgrade/SKILL.md) | **near-default** — the repo has **declared dependencies** (any manifest or lockfile): offer **always**, and install the **inert** `/lib-upgrade` delegator under the onboarding consent **unless explicitly declined**. Installing the delegator runs **no** upgrade — upgrades are always explicit, gated work. |
| **Design system** | [`../addons/design-system/`](../addons/design-system/SKILL.md) | the repo has a **user-facing interface surface**, detected per profile: when any surface is detected — even an ambiguous one — the evaluation and offer are **mandatory, not skippable**, with the detection rationale recorded. **visual-ui** (stylesheet with CSS custom properties, Tailwind config or `@theme` block, UI components, brand/style guide) is **strongly recommended**; **cli-output** (a CLI rendering library + a deliberate display layer) and **conversational** (a chat SDK or message-composition layer) are **recommended**. Every profile **requires explicit acceptance even in trust mode — none is auto-applied**. **Never offer for a repo with no interface surface** (pure library, headless service, infra-only). |
| **agentkit** | [`../addons/agentkit/`](../addons/agentkit/SKILL.md) | the developer wants plans to hand bounded `parallel_safe` tasks to other coding agents (claude, codex, cursor, …) — a machine-level install (`git clone --branch v0.3.0` + `install.sh`), never a repo requirement; delegation additionally needs each plan's `agent_delegation` grant. The kit runs agents in autonomy by default; the `--ask` / `AGENTKIT_PERMISSIONS=ask` opt-out always wins. |
| **Herdr** | [`../addons/herdr/`](../addons/herdr/SKILL.md) | the developer runs coding agents in [Herdr](https://herdr.dev) panes (one machine or several) and wants plans to ask a peer agent to take a task — a machine-level install of `herdr-peers@v0.1.0` (+ Herdr's official skill, pinned), never a repo requirement; delegation additionally needs each plan's `agent_delegation` grant. |
| **DeepWorkPlan Vim** | [`../addons/vim/`](../addons/vim/SKILL.md) | a person on this machine uses Neovim ≥ 0.12 or asks for a terminal editor for plans — a **machine-level** install, never a repo requirement; the editor is never imposed and an existing Neovim config is **never** overwritten without explicit consent (non-interactive runs onto an existing config stop at instructions). Pinned `deepworkplan-vim@v0.4.2`, detected through the product's `addon/surface.json`. |
| **AI Diff Reviewer** | [`../addons/ai-diff-reviewer/`](../addons/ai-diff-reviewer/SKILL.md) | **not offered here — installed in Phase 7a** (required local review, baseline since 2.3.0). In Phase 7b only confirm the Flow B (CI Action) opt-in decision if it was left open; never install the CI surface unrequested. |

The first addon is **devcontainer support**
([`../addons/devcontainer/SKILL.md`](../addons/devcontainer/SKILL.md) +
[`SPEC.md`](../addons/devcontainer/SPEC.md)), a thin integrator of
devcontainer-kit (`dck`, pinned `v0.1.4`). If the developer accepts: read
that addon's `SKILL.md` and run its flow — detect the kit (`dck doctor
--json`), reason the flavour, service, ports and layers from the stack you
detected in Phase 1, show `dck init --dry-run`, and let `dck init` reconcile
any **existing devcontainer — never clobbered**: an existing file changes
only after its diff was accepted, and the kit backs it up first. Record
`addons.devcontainer`, then run the addon's validation step (SPEC §8). If
declined, skip it and continue — the repo stays baseline-conformant.

The second addon is **Dailybot integration**
([`../addons/dailybot/SKILL.md`](../addons/dailybot/SKILL.md) +
[`SPEC.md`](../addons/dailybot/SPEC.md)). Offer it **only when relevant** — the
developer or team already uses Dailybot, or explicitly wants team progress
reporting; in trust mode, recommend it **only** on that signal and **never
auto-install it for everyone**. If accepted: read that addon's `SKILL.md` and run
its flow — detect whether the Dailybot skill/CLI is already present
(reconcile-don't-clobber), offer the **opt-in** install paths (Dailybot agent
skill via `npx --yes skills add https://github.com/DailybotHQ/agent-skill/tree/v3.23.3 --skill dailybot -y`
/ `npx --yes skills update dailybot -y` / OpenClaw `openclaw skills install dailybot`,
or the Dailybot CLI **>= 3.9.0** via pip / Homebrew / the skill's verified
installer flow), **defer
all authentication** to the Dailybot skill's own consent flow (`shared/auth.md`
— `dailybot login` or `DAILYBOT_API_KEY`; never reinvent or store credentials),
wire the **four lifecycle events** (kickoff, significant task, blocked,
completion) as optional progress reports via the dailybot `report` sub-skill,
and **MAY** offer deterministic hook enforcement (`dailybot hook`, CLI >=
3.9.0). The paired Dailybot skill (**3.23.3**) exposes 17 capabilities (chat,
check-ins, forms authoring, ask AI, per-repo API keys, Plan (Beta; CLI >= 3.25.0), and more); this addon wires only **report**
into DWP execution. Every report is strictly **best-effort and never blocks**
the work if Dailybot is absent, unauthenticated, or unreachable. The core
DeepWorkPlan methodology has **zero Dailybot dependency** — this addon is purely
optional team visibility.
After applying, run the addon's validation step (SPEC §8). If declined, skip it
and continue — the repo stays baseline-conformant.

The third addon is **dependency upgrade**
([`../addons/dependency-upgrade/SKILL.md`](../addons/dependency-upgrade/SKILL.md) +
[`SPEC.md`](../addons/dependency-upgrade/SPEC.md)). It is **package-manager
agnostic** and **near-default**: offer it for **every repo with declared
dependencies** — any manifest or lockfile, any ecosystem — in either mode. Under
the Phase 0 onboarding consent, install the **inert** `/lib-upgrade` delegator
into the repo's `.agents/commands/` **unless the developer explicitly
declines**; a prior explicit acceptance is never re-asked, and a decline leaves
a baseline-conformant repo with no command. Installing the delegator runs **no**
upgrade — an upgrade always starts from an explicit request. When invoked: read
that addon's `SKILL.md` and run
its flow — detect the repo's real package manager (npm/pnpm/yarn + ncu,
pip/poetry/uv, cargo, go mod, bundler, composer…), classify upgrades by semver,
upgrade in safe batches, run the repo's **real** validation gate after each
batch, revert a failing batch, and summarize. After
applying, run the addon's validation step (SPEC §9).

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
outbound-message voice rules). Detection makes the evaluation and offer
**mandatory** — recommend detected profiles, strongly for visual UI, and
record the detection rationale with the offer — but apply only after
**explicit acceptance in either mode**. Prior acceptance counts; an explicit
decline is respected for that run; trust mode alone does not authorize
optional addons. When **no** profile
is detected, **do not offer the addon**. Declining leaves a baseline-conformant
repo. If accepted: read that addon's
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

The **DeepWorkPlan Vim** addon
([`../addons/vim/SKILL.md`](../addons/vim/SKILL.md) +
[`SPEC.md`](../addons/vim/SPEC.md)) is a machine-level offer, not a repo
change: detect Neovim and the editor read-only through the product's
`addon/surface.json` (pinned `deepworkplan-vim@v0.4.2`, interface `1`; an
unknown interface is one warning and "not available"), then offer — never
impose — the editor. On acceptance run that addon's flow: the product's
documented, checksum-verified install under its absolute consent gate (an
existing Neovim config is never overwritten without explicit consent; a
non-interactive run onto an existing config stops at instructions), record
`addons.vim` in `.dwp/config.json`, and validate. If declined, skip it — the
repo stays baseline-conformant.

The **agentkit** addon ([`../addons/agentkit/SKILL.md`](../addons/agentkit/SKILL.md)
+ [`SPEC.md`](../addons/agentkit/SPEC.md)) is a machine-level offer: detect
`ak` read-only (`ak doctor --json`, interface `1`), offer it, and on
acceptance show the pinned install and record `addons.agentkit`. Enabling
it authorizes nothing by itself — a plan delegates only when its contract
grants `agent_delegation` (`../execute/delegation.md`). Tell the developer
how delegates launch: the kit runs agents in **autonomy by default** (meant
for disposable or sandboxed environments, such as a dev container), and the
opt-out always wins — `--ask`, or `AGENTKIT_PERMISSIONS=ask` in the
environment or the kit's env file. If declined, skip it — the repo stays
baseline-conformant.

The **Herdr** addon ([`../addons/herdr/SKILL.md`](../addons/herdr/SKILL.md) +
[`SPEC.md`](../addons/herdr/SPEC.md)) is a machine-level offer: detect
`herdr-peers` read-only (`herdr-peers --version` → protocol `1`), offer it,
and on acceptance show the pinned installs (`../addons/herdr/install.md`) and
record `addons.herdr`. The peer protocol lives in herdr-peers, not in this
pack. Enabling it authorizes nothing by itself. If declined, skip it — the
repo stays baseline-conformant.

The eighth addon, **AI Diff Reviewer**
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
