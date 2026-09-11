<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/dwp-mark-dark.png" />
  <img alt="Deep Work Plan" src="./assets/dwp-mark-light.png" width="200" />
</picture>

# DeepWorkPlan Skill Pack

**Models matter. Context matters more.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Open Agent Skills](https://img.shields.io/badge/format-Open%20Agent%20Skills-7b2d26)](https://agentskills.io)
[![skills.sh](https://img.shields.io/badge/install-skills.sh-000)](https://skills.sh)

[🌐 deepworkplan.com](https://deepworkplan.com) · [🔒 Security](SECURITY.md) · [📝 Changelog](CHANGELOG.md) · [🤝 Contributing](CONTRIBUTING.md)

</div>

---

> The official DeepWorkPlan agent skill pack, maintained by [Dailybot](https://www.dailybot.com).

DeepWorkPlan turns any repository into a **structured environment** — context,
guardrails, and a durable plan — where any coding agent executes with precision
and finishes short- and long-horizon work. It makes the repo AI-first (an adapted
`AGENTS.md`, `docs/`, per-module docs, and `.agents/` config), then drives
structured **Deep Work Plans**: a compact executable **Lite** plan for bounded
work, or a per-task **Full** plan for longer work; then execute, refine, resume,
and report with all plan output living in a gitignored
`.dwp/` directory.

> DeepWorkPlan is spec-driven development where the repository itself becomes the harness.

**What it rests on**

- **You steer; the agents do the hours.** You decide what *done* means and where
  the lines are. The plan carries your intent, so the work does not need
  correcting every twenty minutes.
- **The plan is what the agent returns to.** Long work fills any model's context
  and detail falls away. Atomic tasks, validation gates and resumable state give
  the agent something durable to come back to, lap after lap.
- **Done is a contract, not a feeling.** Every task names its acceptance criteria
  and the checks that must pass. An agent does not get to *decide* it finished —
  it passes, or the task stays open.
- **The repository is the harness.** Context, tools, guardrails and state live in
  your repo as plain files any agent can read. No lock-in, no external brain, and
  it survives a context reset or a change of agent mid-flight.
- **Context is the scarcest resource.** Instructions load progressively by
  trigger, validation is selected from what each task actually touched, and
  skills are decided task-locally — so the plan pays for itself instead of
  crowding out the work.

**At a glance**

- **License:** [MIT](LICENSE)
- **Security policy:** [SECURITY.md](SECURITY.md)
- **Changes:** [CHANGELOG.md](CHANGELOG.md)
- **Format:** [Open Agent Skills](https://agentskills.io) standard
- **Docs:** <https://deepworkplan.com>

## Skills

| Skill | What it does |
|-------|-------------|
| **deepworkplan-onboard** | Make any repo AI-first. Reasons about the repo's stack and archetype (orchestrator hub vs individual repo), then generates an adapted `AGENTS.md`, `docs/`, per-module docs, `.agents/`, and the `.claude → .agents` / `.cursor → .agents` symlinks. Offers opt-in addons. |
| **deepworkplan-create** | Create a Deep Work Plan. Starts every request as an executable Lite plan, recommends Lite or Full from the work's risk and horizon, and promotes safely to Full only when needed. |
| **deepworkplan-execute** | Execute an existing plan task-by-task, run each task's validation, and log progress. |
| **deepworkplan-refine** | Modify the scope or tasks of an existing plan, or promote a Lite plan to Full task files. |
| **deepworkplan-resume** | Resume an interrupted plan from its recorded progress state. |
| **deepworkplan-status** | Report the status of a plan — completed tasks, what's left, and blockers — without executing. |
| **deepworkplan-verify** | Check the repository and its plans against the standard — read-only, pass/fail, exits `0`/`1`. Confirms the harness is in place and that every plan's tasks, gates, evidence and final review actually hold, so "done" is auditable rather than asserted. |
| **deepworkplan-author** | Author or update reusable skills, agents, and commands in the current repo — reasons about the repo's `.agents/` layout, follows the Open Agent Skills frontmatter contract, and keeps the `.agents/docs/` catalog in sync. Backs the `/skill-create` and `/agent-create` aliases. |

A root **deepworkplan** meta-skill acts as a router — it describes all
capabilities and routes to the right sub-skill based on the developer's intent.
Each skill can be used independently or together; they share context detection
through a common `shared/` directory. The **AI Diff Reviewer local review** ships
in the baseline (installed by `onboard`, run by every Final Review; its CI
Action stays optional), and opt-in addons such as **devcontainer** support can
layer more onto an onboarded repo.

## Install

### Option 1 — `npx skills` (cross-agent, recommended)

The [skills.sh](https://skills.sh) CLI auto-detects your agent and installs the
skill in the right place:

```bash
npx skills add DailybotHQ/deepworkplan-skill
```

To target a specific agent or list available skills first:

```bash
npx skills add DailybotHQ/deepworkplan-skill --list
npx skills add DailybotHQ/deepworkplan-skill -a claude-code
```

Installing at **project scope** writes an entry to a workspace-root
`skills-lock.json` so the exact skill version is reproducible across your team
(see [Reproducible installs](#reproducible-installs-skills-lockjson) below).

### Option 2 — OpenClaw native registry

```bash
openclaw skills install deepworkplan
```

OpenClaw loads the pack natively on every eligible session — no trigger setup
required.

### Option 3 — Git clone + setup script

Pick the path for your agent, clone, then run `setup.sh`:

| Agent | Default path |
|-------|--------------|
| Claude Code | `~/.claude/skills/deepworkplan/` |
| Cursor | `~/.cursor/skills/deepworkplan/` |
| OpenAI Codex | `~/.codex/skills/deepworkplan/` |
| Windsurf | `~/.codeium/windsurf/skills/deepworkplan/` |
| GitHub Copilot | `~/.copilot/skills/deepworkplan/` |
| Cline | `~/.cline/skills/deepworkplan/` |
| Gemini CLI | `~/.gemini/skills/deepworkplan/` |
| OpenCode | `~/.config/opencode/skills/deepworkplan/` |
| Antigravity | `~/.antigravity/skills/deepworkplan/` |
| OpenClaw | `<workspace>/skills/deepworkplan/` or `~/.openclaw/skills/` |

```bash
git clone https://github.com/DailybotHQ/deepworkplan-skill.git ~/deepworkplan-skill
cd ~/deepworkplan-skill
./setup.sh                # auto-detect installed agents
./setup.sh --host claude  # or target one agent explicitly
```

`setup.sh` symlinks the `deepworkplan` pack plus each sub-skill
(`deepworkplan-create`, `deepworkplan-execute`, `deepworkplan-refine`,
`deepworkplan-resume`, `deepworkplan-status`, `deepworkplan-onboard`) into the
agent's skills directory so they're discoverable as independent slash commands.

### Invoke a skill

`/dwp-create` accepts mode tokens at either edge of the request. `trust` (or
`auto`) skips the guided review; `lite` and `full` override the recommendation.
For example: `/dwp-create trust fix the broken link`, `/dwp-create lite trust
rename this setting`, and `/dwp-create redesign the auth flow full trust`.
`lite` and `full` together are rejected. A direct-edit request remains direct;
the router only offers DWP when the developer asks to plan or organize work.

Once installed, describe what you want and the agent routes to the right
sub-skill:

- "Make this repo AI-first" / "onboard this repo" → **deepworkplan-onboard**
- "Create a plan to ship feature X" → **deepworkplan-create**
- "Execute the plan" / "continue the plan" → **deepworkplan-execute**
- "What's left on the plan?" → **deepworkplan-status**
- "Create a skill / agent" / "evolve the kit" → **deepworkplan-author** (also `/skill-create`, `/agent-create`)

Or invoke directly: `/deepworkplan-create`, `/deepworkplan-onboard`, etc.

## The `.dwp/` convention

All Deep Work Plan output lives in a gitignored `.dwp/` directory at the repo
root:

- `.dwp/plans/PLAN_<slug>/` — the plans (README + state + progress log, plus
  task files when the plan is Full)

There is no draft directory: `create` materializes an executable Lite plan
directly, and that plan is the reviewable artifact. `.dwp/drafts/` and the
`refined-draft` commands were removed in DWP 2.4.0.

`.dwp/` is resolved by `skills/deepworkplan/shared/context.sh` and overridable
via the `DWP_DIR` environment variable. It is meant to be gitignored — plan
artifacts are working state, not committed source. For orchestrator hubs, child
plans live at `repositories/<repo>/.dwp/plans/PLAN_<child>/`.

## Reproducible installs (`skills-lock.json`)

When you install at **project scope** (e.g. `npx skills add` run inside a
workspace), the skills.sh CLI writes the resolved skill source, path, and a
content hash to a `skills-lock.json` at your workspace root. Commit that file to
pin the exact version of DeepWorkPlan your team uses — re-running the installer
later restores the same revision. This skill repo does **not** ship a
`skills-lock.json` of its own; it is a consumer-side artifact that lives in
*your* workspace, not in the skill pack.

## Update

```bash
# npx
npx skills update DailybotHQ/deepworkplan-skill

# Git clone
cd <skill-path> && git pull && ./setup.sh

# OpenClaw
openclaw skills update deepworkplan
```

## Uninstall

```bash
# Remove the skill pack itself
rm -rf <skill-path>

# Remove sub-skill symlinks (Claude Code example)
rm -f ~/.claude/skills/deepworkplan \
      ~/.claude/skills/deepworkplan-create \
      ~/.claude/skills/deepworkplan-execute \
      ~/.claude/skills/deepworkplan-refine \
      ~/.claude/skills/deepworkplan-resume \
      ~/.claude/skills/deepworkplan-status \
      ~/.claude/skills/deepworkplan-onboard

# OpenClaw
openclaw skills remove deepworkplan
```

## Contributing

This README is for **users**. If you want to work on the skill itself, start with
[CONTRIBUTING.md](CONTRIBUTING.md) — the human-facing guide to local setup, the
auto-release flow, and the PR workflow. The canonical, terser rule list for AI
agents is [AGENTS.md](AGENTS.md) (and `CLAUDE.md` is a symlink to it): it covers
the ship boundary (only `skills/deepworkplan/` ships), the SKILL.md frontmatter
contract, the automatic-versioning rule, the commit format, and the pre-commit
checklist. Deeper background lives under [`docs/`](docs/) — [DESIGN.md](docs/DESIGN.md)
(the *why* behind the layout), [INSTALLATION.md](docs/INSTALLATION.md),
[OPENCLAW.md](docs/OPENCLAW.md), and [SUB_SKILL_GUIDE.md](docs/SUB_SKILL_GUIDE.md).

## Links

- [DeepWorkPlan](https://deepworkplan.com)
- [Dailybot](https://www.dailybot.com)
- [Open Agent Skills standard (agentskills.io)](https://agentskills.io)
- [skills.sh](https://skills.sh) — cross-agent skills directory

## :electric_plug: Powered by [Dailybot](https://www.dailybot.com?utm_source=dailybotopensource&utm_medium=deepworkplan-skill)

[Dailybot](https://www.dailybot.com/product/ai) is an AI-powered async communication platform that keeps **people and agents** visible — without adding more meetings or tools. It lives where your team already works (Slack, Teams, Google Chat, Discord, VS Code, and the CLI) and turns scattered signals into clear progress: async check-ins and standups, AI summaries that detect blockers and read team sentiment, workflow automation and approvals, team analytics, and recognition. As AI agents join the workflow, Dailybot surfaces their status and activity right alongside your team's — so long-running agents never go dark. [Learn more](https://www.dailybot.com?utm_source=dailybotopensource&utm_medium=deepworkplan-skill).
