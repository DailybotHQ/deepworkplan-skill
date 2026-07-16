# Per-repo API key override (`.dailybot/env.json`)

> **Read this if the developer asks about "switching between orgs per repo", "local dev keys", "logging into a staging org just for this project", or setting up "different Dailybot environments" for testing.** This is a single source of truth for the `env.json` workflow — sub-skills link here instead of duplicating the rules.

The Dailybot CLI (>= **3.7.0**) supports a per-repository file at `<repo>/.dailybot/env.json` that carries API keys + optional URL overrides for one or more environments (`live`, `local`, `staging`, ...). When a profile is *active*, it overrides `DAILYBOT_API_KEY`, `config.json`, and the login Bearer session **for the enclosing repo only** — enabling the developer to be "logged into different orgs in different repos" without touching global state or env vars.

`env.json` is **opt-in, gitignored, and never required**. The CLI works exactly as before when the file is absent.

---

## STOP — the one thing you MUST enforce as an agent

**`.dailybot/env.json` must NEVER be committed to git. Ever. Under any circumstance.**

If the developer's request involves creating, editing, sharing, moving, or explaining `env.json`, you must treat "keep it gitignored" as a non-negotiable invariant. Concretely, that means:

- **NEVER** run or suggest `git add .dailybot/env.json` (or `git add -A` / `git add .` from a place that would sweep it in). The CLI's `add` command writes the file to disk — that is the *only* place it should ever exist.
- **NEVER** `cat`, `head`, `tail`, or otherwise print the raw file contents into the chat, into a report, into a PR body, or into any other artifact — API keys live inside. Use `dailybot env show` / `dailybot env list` which mask them.
- **NEVER** copy the file into `tmp/`, into a docs example, into a test fixture, or into any other tracked location. If you need to reference structure, use the placeholder schema shown in this doc (with `sk_local_xxxx`-style dummy keys).
- **NEVER** try to work around the CLI's fatal refuse-if-tracked guard (see § "Security — non-negotiable rules" below). If the CLI is blocking a command because `env.json` is tracked, the *only* correct answer is `git rm --cached .dailybot/env.json` + rotate the exposed keys — not `--no-verify`, not "temporarily untrack", not editing the guard away.
- **ALWAYS** verify the repo's `.gitignore` contains `.dailybot/*` before the developer's first `dailybot env add`. If it doesn't, add it (and commit that change) *first*.
- **ALWAYS** treat "the file was committed at some point in history" as a compromise: rotate every key in it via the Dailybot dashboard immediately, then follow the recovery recipe below.

The rule is absolute because git history is forever. On a public repo the keys are burned the instant the push lands; on a private repo they still leak to every collaborator, every past fork, every CI cache, and every backup. `git revert` does not undo the exposure. **Rotate, don't revert.**

The CLI enforces this same rule with four independent protections (gitignore convention, `0o600` permissions, a fatal load-time guard in the root `cli()` callback, and an advisory write-time `git check-ignore` warning). All of them must be in place. If any of them looks broken on the developer's machine, treat it as a bug worth reporting — do NOT paper over it.

---

## When to reach for `env.json`

Suggest it when the developer says any of:

- *"I want a local key just for this project."*
- *"How do I test against staging without messing up my prod login?"*
- *"I need to be in org A in this repo and org B in another repo."*
- *"Can I have per-project Dailybot credentials?"*

Do **not** suggest it when:

- The developer is in CI. Recommend `DAILYBOT_API_KEY` as an env var instead — leaves no on-disk secret to clean up.
- The developer wants team-shared identity for the repo — that's [`profile.json`](repo-profile.md), not `env.json`.
- The developer has a single Dailybot org and a working login session. `dailybot login` + global config is simpler.

---

## Distinction from `profile.json` (critical, do not confuse them)

The two files live side-by-side in `.dailybot/` but serve **opposite roles**:

| File | Committed? | Contains | Role |
|---|---|---|---|
| `.dailybot/profile.json` | **Yes** (tracked) | `name`, `default_metadata`, `report`, `vars` | **Identity** — how the agent signs reports (team-shared) |
| `.dailybot/env.json` | **No** (gitignored) | `api_key`, `api_url`, `app_url` per profile | **Auth context** — which org the CLI talks to (per-developer, per-machine) |

Neither file overlaps on any field. Both can be present, and typically will be: `profile.json` pins the report signature ("this repo's reports come from `Core Hub Bot`"), while `env.json` picks which Dailybot org those reports get sent to on your machine right now.

**Under NO circumstances** should you write API keys to `profile.json` — the CLI hard-errors with `RepoProfileError` when it detects a `key` field there. `env.json` is the ONLY sanctioned place inside `.dailybot/` for credentials.

---

## Schema

```json
{
  "disabled": false,
  "active": "local org 1",
  "profiles": [
    {
      "name": "live",
      "api_key": "sk_live_xxxxxxxx"
    },
    {
      "name": "local org 1",
      "api_key": "sk_local_xxxxxxxx",
      "api_url": "http://localhost:8000",
      "app_url": "http://localhost:8090"
    },
    {
      "name": "staging",
      "api_key": "sk_staging_xxxxxxxx",
      "api_url": "https://staging-api.example.com",
      "app_url": "https://staging-app.example.com"
    }
  ]
}
```

| Field | Type | Required? | Purpose |
|---|---|---|---|
| `disabled` | boolean | optional (default `false`) | Kill-switch. `true` ignores the whole file even if `active` points to a valid profile. Preserves `active` for one-command re-enable. Must be a **JSON boolean** — a hand-edited string like `"true"` is NOT honored: the CLI warns loudly and the file **stays active** (use `dailybot env off` instead). |
| `active` | string \| null | optional | Name of the profile to use. `null` / `""` / missing / unknown-name → file is *inert* and resolution falls through. Only one active at a time. |
| `profiles` | list of objects | **required** | Every configured environment. |
| `profiles[].name` | string | **required** | Unique per file. Human-friendly, may contain spaces. |
| `profiles[].api_key` | string | **required** | The API key for this environment. Plain-text on disk — gitignore is mandatory. |
| `profiles[].api_url` | string | optional | Overrides `DAILYBOT_API_URL` / `credentials.json` when this profile is active. Falls through to `https://api.dailybot.com` when absent. |
| `profiles[].app_url` | string | optional | Overrides `DAILYBOT_APP_URL` when this profile is active. Falls through to `https://app.dailybot.com` when absent. |

Unknown keys are logged as a warning and ignored (forward-compatibility). snake_case only — camelCase is a schema violation.

---

## CLI workflow (always prefer these commands over hand-editing)

```bash
# First profile — creates the file at <repo>/.dailybot/env.json with 0o600
# perms and auto-marks itself active.
dailybot env add \
  --name "local org 1" \
  --key sk_local_xxxxxxxx \
  --api-url http://localhost:8000 \
  --app-url http://localhost:8090

# Additional profiles — appended, active pointer unchanged.
dailybot env add --name live    --key sk_live_yyyyyyyy
dailybot env add --name staging --key sk_staging_zzzzzzzz \
  --api-url https://staging-api.example.com

# Switch which profile is active.
dailybot env use staging
dailybot env use ""                    # clear active → fall through to global auth

# Inspect.
dailybot env show                      # resolved profile (API key masked)
dailybot env list                      # all profiles, active marked
# `env show` also prints an explicit "Disabled: no" row (since `disabled:
# false` is normalized away on write) and resolves defaulted API/Webapp URLs
# so the developer sees the concrete server the context points at.

# Kill-switch — preserves `active` so `on` restores instantly.
dailybot env off
dailybot env on

# Delete a profile. If it was the active one, active is cleared.
dailybot env remove staging --yes
```

The CLI ALWAYS masks API keys in output (`sk_l****` — first 4 chars + `****`). It never echoes the full key back.

---

## Auth resolution order (updated in CLI 3.7.0)

The full precedence for `api_key` / `api_url` / `app_url` when a repo has `env.json`:

| # | Layer | Notes |
|---|---|---|
| 1 | `--profile` / `--api-url` / `--app-url` CLI flags | Per-invocation escape hatch — always wins |
| **2** | **`.dailybot/env.json` active profile** | **New in 3.7.0** — the whole innovation |
| 3 | `.dailybot/profile.json::profile` → `agents.json` | Existing repo profile → global agent profile chain |
| 4 | `agents.json` default profile | Global default |
| 5 | `DAILYBOT_API_KEY` env var | Session-level |
| 6 | `config.json::api_key` (from `dailybot config key=...`) | Persistent global |
| 7 | Login session Bearer token (`credentials.json::token`) | From `dailybot login` |

When `env.json::disabled` is `true`, or `active` is empty/null/unknown, the file is transparently skipped and every resolver behaves as if the file didn't exist.

Two precision notes (CLI >= 3.7.0):

- **Layer 2 holds on the wire, not just in resolution.** When the key comes from `env.json`, the HTTP client sends `X-API-KEY` on the **first** attempt even if a Bearer login session exists — the per-repo key wins even against a server that would have accepted the Bearer, and the global session token is never transmitted to the env.json server. Keys from layers 5–6 keep the historical Bearer-first wire order.
- **Layer 1 vs layer 2 for `agent *` commands:** a keyed `agents.json` profile beats `env.json` only when selected with an explicit `--profile` flag. The same profile resolved implicitly (via `profile.json::profile` or as the `agents.json` default) yields to `env.json`. `dailybot agent profiles --resolve` always shows exactly what will be sent.

---

## Security — non-negotiable rules

`env.json` is one of two files (the other being `credentials.json` in the global config dir) where the CLI stores API keys in plain text. Inside a repo, extra care is required — four independent layers of protection back the "never commit" rule.

### 1. Gitignore is mandatory (and automatic in most setups)

Every Dailybot-aware repo should have this in its root `.gitignore`:

```gitignore
.dailybot/*
!.dailybot/profile.json
```

The broad ignore covers `env.json` automatically. **`env.json` is NEVER excepted** — only `profile.json` is. The Dailybot CLI's own `.gitignore` uses this exact pattern. There is no legitimate reason to un-ignore `env.json` — not with `!.dailybot/env.json`, not with a per-machine dot-file trick, not with `git update-index --assume-unchanged` (that only defers the leak).

### 2. Owner-only permissions (`0o600`)

Every write via `dailybot env` creates the file with mode `0o600` **from the first byte** (`os.open(..., 0o600)` — there is no umask window where the keys sit world-readable), and every load re-chmods it defensively — even if the file was created by an editor or `cp` with a lax umask.

### 3. Fatal refuse-if-tracked guard — fires at the ROOT of every CLI invocation

The root `cli()` callback in `dailybot_cli/main.py` calls `load_repo_env()` on **every command invocation**. That function runs:

```bash
git ls-files --error-unmatch .dailybot/env.json
```

If the file is tracked, `RepoEnvError` fires, `print_error()` writes to stderr, and `SystemExit(1)` aborts the process **before any subcommand runs**. "Tracked" includes **staged-but-uncommitted** — `git ls-files` reads the index, so a stray `git add -f` trips the guard before a commit ever happens. Sample stderr:

```
Error: /path/.dailybot/env.json is tracked by git. This file contains API keys and
must never be committed. Fix with:
  git rm --cached .dailybot/env.json
  # ensure your .gitignore ignores .dailybot/env.json
  git commit -m 'chore: untrack .dailybot/env.json'
The CLI refuses to load env.json while it is tracked.
```

**No auth-consuming command bypasses this** — `dailybot status`, `dailybot user list`, `dailybot form list`, `dailybot agent update`, `dailybot env show`, `dailybot login`, `dailybot upgrade`, `dailybot uninstall`, everything is blocked. There is no silent fallback to global auth — the CLI refuses to operate until `env.json` is untracked. Exactly two carve-outs:

- `dailybot --help` / `dailybot --version` — Click short-circuits them before the callback runs, so the developer can always read instructions.
- The `dailybot hook *` group — it prints the same error to stderr but **still runs and exits 0**, honoring its always-exit-0 harness contract (a tracked env.json must not break every agent session in the repo). Hook commands are local-only and never consume env.json auth, so nothing leaks through this path.

Edge case: if the `git` binary is not on PATH but a `.git` directory exists in an ancestor, the guard cannot verify tracking — it degrades to a **loud warning** instead of a silent pass. Treat that warning as a prompt to check `.gitignore` manually.

### 4. Write-time gitignore warning

`dailybot env add` also runs `git check-ignore` after writing. If `env.json` is **not** covered by any ignore rule, a warning fires on stderr — non-fatal (a brand-new repo might not have a `.gitignore` yet) but very visible:

```
Warning: /path/.dailybot/env.json is NOT gitignored. This file contains API keys
and must never be committed. Add `.dailybot/*` (except `!.dailybot/profile.json`)
to your .gitignore before committing.
```

### If the developer accidentally committed `env.json`

Treat it as a compromise — the world has seen the keys the instant the push landed. Recovery:

1. **Rotate every key in the file immediately** at Dailybot → Settings → API Keys. The old keys must be considered burned.
2. `git rm --cached .dailybot/env.json && git commit -m 'chore: untrack .dailybot/env.json'`
3. Verify `.gitignore` covers `.dailybot/*` (add it if missing) — otherwise the very next `dailybot env add` will re-stage the file.
4. Rewrite `env.json` locally with the freshly rotated keys via `dailybot env add ...`.
5. If the repo has been pushed anywhere (public or private), follow [GitHub's guide to removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) — but do NOT skip step 1. Rotation is what actually contains the exposure; history rewrite is cosmetic and does not undo the leak.

Do NOT try to `git filter-repo` the leaked file out and call it done — assume compromise and rotate first, rewrite history second.

### Quick full audit an agent can run on demand

If the developer asks "is my env.json really safe?", run this end-to-end check:

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ENV_FILE="$ROOT/.dailybot/env.json"

echo "--- 1) Does the file exist? ---"
[ -f "$ENV_FILE" ] && echo "yes: $ENV_FILE" || echo "no (nothing to audit)"

echo "--- 2) Is it gitignored? ---"
(cd "$ROOT" && git check-ignore -v .dailybot/env.json) || echo "NOT IGNORED (fix .gitignore)"

echo "--- 3) Is it accidentally tracked? ---"
(cd "$ROOT" && git ls-files --error-unmatch .dailybot/env.json 2>/dev/null) \
  && echo "TRACKED (SECURITY VIOLATION — rotate keys + git rm --cached)" \
  || echo "not tracked (good)"

echo "--- 4) File permissions ---"
[ -f "$ENV_FILE" ] && stat -c '%a %n' "$ENV_FILE" 2>/dev/null || stat -f '%A %N' "$ENV_FILE"
# Expect 600.

echo "--- 5) CLI resolution ---"
dailybot env show   # masks API keys; confirms the CLI is reading the file
```

Any of 2/3/4 tripping = actionable finding.

---

## Detection pre-flight (when an agent is helping a developer manage keys)

Only run this if the developer's request explicitly touches per-repo auth. Do not preemptively read env.json for every session — it contains secrets and there's no benefit to loading it if you're not being asked about it.

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ENV_FILE="$ROOT/.dailybot/env.json"

if [ -f "$ENV_FILE" ]; then
  echo "REPO_ENV_EXISTS=1"
  # NEVER cat this file — it contains API keys. Use the CLI's show/list
  # subcommands which mask keys automatically:
  dailybot env show 2>&1
else
  echo "REPO_ENV_EXISTS="
fi
```

Rules:

- **Never `cat`, `head`, or otherwise print the raw file** — API keys are inside. Use `dailybot env show` / `dailybot env list` which mask them.
- **Never suggest committing `env.json`** — the CLI will refuse to load it once it's tracked.
- **Never write API keys into `profile.json`** — that's a hard error.
- If the developer asks "what env am I in?", use `dailybot env show` (masked) — do not read the file directly.

---

## Worked examples

### Example 1 — First-time setup for a local dev org

Developer: *"I need to test against my local Dailybot instance for this project without breaking my prod login."*

```bash
# 1. Confirm CLI >= 3.7.0 (env command exists).
dailybot env --help >/dev/null 2>&1 || {
  echo "This feature requires dailybot-cli >= 3.7.0. Run: dailybot upgrade" >&2
}

# 2. Ensure the gitignore covers .dailybot/* (create if needed).
grep -q '^\.dailybot/\*' .gitignore 2>/dev/null || {
  cat >> .gitignore <<'EOF'

# Dailybot per-repo state (env.json contains API keys — never commit it)
.dailybot/*
!.dailybot/profile.json
EOF
}

# 3. Add the local profile. It becomes active automatically because it's the first.
dailybot env add \
  --name local \
  --key sk_local_xxxxxxxx \
  --api-url http://localhost:8000 \
  --app-url http://localhost:8090

# 4. Verify.
dailybot env show
```

Every subsequent `dailybot` command in this repo now talks to `http://localhost:8000` with the local key. In every other repo, the prod login remains untouched.

### Example 2 — Toggling between staging and prod for QA

Developer: *"I want to reproduce a staging bug, then switch back to prod."*

```bash
dailybot env add --name prod    --key sk_prod_xxxx           # first → auto-active
dailybot env add --name staging --key sk_staging_yyyy \
                                --api-url https://staging-api.example.com

# Switch to staging for the bug repro session.
dailybot env use staging

# ... reproduce the bug ...

# Switch back.
dailybot env use prod
```

### Example 3 — Temporarily disabling env.json to test global auth

Developer: *"I want to see what would happen with my global config for a minute, but don't lose my env.json setup."*

```bash
dailybot env off        # env.json ignored, CLI falls through to global auth
# ... test something ...
dailybot env on         # restores the previously active profile
```

`env off` sets `disabled: true` at the top level — the `active` selection is preserved so `env on` restores it instantly.

Verification pattern the developer can run to prove the toggle actually works:

```bash
dailybot env show                # Active env.json Profile: local
dailybot status --auth           # → Authenticated via API key (local org)

dailybot env off
dailybot env show                # env.json is disabled (active would be: local)
dailybot status --auth           # → Authenticated via login (OTP)  (falls back to Bearer)

dailybot env on
dailybot env show                # Active env.json Profile: local  (restored)
dailybot status --auth           # → Authenticated via API key (local org again)
```

If step 2 does not fall back — i.e., the CLI keeps using the env.json profile after `env off` — that's a bug; report it.

### Example 4 — Removing an environment cleanly

```bash
dailybot env remove staging --yes
# If 'staging' was the active profile, active is cleared and the CLI
# falls back to global auth until you run `dailybot env use <name>` again.
```

---

## Interaction with existing auth flows

- **`dailybot login` still works.** It writes to `~/.config/dailybot/credentials.json` (Bearer session). If `env.json` is active for a repo, that key wins over the Bearer for that repo. In other repos (or when `env.json` is disabled/inert), the Bearer takes over normally.
- **`dailybot logout` is unaffected.** It only clears the Bearer session. Your `env.json` remains intact.
- **`dailybot config key=...` still works.** It writes to `~/.config/dailybot/config.json`. `env.json` sits above it in the precedence order.
- **`DAILYBOT_API_KEY` still works.** For CI or one-off overrides. `env.json` beats it inside a repo; outside a repo (or when disabled), the env var wins.
- **Repo `profile.json` is orthogonal.** It still governs the *display name* and `default_metadata` for reports. `env.json` provides *credentials + URLs*. Both can be present.

### env.json key first + transparent alt-credential retry (auto)

When the resolved API key comes from `env.json`, the CLI's HTTP client sends it on the **first** attempt — the global Bearer session never reaches the env.json server. This is what makes the "logged into prod, `cd` into a local-dev repo" case Just Work in one round-trip:

```
                            + client.auth_status()
                            |
                            | Attempt 1: X-API-KEY <env.json local-admin>  -> http://localhost:8000
                            |            200 OK   (prod Bearer never leaves the machine)
                            |
                            + returns local org data (silently)
```

Backing that up, the client automatically retries every user-scoped and agent-scoped call **once** with the alternative credential when the server answers 401 or 403 — in either direction (stale env.json key → Bearer, stale Bearer → API key).

Retry semantics:

- Triggers on **HTTP 401 or 403** (Django/DRF answers 403 for rejected credentials just as often as 401; both are treated as "credential problem, try the other one").
- Fires **at most once per call** with the alternative credential — a double rejection surfaces as a normal auth error.
- **Login-lifecycle endpoints do NOT retry** — `dailybot login`, `dailybot logout`, and the agent-registration challenge always report the truth of what happened (the credential IS what's being negotiated there, or invalidated).
- **`dailybot status --auth` inspects the auth mode after the call** and reports which credential actually succeeded on the wire (`Authenticated via API key` vs `Authenticated via login (OTP)`), so the developer always sees the truth.
- **`dailybot login` inside a repo with an active env.json profile warns first** — login persists the resolved `api_url` into the GLOBAL `~/.config/dailybot/credentials.json`, so the CLI names the profile and the server and suggests `dailybot env off` before proceeding.

Ships with the same CLI floor as `env.json` itself.

---

## Troubleshooting

**"The CLI is not using my env.json."**
1. `dailybot env show` — is it reporting the profile you expect?
2. Look at `disabled`, `active`, and the walk-up path. `env show` prints the resolved file path — is it the one you edited?
3. Are you running with `--profile` / `--api-url` / `--app-url`? Flags win.
4. Did you edit the file directly? Check the JSON — the CLI's `env` commands validate on write, but hand-edits can produce invalid JSON that the loader rejects with a parse warning (printed to stdout, once per process) before falling back to global auth.

**"The CLI refuses to run and complains about tracked env.json."**
Run the fix printed in the error. This is the fatal refuse-if-tracked guard doing its job. (Exception: `dailybot hook *` commands print the error but still run and exit 0 — that is by design, not a hole; see § Security above.)

**"I set `disabled` to `"true"` by hand and the file is still active."**
`disabled` must be a JSON boolean (`true`, no quotes). The CLI warns about the string and treats it as `false` so a typo never silently changes which org you talk to. Run `dailybot env off` instead of hand-editing.

**"I edited env.json by hand and now nothing works."**
`dailybot env show` will surface schema warnings. If unrecoverable, delete the file and re-add profiles via `dailybot env add`.

**"I want the same profile across many repos without duplicating it."**
That's what `~/.config/dailybot/agents.json` (global profiles) is for — see `dailybot agent configure`. `env.json` is intentionally per-repo.

---

## Version compatibility

- Requires **`dailybot-cli >= 3.7.0`**. Older CLIs never look at `.dailybot/env.json` and treat it as harmless clutter.
- The Dailybot agent skill pack targeting this doc requires the same floor.
- If a developer is on an older CLI, offer to upgrade first: `dailybot upgrade` (auto-detects install method).

---

## See also

- [`shared/auth.md`](auth.md) — the general authentication flow (OTP login, API key alternatives, CLI installation).
- [`shared/repo-profile.md`](repo-profile.md) — the sibling file `profile.json` (agent identity, committed).
- [CLI configuration reference](https://github.com/DailybotHQ/cli/blob/main/docs/CONFIGURATION.md#repo-level-env-override-dailybotenvjson) — canonical schema + precedence + security posture.
- [CLI auth-resolution order](https://github.com/DailybotHQ/cli/blob/main/AGENTS.md#14-auth-resolution-order-do-not-break) — the per-field precedence the CLI implements.
- [CLI security posture](https://github.com/DailybotHQ/cli/blob/main/docs/SECURITY.md) — the four-layer protection for `env.json`.
