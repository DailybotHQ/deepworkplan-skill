---
name: dailybot-labels
description: Manage organization Labels via the Dailybot CLI (dailybot-cli >= 3.9.0) — entitlement, list/search, create, update, archive, hard-delete, assign (web chip-picker parity) to forms / check-ins / workflows (automations), and bulk batch add/remove/replace. Use when the developer asks about org labels, tagging entities, label CRUD, or Labels entitlement. Not for private Featured stars (use dailybot-featured) or form-response workflow state names.
version: "3.13.0"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"🏷️","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Labels

> **Requires `dailybot-cli >= 3.9.0`** (pack baseline). That release ships the
> full `dailybot label` surface: `entitlement` / `list` / `get` / `create` /
> `update` / `archive` / `delete` / `assign` / `batch`. Confirm with
> `dailybot label assign --help`. If missing, ask the developer to run
> `dailybot upgrade` (or `pip install --upgrade 'dailybot-cli>=3.9.0'`).

Organization **Labels** are a **shared taxonomy** for Forms, Check-ins, and
Workflows (Automations) — the same chips on the web settings page and row
picker. They are **not** private Featured stars (`dailybot featured` →
[`../featured/SKILL.md`](../featured/SKILL.md)).

The web picker on a form / check-in / automation row is a **replace-set**.
Match that with `dailybot label assign`. Bulk add/remove/replace across many
entities uses `dailybot label batch`.

## When to Use

- List, search, or inspect organization Labels
- Create, update, archive, or hard-delete Labels (when entitled)
- Attach / replace / clear Labels on one form, check-in, or workflow
- Bulk add / remove / replace Labels on many entities
- Check Labels entitlement before building automations that depend on tags

Do **not** use for:

| Intent | Route instead |
|--------|----------------|
| Private per-user stars | [`dailybot-featured`](../featured/SKILL.md) |
| Form **response** workflow states named “labels” (Draft → Review → …) | [`dailybot-forms`](../forms/SKILL.md) transitions |
| Creating the form / check-in / workflow itself | forms / checkin / workflow skills — then come back here to assign |

## Auth

Same session as the rest of the CLI (`dailybot login` or `DAILYBOT_API_KEY` /
`.dailybot/env.json`). See [`../shared/auth.md`](../shared/auth.md).

Point at a non-prod API with the global flag when needed:

```bash
dailybot --api-url <your-api-url> label entitlement
# Example placeholder: https://staging-api.example.com
```

## Step 1 — Entitlement (always first)

Server entitlement is the **source of truth**. Do not assume Labels are (or
are not) a paid-only feature — plans differ.

```bash
dailybot status --auth 2>&1
dailybot label entitlement
dailybot label entitlement --json
```

JSON shape (stable fields):

```json
{
  "entitled": true,
  "feature": "LABELS",
  "reason": null,
  "is_guest": false,
  "can_create": true,
  "can_manage_all": true,
  "can_hard_delete": true,
  "can_manage": true
}
```

| Flag | Meaning |
|------|---------|
| `entitled` | Org may use Labels at all |
| `can_create` | Caller may create Labels |
| `can_manage_all` | Caller may edit/archive Labels they did not create |
| `can_hard_delete` | Caller may hard-delete (elevated; fails when Label is in use) |
| `is_guest` | Guest identity — usually cannot manage |

If `entitled` is `false`, warn briefly (`feature_not_available` /
`paid_plan_required`), surface any upgrade hint, and **continue the primary
task** without looping.

## Step 2 — List / search / get

```bash
dailybot label list
dailybot label list --search sprint --json
dailybot label list --archived --limit 50 --offset 0
dailybot label get <label-uuid>
dailybot label get <label-uuid> --json
```

| Flag | Notes |
|------|--------|
| `--search` | Case-insensitive name search |
| `--archived` | Include archived Labels |
| `--limit` / `--offset` | Pagination (limit default 20, max 100) |
| `--json` | Machine-readable `{count, results:[…]}` |

Copy UUIDs from `label list` / `--json` — assign/batch need Label UUIDs, not
names.

List rows include `usage` / `usage_count` (forms / automations / checkins).
Counters can lag briefly after assign; trust the assign/batch response and
`form list` / `workflow list` enrichment when verifying.

## Step 3 — Create / update

```bash
dailybot label create --name "Sprint" --color "#4A90E2"
dailybot label create --name "Release" --color "#2ECC71" --description "Release train" --json

dailybot label update <label-uuid> --name "Sprint 42" --color "#C0392B"
dailybot label update <label-uuid> --description "Updated copy"
# Clear description:
dailybot label update <label-uuid> --description ""
```

| Flag | Notes |
|------|--------|
| `--name` | Required on create; unique per org |
| `--color` | Hex, e.g. `#4A90E2` |
| `--description` | Optional; empty string on update clears it |
| `--json` | Prefer for scripting |

Duplicate names are rejected — pick another name or update the existing Label.

## Step 4 — Assign to one entity (web picker parity)

`assign` **replaces** the full set of Labels on that entity (same as the web
chip picker). Pass every Label that should remain.

```bash
# Forms
dailybot label assign <form-uuid> --type forms --label <label-uuid>
dailybot label assign <form-uuid> --type forms --label <uuid-a> --label <uuid-b>
dailybot label assign <form-uuid> --type forms --label <uuid-a>,<uuid-b>

# Check-ins (use the check-in UUID from create --json → .uuid or .id)
dailybot label assign <checkin-uuid> --type checkins --label <label-uuid>

# Workflows / Automations (same API; --type automations is an alias)
dailybot label assign <workflow-uuid> --type workflows --label <label-uuid>
dailybot label assign <workflow-uuid> --type automations --label <label-uuid>
```

Clear every Label on an entity:

```bash
dailybot label assign <form-uuid> --type forms --clear
```

| Flag | Notes |
|------|--------|
| `--type` | **Required.** `forms` \| `checkins` \| `workflows` (`automations` alias) |
| `--label` | Repeatable or comma-separated Label UUIDs (replace-set) |
| `--clear` | Replace with an empty set (mutually exclusive with attaching labels) |
| `--json` | Returns `{uuid, labels:[…]}` for the entity |

### After authoring forms / check-ins

`dailybot form create` and `dailybot checkin create` do **not** take
`--labels`. Create first, then assign:

```bash
# Forms expose .uuid
FID=$(dailybot form create -n "Retro" --questions-file q.json --active --json | jq -r '.uuid')
dailybot label assign "$FID" --type forms --label "$LABEL_UUID"

# Check-ins: prefer .uuid (CLI >= 3.9.x also aliases API `id` → `uuid` on --json)
CID=$(dailybot checkin create -n "Standup" --user <user-uuid> \
  --questions-file q.json --time 09:00 --days 1,2,3,4,5 --json | jq -r '.uuid // .id')
dailybot label assign "$CID" --type checkins --label "$LABEL_UUID"
```

Workflows are created in the web app only — list UUIDs with
`dailybot workflow list --json`, then `label assign --type workflows`.

### Verify on list APIs

```bash
dailybot form list --limit 20 --json | jq '.[] | {name, labels}'
# or paginated envelope: .results[]
dailybot workflow list --limit 20 --json | jq '.[] | {name, labels}'
```

`checkin show` may omit `labels` even when assign succeeded — use the assign
`--json` response or list enrichment where available.

## Step 5 — Batch (many entities)

```bash
dailybot label batch --type forms --uuids <uuid1>,<uuid2> --label <label-uuid> --mode add
dailybot label batch --type checkins --uuids <uuid> --label <label-uuid> --mode remove
dailybot label batch --type workflows --uuids <uuid1>,<uuid2> --label <l1>,<l2> --mode replace
dailybot label batch --type automations --uuids <uuid> --label <label-uuid> --mode add --json
```

| Flag | Notes |
|------|--------|
| `--type` | `forms` \| `checkins` \| `workflows` (`automations` alias) |
| `--uuids` | Comma-separated entity UUIDs (**required**, at least one) |
| `--label` | Repeatable or comma-separated Label UUIDs |
| `--mode` | `add` (default) \| `remove` \| `replace` |
| `--json` | `{mode, updated_count, entity_uuids, labels}` |

Use **batch** for bulk add/remove; use **assign** when the web picker
replace-set semantics for a single row matter.

## Step 6 — Archive / delete

```bash
# Soft-archive (idempotent). Archived Labels cannot be newly assigned
# (code: archived_label).
dailybot label archive <label-uuid>
dailybot label archive <label-uuid> --json

# Hard-delete — elevated only; fails when the Label is still attached
# (code: label_in_use).
dailybot label delete <label-uuid> -y
dailybot label delete <label-uuid> -y --json
```

If delete fails because the Label is in use (`label_in_use`): clear or
reassign entities (`label assign … --clear` / `label batch --mode remove`),
then delete again — or leave it archived.

## Worked end-to-end flow

```bash
# 0. Gate
dailybot label entitlement --json | jq '.entitled, .can_create'

# 1. Create taxonomy
L1=$(dailybot label create --name "Sprint" --color "#4A90E2" --json | jq -r '.uuid')
L2=$(dailybot label create --name "Platform" --color "#2ECC71" --json | jq -r '.uuid')

# 2. Author entities (questions required on create)
cat > /tmp/db-q.json <<'EOF'
[{"question": "What shipped?", "short_question": "Shipped", "question_type": "text"}]
EOF
FID=$(dailybot form create -n "Sprint Retro" --questions-file /tmp/db-q.json --active --json | jq -r '.uuid')
CID=$(dailybot checkin create -n "Daily Standup" --user <user-uuid> \
  --questions-file /tmp/db-q.json --time 09:00 --days 1,2,3,4,5 --json | jq -r '.uuid // .id')
WID=$(dailybot workflow list --limit 1 --json | jq -r 'if type=="array" then .[0].uuid else .results[0].uuid end')

# 3. Attach (replace-set on one row; batch for many)
dailybot label assign "$FID" --type forms --label "$L1" --label "$L2" --json
dailybot label assign "$CID" --type checkins --label "$L1" --json
[ -n "$WID" ] && dailybot label assign "$WID" --type workflows --label "$L2" --json
dailybot label batch --type forms --uuids "$FID" --label "$L1" --mode add --json

# 4. Inspect
dailybot label get "$L1" --json | jq '{name, usage, usage_count}'
dailybot form list --limit 5 --json | jq 'map({name, labels})'
```

## Error codes (match on `code`, never `detail`)

See also [`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md).

| `code` | HTTP | When | What to do |
|--------|------|------|------------|
| `feature_not_available` | 403 | Org not entitled to Labels | Stop Labels work; tell the developer; do not retry |
| `paid_plan_required` | 403 | Plan lacks Feature.LABELS | Surface upgrade path if present; do not retry |
| `guest_not_allowed` | 403 | Guest caller hit a Labels endpoint | Stop; Labels require a non-guest member |
| `permission_denied` | 403 | Caller lacks permission for this Labels action | Ask an admin/manager; do not retry blindly |
| `org_admin_required` / `insufficient_role` | 403 | Caller cannot manage/delete | Ask an admin/manager |
| `archived_label` | 400 | Assign/batch used an archived Label | Create a new Label or stop assigning that UUID; do not force |
| `invalid_color` | 400 | Create/update color is not valid hex | Fix `--color` (e.g. `#4A90E2`) |
| `label_limit_exceeded` | 400 | Assign/batch would exceed per-entity Label limit | Remove a Label first, then retry |
| `duplicate_name` | 409 | Label name already exists in the org | Pick another `--name` or update the existing UUID |
| `label_in_use` | 409 | Hard-delete while the Label still has attachments | Clear/reassign entities, then delete — or archive instead |
| `not_found` | 404 | Unknown Label or entity UUID | Verify UUID via `label list` / entity `list` |

Frozen public codes: [Errors](https://www.dailybot.com/developers/errors)
(Labels & personalization). Match on `code` from CLI `--json` (server value
forwarded unchanged).

A **403** is never “session expired” — only **401** is. Re-login will not
fix a plan/role 403.

## HTTP fallback

When the CLI is unavailable, call `/v1/labels/` and the per-entity assign
paths under `/v1/forms/…/labels/`, `/v1/checkins/…/labels/`, or
`/v1/workflows/…/labels/` with Bearer or `X-API-KEY`.
See [`../shared/http-fallback.md`](../shared/http-fallback.md) and
[Labels API docs](https://www.dailybot.com/developers/api/labels).

## Non-Blocking Rule

If auth fails or Labels are not entitled, warn once and continue the
developer's primary task. Never block coding work on Labels availability.
