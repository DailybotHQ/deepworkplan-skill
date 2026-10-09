# Template — devcontainer through `dck` (reason, don't copy-paste)

Reason every option from the repository's **real** files; never from a
preset you remember. Detected reality wins.

## 1. Stack → flavour

| Signal in the repo | `--flavour` |
|---|---|
| `package.json` (Node/TS app, service or lambda) | `node-24` |
| `pyproject.toml`, `requirements.txt`, `setup.py`, `Pipfile` | `python-3.13` |
| neither (Go, Rust, shell, docs, mixed) | `debian` (add the toolchain as a project layer below dck's managed blocks) |

A repository that needs a different runtime version keeps the flavour and
adds its own pinned layer under the Dockerfile's managed `base`/`layers`
blocks — never by editing inside them.

## 2. Service, ports, backing services

- `--service` — the compose service the tools attach to (default `app`).
- `--port name=number` — only ports the app really listens on in dev; they
  bind `127.0.0.1`.
- Backing services (database, cache, queue) the app really uses in dev go in
  `docker/local/docker-compose.yaml` **outside** dck's managed blocks, with
  their versions pinned; `runServices` stays the tools service unless the
  person wants them started together.

## 3. Layers (`.devcontainer/dck.toml` → `[layers]`)

| Layer | On when |
|---|---|
| `agents` | the person wants coding agents inside the container (installs coding-agents-kit at its pinned tag plus the listed CLIs through their vendors' channels; one named volume per CLI home so logins survive rebuilds) |
| `editor` | default on — nvim with DeepWorkPlan Vim; off when the person never edits inside |
| `dailybot` | **only** when the `dailybot` addon is enabled and asks for it |

## 4. Herdr container profile (optional)

Want the container as a Herdr machine? `ssh_port` > 0 and `[herdr] machine =
true`; `dck up` registers it. Running `dck herdr add` edits `~/.ssh/config`
(a guarded include) — ask for that separately. Inside, peers use the pinned
herdr-peers skill (`../../herdr/install.md`).

## 5. Render and validate

```bash
dck init --dry-run --flavour <f> --service <s> [--port web=<n>]   # plan + diffs; writes nothing
dck init --flavour <f> --service <s> [--port web=<n>]             # after acceptance (per-file prompt on a terminal)
dck setup && dck up
dck doctor --json                                                  # interface, runtime, repo, layers, ssh, drift
dck exec -- <the repo's real test command>
```

Record each outcome. A failure is a finding about the environment, never a
repository conformance failure.
