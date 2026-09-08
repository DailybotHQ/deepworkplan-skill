---
name: dailybot-workflow
description: List, inspect, and trigger Dailybot workflows — enumerate the workflows configured for the organization, read one workflow's configuration, and fire API-triggerable workflows on demand. Use when the developer asks "list my workflows", "show workflows", "what's in the release workflow?", "trigger the deploy workflow", or "fire automation X". Creating/editing workflows is done in the Dailybot web app. Plan-gated feature.
version: "3.13.0"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"🔀","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Workflows

> **Requires `dailybot-cli >= 3.9.0`** (the skill-pack baseline). The
> `dailybot workflow list` / `get` / `trigger` command group — including
> `--filter api_trigger` and `--payload` — is available at this floor. If
> `dailybot --version` reports below 3.9.0, ask the developer to run
> `dailybot upgrade`. See [`../SKILL.md` § Required Dailybot CLI
> version](../SKILL.md#required-dailybot-cli-version) for install commands and
> version-check tooling.

You help developers **read** and **trigger** the workflows configured for
their organization. Workflows are Dailybot's automation objects (multi-step
sequences that connect check-ins, forms, and chat actions).

- **List / Get** — enumerate workflows and inspect their configuration.
- **Trigger** — fire an API-triggerable workflow on demand, optionally with a
  JSON payload that the workflow can reference as `{{trigger.body.*}}`.

> **Creating / editing workflows is web-app only.** There is no CLI path for
> creating, editing, enabling, or deleting a workflow. If the developer wants
> to change one, point them at the Dailybot web app.

> **Plan-gated feature.** Workflows are available on higher-tier plans. On a
> plan without them (and on the FREE plan generally) these operations return
> `403 plan_upgrade_required` with an `upgrade_url` — surface the upgrade path
> and stop. See [`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md) § 6.

---

## Auth model — API key or login

Workflow commands accept **either** a Bearer login session (`dailybot login`)
**or** an org API key (`DAILYBOT_API_KEY`). Results are scoped to the acting
identity's permissions (the server resolves the API key's owner). See
[`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md) § 6
for the full API-key ↔ Bearer parity and plan-gating rules.

---

## When to Use

**List / inspect:**
- "list my workflows", "show the org's workflows", "what workflows do we have?"
- "show me the release workflow", "what's configured in workflow X?"
- Another skill needs a workflow's UUID or its configuration for context.

**Trigger:**
- "trigger the deploy workflow", "fire automation X", "run the onboarding workflow"
- "trigger workflow `<uuid>` with this payload"
- A chat button with `callback_workflow` fires the same path — see
  [`../chat/SKILL.md`](../chat/SKILL.md) § Workflow trigger buttons.

Do **not** use this skill to *create* or *change* a workflow — that's a web-app
operation. And do not confuse it with **form workflow states** (the
`draft → review → released` states inside a single form) — those are managed in
[`../forms/SKILL.md`](../forms/SKILL.md). This skill is the org-level
**workflow** object.

To **tag** an existing workflow with organization Labels after you have its
UUID from `workflow list`, use [`../labels/SKILL.md`](../labels/SKILL.md)
(`dailybot label assign <uuid> --type workflows` — `automations` is an alias).

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

# Filter to only API-triggerable workflows (client-side filter):
dailybot workflow list --filter api_trigger --json
```

The `--filter api_trigger` flag is a client-side convenience — it returns only
workflows whose event type is `api_trigger` ("When triggered via API or
button"), i.e. the workflows you can fire from `workflow trigger` or from a
chat button's `callback_workflow`.

---

## Step 3 — Inspect a Workflow

```bash
dailybot workflow get <workflow_uuid> --json
```

Returns the single workflow's full configuration. Treat the JSON as the source
of truth for "what does this workflow do?"; surface the relevant parts to the
developer rather than re-deriving them.

---

## Step 4 — Trigger a Workflow

> **Only `api_trigger` workflows can be triggered.** Workflows with other event
> types (schedule, form submission, etc.) are not triggerable from the CLI —
> the server returns `workflow_not_triggerable`.

> **Confirm before triggering.** `workflow trigger` is side-effecting — it can
> start a deploy or other automation and enqueues a run. Restate the target
> workflow (name + UUID) and the payload (or "no payload") to the developer and
> wait for an explicit yes before running the command. Do not fire workflows
> unprompted. Same confirm-before-write posture as chat button sends.

```bash
dailybot workflow trigger <workflow_uuid> --json
```

### With a JSON payload

The optional `--payload` flag passes a JSON object (≤8 KiB) that the workflow
can reference in its steps as `{{trigger.body.<key>}}`:

```bash
dailybot workflow trigger <workflow_uuid> \
  --payload '{"version": "v2.5", "environment": "production"}' --json
```

### Trigger behavior

- **Success** returns HTTP `202` — the workflow run is **queued**, not
  synchronous. There is no run output in the response; the workflow executes
  asynchronously on the server.
- The payload must be a valid JSON object (not an array or scalar). Payloads
  over 8 KiB are rejected with `workflow_trigger_payload_invalid`.
- The caller must have permission to execute workflows. If not,
  `workflow_execute_not_allowed` is returned.
- A frozen (disabled) workflow returns `workflow_frozen`.
- An unknown UUID returns `404`.

### CLI flag cheat sheet

| Flag | Description |
|------|-------------|
| `<uuid>` | Workflow UUID (positional, required) |
| `--payload` | JSON object payload (≤8 KiB); available to the workflow as `{{trigger.body.*}}` |
| `--json` | Emit the raw API response as JSON to stdout |

### Cross-reference: chat buttons

Chat messages can include buttons that trigger workflows on click via the
`callback_workflow` field (or the `--workflow-button` shorthand). This uses the
same server-side trigger mechanism — see
[`../chat/SKILL.md`](../chat/SKILL.md) § Workflow trigger buttons.

---

## Step 5 — Error Handling

Match on the structured `code` field, never the prose `detail`. The full
error-code table (including `plan_upgrade_required`, `insufficient_role`, and
the 429 back-off behavior) is in
[`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md) § 5.

### List / Get errors

- `plan_upgrade_required` (403, carries `upgrade_url`) — workflows aren't on the
  org's plan. Surface the upgrade link and stop.
- `insufficient_role` / `org_admin_required` (403) — the caller's role can't
  read workflows. Suggest an admin runs it.
- Not authenticated (401) — guide through `dailybot login`.

### Trigger errors

| Status | Code | Meaning | Agent behavior |
|--------|------|---------|----------------|
| `202`  |  | Queued — the workflow run is enqueued | Surface success; note the run is async (no output). |
| `400`  | `workflow_not_triggerable` | The workflow's event type is not `api_trigger` | Only `api_trigger` workflows can be triggered. Use `workflow list --filter api_trigger` to find eligible ones. |
| `400`  | `workflow_trigger_payload_invalid` | Payload is not a valid JSON object, or exceeds 8 KiB | Fix the payload — must be a JSON object ≤8 KiB. |
| `403`  | `workflow_execute_not_allowed` | The caller doesn't have permission to execute workflows | An admin or a user with execute permission must run it. |
| `403`  | `workflow_frozen` | The workflow is disabled (frozen) | Tell the developer; the workflow must be re-enabled in the web app. |
| `404`  |  | Workflow UUID not found | Verify the UUID (`dailybot workflow list`). |

---

## Step 6 — HTTP Fallback (when CLI is unavailable)

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

### Trigger a workflow

```bash
curl -s -X POST \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"version": "v2.5"}}' \
  https://api.dailybot.com/v1/workflows/<workflow_uuid>/trigger/
```

The `payload` field is optional. On success, the response is `202` with a
confirmation body. The workflow run is asynchronous.

---

## Step 7 — Confirm

- **List success** — surface the requested workflow(s) directly. If the count footer
  showed `X < N`, tell the developer the view is truncated and how to widen it.
- **Trigger success** — confirm the workflow was queued:
  > *"Workflow `<uuid>` triggered (queued). The run executes asynchronously — there is no output to wait for."*
- **Failure** — warn briefly. For `plan_upgrade_required`, name the plan gap and
  surface the `upgrade_url`. For `workflow_not_triggerable`, explain that only
  `api_trigger` workflows can be fired.
- **Skipped** — say nothing.

---

## Non-Blocking Rule

Workflow operations must **never block your primary work**. If the CLI is missing,
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
- [`../chat/SKILL.md`](../chat/SKILL.md) — chat buttons can trigger workflows via `callback_workflow`
- **Live API spec:** `https://api.dailybot.com/api/swagger/`
- **Full agent API skill:** `https://www.dailybot.com/skill.md`
