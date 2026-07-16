---
name: dailybot-ask
description: Ask the Dailybot AI a question from the terminal and read the answer, non-interactively. Runs headless — a single `dailybot ask "<question>"` prints the assistant's reply to stdout (or structured JSON with `--json`), so an autonomous agent (Claude Code, CI, a bot) can query the Dailybot AI with only an API key. Use when the developer or agent says "ask Dailybot ...", "query the Dailybot AI", "what does Dailybot say about ...", or wants a one-shot answer from Dailybot's assistant. Distinct from dailybot-chat (bot messages to Slack/Teams) and dailybot-report (progress to the dashboard).
version: "3.10.3"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"🤖","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Ask

> **Requires `dailybot-cli >= 3.7.0`** (the skill-pack baseline) — the `dailybot ask`
> command and full API-key parity on the AI chat. On much older CLIs the AI chat only
> exists as the interactive TUI (`dailybot interactive`) and requires a login
> session. If `dailybot ask --help` is not recognized, ask the developer to run
> `dailybot upgrade`. See [`../SKILL.md` § Required Dailybot CLI version](../SKILL.md#required-dailybot-cli-version).

You ask the **Dailybot AI assistant** a question and read its answer — **without
opening an interactive UI**. This is the headless counterpart of the full-screen
chat (`dailybot ask` with no message, or the deprecated `dailybot interactive`):

```bash
dailybot ask "What are my pending check-ins?"
```

prints the assistant's answer to **stdout** and exits. That makes it the primary
way an **autonomous agent** talks to the Dailybot AI: it needs no TTY, no menu,
and works with only `DAILYBOT_API_KEY` (the server resolves the acting user from
the key's owner).

It is **not**:

- `dailybot-chat` — that sends bot **messages** to Slack / Teams / Discord /
  Google Chat. `ask` talks to the **AI**, it does not post to a channel.
- `dailybot-report` — that posts a progress update to the Dailybot dashboard.
- `dailybot-messages` — that polls the agent-to-agent inbox.

---

## When to Use

Trigger phrases the agent should recognize:

- "ask Dailybot …", "ask the Dailybot AI …", "query Dailybot"
- "what does Dailybot say about …", "get an answer from Dailybot"
- "have Dailybot summarize my check-ins / forms / standup"
- Any time an agent wants a one-shot, machine-readable answer from the Dailybot
  assistant to feed back into its own reasoning.

Do **not** use `dailybot ask` to *post* something to the team — that's
`dailybot-chat` (chat platform) or `dailybot-report` (dashboard).

---

## Step 1 — Verify Setup

Read and follow the authentication steps in [`../shared/auth.md`](../shared/auth.md).
The AI chat accepts **either** a login session **or** an org API key — an agent
with only `DAILYBOT_API_KEY` set can use `dailybot ask` directly.

Confirm the command exists (`dailybot-cli >= 3.7.0`):

```bash
dailybot ask --help 2>&1 | head -1
```

If the command is unknown, the CLI is too old — ask the developer to
`dailybot upgrade`, then continue with the primary task (never block on it).

---

## Step 2 — Ask (one-shot, headless)

```bash
# Plain text answer to stdout:
dailybot ask "In one sentence, what did my team ship this week?"

# Structured JSON (recommended for agents — easy to parse):
dailybot ask "What forms do I have?" --json

# Piped question (equivalent to passing it as an argument):
echo "draft my standup update" | dailybot ask

# Continue a prior turn by reusing its session id:
dailybot ask "tell me more" --session-id <previous-session-id>
```

- **Text mode** prints the assistant's reply verbatim to stdout (markup off, no
  reflow — safe to capture).
- **`--json`** emits a single object:
  ```json
  {"message": "<assistant reply>", "actions": [...], "classification": "direct_response|full_agent", "session_id": "<id or null>"}
  ```
  Read `message` for the answer; `actions` lists any suggested follow-up actions;
  `session_id` (when present) can be passed to the next `--session-id` call to
  keep context.
- Errors surface via standard exit codes (see [`../shared/auth.md`](../shared/auth.md)
  for the shared table); `--json` prints `{"error": ..., "status": ...}`.

### Interactive mode (humans)

If a human wants a back-and-forth conversation instead of one-shot answers, run
`dailybot ask` **with no message** — it opens the full-screen Textual chat
session. (`dailybot interactive` is a deprecated alias for the same thing.)
Agents should stick to the headless one-shot form above.

---

## Step 3 — Rate limits

The AI chat endpoint is throttled to **30 requests/minute per API key**. Normal
agent usage (a few questions per minute) is well within that. On a `429`,
`dailybot ask` exits with the rate-limit code and a "Rate limit exceeded. Try
again in Ns." message; in `--json` mode the payload carries
`retry_after_seconds`. Back off for that many seconds — do not hammer the
endpoint in a loop.

---

## Step 4 — HTTP Fallback (when the CLI is unavailable)

See [`../shared/http-fallback.md`](../shared/http-fallback.md) for base patterns.

**Endpoint:** `POST /v1/cli/chat/completions/` — accepts **either** `X-API-KEY`
or a Bearer login token.

```bash
curl -s -X POST "https://api.dailybot.com/v1/cli/chat/completions/" \
  -H "X-API-KEY: $DAILYBOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are my pending check-ins?"}'
```

Optional body fields: `session_id` (continue a session), `history` /
`messages` (prior turns as `{role, content}`), `reset_thread`. The response is
`{ status, async, correlation_id, classification, message: {role, content}, actions }`
— read `message.content` for the answer. A `429` sets the `Retry-After` header.

---

## Non-Blocking Rule

If the CLI is missing, too old, auth fails, or the endpoint errors: warn the
developer briefly, continue the primary task, do not retry in a loop.
