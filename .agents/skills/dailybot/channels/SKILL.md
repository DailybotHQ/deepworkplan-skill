---
name: dailybot-channels
description: Discover the report channels (Slack/Teams/Discord/Google Chat) available to you via Dailybot, so their UUIDs can be attached to forms and check-ins with --report-channel. Use when the developer needs a channel UUID for form/check-in authoring.
version: "3.10.3"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"📣","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Report Channels

> **Requires `dailybot-cli >= 3.7.0`** (the skill-pack baseline). The `dailybot channels list`
> command is available at this floor. If `dailybot --version` reports below
> 3.7.0, ask the developer to run `dailybot upgrade`. See
> [`../SKILL.md` § Required Dailybot CLI version](../SKILL.md#required-dailybot-cli-version).

Report channels are the Slack / Microsoft Teams / Discord / Google Chat
destinations where Dailybot posts form and check-in reports. This sub-skill lists
the channels available to you so their UUIDs can be attached to a form or check-in
with `--report-channel` during authoring.

## Auth model — API key or login

Works under a login session (Bearer) **or** an org API key (`DAILYBOT_API_KEY`).
Visibility is role-scoped server-side; the CLI never client-filters.

## When to Use

- The developer is **authoring** a form or check-in (see
  [`../forms/SKILL.md`](../forms/SKILL.md) § Authoring and
  [`../checkin/SKILL.md`](../checkin/SKILL.md) § Authoring) and needs a channel
  UUID for `--report-channel`.
- The developer asks "which channels can Dailybot post to?".

Do **not** use this to *send* a message to a channel — that's `dailybot-chat`.

## Step 1 — List channels

```bash
# Human-readable table
dailybot channels list

# Machine-readable (recommended for agents)
dailybot channels list --json
```

JSON shape:

```json
[
  {"uuid": "abc123-def456", "name": "#engineering", "platform": "slack", "channel_id": "C0123ABCDEF"}
]
```

## Step 2 — Use a channel UUID in authoring

```bash
dailybot form create -n "Sprint Retro" --report-channel abc123-def456
dailybot checkin config <followup_uuid> --report-channel abc123-def456
```

`--report-channel` is repeatable to attach multiple channels.

## Non-Blocking Rule

If the CLI is unavailable or unauthenticated, surface the issue once and continue;
never block work on channel discovery. The HTTP fallback is
`GET /v1/report-channels/` (see [`../shared/http-fallback.md`](../shared/http-fallback.md)).

## Additional Resources

- [`../forms/SKILL.md`](../forms/SKILL.md) — forms authoring
- [`../checkin/SKILL.md`](../checkin/SKILL.md) — check-in authoring
- [`../SKILL.md`](../SKILL.md) — router + version floors
