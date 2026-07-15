---
name: dailybot-conversation
description: Open (or idempotently reuse) a private Slack group DM (MPIM) that includes the Dailybot bot, then optionally post a message or report to it. Use when the developer wants to start a Slack group with specific teammates plus the bot — e.g. "open a group DM with Jane and Bob and send them the analysis report". Slack only, org-admin only. Distinct from dailybot-chat (which posts to existing channels/DMs) and dailybot-channels (which discovers report-channel UUIDs).
version: "3.10.3"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"👥","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Conversations

> **Requires `dailybot-cli >= 3.7.0`** (the skill-pack baseline; the
> `dailybot conversation open` command itself shipped in 3.2.0). If
> `dailybot --version` reports lower, ask the developer to run
> `dailybot upgrade` and continue with your primary task meanwhile. See
> [`../SKILL.md` § Required Dailybot CLI version](../SKILL.md#required-dailybot-cli-version).

You help developers **open a private Slack group DM (MPIM)** that includes the
Dailybot bot plus one or more teammates, and — in the same step — optionally post
a message or report to that group. Opening is **idempotent**: the same set of
participants always returns the same channel, so "open it, or reuse the existing
one" is a single call. This is the natural first half of "start a group with Jane
and Bob and send them the report."

This is distinct from **`dailybot-chat`** (which sends to an *already-known*
channel, DM, or team) and from **`dailybot-channels`** (which lists report-channel
UUIDs for form/check-in authoring). If the developer already has a channel id and
just wants to post, route to **chat**. If they want to *create/obtain* a group of
people, start here.

---

## When to Use

- "Open a group DM with Jane and Bob" / "start a Slack group with the release team and the bot"
- "Open a group with `<user>` and send them this report / analysis / summary"
- "Get me a channel with these three people so the bot can post there"
- Any flow that needs a **group channel id** before posting — this command
  returns it (creating the group if needed, reusing it if it already exists)

Do **not** use this for posting to an existing channel/DM (→ **chat**), for
discovering report channels (→ **channels**), or on non-Slack orgs (the command
returns a clear "Slack only" error).

---

## Auth model & permissions

`POST /v1/open-conversation/` accepts **either** an org API key (`X-API-KEY`) or a
login **Bearer** token (`dailybot login`) — the CLI prefers the API key and falls
back to the Bearer token, the same header logic as `chat send`. Two server-enforced
gates:

| Gate | Rule | On failure |
|------|------|------------|
| **Platform** | Slack only | `406 open_conversation_not_supported` → "Group conversations are only supported for Slack workspaces." |
| **Role** | Organization admin only | `403` → "This command requires organization admin privileges." |

Never re-implement these checks client-side; surface the server's decision and
fall back to the non-blocking rule.

---

## Step 1 — Verify Setup

Follow [`../shared/auth.md`](../shared/auth.md), then confirm a credential exists:

```bash
dailybot status --auth >/dev/null 2>&1 || { echo "Run: dailybot login"; exit 3; }
```

If auth fails or the developer declines, skip and continue your primary task.

---

## Step 2 — Resolve the Participants

Participants can be named three ways — the CLI resolves them for you:

| You pass | Flag | Resolution |
|----------|------|------------|
| A user UUID | `-u <uuid>` | used as-is (no directory lookup) |
| An email | `-e me@example.com` or `-u me@example.com` | resolved via `GET /v1/users/` |
| A name | `-u "Jane Doe"` | resolved via `GET /v1/users/` (unique match required) |

- `--user` / `-u` (alias `--users`) and `--email` / `-e` (alias `--emails`) are
  both **repeatable** and accept **comma-separated** values.
- The org directory is fetched **only** when at least one identifier is not a bare
  UUID, so an all-UUID call skips the extra round-trip.
- Duplicates are dropped (first occurrence wins); order is preserved.
- Email/name resolution needs the directory to expose that person — email lookup is
  admin/manager-gated server-side. If a name is ambiguous, the CLI lists the
  matches so you can disambiguate. When unsure who the developer means, confirm
  before opening the group.

> The bot is added automatically — you do **not** pass the bot as a participant.
> One human participant already makes a valid group with the bot.

### Participant limit

Slack group DMs (MPIMs) support **at most 8 total members**. The Dailybot bot
always occupies one slot, so you can pass **at most 7 user UUIDs / emails /
names**. The CLI rejects more than 7 before making the API call; the server also
validates and returns `400 conversation_too_many_participants` if the limit is
exceeded.

---

## Step 3 — Open the Conversation (idempotent)

```bash
# By UUID (no directory lookup)
dailybot conversation open -u <uuid1> -u <uuid2>

# By name / email (resolved via the org directory)
dailybot conversation open -u "Jane Doe" -u bob@example.com

# Headless: capture the channel id for scripting / a follow-up send
CH=$(dailybot conversation open -u <uuid1> -u <uuid2> --json | jq -r .channel)
```

The response is `{ "channel": "<slack-conversation-id>" }` (human output shows a
panel with the channel + participant names). **Idempotent** — calling again with
the same participants returns the *same* channel, so you never create duplicates.

### `--json` shape

```json
{
  "channel": "<slack-conversation-id>",
  "participants": [
    {"uuid": "<uuid1>", "name": "Jane Doe"},
    {"uuid": "<uuid2>", "name": "Bob Stone"}
  ],
  "message_sent": false
}
```

> When all participants were given as bare UUIDs, `name` echoes the UUID (the
> directory lookup was skipped). Pass names/emails if you want resolved display
> names in the output.

---

## Step 4 — Open **and** post a report in one call

Add `-m/--message` to post to the freshly opened group immediately. The CLI chains
a `POST /v1/send-message/` with `channel_type: "group_chat"` (the same delivery
path as `dailybot chat send`).

```bash
dailybot conversation open -u "Jane Doe" -u bob@example.com \
  -m "Report on the latest analysis — summary in this message, details to follow."
```

This is the whole "open a group with X and Y and send them the report" flow in a
single command. `--json` then reports `"message_sent": true`.

> **Markdown rules for the message.** The message renders with the same
> constrained Markdown subset as chat messages — one `#` heading level, real `\n`
> newlines, `**bold**` / `*italic*` / `` `code` `` / links / lists / tables. See
> the **Markdown Content Rules** in [`../chat/SKILL.md`](../chat/SKILL.md) and
> [`../forms/SKILL.md`](../forms/SKILL.md) before composing a longer report.
>
> For richer sends (threads, buttons, custom bot identity), open the group here to
> get the channel id, then use **[`../chat/SKILL.md`](../chat/SKILL.md)** with
> `--channel <id> --channel-type group_chat` — chat owns the full messaging surface.

---

## Step 5 — Error Handling

Match on the machine-readable `code` (with `--json`), never the prose `detail`.

| HTTP | `code` | Meaning / agent action |
|------|--------|------------------------|
| 406 | `open_conversation_not_supported` | Org is not on Slack. Tell the developer group DMs are Slack-only; stop. |
| 403 | — | Caller is not an org admin. Explain the command needs admin rights. |
| 400 | `conversation_too_many_participants` | More than 7 users passed (8 total including the bot). Reduce the list. |
| 400 | `one_or_more_users_not_found` | A participant isn't an active org user. Re-check the names/UUIDs. |
| 400 | `no_valid_users` | The list contained invalid UUIDs. Fix the identifiers. |
| 400 | `params_validation_error` | `users_uuids` wasn't a list — a CLI usage error; re-run with `-u`. |
| 409 | `conversation_can_not_be_opened` | Slack rejected it (a participant may be deactivated on the Slack side). Surface and stop. |
| 401 | — | Not authenticated. Guide through `dailybot login`. |
| 429 | — | Rate limited. Do not retry in a tight loop. |

The CLI already translates these to friendly messages and exits non-zero; when a
body has no `code` (network / gateway error), warn briefly and fall back to the
non-blocking rule.

---

## Step 6 — HTTP Fallback (CLI unavailable)

`POST /v1/open-conversation/` accepts **either** `X-API-KEY` or
`Authorization: Bearer`. See [`../shared/http-fallback.md`](../shared/http-fallback.md)
for base patterns.

```bash
# Open (or fetch) the group — returns {"channel": "<id>"}
curl -s -X POST https://api.dailybot.com/v1/open-conversation/ \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"users_uuids":["<uuid1>","<uuid2>"]}'

# Post to the returned group channel (note channel_type=group_chat)
curl -s -X POST https://api.dailybot.com/v1/send-message/ \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Report on the latest analysis…",
       "target_channels":[{"id":"<channel-id>","channel_type":"group_chat"}]}'
```

---

## Step 7 — Confirm

- **Success** — confirm the channel is ready (and that the message was posted, if
  `-m` was used). Example: *"Opened a group DM with Jane and Bob — the bot is in it
  and your report is posted."*
- **Failure** — warn briefly and map the `code` to the action in Step 5.
- **Skipped** — say nothing.

---

## Non-Blocking Rule

Conversation operations must **never block the developer's primary work**. If the
CLI is missing, auth fails, the org isn't on Slack, the caller isn't an admin, or
any command errors: warn briefly, continue the primary task, do not retry
automatically, and do not enter a diagnostic loop.

---

## Additional Resources

- [`../chat/SKILL.md`](../chat/SKILL.md) — full messaging surface (threads, buttons, identity); use with `--channel-type group_chat` to post to a group you opened here
- [`../teams/SKILL.md`](../teams/SKILL.md) — resolve a person's UUID by name
- [`../shared/auth.md`](../shared/auth.md) — authentication setup
- [`../shared/http-fallback.md`](../shared/http-fallback.md) — HTTP API fallback patterns
- [`../shared/dashboard-urls.md`](../shared/dashboard-urls.md) — full dashboard URL catalog
- **Full agent API skill:** `https://www.dailybot.com/skill.md`
