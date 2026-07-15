# Repo profile (`.dailybot/profile.json`) — mandatory pre-flight

> **Read this before constructing ANY `dailybot` CLI command from ANY Dailybot sub-skill (report, chat, kudos, email, forms, checkin, teams, health, messages).** This is a single source of truth — sub-skills link here instead of duplicating the rules.

The Dailybot CLI honours a per-repository configuration file at `<repo>/.dailybot/profile.json`. When a developer commits this file, they are telling every agent that works inside the repo *"use this identity and these defaults — don't pass them on the command line"*. If your CLI invocation also passes those values via flags, the flags **silently override the repo file** (per the [auth-resolution order](https://github.com/DailybotHQ/cli/blob/main/AGENTS.md#14-auth-resolution-order-do-not-break)), and the developer's pin is bypassed — bug.

This pre-flight closes that gap. Run it once per turn (or once per work session if you cache it) — the answer is invariant for the duration you stay in the same repo.

---

## The rule (one line)

> Before constructing any `dailybot <subcommand>` command line, walk up from `$PWD` looking for a `.dailybot/` directory. If `.dailybot/profile.json` exists in the closest ancestor, **omit from your command every flag the profile already provides**. (If `.dailybot/env.json` also exists, the CLI reads it automatically for credentials + URL overrides — see [`shared/env-json.md`](env-json.md); do not attempt to override its keys from the command line.)

What "already provides" means concretely:

| Profile key | Effect | Omit from your command line |
|---|---|---|
| `name` | Pins the agent display name | `--name` (and its short alias `-n`) |
| `profile` | Pins a named profile slug from `~/.config/dailybot/agents.json` | `--profile` (and its short alias `-p`) |
| `default_metadata.<key>` | Each `<key>` is shallow-merged into every outgoing report's metadata, with your inline value winning if both are set | `<key>` from your `--metadata` / `-d` JSON object — pass only keys the profile does **not** set |

Anything else the profile may contain (future-proofing — the schema may grow) is still **safe to ignore** for your command line; the CLI itself reads the full file.

### The `report` policy block (hooks, not flags)

The profile may also carry a `report` object. It is **not** a command-line concern — you never translate it into or out of a flag — but it is a committed team policy the Dailybot hooks honour, so it's documented here for completeness:

```json
{
  "name": "CLI",
  "default_metadata": { "repo": "cli" },
  "report": {
    "min_interval_minutes": 30,
    "nudge": true
  }
}
```

| `report` key | Effect | Default |
|---|---|---|
| `min_interval_minutes` | Minimum gap before the hooks surface another "you have unreported work" reminder for this repo. Raise it to make reminders less frequent. | `30` |
| `nudge` | `false` turns hook reminders off repo-wide (manual `dailybot agent update` still works); `true` keeps them on. | `true` |

This block is consumed by the deterministic hook reminders (`dailybot hook session-start` / `stop`), not by the report command itself. See [`../report/hooks.md`](../report/hooks.md) § "Per-repo controls" for the full hook policy (including the `.dailybot/disabled` kill-switch and `dailybot hook dismiss` snooze).

---

## How to detect the repo profile (mandatory pre-flight)

You must do this **inside the sub-agent / before issuing the command**, not after. Two equivalent ways:

### Shell one-liner (preferred — POSIX, no extra tools)

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROFILE="$ROOT/.dailybot/profile.json"
if [ -f "$PROFILE" ]; then
  cat "$PROFILE"
fi
```

If the file exists you'll see its JSON; pick which flags to omit based on the keys present.

### Programmatic (Python 3 — always available)

```bash
python3 - <<'PY'
import json, os, pathlib
cur = pathlib.Path.cwd()
for p in [cur, *cur.parents]:
    f = p / ".dailybot" / "profile.json"
    if f.is_file():
        profile = json.loads(f.read_text())
        print(f"REPO_PROFILE={f}")
        print(f"PROFILE_NAME={profile.get('name','')}")
        print(f"PROFILE_SLUG={profile.get('profile','')}")
        for k in (profile.get('default_metadata') or {}):
            print(f"DEFAULT_META_KEY={k}")
        break
else:
    print("REPO_PROFILE=")
PY
```

Read the output and skip the corresponding flags.

> **Walk-up semantics — closest wins.** If multiple ancestors have a `.dailybot/profile.json` (rare but legal), the one closest to `$PWD` wins. The CLI itself follows the same rule, so anything you would have done by hand is what `dailybot` will do at run time.

---

## Worked example

A repo at `/workspace` ships:

```json
{
  "name": "CLI",
  "default_metadata": { "repo": "cli" }
}
```

An agent wants to send a Dailybot report from `/workspace/some/subdir`. **Wrong** (overrides the profile silently):

```bash
dailybot agent update "..." \
  --name "Claude (Cursor)" \
  --metadata '{"model":"claude-opus-4-7","repo":"cli"}'
```

Why wrong: `--name "Claude (Cursor)"` silently overrides `"CLI"` from the profile. `"repo":"cli"` in `--metadata` is redundant (the profile already merges it) but not harmful.

**Right** (respects the profile):

```bash
dailybot agent update "..." \
  --metadata '{"model":"claude-opus-4-7"}'
```

Why right: no `--name`, so the profile's `"CLI"` wins. `--metadata` only carries keys the profile does **not** set (`model`); the CLI shallow-merges the profile's `default_metadata.repo` automatically. The outgoing report carries `name="CLI"`, `metadata={"repo":"cli","model":"claude-opus-4-7"}`.

---

## Why a repo profile exists

`.dailybot/profile.json` is the **team's contract** for how agents should identify themselves inside a given codebase. It is:

- **Committed to git** (visible to every team member and every CI agent)
- **Credential-free by design** — `.dailybot/profile.json` MUST NOT contain a `key` field; if it does, the CLI hard-errors. Secrets live only in `~/.config/dailybot/credentials.json` or `~/.config/dailybot/agents.json` on the developer's machine.
- **Authoritative** — it's how the repo owner says *"reports from this codebase should appear as `<name>` with metadata `<defaults>` no matter which agent / which laptop / which CI runner issued them"*. Honouring it is how that contract is kept.

Ignoring it via a flag override defeats the whole point.

---

## Sub-skill responsibilities

Every sub-skill that invokes `dailybot agent <verb>` (or any `dailybot` subcommand that consumes the agent identity) **must**:

1. Run this pre-flight on first use within a turn.
2. Drop `--name`, `--profile`, and the relevant `--metadata` keys from the constructed command according to the table above.
3. If the sub-skill's example commands show those flags (for readability / pedagogical reasons), they must be accompanied by an explicit "omit these if a repo profile sets them — see [`shared/repo-profile.md`](./repo-profile.md)" note.

This applies to: `dailybot-report`, `dailybot-chat`, `dailybot-kudos`, `dailybot-email`, `dailybot-forms`, `dailybot-checkin`, `dailybot-teams`, `dailybot-health`, `dailybot-messages`. (Everything in the pack.)

---

## What about `.dailybot/` files other than `profile.json`?

Since CLI **3.7.0**, `.dailybot/` also supports an **opt-in, gitignored** file called `env.json` that carries per-repo API keys + URLs for one or more environments. It is orthogonal to `profile.json` — different purpose, different lifecycle, different security posture:

| File | Committed? | Purpose |
|---|---|---|
| `.dailybot/profile.json` | **Yes** (tracked) | *Identity* — how reports get signed (team-shared) |
| `.dailybot/env.json` | **No** (gitignored) | *Auth context* — which org the CLI talks to (per-developer) |

If the developer asks about per-repo API keys, staging/local dev orgs, or "logging into different orgs in different repos", route them to [`shared/env-json.md`](env-json.md) instead — that file has the full workflow, security rules, and CLI commands.

Do **not** attempt to read `env.json` directly (`cat` etc.) from an agent context — it contains API keys. Use `dailybot env show` / `dailybot env list`, which mask them automatically.

Any other file you find in `.dailybot/` is out of scope for this skill pack — leave it alone.

---

## See also

- [`shared/auth.md`](./auth.md) — full authentication / profile resolution model (Bearer token, API key, profile slug, env var).
- [`shared/env-json.md`](./env-json.md) — the sibling `env.json` file (per-repo API keys + URLs, gitignored, CLI 3.7.0+).
- [CLI auth-resolution order](https://github.com/DailybotHQ/cli/blob/main/AGENTS.md#14-auth-resolution-order-do-not-break) — the per-field precedence the CLI implements (this doc is the agent-side mirror).
- [CLI configuration reference](https://github.com/DailybotHQ/cli/blob/main/docs/CONFIGURATION.md) — the full `.dailybot/profile.json` schema, security rules, and migration notes.
