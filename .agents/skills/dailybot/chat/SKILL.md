---
name: dailybot-chat
description: Send and edit Dailybot bot messages on the team's connected chat platform (Slack, Microsoft Teams, Discord, Google Chat) — to user DMs, channels, or whole teams. Supports report-style threads (one headline + replies, in one call), interactive buttons (approval flows, workflow triggers, modals, callbacks), and editing the parent or any reply afterward. Use when the developer says "send a message to my Slack channel", "ping the team in chat", "post the deploy report to #releases", "send an approval request with buttons", or wants to update a previously sent bot message. Works headless for agents.
version: "3.13.0"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"💬","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Chat

> **Requires `dailybot-cli >= 3.9.0`** (the skill-pack baseline). The
> `dailybot chat send` / `chat update` command group — including
> `--thread-message`, login-Bearer auth on `/v1/send-message/`,
> `--send-as-user` / `--send-as-me`, and the full interactive-button
> surface (`--buttons`, approval / workflow-button flags, modals,
> callbacks) — is available at this floor. If `dailybot --version` is
> below 3.9.0, ask the developer to run `dailybot upgrade`. See
> [`../SKILL.md` § Required Dailybot CLI version](../SKILL.md#required-dailybot-cli-version)
> for install commands and version-check tooling.

You send **Dailybot bot messages** on the developer's behalf to the organization's connected chat platform (Slack, Microsoft Teams, Discord, Google Chat) — to user DMs, channels, or whole teams (expanded to member DMs server-side). This skill is the right surface for:

- A short heads-up to a channel ("deploy started")
- A **report-style post**: a short headline in the channel + the full detail in **its thread**, in a single call (keeps the channel clean, groups the context, looks like a real human update)
- Pinging one or several teammates by DM
- Editing a previously sent message in place — including any individual thread reply

It is **not**:

- `dailybot-report` — that posts progress updates to the Dailybot dashboard (no Slack/Teams delivery by default).
- `dailybot-email` — that sends transactional email.
- `dailybot-messages` — that polls inbound agent-to-agent messages.

If the developer wants to "tell the team in Dailybot" generically, prefer `dailybot-report`. Route to `dailybot-chat` only when they explicitly mention chat / Slack / Teams / Discord / Google Chat, or a channel id / channel name, or want a message visible inside the chat tool itself.

---

## When to Use

Trigger phrases the agent should recognize:

**Send (channels / users / teams):**
- "send a Slack message to #releases", "post to channel C0123"
- "DM Carolina that the build is green", "ping Sergio Florez in chat"
- "broadcast this to the Engineering team in Slack"
- "post a deploy summary to #releases with the changelog as a thread"
- "send a chat message to the QA team"

**Interactive buttons / approvals:**
- "send an approval request with approve/reject buttons"
- "post a message with a button that triggers the deploy workflow"
- "send a message with interactive buttons to #releases"

**Edit / update a previous message:**
- "update the deploy message to say done"
- "edit that Slack message I just sent"
- "change the second thread reply to say rolled back"

**Do not** send chat messages autonomously without the developer's explicit request — chat messages are visible to other people and carry the developer's own identity (with a login session) or the bot identity (with an API key). Always confirm before sending unless the developer pre-approved a flow (`--yes`-style intent).

> **Need to create a Slack group of people first?** This sub-skill posts to an
> *already-known* target (channel id, DM, or team). To **open (or reuse) a Slack
> group DM with specific teammates + the bot** and get its channel id, use
> [`../conversation/SKILL.md`](../conversation/SKILL.md) (`dailybot conversation
> open`) — then come back here with `--channel <id> --channel-type group_chat` for
> any richer follow-up (threads, buttons, custom identity).

---

## Auth model — both login Bearer and org API key are supported

`POST /v1/send-message/` accepts either auth, and the CLI uses whichever is configured:

- **Login Bearer token** (`dailybot login` — preferred for human-driven sends): the message is delivered **as the logged-in user**, scoped by their role in their own org. Admins/managers reach anyone / any connected channel / any team; team members reach teammates, public channels, and teams they belong to; guests reach only themselves. Per-token CLI rate limits apply.
- **Organization API key** (`dailybot config key=...` or `DAILYBOT_API_KEY`): org-wide scope, not role-restricted, not per-token throttled — the canonical agent path.

The client picks the **API key first** if one is set, else falls back to the Bearer. The `update` call follows the same auth as `send`.

If the developer is unauthenticated, read [`../shared/auth.md`](../shared/auth.md) and surface either path. Do not push the developer to create an API key just to send one chat message — `dailybot login` is enough for a human.

---

## Step 1 — Verify Setup

Read and follow [`../shared/auth.md`](../shared/auth.md). It covers CLI installation, login (email OTP), API key setup, and agent profile configuration.

Then verify the CLI sees a usable session:

```bash
dailybot status --auth 2>&1
```

If auth fails or the developer declines, **skip and continue with your primary task** — chat messages must never block work (see the non-blocking rule below).

---

## Step 2 — Resolve the Target(s)

The CLI targeting flags **only accept ids/emails, never free-form names**:

| Flag | Short | Accepts |
|------|-------|---------|
| `--user`    | `-u` | User UUID, email, or chat-platform external id |
| `--channel` | `-c` | Channel id from the chat platform (Slack `C0…`, Teams channel id, Discord channel id, Google Chat space) |
| `--team`    | `-t` | Team UUID (expanded server-side to member DMs) |

At least one of `--user / --channel / --team` is required. They can be repeated and combined.

### 2a — User by name → resolve via `dailybot user list`

When the developer references a teammate by name ("send to Sergio Florez"), resolve the name to a UUID with the organization directory:

```bash
dailybot user list --json
```

This returns active members with their names and UUIDs (emails are intentionally hidden — PII). Pick the unambiguous match; if multiple names match, surface them and ask the developer to disambiguate. Never guess.

### 2b — Team by name → delegate to `dailybot-teams`

For a team-by-name target ("send a message to the QA team"), delegate to the `dailybot-teams` skill exactly as `dailybot-kudos` does — see [`../teams/SKILL.md`](../teams/SKILL.md) for the canonical resolver. The same scoping-aware error message applies if the team is not visible to the caller.

### 2c — Channel by id (always)

Channels are always referenced by their platform external id (Slack `C0123456789`, Teams `19:abc@thread.tacv2`, Discord numeric id, Google Chat `spaces/AAA…`). The CLI does not resolve channels by display name — ask the developer to paste the id if they only know the name. (Tip for Slack: right-click the channel → *View channel details* → bottom shows the id.)

### 2d — Always confirm before sending

Show the resolved targets + the message body + (for team targets) the expanded receiver count, then ask "Send? (yes / edit / cancel)". Chat sends are externally visible — do not skip confirmation unless the developer has already approved this exact send.

---

## Step 3 — Choose Execution Path

```bash
command -v dailybot
```

- **CLI found** → Step 4A
- **CLI not found** → Step 4B (HTTP fallback; see [`../shared/http-fallback.md`](../shared/http-fallback.md) for base patterns)

---

## Step 4A — Send via CLI

> **Timeout:** Allow at least 30 seconds for CLI commands to complete. Do not use a shorter timeout.

### Single message to a channel

```bash
dailybot chat send -c C0123 -m "Deploy v2.4 started 🚀"
```

### DM one or several people (by UUID, resolved in Step 2a)

```bash
dailybot chat send \
  -u 294bf2cc-e3c7-401d-a1d6-bf20aa64bb33 \
  -u 8a1b9c1e-9d7e-4f0e-9aa1-7c5e4d0a5e0c \
  -m "Standup in 10 min — please join the Slack huddle"
```

### To a whole team (expanded to member DMs)

```bash
dailybot chat send -t <team-uuid> -m "Survey is open until Friday"
```

### Report style — headline + the detail in its thread, in ONE call

This is the canonical pattern for any "report" the developer wants visible in chat (deploys, releases, incidents, status changes). The response returns the **parent `bot_message_id` plus one id per reply**, all individually editable later.

```bash
dailybot chat send -c C0123 -m "🚀 Release v2.4 shipped" \
  --thread-message "Changelog: …" \
  --thread-message "Rollout: 100% at 14:30 UTC" \
  --thread-message "Next deploy window: tomorrow 10 AM"
```

Constraints:
- `--thread-message` is repeatable up to **10 replies per call** (validated client-side).
- Each reply inherits the parent's recipients — replies do not target their own users/channels/teams.
- Thread rendering: native on Slack (channels + DMs). On Teams/Discord/Google Chat threads work in channels and arrive **flat in DMs** (the replies always land, never dropped).

### Custom Slack identity (Slack only)

```bash
dailybot chat send -c C0123 -m "Build #421 ✅" \
  --bot-name "Release Bot" --bot-icon-emoji ":rocket:" \
  --link-button "Open report::https://app.dailybot.com/r/421"
```

`--bot-icon-url` (https-only) and `--bot-icon-emoji` are mutually exclusive. Custom identity requires the Slack `chat:write.customize` scope on the Dailybot app — without it Slack uses the default identity and the API still returns `ok: true`. On Teams/Discord/Google Chat, custom identity is silently ignored.

### Send as a user's identity (Slack only, admin-only)

> **Admin-only.** `--send-as-user` / `--send-as-me` require an org admin; a
> member gets `403 org_admin_required`.

Instead of a custom bot name/icon, an admin can post the message **with a real
user's identity** — their name and profile picture — so it reads as if that
person sent it. **Slack only. Admin-only.** Two flags:

| Flag | Meaning |
|------|---------|
| `--send-as-user <UUID>` | Send with the identity of that user (name + profile picture). |
| `--send-as-me` | Shortcut — send as the **authenticated user** (the CLI resolves your own UUID). |

```bash
# Post to a channel as a specific teammate (admin only):
dailybot chat send -c C0123 -m "Deploying the hotfix now" \
  --send-as-user 294bf2cc-e3c7-401d-a1d6-bf20aa64bb33

# Post as yourself:
dailybot chat send -c C0123 -m "Standup starting" --send-as-me
```

**Constraints (validated client-side before the request):**

- **Mutually exclusive with** `--bot-name` / `--bot-icon-url` /
  `--bot-icon-emoji` — you send as a *user identity* or a *custom bot
  identity*, not both. The conflict is rejected up front with
  `send_as_user_conflict`.
- An invalid `--send-as-user` UUID is rejected client-side with
  `send_as_user_invalid_uuid` before any request goes out.
- A well-formed UUID that doesn't resolve to a user comes back as
  `send_as_user_not_found` (400).
- **Slack only** — on Teams/Discord/Google Chat the flags are ignored.
- **Admin-only** — a non-admin caller is rejected server-side (see the role
  error codes in [`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md) § 5).

### Ephemeral message (Slack only; only the recipient sees it)

```bash
dailybot chat send -u ana@co.com -m "Heads up: build broke" --ephemeral
```

Ephemeral needs a `--user` target. A channel-only ephemeral send is skipped by the platform — the CLI warns up front.

### Buttons

The CLI supports multiple button styles — from simple link buttons to rich
interactive actions (approval flows, workflow triggers, modals). **Max 25
buttons per message.** All button flags are repeatable.

#### Link buttons (jump to a URL)

```bash
--link-button "View PR::https://github.com/org/repo/pull/123"
```

#### Interactive buttons (server-side action; value is what's sent on click)

```bash
--button "Approve::approve-release-v2.4"
```

#### Approval flow buttons

A shorthand for the common approve/reject pattern. Each button carries a
`callback_url` where the server POSTs the button value on click, plus an
optional Bearer token for the callback endpoint:

```bash
dailybot chat send -c C0123 -m "Release v2.5 ready for approval" \
  --approve-button "Approve=approved" \
  --reject-button "Reject=rejected" \
  --callback-url "https://ci.example.com/hooks/release" \
  --callback-bearer "$CI_TOKEN"
```

`--approve-button` and `--reject-button` take `"Label=value"` (equals sign
separator). `--callback-url` sets the URL for both. `--callback-bearer` is
optional — when set, each button gets
`callback_auth: {"type": "bearer", "token": "<token>"}`. Prefer passing the
token via an env var (`--callback-bearer "$TOKEN"`) so it does not land in
shell history or process lists.

#### Workflow trigger buttons

Fire a Dailybot workflow when clicked — the button carries a
`callback_workflow` reference:

```bash
dailybot chat send -c C0123 -m "Ready to deploy?" \
  --workflow-button "Deploy now=<workflow-uuid>"
```

`--workflow-button` takes `"Label=<workflow-uuid>"`. Only workflows with the
`api_trigger` event type ("When triggered via API or button") can be fired this
way. Resolve eligible UUIDs with `dailybot workflow list --filter api_trigger`.
See [`../workflow/SKILL.md`](../workflow/SKILL.md) for triggering workflows
directly (including `--payload`).

#### Full-control buttons via `--buttons` (JSON pass-through)

For advanced callbacks (forms, commands, prompts, modals, auth overrides), pass
the full button contract as a JSON array. Keys are forwarded untouched (including
unknown future fields). Prefer including `button_type` / `value` for interactive
buttons (the ergonomic flags set these automatically):

```bash
dailybot chat send -u <user-uuid> -m "Pick an action" \
  --buttons '[
    {"label": "Open form", "button_type": "interactive", "value": "open_form",
     "callback_form": "<form-uuid>"},
    {"label": "Run command", "button_type": "interactive", "value": "run_cmd",
     "callback_command": "/deploy staging"},
    {"label": "Ask AI", "button_type": "interactive", "value": "ask",
     "callback_prompt": "Summarize the last deploy"},
    {"label": "Start workflow", "button_type": "interactive", "value": "wf",
     "callback_workflow": "<workflow-uuid>"},
    {"label": "Confirm", "button_type": "interactive", "value": "confirm",
     "callback_url": "https://ci.example.com/confirm",
     "callback_auth": {"type": "bearer", "token": "<token>"}},
    {"label": "Details", "button_type": "interactive", "value": "details",
     "response": "Here are the deploy details…"},
    {"label": "Fill info", "button_type": "interactive", "value": "fill",
     "callback_url": "https://hooks.example.com/x",
     "modal_body": {
       "title": "Request details",
       "submit_label": "Submit",
       "blocks": [
         {"type": "input", "name": "summary", "label": "Summary", "optional": false},
         {"type": "input", "name": "notes", "label": "Notes", "multiline": true, "optional": true}
       ]
     }}
  ]'
```

**Button contract fields:**

| Field | Description |
|-------|-------------|
| `label` | Button text (required) |
| `button_type` | `"link"` (needs `url`) or `"interactive"` (needs `value` + a callback / `response`) |
| `url` | Destination for link buttons |
| `value` | Click payload for interactive buttons |
| `callback_url` | HTTPS URL the server POSTs to on click (may include modal answers) |
| `callback_form` | Open a Dailybot form for the user to fill |
| `callback_command` | Execute a Dailybot ChatOps command |
| `callback_prompt` | Send a prompt to the Dailybot AI |
| `callback_workflow` | Trigger a Dailybot `api_trigger` workflow by UUID |
| `modal_body` | Modal composer: `{title, submit_label?, blocks: [{type, name, label, …}]}` — used with `callback_url` or `callback_workflow` when collecting inputs |
| `response` | Auto-reply text (may nest further buttons) |
| `callback_auth` | Auth for `callback_url` only: `{type: "bearer"\|"basic"\|"custom_header", …}` — never a bare `"Bearer …"` string |

**Constraints:**

- At most **one** of the five callback types (`callback_url`, `callback_form`,
  `callback_command`, `callback_prompt`, `callback_workflow`) per button.
  Combining two is rejected with `button_callback_conflict`.
- A button cannot mix a link `url` with any `callback_*` — that's
  `button_link_and_callback_conflict`.
- Unknown keys are forwarded to the API (forward-compatible).
- Max **25** buttons per message (`buttons_count_out_of_range`).
- `callback_auth` is only valid with `callback_url`.

#### Button behavior on `chat update`

When editing a message, buttons are round-tripped — the existing buttons are
preserved unless you pass new button flags. Custom identity flags
(`--bot-name`/`--bot-icon-*`) and send-as-user flags are ignored on edits.
The 72-hour edit window applies.

> Interactive-button flags (`--buttons`, `--approve-button` /
> `--reject-button`, `--callback-url`, `--callback-bearer`,
> `--workflow-button`) require **`dailybot-cli >= 3.9.0`** (this pack's
> baseline). `--link-button` and `--button` are also available at that floor.

### Headless / agent use — capture the ids in JSON

```bash
RESPONSE=$(dailybot chat send -c C0123 -m "Deploying…" \
  --thread-message "Started at 14:00 UTC" --json)

PARENT=$(echo "$RESPONSE" | jq -r .bot_message_id)
REPLY1=$(echo "$RESPONSE" | jq -r '.thread_responses[0]')
```

`--json` prints the raw API response (`{ "bot_message_id": "<parent>", "thread_responses": ["<reply1>", …] }`) to stdout — no panels, no prompts. Pair it with `--yes`-style intent (i.e. you've already confirmed with the developer) for fully headless flows.

### Raw payload escape hatch (forward-compat)

For multi-part `messages`, rich `thread_responses` objects, or any future API field the building flags do not expose yet:

```bash
dailybot chat send --payload-json '{
  "target_channels": ["C0123"],
  "messages": [{"message": "Deploy started"}],
  "thread_responses": [{"message": "Changelog: …"}]
}'
```

`--payload-json` bypasses the structured flags and is forward-compatible with anything the API accepts.

### Update a previously sent message (parent **or** any thread reply)

A reply id is just another `bot_message_id` — `chat update` edits either:

```bash
# Edit the parent (the channel post itself)
dailybot chat update "$PARENT" -c C0123 -m "Deploy done ✅"

# Edit one of the thread replies
dailybot chat update "$REPLY1" -c C0123 -m "Started at 14:00 UTC (took 6 min)"
```

The chat platform keeps the message's original bot name/avatar on an edit, so identity flags (`--bot-name`/`--bot-icon-*`) are ignored when updating. Pass the same channel id you originally sent to.

### CLI flag cheat sheet

| Flag | Short | Description |
|------|-------|-------------|
| `--user` | `-u` | Target user by UUID, email, or platform external id (repeatable) |
| `--channel` | `-c` | Target channel id (repeatable) |
| `--team` | `-t` | Target team UUID; expanded to members as DMs (repeatable) |
| `--text` | `-m` | Message text (markdown where supported) |
| `--image-url` | `-i` | Public image URL to attach |
| `--link-button` |  | `"Label::https://url"` (repeatable) |
| `--button` |  | `"Label::value"` interactive button (repeatable) |
| `--buttons` |  | JSON array of button objects (full contract; see § Buttons) |
| `--approve-button` |  | `"Label=value"` approval button (repeatable) |
| `--reject-button` |  | `"Label=value"` rejection button (repeatable) |
| `--callback-url` |  | Callback URL for approve/reject buttons |
| `--callback-bearer` |  | Bearer token sent with the callback POST |
| `--workflow-button` |  | `"Label=<workflow-uuid>"` trigger a workflow on click (repeatable) |
| `--thread-message` |  | Reply posted in the parent's thread (repeatable; max 10) |
| `--thread` |  | Reply into an existing platform thread id (channels) |
| `--channel-type` |  | `channel` / `private_channel` / `group_chat` / `direct_message` |
| `--bot-name` |  | Custom bot display name (Slack only) |
| `--bot-icon-url` |  | Custom bot avatar URL, https (Slack only) |
| `--bot-icon-emoji` |  | Custom bot avatar emoji (Slack only) |
| `--send-as-user` |  | Send with a user's identity by UUID (Slack only, admin-only; excludes `--bot-*`) |
| `--send-as-me` |  | Send as the authenticated user (Slack only, admin-only) |
| `--ephemeral` |  | Send ephemerally — recipient-only (Slack; needs `--user`) |
| `--skip-time-off` |  | Skip users currently flagged as away / on time-off |
| `--metadata` | `-d` | JSON metadata to attach |
| `--payload-json` |  | Raw request body JSON (full API control; bypasses building flags) |
| `--json` |  | Emit the raw API response as JSON to stdout (headless) |
| `--profile` | `-p` | Agent profile from `agents.json` (rarely needed for chat) |

---

## Step 4B — Send via HTTP API (CLI unavailable)

See [`../shared/http-fallback.md`](../shared/http-fallback.md) for base patterns. **`POST /v1/send-message/` accepts either `X-API-KEY` or `Authorization: Bearer`** — use whichever you have.

### Channel send with a thread (parent + 2 replies in one call)

```bash
curl -s -X POST https://api.dailybot.com/v1/send-message/ \
  -H "X-API-KEY: $DAILYBOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "target_channels": ["C0123"],
    "message": "🚀 Release v2.4 shipped",
    "thread_responses": [
      {"message": "Changelog: …"},
      {"message": "Rollout: 100% at 14:30 UTC"}
    ]
  }'
```

Response:

```json
{
  "bot_message_id": "$db/cd626a24-...",
  "thread_responses": [
    "$db/22aca052-...",
    "$db/1f57b5fc-..."
  ]
}
```

### DM a user (Bearer path — login session)

```bash
curl -s -X POST https://api.dailybot.com/v1/send-message/ \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target_users": ["294bf2cc-e3c7-401d-a1d6-bf20aa64bb33"],
    "message": "Standup in 10 min"
  }'
```

### Edit a previously sent message (parent or a thread reply)

```bash
curl -s -X POST https://api.dailybot.com/v1/send-message/ \
  -H "X-API-KEY: $DAILYBOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "target_channels": ["C0123"],
    "bot_message_id": "$db/22aca052-...",
    "message": "Started at 14:00 UTC (took 6 min)"
  }'
```

### Request fields (most-used)

| Field | Required | Notes |
|-------|----------|-------|
| `target_users` / `target_channels` / `target_teams` | At least one | Arrays. Channels accept either a bare string id or an object `{id, channel_type?, thread?}` |
| `message` | Either `message` or `messages` | Single message body (string). |
| `messages` | (alt) | Multi-part — array of `{message, image_url?, buttons?, ...}` |
| `image_url` | No | https URL |
| `buttons` | No | `[{label, button_type: "link"|"interactive", url?|value?}]` |
| `thread_responses` | No | `[{message}, …]` — posted in the parent's thread (≤10) |
| `platform_settings` | No | Slack-only: `bot_username`, `bot_icon_url`, `bot_icon_emoji`, `is_ephemeral` |
| `metadata` | No | Arbitrary JSON |
| `skip_users_on_time_off` | No | Boolean — skip recipients currently on time-off |
| `bot_message_id` | No | Set to **edit** that message (parent or reply id) |

### Response shape

```json
{
  "bot_message_id": "$db/<parent-id>",
  "thread_responses": ["$db/<reply1>", "$db/<reply2>"]
}
```

`thread_responses` is only present when the request included them. The parent id and every reply id are reusable as `bot_message_id` in a later edit.

---

## Step 5 — Error Handling

The CLI translates these to friendly messages automatically. In `--json` mode (or via curl), match on the structured `code` field, not the prose `detail`.

| Status | Code | Meaning | Agent behavior |
|--------|------|---------|----------------|
| `200`  |  | Success | Surface `bot_message_id` + any `thread_responses` ids. |
| `400`  | `invalid_thread_responses` | Too many (>10), bad structure, or nested targeting | Trim to ≤10 replies, no targeting on replies, retry. |
| `400`  | `send_as_user_conflict` | `--send-as-user`/`--send-as-me` combined with `--bot-name`/`--bot-icon-*` | Drop the custom-identity flags — the two are mutually exclusive. (Caught client-side.) |
| `400`  | `send_as_user_invalid_uuid` | `--send-as-user` isn't a valid UUID | Fix the UUID. (Caught client-side before the request.) |
| `400`  | `send_as_user_not_found` | The `--send-as-user` UUID doesn't resolve to a user | Confirm the user exists (`dailybot user list`). |
| `400`  | `button_link_and_callback_conflict` | A button has both a link `url` and a `callback_*` field | Use one or the other — a button is either a link or an interactive callback. |
| `400`  | `button_callback_conflict` | A button has more than one `callback_*` field | Only one of `callback_url`/`callback_form`/`callback_command`/`callback_prompt`/`callback_workflow` per button. |
| `400`  | `button_callback_url_invalid` | `callback_url` is not a valid URL | Fix the URL. |
| `400`  | `button_modal_body_invalid` | `modal_body` JSON is malformed or has invalid field types | Use `{title, submit_label?, blocks: [{type, name, label, …}]}` — not a bare array of fields. |
| `400`  | `button_callback_form_not_found` | `callback_form` UUID doesn't match a form | Verify the form UUID (`dailybot form list`). |
| `400`  | `button_callback_command_invalid` | `callback_command` is not a recognized ChatOps command | Check the command string. |
| `400`  | `button_callback_prompt_invalid` | `callback_prompt` is empty or too long | Fix the prompt text. |
| `400`  | `button_callback_workflow_not_found` | `callback_workflow` UUID doesn't match a workflow, or the workflow isn't triggerable | Verify the UUID (`dailybot workflow list --filter api_trigger`). |
| `400`  | `button_response_invalid` | `response` text is empty or too long | Fix the response text. |
| `400`  | `button_callback_auth_invalid` | `callback_auth` value is malformed | Use `{type: "bearer"\|"basic"\|"custom_header", …}` — only with `callback_url`. |
| `400`  | `buttons_count_out_of_range` | More than 25 buttons on a single message | Reduce to ≤25 buttons. |
| `400`  | (other) | No/invalid targets, malformed UUID, empty channel id, invalid bot identity | Surface the `detail` verbatim and fix the input. |
| `401` / `403` |  | Unauthenticated / invalid auth | Suggest `dailybot login` (or, if the developer prefers, `dailybot config key=...`). |
| `403`  | `cli_send_message_target_not_allowed` | Login Bearer caller targeting outside their role scope (cross-org, channel they can't post to, team they don't belong to) | Tell the developer which target was rejected and suggest either picking an in-scope target or using an org API key for org-wide reach. |
| `404`  | `team_does_not_exists_or_not_enough_permissions_granted` | Team UUID is invalid or the caller can't post to it | Re-run `dailybot team list` and confirm visibility. |
| `429`  |  | Rate limit on the per-token CLI throttle | Wait a bit and retry; do not retry in a tight loop. |
| `5xx`  |  | Server error | Warn the developer and stop; this is on Dailybot's side. |

If the auth path is **X-API-KEY**, the role-scope error (`cli_send_message_target_not_allowed`) does not apply — the API key is org-wide.

---

## Step 6 — Sample Multi-turn Dialogues

### Dialogue A — Quick channel ping

```
Developer: "send a Slack message to C02MRM9NF8B saying the staging deploy is done"
Agent:
  1. Confirm: "I'll send to channel C02MRM9NF8B: 'Staging deploy done ✅'. Send? (y/n)"
  2. dailybot chat send -c C02MRM9NF8B -m "Staging deploy done ✅"
  3. Surface the bot_message_id (so the developer can ask for an edit later).
```

### Dialogue B — Report-style post with a thread (the canonical pattern)

```
Developer: "post a release report to #releases: headline 'Release v2.4 shipped', and in the thread add the changelog and the rollout time"
Agent:
  1. (Channel id needed — ask the developer for the id of #releases, e.g. C0123456789)
  2. Confirm:
       "I'll post to C0123456789:
          Parent:    🚀 Release v2.4 shipped
          Thread 1:  Changelog: ...
          Thread 2:  Rollout: 100% at 14:30 UTC
        Send? (y/n)"
  3. dailybot chat send -c C0123456789 -m "🚀 Release v2.4 shipped" \
       --thread-message "Changelog: ..." \
       --thread-message "Rollout: 100% at 14:30 UTC" \
       --json
  4. Capture the parent id + reply ids; surface all three so the developer can edit any of them later.
```

### Dialogue C — DM a teammate by name

```
Developer: "ping Sergio Florez in chat that the prod hotfix is merged"
Agent:
  1. dailybot user list --json   → find "Sergio Florez" → UUID 294bf2cc-...
  2. Confirm: "I'll DM Sergio Florez (UUID 294bf2cc-...): 'Prod hotfix merged ✅'. Send? (y/n)"
  3. dailybot chat send -u 294bf2cc-... -m "Prod hotfix merged ✅"
  4. Surface the bot_message_id.
```

### Dialogue D — Edit the second thread reply after the rollout

```
Developer: "actually update the rollout reply to say 'rolled back, see incident #42'"
Agent:
  1. Use the stored REPLY2 bot_message_id from the earlier --json capture.
  2. Confirm: "I'll edit that reply to: 'Rolled back, see incident #42'. Update? (y/n)"
  3. dailybot chat update "$REPLY2" -c C0123456789 -m "Rolled back, see incident #42"
  4. Surface success.
```

### Dialogue E — Approval flow with callback

```
Developer: "send a release approval request to #releases with approve/reject buttons
            that POST to our CI webhook"
Agent:
  1. Confirm:
       "I'll post to C0123456789:
          Message:  🚢 Release v2.5 ready for approval
          Buttons:  [Approve] → POST approved, [Reject] → POST rejected
          Callback: https://ci.example.com/hooks/release
        Send? (y/n)"
  2. dailybot chat send -c C0123456789 \
       -m "🚢 Release v2.5 ready for approval" \
       --approve-button "Approve=approved" \
       --reject-button "Reject=rejected" \
       --callback-url "https://ci.example.com/hooks/release" \
       --callback-bearer "$CI_TOKEN" --json
  3. Surface the bot_message_id.
```

### Dialogue F — Workflow trigger button

```
Developer: "post a message to #deploys with a button that fires the deploy workflow"
Agent:
  1. dailybot workflow list --filter api_trigger --json   → find the deploy workflow UUID
  2. Confirm:
       "I'll post to C0123456789:
          Message:  Deploy ready — click to start
          Button:   [Deploy now] → triggers workflow <uuid>
        Send? (y/n)"
  3. dailybot chat send -c C0123456789 \
       -m "Deploy ready — click to start" \
       --workflow-button "Deploy now=<workflow-uuid>" --json
  4. Surface the bot_message_id.
```

### Dialogue G — Modal with inputs + callback URL

```
Developer: "DM me a button that opens a form modal and POSTs the answers to our webhook"
Agent:
  1. Resolve the developer's user UUID (`dailybot me --json` or `user list`).
  2. Confirm the message + that the modal collects Summary + Notes, callback = the webhook URL.
  3. dailybot chat send -u <user-uuid> -m "Please fill in the details" \
       --buttons '[{"label":"Open form","button_type":"interactive","value":"open",
         "callback_url":"https://hooks.example.com/x",
         "modal_body":{"title":"Request details","submit_label":"Submit",
           "blocks":[
             {"type":"input","name":"summary","label":"Summary"},
             {"type":"input","name":"notes","label":"Notes","multiline":true}]}}]' --json
  4. Surface the bot_message_id; remind that answers land on the webhook after Submit.
```

### Dialogue H — Team not visible to the caller (role scope)


```
Developer: "post a heads-up to the Security team's channel"
Agent:
  1. dailybot team list   → no "Security" team visible to the caller.
  2. Stop and surface (delegated from dailybot-teams):
       "I don't see a team named 'Security' on your account. You may not be a member,
        or it doesn't exist. Run `dailybot team list` to confirm what you can reach.
        If you need org-wide reach, set an API key with `dailybot config key=...`."
```

---

## Step 7 — Confirm

After the command runs:

- **Success** — briefly confirm and surface ids the developer may want for an edit:
  > *"Sent to #releases. Parent id `$db/cd62…` (+ 2 thread reply ids if you ever want to edit them)."*
- **Edit success** — confirm what changed:
  > *"Updated reply `$db/22ac…` in #releases."*
- **Failure** — warn briefly. For `cli_send_message_target_not_allowed`, name the rejected target and suggest an in-scope alternative.
- **Skipped** — say nothing.

---

## Safety & etiquette

- **Always confirm** the message body + targets before sending. Chat is externally visible to other humans.
- **Never** send chat messages autonomously without an explicit ask, unless the developer pre-approved a flow that explicitly chains chat sends (e.g. an on-call rotation script).
- **No secret leakage.** Treat the message body the same way `dailybot-email` treats the email body — never embed API keys, tokens, or sensitive env vars. If the developer's draft contains a credential-shaped token, surface it and ask before sending.
- **No mass DMs without consent.** A `--team` target expands to every member's DM — restate the receiver count when confirming.
- **Custom bot identity is Slack-only.** If you set `--bot-name`/`--bot-icon-*` for a Teams/Discord/Google Chat target, those flags are silently ignored — call that out so the developer isn't surprised.

---

## Cross-skill contract

- **Team resolution** is delegated to `dailybot-teams` (`../teams/SKILL.md`). Do not inline `dailybot team list` parsing here — the resolver and the scoping-aware error message live in one place.
- **User resolution** uses the canonical `dailybot user list --json` directory (same as `dailybot-kudos`). PII rules apply: emails are not shown, names + UUIDs only.
- **Chat is not a substitute for `dailybot-report`.** When the developer says "report this to my team", default to `dailybot-report` (dashboard + optional broadcast). Use `dailybot-chat` only when they specifically want a chat message delivered to a chat platform.

---

## Non-Blocking Rule

Sending chat messages must **never block the developer's primary work**. If the CLI is missing, auth fails, the network is down, the role denies the target, or the command errors:

1. Warn the developer briefly.
2. Continue with the primary task.
3. Do not retry automatically.
4. Do not enter a diagnostic loop.

---

## Additional Resources

- [`../shared/auth.md`](../shared/auth.md) — authentication setup (login OTP, API key)
- [`../shared/http-fallback.md`](../shared/http-fallback.md) — HTTP API fallback patterns
- [`../teams/SKILL.md`](../teams/SKILL.md) — team-name resolver (called by this skill)
- [`../kudos/SKILL.md`](../kudos/SKILL.md) — user-resolution pattern (same approach as Step 2a)
- **Live API spec:** `https://api.dailybot.com/api/swagger/`
- **Full agent API skill:** `https://www.dailybot.com/skill.md`
- **CLI command reference:** [`DailybotHQ/cli` — `dailybot chat send/update`](https://github.com/DailybotHQ/cli/blob/main/docs/API_REFERENCE.md)
