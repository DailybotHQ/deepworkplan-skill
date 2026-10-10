---
name: deepworkplan-addon-devcontainer
description: Optional DeepWorkPlan addon that gives a repository a reproducible dev container through devcontainer-kit (the `dck` command, DailybotHQ/devcontainer-kit pinned at v0.2.2, interface 2) - a vendor-neutral thin integrator that detects the kit with `dck doctor --json`, offers the kit and its tag-pinned `dck-dockerfile` skill, and lets them render the repository's own layout (.devcontainer/devcontainer.json, docker/local/<service>/Dockerfile, docker/local/docker-compose.yaml, dev.sh) from the official runtime image pinned by digest - no shared base image required. Reconciles an existing layout and never clobbers it, keeps loopback ports and agent forwarding, and validates the result with a real build. Opt-in, never required, never a conformance gate.
version: "7.1.3"
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
| Tag | `v0.2.2` (per-repository Dockerfile; no shared base image) |
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
gives git over SSH through the host's agent, so no private key enters the container.
`[herdr] machine` registers the container as a Herdr machine, and
`[herdr] layout = "standard"` opens it with the Home · Editor · Development ·
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
  agent socket (never host `~/.ssh`, `~/.gitconfig` or `${HOME}`); publish a port beyond loopback unless the repository's own
  config says so; pass `--trust` on the developer's behalf; copy a private
  key into an image or container; answer dck's `ssh-add` prompt or set
  `[ssh] host_extra` in the developer's host profile on their behalf; run
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
git clone --branch v0.2.2 https://github.com/DailybotHQ/devcontainer-kit
./devcontainer-kit/install.sh
npx --yes skills add https://github.com/DailybotHQ/devcontainer-kit/tree/v0.2.2 --skill dck-dockerfile -y
```

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

`python3 ../../shared/config.py enable devcontainer --version v0.2.2 --repo <repo>`,
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
`dck exec -- <command>` (a compound command: `dck exec -- bash -c '…'`).
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
   descriptor pins `DailybotHQ/devcontainer-kit` `v0.2.2`, interface 2; no
   template, Dockerfile, compose file, entrypoint or `dev.sh` copy ships here.
2. `dck doctor --json` reports interface 2, a valid repo config and no drift.
3. Existing files were changed only through accepted render diffs, each
   with a backup.
4. Ports bind loopback; no privileged options; no host `~/.ssh`,
   `~/.gitconfig` or `${HOME}` mount; no key material in the image.
5. The image builds for real, and the repository's real test command runs
   inside the container (or the failure is recorded).
