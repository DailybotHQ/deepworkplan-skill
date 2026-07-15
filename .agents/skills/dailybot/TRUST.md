# Trust & guarantees — Dailybot agent skill

This file ships **inside** the skill so you can read exactly what the Dailybot
skill will and will not do on your machine before you let it run. It restates,
in one place, the guarantees enforced by the skill's design and its consent
flows. The authoritative security policy lives in the repo's
[`SECURITY.md`](https://github.com/DailybotHQ/agent-skill/blob/main/SECURITY.md);
this is the install-time companion to it.

Source of truth: <https://github.com/DailybotHQ/agent-skill>. License: MIT.

## What this skill is

A **Markdown-first** agent skill: the "code" is the `SKILL.md` prompt files an
agent reads at runtime, plus one small Bash helper (`shared/context.sh`, which
detects repo/branch/agent metadata locally). Unlike a pure methodology skill,
Dailybot is an **integration** — its whole purpose is to connect your agent to
your team through Dailybot's first-party API. So it is honest and up-front:
running its capabilities **does** invoke the `dailybot` CLI and **does** make
authenticated HTTPS calls to Dailybot's own API. It never talks to any other
third party, and it emits **no hidden telemetry** — every call is one you asked
for (send a report, poll messages, complete a check-in, …).

## Permissions it requests (`allowed-tools`)

`Bash, Read, Grep, Glob` — and why each is needed:

- **Read, Grep, Glob** — read this skill's own files, detect the installed CLI
  version, and inspect an optional committed `.dailybot/profile.json` to honor
  the team's report identity and policy.
- **Bash** — run the `dailybot` CLI (the actual integration surface) and
  `shared/context.sh` (reads local git + environment metadata only).

It does **not** request `Edit` or `Write`. The only files it changes are written
through the `dailybot` CLI or through the **consent-gated** setup flows below.

## What it does to your machine

Every action that touches your machine is **opt-in and shown to you first**:

- **CLI install (with consent).** If the `dailybot` CLI is missing, the skill
  proposes the official installer and installs **only after you confirm**. The
  primary install path is **defense-in-depth verified** — it downloads
  `install.sh` from the CDN *and* from the GitHub source, refuses to run if they
  differ, and checks the published `SHA256` before executing. See
  [`shared/auth.md`](shared/auth.md).
- **Credentials at rest.** Login (email OTP → Bearer) or an org `DAILYBOT_API_KEY`
  is stored by the CLI under `~/.config/dailybot/` with `0600` permissions
  (owner-only). Secrets are masked in all output — never printed or logged in
  full.
- **Auto-activation & hooks (both opt-in, both reversible).** If you accept, the
  skill writes a marked trigger block to your agent config and/or wires the
  `dailybot hook` lifecycle commands. Both are shown to you verbatim before any
  write, both carry an uninstall marker (`dailybot-auto-activation` for triggers,
  the `dailybot hook` command string for hooks), and neither is ever written
  silently. See [`report/SKILL.md`](report/SKILL.md) Step 0 and
  [`report/hooks.md`](report/hooks.md).

## What it does NOT do

- **No silent installs or writes** — CLI install, auto-activation, and hooks are
  each gated on your explicit confirmation. Nothing anywhere in this skill says
  "install without asking."
- **No hidden telemetry, no analytics, no "phone home."** At runtime the only
  network calls are the CLI actions you invoke, against Dailybot's first-party
  API. The one-time CLI installer additionally fetches from the Dailybot CDN and
  cross-checks the GitHub source for verification (see Provenance below) — always
  behind your consent.
- **Never exfiltrates repo config.** The CLI carries `.dailybot/profile.json`'s
  `vars` block for local use but **never sends it** in any report, message, or
  payload.
- **Never sends secrets to a third party**, never emails without a confirmed
  recipient + body summary and a pre-send credential scan (see
  [`email/SKILL.md`](email/SKILL.md)), and never posts chat/report content you
  did not author.
- **No background daemon, no persistent external state** beyond the credential/
  config files under `~/.config/dailybot/`.

## Provenance — verify before you run

Two independent things to verify:

1. **The CLI installer** is checksummed. The primary install path in
   [`shared/auth.md`](shared/auth.md) downloads `install.sh` from both the CDN and
   the GitHub source, diffs them, and verifies the published `install.sh.sha256`
   before running — so a tampered CDN copy is refused.
2. **The skill itself** is fully open source. Every shipped file lives under
   `skills/dailybot/` at a tagged release; diff your installed copy against the
   repository at its tag to confirm it is unmodified. (Releases are currently
   checksummed at the installer level, not signed at the skill level — signing is
   a documented next step, not a current claim.)

## Self-audit (don't take our word for it)

Run these from the repo root (or your installed skill directory) to confirm the
claims above:

```bash
# 1. The skill ships exactly ONE runtime script — context.sh — and it makes no
#    network call. All Dailybot API access is delegated to the separately
#    installed `dailybot` CLI, never to ad-hoc HTTP embedded in the skill:
find skills/dailybot -name '*.sh'          # -> only shared/context.sh
grep -nE 'curl|wget|http' skills/dailybot/shared/context.sh \
  || echo 'OK: context.sh reads local git + env only'

# 2. No hardcoded credentials or tokens anywhere in the shipped skill:
grep -RInE '(api[_-]?key|token|secret|bearer)[[:space:]]*[:=][[:space:]]*["'"'"'][A-Za-z0-9._-]{16,}' \
  skills/dailybot || echo 'OK: no embedded secrets'

# 3. The one place the skill triggers a download — the CLI installer — is
#    checksum-verified before it runs (defense-in-depth guard):
grep -nE 'sha256|shasum|diff -q' skills/dailybot/shared/auth.md
```

## Reporting a vulnerability

Privately, to **security@dailybot.com** — never a public issue. See
[`SECURITY.md`](https://github.com/DailybotHQ/agent-skill/blob/main/SECURITY.md).
