---
name: dailybot-env
description: Manage per-repo API key overrides in `.dailybot/env.json` — an opt-in, gitignored file that carries API keys + optional URLs for one or more environments (live, local, staging). One profile is active at a time; when set, it overrides `DAILYBOT_API_KEY`, `config.json`, and the login Bearer session for the enclosing repo. Use when the developer wants to be "logged into different orgs in different repos" simultaneously, needs a local dev key just for this project, or wants to toggle between staging and prod without touching global config or env vars. Requires CLI >= 3.9.0 (pack baseline; `env` shipped in 3.7.0).
version: "3.23.2"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"🔑","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot per-repo API key override (`env.json`)

> **Requires `dailybot-cli >= 3.9.0`** (the skill-pack baseline). The
> `dailybot env` command group and `.dailybot/env.json` loader shipped in
> 3.7.0 and are included in this floor. If `dailybot --version` reports
> below 3.9.0, ask the developer to run `dailybot upgrade` before continuing.
> See [`../SKILL.md` § Required Dailybot CLI version](../SKILL.md#required-dailybot-cli-version).

This sub-skill lets an agent configure and manage `<repo>/.dailybot/env.json` — an **opt-in, gitignored** file that pins API keys + URL overrides per environment (live, local, staging) for the enclosing repo. When a profile is *active*, it overrides `DAILYBOT_API_KEY`, `config.json`, and the login Bearer session **only for that repo**.

> **The full workflow, schema, security rules, and worked examples live in [`../shared/env-json.md`](../shared/env-json.md).** Read it first — it is the single source of truth. This file is the routing entry-point and quick-reference.

## When to use

Route here when the developer says any of:

- *"I want a local API key just for this project."*
- *"How do I test against staging without breaking my prod login?"*
- *"Can I be in org A in this repo and org B in another repo?"*
- *"Set up per-project Dailybot credentials for me."*
- *"Switch this repo to my localhost Dailybot instance."*
- *"Keep production login for reports but test Plan locally."*
- *"Switch env profiles / live vs testing."*

**Do not** route here when:

- The developer is in CI. Use `DAILYBOT_API_KEY` as an env var — leaves no on-disk secret.
- The developer wants team-shared *identity* (agent name, default metadata). That's `.dailybot/profile.json` — see [`../shared/repo-profile.md`](../shared/repo-profile.md).
- The developer has one Dailybot org and a working login session. `dailybot login` + global config is simpler.

## Pre-flight — before writing anything

1. **Confirm the CLI meets the pack baseline** (>= 3.9.0):

    ```bash
    dailybot env --help >/dev/null 2>&1 || {
      echo "This feature requires dailybot-cli >= 3.9.0. Run: dailybot upgrade" >&2
      exit 1
    }
    ```

2. **Ensure the repo's `.gitignore` covers `.dailybot/*`.** The Dailybot skill pack expects this pattern:

    ```gitignore
    .dailybot/*
    !.dailybot/profile.json
    ```

    If missing, add it (creating `.gitignore` if needed):

    ```bash
    grep -q '^\.dailybot/\*' .gitignore 2>/dev/null || cat >> .gitignore <<'EOF'

    # Dailybot per-repo state (env.json contains API keys — never commit it)
    .dailybot/*
    !.dailybot/profile.json
    EOF
    ```

    If the developer skips this step and later commits `env.json`, the CLI will refuse to load it and print an actionable error. `dailybot env add` also fires a soft warning when the file isn't gitignored yet.

## The commands (quick reference)

```bash
# CREATE a profile (creates the file if needed; first profile auto-becomes active)
dailybot env add --name NAME --key KEY [--api-url URL] [--app-url URL] [--kind live|testing]

# SWITCH active profile
dailybot env use NAME       # switch active
dailybot env use ""         # clear active (fall through to global auth)

# INSPECT
dailybot env show           # resolved profile (API key masked)
dailybot env list           # all profiles, active marked

# DELETE
dailybot env remove NAME [--yes]

# KILL SWITCH (preserves active)
dailybot env off            # disable the file
dailybot env on             # re-enable
```

All API keys are masked in output (`sk_l****`). The CLI never echoes the full key back.

## Common recipes

### First-time setup for a local dev org

```bash
dailybot env add \
  --name local \
  --key sk_local_xxxxxxxx \
  --api-url http://localhost:8000 \
  --app-url http://localhost:8090

dailybot env show   # verify
```

Because this is the first profile, it becomes active automatically. Every subsequent `dailybot` command in this repo now talks to `http://localhost:8000`. Other repos are unaffected.

### Toggle between staging and prod

```bash
dailybot env add --name prod    --key sk_prod_xxxx           # first → auto-active
dailybot env add --name staging --key sk_staging_yyyy \
                                --api-url https://staging-api.example.com

dailybot env use staging   # switch to staging for bug repro
# ... work in staging ...
dailybot env use prod      # switch back
```

### Temporarily disable env.json without losing setup

```bash
dailybot env off   # env.json ignored; CLI falls through to global auth
# ... test something with your global login ...
dailybot env on    # restores the previously active profile
```

`env off` sets `disabled: true` at the top level; `active` is preserved so `env on` instantly restores the previous selection.

### Dual session — production reports, local testing (recommended)

The pack is production-first. Keep OTP (or a `kind: live` profile) for **reports**. Put local/dev keys in the **same** `env.json` as `kind: testing` and switch with `env use` — nothing new to learn.

```bash
dailybot env off                    # production login for agent update / default CLI
dailybot env add --name local --key sk_local_xxxxxxxx \
  --api-url http://localhost:8000   # infers --kind testing
dailybot env use local              # this repo now talks to local
# ... Plan / API probes ...
dailybot env off                    # REQUIRED before dailybot agent update
dailybot agent update "…"           # production dashboard
```

Do **not** `dailybot login` while a testing profile is active. A login token only travels to the API host that issued it, so a testing profile never receives the production session, not even as a fallback; a Plan structure write refused for the testing key (an agent or organization key, or a guest's) ends as exit 4 `insufficient_scope` or `guest_not_allowed`. Full rules: [`../shared/env-json.md` § Dual session](../shared/env-json.md#dual-session--production-reports--testing-profiles).

### Delete a profile

```bash
dailybot env remove staging --yes
# If 'staging' was active, active is cleared and the CLI falls back to
# global auth until you run `dailybot env use <name>` again.
```

## Security — what an agent must never do

1. **Never `cat` or otherwise print raw `env.json`.** It contains API keys. Use `dailybot env show` / `dailybot env list` — they mask.
2. **Never suggest committing `env.json`.** The CLI has a fatal `RepoEnvError` guard that fires on load if the file is tracked.
3. **Never write API keys into `.dailybot/profile.json`.** That is a hard error in the CLI. `env.json` is the ONLY sanctioned place inside `.dailybot/` for credentials.
4. **If the developer accidentally committed `env.json`**: tell them to rotate every key immediately (assume compromise), then `git rm --cached` + fix `.gitignore` + rewrite `env.json` with newly generated keys. Do NOT try to `git filter-repo` the leak away — assume the world has seen the keys.

Full four-layer protection story (gitignore, `0o600`, fatal refuse-if-tracked, write-time gitignore warning): see [`../shared/env-json.md` § Security](../shared/env-json.md#security--non-negotiable-rules).

## Interaction with existing auth (short version)

| Existing flow | Effect when env.json is active in this repo |
|---|---|
| `dailybot login` | Still writes Bearer to `credentials.json`. env.json wins **inside this repo**. Other repos use the Bearer normally. |
| `dailybot logout` | Unaffected — only clears Bearer. env.json remains intact. |
| `dailybot config key=...` | Still works globally. env.json sits above it in precedence. |
| `DAILYBOT_API_KEY` env var | Still works. env.json beats it inside a repo. |
| `.dailybot/profile.json` | Orthogonal — still signs reports (identity). env.json provides credentials + URLs. Both can be present. |

Precedence order (full table in [`../shared/env-json.md` § Auth resolution order](../shared/env-json.md#auth-resolution-order-updated-in-cli-370)).

## Troubleshooting (quick reference)

- **"The CLI is not using my env.json."** → `dailybot env show`; check `disabled`, `active`, and the walk-up path. Are you overriding with `--profile` / `--api-url` / `--app-url` flags?
- **"The CLI refuses to run and complains about tracked env.json."** → run the exact fix printed in the error message. Staged-but-uncommitted counts as tracked. (`dailybot hook *` commands print the error but still run and exit 0 — by design, per their harness contract.)
- **"I edited env.json by hand and now nothing works."** → `dailybot env show` surfaces schema warnings; if unrecoverable, delete the file and re-add profiles via `dailybot env add`.
- **"A Plan structure write fails with `insufficient_scope` on my testing profile, but I'm logged in."** → expected. Your login belongs to the production host; the CLI never sends it to another host, so the testing key alone answered, and it is an agent or organization key (nobody behind it). Use a personal API key that host issued to a non-guest member, or sign in against that host.
- **"I set `disabled: "true"` and it's still active."** → `disabled` must be a JSON boolean; the CLI warns and treats a string as `false`. Use `dailybot env off`.

## See also

- [`../shared/env-json.md`](../shared/env-json.md) — full schema, precedence, security posture, worked examples.
- [`../shared/repo-profile.md`](../shared/repo-profile.md) — the sibling `profile.json` file (agent identity, tracked in git).
- [`../shared/auth.md`](../shared/auth.md) — general authentication flow (OTP login, API key alternatives, CLI installation).
