# Template — `docker/local/{service}/Dockerfile` (reason, don't copy)

Reasoning template with **Node** and **Python** branches. The base image, user,
and dependency install are reasoned per repo; the **agent-tooling block**
(install claude/codex/cursor/gh/dailybot CLIs, source `custom_commands.sh`,
pre-create persistence dirs) is the stable part.

## Shared across both branches (the stable tooling block)

Every Dockerfile, regardless of language:

1. Installs base tools: `sudo git bash-completion nano ssh curl gnupg
   ca-certificates build-essential`.
2. Creates the dev user (or uses the image's) with UID/GID 1000 + passwordless
   sudo — **unless** the base image already ships a suitable non-root user.
3. Installs the **agent CLIs** — always via a **package manager or a verified
   two-step download-then-execute flow**, never by piping a remote installer to
   a shell (see security note below):
   - **GitHub CLI (`gh`)** — via `apt` on Debian/Ubuntu bases (`apt install
     gh` from the GitHub CLI apt repo) or `brew install gh`. Pin the version
     in the Dockerfile when reproducibility matters.
   - **Dailybot CLI** — via `pip install 'dailybot-cli>=3.7.0'` (preferred
     when Python is already in the image), or `brew install
     dailybothq/tap/dailybot`, or the Dailybot skill's own verified installer
     flow documented at
     [`DailybotHQ/agent-skill · shared/auth.md`](https://github.com/DailybotHQ/agent-skill/blob/main/skills/dailybot/shared/auth.md).
   - **Codex CLI** — via `npm install -g @openai/codex` (or the vendor's
     current recommended package-manager path — check the OpenAI docs).
   - **Claude Code** (installed as the dev user) — via `npm install -g
     @anthropic-ai/claude-code`, following the current Anthropic docs.
   - **Cursor CLI** (installed as the dev user) — via the current
     package-manager path documented at
     [cursor.com/docs](https://cursor.com/docs).

> ### Security note — no remote-installer pipes in Dockerfiles
>
> The Dockerfile MUST NOT combine "fetch a remote installer" and "execute it"
> into a single shell pipeline (the POSIX one-line `fetch → pipe → shell`
> pattern, or the equivalent PowerShell `download → invoke-expression`). That
> pattern executes whatever the vendor's server returns at build time with
> **no version pin and no integrity check** — vendor infrastructure changes,
> mirrors, or a compromised CDN silently reshape the image. Prefer, in order:
> 1. **Package managers** (`apt`, `apk`, `dnf`, `brew`, `pip`, `npm`, `cargo`)
>    — they pin versions, verify checksums, and are cacheable/reproducible.
> 2. **A verified two-step flow when a package-manager path does not exist**:
>    first, download the installer to a local file; then, verify its SHA-256
>    against the vendor's published sidecar (or verify a cosign signature);
>    then, execute the verified local file in a separate RUN step.
> 3. **A multi-stage build** that fetches, verifies, and extracts the binary
>    in a build stage, and only copies the verified binary into the runtime
>    stage.
>
> This is a hard requirement for public / OSS images (methodology-spec §5)
> and is what Snyk (rule E005) and Socket (Anomaly/Security alerts) audit
> for. A Dockerfile that fetches-and-executes a remote installer in one
> shell pipeline will fail `npx skills audit` and every mainstream container
> security scanner.
4. `ENV EDITOR=nano VISUAL=nano GIT_EDITOR=nano`.
5. `WORKDIR {workspaceFolder}`.
6. Copies `entrypoint.sh`, strips CRLF, `chmod +x`.
7. Pre-creates `{user-home}/.claude_data .codex_data .cursor_data .gh_data
   .dailybot_data .ssh` owned by the dev user.
8. As the dev user: `git config` defaults + `echo 'source
   {workspaceFolder}/docker/custom_commands.sh' >> ~/.bashrc`, then remove any
   seeded `~/.claude` / `~/.claude.json` (the entrypoint re-seeds from volume).
9. `ENTRYPOINT ["/entrypoint.sh"]`.

> Reason the **package manager** from the lockfile that exists. Node: enable
> Corepack for pnpm/yarn shims if the repo pins `packageManager`; otherwise plain
> npm. Python: poetry / pip-tools / uv as the repo actually uses.

## Node branch

```dockerfile
FROM node:{24.x}-trixie-slim          # reason exact version from .nvmrc / engines / packageManager
# ... base tools (apt) ...
# node image already ships a `node` user (UID 1000); use it OR create dev-user.
# Corepack for pnpm/yarn if the repo pins packageManager:
RUN corepack enable && corepack --version
# gh + dailybot + codex CLIs (system-wide), then USER node/dev-user for claude/cursor.
WORKDIR {/code/js | /app}
# (no app `npm install` in the dev image if you bind-mount the repo; install at runtime)
```

Decision notes (Node):
- **User**: reuse the image's `node` user, or create `dev-user` for parity with
  Python repos — pick one and keep `remoteUser`/volume paths consistent.
- **Native modules**: keep `build-essential` for packages that compile.
- **Static-site / Lighthouse**: add chromium + its deps (see `static-site`
  preset) when the build runs headless Chrome.

## Python branch

```dockerfile
FROM python:{3.x}-slim-trixie         # reason exact version from pyproject / .python-version
# ... base tools (apt) ...
RUN groupadd --gid 1000 dev-user && useradd --uid 1000 ... (sudoers)
# Node 24 too (agent CLIs + any JS tooling), gh, dailybot, codex.
# Install deps from the LOCKFILE in its own cache layer (reproducible):
COPY {requirements/dev.txt | poetry.lock+pyproject.toml} /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-dev.txt   # or poetry install
WORKDIR {/app | /workspace}
```

Decision notes (Python):
- **Multi-stage** when native deps need a build toolchain at build time only
  (api-services builds wheels in a `python-build-stage`, copies them into a slim
  `python-run-stage`). A pure-Python CLI does **not** need multi-stage.
- **Locales**: generate `en_US`/`es_ES`/`pt_PT` if the app formats localized
  output (api-services).
- **Isolated tools**: install aggressive-pin tools (e.g.
  `python-semantic-release`) via `pipx --global` so they don't downgrade the main
  env (cli repo).
- **Lockfile pinning** is mandatory for reproducibility (and doubly so for
  public-OSS — SPEC §5).
```
