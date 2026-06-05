# Installation Guide

DeepWorkPlan supports several install paths, ordered here from "easiest, most
users should use this" to "explicit fallback." Pick the one that matches your
situation — all paths produce the same runtime behavior; what differs is the
install ergonomics.

If you're picking for the first time and aren't sure: **use Method 1
(`npx skills add`).** It's the cross-agent, auto-detect, easy-to-update path.

---

## Quick comparison

| Method | When to use | Command (TL;DR) |
|--------|-------------|-----------------|
| 1. `npx skills add` (recommended) | Any agent, any OS, you have Node available | `npx skills add DailybotHQ/deepworkplan-skill` |
| 2. OpenClaw native | You're on OpenClaw | `openclaw skills install deepworkplan` |
| 3. Git clone + `setup.sh` | No Node available, you want explicit control | `git clone … && ./setup.sh` |
| 4. Manual per-agent | You want one specific agent and no symlink layer | `git clone … ~/.<agent>/skills/deepworkplan-pack` |

---

## Method 1 — `npx skills add` (cross-agent, recommended)

Uses the [skills.sh](https://skills.sh) CLI. It auto-detects which AI coding
agents you have installed and creates the appropriate symlinks for each.

```bash
npx skills add DailybotHQ/deepworkplan-skill
```

Useful flags:

| Flag | Purpose |
|------|---------|
| `--list` | Show the skills in the repo without installing |
| `-a <agent>` | Install for a specific agent only (e.g. `-a claude-code`, `-a cursor`) |
| `-g, --global` | Install globally (`~/.<agent>/skills/`) instead of per-project |
| `--copy` | Copy files instead of symlinking (use when symlinks aren't supported) |
| `-y` | Skip all prompts (CI/CD-friendly) |

Examples:

```bash
# Just see what's in the repo
npx skills add DailybotHQ/deepworkplan-skill --list

# Install only into Claude Code, globally
npx skills add DailybotHQ/deepworkplan-skill -a claude-code -g

# Non-interactive (e.g. inside a Dockerfile or CI step)
npx skills add DailybotHQ/deepworkplan-skill -y
```

Installing at **project scope** writes an entry to a workspace-root
`skills-lock.json` so the exact skill version is reproducible across your team —
commit that file to pin the version.

To update later: `npx skills update DailybotHQ/deepworkplan-skill`.
To uninstall: `npx skills remove deepworkplan`.

**Pros:** one command, cross-agent, easy updates. **Cons:** requires Node.js / `npx`.

---

## Method 2 — OpenClaw native registry

If your agent is [OpenClaw](https://www.openclaw.dev), use its built-in skill
registry — simpler than the cross-agent CLI and better integrated with OpenClaw's
session lifecycle.

```bash
openclaw skills install deepworkplan
```

OpenClaw loads the pack natively on every eligible session — no trigger setup
required. To update: `openclaw skills update deepworkplan`. To uninstall:
`openclaw skills remove deepworkplan`. See [`OPENCLAW.md`](OPENCLAW.md) for notes.

**Pros:** native to OpenClaw, no Node required, no symlink layer. **Cons:** OpenClaw-only.

---

## Method 3 — Git clone + `setup.sh`

For users who don't want Node and prefer explicit control. The included
`setup.sh` auto-detects which agents are installed and creates symlinks for each.

```bash
git clone https://github.com/DailybotHQ/deepworkplan-skill.git ~/deepworkplan-skill
cd ~/deepworkplan-skill
./setup.sh                 # auto-detect installed agents
./setup.sh --host claude   # or: cursor, codex, windsurf, copilot, cline, gemini, opencode, antigravity
```

`setup.sh` creates these symlinks for each detected agent:

- `~/.<agent>/skills/deepworkplan` → the cloned repo's `skills/deepworkplan/`
- `~/.<agent>/skills/deepworkplan-create` → `skills/deepworkplan/create/`
- `~/.<agent>/skills/deepworkplan-execute` → `skills/deepworkplan/execute/`
- `~/.<agent>/skills/deepworkplan-refine` → `skills/deepworkplan/refine/`
- `~/.<agent>/skills/deepworkplan-resume` → `skills/deepworkplan/resume/`
- `~/.<agent>/skills/deepworkplan-status` → `skills/deepworkplan/status/`
- `~/.<agent>/skills/deepworkplan-onboard` → `skills/deepworkplan/onboard/`

The per-sub-skill symlinks are what make `deepworkplan-create` etc. discoverable
as standalone slash commands.

To update later: `cd ~/deepworkplan-skill && git pull && ./setup.sh`.

To uninstall:

```bash
rm -rf ~/deepworkplan-skill
rm -f ~/.<agent>/skills/deepworkplan \
      ~/.<agent>/skills/deepworkplan-{create,execute,refine,resume,status,onboard}
```

**Pros:** zero external tools, full control, explicit about what's on disk.
**Cons:** manual updates (no `npx skills update`).

---

## Method 4 — Manual per-agent (no symlink layer)

For the simplest possible filesystem layout for one specific agent: clone the
repo directly into the agent's skills directory.

```bash
git clone https://github.com/DailybotHQ/deepworkplan-skill.git ~/.claude/skills/deepworkplan-pack
# or ~/.cursor/skills/deepworkplan-pack, etc.
```

Per-agent paths:

| Agent | Path |
|-------|------|
| Claude Code | `~/.claude/skills/<dir>` |
| Cursor | `~/.cursor/skills/<dir>` |
| OpenAI Codex | `~/.codex/skills/<dir>` |
| Windsurf | `~/.codeium/windsurf/skills/<dir>` |
| GitHub Copilot | `~/.copilot/skills/<dir>` |
| Cline | `~/.cline/skills/<dir>` |
| Gemini CLI | `~/.gemini/skills/<dir>` |
| OpenCode | `~/.config/opencode/skills/<dir>` |
| Antigravity | `~/.antigravity/skills/<dir>` |
| OpenClaw | `<workspace>/skills/<dir>` or `~/.openclaw/skills/` |

The runnable skill lives inside the clone at `skills/deepworkplan/`, and the
agent will discover it. **This does not create the per-sub-skill symlinks** —
`deepworkplan-create` etc. won't appear as standalone slash commands. If you need
those, use Method 3.

**Pros:** no extra tooling, simplest layout. **Cons:** no per-sub-skill
discoverability, manual updates, one agent at a time.

---

## Verifying the install

After any method, restart your agent (close + reopen the session, or use its
"reload" command) and check the skill is discovered. Ask *"what deepworkplan
skills are available?"* — a properly installed pack lists `deepworkplan` plus the
six sub-skills.

To verify the symlink state directly:

```bash
ls -la ~/.claude/skills/ | grep deepworkplan   # or your agent's path
```

You should see `deepworkplan` and `deepworkplan-{create,execute,refine,resume,status,onboard}`
(or just the `deepworkplan` directory if you used Method 4).

---

## What happens on first use

There are **no install prompts, no authentication, and no network calls** — this
is a markdown-first skill. The first time you ask an agent to *"onboard this
repo"* or *"create a plan"*, it simply reads the relevant `SKILL.md` and acts:

- **Onboarding** reasons about your repo's stack and archetype and generates an
  adapted `AGENTS.md`, `docs/`, per-module docs, `.agents/`, and the
  `.claude → .agents` symlink. It's non-destructive and idempotent, and it adds
  `.dwp/` to your `.gitignore`.
- **Plans** land under a gitignored `.dwp/` directory at the repo root
  (`.dwp/plans/PLAN_<slug>/`, `.dwp/drafts/`), overridable via the `DWP_DIR`
  environment variable.

---

## Updating the skill

| Method used | Update command |
|-------------|----------------|
| 1 (`npx skills add`) | `npx skills update DailybotHQ/deepworkplan-skill` |
| 2 (OpenClaw) | `openclaw skills update deepworkplan` |
| 3 (git clone + setup) | `cd <skill-path> && git pull && ./setup.sh` |
| 4 (manual per-agent) | `cd <skill-path> && git pull` |

---

## Uninstalling

| Method used | Uninstall steps |
|-------------|-----------------|
| 1 | `npx skills remove deepworkplan` |
| 2 | `openclaw skills remove deepworkplan` |
| 3 / 4 | Delete the cloned directory and any per-agent symlinks (see Method 3 for the symlink list) |

---

## Troubleshooting

| Problem | Likely cause |
|---------|--------------|
| Agent doesn't recognize the skill after install | Restart the session. Agents discover skills at session start, not mid-session. |
| `npx skills add` fails with a Git error | Wrap the repo slug in quotes if your shell expands it: `'DailybotHQ/deepworkplan-skill'`. |
| Sub-skills (`deepworkplan-create` etc.) don't appear as slash commands | You used Method 4 (no symlink layer). Use Method 3 for per-sub-skill discoverability. |
| Plan output showing up in `git status` | `.dwp/` should be gitignored. Re-run onboarding, or add `.dwp/` to `.gitignore` manually. |

---

## See also

- [`../README.md`](../README.md) — quick-start version of this guide
- [`OPENCLAW.md`](OPENCLAW.md) — OpenClaw-specific notes
- [`DESIGN.md`](DESIGN.md) — why the install paths and layout are what they are
- [`../SECURITY.md`](../SECURITY.md) — what the skill does on your machine
- [`../skills/deepworkplan/shared/dwp-paths.md`](../skills/deepworkplan/shared/dwp-paths.md) — the `.dwp/` output convention
