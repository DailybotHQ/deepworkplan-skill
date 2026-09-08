---
name: dailybot-featured
description: Manage private Featured stars via the Dailybot CLI — list, set, and batch feature/unfeature Forms, Automations, and Check-ins for the authenticated user. Use when the developer asks to star/unstar dashboards items or manage Featured state. Not for organization Labels (use dailybot-labels).
version: "3.13.0"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"⭐","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Featured

> **Requires `dailybot-cli >= 3.9.0`** with `dailybot featured …` commands. If missing, ask the developer to run `dailybot upgrade`.

**Featured** is private per-user personalization — star Forms, Automations, or Check-ins so they surface first in your dashboards. Not gated by paid Labels.

## When to Use

- List which entities the user has starred
- Star or unstar one entity
- Batch feature/unfeature after bulk selection

Entity types: `forms`, `automations`, `checkins`.

## Step 1 — Verify Setup

Read [`../shared/auth.md`](../shared/auth.md). Featured requires a user-scoped session or API key.

## Step 2 — Common commands

```bash
dailybot featured list --entity-type forms
dailybot featured set <entity_uuid> --entity-type checkins
dailybot featured set <entity_uuid> --entity-type automations --unfeatured
dailybot featured batch --entity-type forms --uuids uuid-1,uuid-2
```

Add `--json` for machine-readable output.

## Step 3 — HTTP fallback

```bash
curl "https://api.dailybot.com/v1/me/featured/?entity_type=forms" \
  -H "Authorization: Bearer $DAILYBOT_CLI_TOKEN"
```

See [`../shared/http-fallback.md`](../shared/http-fallback.md).

## Non-Blocking Rule

If auth fails, warn briefly and continue the primary task.
