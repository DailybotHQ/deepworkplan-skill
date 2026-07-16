# Skills & Agents Catalog

Everything the `.agents/` kit provides for working **on this repo**. This is
dev-infrastructure — it does NOT ship to end users (only `skills/deepworkplan/`
ships). It exists so any agent (Claude Code, Cursor, Codex, Gemini, Copilot) can
pilot this repo consistently — i.e. the skill pack dogfoods its own methodology.

## Agents (`.agents/agents/`)

| Agent | Model tier | Role |
|-------|-----------|------|
| [reviewer](../agents/reviewer.md) | standard | Reviews a diff for ship-boundary, frontmatter, bash 3.2, and public-surface violations |
| [architect](../agents/architect.md) | heavy | Plans changes (new sub-skills, addons, presets), location, frontmatter, and bump level |
| [executor](../agents/executor.md) | standard | Implements a plan task-by-task, running the local gate after each step |
| [frontmatter-guardian](../agents/frontmatter-guardian.md) | light | Audits and fixes SKILL.md frontmatter against the validator |
| [shell-auditor](../agents/shell-auditor.md) | light | Keeps the shell scripts shellcheck-clean and bash 3.2-safe |

## Skills (`.agents/skills/`)

Repo-development skills (not shipped):

| Skill | Purpose |
|-------|---------|
| [fix-frontmatter](../skills/fix-frontmatter/SKILL.md) | Run the validator and fix any non-conformant `SKILL.md` |
| [shellcheck-fix](../skills/shellcheck-fix/SKILL.md) | Shellcheck the shell scripts and fix while keeping bash 3.2 compatibility |
| [write-bats-test](../skills/write-bats-test/SKILL.md) | Add/extend bats-core tests following the `tests/` convention |

Plus the **installed DeepWorkPlan pack**, symlinked at
[`.agents/skills/deepworkplan`](../skills/deepworkplan) →
`../../skills/deepworkplan` (the repo's own shipped artifact, dogfooded). It
provides the router and sub-skills `create`, `execute`, `refine`, `resume`,
`status`, `verify`, `onboard`, `author`, plus addons under `addons/`. The
`/dwp-*`, `/skill-create`, and `/agent-create` commands route here.

### Vendored third-party skills (dogfood, not repo-dev)

Tracked under `.agents/skills/` and pinned via `skills-lock.json`. Refreshed by
`auto-release.yml` on every release cut — do **not** hand-edit. Listed here so
the catalog has no orphans; they are **not** repo-development skills.

| Skill | Upstream | Purpose |
|-------|----------|---------|
| [dailybot](../skills/dailybot/SKILL.md) | [`DailybotHQ/agent-skill`](https://github.com/DailybotHQ/agent-skill) | Team standup reporting for plan lifecycle events (Dailybot addon) |
| [ai-diff-reviewer](../skills/ai-diff-reviewer/SKILL.md) | [`DailybotHQ/ai-diff-reviewer`](https://github.com/DailybotHQ/ai-diff-reviewer) | Local + CI PR review (AI Diff Reviewer addon); byte-identical `prompt.md` with the Action |

## Commands (`.agents/commands/`)

See [COMMANDS_REFERENCE.md](COMMANDS_REFERENCE.md) for the full list and
procedure links: the eight `deepworkplan` delegators (`dwp-create`,
`dwp-execute`, `dwp-refine`, `dwp-resume`, `dwp-status`, `dwp-verify`,
`skill-create`, `agent-create`) and the three repo-dev commands
(`validate-frontmatter`, `run-tests`, `commit`).
