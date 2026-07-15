# Dailybot Authentication

This file is shared across all Dailybot skills. Every skill references it for
auth setup before performing its primary action.

Run these checks in order. Stop at the first failure. Present **one clear
action** to the developer at a time during interactive login — never ask
multiple questions at once.

---

## 1. Check Dailybot CLI is installed

```bash
command -v dailybot
```

If `dailybot` is found, verify it runs:

```bash
dailybot --version 2>&1 || dailybot status --auth 2>&1
```

### If the CLI is not installed — confirm, then run the universal installer

Installing software on the developer's machine is a security-relevant action.
The first time you need to install the CLI in a session, **show the proposed
command and proceed only after explicit confirmation**. Do not re-prompt for
later invocations in the same session — once the developer has confirmed,
treat that as session-wide consent.

> [!NOTE]
> The Dailybot CLI ships **two installer entry points** that pair with
> SHA-256 sidecar files. Pick the one that matches the developer's shell:
> - **`install.sh`** — Linux, macOS, WSL2, Git Bash, Docker, CI. Auto-detects
>   the OS internally and routes to `brew install dailybothq/tap/dailybot`
>   on macOS, the prebuilt PyInstaller binary on Linux x86_64, or
>   `pipx` / `uv tool` / `pip --user` everywhere else.
> - **`install.ps1`** — only for **native Windows PowerShell** when WSL2 and
>   Git Bash are unavailable. Wraps `pipx` / `uv tool` / `pip --user` and
>   requires Python 3.10+ on PATH. There is no native Windows `.exe`.
>
> If the developer is on Windows but has WSL2 or Git Bash, prefer
> `install.sh` — it has broader testing coverage.

> [!NOTE]
> **Installing a specific version.** Both installers default to the latest
> release but accept a version pin (the skill-pack baseline is **`dailybot-cli >= 3.7.0`**):
> - `install.sh` — set `DAILYBOT_VERSION=<version>` in the environment, or
>   pass `bash -s -- --version <version>`. Example (drop it into the verified
>   snippet below, right before `bash /tmp/install.sh`):
>   `DAILYBOT_VERSION=<version> bash /tmp/install.sh`.
> - `install.ps1` — set `$env:DAILYBOT_VERSION = '<version>'` before running
>   (piping to `iex` cannot forward arguments).
> - Both scripts validate the value before use, so a malformed version aborts
>   the install rather than being interpolated into a command.
>
> When the developer already has Python, `pip install dailybot-cli==<version>`
> is the simplest pin and works on every release. See
> [`../SKILL.md` § Pinning a specific version](../SKILL.md#pinning-a-specific-version).

#### curl flags: always `-fsSL`

Every command in this skill fetches over HTTPS with `curl -fsSL`:

| Flag | Why |
|------|-----|
| `-f` | **Fail on HTTP errors.** Without it, a `404`/`500` response body is written to stdout **with exit status `0`** — and in a pipe, `bash` executes that error page. With `-f`, curl emits nothing and exits non-zero. |
| `-s` | Silent — no progress meter cluttering agent output. |
| `-S` | But still show the error message on stderr when it does fail. |
| `-L` | Follow redirects (`cli.dailybot.com` redirects to the CDN origin). |

#### Why an agent must never pipe the installer straight into bash

A `curl … | bash` one-liner is what a **human** types and watches. An agent runs
unattended, where two failure modes are invisible:

1. **Partial execution.** The pipeline *streams* — bash starts executing before the
   download finishes, so a connection truncated mid-transfer runs **half a script**.
   Neither `-f` nor `set -o pipefail` prevents this; they only change the exit status
   *after the fact*.
2. **Silent no-op.** In a shell without `pipefail` (Docker's default `sh -c`, most CI
   `run:` steps), the pipeline's exit status is **bash's**, not curl's. A failing curl
   writes nothing to stdout, bash reads an empty script and exits `0` — the step
   "succeeds" with **nothing installed**, surfacing later as `command not found`.

Both disappear when you download the file, verify it, and *then* execute it — which is
what the primary path below does. Use it for every automated context (agents, CI,
Dockerfiles, provisioning scripts).

#### Primary path: defense-in-depth verified install (Linux, macOS, WSL2, Git Bash, Docker, CI)

Show the developer this prompt the first time:

> "I'd like to install the Dailybot CLI. The command I'll run is:
>
> ```bash
> curl -fsSL https://cli.dailybot.com/install.sh                              -o /tmp/install.sh
> curl -fsSL https://raw.githubusercontent.com/DailybotHQ/cli/main/install.sh -o /tmp/install.sh.gh
> diff -q /tmp/install.sh /tmp/install.sh.gh || { echo "Install script on Cloudflare CDN does not match the GitHub source — refusing to install." >&2; exit 1; }
> curl -fsSL https://cli.dailybot.com/install.sh.sha256 -o /tmp/install.sh.sha256
> ( cd /tmp && shasum -a 256 -c install.sh.sha256 ) || exit 1
> bash /tmp/install.sh
> ```
>
> The script auto-detects your OS and uses Homebrew on macOS, the prebuilt
> binary on Linux, or pipx/uv/pip elsewhere. To uninstall or upgrade later,
> the CLI itself owns those workflows (`dailybot upgrade`). **Should I
> proceed?** (yes / no)"

The flow has **three independent integrity checks** before the script
executes — any one of them aborts the install:

1. **Cross-origin diff.** The script is fetched twice — once from
   `cli.dailybot.com` (Cloudflare CDN) and once from
   `raw.githubusercontent.com/DailybotHQ/cli/main/install.sh` (GitHub's
   public-source endpoint). They must be byte-identical. A coordinated
   compromise that flips both Cloudflare AND GitHub's raw output for the
   same file would be required to defeat this; either alone is caught.
2. **SHA-256 sidecar match.** The `.sha256` companion file (also served
   by `cli.dailybot.com`, regenerated on every CLI release by
   `sync-installer-checksums.yml`) must match the script's actual hash.
   This catches CDN cache corruption and stale-deploy scenarios.
3. **(Optional) Cosign signature verification.** If `cosign` is on PATH
   AND the CLI repo has published `install.sh.sig` + `install.sh.cert`
   (signed by `DailybotHQ/cli` GitHub Actions OIDC, recorded in the
   public Sigstore transparency log), the agent should also run:
   ```bash
   if command -v cosign >/dev/null 2>&1 && curl -fsI https://cli.dailybot.com/install.sh.sig >/dev/null 2>&1; then
     curl -fsSL https://cli.dailybot.com/install.sh.sig  -o /tmp/install.sh.sig
     curl -fsSL https://cli.dailybot.com/install.sh.cert -o /tmp/install.sh.cert
     cosign verify-blob \
       --certificate-identity-regexp 'https://github.com/DailybotHQ/cli/.*' \
       --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
       --signature /tmp/install.sh.sig \
       --certificate /tmp/install.sh.cert \
       /tmp/install.sh || exit 1
   fi
   ```
   This binds the script to GitHub's OIDC identity, anchored in the
   transparency log. Until the CLI repo publishes `.sig`/`.cert` files
   the step is a no-op (the `curl -fsI` probe falls through), so the
   agent never errors on it being absent.

If any check fails, **abort** and warn the developer — never fall back
silently. If `install.sh.sha256` itself returns non-200 (rare CDN
incident), warn the developer and offer two choices: (a) re-fetch later,
or (b) skip CLI install and use the HTTP API path below. Do not run the
script unverified.

> **Threat-model rationale and operational controls** (HSTS preload,
> Certificate Transparency monitoring, the public Sigstore log) are
> documented in [`SECURITY.md`](../../../SECURITY.md) under
> *"Supply-chain integrity for the CLI installer"*.

#### Native Windows PowerShell (only when WSL2 / Git Bash unavailable)

```powershell
$tmp = "$env:TEMP\dailybot-install"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
Invoke-WebRequest "https://cli.dailybot.com/install.ps1"        -OutFile "$tmp\install.ps1"
Invoke-WebRequest "https://cli.dailybot.com/install.ps1.sha256" -OutFile "$tmp\install.ps1.sha256"
$expected = (Get-Content "$tmp\install.ps1.sha256").Split(" ")[0]
$actual   = (Get-FileHash "$tmp\install.ps1" -Algorithm SHA256).Hash.ToLower()
if ($expected -ne $actual) { throw "SHA-256 mismatch — refusing to run install.ps1" }
& "$tmp\install.ps1"
```

`install.ps1` requires Python 3.10+ on PATH (it shells out to
`pipx` / `uv tool` / `pip --user`). If the developer is on Windows + WSL2
or Git Bash, the bash path above is preferred — broader test coverage and
no Python prerequisite.

#### Manual control (developer prefers their own package manager)

If the developer would rather install via their own toolchain instead of the
script, all three produce the same `dailybot` binary:

- macOS: `brew install dailybothq/tap/dailybot`
- Cross-platform Python (recommended for raw control):
  `pipx install dailybot-cli` or `uv tool install dailybot-cli`
- Last resort: `pip install --user dailybot-cli`

Use these when the developer says "I'd rather use brew/pipx" or when running
in an environment that already has one of them set up. Don't surface them as
the default — the universal script covers more cases and gets the same
result. Do **not** `pip install dailybot-cli` against the system Python
without explicit user consent; the installer scripts already pick the right
isolated path automatically.

#### Skipping consent prompts (CI / Docker / power users)

If `DAILYBOT_AUTO_YES=1` is set in the environment, treat install consent as
already given — run the verified install command directly without the
interactive prompt. The SHA-256 check still runs and still aborts on
mismatch. **`DAILYBOT_AUTO_YES` does NOT skip email confirmations** — those
are mandatory regardless.

After any install attempt, re-check:

```bash
command -v dailybot
```

If `dailybot` is not on PATH after a successful install, surface the likely
cause to the developer and stop — do not loop on retries:

- The shell may not have reloaded PATH (open a new terminal).
- On Linux, the user-site bin directory (`~/.local/bin`) may not be on PATH.
- pipx/uv shims may not yet be linked.

#### Upgrading later

The skill does **not** own upgrade logic. The CLI ships its own
`dailybot upgrade` command (since v1.4.0) that auto-detects how the CLI
was installed and either runs the right upgrade in a subprocess
(`pipx`/`uv`/`pip`) or prints the exact command for installs the CLI
shouldn't drive (Homebrew, prebuilt binary, editable). Tell the developer:

> "To upgrade the Dailybot CLI later, run `dailybot upgrade`. To check
> whether you're on the latest version, run `dailybot version --check`."

That's the entire upgrade story. Don't pin a version anywhere in the skill,
don't reimplement upgrade detection, don't suggest re-running the installer
to get a newer version.

### If the CLI still cannot be installed

Stop trying installers. Briefly explain the limitation, then use the **HTTP
API** path with `DAILYBOT_API_KEY` per
[`http-fallback.md`](http-fallback.md). Ask the developer to create an API
key at Dailybot → Settings → API Keys and export it:

```bash
export DAILYBOT_API_KEY="<their-key>"
```

Sandboxed environments, CI, or minimal containers may never get a working
CLI — HTTP fallback is expected there.

---

## 2. Check authentication

```bash
dailybot status --auth 2>&1
```

If already authenticated — skip to "3. Check agent profile."

If not authenticated, guide the developer through login **one step at a
time**. Most developers already belong to a Dailybot organization through
their team — always start with login, not registration.

The CLI checks credentials in this order: agent profile → `DAILYBOT_API_KEY`
env var → stored key (`dailybot config key=...`) → login session.

### OTP login flow

**Start with only this question:**

> "To connect Dailybot, I need to log in with your account.
>
> **What email address do you use for Dailybot?**
>
> (If you'd rather do it yourself, run `dailybot login` in your terminal and
> let me know when you're done.)"

If they prefer to handle it themselves — wait for confirmation, verify with
`dailybot status --auth`, continue.

If they provide their email, proceed one step at a time:

1. `dailybot login --email=<their-email>`
2. Ask: "Check your email for a verification code from Dailybot. What's the code?"
3. `dailybot login --email=<their-email> --code=<their-code>`
4. If output lists multiple organizations, show the list and ask them to pick one
5. If needed: `dailybot login --email=<their-email> --code=<their-code> --org=<selected-uuid>`
6. Verify: `dailybot status --auth`

### API key alternative

If the developer already has an API key, they can store it instead:

```bash
dailybot config key=<their-api-key>
```

This persists the key on disk — no env var or login session needed afterward.

### Self-registration (only when explicitly requested)

**Only if login fails and they explicitly say they don't have an account** —
offer standalone registration:

> "No problem — I can register a new Dailybot organization right from here.
> What's a name for your organization?"

1. Ask for an org name and optionally a contact email
2. `dailybot agent register --org-name "<org_name>" --agent-name "<agent_tool>"`
   Or with email: `dailybot agent register --org-name "<org_name>" --agent-name "<agent_tool>" --email <their-email>`
3. The command creates an org, generates an API key, and saves an agent profile automatically
4. Output includes a **claim URL** — tell the developer: *"Share this with your team admin to connect Dailybot to Slack, Teams, Discord, or Google Chat. It expires in 30 days."*
5. Verify: `dailybot status --auth`

**Never proactively suggest `dailybot agent register`.** Only offer it if the
developer clearly states they have no existing account.

### Auth rules

- Never store the developer's email, verification code, or API key in any file you create
- If login fails, suggest they run `dailybot login` manually in their terminal
- If auth seems corrupted, suggest `dailybot logout` then re-login
- If they decline to authenticate now, skip the current skill entirely
- Auth issues must **never** block your primary work

---

## 3. Check agent profile

```bash
dailybot agent profiles 2>&1
```

If a default profile exists — note the name. You can omit `--name` on
subsequent CLI commands.

> **Repo profile takes precedence over the global default profile.** If
> the repo ships a `.dailybot/profile.json` with a `name` field, that
> name wins over whatever the global default is — and you must omit
> `--name` regardless of what the global default is. Same for
> `default_metadata` keys. Full rules:
> [`shared/repo-profile.md`](repo-profile.md).

If no profile exists and authentication succeeded, create one automatically.
This is metadata only (no install, no network call beyond the CLI command),
so no separate confirmation is needed:

```bash
dailybot agent configure --name "<agent_tool>"
```

Briefly confirm:

> "Dailybot is ready. Your agent profile is set as **<agent_tool>**."

---

## After Authentication

Once authenticated via CLI login, the CLI handles credentials automatically.
No `DAILYBOT_API_KEY` is needed for CLI commands. HTTP fallback calls still
require an API key — ask the user to generate one at
Dailybot → Settings → API Keys.

---

## 4. Auth model — unified Bearer-first priority everywhere

**All endpoints use the same auth priority: Bearer token first, API key
second** (unified in CLI 3.5.1). There is no longer a split where agent
endpoints preferred API key and user endpoints preferred Bearer — the CLI
now behaves consistently everywhere. The server accepts both credentials on
every `/v1/` endpoint, so the two paths are functionally identical.

One deliberate exception (CLI >= 3.7.0): when the API key resolves from a
repo's `.dailybot/env.json` active profile, the client sends `X-API-KEY`
**first** — the per-repo key must beat the global Bearer session even against
a server that would accept the Bearer, and the session token must never be
transmitted to the env.json server. The 401/403 alt-credential retry covers
the reverse direction. See [`env-json.md`](env-json.md).

| Scope | Auth priority | Used by |
|-------|--------------------------------|---------|
| **All endpoints** | Bearer preferred → API key fallback | Every command: `agent update`, `form submit`, `kudos`, `chat send`, `ask`, etc. |
| **Login lifecycle** | OTP / Bearer only | `dailybot login`, `dailybot logout` (revokes the session token) |

### Per-repo API key override (`.dailybot/env.json`) — CLI >= 3.7.0

Since `dailybot-cli >= 3.7.0`, the CLI also honours an **opt-in, gitignored**
per-repo file at `<repo>/.dailybot/env.json` that carries API keys + optional
URL overrides for one or more environments. When present with an *active*
profile, it sits **just below** explicit `--profile` / `--api-url` flags in
the auth-resolution order — above `agents.json`, above `DAILYBOT_API_KEY`,
above `config.json`, above the login Bearer.

If the developer asks about "per-repo API keys", "staging vs prod",
"different orgs per project", or wants to override auth without touching
env vars, route them to [`shared/env-json.md`](env-json.md) — it has the
full schema, CLI commands (`dailybot env add / use / show / list / remove /
off / on`), security posture, and worked examples.

`env.json` is orthogonal to `profile.json`:

- `profile.json` = identity (tracked in git, team-shared).
- `env.json` = auth context (gitignored, per-developer).

Neither field overlaps. Both can be present.

Both credentials can coexist — the CLI stores them separately, and a developer
can hold an API key and a Bearer session at the same time.

### Automatic fallback on 401 or 403

When the primary credential is rejected (HTTP **401 or 403**), the CLI
automatically retries once with the alternative credential if available.
This is bidirectional:

- **Bearer expired** → retries with API key
- **API key stale/revoked** → retries with Bearer session

Both `_agent_request()` (agent-scoped endpoints) and `_request()` (all
user-scoped endpoints — `auth_status`, `checkin`, `form`, `kudos`, `chat`,
`ask`, `user`, `team`, ...) implement identical retry semantics. Login-
lifecycle endpoints (`request_code`, `verify_code`, `logout`, agent
registration) never retry because the credential IS the thing being
negotiated or invalidated.

The retry covers three real-world cases at zero UX cost:

1. **`env.json` active + stale Bearer.** Prod OTP session on disk, `cd` into
   a repo whose `env.json` points at `http://localhost:8000` — the local
   API rejects the Bearer (403), the retry uses the `env.json` API key,
   the command succeeds. `dailybot status --auth` then reports
   `Authenticated via API key` (not `login (OTP)`) — the report reflects
   what actually worked, not what was tried first.
2. **Bearer expired** in normal single-org use → falls back to a locally
   configured API key without a login prompt.
3. **API key revoked** while a valid login session exists → falls back to
   the Bearer.

Retrying on **403** in addition to 401 is required because Django/DRF
frequently returns 403 for rejected credentials (see
[DRF authentication docs](https://www.django-rest-framework.org/api-guide/authentication/#unauthorized-and-forbidden-responses)).
Relying on 401 alone leaves the local-Django + `env.json` case broken.

> **Parity.** All commands — user-scoped (`checkin`, `form`, `kudos`, `user`),
> agent-scoped (`agent update`, `agent health`), and the AI chat (`ask`) —
> accept an org API key **or** a Bearer login session. Only
> `dailybot logout` is Bearer-only.

### Checking session status

```bash
dailybot status --auth 2>&1
```

The output shows both the API key status and the Bearer session status. If
neither is present, guide the developer through `dailybot login` (Section 2) or
ask them to set `DAILYBOT_API_KEY`.

### Config directory override

The `DAILYBOT_CONFIG_DIR` environment variable overrides where all credential
and config files are stored (default: `~/.config/dailybot/`):

```bash
export DAILYBOT_CONFIG_DIR=/tmp/my-sandbox-config
dailybot login --email me@example.com
```

This is useful for development sandboxes, CI environments, or testing
scenarios with isolated config directories. The directory is created
automatically if it does not exist.

### Commands need *some* credential

Every authenticated command works with **either** a login session or an API
key. Only `dailybot logout` requires a Bearer session (it revokes the session
token itself). If neither credential is present, the CLI exits with a clear
error suggesting `dailybot login` or setting `DAILYBOT_API_KEY`.
