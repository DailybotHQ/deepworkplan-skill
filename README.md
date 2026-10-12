<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/dwp-mark-dark.png" />
  <img alt="Deep Work Plan" src="./assets/dwp-mark-light.png" width="200" />
</picture>

# DeepWorkPlan Skill Pack

**Models matter. Context matters more.**

[![CI](https://github.com/DailybotHQ/deepworkplan-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/DailybotHQ/deepworkplan-skill/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/DailybotHQ/deepworkplan-skill?include_prereleases&sort=semver)](https://github.com/DailybotHQ/deepworkplan-skill/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Open Agent Skills](https://img.shields.io/badge/format-Open%20Agent%20Skills-7b2d26)](https://agentskills.io)
[![skills.sh](https://img.shields.io/badge/install-skills.sh-000)](https://skills.sh)

[🌐 deepworkplan.com](https://deepworkplan.com) · [🔒 Security](SECURITY.md) · [📝 Changelog](CHANGELOG.md) · [🤝 Contributing](CONTRIBUTING.md)

</div>

---

## What it is

> The official DeepWorkPlan agent skill pack, maintained by [Dailybot](https://www.dailybot.com).

DeepWorkPlan turns any repository into a **structured environment** — context,
guardrails and a durable plan — where any coding agent executes with precision
and finishes short- and long-horizon work. It is for developers and teams who
hand real work to coding agents (Claude Code, Codex, Cursor, Gemini CLI,
Copilot, OpenClaw and others) and need that work to survive context resets,
agent changes and long runs.

> DeepWorkPlan is spec-driven development where the repository itself becomes the harness.

The pack does three things:

- **Onboards any repository, completely.** `/deepworkplan-onboard` writes an
  adapted `AGENTS.md`, `docs/`, per-module docs and `.agents/` and installs
  the required local review — the pack and that review go into every
  repository. It then **detects every addon, upgrades the ones you use and
  offers the ones that fit**, whether the repository has none, an older
  release or a hand-written docker setup; nothing is added just to complete
  the set. When you want a container, it ends in the full working stack: dev
  container, editor, agents on your own accounts and a Herdr workspace.
- **Runs Deep Work Plans.** A compact executable **Lite** plan for bounded
  work, or a per-task **Full** plan for longer work: atomic tasks, acceptance
  criteria, validation gates and resumable state under a gitignored `.dwp/`.
- **Orchestrates many agents.** A lead agent runs one agent per repository or
  workstream in its own pane — on the host, in containers or on other
  machines — each on an account chosen by remaining quota, across vendors,
  coordinated through one authorized ask and reply, with one branch and one
  release per repository.

The methodology works alone: apart from the required local review, every addon
is optional and only amplifies it.
The current major line is **v7** (DWP standard 7.0.0; releases are on the
[Releases](https://github.com/DailybotHQ/deepworkplan-skill/releases) page).
New plans use the v7 contract; existing v6 and v5 plans keep their recorded
lifecycle.

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

## Install

Pin a release tag: the commands below install exactly `v7.6.0` (newer tags are on
the [Releases](https://github.com/DailybotHQ/deepworkplan-skill/releases) page).

### Option 1 — `npx skills` (cross-agent, recommended)

```bash
npx --yes skills add https://github.com/DailybotHQ/deepworkplan-skill/tree/v7.6.0 --skill deepworkplan -y
```

The [skills.sh](https://skills.sh) CLI detects your agent and installs the pack
in the right place; `-a claude-code` (or another agent id) targets one agent.
Installed at **project scope**, it records the source and a content hash in a
workspace-root `skills-lock.json` — commit it so your team restores the same
revision. Pin with the tree-URL form above: the CLI ignores the ref of the
`OWNER/REPO@ref` shorthand and installs the default branch.

### Option 2 — OpenClaw native registry

```bash
openclaw skills install deepworkplan
```

### Option 3 — Git clone + setup script (verifiable)

```bash
git clone --branch v7.6.0 https://github.com/DailybotHQ/deepworkplan-skill.git ~/deepworkplan-skill
cd ~/deepworkplan-skill
curl -fsSL https://github.com/DailybotHQ/deepworkplan-skill/releases/download/v7.6.0/SHA256SUMS -o SHA256SUMS
./scripts/verify-integrity.sh SHA256SUMS   # non-zero exit: a shipped file does not match
./setup.sh                # auto-detect installed agents
./setup.sh --host claude  # or target one agent explicitly
```

`setup.sh` links the `deepworkplan` router plus each sub-skill
(`deepworkplan-create`, `-execute`, `-refine`, `-resume`, `-status`,
`-onboard`, `-verify`, `-author`, `-upgrade`) into the agent's skills
directory. Default paths per agent are in
[docs/INSTALLATION.md](docs/INSTALLATION.md).

### Update and uninstall

- **Update:** re-run the pinned install with the new tag, or ask the agent to
  `/deepworkplan-upgrade` — it checks for a newer release read-only and
  downloads only with your explicit acceptance; `.dwp/` is never migrated.
  OpenClaw: `openclaw skills update deepworkplan`.
- **Uninstall:** remove the skill directory and the `deepworkplan-*` links the
  installer created (`openclaw skills remove deepworkplan` on OpenClaw).

## Quickstart

1. **Install** the pack (pinned, above) where your agent can see it.
2. **Onboard** the repository: `/deepworkplan-onboard` (Claude Code) or
   `#deepworkplan-onboard` in any other agent. It writes an adapted
   `AGENTS.md`, `docs/`, `.agents/` (including the short `/dwp-*` commands
   used below), installs the required local review and offers the addons.
   Ask it to **set up the addons that fit** — it detects every addon,
   upgrades the ones you use and offers the rest only where they fit; run it
   again on an older onboarding (`upgrade`) to bring the addons you use to the
   pack's pins.
3. **Plan** real work: `/dwp-create <what you want done>` writes a Deep Work
   Plan under the gitignored `.dwp/plans/`.
4. **Execute** it: `/dwp-execute <plan>` works task by task, validates each
   one against its gates and commits; `/dwp-resume` picks up after an
   interruption; `/dwp-status` and `/dwp-verify` report.

`/dwp-create` accepts mode tokens at either edge of the request: `trust` (or
`auto`) skips the guided review, `lite` and `full` override the recommended
format — for example `/dwp-create trust fix the broken link` or
`/dwp-create redesign the auth flow full trust`.

## Addons that fit, kept up to date

The pack and the required local review go into every repository; every other
addon only where it fits. Onboarding starts from one read-only plan of the
repository:

```bash
python3 <pack>/shared/addon_sync.py plan --repo .
```

```text
addon               scope         installed   pin         action
------------------  ------------  ----------  ----------  ----------
agentkit            machine       v0.4.0      v0.5.3      upgrade
ai-diff-reviewer    repo          v3.1.0      v3.3.11      upgrade
dailybot            repo          -           v3.23.14    install
dependency-upgrade  repo          yes         (in pack)   record
design-system       repo          -           (in pack)   evaluate
                    offer only when an interface surface is detected
devcontainer        machine+repo  -           v0.3.5      reconcile
                    a docker setup without dck markers: dck init --dry-run shows each replace as a diff; …
herdr               machine       v0.2.3      v0.2.3      available
                    on this machine (v0.2.3, pin v0.2.3); not enabled for this repository
vim                 machine       -           v0.7.0      install
pending: agentkit, ai-diff-reviewer, dependency-upgrade, devcontainer
offers: dailybot, herdr, vim (only where they fit; a decline writes nothing)
evaluate: design-system (run its detection before reporting done)
```

(Illustrative output; the pins are the ones the installed pack carries.)

For each addon the planner reads its detection, the vendored skill and
`skills-lock.json`, the `.dwp/config.json` registry and the dev-container
layout, and names one action: **install**, **upgrade** to the pin,
**record**, **current**, **newer** (never downgraded), **reconcile** (a
hand-written dev container, changed only through a shown diff and your
consent), **available** (a tool on your machine this repository never
enabled), **declined** (never re-offered) and a few more. `pending` is what
the repository uses or requires and is not yet at the pin; `offers` is what
fits but was never chosen here — made once, and a decline writes nothing. The
agent runs each accepted addon's own flow in a fixed order, records the
result, and re-plans until `pending: nothing`. A second pass over a finished
repository changes nothing. Machine-level installs (`ak`, `dck`,
herdr-peers, the editor) are shown as exact, tag-pinned, checksum-verified
commands and run only on your acceptance.

With the dev container, onboarding ends in the full stack: `dck init` with the
agents layer and only the CLIs you choose, the editor and Dailybot layers when
those addons are on, a Herdr machine with the App · Editor · Development ·
Agents layout, then `bash dev.sh up` and a verification checklist
(`dck doctor`, `ak doctor` inside, `herdr workspace list`, `ssh -T`,
`gh auth status`). Your own accounts can reach the container only through your
**host** profile (`[agents] host_profiles`), never the repository.

Procedure: [`onboard/all-addons.md`](skills/deepworkplan/onboard/all-addons.md).

## Orchestrating many agents

For work across several repositories or long parallel workstreams, a **lead**
agent runs **lanes** — one agent per repository, each in its own
[Herdr](https://herdr.dev) pane:

| Concern | How |
|---------|-----|
| Accounts and vendors | `ak usage --json` once per batch; `ak pick <kind> --count N` assigns the accounts with the most room; Claude, Codex and others mix by plan choice |
| Launch | `ak <kind> @<profile> --trust-cwd "<lane brief>"` in a pane on the lane's checkout; in containers, the host's accounts through host profiles |
| Coordination | only the lead and each lane, through herdr-peers asks and replies: plan ready, PR open, blocked, done; GO with the release tags |
| Branches and releases | one lane per repository on its base checkout: one branch, one PR, one release; worktrees only when two writers share a repository |
| Unattended operation | under your standing authorization, lanes launch with no per-launch approval: folders are pre-trusted with `--trust-cwd`, Claude's bypass-permissions acknowledgement is a one-time step you take per profile, and any other prompt a lane meets is recorded and escalated to you — the one keystroke an agent may send is folder trust on a pane it launched when `--trust-cwd` is unavailable |
| Verification and record | each repository's own gate decides; every delegation, intervention and account is recorded in the plan |

Guide: [`guide/orchestration-at-scale.md`](skills/deepworkplan/guide/orchestration-at-scale.md).

## Skills

| Skill | What it does |
|-------|-------------|
| **deepworkplan-onboard** | Make any repo AI-first: an adapted `AGENTS.md`, `docs/`, per-module docs, `.agents/` and the `.claude → .agents` / `.cursor → .agents` symlinks; installs the required local review; offers the optional addons where they fit and, on request or on a harness upgrade, upgrades the ones the repository uses. A targeted, idempotent harness upgrade for repositories onboarded earlier. |
| **deepworkplan-create** | Create a Deep Work Plan: every request starts as an executable Lite plan, promoted to Full only when the work's risk and horizon call for it. |
| **deepworkplan-execute** | Execute a plan task by task, run each task's gates, and log progress; delegate `parallel_safe` tasks when the plan grants it. |
| **deepworkplan-refine** | Change a plan's scope or tasks, or promote a Lite plan to Full task files. |
| **deepworkplan-resume** | Resume an interrupted plan from its recorded state. |
| **deepworkplan-status** | Report a plan's progress, what is left and its blockers, without executing. |
| **deepworkplan-verify** | Check the repository and its plans against the standard — read-only, exits `0`/`1` — so "done" is auditable rather than asserted. |
| **deepworkplan-author** | Author or update skills, agents and commands in the repo's `.agents/`, keeping the catalog in sync (`/skill-create`, `/agent-create`). |
| **deepworkplan-upgrade** | Check for a newer pack release (read-only) and upgrade only with explicit consent. |

A root **deepworkplan** router describes every capability and routes by intent.

### Addons

The AI Diff Reviewer local review goes into every repository; the others are
optional and installed only where they fit. Each is recorded in the
`.dwp/config.json` registry and documented on its kit page:

| Addon | What it adds | Kit page |
|-------|--------------|----------|
| AI Diff Reviewer | the required local review in every Final Review; an optional CI Action | [/kit/ai-diff-reviewer](https://deepworkplan.com/kit/ai-diff-reviewer) |
| agentkit | headless delegates, accounts and quota through coding-agents-kit (`ak`) | [/kit/agentkit](https://deepworkplan.com/kit/agentkit) |
| Herdr | interactive delegates and lanes in Herdr panes through herdr-peers | [/kit/herdr](https://deepworkplan.com/kit/herdr) |
| devcontainer | a reproducible dev container through devcontainer-kit (`dck`) | [/kit/devcontainer](https://deepworkplan.com/kit/devcontainer) |
| DeepWorkPlan Vim | the terminal editor for plans | [/kit/vim](https://deepworkplan.com/kit/vim) |
| Dailybot | progress reports at the plan lifecycle events | [/kit/dailybot](https://deepworkplan.com/kit/dailybot) |
| dependency upgrade | safe, batched, revertible dependency upgrades (`/lib-upgrade`) | [/kit/dependency-upgrade](https://deepworkplan.com/kit/dependency-upgrade) |
| design system | a `DESIGN.md` reasoned from the repository's real design source | [/kit/design-system](https://deepworkplan.com/kit/design-system) |

## Documentation

- [deepworkplan.com](https://deepworkplan.com) — the methodology, the kit pages and the published schemas
- [`skills/deepworkplan/spec/`](skills/deepworkplan/spec/README.md) — the normative standard (7.0.0)
- [`skills/deepworkplan/guide/GUIDE.md`](skills/deepworkplan/guide/GUIDE.md) — the methodology guide, including [orchestration at scale](skills/deepworkplan/guide/orchestration-at-scale.md)
- [`docs/`](docs/) — [installation](docs/INSTALLATION.md), [design](docs/DESIGN.md), [compatibility](docs/COMPATIBILITY.md), [testing](docs/TESTING_GUIDE.md)
- [CHANGELOG.md](CHANGELOG.md) · [Open Agent Skills standard](https://agentskills.io) · [skills.sh](https://skills.sh)

### The `.dwp/` convention

All Deep Work Plan output lives in a gitignored `.dwp/` directory at the repo
root:

- `.dwp/plans/PLAN_001_<slug>/`, `PLAN_002_<slug>/`, ... — new plans in a flat,
  creation-ordered folder list (README + state + progress log, plus task files
  when the plan is Full). Existing unnumbered folders keep their names.

There is no draft directory: `create` materializes an executable Lite plan
directly, and that plan is the reviewable artifact. `.dwp/drafts/` and the
`refined-draft` commands were removed in DWP 2.4.0.

`.dwp/` is resolved by `skills/deepworkplan/shared/context.sh` and overridable
via the `DWP_DIR` environment variable. It is meant to be gitignored — plan
artifacts are working state, not committed source. For orchestrator hubs, child
plans use the same numbering within each managed repository.

Each repository assigns IDs starting at `001`; the counter is kept in
`.dwp/plans/.next-plan-id`, so deleting a plan does not reuse its number.
`latest` selects the highest numbered plan. You can also select a plan by its
full folder name, ID, or unique slug. Existing folders such as
`PLAN_improve_docs/` are not renamed and remain usable. The current pack
creates v7 plans (v6 on explicit request) with 2–5-word slugs. The retained v5 creation flow uses
2–4 words to fit its frozen schemas.

### Benchmark metrics and learnings (opt-in)

DWP can record how each executed plan went, so skill versions can be compared
on recorded evidence instead of impressions. It is off unless you turn it on.
In `<repo>/.dwp/config.json` (this repository only):

```json
{ "benchmark": { "enabled": true } }
```

Or in `~/.dwp/config.json` (every repository you run plans in):

```json
{ "benchmark": { "enabled": true } }
```

The repository file wins over the global one, and anything malformed is
disabled with a warning — the feature fails closed. When enabled, the v6
execute flow emits two artifacts into the finished plan's `analysis_results/`
at completion: `benchmark.json`, a machine-readable record, and `DWP_REPORT.md`,
a human summary rendered from it. Both cover execution timing (calendar
spans — overall and per task — never active runtime), plan shape and
complexity counts, friction events (retries, adaptations, refusals), gate
outcomes with evidence classes, context accounting, and diff statistics —
plus tokens and spend only when the host actually metered them.

A nested flag adds the learnings half:

```json
{ "benchmark": { "enabled": true, "learnings": true } }
```

`DWP_REPORT.md` then also carries the friction **explained** — each friction
event's recorded reason, copied verbatim from the journal — and a curated
learnings table the completing agent authors once (category, anchor, finding,
proposal). Reruns regenerate the derived half and preserve the curated
entries byte-for-byte. The report is a rendering of the JSON records, never a
second source, and it is distinct from the on-request Executive Report.

Three honesty rules hold by construction: nothing is imputed (unmetered
quantities are null, never estimated), the emission is best-effort (a failure
warns and never blocks plan completion), and nothing leaves your repositories
— the record names only the repository basename and branch. The v5 line is
frozen: v5 plans are listed by the aggregator as not collected and are never
measured.

To combine records across plans and repositories:

```bash
python3 skills/deepworkplan/shared/benchmark.py aggregate \
    --roots ~/code/repo-a ~/code/repo-b --csv monthly.csv --out monthly.md
```

The aggregate report groups by skill version and repository, adds a learnings
digest (curated entries grouped by version and category, most-flagged
sections, plans with at least one spec-gap, median per-task span, metered
coverage) plus one CSV row per plan with flattened learnings columns, and
carries a standing note: workloads differ across plans, repositories and
versions, so aggregates are evidence for discussion, not a causal comparison.
The specification is [`skills/deepworkplan/spec/BENCHMARK.md`](skills/deepworkplan/spec/BENCHMARK.md)
(record schemas: [`benchmark-record`](skills/deepworkplan/spec/schema/benchmark-record.schema.json)
and [`learnings-record`](skills/deepworkplan/spec/schema/learnings-record.schema.json)).

## Part of the DeepWorkPlan ecosystem

[DeepWorkPlan](https://deepworkplan.com) turns any repository into an AI-first,
agent-pilotable codebase. These projects ship together; every addon is optional.

| Repository | Role | Purpose |
| --- | --- | --- |
| [deepworkplan-skill](https://github.com/DailybotHQ/deepworkplan-skill) (this repository) | Pack | The methodology, specification and kit as an installable agent skill |
| [coding-agents-kit](https://github.com/DailybotHQ/coding-agents-kit) | Addon: agentkit | One command for every coding agent: accounts, quota, `ak pick`, headless runs |
| [devcontainer-kit](https://github.com/DailybotHQ/devcontainer-kit) | Addon: devcontainer | A reproducible dev container per repository, wired to Herdr and the host's accounts |
| [herdr-peers](https://github.com/DailybotHQ/herdr-peers) | Addon: Herdr | Ask an agent in another Herdr pane, on any machine, and get one authorized reply |
| [deepworkplan-vim](https://github.com/DailybotHQ/deepworkplan-vim) | Addon: DeepWorkPlan Vim | The terminal editor for plans: plan browser, lanes view, Markdown viewer |
| [ai-diff-reviewer](https://github.com/DailybotHQ/ai-diff-reviewer) | Required local review | Reviews a change set locally and in CI; every Final Review runs it |
| [agent-skill](https://github.com/DailybotHQ/agent-skill) | Addon: Dailybot | The Dailybot agent skill: progress reports, check-ins, chat and more |
| [deepworkplan.com](https://deepworkplan.com) ([source](https://github.com/DailybotHQ/deepworkplan-website)) | Site and hub | The methodology, specification, kit catalog and `/init.md`; coordinates the ecosystem |

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md) (GitHub
private vulnerability reporting or security@dailybot.com). In short: the core
methodology makes no network calls and emits no telemetry; its only external
processes are `git` and, for addons, their declared read-only detect commands;
every install the pack names is tag-pinned or package-managed, and nothing is
piped into a shell;
secrets are referred to by name, never printed or stored. Coding agents launched
through `ak` run in autonomy by default, and your opt-out
(`AGENTKIT_PERMISSIONS=ask`) always wins. The full model, with a self-audit you
can run, is [`skills/deepworkplan/TRUST.md`](skills/deepworkplan/TRUST.md). CI
runs a public-hygiene check on every change.

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

## License

[MIT](LICENSE). Contributions are accepted under the same license; see
[CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).

## :electric_plug: Powered by [Dailybot](https://www.dailybot.com?utm_source=dailybotopensource&utm_medium=deepworkplan-skill)

[Dailybot](https://www.dailybot.com/product/ai) is an AI-powered async communication platform that keeps **people and agents** visible — without adding more meetings or tools. It lives where your team already works (Slack, Teams, Google Chat, Discord, VS Code, and the CLI) and turns scattered signals into clear progress: async check-ins and standups, AI summaries that detect blockers and read team sentiment, workflow automation and approvals, team analytics, and recognition. As AI agents join the workflow, Dailybot surfaces their status and activity right alongside your team's — so long-running agents never go dark. [Learn more](https://www.dailybot.com?utm_source=dailybotopensource&utm_medium=deepworkplan-skill).

---

Part of the [DeepWorkPlan](https://deepworkplan.com) ecosystem — works on its own.
