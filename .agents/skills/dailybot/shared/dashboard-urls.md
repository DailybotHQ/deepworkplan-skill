# Shared reference — Dailybot dashboard URLs

> **Requires `dailybot-cli >= 3.7.0`** (the skill-pack baseline). The
> `--app-url` flag and `DAILYBOT_APP_URL` env var for configuring the dashboard
> base URL are available at this floor, as is the per-profile `app_url` in
> [`env-json.md`](env-json.md).

This is the **single source of truth** for all dashboard (webapp) URLs that
agents can embed in reports, messages, or surface to the developer. Sub-skills
link here instead of repeating route tables.

---

## 1. Base URL resolution

The dashboard base URL resolves in this order:

| Priority | Source | Example |
|----------|--------|---------|
| 1 | `--app-url` CLI flag | `dailybot --app-url http://localhost:8090 agent update …` |
| 2 | `DAILYBOT_APP_URL` env var | `export DAILYBOT_APP_URL=http://localhost:8090` |
| 3 | Default | `https://app.dailybot.com` |

For **local development**, set the env var or pass the flag:

```bash
export DAILYBOT_APP_URL=http://localhost:8090
```

> **Do not hardcode staging or dev URLs** in committed code, docs, or skill
> files. Use the env var or flag for non-production environments.

---

## 2. Route catalog

All paths below are relative to the base URL. Replace `{placeholders}` with
actual UUIDs/IDs from API responses. Routes marked `[fullscreen]` open a
standalone page (no sidebar navigation).

### Home

| Description | Path |
|-------------|------|
| Main home | `/home` |

### Forms

| Description | Path |
|-------------|------|
| Forms home | `/forms/home` |
| Responses list | `/forms/{form_uuid}/responses` |
| Response detail | `/forms/{form_uuid}/responses/{response_uuid}` |
| Create form — questions `[fullscreen]` | `/forms/create/form-questions` |
| Create form — setup `[fullscreen]` | `/forms/create` |
| Fill form (public) `[fullscreen]` | `/forms/{form_uuid}/responses/create/` |
| Edit response `[fullscreen]` | `/forms/{form_uuid}/responses/update/{response_uuid}` |

### Check-ins

| Description | Path |
|-------------|------|
| Check-ins home | `/checkins/home` |
| Daily report | `/checkins/{checkin_uuid}/daily-report` |
| Daily report (date) | `/checkins/{checkin_uuid}/daily-report/{YYYY-MM-DD}` |
| Activity | `/checkins/{checkin_uuid}/activity` |
| Submit response `[fullscreen]` | `/checkins/response-daily/{checkin_uuid}/add/{YYYY-MM-DD}` |
| Edit response `[fullscreen]` | `/checkins/response-daily/{checkin_uuid}/edit/{YYYY-MM-DD}` |
| Create check-in `[fullscreen]` | `/checkins/create` |
| Edit — questions `[fullscreen]` | `/checkins/edit/{checkin_uuid}/questions` |
| Edit — frequency `[fullscreen]` | `/checkins/edit/{checkin_uuid}/frequency` |
| Edit — participants `[fullscreen]` | `/checkins/edit/{checkin_uuid}/participants` |
| Edit — reporting `[fullscreen]` | `/checkins/edit/{checkin_uuid}/reporting` |

### Kudos

| Description | Path |
|-------------|------|
| Kudos home | `/kudos/home` |
| Wall of fame | `/kudos/wall-of-fame` |
| Team values | `/kudos/team-values` |
| Send kudo `[fullscreen]` | `/kudos/send` |
| Kudo detail `[fullscreen]` | `/kudos/detail/{kudo_id}` |
| Company value detail `[fullscreen]` | `/kudos/company-values/{value_id}` |

### Agents

| Description | Path |
|-------------|------|
| Agents home | `/agents/home` |
| Reports | `/agents/reports` |
| Messages | `/agents/messages` |
| Analytics | `/agents/analytics/{tab}` (`agents`, `coauthors`, `insights`) |
| Agent detail | `/agents/{agent_uuid}` |
| Report detail | `/agents/report/{report_id}` |
| Co-author detail | `/agents/co-author/{coauthor_uuid}` |

---

## 3. Building full URLs

Combine the base URL + path. When the API returns a `url` field (e.g. in
`POST /v1/agent-reports/` → `{"url": "https://app.dailybot.com/agents/report/123"}`),
**prefer the server-returned URL** — it already includes the correct host. Only
construct URLs manually when the API does not return one (e.g. linking to a
form's responses page or a check-in's daily report).

```python
# Example: construct a form responses URL
app_url = get_app_url()  # resolves --app-url > env > default
form_uuid = "abc-123"
url = f"{app_url}/forms/{form_uuid}/responses"
```

---

## 4. When to surface dashboard URLs

Agents should include dashboard links in reports and messages when:

- **After submitting a form response** — link to the response detail page
- **After giving kudos** — link to the kudo detail or wall of fame
- **In agent progress reports** — the `View:` line already shows the report URL
- **When the developer asks** to "see it in the dashboard" or "open it in the web"
- **In chat messages** — as clickable links (Slack/Teams render them as hyperlinks)

Do **not** surface dashboard URLs:
- When the developer is working offline or in a CI/headless context
- In error messages (errors should guide the user to CLI commands, not the web)
