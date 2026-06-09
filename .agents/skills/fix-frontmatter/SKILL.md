---
name: fix-frontmatter
description: Run the frontmatter validator and fix any SKILL.md that violates the repo's frontmatter contract. Use after editing or adding a SKILL.md.
version: "1.0.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit
---

# Fix Frontmatter

## Goal

Bring every `SKILL.md` under `skills/` back into conformance with the frontmatter
contract that CI enforces, so `scripts/validate-frontmatter.py` passes.

## When to use

After adding or editing any `SKILL.md`, or when CI's "SKILL.md frontmatter
validation" job fails.

## Steps

1. Run `python3 scripts/validate-frontmatter.py` and read every reported issue.
2. For each flagged file, fix the frontmatter:
   - `name:` → kebab-case, starts with `deepworkplan` (e.g. `deepworkplan-create`)
   - `version:` → quoted SemVer (`"2.8.0"`)
   - replace `homepage:` with `documentation_url:`
   - ensure `---` delimiters and the required keys exist
3. Re-run the validator until it prints `OK: all N SKILL.md file(s) validated`.

## Validation

`python3 scripts/validate-frontmatter.py` exits 0.

## Notes

Never edit a `version:` **number** to make the check pass — fix only quoting or
format. The `auto-release.yml` bot owns version numbers (`AGENTS.md` §4). The
validator scans `skills/` only; `.agents/skills/*` is not CI-gated but follows
the same style.
