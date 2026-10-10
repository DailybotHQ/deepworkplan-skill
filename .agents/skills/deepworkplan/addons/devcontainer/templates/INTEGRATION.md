# Template — devcontainer through `dck` (reason, don't copy-paste)

Reason every option from the repository's **real** files; never from a
preset you remember. Detected reality wins. When the `dck-dockerfile` skill
is installed, it does this detection and asks once for confirmation; this
page is the same reasoning for when it is not.

## 1. Stack → runtime

| Signal in the repo | Runtime |
|---|---|
| `package.json` / `pnpm-lock.yaml` (Node/TS app, service or lambda) | `node`, at the version `engines` declares |
| `pyproject.toml` / `uv.lock`, `requirements.txt`, `setup.py`, `Pipfile` | `python` |
| neither (Go, Rust, shell, docs, mixed) | `debian` (add the toolchain in the Dockerfile's project section, outside the kit's managed blocks) |

The Dockerfile starts from that runtime's **official image**, pinned by
digest in the kit's pin file. No shared base image is needed.

## 2. Service, ports, backing services

- Service name: the existing compose service, else the repository
  directory name.
- Ports: only ports the app really listens on in dev (existing compose,
  framework config, dev-script flags); they bind `127.0.0.1`.
- Backing services (database, cache, queue) the app really uses in dev go in
  `docker/local/docker-compose.yaml` **outside** the kit's managed blocks,
  with their versions pinned.

## 3. What goes in the image

| Piece | When |
|---|---|
| coding-agent CLIs through `ak install` | only the kinds the person names; each CLI home is a named volume so logins survive `dev.sh rebuild`. Agents launch in autonomy by default — the container is the sandbox; the compose's commented `AGENTKIT_PERMISSIONS=ask` line is the opt-out |
| DeepWorkPlan Vim | default on; off when the person never edits inside |
| extras (for example chromium for Lighthouse or Playwright) | only when the repository's own scripts need them |
| the Dailybot CLI | **only** when the `dailybot` addon is enabled and asks for it |

## 4. Herdr container profile (optional)

Want the container as a Herdr machine? Turn on the kit's Herdr machine
option; `bash dev.sh up` registers it. Running `dck herdr add` edits
`~/.ssh/config` (a guarded include) — ask for that separately. Git and SSH
inside use the host's agent, never a mounted `~/.ssh`; the kit picks the
agent socket by Docker provider. Inside, peers use the pinned herdr-peers
skill (`../../herdr/install.md`). `[herdr] mesh` (default `true`, Docker
Desktop only) connects the repository's container to the other dck
containers; it widens trust between them, so name that cost, and set
`mesh = false` when the container should stay on its own.

## 5. Render and validate

```bash
dck init --dry-run <options from §1–§3>     # plan + diffs; writes nothing
dck init <options from §1–§3>               # after acceptance (per-file prompt on a terminal)
dck doctor --json                           # interface 2, runtime, repo, drift
bash dev.sh build && bash dev.sh up         # a real build; a failure is a failed run
dck exec -- <the repo's real test command>
```

Use the option names the kit's `v0.2.1` documentation gives (`dck init
--help`). Record each outcome. A failure is a finding about the environment,
never a repository conformance failure.
