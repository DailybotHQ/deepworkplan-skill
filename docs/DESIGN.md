# Design Decisions

Why this repository is laid out the way it is. If you're about to refactor
something to "modernize" or "simplify" it, read the relevant section first — most
of these choices have a reason that isn't obvious from the files, and reversing
them breaks either discovery, the ship boundary, or the methodology itself.

This document is for AI agents and human contributors who need the *why*, not
just the *what*. The conventions themselves are in [`AGENTS.md`](../AGENTS.md).
The behavior is in [`skills/deepworkplan/SKILL.md`](../skills/deepworkplan/SKILL.md)
and the normative standard under
[`skills/deepworkplan/spec/`](../skills/deepworkplan/spec/README.md).

---

## 1. Router meta-skill + sub-skills (not one big SKILL.md)

We ship **one discoverable skill** (`deepworkplan`) that routes to six internal
sub-skills (`onboard`, `create`, `execute`, `refine`, `resume`, `status`). An
alternative would have been a single multi-thousand-line `SKILL.md` covering
everything.

We chose the router approach because:

- **Description-based discovery works better with focused descriptions.** When an
  agent decides "should I activate this skill?", it reads the `description`
  field. A focused description like *"Resume an interrupted plan from its
  recorded progress"* triggers more accurately than a generic *"Do anything with
  plans"*.
- **Different invocation policies per capability.** Each sub-skill is its own
  `/deepworkplan-*` slash command with its own frontmatter, so users can invoke
  exactly the verb they want.
- **Independent symlinks via `setup.sh`.** Users get
  `~/.claude/skills/deepworkplan-create` etc. as standalone commands. This
  requires each sub-skill to live in its own folder.
- **Easier to evolve one capability without touching others.** A change to
  `execute/SKILL.md` doesn't ripple into `onboard/`.

Trade-off: more files. We accept that — for a public skill people will audit,
focused files beat one giant one.

## 2. Everything under `skills/deepworkplan/` (not `SKILL.md` at repo root)

skills.sh discovers skills in two patterns: a `SKILL.md` at the repo root (for
single-skill repos), or `skills/<name>/SKILL.md` (for single or multi-skill
packs). We use the second pattern even though we ship one logical skill because:

- It lets us keep dev infrastructure at the repo root (`AGENTS.md`, `tests/`,
  `scripts/`, `docs/`, `.github/`) without ambiguity. With the root pattern,
  every root file becomes part of the "skill" semantically.
- The boundary "what ships at runtime" is unambiguous: **anything inside
  `skills/deepworkplan/` ships, anything outside doesn't.** No `.skillignore`-style
  exclusion list to maintain.

The CI ship-boundary discipline (and `AGENTS.md` rule #2) depend on this holding.

## 3. `shared/`, `spec/`, `guide/`, `examples/`, `addons/` live **inside** the pack

`context.sh`, `dwp-paths.md`, `adaptation.md`, the RFC-2119 spec, the methodology
guide, the templates, and the addons are all under `skills/deepworkplan/` even
though they're "reference material," because:

- skills.sh and `setup.sh` install the **pack directory**. If `spec/` or
  `shared/` were siblings (e.g. `skills/_shared/`), an installed
  `deepworkplan/SKILL.md` referencing `../shared/context.sh` wouldn't resolve on
  the user's machine.
- Every install must be self-contained. A sub-skill may read `../shared/`,
  `../spec/`, or `../examples/`, but it must never reach *out of*
  `skills/deepworkplan/`.

## 4. `setup.sh` exists alongside `npx skills add`

There are two install paths: `npx skills add dailybotops/deepworkplan-skill`
(skills.sh CLI, the canonical cross-agent installer) and `git clone && ./setup.sh`
(symlinks the pack and each sub-skill). `setup.sh` is not redundant:

- It works without Node.js / npm. Users in minimal containers, or who prefer not
  to add an npm dependency, get a pure-bash path.
- It makes the layout obvious — the script is small and readable and shows
  exactly which path the skill installs to per agent.
- It's the path you use while hacking on the skill locally: clone, edit, re-run
  setup, and your symlinked install picks up edits live.

## 5. `documentation_url` (not `homepage`) in frontmatter

Older Agent Skill examples used `homepage:` for the project URL. We use
`documentation_url:` because some agent harnesses interpret `homepage` as "fetch
this URL to refresh the skill content" — a remote-load semantics we explicitly
don't want. A single DNS/CDN issue could otherwise push modified instructions to
every installed user. `documentation_url` is unambiguous: a *reference link*, not
a *re-fetch source*. `scripts/validate-frontmatter.py` rejects any new
`homepage:` entries.

## 6. Kebab-case `name:` in frontmatter (not snake_case)

skills.sh URLs and flags use kebab-case (`deepworkplan-create`), and `setup.sh`
symlinks are kebab (`~/.claude/skills/deepworkplan-create`). Snake_case in
frontmatter plus kebab in symlinks is an inconsistency that confuses users and
breaks discovery for some agents. The validator rejects `deepworkplan_*` names.

## 7. The `.dwp/` output convention (gitignored working state)

All Deep Work Plan output lives in a gitignored `.dwp/` directory at the repo
root (`.dwp/plans/PLAN_<slug>/`, `.dwp/drafts/`), resolved by
[`shared/context.sh`](../skills/deepworkplan/shared/context.sh) and overridable
via `DWP_DIR`. We chose a single conventional, gitignored directory because:

- **Plan artifacts are working state, not committed source.** They're how an
  agent and a developer coordinate a long-running effort — valuable during the
  work, noise in the git history afterward.
- **One predictable location** lets every sub-skill find prior plans without
  configuration, and lets onboarding add one line to `.gitignore` instead of
  scattering output across the tree.
- For orchestrator hubs, child plans nest under
  `repositories/<repo>/.dwp/plans/…` — same convention, applied per managed repo.

This is a public contract (see `AGENTS.md` rule #5): changing the `.dwp/` layout
or the `DWP_DIR`/`DWP_AGENT_TOOL` env vars is a breaking change.

## 8. Reasoning over copy-paste (~90% baseline, ~10% reasoned per repo)

The skill is **markdown-first**: its "code" is instructions an agent reads and
then *reasons about*, not templates it blindly stamps out. As
[`shared/adaptation.md`](../skills/deepworkplan/shared/adaptation.md) puts it,
roughly 90% of any generated artifact follows a fixed baseline shape, and ~10% is
reasoned from the target repo's actual stack, validation commands, and module
layout. We designed it this way because a skill that copy-pastes a fixed
`AGENTS.md` produces plausible-but-wrong docs for every repo that isn't the one
it was templated from. The onboarding presets under
[`onboard/presets/`](../skills/deepworkplan/onboard/presets/README.md) are
*reasoning starting points*, not files to copy verbatim.

## 9. Two archetypes (individual repo vs orchestrator hub)

Onboarding and plan execution branch on two repo archetypes, classified by a
heuristic in [`spec/ARCHETYPES.md`](../skills/deepworkplan/spec/ARCHETYPES.md): a
normal **individual repo** (the ~99% case) and an **orchestrator hub** that
coordinates work across many managed repos. We encode this explicitly rather than
pretend one shape fits all because the orchestrator case needs child `.dwp/`
nesting, an `ORCHESTRATOR_MANIFEST.md`, and integration-checkpoint tasks that
would be dead weight in a single repo.

## 10. A normative RFC-2119 spec, shipped with the skill

The standard itself — five RFC-2119 documents under
[`spec/`](../skills/deepworkplan/spec/README.md) — ships inside the pack, not just
on the website. The skill *implements* a standard, and an agent benefits from
reading the MUST/SHOULD/MAY contract directly when it needs to resolve an
ambiguity. Keeping the spec versioned alongside the sub-skills also means the
standard and its implementation can never silently drift apart.

## 11. Addons are opt-in and non-blocking

The `devcontainer` and `dailybot` addons under
[`addons/`](../skills/deepworkplan/addons/README.md) are strictly opt-in. Core
DeepWorkPlan has **zero** dependency on either — the `dailybot` addon, for
instance, only wires optional progress reporting *if* the developer already has
Dailybot and consents, and it must never block plan execution. We keep addons
vendor-neutral and deferred so the core methodology stays useful to everyone and
the skill never becomes a covert install vector for a vendor's tooling.

## 12. Markdown-first: no network, no CLI, no auth, no consent prompts

Unlike skills that call a vendor API, DeepWorkPlan makes **no network calls,
ships no CLI, and needs no authentication**. The only executable code is two
bash helpers that read local git/filesystem state and emit JSON. This is a
deliberate security posture (see [`SECURITY.md`](../SECURITY.md)): the smaller
the runtime surface, the easier the skill is to audit and approve. It's also why
this repo has no consent/secret-scan flows — there's no outbound action to gate.

## 13. Versioning is automatic (conventional commits → auto-release)

`.github/workflows/auto-release.yml` reads the version from the router
`SKILL.md`, inspects conventional commits since the last tag, bumps every
`SKILL.md` in sync, prepends to `CHANGELOG.md`, tags, and creates a GitHub
Release on every merge to `main`. Contributors never hand-edit `version:` fields,
`CHANGELOG.md`, or tags. We automate this because a markdown skill spread across a
router plus six sub-skills plus addons is exactly the kind of thing where
hand-bumping versions drifts out of sync — and a wrong version is what users see
first.
