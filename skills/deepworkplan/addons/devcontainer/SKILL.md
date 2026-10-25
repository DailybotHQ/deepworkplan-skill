---
name: deepworkplan-addon-devcontainer
description: Optional DeepWorkPlan addon that gives a repository a reproducible dev container through devcontainer-kit (the `dck` command, DailybotHQ/devcontainer-kit pinned at v1.0.1, interface 2) - a vendor-neutral thin integrator that detects the kit with `dck doctor --json`, offers the kit and its tag-pinned `dck-dockerfile` skill, and lets them render the repository's own layout (.devcontainer/devcontainer.json, docker/local/<service>/Dockerfile, docker/local/docker-compose.yaml, dev.sh) from the official runtime image pinned by digest - no shared base image required. Reconciles an existing layout and never clobbers it, keeps loopback ports and agent forwarding, and validates the result with a real build. Opt-in, never required, never a conformance gate.
version: "7.9.0"
documentation_url: https://deepworkplan.com/kit/devcontainer
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"📦","homepage":"https://deepworkplan.com/kit/devcontainer","requires":{"anyBins":["docker","git"]}}}
---

# DeepWorkPlan — Devcontainer Addon

Give the repository a **reproducible, isolated dev container** that any human
or AI agent can open the same way — from a terminal (`bash dev.sh up`), from
VS Code / Cursor ("Reopen in Container"), or with the `devcontainer` CLI.
This is an **opt-in addon**, never required for a repo to be AI-first and
never a conformance gate.

This addon is a **thin integrator** of **devcontainer-kit**
(`https://github.com/DailybotHQ/devcontainer-kit`, MIT, works without DWP).
The Dockerfile template, the render (`dck init`), the pinned images and
tools, the entrypoint, SSH, Herdr registration and the `dck-dockerfile`
skill are the kit's; this addon decides **whether** to offer it, **which
options** fit the repository, and **how to validate** the result. It
carries no copy of the template and no company-specific network, volume or
file name.

| Pin | Value |
|-----|-------|
| Product | `DailybotHQ/devcontainer-kit` |
| Tag | `v1.0.1` (per-repository Dockerfile, no shared base image; host accounts through `[agents] host_profiles` since `v0.3.0`; the antigravity kind, per-developer CLI choice (`[agents] supported`) and non-shared profiles on the agents volume since `v0.3.6`; coding-agents-kit `v0.7.1` and herdr-peers `v0.3.2` baked in since `v0.3.7`; the first stable release, its interface committed to semantic versioning, baking coding-agents-kit, herdr-peers and deepworkplan-vim `v1.0.0`, `v1.0.0`; coding-agents-kit `v1.0.1` baked in, so `@default` stays the container's own account, and a `dck doctor` warning when a shared `codex@default` mixes host and container Codex versions, since `v1.0.1`) |
| Interface | `2` (`dck doctor --json` → `"interface": 2`) |
| Skill | `dck-dockerfile`, installed from the same tag |
| Registry key | `devcontainer` (`.dwp/config.json` → `addons.devcontainer`) |
| Abilities | none (it provides an environment, not a delegation transport) |

## Read these first (all relative inside the skill)

- [`SPEC.md`](SPEC.md) — the normative contract.
- [`templates/INTEGRATION.md`](templates/INTEGRATION.md) — reasoning aid:
  stack → runtime, ports and agents, the Herdr container profile,
  validation.

## When this runs

`onboard` Phase 7b offers it when the repository benefits from an isolated,
reproducible environment (services, a pinned toolchain, agents that should
not touch the host); or on direct invocation. No other flow requires it.

## What the kit renders (one layout, every repository)

```
.devcontainer/devcontainer.json        # opens the same compose service as dev.sh
docker/local/<service>/Dockerfile      # plus its entrypoint and layer scripts
docker/local/docker-compose.yaml
dev.sh                                 # up, down, shell, exec, build, rebuild, herdr
```

The Dockerfile starts **from the official runtime image** (node, python or
debian) pinned by `tag@sha256:digest`. **No shared base image is required**:
the repository owns its Dockerfile, and nothing depends on the kit's GHCR
image. The kit's managed blocks carry a render stamp, so `dck init`
re-renders them and `dck doctor` reports drift; a project section outside
them survives every re-render. An existing `dev.sh` is kept.

The options live in `.devcontainer/dck.toml` (interface 2; `dck init`
migrates an interface-1 file). `dev.sh` is the one entry point
(`bash dev.sh up` builds, starts and registers). `ssh_agent` (default on)
gives git over SSH through the host's agent, so no private key enters the container
unless the developer turns on `[ssh] copy_keys` in their host profile (below).
`[herdr] machine` registers the container as a Herdr machine, and
`[herdr] layout = "standard"` opens it with the App · Editor · Development ·
Agents sidebar (`"none"` skips it). Every image carries herdr-peers.
`[herdr] mesh` (optional, default `true`, Docker Desktop only) lets agents
inside reach the other dck containers; it widens trust between containers,
so say so when you offer it, and `mesh = false` keeps the container on its
own. The agent socket follows the Docker provider: Docker Desktop and
OrbStack share the host agent, a native Linux engine mounts
`$SSH_AUTH_SOCK`, and other runtimes get none in exec sessions (`dck ssh`
and Herdr sessions still forward it). With `ssh_host_config` (default on),
git over SSH with your own `~/.ssh/config` aliases (`git@github.com-work:…`)
works inside: `dck up` and `dck rebuild` copy the aliases for git hosting
services (GitHub, GitLab, Bitbucket, Azure DevOps, Codeberg, sourcehut) with
**public** keys and already-trusted host keys only — no private key is
copied — and only aliases whose key the host agent holds. On a terminal dck
offers `ssh-add` for a missing key (`[Y/n]`, the developer's answer); other
hosts are the developer's opt-in through `[ssh] host_extra` in the host
profile, never the repository's `dck.toml`. `ssh_host_config = false` turns
it off.

### Host accounts inside the container (`host_profiles`, opt-in)

With devcontainer-kit's host profiles a container's agents use the
developer's own `ak` accounts with no login inside — the way git already
works through the host's SSH agent. Both keys live in the developer's
**host** profile (`~/.config/dck/profile.toml`, `[agents]`), never in the
repository's `dck.toml`:

- `host_profiles = true` (default `false`) binds, one by one, each host `ak`
  profile (`$AGENTKIT_PROFILES_DIR/<cli>/<name>`) of the CLIs the
  repository installs (`[agents] clis`) whose profiles are file-portable
  (claude, codex, pi, cline, grok, opencode), and points
  `AGENTKIT_PROFILES_DIR` at them inside; `host_profile_names` (for example
  `["claude@work1", "codex@default"]`) limits the share to the profiles
  listed. A mount is read-write only where that CLI writes (its state,
  sessions, refreshed logins); never the whole agentkit home, never a whole
  CLI directory. Codex `@default` gets the host Codex home when
  `codex@default` is shared. Cursor and Antigravity profiles are never
  shared (they hold absolute host links).
- The container reads credentials from a host-generated env file (`0600`),
  mounted read-only as `AGENTKIT_ENV`, holding only the Claude token of each
  shared Claude profile (`CLAUDE_CODE_OAUTH_TOKEN` for `claude@default`,
  `CLAUDE_CODE_OAUTH_TOKEN_<SUFFIX>` for `claude@<name>`) and the exact names
  listed in `host_env_keys` (default `[]`, no prefixes or wildcards). With
  `host_profiles` off nothing is copied. Claude authenticates through the
  profile's token, Codex through its auth file. Values never appear in
  compose, logs or `dck doctor`.
- Folder trust for the app path is written in the container's homes and in
  shared profiles. Claude's bypass-permissions acknowledgement is written by
  the kit only in the container's own homes with autonomy on — never in a
  shared host profile, and never with `AGENTKIT_PERMISSIONS=ask`. A shared
  host profile needs that acknowledgement once from the developer on the
  host (`ak claude @<name>`, accept, exit); no agent sends keys for it
  (`../../guide/orchestration-at-scale.md` §16.5).
- A shared Codex `auth.json` is read-write: **one active writer per
  account** — do not run the same Codex account in two places at once.

**Across restarts (`v0.3.1`).** A second `dck up` keeps the shared tokens:
the env file is bound through its per-project directory and rewritten
atomically, so a running container sees the new file without
`--recreate`. A removed `state` volume no longer breaks `dck ssh` or the
Herdr machine: the container's host key is read from the container itself
and re-pinned, with a note. Logins kept on the `state` volume (`gh`, the
CLIs' own homes when not shared) survive `bash dev.sh rebuild`, but a fresh
`state` volume needs one `gh auth login` inside — the developer's step, never
an agent's.

Offer it only when the developer wants container lanes on host accounts
(`../../guide/orchestration-at-scale.md` §16.3); it widens what a container
can use, so say which profiles it shares and that a process in the container
can use those accounts and change their login files (the read-write
mounts). Setting it is the
developer's decision in their host profile — this addon describes it, never
sets it.

**Host SSH keys (`[ssh] copy_keys`, `v0.3.2`, opt-in).** Some tools read
only key files and ignore the forwarded agent (`gh auth login` offers to
generate a new key). The developer can turn on `[ssh] copy_keys = true` in
their **host** profile (`dck setup` asks once, default no; a repository's
`dck.toml` cannot set it). While it is on, `dck up` binds the whole host
`~/.ssh` read-only at `~/.ssh_host`, and each container start copies its
`id_*` keys into the container's `~/.ssh` on the state volume (`0600`, `.pub`
`0644`, kept in step with the host); agent forwarding is unchanged and
turning it off removes the copies. Name the cost when it comes up: every
file of the host `~/.ssh` is readable inside, and private keys rest in the
state volume. Never set it, never answer that `dck setup` question.

**One compose project, several services (`[compose] state_volume`,
`v0.3.2`).** The state volume (sshd host key, `~/.ssh`, `gh` auth, Herdr
client state, history) is named `state` by default. When the repository's
service shares a compose project (`COMPOSE_PROJECT_NAME`) with others, give
it its own name — `state_volume` in `dck.toml` or
`dck init --state-volume NAME` — or every service mounts the same
`<project>_state` volume; `dck doctor` flags it.

**Rebuild and start (`v0.3.2`).** `bash dev.sh rebuild`, `dck start` and
`dck restart` re-run `dck up`'s post-start steps: the Herdr machine is
registered again (host key re-pinned), the mesh and host-catalog mirror are
pushed, the layout is created. A container rebuilt from scratch reaches the
host and its peers with no hand `dck herdr mesh`. The image also carries
coding-agents-kit's skills (`agentkit`, `agentkit-setup`,
`agentkit-orchestrate`), linked into every agent at each start.

**Codex panes inside a container (`v0.3.3`).** A Codex lane's commands run
from a per-profile server, so herdr-peers cannot probe its own machine and
needs `HERDR_PEERS_SELF` (the container's machine id as saved in the host's
Herdr catalog) for asks to the host or another machine. Since `v0.3.3` dck
records that id on the state volume (`dck up`, after every `dck herdr add`,
and `dck herdr mesh`) and the login profile exports it, so no lane sets it
by hand; `dck doctor` shows both ids (`herdr self`) and flags a mismatch.
With an older kit, the lead's brief names the value and the lane sets it.
Since `v0.3.4` the entrypoint also turns off Codex's startup update check
and its app-server daemon auto-start in the container's own Codex configs
(the kit pins every CLI version), never in the host's Codex home or a
host-shared profile, keeping any value the developer set; Codex's hook
trust stays the developer's consent.
The image also carries herdr-peers `v1.0.0` (notices and lead records included), whose state is kept per Herdr
server, so a checkout bind-mounted into the container no longer shares the
host's state.

**Shared compose stacks (`v0.3.3`, additive).** When the repository is one
service of a product that runs as one compose project across several
repositories (an API, a web app, workers, a database), reason these keys
from the real stack — the kit's `docs/shared-stack.md` is the reference —
instead of hand-editing what dck renders:

- `[compose] project` (the same value in every repository of the stack),
  one `state_volume` per service, `[compose] networks` (external) and
  `[compose] volumes` with the top-level `user:volumes` / `user:networks`
  sub-blocks for the other services' data.
- **The user block** — `# >>> user:<svc> >>>` … `# <<< user:<svc> <<<`
  inside the dck service, kept verbatim: plain keys for what dck does not
  render (`depends_on`, `healthcheck`), `x-dck-merge:` for keys it does
  (lists appended, maps merged with the user's entry winning, `command` and
  `entrypoint` replaced). Repository additions go there, never inside dck's
  own markers; a file with some of dck's markers but not all is refused.
- **Port strings**: `ssh_port` and `ports` accept compose expressions such
  as `"${API_HOST_PORT:-8000}:8000"`; they stay loopback-prefixed unless the
  string names a host IP, which only the repository's own config may do.
- `[build] context` / `[build] dockerfile` for a Dockerfile shared by several
  services, `dev_sh = false` (`dck init --no-dev-sh`) for a repository that
  keeps its own `dev.sh`, and `[agents] presets` for the ak alias presets.
- `[agents] node_first = true` puts the agents' own Node (kept under
  `/opt/dck/node` since `v0.3.3`, never over the image's) first on PATH; off
  by default, set only when the repository's tooling needs it.

A repository that sets none of these renders byte-identically to `v0.3.2`.

**Workspace satellites (`v0.3.5`).** A repository whose scripts start a
second instance of its dev service (`<svc>satellite`, in its own compose
project with its own ports) starts it through dck, not plain
`docker compose`, so the satellite gets every host step the main service
gets (the authorized dck key, `[ssh] copy_keys`, host-profile accounts and
`default_profile`, the git identity, `HERDR_PEERS_SELF`, its own Herdr
machine `dck-<project>-<service>` on the mesh, the Codex/Claude container
config):

```
dck --project <P> --compose-file <main> --compose-file <overlay> --service <svc>satellite up [--seed-state-from <VOLUME>] [--label "<label>"]
dck --project <P> --compose-file <main> --compose-file <overlay> --service <svc>satellite down
```

Define the satellite after `# <<< dck:service <<<` in the main compose file
(`extends: <svc>`), or in an overlay file, where `extends` must name the
file (`extends: {file: docker-compose.yaml, service: <svc>}`); give it a
`profiles: [satellite]` entry and its own ports and volumes, never the main
state volume. `--seed-state-from` copies only the login state (`gh`,
Dailybot) once into an empty satellite state volume — never history, keys
or Herdr state. `down` removes only that service, its Herdr machine and
its SSH alias. The recipe is the kit's `docs/shared-stack.md`
(workspace satellites). Since `v0.3.5` a workspace inside a renamed user's
home (`user` other than `dev`, `workspace` under `/home/<user>`) also builds.

**Default account inside (`[agents] default_profile`, host profile).**
`{ claude = "@work3" }` exports `AGENTKIT_DEFAULT_PROFILE_<CLI>` into the
container when that profile is shared, so a bare `ak claude` inside uses
that account (coding-agents-kit `v0.5.2` and later); a macOS `@default` Claude login
lives in the Keychain and cannot be shared. It is the developer's host
profile key — describe it, never set it. Since `v0.3.4`, when it is set
and shared, the container's login shells also export `CLAUDE_CONFIG_DIR` /
`CODEX_HOME` for that profile, so a pane Herdr restores with a plain
`claude --resume` or `codex resume` opens on that account instead of a
login screen (a value ak sets wins). `dev.sh` also prints dck's refusals
(exit 5: a configuration that needs `--trust`, or markers to fix) on stdout. Since `v0.3.3` the host's git
identity (name, email, SSH signing key reference) is pushed into the
container at every start, with no `~/.gitconfig` mount.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`:

- **Before consent: read-only.** `command -v dck docker`, `dck doctor --json`,
  and reading the repository's existing `.devcontainer/`, `docker/` and
  `dev.sh` files.
- **Writes (only after explicit acceptance):** the kit install (pinned tagged
  clone + `install.sh`), the repo-local `dck-dockerfile` skill (tag-pinned
  `skills add`, recorded in `skills-lock.json`), the render in the
  repository — which shows a plan and diffs and changes an existing file
  only with consent, after a timestamped backup — the `addons.devcontainer`
  registry entry, and the validation record.
- **It MUST NOT:** pass `dck init --yes` without the developer's explicit
  acceptance of the shown diff; add `privileged`, `cap_add`, host namespaces,
  the Docker socket or host bind mounts beyond the workspace and the SSH
  agent socket (never host `~/.ssh`, `~/.gitconfig` or `${HOME}`; the kit's
  read-only `~/.ssh_host` bind exists only under the developer's own
  `[ssh] copy_keys`); publish a port beyond loopback unless the repository's own
  config says so; pass `--trust` on the developer's behalf; copy a private
  key into an image or container, or set `[ssh] copy_keys` for the developer; answer dck's `ssh-add` prompt or set
  `[ssh] host_extra` in the developer's host profile on their behalf; set
  `[agents] host_profiles`, `host_env_keys` or `default_profile` there for them, or print a
  shared credential's value; run
  `dck herdr add` (it edits
  `~/.ssh/config`) without its own explicit approval; install anything on
  the host beyond the kit and its skill; or write any secret value (`.env`
  files are `0600` and stay gitignored).

## The flow

### Step 0 — Detect (read-only)

`command -v dck` → `dck doctor --json`: `interface` must be `2` (otherwise one
warning and "not available"; a `1` means a kit older than `v0.2.0` — offer the
upgrade; `version` `0.2.0` is unsupported since `v0.2.1`, its security
release — offer the upgrade too); read `runtime` (Docker/OrbStack/colima and Compose), `repo` (config
validity) and `drift`. Note an existing `.devcontainer/`, `docker/` or
`dev.sh` — it will be **reconciled**, never replaced silently.

### Step 1 — Offer (never impose)

Explain what it adds (one reproducible environment the developer and every
agent share, loopback-only ports, agent forwarding instead of private-key
copies, optional coding agents and DeepWorkPlan Vim inside) and what it
costs (Docker, an image build). Say that `ssh_host_config` is on by default:
the developer's git-host aliases, their public keys and trusted host keys
are copied in. Declining is complete.

### Step 2 — Install the kit and its skill (pinned; point-don't-run by default)

```
git clone --branch v1.0.1 https://github.com/DailybotHQ/devcontainer-kit
./devcontainer-kit/install.sh
npx --yes skills add https://github.com/DailybotHQ/devcontainer-kit/tree/v1.0.1 --skill dck-dockerfile -y
```

Before running the installer, check the tag and the release's `SHA256SUMS`
(pinned digest, at least one file verified) as
[`../machine-installs.md`](../machine-installs.md) shows.

The third line installs the `dck-dockerfile` skill into the repository
(repo-local, recorded in `skills-lock.json`), so "install the kit, ask the
agent" works in any coding agent. Run them yourself only interactively and
with explicit acceptance; re-detect afterwards.

### Step 3 — Render the layout (reconcile, never clobber)

Hand the work to the `dck-dockerfile` skill: it detects the service name,
runtime, ports, the coding-agent CLIs to install (none unless named) and
extras such as chromium, shows them once for confirmation, renders through
`dck init` with the kit's pins, and never edits an existing file without
showing the diff and getting approval. Without the skill, reason the same
options (`templates/INTEGRATION.md`) and run `dck init --dry-run …` first,
then `dck init …` after acceptance.

### Step 4 — Record and validate

`python3 ../../shared/config.py enable devcontainer --version v1.0.1 --repo <repo>`,
then validate what was rendered:

- `dck doctor --json` — interface 2, repo config valid, no drift;
- a **real** `docker build` (the skill runs it; a failed build is a failed
  run, never a success), then `bash dev.sh up`;
- inside the container: `ak doctor --json` reports `permissions: auto`
  when agents are installed (`ask` when the documented opt-out is set —
  that is the expected result, never a failure to "fix"), `nvim --headless +qa` exits 0 when the editor
  is, and the repository's real test command runs.

Every result is recorded; none blocks a flow.

**Autonomy inside the container.** coding-agents-kit launches agents in
autonomy by default, which is what a disposable container is for: the
rendered compose sets nothing for permissions and carries a commented
`AGENTKIT_PERMISSIONS=ask` line as the documented opt-out.

**Plan gates in the container (F-21).** When the repository's real gates
run inside the container, a plan declares `dck` in
`scope.allowed_command_classes` and writes each gate check as
`dck exec <service> -- <command>` (a compound command: `dck exec <service> -- bash -c '…'`).
A plan that recorded `dck exec -- <command>` (no service) is changed
through an explicit `refine`, never migrated silently.
`ledger.py gate` executes the wrapper itself, so the evidence stays
`observed`; `validate-contract` refuses a check whose wrapper is not
declared. Without the container the methodology is unchanged — the same
plan simply declares the host command instead.

## Failure-mode guardrails

- **Never required, never blocking.** No Docker, no kit, an unknown
  interface, a declined diff, a failed build: record and continue on the
  host.
- **Reconcile, don't clobber.** Only consented, backed-up render changes
  touch existing files; nothing outside the kit's managed blocks moves.
- **Vendor-neutral.** No company network, volume, CLI or profile file is a
  requirement; the Dailybot CLI layer appears only when the `dailybot` addon
  asks for it.

## Validation checklist (component 4 — mirrored from SPEC §8)

1. `SKILL.md`, `SPEC.md`, `addon.json`, `templates/INTEGRATION.md` exist; the
   descriptor pins `DailybotHQ/devcontainer-kit` `v1.0.1`, interface 2; no
   template, Dockerfile, compose file, entrypoint or `dev.sh` copy ships here.
2. `dck doctor --json` reports interface 2, a valid repo config and no drift.
3. Existing files were changed only through accepted render diffs, each
   with a backup.
4. Ports bind loopback; no privileged options; no host `~/.ssh`,
   `~/.gitconfig` or `${HOME}` mount proposed by the addon (the kit's
   read-only `~/.ssh_host` bind exists only under the developer's own
   `[ssh] copy_keys`); no key material in the image.
5. The image builds for real, and the repository's real test command runs
   inside the container (or the failure is recorded).
