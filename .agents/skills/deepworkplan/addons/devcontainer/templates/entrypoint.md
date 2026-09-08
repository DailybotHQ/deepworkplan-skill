# Template — `docker/local/{service}/entrypoint.sh` (the near-verbatim piece)

> **This is the one piece you copy near-verbatim.** The AI-CLI persistence
> pattern is stable across every Dailybot repo. The **only** things you adapt are
> `{user-home}` (and whether you set it up for one user or both `root` +
> `dev-user`). Do not re-invent it; do not "improve" the seed logic.

## Why it exists

AI/agent CLIs (`claude`, `codex`, `cursor`, `gh`, `dailybot`) store auth + session
state under the home directory. Without persistence, every `docker compose build`
logs the agent out. This entrypoint makes that state live in **named volumes**,
so it **seeds on first run and survives rebuilds**.

## The pattern (per tool)

For each tool's real config location, the entrypoint does — idempotently:

1. Ensure the persistent data dir exists (`{user-home}/.{tool}_data`, backed by a
   named volume).
2. If the real path (`~/.claude`, `~/.codex`, `~/.cursor`,
   `~/.config/gh`, `~/.config/dailybot`, `~/.claude.json`, `~/.config/claude-code`,
   `~/.config/cursor`) is **not already a symlink**:
   - **Seed only if the volume copy is empty** (`cp` real → data dir), so existing
     persisted auth is never clobbered.
   - Remove the real path.
   - Symlink it into the persistent data dir.
3. `chown` the data dirs to the dev user.

SSH keys are **opt-in, never seeded silently**: the host `~/.ssh` may be mounted
**read-only** at `~/.ssh_host`, but the entrypoint **copies** each `id_*`
private key (plus `*.pub`, `config`, `known_hosts`) into a writable `~/.ssh`
**only when the developer explicitly enabled it** — the read-only mount present
**and** `SEED_SSH_KEYS=1` set in the devcontainer/compose environment (a
visible, version-controlled line the developer chose to write). Without that
explicit opt-in, the container starts with an empty `~/.ssh` and git-over-SSH
falls back to the developer's normal credential flow (HTTPS + `gh auth`, or
forwarded agent). The copy is `chmod 600`/`700` and **only if keys aren't
already present** (so a persistent volume is never overwritten).

The script ends with `exec "$@"` so the compose `command` (`sleep infinity` for
the devcontainer) runs as PID 1's child.

## Blast radius & security rationale (read before adapting)

Everything this entrypoint touches is **developer-local**:

- The `*_data` targets are **Docker named volumes on the developer's own
  machine** — nothing crosses the network, and no host file outside the mounts
  the developer declared is read or modified.
- The AI-CLI persistence symlinks only **relocate auth/session state inside the
  container** so a rebuild does not log the agent out. They never exfiltrate,
  copy state out of the container, or phone home.
- The SSH seeding is **consent-gated by construction** (read-only mount +
  `SEED_SSH_KEYS=1`), copies **into** the container only, preserves `600`/`700`
  permissions, and is a no-op once keys exist. Default is **off**: a generated
  devcontainer that the developer did not explicitly opt in never touches
  private keys at all.
- Removing the read-only mount or setting `SEED_SSH_KEYS=0` (or simply never
  setting it) at any time disables the behavior without touching anything else.

If a security review of the target repo would rather not ship key copying at
all, generate the devcontainer without the `~/.ssh_host` mount — the entrypoint
degrades cleanly.

## Reference skeleton (copy, adjust `{user-home}` / users only)

```bash
#!/bin/bash
# AI-CLI persistence: seed-on-first-run, preserve-on-rebuild.

# Generic helper: link a real path into a persistent volume dir, seeding once.
# $1 = real path, $2 = persistent target (inside the *_data volume)
link_persist() {
  local real="$1" target="$2"
  if [ ! -L "$real" ]; then
    if [ -e "$real" ]; then
      # seed only if the volume target is empty/missing
      if [ ! -e "$target" ] || [ -z "$(ls -A "$target" 2>/dev/null)" ]; then
        mkdir -p "$(dirname "$target")"; cp -r "$real" "$target"
      fi
      rm -rf "$real"
    else
      mkdir -p "$target"
    fi
    mkdir -p "$(dirname "$real")"
    ln -sf "$target" "$real"
  fi
}

setup_ai_cli_persistence() {
  local H="$1"   # {user-home}, e.g. /home/dev-user
  mkdir -p "$H/.config"
  # Claude Code: .claude.json + .claude dir + .config/claude-code (+ .json.backup)
  link_persist "$H/.claude.json"               "$H/.claude_data/claude.json"
  link_persist "$H/.claude"                    "$H/.claude_data/claude_dir"
  link_persist "$H/.config/claude-code"        "$H/.claude_data/config_claude_code"
  # Codex
  link_persist "$H/.codex"                     "$H/.codex_data/codex_dir"
  # Cursor: CLI dir + auth tokens
  link_persist "$H/.cursor"                    "$H/.cursor_data/cursor_dir"
  link_persist "$H/.config/cursor"             "$H/.cursor_data/config_cursor"
  # GitHub CLI
  link_persist "$H/.config/gh"                 "$H/.gh_data/gh_config"
  # Dailybot CLI
  link_persist "$H/.config/dailybot"           "$H/.dailybot_data/config_dailybot"
}

setup_ssh_keys() {
  # OPT-IN: runs only when the developer mounted the host ~/.ssh read-only AND
  # explicitly set SEED_SSH_KEYS=1 in the devcontainer/compose environment.
  # Default (no mount, or flag unset/0) → no-op; the container never touches
  # private keys the developer did not explicitly hand it.
  if [ "${SEED_SSH_KEYS:-0}" != "1" ]; then return 0; fi
  local H="$1"; local SRC="$H/.ssh_host" DST="$H/.ssh"
  [ -d "$SRC" ] || return 0
  mkdir -p "$DST"
  if [ ! -f "$DST/id_rsa" ] && [ ! -f "$DST/id_ed25519" ] && [ ! -f "$DST/id_ecdsa" ]; then
    cp "$SRC"/id_* "$DST/" 2>/dev/null || true
    cp "$SRC"/*.pub "$DST/" 2>/dev/null || true
    cp "$SRC/config" "$DST/config" 2>/dev/null || true
    cp "$SRC/known_hosts" "$DST/known_hosts" 2>/dev/null || true
  fi
  chmod 700 "$DST" 2>/dev/null || true
  chmod 600 "$DST"/id_* "$DST/config" 2>/dev/null || true
}

# Adjust to your dev user. Heavier repos run this for BOTH /root and /home/dev-user.
setup_ai_cli_persistence "{user-home}"
setup_ssh_keys           "{user-home}"   # no-op unless the developer opted in
chown -R {dev-user}:{dev-user} {user-home}/.claude_data {user-home}/.codex_data \
  {user-home}/.cursor_data {user-home}/.gh_data {user-home}/.dailybot_data \
  {user-home}/.ssh {user-home}/.config 2>/dev/null || true

exec "$@"
```

## Decision notes

- The reference repos write this as **explicit per-tool functions** rather than
  the compact `link_persist` helper above — both are valid; prefer whichever
  matches the repo's existing style on reconcile. The **behavior** (seed-once,
  symlink, preserve, `exec "$@"`) is what MUST be preserved.
- **Keep the SSH opt-in gate as-is.** The `SEED_SSH_KEYS=1` guard (plus the
  read-only mount) is what makes private-key copying an explicit developer
  choice instead of a silent credential harvest — a pattern security scanners
  rightly flag (Snyk E006) when it ships ungated. Do not "simplify" it away, and
  do not pre-set the variable in generated files: the developer writes it.
- **Single vs dual user:** the hub/cli run as `dev-user` only → one call. The
  api-services container can run as `root` (app) or `dev-user` (devcontainer) →
  call the setup for **both** home dirs against the **same** named volumes.
- **CRLF:** the Dockerfile strips `\r` from the script before `chmod +x`.
- **Never seed over existing auth:** the `[ -z "$(ls -A ...)" ]` guard is what
  keeps a rebuild from wiping a logged-in session — keep it.
```
