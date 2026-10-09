# SPEC.md — Devcontainer Addon (Normative)

## Abstract

The normative specification of the DeepWorkPlan **devcontainer addon**: an
opt-in, vendor-neutral thin integrator of **devcontainer-kit** (`dck`;
`DailybotHQ/devcontainer-kit`, MIT, its own release cycle). The kit owns the
Dev Containers layout (`dck init`), the pinned base images, the entrypoint
library, the launcher, SSH agent forwarding and Herdr registration. This
addon owns detection, the offer, the pinned install, the mapping from a
repository's real stack to the kit's options, the registry record and the
validation.

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 2.0.0 |
| **Status** | Beta (DeepWorkPlan 7.0.0-beta.1) — supersedes the 1.x in-pack templates |
| **Product pin** | `DailybotHQ/devcontainer-kit` `v0.1.2`, interface `1` |
| **Companions** | `SKILL.md`, `addon.json`, `templates/INTEGRATION.md`, `../README.md`, `../../spec/ADDONS.md` |

## 1. Conventions

RFC 2119 keywords. **The kit** is devcontainer-kit; **the addon** is this
folder.

## 2. Placement (revised for 7.0.0)

The 1.x addon carried copy-paste templates (Dockerfile, compose, entrypoint,
custom commands) and company-specific requirements; an audit found they
had drifted from every real setup. The implementation moved into a product
that owns it and tests it. This folder **MUST NOT** carry a copy of the
layout, the entrypoint or the images, and **MUST NOT** require any
company-specific network, volume, CLI or profile file.

## 3. What This Addon Is — and Is Not

- **Optional and never required**; a repository without a container is
  fully conformant.
- It contributes **no** host ability and requires **no** grant: it provides
  an environment.
- It is not a launcher, an image or a template set.

## 4. Detection

- Read-only: `command -v dck`, `dck doctor --json`.
- `interface` **MUST** equal `1`; otherwise one warning and "not available".
- An existing `.devcontainer/` or `docker/` layout **MUST** be treated as the
  repository's own work: reconciled through `dck init`, never replaced.

## 5. Offer, Install and Render

- Explicit opt-in (`onboard` Phase 7b); a decline writes nothing.
- Install:
  `git clone --branch v0.1.2 https://github.com/DailybotHQ/devcontainer-kit` then
  `./devcontainer-kit/install.sh`. A fetch-and-execute pipeline **MUST NOT**
  appear in this pack's text.
- Options **MUST** be reasoned from the repository's real files
  (`templates/INTEGRATION.md`): `--flavour` (`node-24`, `python-3.13`,
  `debian`), `--service`, named `--port`s, the `[layers]` (`agents`,
  `editor`, `dailybot`), and `[herdr] machine`.
- The addon **MUST** show `dck init --dry-run` first; an existing file
  changes only after the person accepted its diff (the kit backs it up as
  `<file>.dck-bak-<timestamp>`). `--yes` **MUST NOT** be passed without that
  acceptance; `--trust` **MUST NOT** be passed on the person's behalf.
- The `dailybot` layer is enabled **only** when the `dailybot` addon is
  enabled and asks for it. The `agents` layer installs coding-agents-kit at
  the kit's pinned tag; its wrappers add no permission-bypass flag.
- On acceptance: `addons.devcontainer` = `{"enabled": true, "version":
  "v0.1.2"}` via `shared/config.py enable`.

## 6. Security Defaults (inherited, never weakened)

Ports bind `127.0.0.1` unless the repository's config says otherwise; no
`privileged`, `cap_add`, host namespaces, Docker socket or host bind mounts in
what this addon proposes; SSH into the container uses **agent forwarding**
from the host — private keys are never copied into an image or container;
the container's sshd is pubkey-only with runtime host keys; `.env` files are
`0600` and gitignored; no secret value is written by the addon.

## 7. Herdr Container Profile

When the repository wants its container as a Herdr machine (the herdr
addon's container profile): `ssh_port` > 0 and `[herdr] machine = true` in
`.devcontainer/dck.toml`; `dck up` registers it. `dck herdr add` writes the
user's `~/.ssh/config` include and **MUST** be run only with its own
explicit approval. Peers then run the pinned herdr-peers skill inside the
container (`../herdr/install.md` §3).

## 8. Validation Checklist

1. `SKILL.md`, `SPEC.md`, `addon.json`, `templates/INTEGRATION.md` exist; no
   layout/entrypoint/image copy ships in this folder; `addon.json` pins
   `DailybotHQ/devcontainer-kit` `v0.1.2`, interface 1.
2. `dck doctor --json`: interface 1; repo config valid; drift reported.
3. Existing files changed only through accepted `dck init` diffs with
   backups.
4. §6 holds for everything the addon proposed.
5. The repository's real test command ran inside the container, or the
   failure is recorded. Every outcome is recorded; none blocks a flow.
