# Adding a New Sub-Skill

Step-by-step for adding a new capability under `skills/deepworkplan/`. Use this
when you have a new verb that's distinct enough from the existing six
(`onboard`, `create`, `execute`, `refine`, `resume`, `status`) to deserve its own
`SKILL.md`, but tightly enough coupled to the DeepWorkPlan methodology that it
belongs in this pack rather than a separate repo.

If you're not sure whether your idea qualifies, see the decision tree at the
bottom.

---

## 0. Decide the name

Pick a kebab-case name starting with `deepworkplan-`:

```
deepworkplan-review
deepworkplan-archive
deepworkplan-split
```

Snake_case (`deepworkplan_review`) and camelCase (`deepworkplanReview`) are
forbidden — they break skills.sh discovery and `setup.sh` symlink naming. CI
(`scripts/validate-frontmatter.py`) will reject them.

The folder name **drops the `deepworkplan-` prefix** because it lives inside
`skills/deepworkplan/`:

```
skills/deepworkplan/review/SKILL.md      # name in frontmatter: deepworkplan-review
```

## 1. Create the directory

```bash
mkdir -p skills/deepworkplan/<verb>
```

If your skill has supporting files (templates, examples), put them in the same
directory so the install stays self-contained:

```
skills/deepworkplan/<verb>/
├── SKILL.md
├── examples.md          # optional
└── command-templates/   # optional, like onboard/command-templates/
```

Never reach *out of* `skills/deepworkplan/` at runtime — a sub-skill may read
`../shared/`, `../spec/`, or `../examples/`, but nothing above the pack.

## 2. Write `SKILL.md`

Copy this template and adjust:

```markdown
---
name: deepworkplan-<verb>
description: <one paragraph with trigger phrases — when to activate, what it produces, when NOT to use it. This is what every agent harness uses for relevance scoring.>
version: "2.0.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
---

# DeepWorkPlan — <Verb> (Sub-Skill)

<One paragraph: what this sub-skill does and when an agent should use it.>

---

## When to use

- <trigger phrase 1>
- <trigger phrase 2>
- <when NOT to use it — route elsewhere>

---

## Context detection

Run the shared context helper to resolve the repo, branch, agent, and `.dwp/`
location:

\`\`\`bash
bash ../shared/context.sh
\`\`\`

See [`../shared/dwp-paths.md`](../shared/dwp-paths.md) for the `.dwp/` output
convention and [`../shared/adaptation.md`](../shared/adaptation.md) for the
reasoning-over-copy-paste principle.

---

## Steps

1. …
2. …

---

## Additional resources

- [`../spec/DWP_SPECIFICATION.md`](../spec/DWP_SPECIFICATION.md) — the normative plan contract
- [`../guide/GUIDE.md`](../guide/GUIDE.md) — the methodology guide
```

> Set `version` to match whatever the rest of the pack currently carries — the
> auto-release bot keeps every `SKILL.md` in sync, so a new file just needs to
> start at the same version the router has, then it rides the next release.

### Frontmatter checklist

- [ ] `name` is kebab-case and starts with `deepworkplan-`
- [ ] `description` is a full paragraph; mentions both *when to use* and *when not to*
- [ ] `version` is quoted (`"2.0.0"`) — and you did **not** hand-pick a new number
- [ ] `documentation_url` (NOT `homepage`)
- [ ] `user-invocable` is `true` if the developer should be able to type
      `/deepworkplan-<verb>` to invoke it explicitly, `false` otherwise
- [ ] `allowed-tools` lists only what the skill actually uses

## 3. Register it in the router meta-skill

Edit `skills/deepworkplan/SKILL.md` (the router) and add a row to the
**routing rules** table mapping intent phrases → your new sub-skill:

```
| "review the plan", "/dwp-review" | **Review** → read [`review/SKILL.md`](review/SKILL.md) |
```

## 4. Update `setup.sh`

Add the verb to the `SKILLS` array so symlinks get created for it:

```bash
SKILLS=("create" "execute" "refine" "resume" "status" "onboard" "<verb>")
```

This is what makes `deepworkplan-<verb>` appear as a standalone slash command
after `setup.sh` runs.

## 5. Add tests (if it ships shell behavior)

The frontmatter validator checks discoverability automatically in CI. If your
sub-skill ships a shell helper or changes `setup.sh`/`context.sh` behavior, add or
extend a bats file under `tests/` covering at least the happy path and one edge
case. At minimum, the existing `tests/setup-sh.bats` should be updated so the new
symlink is asserted:

```bash
[ -L "$FAKE_HOME/.claude/skills/deepworkplan-<verb>" ]
```

## 6. Update documentation

- `README.md` — add the new sub-skill to the **Skills** table and the
  uninstall symlink list.
- `CONTRIBUTING.md` / `AGENTS.md` — only if the sub-skill changes a convention.
- The spec under `skills/deepworkplan/spec/` — only if the new verb introduces
  normative behavior other agents must implement.

Do **not** edit `CHANGELOG.md` or `version:` fields — the auto-release bot owns
them.

## 7. Pre-merge checks

Same as for any other PR:

```bash
shellcheck setup.sh skills/deepworkplan/shared/context.sh scripts/*.sh
bats tests/
python3 scripts/validate-frontmatter.py
HOME="$(mktemp -d)" ./setup.sh --host claude   # confirm the new symlink is created
```

## 8. Commit with the right prefix

Adding a new sub-skill is **additive**, so use a `feat(...)` prefix to make the
auto-release pick a MINOR bump:

```
feat(<verb>): add the deepworkplan-<verb> sub-skill
```

If the new sub-skill removes or renames existing public surface (a slash command,
the `.dwp/` convention, a `setup.sh` flag), it's a MAJOR change — use
`feat(<verb>)!:` and document the migration in the PR body.

---

## Decision tree: should I add a sub-skill, or do something else?

| Situation | Recommendation |
|-----------|---------------|
| New verb with distinct trigger phrases (e.g. "review a plan") | ✅ Add a sub-skill |
| Tweak to an existing flow (e.g. a new option in `execute`) | ❌ Modify the existing sub-skill, don't fork |
| Helper that multiple sub-skills will use | ❌ Add to `skills/deepworkplan/shared/`, not as a sub-skill |
| New reproducible-environment or vendor integration | ⚠️ Consider an **addon** under `addons/` (opt-in, non-blocking) — see [`spec/ADDONS.md`](../skills/deepworkplan/spec/ADDONS.md) |
| New onboarding behavior for a specific stack | ❌ Add a preset under `onboard/presets/`, not a new sub-skill |
| Internal dev/debug tool for maintainers | ❌ Belongs in `scripts/` at the repo root, never in `skills/` |

If in doubt, open an issue with the feature-request template and sketch the user
story before writing code. The router works best when each sub-skill is genuinely
distinct — adding overlapping verbs makes routing decisions noisier for every
agent that loads the pack.
