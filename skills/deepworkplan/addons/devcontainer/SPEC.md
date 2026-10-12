# SPEC.md — Devcontainer Addon (Normative)

## Abstract

The normative specification of the DeepWorkPlan **devcontainer addon**: an
opt-in, vendor-neutral thin integrator of **devcontainer-kit** (`dck`;
`DailybotHQ/devcontainer-kit`, MIT, its own release cycle). The kit owns the
Dockerfile template and its render (`dck init`), the pinned images and
tools, the entrypoint, the launcher, SSH agent forwarding, Herdr
registration and the `dck-dockerfile` skill. This addon owns detection, the
offer, the pinned installs, the mapping from a repository's real stack to
the kit's options, the registry record and the validation.

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 3.0.0 |
| **Status** | Stable — per-repository Dockerfile, no shared base image (devcontainer-kit `v0.3.2`, interface 2); supersedes 2.x (base-image flavours, interface 1) |
| **Product pin** | `DailybotHQ/devcontainer-kit` `v0.3.2`, interface `2`; skill `dck-dockerfile` at the same tag |
| **Companions** | `SKILL.md`, `addon.json`, `templates/INTEGRATION.md`, `../README.md`, `../../spec/ADDONS.md` |

## 1. Conventions

RFC 2119 keywords. **The kit** is devcontainer-kit; **the addon** is this
folder; **the skill** is the kit's `dck-dockerfile`.

## 2. Placement

The 1.x addon carried copy-paste templates (Dockerfile, compose, entrypoint,
custom commands) and company-specific requirements; an audit found they
had drifted from every real setup. The implementation lives in a product
that owns it and tests it. This folder **MUST NOT** carry a copy of the
layout, the Dockerfile template, the compose file, the entrypoint, `dev.sh`
or any image, and **MUST NOT** require any company-specific network,
volume, CLI or profile file.

## 3. What This Addon Is — and Is Not

- **Optional and never required**; a repository without a container is
  fully conformant.
- It contributes **no** host ability and requires **no** grant: it provides
  an environment.
- It is not a launcher, an image or a template set.

## 4. Detection

- Read-only: `command -v dck`, `dck doctor --json`.
- `interface` **MUST** equal `2`; otherwise one warning and "not available"
  (interface `1` is a kit older than `v0.2.0`: offer the upgrade).
- `version` `0.2.0` reports interface `2` but is unsupported since the
  `v0.2.1` security release: the addon **MUST NOT** treat it as compatible
  and **MUST** offer the upgrade to the pinned tag.
- An existing `.devcontainer/`, `docker/` layout or `dev.sh` **MUST** be
  treated as the repository's own work: reconciled through the render,
  never replaced.

## 5. Offer, Install and Render

- Explicit opt-in (`onboard` Phase 7b); a decline writes nothing.
- Install the kit:
  `git clone --branch v0.3.2 https://github.com/DailybotHQ/devcontainer-kit` then
  `./devcontainer-kit/install.sh`. A fetch-and-execute pipeline **MUST NOT**
  appear in this pack's text.
- The addon **SHOULD** offer the skill with
  `npx --yes skills add https://github.com/DailybotHQ/devcontainer-kit/tree/v0.3.2 --skill dck-dockerfile -y`
  (repo-local, recorded in `skills-lock.json`); the install **MUST** name
  the exact tag in that tree-URL form.
- **The layout.** The render produces exactly
  `.devcontainer/devcontainer.json`, `docker/local/<service>/Dockerfile`
  (plus its entrypoint and layer scripts), `docker/local/docker-compose.yaml`
  and `dev.sh` (kept when it exists). `devcontainer.json` opens the same
  compose service as `dev.sh`.
- **No shared base image.** The Dockerfile starts from the official runtime
  image (node, python or debian) pinned by `tag@sha256:digest`. The addon
  **MUST NOT** require or propose the kit's GHCR base image.
- Options **MUST** be reasoned from the repository's real files
  (`templates/INTEGRATION.md`): service, runtime, ports, the coding-agent
  CLIs to install (none unless the person names them), extras, and the
  Herdr machine profile.
- The addon **MUST** show the render as a plan and diffs first
  (`dck init --dry-run`, or the skill's confirmation step); an existing file
  changes only after the person accepted its diff (the kit backs it up as
  `<file>.dck-bak-<timestamp>`). `--yes` **MUST NOT** be passed without that
  acceptance; `--trust` **MUST NOT** be passed on the person's behalf.
- The `dailybot` layer is enabled **only** when the `dailybot` addon is
  enabled and asks for it. The agents layer installs coding-agents-kit from
  its checksum-verified release and the CLIs through `ak install`; agents in
  the container launch in the kit's autonomy by default, and the compose
  carries the commented `AGENTKIT_PERMISSIONS=ask` opt-out. The addon adds
  no autonomy flag. Since `v0.3.2` the image also carries coding-agents-kit's
  three skills (`agentkit`, `agentkit-setup`, `agentkit-orchestrate`) from the
  same verified release tarball, linked into every agent's skills directory
  at each start, so a recreate keeps them; the addon installs no second copy.
- On acceptance: `addons.devcontainer` = `{"enabled": true, "version":
  "v0.3.2"}` via `shared/config.py enable`.

## 6. Security Defaults (inherited, never weakened)

Ports bind `127.0.0.1` unless the repository's config says otherwise; no
`privileged`, `cap_add`, host namespaces, Docker socket or host bind mounts
beyond the workspace and the SSH agent socket in what this addon proposes —
in particular no host `~/.ssh`, `~/.gitconfig` or `${HOME}` mount (the kit's
read-only `~/.ssh_host` bind under the developer's own `[ssh] copy_keys`,
§6.2, is never proposed by the addon); SSH and git inside the container use the host's
**agent** (forwarding, or the agent socket the kit picks by Docker
provider — Docker Desktop and OrbStack share the host agent, a native
Linux engine mounts `$SSH_AUTH_SOCK`, other runtimes get none in exec
sessions). With the kit's `ssh_host_config` (default `true`), the
developer's `~/.ssh/config` aliases for git hosting services are copied in
with **public** keys and already-trusted host keys only, and only those
whose key the host agent holds, so git over SSH with their own aliases
works inside; the addon **MUST NOT** answer the kit's `ssh-add` offer or
write `[ssh] host_extra` (a host-profile key that widens the copy beyond git
hosting services) on the developer's behalf — private keys are
never copied into an image, and into a container only through the
developer's own `[ssh] copy_keys` opt-in (§6.2), which this addon never
proposes or sets; the container's sshd is
pubkey-only with host keys generated at runtime, never baked in; every
download in the image is verified; `.env` files are `0600` and gitignored;
no secret value is written by the addon.

## 6.1. Host Accounts (`host_profiles`, opt-in)

- `[agents] host_profiles` (bool, default `false`) and `host_env_keys`
  (list of variable **names**, default `[]`) belong to the developer's
  **host** profile (`~/.config/dck/profile.toml`). The addon **MUST NOT**
  set them, and **MUST NOT** propose them in a repository's `dck.toml`.
- When on, only profiles of the CLIs the repository installs are shared —
  each bound by itself (`$AGENTKIT_PROFILES_DIR/<cli>/<name>`, optionally
  limited by `host_profile_names`), read-write only where the CLI writes,
  plus the host Codex home when `codex@default` is shared; the agentkit home
  is never mounted, and Cursor and Antigravity profiles are never shared.
- Shared variables reach the container only through a host-generated
  `0600` env file mounted read-only as `AGENTKIT_ENV`, holding the Claude
  token of each shared Claude profile and the exact names in
  `host_env_keys` — nothing else, and nothing at all with `host_profiles`
  off. A value **MUST NOT** appear in compose, a log, doctor output or
  anything this addon writes.
- Claude's bypass-permissions acknowledgement is written by the kit only in
  the container's own homes with autonomy on — never in a shared host profile,
  and never with `AGENTKIT_PERMISSIONS=ask`. No agent sends keys for it.
- The offer **MUST** say which accounts become usable inside the
  container, that a process there can change those profiles' login files
  through the read-write mounts, and that a shared Codex `auth.json` allows
  one active writer per account.

## 6.2. Host SSH Keys (`[ssh] copy_keys`, opt-in, `v0.3.2`)

- `[ssh] copy_keys` (bool, default `false`) belongs to the developer's
  **host** profile; a repository's `dck.toml` cannot set it, and `dck setup`
  asks once (default no). The addon **MUST NOT** set it or answer that
  question, and **MUST NOT** propose it in a repository's files.
- When on, `dck up` binds the host's whole `~/.ssh` **read-only** at
  `~/.ssh_host` through a runtime compose overlay, and every container start
  copies its `id_*` keys into the container's `~/.ssh` on the state volume
  (private `0600`, `.pub` `0644`; refreshed or removed when they change or
  disappear on the host). dck's own `config`, `config.d/`, `authorized_keys`
  and `known_hosts.dck-host` are untouched; agent forwarding is unchanged.
  Turning it off removes the copies at the next start.
- It exists for tools that read only key files (for example
  `gh auth login`). If the developer raises it, the addon **MUST** state the
  trade-off: while it is on, every file of the host `~/.ssh` is readable
  inside the container, and private keys rest in the state volume (removing
  that volume wipes them). `dck doctor` reports the opt-in and key file
  names only.

## 6.3. State Volume (`[compose] state_volume`, `v0.3.2`)

The service's state volume (sshd host key, `~/.ssh`, `gh` auth, Herdr client
state, history) defaults to `state`. When several services share one compose
project (one `COMPOSE_PROJECT_NAME`), each **MUST** get its own name through
`[compose] state_volume` in `dck.toml` (or `dck init --state-volume NAME`);
otherwise they all mount one `<project>_state` volume. The addon reasons
this from the repository's compose setup and passes the name to the render;
`dck doctor` flags a shared state volume. The mount point inside does not
change, and an existing install keeps its `state` volume.

## 7. Herdr Container Profile

When the repository wants its container as a Herdr machine (the herdr
addon's container profile): enable the kit's Herdr machine option; `dck up`
(or `bash dev.sh up`) registers it. `dck herdr add` writes the user's
`~/.ssh/config` include and **MUST** be run only with its own explicit
approval. Peers then run the pinned herdr-peers skill inside the container
(`../herdr/install.md` §3); every `v0.3.2` image carries herdr-peers. The
kit's `[herdr] layout` key (`"standard"`: App · Editor · Development ·
Agents, created by `dck up`; `"none"` skips it) is the kit's choice, and the
addon passes the person's preference without adding its own. The optional
`[herdr] mesh` key (default `true`, Docker Desktop only) lets agents inside
reach the other dck containers; it widens trust between containers, so
the offer **MUST** say so, and `mesh = false` is the person's opt-out.
Since `v0.2.3` the mesh also reaches the host (the kit's opt-in loopback
host listener, offered once by `dck setup`, or an existing listener named in
the host profile) and the host's other loopback containers, keeps the
container's Herdr catalog across rebuilds, and installs a verified
herdr-peers on the host. The listener lets code in a running container open
a shell on the host as the developer — the offer **MUST** say so; its
opt-outs are `dck host listener disable` and `[host] machine = false`.
Since `v0.3.2`, `dck rebuild`, `dck start` and `dck restart` run the same
post-start steps as `dck up`: the Herdr machine is registered again (re-added
when it was removed, its host key re-pinned), the mesh and the host-catalog
mirror are pushed and the layout is created, so a container built from
scratch reaches the host and its peers without a hand `dck herdr mesh`. With
kit `v0.3.2`, the lead's brief names the value and a Codex pane inside a container **MUST** set
`HERDR_PEERS_SELF=<the container's machine id as saved on the host>` for
herdr-peers asks to other machines (its commands run from a per-profile
server, so the self probe cannot find it); dck `v0.3.3` is expected to set it.

## 8. Validation Checklist

1. `SKILL.md`, `SPEC.md`, `addon.json`, `templates/INTEGRATION.md` exist; no
   layout, Dockerfile, compose, entrypoint, `dev.sh` or image copy ships in
   this folder; `addon.json` pins `DailybotHQ/devcontainer-kit` `v0.3.2`,
   interface 2.
2. `dck doctor --json`: interface 2; repo config valid; drift reported.
3. Existing files changed only through accepted render diffs with
   backups.
4. §6 holds for everything the addon proposed.
5. The image built for real, and the repository's real test command ran
   inside the container, or the failure is recorded. Every outcome is
   recorded; none blocks a flow.
