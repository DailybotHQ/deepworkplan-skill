# `.agents/` — cross-agent kit for working on this repo

This directory is the **canonical, cross-agent home** for everything that
defines how AI assistants work **on this repository**: agents (personas),
commands (slash commands), skills (procedures), catalogs, and settings. The same
content is consumed by Claude Code, Cursor, OpenAI Codex, Gemini, Copilot, and
any other agent that reads local skills/commands.

> [!IMPORTANT]
> **This is dev-infrastructure — it does NOT ship.** Only `skills/deepworkplan/`
> is distributed to end users (via skills.sh / OpenClaw / git clone). `.agents/`
> lives only on GitHub and on contributors' machines, exactly like `.github/`,
> `tests/`, `scripts/`, and `docs/`. See `AGENTS.md` §2.

This repo **dogfoods the methodology it ships**: the DeepWorkPlan pack lives
at [`skills/deepworkplan`](skills/deepworkplan) as a **vendored copy** fetched
via `npx skills add DailybotHQ/deepworkplan-skill@vX.Y.Z` and pinned in
[`skills-lock.json`](../skills-lock.json), so the `/dwp-*` commands and agents
here pilot this very repo using **exactly what a consumer would install**.
That copy is refreshed automatically by the auto-release workflow after each
tag lands — never hand-edit it (see AGENTS.md §4).

```
.agents/
├── README.md                ← this file
├── settings.json            ← harness config (sensible permissions; no secrets)
├── agents/                  ← reviewer, architect, executor, frontmatter-guardian, shell-auditor
├── commands/                ← dwp-* delegators + skill-create/agent-create + validate-frontmatter/run-tests/commit
├── skills/                  ← fix-frontmatter, shellcheck-fix, write-bats-test + deepworkplan (vendored, bot-managed)
└── docs/                    ← skills_agents_catalog.md, COMMANDS_REFERENCE.md
.claude → .agents            ← backward-compat symlink (Claude Code reads .claude/)
.cursor → .agents            ← backward-compat symlink (Cursor reads .cursor/)
```

## Backward compatibility — the `.claude` symlink

Claude Code historically reads from `.claude/`. To avoid duplicating files,
`.claude` is a symlink to `.agents`, so every `.claude/...` path resolves
transparently to `.agents/...`. Edit the real files under `.agents/`, never
through the `.claude/` symlink.

## Where to start

- Working on the skill? Read [`AGENTS.md`](../AGENTS.md) (the contributor spec).
- Need a command? See [`docs/COMMANDS_REFERENCE.md`](docs/COMMANDS_REFERENCE.md).
- Want the full inventory? See [`docs/skills_agents_catalog.md`](docs/skills_agents_catalog.md).
