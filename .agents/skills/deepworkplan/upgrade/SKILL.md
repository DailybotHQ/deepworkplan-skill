---
name: deepworkplan-upgrade
description: Check whether a newer DeepWorkPlan skill and DWP standard exists and — only after the developer explicitly accepts — install the latest published tag through the documented channel and re-run onboarding exactly as if https://deepworkplan.com/init.md were executed fresh, preserving every plan under .dwp/ and surfacing local adaptations instead of silently overwriting them. Use when the developer asks to upgrade, update, or refresh DWP in a repository that already has it installed. Do not use it to onboard a repo for the first time (that is the onboard sub-skill) or to migrate an old plan's shape (that is refine migrate, and plans are never migrated by an upgrade).
version: "5.0.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
---

# DeepWorkPlan — Upgrade (Sub-Skill)

Keep a repository's installed DeepWorkPlan skill and its declared DWP standard
current. Three phases, strictly ordered: **check** (read-only, safe to run
anytime), **consent** (nothing downloads without an explicit yes), **upgrade**
(same install command a fresh consumer runs, then onboarding re-executed as if
https://deepworkplan.com/init.md were executed fresh). An upgrade never touches
`.dwp/` — plans and their recorded evidence are history, not state to migrate
(`../spec/DWP_SPECIFICATION.md` §6.5).

---

## When to use

- "upgrade DWP", "update the deepworkplan skill", "is there a newer version?",
  "re-run the init", "/dwp-upgrade"
- Before a long plan, when the developer wants the harness current
- **Not** for first-time onboarding (route to `../onboard/SKILL.md`)
- **Not** for changing an in-flight plan's scope or shape (`../refine/SKILL.md`)
- **Not** for the targeted harness upgrade of one outdated piece — that is
  `../onboard/SKILL.md` Phase 0; this sub-skill replaces the whole skill first

## Context detection

Run the shared context helper to resolve the repo, branch, agent and `.dwp/`
location:

```bash
bash ../shared/context.sh
```

Then locate the installed pack: the `deepworkplan/` directory this sub-skill
was read from (in a repo, typically `.agents/skills/deepworkplan/`; a global
install lives under `~/.<agent>/skills/deepworkplan/`). Everything below reads
versions relative to that directory.

---

## Phase 1 — Check (read-only)

1. **Installed version.** Read `version:` from the installed pack's
   `SKILL.md` frontmatter — read it, never edit it. Also read the DWP standard
   the installed checker implements (`SUPPORTED_SPEC` in
   `verify/conformance.sh`) and the standard the repository declares (the
   `DWP standard:` line in `AGENTS.md`, if present).
2. **Latest published version.** Through the documented channel, resolve the
   newest release tag:
   ```bash
   git ls-remote --tags https://github.com/DailybotHQ/deepworkplan-skill.git
   ```
   Sort the `vX.Y.Z` tags numerically and take the highest. (`gh release view
   --repo DailybotHQ/deepworkplan-skill` is an equivalent alternative when the
   GitHub CLI is present.)
3. **Report, then stop.** State, in a few lines: installed skill version,
   latest published version, the standard each implements (the two series are
   2.x historical and 4.x current — `../spec/DWP_SPECIFICATION.md` "Status"),
   and where the changelog lives
   (`https://github.com/DailybotHQ/deepworkplan-skill/blob/main/CHANGELOG.md`).
   If installed == latest, say the repository is current and **end here**.
4. **Offline or unreachable upstream.** If the network call fails (no network,
   DNS, proxy, rate limit), say so in one line, state the installed version,
   and **exit cleanly** — no partial state, no error cascade, no retry loop.

## Phase 2 — Consent (nothing moves without an explicit yes)

1. **Name what the upgrade overwrites:** the vendored skill files under the
   installed pack directory (and only those). Name what it does **not** touch:
   `.dwp/` (plans, state, evidence), `AGENTS.md`, `docs/`, `.agents/` outside
   the vendored pack, and every addon the repository configured.
2. **Surface local adaptations before overwriting anything.** Repositories
   deliberately adapt their vendored copy (a repo may pin and maintain its own
   edition — a blind reinstall would erase that work). Stage the incoming tag
   into a temporary directory and diff it against the installed tree:
   ```bash
   diff -r --brief .agents/skills/deepworkplan "$TMP/incoming/deepworkplan" || true
   ```
   Report the differing files grouped two ways: files where the incoming tag
   itself changed (a normal upgrade), and files where the installed tree
   differs from the tag it claims (installed `version:`) — those are **local
   adaptations**. In a git repository the vendored tree is tracked, so the
   after-install `git diff` shows the full picture the same way.
3. **Ask.** One question, listing both groups: proceed with the upgrade, and
   for adapted files — re-apply the adaptation on top of the new version, or
   take the new version as-is? Only an explicit acceptance starts Phase 3; a
   decline or silence ends the sub-skill with the Phase 1 report standing.

## Phase 3 — Upgrade (accepted)

1. **Install the exact tag** the developer accepted, using the same documented
   command a fresh consumer would run through the skills.sh channel (both
   `-y` flags are required in a non-interactive session):
   ```bash
   npx --yes skills add DailybotHQ/deepworkplan-skill@vX.Y.Z --skill deepworkplan --force -y
   ```
   A repository that installed via Method 2 or 3 upgrades through its own
   documented channel instead (`openclaw skills update deepworkplan`, or
   `git pull && ./setup.sh` in the clone). Verify afterwards that the
   installed `version:` now equals the accepted tag; a mismatch aborts the
   phase with the difference stated — never continue on a wrong version.
2. **Re-run onboarding as if executing
   https://deepworkplan.com/init.md fresh.** Read `../onboard/SKILL.md` and
   execute it end-to-end as a first-run onboarding — **not** its Phase 0
   targeted-upgrade branch: the skill files were just replaced, so every
   phase re-reasons against the new version. Its guarantees hold unchanged —
   non-destructive, reconcile-don't-overwrite, idempotent on a second run.
   This re-detects the stack, reconciles `AGENTS.md`/`docs/`/`.agents/`, and
   re-offers addons under their standing policies (AI Diff Reviewer local
   install rides onboarding authorization; every optional addon still needs
   explicit acceptance).
3. **Re-stamp the standard.** The provenance line in `AGENTS.md` becomes
   `DWP standard: <the standard the new pack implements> (onboarded
   YYYY-MM-DD; upgraded YYYY-MM-DD; skill x.y.z)` — the upgrade variant of
   `../spec/DOCUMENTATION_STANDARD.md` §3.5. Never edit the skill's own
   `version:` fields or `CHANGELOG.md`; the release process owns them.
4. **Leave `.dwp/` untouched.** Plans keep their recorded lifecycle and their
   authored standard — an old plan declaring 2.x stays valid as historical and
   is never migrated by an upgrade; migrating one is a separate, explicit
   `refine migrate` decision (`../spec/DWP_SPECIFICATION.md` §6.5).
5. **Close the loop.** Re-apply the accepted adaptation decisions on the new
   files, run `../verify/SKILL.md` conformance, and report: old → new skill
   version, old → new standard stamp, what the re-onboarding reconciled, the
   adaptations applied or dropped, and the conformance verdict.

---

## Guarantees

- **Read-only until accepted.** Phase 1 writes nothing; Phase 3 starts only
  after an explicit yes naming exactly what changes.
- **`.dwp/` is history.** No plan, state file, gate record or evidence file is
  migrated, rewritten or invalidated by an upgrade.
- **No silent loss.** Local adaptations are diffed, listed and decided before
  any overwrite; a git-tracked vendored tree keeps the full audit trail.
- **Offline-safe.** An unreachable upstream is a clean report and exit —
  never a partial install and never a guess.
