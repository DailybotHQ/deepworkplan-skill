---
name: deepworkplan-addon-devcontainer
description: Optional DeepWorkPlan addon that gives a repository a reproducible dev container through devcontainer-kit (the `dck` command, DailybotHQ/devcontainer-kit pinned at v0.1.2, interface 1) - a vendor-neutral thin integrator that detects the kit with `dck doctor --json`, offers `dck init` (which reconciles an existing layout and never clobbers it), maps the detected stack to a base-image flavour and the opt-in layers (agents through coding-agents-kit, the editor, Dailybot only when that addon asks), optionally registers the container as a Herdr machine, and validates the result. Opt-in, never required, never a conformance gate.
version: "6.1.0"
documentation_url: https://deepworkplan.com/kit/devcontainer
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"📦","homepage":"https://deepworkplan.com/kit/devcontainer","requires":{"anyBins":["docker","git"]}}}
---

# DeepWorkPlan — Devcontainer Addon

Give the repository a **reproducible, isolated dev container** that any human
or AI agent can open the same way — from a terminal (`dck up`), from VS Code /
Cursor ("Reopen in Container"), or with the `devcontainer` CLI. This is an
**opt-in addon**, never required for a repo to be AI-first and never a
conformance gate.

This addon is a **thin integrator** of **devcontainer-kit**
(`https://github.com/DailybotHQ/devcontainer-kit`, MIT, works without DWP).
The layout, the pinned base images, the entrypoint library, the launcher,
SSH and Herdr registration are the kit's; this addon decides **whether** to
offer it, **which options** fit the repository, and **how to validate** the
result. It carries no company-specific network, volume or file name.

| Pin | Value |
|-----|-------|
| Product | `DailybotHQ/devcontainer-kit` |
| Tag | `v0.1.2` |
| Interface | `1` (`dck doctor --json` → `"interface": 1`) |
| Registry key | `devcontainer` (`.dwp/config.json` → `addons.devcontainer`) |
| Abilities | none (it provides an environment, not a delegation transport) |

## Read these first (all relative inside the skill)

- [`SPEC.md`](SPEC.md) — the normative contract.
- [`templates/INTEGRATION.md`](templates/INTEGRATION.md) — reasoning aid:
  stack → flavour and layers, the Herdr container profile, validation.

## When this runs

`onboard` Phase 7b offers it when the repository benefits from an isolated,
reproducible environment (services, a pinned toolchain, agents that should
not touch the host); or on direct invocation. No other flow requires it.

## Trust boundary (write scope)

`allowed-tools` includes write-capable `Edit`, `Write`, and `Bash`:

- **Before consent: read-only.** `command -v dck docker`, `dck doctor --json`,
  and reading the repository's existing `.devcontainer/` and `docker/` files.
- **Writes (only after explicit acceptance):** the kit install (pinned tagged
  clone + `install.sh`), `dck init` in the repository — which shows a plan and
  diffs and changes an existing file only with consent, after a timestamped
  backup — the `addons.devcontainer` registry entry, and the validation record.
- **It MUST NOT:** pass `dck init --yes` without the developer's explicit
  acceptance of the shown diff; add `privileged`, `cap_add`, host namespaces,
  the Docker socket or host bind mounts; publish a port beyond loopback unless
  the repository's own config says so; pass `--trust` on the developer's
  behalf; copy a private key into an image or container; run `dck herdr add`
  (it edits `~/.ssh/config`) without its own explicit approval; or write any
  secret value (`.env` files are created `0600` by `dck setup` and stay
  gitignored).

## The flow

### Step 0 — Detect (read-only)

`command -v dck` → `dck doctor --json`: `interface` must be `1` (otherwise one
warning and "not available"); read `runtime` (Docker/OrbStack/colima and
Compose), `repo` (config validity) and `drift`. Note an existing
`.devcontainer/` or `docker/` layout — it will be **reconciled**, never
replaced silently.

### Step 1 — Offer (never impose)

Explain what it adds (one reproducible environment, loopback-only ports,
agent forwarding instead of key copies, optional coding agents and editor
inside) and what it costs (Docker, an image pull). Declining is complete.

### Step 2 — Install the kit (pinned; point-don't-run by default)

```
git clone --branch v0.1.2 https://github.com/DailybotHQ/devcontainer-kit
./devcontainer-kit/install.sh
```

### Step 3 — Render the layout (reconcile, never clobber)

Reason the options from the real stack (`templates/INTEGRATION.md`), then
`dck init --dry-run …` to show the plan and diffs; only after acceptance run
`dck init …` (the kit asks per changed file on a terminal, or `--yes` once the
person accepted the shown diffs). Then `dck setup && dck up`.

### Step 4 — Record and validate

`python3 ../../shared/config.py enable devcontainer --version v0.1.2 --repo <repo>`,
then `dck doctor --json` (runtime, repo config, layers, ssh, drift) and
`dck exec -- <the repo's real test command>` — every result recorded, none
blocking.

## Failure-mode guardrails

- **Never required, never blocking.** No Docker, no kit, an unknown
  interface, a declined diff: record and continue on the host.
- **Reconcile, don't clobber.** Only `dck init`'s consented, backed-up
  changes touch existing files; nothing outside its managed blocks moves.
- **Vendor-neutral.** No company network, volume, CLI or profile file is a
  requirement; the Dailybot CLI layer appears only when the `dailybot` addon
  asks for it.

## Validation checklist (component 4 — mirrored from SPEC §8)

1. `SKILL.md`, `SPEC.md`, `addon.json`, `templates/INTEGRATION.md` exist; the
   descriptor pins `DailybotHQ/devcontainer-kit` `v0.1.2`, interface 1.
2. `dck doctor --json` reports interface 1 and a valid repo config.
3. Existing files were changed only through consented `dck init` diffs, each
   with a `*.dck-bak-*` backup.
4. Ports bind loopback; no privileged options; no key material in the image.
5. The repository's real test command runs inside the container (or the
   failure is recorded).
