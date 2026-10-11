# Herdr addon — install (pinned)

Show these to the person; run them yourself only in an interactive session
after explicit acceptance. Every skill install names an exact tag (W012).

## 1. Herdr itself (the multiplexer)

Install Herdr through its own documented paths — the install page
`https://herdr.dev/docs/install/`, mise pinned (`mise use -g herdr@0.9.3`),
Homebrew (`brew install herdr`, then confirm the version) or the release
archive of the tag `https://github.com/herdrdev/herdr/releases/tag/v0.9.3`.
Pick one; never pipe a downloaded installer into a shell. Re-detect
afterwards with `herdr --version` (0.9.3 or later in the 0.9 line matches
the pinned official skill).

## 2. The two skills (host)

```
npx --yes skills add https://github.com/herdrdev/herdr/tree/v0.9.3 --skill herdr -g -y
npx --yes skills add https://github.com/DailybotHQ/herdr-peers/tree/v0.2.1 --skill herdr-peers -g -y
```

Both `-y` flags are required in an agent's non-interactive shell (`npx
--yes` skips the download prompt; `skills add … -y` skips the target picker).
The first is Herdr's official skill (the authority for every `herdr`
command; `herdr --skill` prints the copy matching the installed binary).
The second installs the herdr-peers skill and its helper script. Verify:
`herdr-peers --version` → `herdr-peers 0.2.1 (protocol 1)`.

For a scoped trial in one repository without touching `$HOME` (F-10),
install the helper skill repo-locally — drop `-g`:

```
npx --yes skills add https://github.com/DailybotHQ/herdr-peers/tree/v0.2.1 --skill herdr-peers -y
```

It lands under the repository's agent skills directory (e.g.
`.agents/skills/herdr-peers/`); call its helper by that path instead of
`herdr-peers` on `PATH`, and keep the registry entry as
`{"enabled": true, "note": "repo-local trial"}` until the machine-level
install exists. Herdr itself, coding-agents-kit, devcontainer-kit and the
editor stay machine-level.

## 3. Containers

A dev container that should host peers carries Herdr and the same two
pinned skills in its image or setup step (the `devcontainer` addon and
devcontainer-kit handle this when their `herdr` options are on). From
inside a container, peers on the host are reached through Herdr's own
machine registration — never by editing `~/.ssh` or host trust from this
addon; SSH trust changes need their own explicit approval.

With devcontainer-kit `v0.3.0` the mesh needs no hand step: `dck up` pushes
into the container the host (through the kit's opt-in host listener, or an
existing loopback listener named in the dck host profile), every other dck
container and the other loopback containers the host's Herdr already
manages, each with a pinned host key; the container's Herdr machine catalog
survives `dck rebuild`, and since `v0.2.6` is a copy of the host's own Herdr catalog, so every agent names every machine by the same id and replies route back; and `dck setup` installs a verified herdr-peers on
the host, so host agents answer with `herdr-peers reply` too. Enabling the
listener, and listing extra keys (`[ssh] authorized_extra`) so non-dck
containers can reach dck ones, are the developer's decisions in the kit's
host profile — this addon describes them, never sets them.

## 4. Record the acceptance

```
python3 <pack>/shared/config.py enable herdr --version v0.2.1 --repo <repo>
```
