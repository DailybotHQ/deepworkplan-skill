# Publishing Playbook — `DailybotHQ/deepworkplan-skill`

> **Not installed.** Contributor / maintainer document. This is the launch and
> ongoing-release playbook for the DeepWorkPlan skill pack. End users don't need
> it — they install via the methods in [README.md](README.md).

The repository auto-releases from `main` once it's set up. This playbook covers
the **one-time launch** and the **steady-state release loop**.

---

## 1. Create the GitHub repository

1. Create `github.com/DailybotHQ/deepworkplan-skill` (public).
2. Push this repo tree to it (`main` as the default branch):
   ```bash
   git init -b main
   git add -A
   git commit -m "feat(skill): initial public release of the DeepWorkPlan skill pack"
   git remote add origin git@github.com:DailybotHQ/deepworkplan-skill.git
   git push -u origin main
   ```
   > Confirm the ship boundary before the first push: only `skills/deepworkplan/`
   > should be the runtime artifact. Everything else is dev infra.

## 2. Configure secrets and branch protection

1. **`AUTOMATION_GITHUB_TOKEN` secret.** The `auto-release.yml` workflow pushes
   the release commit and tag back to a protected `main`. Create a fine-grained
   PAT (or GitHub App token) for the `dailybotops` automation identity with
   `contents: write` on this repo and add it as the repo secret
   `AUTOMATION_GITHUB_TOKEN`. (If you skip this, the workflow falls back to the
   default `GITHUB_TOKEN`, which cannot push to a protected branch unless
   `github-actions[bot]` is in the bypass list.)
2. **Branch protection on `main`.** Require PRs, require the CI checks
   (frontmatter validation, shellcheck, context.sh smoke, setup.sh smoke,
   markdown links) to pass, and add the automation identity to the
   "allowed to bypass / push" list so the release commit can land.

## 3. First release

The repo ships seeded at version `2.0.0` (every SKILL.md carries
`version: "2.0.0"`, and `CHANGELOG.md` has the `[2.0.0]` section). The
auto-release reads the **router** `skills/deepworkplan/SKILL.md` as the version
source of truth, so to publish the initial release, tag it manually once:

```bash
git tag -a v2.0.0 -m "Release 2.0.0"
git push origin v2.0.0
```

Then create the GitHub Release for `v2.0.0` (Releases → Draft a new release →
choose the `v2.0.0` tag → generate notes). From here on, **the workflow takes
over** — you do not tag or edit versions by hand again.

## 4. Steady-state release loop (automatic)

On every merge to `main`, `auto-release.yml`:

1. Reads the current version from the router `skills/deepworkplan/SKILL.md`.
2. Inspects conventional commits since the last `vX.Y.Z` tag and picks the bump:
   `feat(...)!:` / `BREAKING CHANGE:` → MAJOR, `feat(...):` → MINOR, else PATCH.
3. Syncs the new version into **all** SKILL.md files (router + six sub-skills +
   addon).
4. Prepends a dated section to `CHANGELOG.md`.
5. Commits as `chore(release): X.Y.Z [skip ci]`, tags `vX.Y.Z`, pushes, and
   creates a GitHub Release.

Maintainers' only job is to **write good conventional commits**. Never hand-edit
`version:` fields, `CHANGELOG.md`, or tags — see [AGENTS.md](AGENTS.md) rule 4.

## 5. skills.sh registry

`skills.sh` resolves GitHub-hosted skills directly, so the install command
`npx skills add DailybotHQ/deepworkplan-skill` works as soon as the repo is
public — no separate registry submission is strictly required. To appear in the
searchable directory / get re-indexed:

- Ensure each `SKILL.md` has valid frontmatter (the CI validator guarantees this).
- Submit the repo to the skills.sh directory if/when an explicit submission flow
  exists; otherwise the indexer picks up the public repo and re-indexes within
  hours of each push to `main`.

## 6. OpenClaw listing

- Publish the pack to the OpenClaw registry so `openclaw skills install deepworkplan`
  resolves it. Follow the OpenClaw publishing flow (registry entry pointing at
  this GitHub repo / the `skills/deepworkplan/` path).
- OpenClaw loads the pack natively per eligible session; no auto-activation
  trigger files are needed.

## 7. `skills-lock.json` (consumer-side)

DeepWorkPlan does **not** ship a `skills-lock.json` of its own — that's a
**consumer-side** artifact. When a team installs at project scope (e.g.
`npx skills add DailybotHQ/deepworkplan-skill` inside a workspace), the
skills.sh CLI writes an entry (source, `skills/deepworkplan/SKILL.md` path, and
a content hash) to a `skills-lock.json` at *their* workspace root, mirroring how
the Dailybot Core Hub tracks its own `skills-lock.json` for reproducible
installs. Document this in onboarding, but never commit a fabricated lock file
into this skill repo.

## 8. Post-launch update path for end users

| Method | Update command |
|--------|----------------|
| `npx skills` | `npx skills update DailybotHQ/deepworkplan-skill` |
| Git clone | `cd <skill-path> && git pull && ./setup.sh` |
| OpenClaw | `openclaw skills update deepworkplan` |

Existing users pull the latest tagged release. Because the auto-release syncs
the version across every SKILL.md, the version a user sees in any sub-skill's
frontmatter matches the pack release they installed.
