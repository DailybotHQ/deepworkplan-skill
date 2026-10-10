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
| **Status** | Stable — per-repository Dockerfile, no shared base image (devcontainer-kit `v0.2.2`, interface 2); supersedes 2.x (base-image flavours, interface 1) |
| **Product pin** | `DailybotHQ/devcontainer-kit` `v0.2.2`, interface `2`; skill `dck-dockerfile` at the same tag |
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
  `git clone --branch v0.2.2 https://github.com/DailybotHQ/devcontainer-kit` then
  `./devcontainer-kit/install.sh`. A fetch-and-execute pipeline **MUST NOT**
  appear in this pack's text.
- The addon **SHOULD** offer the skill with
  `npx --yes skills add https://github.com/DailybotHQ/devcontainer-kit/tree/v0.2.2 --skill dck-dockerfile -y`
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
  no autonomy flag.
- On acceptance: `addons.devcontainer` = `{"enabled": true, "version":
  "v0.2.2"}` via `shared/config.py enable`.

## 6. Security Defaults (inherited, never weakened)

Ports bind `127.0.0.1` unless the repository's config says otherwise; no
`privileged`, `cap_add`, host namespaces, Docker socket or host bind mounts
beyond the workspace and the SSH agent socket in what this addon proposes —
in particular no host `~/.ssh`, `~/.gitconfig` or `${HOME}` mount; SSH and git inside the container use the host's
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
never copied into an image or container; the container's sshd is
pubkey-only with host keys generated at runtime, never baked in; every
download in the image is verified; `.env` files are `0600` and gitignored;
no secret value is written by the addon.

## 7. Herdr Container Profile

When the repository wants its container as a Herdr machine (the herdr
addon's container profile): enable the kit's Herdr machine option; `dck up`
(or `bash dev.sh up`) registers it. `dck herdr add` writes the user's
`~/.ssh/config` include and **MUST** be run only with its own explicit
approval. Peers then run the pinned herdr-peers skill inside the container
(`../herdr/install.md` §3); every `v0.2.2` image carries herdr-peers. The
kit's `[herdr] layout` key (`"standard"`: Home · Editor · Development ·
Agents, created by `dck up`; `"none"` skips it) is the kit's choice, and the
addon passes the person's preference without adding its own. The optional
`[herdr] mesh` key (default `true`, Docker Desktop only) lets agents inside
reach the other dck containers; it widens trust between containers, so
the offer **MUST** say so, and `mesh = false` is the person's opt-out.

## 8. Validation Checklist

1. `SKILL.md`, `SPEC.md`, `addon.json`, `templates/INTEGRATION.md` exist; no
   layout, Dockerfile, compose, entrypoint, `dev.sh` or image copy ships in
   this folder; `addon.json` pins `DailybotHQ/devcontainer-kit` `v0.2.2`,
   interface 2.
2. `dck doctor --json`: interface 2; repo config valid; drift reported.
3. Existing files changed only through accepted render diffs with
   backups.
4. §6 holds for everything the addon proposed.
5. The image built for real, and the repository's real test command ran
   inside the container, or the failure is recorded. Every outcome is
   recorded; none blocks a flow.
