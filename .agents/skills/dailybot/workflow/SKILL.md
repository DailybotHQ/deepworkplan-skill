---
name: dailybot-workflow
description: List and inspect Dailybot workflows (read-only) — enumerate the workflows configured for the organization and read one workflow's configuration. Use when the developer asks "list my workflows", "show workflows", or "what's in the release workflow?". Writes are done in the Dailybot web app; this skill only reads. Plan-gated feature.
version: "3.10.3"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"🔀","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Workflows (read-only)

> **Requires `dailybot-cli >= 3.7.0`** (the skill-pack baseline). The `dailybot workflow list` /
> `dailybot workflow get` command group is available. If
> `dailybot --version` reports below 3.7.0, ask the developer to run
> `dailybot upgrade`. See [`../SKILL.md` § Required Dailybot CLI version](../SKILL.md#required-dailybot-cli-version)
> for install commands and version-check tooling.

You help developers **read** the workflows configured for their organization.
Workflows are Dailybot's automation objects (multi-step sequences that connect
check-ins, forms, and chat actions). This skill is **read-only** — it lists
workflows and reads one workflow's configuration so an agent can reference or
explain them.

> **Writes are web-app only.** Creating, editing, enabling, or deleting a
> workflow is done in the Dailybot web app — there is **no** CLI write path.
> Do not attempt to mutate a workflow from the CLI; if the developer wants to
> change one, point them at the Dailybot web app.

> **Plan-gated feature.** Workflows are available on higher-tier plans. On a
> plan without them (and on the FREE plan generally) these reads return
> `403 plan_upgrade_required` with an `upgrade_url` — surface the upgrade path
> and stop. See [`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md) § 6.

---

## Auth model — API key or login

Workflow reads accept **either** a Bearer login session (`dailybot login`)
**or** an org API key (`DAILYBOT_API_KEY`). Results are scoped to the acting
identity's permissions (the server resolves the API key's owner). See
[`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md) § 6
for the full API-key ↔ Bearer parity and plan-gating rules.

---

## When to Use

- "list my workflows", "show the org's workflows", "what workflows do we have?"
- "show me the release workflow", "what's configured in workflow X?"
- Another skill needs a workflow's UUID or its configuration for context.

Do **not** use this skill to *create* or *change* a workflow — that's a web-app
operation. And do not confuse it with **form workflow states** (the
`draft → review → released` states inside a single form) — those are managed in
[`../forms/SKILL.md`](../forms/SKILL.md). This skill is the org-level
**workflow** object.

---

## Step 1 — Verify Setup

Read and follow the authentication steps in [`../shared/auth.md`](../shared/auth.md).

Confirm at least one credential is present:

```bash
dailybot status --auth 2>&1
```

If auth fails or the developer declines, skip and continue with your primary task.

---

## Step 2 — List Workflows

```bash
dailybot workflow list --json
```

Returns the workflows visible to the caller in the standard pagination
envelope (`{count, next, previous, results}`), and prints a `Showing X of N`
footer in human mode.

### Query flags

`workflow list` accepts the **full shared list query flag set** — pagination
(`--page`, `--page-size`, `--all`, `--limit`), search (`--search` / `--grep`),
and date range (`--since`, `--until`, `--date`, `--last-week`, `--today`). The
complete flag table, defaults, and the envelope/footer contract live in
[`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md) —
read it once and don't duplicate the reasoning here.

```bash
# Everything (default — walks all pages):
dailybot workflow list --json

# Search by name, most recent first page only:
dailybot workflow list --search release --page-size 20 --json

# Fetch every page explicitly:
dailybot workflow list --all --json
```

---

## Step 3 — Inspect a Workflow

```bash
dailybot workflow get <workflow_uuid> --json
```

Returns the single workflow's full configuration. Treat the JSON as the source
of truth for "what does this workflow do?"; surface the relevant parts to the
developer rather than re-deriving them.

---

## Step 4 — Error Handling

Match on the structured `code` field, never the prose `detail`. The full
error-code table (including `plan_upgrade_required`, `insufficient_role`, and
the 429 back-off behavior) is in
[`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md) § 5.

Most likely codes for this skill:

- `plan_upgrade_required` (403, carries `upgrade_url`) — workflows aren't on the
  org's plan. Surface the upgrade link and stop.
- `insufficient_role` / `org_admin_required` (403) — the caller's role can't
  read workflows. Suggest an admin runs it.
- Not authenticated (401) — guide through `dailybot login`.

---

## Step 5 — HTTP Fallback (when CLI is unavailable)

See [`../shared/http-fallback.md`](../shared/http-fallback.md) for base
patterns. Workflow endpoints accept **either** Bearer token or `X-API-KEY`.

### List workflows

```bash
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  https://api.dailybot.com/v1/workflows/
```

### Get a single workflow

```bash
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  https://api.dailybot.com/v1/workflows/<workflow_uuid>/
```

---

## Step 6 — Confirm

- **Success** — surface the requested workflow(s) directly. If the count footer
  showed `X < N`, tell the developer the view is truncated and how to widen it.
- **Failure** — warn briefly. For `plan_upgrade_required`, name the plan gap and
  surface the `upgrade_url`.
- **Skipped** — say nothing.

---

## Non-Blocking Rule

Workflow reads must **never block your primary work**. If the CLI is missing,
auth fails, the feature isn't on the plan, the network is down, or any command
errors:

1. Warn the developer briefly.
2. Continue with the primary task.
3. Do not retry automatically.
4. Do not enter a diagnostic loop.

---

## Additional Resources

- [`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md) — list query flags, pagination envelope, error codes, plan gating
- [`../shared/auth.md`](../shared/auth.md) — authentication setup
- [`../shared/http-fallback.md`](../shared/http-fallback.md) — HTTP API fallback patterns
- **Live API spec:** `https://api.dailybot.com/api/swagger/`
- **Full agent API skill:** `https://www.dailybot.com/skill.md`
