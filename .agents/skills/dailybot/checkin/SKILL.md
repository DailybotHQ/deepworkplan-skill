---
name: dailybot-checkin
description: Drive the full check-in lifecycle via Dailybot — list and complete pending check-ins, see pending/completed status for a day, inspect a check-in's questions and schedule, browse response history, edit or reset a submitted response, and backfill or future-date responses. Also authors check-ins — create and configure a check-in (schedule, participants, reminders, privacy, smart/AI) and manage its questions (types, report titles, variations, conditional logic). Works headless with an API key. Use when the developer asks to fill in their standup, answer daily questions, check what check-ins they have, edit or reset a check-in, review past responses, or create/configure a check-in. Do not use for free-text progress reports — those go through dailybot-report.
version: "3.10.3"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"✅","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Check-in

You help developers complete their pending check-ins (daily standups, weekly surveys, async rituals) through Dailybot. Check-ins are structured questionnaires set up by a team lead — each has a set of questions that the developer answers. This is distinct from free-text progress reports (handled by `dailybot-report`).

---

## Auth model — API key or login

Check-in commands accept **either** a Bearer login session (`dailybot login`)
**or** an org API key (`DAILYBOT_API_KEY`).
A login session is the same one used by the webapp — it scopes actions to the
acting identity's permissions and pending check-ins (the server resolves the
API key's owner).

If the developer has only an API key, check-in commands still work — the CLI
falls back to `X-API-KEY`. Prefer `dailybot login` for the human's own personal
pending check-ins. (Both credentials work —
`dailybot upgrade` or `dailybot login`.)

---

## When to Use

- "complete my check-in", "fill in my standup", "answer my dailybot"
- "what check-ins do I have?", "any pending standups?", "check-in status"
- "what does my standup ask?" / inspect a check-in's questions or schedule (`show`)
- "show my past check-ins", "check-in history"
- "edit / update my check-in answer", "reset / delete today's check-in" (`edit` / `reset`)
- "submit my standup for yesterday / for a specific date" (backfill / future-date)
- At the start of a work session when the developer wants to catch up on rituals

Do **not** use this skill for free-text progress reports — route those to
`dailybot-report` instead. Check-ins are structured questionnaires with
specific questions; reports are freeform updates.

---

## Step 1 — Verify Setup

Read and follow the authentication steps in [`../shared/auth.md`](../shared/auth.md). That file covers CLI installation, login, API key setup, and agent profile configuration.

**Additionally**, confirm at least one credential is present (a login session or an API key):

```bash
dailybot status --auth 2>&1
```

If the output shows a logged-in user session **or** a configured API key,
proceed. Otherwise guide them through `dailybot login` (see auth.md) or ask
them to set `DAILYBOT_API_KEY`.

If auth fails or the developer declines, skip and continue with your primary task.

---

## Step 2 — List Pending Check-ins

```bash
dailybot checkin list --json
```

This returns today's pending check-ins for the logged-in user.

### JSON output shape

```json
{
  "count": 1,
  "pending_checkins": [
    {
      "followup_name": "Daily Standup",
      "followup_uuid": "<uuid>",
      "template_questions": [
        {
          "uuid": "<question-uuid>",
          "question": "What did you complete yesterday?",
          "question_type": "text_field",
          "is_blocker": false,
          "index": 0
        }
      ]
    }
  ]
}
```

### Present check-ins to the developer

When check-ins are found, summarize them clearly:

> "You have **1 pending check-in** via Dailybot:
>
> 1. **Daily Standup** — 3 questions
>    - What did you complete yesterday?
>    - What are you working on today?
>    - Any blockers?
>
> Want me to help you fill it in?"

When no check-ins are found:

> "No pending check-ins right now. You're all caught up."

---

## Step 3 — Complete a Check-in

Once the developer wants to complete a check-in, you have two approaches:

### 3a. Gather answers from context (recommended for agents)

Use what you know about the developer's recent work to draft answers, then
confirm before submitting. This is the best experience — the developer
reviews and approves rather than typing everything.

> "Based on your recent work, here's what I'd submit for **Daily Standup**:
>
> 1. *What did you complete yesterday?* — "Shipped the auth refactor with full test coverage"
> 2. *What are you working on today?* — "Starting the payment integration"
> 3. *Any blockers?* — "None"
>
> **Should I submit these answers?** (yes / edit / skip)"

### 3b. Ask the developer for each answer

If you don't have enough context, ask for each answer individually:

> "For your **Daily Standup**:
>
> 1. What did you complete yesterday?"

Wait for each answer, then confirm before submitting.

### Submit via CLI (non-interactive)

```bash
dailybot checkin complete <followup_uuid> \
  -a 0="Shipped the auth refactor with full test coverage" \
  -a 1="Starting the payment integration" \
  -a 2=no \
  --yes
```

> **Timeout**: Allow at least 30 seconds for CLI commands to complete. Do not use a shorter timeout.

### Answer types — match the question, not your prose

Every answer is validated against its question's `question_type`. Read the types
first (`dailybot checkin show <followup_uuid> --json`) and answer accordingly;
the server rejects a mismatch with `400 ["response is not valid"]` and does not
say which question was wrong.

| `question_type` | Answer with | Example |
|-----------------|-------------|---------|
| `text` | Free text | `-a 0="Shipped the auth refactor"` |
| `boolean` | `yes`/`no`, `true`/`false`, or `1`/`0` | `-a 2=no` |
| `numeric` | A number | `-a 1=8` |
| `multiple_choice` | One of the question's `choices` labels | `-a 3="Blocked"` |

A blocker question is very often `boolean`, so answering it `"None"` or `"N/A"`
— the natural English answer — is rejected. The CLI converts your string to the
right JSON type; it cannot guess that `"None"` means `false`.

### CLI flags

| Flag | Short | Description |
|------|-------|-------------|
| `--answer` | `-a` | `index=response` pair (0-based question index). Repeatable. |
| `--response-date` | | Target date `YYYY-MM-DD`. Defaults to today. Only works while the check-in is still **pending**; once today's response is submitted you can no longer backfill a past day from the CLI. |
| `--yes` | `-y` | Skip confirmation prompt. |
| `--json` | | Emit machine-readable JSON output. |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `3` | Not authenticated — guide through `dailybot login` |
| `7` | User aborted the confirmation prompt |

---

## Step 3.5 — The full check-in lifecycle

Beyond `list` + `complete`, the CLI covers the whole check-in lifecycle. **Every
command below takes `--json` and works headless with an API key** — this is what
lets an agent do almost everything with check-ins from the terminal.

### Status for a day

```bash
dailybot checkin status [--date YYYY-MM-DD] [--json]
```

Each check-in with its **pending/completed** state for that day (default today).
JSON: `{ "date", "count", "checkins": [{ uuid, name, response_completed, ... }] }`.

### Inspect a check-in's questions & schedule

```bash
dailybot checkin show <followup_uuid> [--json]
```

Name, schedule (frequency / time / timezone), and every question with its type
and UUID. Use this to know **what** a check-in asks (and each question's `uuid`)
before completing or editing it.

### Browse response history

```bash
dailybot checkin history <followup_uuid> --days 7 [--json]
dailybot checkin history <followup_uuid> --from 2026-06-01 --to 2026-06-30 --json
dailybot checkin history <followup_uuid> --user <user_uuid> --days 30   # one participant
dailybot checkin history <followup_uuid> --search "deploy" --days 30    # keyword filter
dailybot checkin history <followup_uuid> --days 30 --page 2 --page-size 20
```

Responses over a date range (date, completed, answer summary). Check-ins are
team-wide, so this lists **every participant's** responses by default (unlike
forms, which default to your own). Pass `--user <uuid>` to narrow to one
participant — that filter is admin/manager only; a member always sees only their
own responses regardless of the flag.

> **`--user` takes a UUID, nothing else.** An email or a display name is
> rejected before the request with `invalid_user_identifier`. Resolve it first
> with `dailybot user list --json`.

> **Paging.** `--page` / `--page-size` / `--limit` return a single slice; with
> none of them the command walks every page. `--search` / `--grep` is a
> case-insensitive substring filter (max 256 chars, truncated client-side). See
> [`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md).

### Edit an existing response

```bash
dailybot checkin edit <followup_uuid> -a 0="Updated answer" --yes [--json]
dailybot checkin edit <followup_uuid> [--date YYYY-MM-DD]   # prompts each question with the current value
```

Overrides specific answers on the already-submitted response, then re-submits.
Use `dailybot checkin history`/`show` first to learn the question order.

### Reset (delete) a response

```bash
dailybot checkin reset <followup_uuid> [--date YYYY-MM-DD] [--yes] [--json]
```

Deletes your own response for a day (confirms first unless `--yes` / `--json`).

### Backfill (past) & future-dating

`complete` accepts `--response-date`; `edit` / `reset` / `history` accept
`--date` (or `--from/--to`). The server may refuse when the check-in disallows
it — the CLI maps the `code` to a friendly message (and includes it in `--json`
errors):

| `code` | Meaning |
|--------|---------|
| `previous_responses_are_not_allowed` | Backfill is disabled for this check-in |
| `future_responses_are_not_allowed` | Future-dating is disabled |
| `followup_not_allow_responses_before_trigger_time` | Too early (before the trigger time) |
| `user_is_not_a_followup_member` | You're not a participant |
| `responses_not_allowed_on_inactive_followup` | The check-in is inactive |
| `template_questions_version_conflict` | Questions changed — re-run `show` and retry |
| `response_date_format_is_invalid` | Use `YYYY-MM-DD` |

### Interactive terminal chat

In `dailybot ask` (the AI chat), the native slash commands `/checkins`,
`/checkin edit`, and `/checkin reset` drive these same flows with numbered
prompts — handy for humans; agents should use the headless commands above.

---

## Step 3.7 — Authoring check-ins (create / configure / questions)

> **Requires `dailybot-cli >= 3.7.0`** (the skill-pack baseline). The authoring surface — `checkin create`,
> `checkin config`, `checkin archive`, the `checkin questions add|edit|delete|reorder`
> group, resolving people by email, the smart/AI flags, and the **create requires
> ≥ 1 question** rule (`questions_required`) — is all available. If
> `dailybot --version` is below 3.7.0, run `dailybot upgrade`.

Everything above **answers** a check-in. This section **builds** one. As of the
authoring release, an agent can create a check-in from scratch, tune every
scheduling / reminder / privacy / AI setting, manage its questions (including
conditional jump logic), verify the result with a round-trip read, and archive
it — all headless with an API key.

> **Role-gated.** Configuring, archiving a check-in, and editing its questions
> are **admin/manager** operations server-side. **Creating** a check-in is now
> allowed for **any authenticated member**.
> Update and delete remain admin/manager only. Answering check-ins (Steps 2–3.5)
> is not role-gated.

### Create in one shot vs. configure incrementally

There are two authoring styles, and they share the same flag vocabulary:

- **One-shot create** — `dailybot checkin create -n "Name" [all the flags]`
  builds a fully-configured check-in in a single call, seeding questions with
  `--questions-file` / `--interactive` / `--ai-short-question`.
- **Incremental configure** — `dailybot checkin create -n "Name" --user @me
  --questions-file q.json` first (participant + at least one question are both
  mandatory), then `dailybot checkin config <followup_uuid> [flags]` to change
  settings later. **`config` is a partial update: only the flags you pass
  change**; everything else is left untouched. This is the safest way for an
  agent to adjust one setting without disturbing the rest.

Both accept the same scheduling / reminder / submission / privacy / smart-AI /
participant / channel flags below. A few flags are **create-only** or
**config-only** — the reference table calls those out.

```bash
# Create a check-in (minimal — one participant AND one question are mandatory)
dailybot checkin create -n "Daily Standup" --user me@example.com --questions-file q.json

# Later, flip one setting without touching anything else
dailybot checkin config <followup_uuid> --time 09:30 --reminders 2
```

> **Timeout**: Allow at least 30 seconds for these commands. Do not use a shorter timeout.

### Participants are required (read this first)

**A check-in must have at least one participant AND at least one question.**

- **Non-interactive create with no `--user` and no `--team` fails fast** with
  `checkin_requires_participant`. Always pass at least one participant when
  scripting a create.
- **Create with no questions fails fast** with `questions_required` — seed at
  least one question with `--questions-file` or `--interactive` (add/edit/remove
  more later via `checkin questions`).
- In an interactive TTY, `create` **prompts** for participants instead of
  erroring.
- On **`config`, `--user` / `--team` REPLACE the entire participant set** (full
  replace, not append). To add one person you must re-list everyone who should
  remain. Same semantics for `--report-channel` (see channels below).

```bash
# Two people + a whole team as participants
dailybot checkin create -n "Daily Standup" \
  --user me@example.com --user "Jane Doe" \
  --team "My Team"
```

### Full flag reference (`create` / `config`)

Users resolve by **name, email, or UUID**. Resolving a `--user` by **email
needs admin/manager permissions**; when that lookup isn't allowed the CLI falls
back with a clear message (use a UUID or name instead).

#### Scheduling

| Flag | Values / format | Notes |
|------|-----------------|-------|
| `--time` | `HH:MM` | Delivery time. |
| `--days` | comma weekdays `0-6` | `0 = Sunday`. E.g. `1,2,3,4,5` = Mon–Fri. |
| `--timezone` | IANA name | E.g. `America/New_York`. |
| `--schedule-file` | JSON path | Full schedule object from a file. |
| `--start-on` / `--end-on` | `YYYY-MM-DD` | Active window bounds. |
| `--frequency` | `weekly` **only** | Weekly cadence. Monthly/custom go through `--frequency-advanced` — `--frequency monthly` fails fast (`invalid_frequency_type`). |
| `--every` | integer `>= 1` | Repeat interval (every N periods). |
| `--frequency-advanced` | `disabled` / `monthly` / `custom` | Advanced cadence selector. Use `custom` with `--cron`. |
| `--cron` | `"m h dom mon dow"` | 5-field cron, **for `custom` cadence only**. |
| `--trigger-based` / `--fixed-time` | flag | Trigger-based vs. fixed-time delivery. |
| `--participant-timezone` / `--custom-timezone` | flag | Use each participant's TZ vs. one custom TZ. |
| `--report-time` | `HH:MM` | When the aggregated report is posted. |

#### Reminders

| Flag | Values | Notes |
|------|--------|-------|
| `--reminders` | `0-5` | Number of reminders. `0` = off. |
| `--reminder-interval` | `0-60` | Minutes between reminders. |
| `--reminder-condition` | `smart_frequency` / `fixed_frequency` | When reminders fire. |
| `--reminder-tone` | `standard` / `persuasive` | Reminder voice (`invalid_reminder_tone` if other). |

#### Submission rules

| Flag | Notes |
|------|-------|
| `--work-days` / `--no-work-days` | Restrict to working days. |
| `--allow-early` / `--no-early` | Allow submitting before the trigger time. |
| `--allow-past` / `--no-past` | Allow backfilling past responses. |
| `--allow-future` / `--no-future` | Allow future-dating responses. |
| `--one-by-one` / `--aggregated` | Deliver questions one-by-one vs. all at once. |

#### Privacy / anonymity

| Flag | Values | Notes |
|------|--------|-------|
| `--anonymous` / `--no-anonymous` | flag | **Irreversible**: once anonymous, `--no-anonymous` fails with `anonymous_irreversible` (unlike forms). |
| `--privacy` | `only_owner`, `owner_and_members`, `managers_and_members`, `managers_and_admins`, `org_admins`, `everyone`, `custom` | Who can see responses. |

#### Smart / AI

| Flag | Values | Dependency |
|------|--------|-----------|
| `--smart` / `--no-smart` | flag | Adaptive AI conversation mode. |
| `--intelligence` / `--no-intelligence` | flag | AI insights on responses. **Requires `--smart`.** |
| `--max-clarifying` | `0-5` | Cap on AI follow-up questions. **Requires `--intelligence`** when `> 0`. |

The dependency chain is enforced server-side: `--intelligence` without `--smart`
and `--max-clarifying > 0` without `--intelligence` both fail with
`intelligence_requires_smart_checkin`.

#### Intro / outro

| Flag | Notes |
|------|-------|
| `--intro` | Opening message, `3–1024` chars. |
| `--outro` | Closing message, `3–1024` chars. |

#### Participants

| Flag | Scope | Notes |
|------|-------|-------|
| `--user` | create + config | Name, email, or UUID. Repeatable. On `config`, REPLACES the user set. |
| `--team` | create + config | Name or UUID. Repeatable. On `config`, REPLACES the team set. |

#### Channels

| Flag | Notes |
|------|-------|
| `--report-channel` | Channel UUID. Repeatable, **max 3** (`too_many_report_channels`, enforced client- and server-side). On `config`, REPLACES the channel set. |

#### Questions seeding (create) + config-only flags

| Flag | Scope | Notes |
|------|-------|-------|
| `--questions-file` | create | Seed questions from a JSON array (see below). |
| `--interactive` | create | Prompt for questions interactively. |
| `--ai-short-question` | create | Let AI generate report titles for seeded questions. |
| `-n` / `--name` | create + config | Check-in name. |
| `--active` / `--inactive` | config | Activate / deactivate the check-in. |

### Question authoring (`checkin questions ...`)

Questions are managed with a dedicated subgroup. **This is the same question
model forms use** — the types, report-title rule, variations, and conditional
logic below are shared.

```bash
dailybot checkin questions add    <followup_uuid> --type TYPE --question TEXT [flags]
dailybot checkin questions edit   <followup_uuid> <question_uuid> [same flags]
dailybot checkin questions delete <followup_uuid> <question_uuid>
dailybot checkin questions reorder <followup_uuid> <q_uuid> <q_uuid> ...
```

#### Question types

The complete catalog is **four** types — there are no others:

| `--type` | Options? | Behavior |
|----------|----------|----------|
| `text` | no | Free-text answer. |
| `multiple_choice` | **yes** — `--options "A,B,C"` | Choose from a fixed list. |
| `boolean` | no | Yes/No answer. |
| `numeric` | no | Numeric answer. |

Common flags on `add` / `edit`:

| Flag | Notes |
|------|-------|
| `--required` / `--optional` | Whether an answer is mandatory. |
| `--blocker` / `--no-blocker` | Tag the "blocker" question. |
| `--short-question` | Report title, `<= 512` chars. See the rule below. |
| `--ai-short-question` | Let AI generate the report title instead. |
| `--variation` | Alternate phrasing. Repeatable, **up to 10**, rotated per run. |
| `--logic-file` | Conditional logic from a JSON file. |
| `--jump-if-equals` / `--jump-to` / `--else-jump-to` | Inline conditional logic (see below). |

#### Report title is REQUIRED on `add`

Every added question needs a **report title** (the short label used in the
posted report). Provide it **one of two ways**:

- `--short-question "Title"` — an explicit title (`<= 512` chars), **or**
- `--ai-short-question` — let Dailybot's AI generate one.

Explicit titles are preserved; **AI only fills in the blanks**. Passing neither
is an error: `short_question_required`. On **`edit`** the report title is **not**
required (edits are partial updates).

```bash
# Add a required text question with an explicit report title + two variations
dailybot checkin questions add <followup_uuid> \
  --type text --question "What did you complete yesterday?" \
  --short-question "Yesterday" --required \
  --variation "What did you get done since your last update?" \
  --variation "Recap of yesterday's work?"

# Add a multiple-choice question and let AI name it
dailybot checkin questions add <followup_uuid> \
  --type multiple_choice --question "How's the sprint going?" \
  --options "On track,At risk,Blocked" --ai-short-question
```

#### Reordering

`questions reorder` takes the **complete set** of question UUIDs in the new
order. Passing a partial/incomplete set is rejected with
`question_uuids_incomplete` — always list **every** question.

```bash
dailybot checkin questions reorder <followup_uuid> \
  <q_uuid_c> <q_uuid_a> <q_uuid_b>
```

#### Conditional logic (jump rules)

A question can branch to a later question (or end the check-in) based on the
answer. Attach logic **either** with a full JSON file (`--logic-file`) **or**
inline with `--jump-if-equals VALUE --jump-to N [--else-jump-to M]`.

**Logic shape:**

```json
{
  "rules": {
    "rules_if": [
      {
        "conditions": [
          {"operator": "is_equal_to", "comparison_value": "Blocked", "logic_connector": "or"}
        ],
        "then": {"action": "jump_to", "target": 5}
      }
    ],
    "rules_else": {"action": "jump_to", "target": -1}
  }
}
```

- **`rules_else` is required.**
- **Jump targets are forward-only**: `target` must be **greater than this
  question's index**, or `-1` (end the check-in). The **server owns the index**
  and **auto-clamps dangling targets** when a question is deleted or reordered.

**Operators by question type:**

| Type | Operators |
|------|-----------|
| `text` | `is_equal_to`, `is_not_equal_to`, `contains`, `not_contains`, `begins_with`, `not_begins_with`, `ends_with`, `not_ends_with` |
| `numeric` | `is_equal_to`, `is_not_equal_to`, `lower_than`, `lower_or_equal_than`, `greater_than`, `greater_or_equal_than` |
| `multiple_choice` / `boolean` | `is_equal_to`, `is_not_equal_to` |

**Logic connectors:**

| Type | Allowed connectors |
|------|--------------------|
| `text` / `numeric` / `boolean` | `and`, `or` |
| `multiple_choice` | `or` only |

Boolean comparison values are JSON `true` / `false` (the CLI coerces
`--jump-if-equals true` / `--jump-if-equals false`).

**Actions:**

| `action` | `target` |
|----------|----------|
| `jump_to` | integer question index (forward-only, or `-1` = end) |
| `trigger_checkin` | a check-in UUID |
| `trigger_form` | a form UUID |

**Inline jump example** — if the blocker answer is `Yes`, skip ahead to question 4:

```bash
dailybot checkin questions add <followup_uuid> \
  --type boolean --question "Any blockers?" \
  --short-question "Blockers" --blocker \
  --jump-if-equals true --jump-to 4 --else-jump-to -1
```

### `--questions-file` JSON format

`--questions-file` (and forms' equivalent) is a **JSON array**, **max 50
questions**. Each object supports:

| Key | Alias | Notes |
|-----|-------|-------|
| `question_type` | `type` | One of the four types. |
| `question` | `label` | The question text. |
| `options` | | For `multiple_choice`. |
| `required` | | Boolean. |
| `is_blocker` | | Boolean. |
| `short_question` | | Report title. |
| `variations` | | Array of alternate phrasings. |
| `logic` | | Logic object (same shape as above). |

```json
[
  {
    "question_type": "text",
    "question": "What did you complete yesterday?",
    "short_question": "Yesterday",
    "required": true,
    "variations": ["Recap of yesterday's work?"]
  },
  {
    "question_type": "text",
    "question": "What are you working on today?",
    "short_question": "Today",
    "required": true
  },
  {
    "question_type": "boolean",
    "question": "Any blockers?",
    "short_question": "Blockers",
    "is_blocker": true,
    "logic": {
      "rules": {
        "rules_if": [
          {"conditions": [{"operator": "is_equal_to", "comparison_value": true, "logic_connector": "or"}],
           "then": {"action": "jump_to", "target": 3}}
        ],
        "rules_else": {"action": "jump_to", "target": -1}
      }
    }
  }
]
```

### Round-trip verification (`checkin show`)

After authoring, read the full config back with `dailybot checkin show
<followup_uuid> --json` and confirm it matches your intent. The detail JSON:

```json
{
  "id": "<uuid>",
  "name": "Daily Standup",
  "is_active": true,
  "is_archived": false,
  "schedule": {"days": [1, 2, 3, 4, 5], "time": "09:00", "timezone": "America/New_York"},
  "start_on": "2026-07-01",
  "end_on": null,
  "frequency_type": "weekly",
  "frequency": 1,
  "frequency_advanced": "disabled",
  "frequency_cron": null,
  "reminders_max_count": 2,
  "reminders_frequency_time": 15,
  "reminders_trigger_condition": "smart_frequency",
  "reminder_tone": "standard",
  "is_anonymous": false,
  "privacy": "owner_and_members",
  "use_participant_timezone": true,
  "allow_past_responses": true,
  "allow_future_responses": false,
  "is_smart_checkin": false,
  "is_intelligence_enabled": false,
  "max_clarifying_questions": 0,
  "custom_template_intro": "Good morning! Time for standup.",
  "custom_template_outro": "Thanks — have a great day!",
  "participants": {
    "users": [{"uuid": "<uuid>", "name": "Jane Doe"}],
    "teams": [{"uuid": "<uuid>", "name": "My Team"}]
  },
  "report_channels": [
    {"id": "<uuid>", "name": "standups", "platform": "slack", "type": "channel"}
  ],
  "questions": [
    {
      "uuid": "<uuid>",
      "index": 0,
      "question": "What did you complete yesterday?",
      "question_type": "text",
      "required": true,
      "is_blocker": false,
      "short_question": "Yesterday",
      "choices": [],
      "variations": ["Recap of yesterday's work?"],
      "logic": null
    }
  ]
}
```

For `multiple_choice`, `choices` is populated as `[{"label": "...", "value": "..."}]`.

### Archiving

`dailybot checkin archive <followup_uuid> [--yes]` soft-deletes a check-in
(confirms first unless `--yes`).

### Authoring error codes

| `code` | Meaning |
|--------|---------|
| `questions_required` | Create had no questions — seed ≥ 1 with `--questions-file`/`--interactive`. |
| `checkin_requires_participant` | Create had no `--user`/`--team` — add at least one participant. |
| `intelligence_requires_smart_checkin` | `--intelligence` needs `--smart`; `--max-clarifying > 0` needs `--intelligence`. |
| `anonymous_irreversible` | Tried `--no-anonymous` on an already-anonymous check-in — not allowed. |
| `too_many_report_channels` | More than 3 `--report-channel` values. |
| `short_question_required` | `add` had neither `--short-question` nor `--ai-short-question`. |
| `invalid_frequency_type` | Used `--frequency` for a non-weekly cadence — use `--frequency-advanced`. |
| `invalid_reminder_tone` | `--reminder-tone` was not `standard`/`persuasive`. |
| `invalid_frequency_cron` | Malformed 5-field `--cron` expression. |
| `question_uuids_incomplete` | `reorder` didn't list every question UUID. |
| `unknown_field` | CLI sent a field the server doesn't recognize → suggests `dailybot upgrade`. |

### End-to-end examples

**1. Daily standup with participants + reminders, seeded from a questions file:**

```bash
# 1. Create with schedule, participants, a report channel, and reminders
dailybot checkin create -n "Daily Standup" \
  --time 09:00 --days 1,2,3,4,5 --timezone America/New_York \
  --frequency weekly --every 1 \
  --reminders 2 --reminder-interval 15 --reminder-condition smart_frequency \
  --user me@example.com --team "My Team" \
  --report-channel <channel-uuid> \
  --intro "Good morning! Time for standup." \
  --questions-file ./standup-questions.json

# 2. Verify the round-trip
dailybot checkin show <followup_uuid> --json
```

**2. Smart AI check-in with insights and capped follow-ups:**

```bash
dailybot checkin create -n "Weekly Retro" \
  --time 16:00 --days 5 --timezone America/New_York \
  --smart --intelligence --max-clarifying 3 \
  --privacy managers_and_members \
  --user me@example.com

dailybot checkin questions add <followup_uuid> \
  --type text --question "What went well this week?" \
  --short-question "Wins" --required
```

**3. Custom-cron cadence (first business day of the month) + conditional logic:**

```bash
# Custom cadence needs --frequency-advanced custom + a 5-field --cron
dailybot checkin create -n "Monthly Ops Review" \
  --frequency-advanced custom --cron "0 9 1 * *" \
  --timezone America/New_York \
  --team "My Team"

# A blocker question that jumps to a detail question when there ARE blockers
dailybot checkin questions add <followup_uuid> \
  --type boolean --question "Any blockers?" \
  --short-question "Blockers" --blocker \
  --jump-if-equals true --jump-to 2 --else-jump-to -1

# Incrementally flip one setting later (partial update — nothing else changes)
dailybot checkin config <followup_uuid> --reminders 1 --reminder-tone persuasive
```

---

## Step 4 — HTTP Fallback (when CLI is unavailable)

See [`../shared/http-fallback.md`](../shared/http-fallback.md) for base patterns.

**Important:** Check-in endpoints accept **either** Bearer token or `X-API-KEY` auth.

### List pending check-ins

```bash
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  https://api.dailybot.com/v1/cli/status/
```

### List responses (history)

```bash
# Default — ALL participants' responses in the date range (no user scoping)
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  "https://api.dailybot.com/v1/checkins/<followup_uuid>/responses/?date_start=2026-06-01&date_end=2026-06-30"

# Narrow to one participant (admin/manager callers only)
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  "https://api.dailybot.com/v1/checkins/<followup_uuid>/responses/?date_start=2026-06-01&date_end=2026-06-30&user=<user_uuid>"
```

**Scoping contract for `GET /v1/checkins/<followup_uuid>/responses/`:**

| Scenario | Query params | Result |
|----------|--------------|--------|
| See all responses | *(none)* | Every participant's responses in the date range |
| Filter to one user (admin/manager) | `?user=<user_uuid>` | Only that user's responses |
| Filter to one user (member) | `?user=<user_uuid>` | Only the caller's own responses (server-side guard) |

- The default returns **all participants' responses** — no user filter is applied.
- `?all=true` is **not needed** for check-in responses (the default already returns
  everything). It is accepted as a harmless no-op if a legacy integration still sends it.

> **Check-ins vs. forms differ.** The check-in responses endpoint defaults to
> **all participants**; the form responses endpoint
> (`GET /v1/forms/<form_uuid>/responses/`) defaults to the **caller's own** responses
> and requires `?all=true` (admin/owner with `VIEW_REPORTS`) to widen the scope. This
> asymmetry is intentional and reflects each endpoint's historical design.

### Complete a check-in

```bash
curl -s -X POST \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.dailybot.com/v1/checkins/<followup_uuid>/responses/ \
  -d '{
    "responses": [
      {"uuid": "<question-uuid>", "index": 0, "response": "Shipped the auth refactor"},
      {"uuid": "<question-uuid>", "index": 1, "response": "Starting payment integration"},
      {"uuid": "<question-uuid>", "index": 2, "response": "None"}
    ],
    "last_question_index": 2
  }'
```

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

---

## Step 5 — Confirm

After the command runs:

- **Success** — briefly confirm. Example: *"Submitted your Daily Standup check-in to Dailybot."*
- **Failure** — warn briefly. If not authenticated (exit code 3), suggest `dailybot login`.
- **Skipped** — say nothing.

---

## Non-Blocking Rule

Check-in completion must **never block your primary work**. If the CLI is missing, auth fails, the network is down, or the command errors:

1. Warn the developer briefly
2. Continue with the primary task
3. Do not retry automatically
4. Do not enter a diagnostic loop

---

## Additional Resources

- [`../shared/auth.md`](../shared/auth.md) — authentication setup
- [`../shared/http-fallback.md`](../shared/http-fallback.md) — HTTP API fallback patterns
- [`../shared/dashboard-urls.md`](../shared/dashboard-urls.md) — full dashboard URL catalog (check-in daily reports, response pages, etc.)
- **Live API spec:** `https://api.dailybot.com/api/swagger/`
- **Full agent API skill:** `https://www.dailybot.com/skill.md`
