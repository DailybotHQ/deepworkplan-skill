---
description: Validate the YAML frontmatter on every SKILL.md under skills/ (the CI gate)
---

# /validate-frontmatter

Run this repo's frontmatter validator — the same check CI enforces on every PR.

## What to do

1. From the repo root, run:

   ```bash
   python3 scripts/validate-frontmatter.py
   ```

2. The validator scans every `SKILL.md` under `skills/` (router + sub-skills +
   addon) and fails if any violates the conventions in `AGENTS.md`:
   - `name:` is kebab-case and starts with `deepworkplan`
   - `version:` is a **quoted** SemVer string
   - the legacy `homepage:` key is **absent** (use `documentation_url:`)
   - frontmatter is delimited by `---` markers

3. On failure, fix the offending `SKILL.md` frontmatter and re-run until clean.
   Do **not** hand-edit `version:` to "fix" a check — the auto-release bot owns
   version numbers (see `AGENTS.md` §4). If the validator flags an unquoted or
   malformed version, fix the quoting/format, not the number.
