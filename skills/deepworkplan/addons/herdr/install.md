# Herdr addon — install (pinned)

Show these to the person; run them yourself only in an interactive session
after explicit acceptance. Every skill install names an exact tag (W012).

## 1. Herdr itself (the multiplexer)

Install Herdr through its own documented paths — the install page
`https://herdr.dev/docs/install/`, Homebrew (`brew install herdr`), mise
(`mise use -g herdr`) or a release archive from
`https://github.com/herdrdev/herdr/releases`. Pick one; never pipe a
downloaded installer into a shell. Re-detect afterwards with
`herdr --version`.

## 2. The two skills (host)

```
npx --yes skills add herdrdev/herdr@v0.9.3 --skill herdr -g
npx --yes skills add DailybotHQ/herdr-peers@v0.1.0 --skill herdr-peers -g
```

The first is Herdr's official skill (the authority for every `herdr`
command; `herdr --skill` prints the copy matching the installed binary).
The second installs the herdr-peers skill and its helper script. Verify:
`herdr-peers --version` → `herdr-peers 0.1.0 (protocol 1)`.

## 3. Containers

A dev container that should host peers carries Herdr and the same two
pinned skills in its image or setup step (the `devcontainer` addon and
devcontainer-kit handle this when their `herdr` options are on). From
inside a container, peers on the host are reached through Herdr's own
machine registration — never by editing `~/.ssh` or host trust from this
addon; SSH trust changes need their own explicit approval.

## 4. Record the acceptance

```
python3 <pack>/shared/config.py enable herdr --version v0.1.0 --repo <repo>
```
