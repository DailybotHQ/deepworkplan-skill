# Shared reference — list query flags, pagination, and machine-readable errors

> **Requires `dailybot-cli >= 3.7.0`** (the skill-pack baseline). Everything on this page — the shared
> list query flags, the `{count, next, previous, results}` pagination envelope,
> the `Showing X of N` footer, the machine-readable error `code` dispatch, and
> the API-key / Bearer parity + free-plan gating rules — is available at this
> floor. If `dailybot --version` is below 3.7.0, ask the developer to run
> `dailybot upgrade`.

This is the **single source of truth** for behavior shared across every
list-style Dailybot command. The sub-skills (`forms`, `kudos`, `workflow`,
`checkin`) link here instead of repeating it. Read it once per session and
cache the answer.

---

## 1. The list query flags

These flags are accepted by the list commands noted below. `--search` is also
accepted on `form responses` and `checkin history`, which additionally take
`--page` / `--page-size` / `--limit` (but **not** `--all` — on `form responses`
that flag already means "every author's responses", not "every page").

| Flag | Alias | Meaning |
|------|-------|---------|
| `--page N` | | Fetch page `N` (1-based). |
| `--page-size N` | | Items per page. **Max 100** — larger values are clamped client-side. Passing it alone returns that one page, not the whole list. |
| `--all` | | Fetch **every** page and concatenate the results. Mutually exclusive with `--limit`. |
| `--limit N` | | Stop after the first `N` items (across pages). Mutually exclusive with `--all`. |
| `--search TEXT` | `--grep TEXT` | Case-insensitive substring filter. **Max 256 chars** — longer queries are rejected client-side with an error before the request is made. |
| `--since YYYY-MM-DD` | | Start of a date range (inclusive). |
| `--until YYYY-MM-DD` | | End of a date range (inclusive). |
| `--date YYYY-MM-DD` | | A single day (shorthand for `--since D --until D`). |
| `--last-week` | | The previous calendar week (Monday–Sunday). |
| `--today` | | The current day. |

**Which commands take the full set:** `dailybot form list`,
`dailybot kudos list`, `dailybot kudos org`, `dailybot workflow list`.
**Paging (`--page` / `--page-size` / `--limit`) + `--search`, but no `--all`:**
`dailybot form responses`, `dailybot checkin history`. Both also take their own
date flags (`--from` / `--to`, and `--days` on `checkin history`).

### Defaults and combinations

- **No flags → fetch everything.** With neither `--all`, `--limit`, nor
  `--page`, the CLI transparently walks all pages and returns the full set.
- **`--all` and `--limit` are mutually exclusive** — passing both is a
  client-side error.
- `--page` / `--page-size` fetch **one** explicit page; combine them to page
  manually.
- Date flags compose with `--search` (e.g. `--search retro --since 2026-07-01`).
- `--date`, `--last-week`, and `--today` are conveniences that expand into a
  `--since`/`--until` range for you.

---

## 2. The pagination envelope

Every list endpoint returns a standard envelope:

```json
{
  "count": 137,
  "next": "https://api.dailybot.com/v1/forms/?page=3",
  "previous": "https://api.dailybot.com/v1/forms/?page=1",
  "results": [ ... ]
}
```

- `count` — total items matching the query (across all pages).
- `next` / `previous` — absolute URLs to the adjacent pages, or `null` at the
  ends. The CLI follows `next` internally when you pass `--all` (or no paging
  flags).
- `results` — the items on the current page.

> **The envelope is unconditional.** Every `/v1` list endpoint returns the shape
> above with no opt-in parameter. HTTP-fallback callers can rely on it
> everywhere. Default page size is 25; `?page_size=N` raises it to at most 100.

---

## 3. The count footer

Every list command prints a `Showing X of N` footer (human output):

```
Showing 25 of 137
```

- `X` is how many rows were displayed this invocation (honoring `--limit` /
  `--page-size`); `N` is the envelope's `count`.
- When `X < N`, more items exist — re-run with `--all`, a larger `--page-size`,
  or the next `--page` to see them. Surface that to the developer so they know
  the view is truncated.
- In `--json` mode the footer is omitted; read `count` from the envelope
  instead.

---

## 4. Reading a resource's identifier — `uuid` or `id`

Resources do not agree on the name of their identifier field:

| Field | Resources |
|-------|-----------|
| `uuid` | forms, form responses, check-in responses, workflows, users, teams |
| `id` | kudos, check-ins (followups) |
| both (same value) | agent reports, agent messages, agent health |

**Always read `.uuid // .id`.** It is correct for every resource today and stays
correct as more of them migrate to `uuid`:

```bash
FID=$(dailybot form create -n "Release" --json | jq -r '.uuid // .id')
CID=$(dailybot checkin list --json | jq -r '.checkins[0].uuid // .checkins[0].id')
```

Do **not** hardcode `.id` for a form or a form response — that field no longer
exists there, and `jq -r '.id'` yields the string `null`, which then gets
interpolated into a URL as a literal `null`.

---

## 5. Machine-readable error codes

The CLI dispatches on a stable `code` field in the error body and
prints a friendly, actionable message. **Always match on `code`, never on the
human `detail` prose** — `detail` is display text and may change wording.

In `--json` mode the error surfaces as `{ error, status, code, detail }`.

### 403 — permission / plan gating

> **A `403` never means the session expired.** Only a `401` does. A `403` is a
> verdict about the caller's role or plan, and re-running `dailybot login` will
> reproduce it exactly. Read the `code` and tell the developer what they lack —
> a role, a plan, or membership in a scope.

| `code` | Meaning | What to do |
|--------|---------|------------|
| `plan_upgrade_required` | The feature isn't on the org's current plan. Carries an `upgrade_url`. | Tell the developer the feature needs a plan upgrade; surface the `upgrade_url`. Do not retry. |
| `plan_free_api_keys_forbidden` | API keys are fully blocked on the FREE plan. | Suggest `dailybot login` (a Bearer session) instead of an API key. |
| `plan_missing_core_api_integrations` | The org's plan lacks the core API integration this call needs. | Explain the integration/plan gap; do not retry. |
| `api_key_owner_inactive` | The API key's owning user is deactivated. | The key is unusable — have an admin reactivate the owner or issue a new key. |
| `insufficient_role` | The caller's role is below what the action requires. Carries the required and current role. | Name the required role; suggest an admin/manager runs it. |
| `member_in_scope_required` | The caller must be a member of the targeted scope (team/check-in/form). | Pick a scope the caller belongs to. |
| `org_admin_required` | The endpoint is org-admin only (e.g. `kudos org`, `chat send --send-as-user`, webhook/team-member management). | Only an org admin can run it — a member must ask an admin or use an admin API key. Not a session problem. |

### 400 — bad input

| `code` | Meaning | What to do |
|--------|---------|------------|
| `target_user_inactive` | The targeted user is deactivated. | Pick an active user. |
| `search_query_too_long` | `--search` exceeded the 256-char limit. | The query is rejected client-side before the request. If you hit this server-side, shorten the query. |
| `invalid_date_range` | `--since`/`--until` are malformed or reversed. | Fix the dates (`YYYY-MM-DD`, since ≤ until). |
| `invalid_user_identifier` | `--user` was given an email or a name. | `--user` takes **only a UUID**. Get it from `dailybot user list --json`. (Caught client-side before the request.) |
| `invalid_workflow_state` | On `form responses --state`: the form has no workflow. On `form create` / `form config --state`: the `"Label:#color"` spec is malformed. | Two meanings, one code — read which command you ran. For the filter, drop `--state` (or pick a workflow form). |
| `send_as_user_conflict` | `--send-as-user`/`--send-as-me` combined with `--bot-name`/`--bot-icon-*`. | Drop the custom-identity flags; the two are mutually exclusive. |
| `send_as_user_invalid_uuid` | `--send-as-user` value isn't a valid UUID. | Fix the UUID. (Caught client-side before the request.) |
| `send_as_user_not_found` | The `--send-as-user` UUID doesn't resolve to a user. | Confirm the user exists (`dailybot user list`). |
| `invalid_kudos_filter` | `kudos list --filter` got an unrecognized value. | Use `received` or `given` (the CLI also accepts `KUDOS_RECEIVED` / `KUDOS_GIVEN`). |
| `send_message_validation_error` | `chat send` payload is missing content or otherwise invalid. | Read the `detail` — it names the problem (e.g. no message/buttons/image). |
| `invalid_owner_user_id` | `--owner` value isn't a valid UUID (after resolution). | Fix the UUID or name. |
| `too_many_owner_user_ids` | More than 50 `--owner` values. | Narrow the filter — max 50 owners per request. |

### 429 — rate limit

| `code` | Meaning | What to do |
|--------|---------|------------|
| `free_plan_daily_limit_exceeded` | A FREE-plan daily allowance is exhausted. | **Do not retry** — it resets tomorrow. Tell the developer. |
| *(generic 429, no code)* | Per-token throttle. | The CLI backs off with a **bounded** retry automatically; don't add your own tight retry loop. |

---

## 6. Auth model — API key ↔ Bearer parity, and plan gating

### Parity

`X-API-KEY` (an org API key) works on **every** `/v1/` endpoint **except**
`POST /v1/cli/auth/logout/`, which is Bearer-only. An API key and a login
Bearer session are otherwise **interchangeable** on user-scoped commands — the
server resolves the API key's owner and scopes the action to that identity.

### Free-plan gating

On a **FREE** plan the two credentials behave very differently:

- **API keys are fully blocked.** Any `X-API-KEY` call returns
  `403 plan_free_api_keys_forbidden` → route the developer to `dailybot login`.
- **Bearer sessions are allowed, but only for an allowlist** of endpoints on
  FREE:
  - agent reports (`50`/day),
  - `send-email` (`20`/day),
  - agent messages,
  - agent health,
  - agent register + claim,
  - `dailybot me`, `dailybot org`, and `dailybot status` / `dailybot checkin
    list` (both read `cli status` — today's pending check-ins).
- **Everything else on FREE** returns `403 plan_upgrade_required` with an
  `upgrade_url`. Surface the upgrade path and stop — do not retry.

Paid plans lift both restrictions (API keys work, the allowlist no longer
applies), subject to the usual role scoping.

---

## 7. Non-blocking rule

As with every Dailybot operation: if a list/read errors, warn briefly, honor
the `code`, and continue the primary task. Never retry in a tight loop —
especially on `free_plan_daily_limit_exceeded` (resets tomorrow) or
`plan_upgrade_required` (needs a plan change, not a retry).
