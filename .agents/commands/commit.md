---
description: Stage and commit with a conventional-commit message the auto-release bot can read
---

# /commit

Create a commit whose message drives this repo's automatic versioning. The
`auto-release.yml` workflow reads merged commit messages to pick the bump level,
so the `<type>(<scope>):` prefix is not cosmetic — it is the release input.

## What to do

1. Run the local gate first (`/run-tests`) and confirm it is clean.
2. Stage the intended changes (review `git status` / `git diff` first — never
   blind-stage). Respect the **ship boundary**: runtime files only under
   `skills/deepworkplan/`, dev-infra at the repo root / `.agents/` / `.github/`.
3. Write the message in this format:

   ```
   <type>(<scope>): <short description>

   <body — what changed, why, risks>

   Co-Authored-By: <agent name + version> <noreply@anthropic.com>
   ```

   - **Types:** `feat`, `fix`, `docs`, `chore`, `test`, `ci`, `refactor`
   - **Scopes:** `skill`, `create`, `execute`, `refine`, `resume`, `status`,
     `onboard`, `addon`, `shared`, `setup`, `ci`, `docs`, `release`
   - **Bump mapping (the bot reads this):** `feat(...)!:` / `BREAKING CHANGE:` →
     MAJOR · `feat(...):` → MINOR · everything else → PATCH

4. **Do NOT** hand-edit `version:` fields or `CHANGELOG.md` — the bot owns them.
5. Commit only when the user asks. If on `main`, branch first.
