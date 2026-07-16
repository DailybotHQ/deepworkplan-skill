# Dailybot HTTP API Fallback

Use this path when the Dailybot CLI is unavailable (sandboxed environments, CI containers, or when the developer can't install it). Requires `curl`.

**Base URL:** `https://api.dailybot.com`
**Auth header:** `X-API-KEY: $DAILYBOT_API_KEY`

The `DAILYBOT_API_KEY` environment variable must be set. If it's not, ask the developer to generate a key at **Dailybot → Settings → API Keys** and set it:

```bash
export DAILYBOT_API_KEY="<their-key>"
```

---

## Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/v1/agent-reports/` | Submit an activity report |
| `POST` | `/v1/agent-health/` | Health check + receive pending messages |
| `GET` | `/v1/agent-health/?agent_name=<n>` | Retrieve last health status |
| `GET` | `/v1/agent-messages/?agent_name=<n>&delivered=false` | Poll for undelivered messages |
| `POST` | `/v1/agent-email/send/` | Send an email on behalf of your agent |
| `POST` | `/v1/send-message/` | Send / edit a bot chat message (DM, channel, team). Accepts `X-API-KEY` **or** `Authorization: Bearer`. Targets `target_users` / `target_channels` / `target_teams`; optional `thread_responses[]` (≤10) posts replies in the parent's thread in the same call; passing `bot_message_id` edits that message (parent or reply). |

---

## Common Patterns

### POST request template

```bash
curl -s -X POST https://api.dailybot.com/v1/<endpoint>/ \
  -H "X-API-KEY: $DAILYBOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '<json_payload>'
```

### GET request template

```bash
curl -s -X GET "https://api.dailybot.com/v1/<endpoint>/?<query_params>" \
  -H "X-API-KEY: $DAILYBOT_API_KEY"
```

---

## Error Handling

- **401 Unauthorized** — API key is invalid or expired. Ask the developer for a new key.
- **403 Forbidden** — API key doesn't have the required scope. Check key permissions.
- **429 Too Many Requests** — Rate limited. Slow down. Do not retry in a tight loop.
- **Network failure** — Warn briefly and continue with primary work. Do not enter a diagnostic loop.

All HTTP calls should be non-blocking. If a call fails, warn the developer and move on.

---

---

## User-Scoped Endpoints (Bearer Token Auth)

The user-scoped commands (`checkin`, `form`, `kudos`, `user`) use a **Bearer
token** instead of an API key. All other patterns (error handling,
non-blocking behavior) remain the same.

**Auth header:** `Authorization: Bearer $DAILYBOT_BEARER_TOKEN`

The Bearer token is obtained via the OTP login flow (see
[`auth.md`](auth.md) Section 4).

### Obtaining a Bearer token programmatically

```bash
# Step 1 — request OTP
curl -s -X POST https://api.dailybot.com/v1/cli/request-code/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'

# Step 2 — verify OTP (returns token)
curl -s -X POST https://api.dailybot.com/v1/cli/verify-code/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","code":"123456"}'
# → {"token":"<bearer-token>","organization":"Org Name"}
```

### User-Scoped Endpoint Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/v1/cli/status/` | List pending check-ins for the logged-in user |
| `POST` | `/v1/checkins/<followup_uuid>/responses/` | Complete a check-in |
| `GET` | `/v1/forms/?include=questions` | List forms with question definitions |
| `POST` | `/v1/forms/<form_uuid>/responses/` | Submit a form response |
| `GET` | `/v1/users/` | List organization members (paginated) |
| `POST` | `/v1/kudos/` | Give kudos to a teammate |

### Example requests

#### List pending check-ins

```bash
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  https://api.dailybot.com/v1/cli/status/
```

#### Complete a check-in

```bash
curl -s -X POST \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.dailybot.com/v1/checkins/<followup_uuid>/responses/ \
  -d '{
    "responses": [
      {"uuid": "<question-uuid>", "index": 0, "response": "Done"}
    ],
    "last_question_index": 0
  }'
```

#### List forms (with questions)

```bash
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  "https://api.dailybot.com/v1/forms/?include=questions"
```

#### Submit a form response

```bash
curl -s -X POST \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.dailybot.com/v1/forms/<form_uuid>/responses/ \
  -d '{"content": {"<question_uuid>": "My answer"}}'
```

#### List organization members

```bash
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  https://api.dailybot.com/v1/users/
```

Paginated — follow `next` URL until null (max 50 pages).

#### Give kudos

```bash
curl -s -X POST \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.dailybot.com/v1/kudos/ \
  -d '{"receivers": ["<user-uuid>"], "content": "Great work!"}'
```

### User-Scoped Error Handling

Same HTTP status codes as agent endpoints, plus:

| Code | Exit | Meaning |
|------|------|---------|
| `402` | `5` | Quota exhausted (form response limit) |
| `403` | `4` | Permission denied, self-kudos, or daily kudos limit |
| `406` | `4` | Daily kudos limit reached |
| `429` | `6` | Rate limited — 60 req/min |

---

## API Reference

Full API documentation: `https://api.dailybot.com/api/swagger/`
Full agent API skill: `https://www.dailybot.com/skill.md`
