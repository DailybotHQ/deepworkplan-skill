# Commands Reference

All slash commands available in this repo, with the procedure file each one
runs. Invoke with `/` in Claude Code, or `#<name>` / plain text in other agents.

When a command is invoked, the agent MUST read the linked procedure file and
follow it exactly — the file is the spec.

## DeepWorkPlan delegators (thin aliases → installed skill)

These route to the `deepworkplan` skill (committed dogfood copy at
`.agents/skills/deepworkplan`). The flow lives in the skill; these files only
route, so there is a single source of truth.

| Command | Procedure | Routes to |
|---------|-----------|-----------|
| `/dwp-create` | [commands/dwp-create.md](../commands/dwp-create.md) | `create` sub-skill |
| `/dwp-execute` | [commands/dwp-execute.md](../commands/dwp-execute.md) | `execute` sub-skill |
| `/dwp-refine` | [commands/dwp-refine.md](../commands/dwp-refine.md) | `refine` sub-skill |
| `/dwp-resume` | [commands/dwp-resume.md](../commands/dwp-resume.md) | `resume` sub-skill |
| `/dwp-status` | [commands/dwp-status.md](../commands/dwp-status.md) | `status` sub-skill |
| `/dwp-verify` | [commands/dwp-verify.md](../commands/dwp-verify.md) | `verify` sub-skill |
| `/skill-create` | [commands/skill-create.md](../commands/skill-create.md) | `author` sub-skill (create a skill) |
| `/agent-create` | [commands/agent-create.md](../commands/agent-create.md) | `author` sub-skill (create an agent) |

> The skill's own sub-skills are also `user-invocable`, so `/deepworkplan-create`,
> `/deepworkplan-execute`, etc. work directly. The `dwp-*` files are the shorter,
> conventional aliases.

## Repo development commands

| Command | Procedure | Purpose |
|---------|-----------|---------|
| `/validate-frontmatter` | [commands/validate-frontmatter.md](../commands/validate-frontmatter.md) | Run `scripts/validate-frontmatter.py` (the CI frontmatter gate) |
| `/run-tests` | [commands/run-tests.md](../commands/run-tests.md) | Full local CI gate: frontmatter + shellcheck + bats + setup smoke |
| `/commit` | [commands/commit.md](../commands/commit.md) | Conventional commit the auto-release bot can read |
