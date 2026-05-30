<!--
Thanks for contributing! Read AGENTS.md once if you haven't — it lists every
convention and the reasoning behind each. CONTRIBUTING.md is the longer,
human-facing version of the same rules.
-->

## Summary

<!-- 1-3 sentences: what changed and why it matters. -->

## Type

- [ ] feat — new behavior
- [ ] fix — bug fix
- [ ] docs — documentation only
- [ ] chore — repo maintenance
- [ ] test — adding tests
- [ ] ci — CI configuration
- [ ] refactor — no user-visible change

## Scope

- [ ] Modified runtime skill (anything under `skills/deepworkplan/`)
- [ ] Modified dev infrastructure (anything outside `skills/deepworkplan/`)

## Pre-merge checklist

- [ ] `shellcheck setup.sh skills/deepworkplan/shared/context.sh scripts/*.sh` passes
- [ ] `bats tests/` passes
- [ ] `python3 scripts/validate-frontmatter.py` passes
- [ ] No runtime file added outside `skills/deepworkplan/` (and no dev-infra file added inside it)
- [ ] `.dwp/` stays gitignored — no plan output committed
- [ ] No `name: deepworkplan_*` (snake_case) introduced — kebab-case only
- [ ] No `homepage:` field introduced — use `documentation_url:`
- [ ] No bash 4+ idioms (`mapfile`, `declare -A`, `${var^^}`) introduced
- [ ] CHANGELOG.md NOT hand-edited and `version:` fields NOT hand-bumped (the auto-release bot owns them)
- [ ] Public surface preserved (the six `/deepworkplan-*` slash commands, the `.dwp/` convention, `setup.sh` flags, skill `name` fields) — or major version bumped (`feat(...)!:`) with a migration note
- [ ] Commit messages follow `<type>(<scope>): description` format

## Test plan

<!--
Bulleted markdown checklist. Mention which environments you tested manually
(macOS, Linux, WSL2, CI). At minimum:
- ./setup.sh --host claude
- bash skills/deepworkplan/shared/context.sh in a regular dir
- bash skills/deepworkplan/shared/context.sh with DWP_DIR / DWP_AGENT_TOOL set
-->

- [ ]
- [ ]

## Risks

<!-- Anything reviewers should pay extra attention to. Migration paths,
behavior changes, cross-platform considerations. -->

## Breaking changes (only if applicable)

<!-- If you bumped major version (feat(...)!:), describe:
- What broke and why (slash command, .dwp/ convention, setup.sh flag, skill name…)
- Migration path for existing users
- Deprecation timeline if any
-->
