---
name: dailybot-forms
description: List, inspect, submit, update, and transition form responses via Dailybot — including forms with workflow states and audience-scoped permissions. Also authors forms — create and configure a form (workflow states, permissions, anonymous/public/approval, ChatOps command) and manage its questions (types, report titles, variations, conditional logic). Use when the developer wants to see available forms, fill out a survey, continue an in-progress response, move a response between states, read prior responses, or create/configure a form. Do not use for daily check-ins — those go through dailybot-checkin.
version: "3.10.3"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"📋","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Forms

> **Requires `dailybot-cli >= 3.7.0`** (the skill-pack baseline). The full forms lifecycle — `form list` / `submit` / `get` / `responses` / `response get` / `update` / `transition` / `delete` — plus the structured `--json` 4xx error shape are all available. If `dailybot --version` is below 3.7.0, ask the developer to run `dailybot upgrade`. See [`../SKILL.md` § Required Dailybot CLI version](../SKILL.md#required-dailybot-cli-version) for install commands and version-check tooling.

You help developers work with the full Dailybot forms lifecycle: list, inspect, submit, update, transition between workflow states, and read prior responses. Forms are custom questionnaires created by team leads — feedback surveys, retrospectives, release checklists, approval flows, or any structured data collection. Some forms are simple "fill once and done"; others have **workflow states** (e.g. `draft → review → released`) with audience-scoped permissions on who can edit and who can transition.

This skill is distinct from daily check-ins (handled by `dailybot-checkin`) and free-text reports (handled by `dailybot-report`).

---

## Upgrade-safety contract — read this before editing forms behavior

This SKILL.md is the **universal** forms skill. It is overwritten on every upgrade of the Dailybot skill pack (managed by `skills-lock.json`). Two rules keep customer customizations safe:

| MUST | MUST NOT |
|------|----------|
| Read `.dailybot/profile.json` and honor `vars.custom_form_skills`. | Write anything outside `.agents/skills/dailybot/`. |
| Defer to a custom skill when the resolver finds a mapping. | Read, modify, or scan files under `.agents/skills/dailybot-custom/` or any other customer-owned namespace. |
| Warn (do not error) when a registered custom-skill path is missing on disk — fall back to the generic flow. | Send `.dailybot/profile.json` contents (especially `vars`) in any report / payload to the server. |
| Document this contract verbatim here. | Embed customer-specific logic in this universal skill — if you find yourself writing `if form.name == "Release Form":`, the right answer is a custom skill under `.agents/skills/dailybot-custom/`. |

Customer-authored form skills live at `.agents/skills/dailybot-custom/<name>/SKILL.md`. The universal skill MUST defer to them; never copy customer logic into this file.

---

## Auth model — API key or login

All form commands accept **either** a Bearer login session (`dailybot login`) **or** an org API key (`DAILYBOT_API_KEY`). Access is scoped to the acting identity's permissions (the server resolves the API key's owner) — they only see forms (and responses) they have access to, and the server enforces every audience check on the API side.

If the developer has only an API key, form commands still work — the CLI falls back to `X-API-KEY`.

---

## When to Use

- The developer asks "what forms do I have?", "list my forms", "show available surveys"
- The developer asks to "fill out the retro form", "submit the feedback survey", "answer the pulse check"
- The developer wants to **continue** an in-progress form response: "keep filling the release form", "update my draft"
- The developer wants to **move a response forward**: "mark the release as approved", "transition to released", "send for review"
- The developer wants to **read prior responses**: "show me the last release form", "what was answered last time?"
- The developer wants to **delete** a response they own

Do **not** use this skill for daily standup check-ins — route those to `dailybot-checkin`. Forms are ad-hoc, periodic, or workflow-driven; check-ins are recurring daily/weekly rituals tied to follow-ups.

---

## Step 1 — Verify Setup

Read and follow the authentication steps in [`../shared/auth.md`](../shared/auth.md). That file covers CLI installation, login, API key setup, and agent profile configuration.

**Additionally**, confirm at least one credential is present (a login session or an API key):

```bash
dailybot status --auth 2>&1
```

If the output shows a logged-in user session **or** a configured API key, proceed. Otherwise guide them through `dailybot login` (see auth.md) or ask them to set `DAILYBOT_API_KEY`.

A scripted preflight that does both at once and exits with code `3` if unauthenticated:

```bash
dailybot status --auth >/dev/null 2>&1 || { echo "Run: dailybot login"; exit 3; }
```

If auth fails or the developer declines, skip and continue with your primary task.

---

## Step 2 — Lifecycle Decision Tree

When the developer asks anything form-related, walk this tree before acting:

```
1. Identify the target form by name or slug (or pick from a list).
2. Run `dailybot form list --json` to find its UUID and confirm visibility.
3. Run `dailybot form get <form_uuid> --json` to read questions, the `workflow`
   object (`null` or `{enabled, states}`), audience configuration, and the form's slug.
4. RESOLVER: check .dailybot/profile.json → vars.custom_form_skills.
   - If a custom skill is registered for this form (by UUID or by slug),
     LOAD THAT SKILL'S SKILL.md and follow its instructions INSTEAD of
     continuing the generic flow.
   - Otherwise, continue.
5. Decide whether to continue an existing response or start fresh:
   - `dailybot form responses <form_uuid> --latest --json`
   - If a response exists and its `current_state` is NOT terminal
     (or the form allows reopening), prefer the update + transition path.
   - Otherwise, submit a new response.
6. After every mutating call, re-read `current_state` and `allowed_transitions`
   on the response to decide the next move (update? transition? done?).
```

The resolver step (4) is the customer-extension hook. See **Step 7 — Custom-skill resolver** below.

---

## Step 3 — List Available Forms

```bash
dailybot form list --json
```

Returns all forms in the caller's organization. Every org member sees every org form; capabilities (editing, response visibility, state changes) are governed by each form's permissions. Pass `--mine` to narrow to only your own forms. (If a developer reports "I only see a handful of my forms," check `dailybot --version` and have them `dailybot upgrade` — older CLIs had a server-side visibility bug.) The shape is stable and machine-readable:

```json
[
  {
    "uuid": "<form-uuid>",
    "slug": "team-feedback",
    "name": "Team Feedback",
    "workflow": null,
    "questions": [
      {
        "uuid": "<question-uuid>",
        "question": "How was your week?",
        "question_type": "text_field"
      }
    ]
  },
  {
    "uuid": "<form-uuid>",
    "slug": "code-release-form",
    "name": "Code Release Form",
    "workflow": { "enabled": true, "states": [ ... ] },
    "questions": [ ... ]
  }
]
```

> The `slug` field is stable across environments (dev / staging / prod), while `id` rotates per environment. Prefer `slug` for any persistent mapping you keep across deployments. See the resolver in Step 7.

### Pagination, search, and date filters

> **Note:** the shared list query flags below are part of the `dailybot-cli >= 3.7.0` baseline. Older CLIs
> return the full list with no filtering.

`form list` accepts the **full shared list query flag set** — pagination
(`--page`, `--page-size`, `--all`, `--limit`), search (`--search` / `--grep`),
and date range (`--since`, `--until`, `--date`, `--last-week`, `--today`). With
no flags it fetches everything. The complete flag table, the
`{count, next, previous, results}` envelope, and the `Showing X of N` footer are
documented once in [`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md).

```bash
# Search forms by name, restricted to a date range:
dailybot form list --search retro --since 2026-07-01 --json

# Fetch every page explicitly (equivalent to the no-flag default):
dailybot form list --all --json

# One explicit page of 20:
dailybot form list --page 2 --page-size 20 --json
```

### Filter by owner — `--mine` and `--owner`

Pass **`--mine`** to narrow the result to only the forms **you own**, or
**`--owner`** (repeatable) to filter by specific owners. `--owner` accepts
a UUID, email, or name — non-UUID values are resolved via the org directory.
The two flags can be combined (AND semantics with every other filter).

```bash
# Only the forms I own:
dailybot form list --mine --json

# Forms owned by a specific person (by name):
dailybot form list --owner "Jane Doe" --json

# Forms owned by two people (by UUID):
dailybot form list --owner <uuid-1> --owner <uuid-2> --json
```

> **Deprecation:** the `--filter me` scope is deprecated server-side. Use
> `--mine` or `--owner` instead — `--filter me` still works but maps to
> the legacy `filter=me` parameter.

### Form owners picker — `form owners`

A lightweight endpoint to discover which org members own at least one form,
without pulling the full member directory.

```bash
dailybot form owners                     # table of owners
dailybot form owners --search jane       # search by name/email
dailybot form owners --json              # machine-readable
```

Each result has `uuid`, `full_name`, `image`, `role`, and optionally `email`
(email is only visible to admins/managers — the CLI must not assume it exists).

### Server-side filtering, sorting, and archived forms

| Flag | Values | Description |
|------|--------|-------------|
| `--filter` | `all`, `public`, `approval`, `workflow`, `archived` | Scope filter (server-side). `me` still works but is deprecated. |
| `--owner` | UUID, email, or name (repeatable) | Filter by form owner(s). Max 50. |
| `--order` | `alphabetical`, `recent`, `total` | Sort field (`total` = total response count). |
| `--ascending` / `--asc` | flag | Sort ascending (default: descending). |
| `--include-questions` | flag | Include question definitions in each form. |
| `--include-archived` | flag | Include archived forms (hidden by default). |

```bash
# Workflow-enabled forms, sorted alphabetically ascending:
dailybot form list --filter workflow --order alphabetical --asc --json

# Only forms with approval flow:
dailybot form list --filter approval --json

# Public forms sorted by total responses:
dailybot form list --filter public --order total --json

# Archived forms:
dailybot form list --filter archived --json

# Include question definitions:
dailybot form list --include-questions --json
```

> **The envelope is unconditional.** `GET /v1/forms/` and the responses endpoint
> below always return `{count, next, previous, results}`; no query parameter is
> needed. See the shared doc.

### Present forms to the developer

When forms are found:

> "You have **2 forms** available in Dailybot:
>
> 1. **Team Feedback** — 3 questions (no workflow)
> 2. **Code Release Form** — 8 questions (workflow: draft → review → released)
>
> Which one would you like to work with?"

When no forms are found:

> "No forms are available for you right now."

---

## Step 4 — Inspect a Form

```bash
dailybot form get <form_uuid> --json
```

Use this **before** submitting or updating. It returns the form's full configuration including workflow definition and the audience-based permission flags. Treat this output as the source of truth for "what can I do on this form?".

### JSON shape (workflow-enabled form)

The workflow definition is nested under the `workflow` key: `null` when the form has no
workflow, or `{"enabled": true, "states": [...]}` when it does. Each state carries
`{key, label, color, order}` — the ordered list defines the forward progression (the
first state is the initial one, the last is the final/terminal one). `allow_reopen_from_final_state`
is a **top-level** boolean. Audience permissions also live at the top level. All of it is
server-defined.

```json
{
  "uuid": "<form-uuid>",
  "slug": "code-release-form",
  "name": "Code Release Form",
  "allow_reopen_from_final_state": false,
  "state_change_permission": { "audience": "...", "...": "..." },
  "edit_permission":         { "audience": "...", "...": "..." },
  "view_reports_permission": { "audience": "...", "...": "..." },
  "workflow": {
    "enabled": true,
    "states": [
      {"key": "draft",    "label": "Draft",    "color": "#9CA3AF", "order": 0},
      {"key": "review",   "label": "Review",   "color": "#F59E0B", "order": 1},
      {"key": "released", "label": "Released", "color": "#10B981", "order": 2}
    ]
  },
  "questions": [ ... ]
}
```

> A form with no workflow returns `"workflow": null`. The legacy `workflow_enabled`
> boolean and `workflow_config` object are **gone** — read `workflow` and, when present,
> `workflow.enabled` / `workflow.states`. The per-response moves the current caller can make
> still arrive as `allowed_transitions` on each **response** payload (Steps 5–6) — the server
> computes those from the ordered states and the caller's audience.

### Audience permissions

The three `*_permission` fields are server-evaluated. Treat them as **opaque** in this skill — never re-implement the audience evaluation client-side. The server returns `can_change_state`, `can_edit`, and `can_view_reports` (or equivalent) on each response payload as the decided result. Trust those booleans.

---

## Step 5 — Workflow-state Vocabulary

When the form has a workflow (`workflow.enabled: true`), the agent must understand five fields that appear on every response payload. Surface them when they affect what the developer can do next:

| Field | Meaning | Agent behavior |
|-------|---------|----------------|
| `current_state` | The effective state of this response right now. | Display the label. Drive the next action from it. |
| `allowed_transitions` | `[{to_state, label}]` — the moves the **current caller** can make from `current_state`. Server-computed; honors audience. | Pick one and confirm with the developer before invoking `transition`. If the list is empty, no transitions are available to the caller. |
| `can_change_state` | Boolean — whether the caller is in the audience for state changes. | If `false`, do not offer the transition path. Tell the developer the audience excludes them. |
| `allow_reopen_from_final_state` | Form-level boolean. `false` (default) means the terminal state is sticky — once reached, the response cannot move out. | If `false` and `current_state` is a final state, do not attempt a transition. If `true`, the response can transition back to a non-final state. |
| `state_history` | Append-only list of `{from_state, to_state, actor_name, at}` entries. | Surface the latest entry (who moved it last, when) when relevant for context. |

> Never infer state transitions from labels or names — the only valid moves are the ones in `allowed_transitions`. The server's audience checks may legitimately exclude transitions the developer *thinks* should be available.

---

## Step 5.5 — Authoring forms (create / configure / questions)

> **Requires `dailybot-cli >= 3.7.0`** (the skill-pack baseline). The full authoring surface — `form create`, `form config` (workflow states, the three permission audiences, anonymous/public/brand/require-identity with `public_url`, approval + approvers, the ChatOps command), `form archive`, the `form questions add|edit|delete|reorder` group, resolving people by email, `--no-approvers`, the 3 report-channel cap, and the **create requires ≥ 1 question** rule (`questions_required`) — is all available. If `dailybot --version` is below 3.7.0, ask the developer to run `dailybot upgrade`.

Everything above this point *reads* and *responds to* forms. This section *builds and reshapes* them. An agent with the right permissions can now create a form, wire up its workflow states, permission audiences, approval flow, and ChatOps command, and manage its questions — all end-to-end from the CLI, without opening the Dailybot webapp.

Permissions are server-enforced. Creating and configuring forms typically requires org **admin / manager** rights (or an API key whose owner has them). If the acting identity lacks the rights, the server returns a 403 — surface it and fall back to the non-blocking rule; never re-implement the permission check client-side.

### One-shot `create` vs. incremental `config`

There are two ways to reach the same configured form. Pick based on how much you know up front:

| Approach | Command | When to use |
|----------|---------|-------------|
| **One-shot** | `dailybot form create -n NAME [all config flags] [--questions-file / --interactive]` | You already know the full shape (name, workflow, permissions, seed questions). Everything lands in a single call. |
| **Incremental** | `dailybot form create -n NAME` → then one or more `dailybot form config <uuid> [flags]` → then `form questions add …` | You're building up the form conversationally, or reconfiguring an existing one. |

- `form create` and `form config` accept the **same config flags** (listed below). `create` additionally accepts the question-seeding flags (`--questions-file`, `--interactive`, `--ai-short-question`); `config` does not seed questions — use the `form questions` group for that.
- `form config` is a **full partial-update**: send only the flags you want to change; anything you omit is left untouched. It is a strict **superset of `form edit`** (which only touches name + report channels). Prefer `form config` for anything beyond a name/channel tweak.
- **`--report-channel` and the permission/approver objects use full-replace semantics** — see the callouts below. Most other scalar flags are simple set-if-passed.

A form **must have at least one question at create time** — `POST` create with a missing/empty `questions` array is rejected with `400 {"code": "questions_required"}` ("A form must have at least one question."). Seed at least one question inline on create (see the `--questions-file` schema below); you can add, edit, remove, and reorder questions afterward via the `form questions` group. (Even a workflow-only or approval-routing form needs a seed question.)

### Config flag reference

Both `form create` and `form config` accept these. Grouped by concern:

**Basics**

| Flag | Meaning |
|------|---------|
| `-n`, `--name` | Form name (min length enforced — too short → `form_name_too_short`). |
| `--active` / `--inactive` | Whether the form is active (accepting responses). |
| `--report-channel UUID` | Chat channel to post responses to. **Repeatable, max 3.** On `config` this **REPLACES** the entire set — pass all channels you want every time. More than 3 → `too_many_report_channels`. |

**Sharing / behavior**

| Flag | Meaning |
|------|---------|
| `--anonymous` / `--no-anonymous` | Collect responses anonymously. Freely toggleable in **both** directions (unlike check-in anonymity, which is irreversible once on). |
| `--public` / `--no-public` | Allow responses through a public shared link (no Dailybot account needed). Surfaces `public_url` when on — see **Public forms** below. |
| `--brand` / `--no-brand` | Brand the public form with the org logo. |
| `--require-identity` / `--no-require-identity` | Make email + name mandatory on public responses. |
| `--reopen-from-final` / `--no-reopen-from-final` | Set the top-level `allow_reopen_from_final_state` boolean (whether a response can move back out of a terminal workflow state). |

**Workflow**

| Flag | Meaning |
|------|---------|
| `--state "Label:#color"` | Add a workflow state. **Repeatable and ordered** — position defines the sequence. Passing any `--state` **enables** the workflow. Max 20 states. |
| `--no-workflow` | Turn the workflow off (clears states). |

**Permissions** (three independent audiences)

| Flag | Meaning |
|------|---------|
| `--can-edit MODE` | Who can edit responses. `MODE` = `everyone` \| `owner_and_admins` \| `restricted`. |
| `--can-see MODE` | Who can see responses/reports. Same `MODE` values. |
| `--can-change-states MODE` | Who can transition responses between states. Same `MODE` values. |
| `--can-edit-user`, `--can-edit-team` | For `restricted` edit: name the allowed users/teams. |
| `--can-see-user`, `--can-see-team` | For `restricted` view. |
| `--change-states-user`, `--change-states-team` | For `restricted` state-changes. |

Users accept **name / email / UUID**; teams accept **name / UUID**. Passing any `-user`/`-team` flag **implies `restricted` mode** for that audience — you don't have to also pass `--can-edit restricted`. Each audience object is **full-replace**: the users/teams you send become the new value; omitting a key clears it. A `restricted` audience with **empty** user + team lists effectively means "owner + admins only".

**Approval flow**

| Flag | Meaning |
|------|---------|
| `--approval` / `--no-approval` | File new submissions for approval before they count as final. |
| `--approver-user` | An approver by name / email / UUID. **Repeatable.** |
| `--approver-team` | An approver team. **Repeatable.** |
| `--no-approvers` | Clear the approver list. |

The approver list is **full-replace** (`{user_uuids, team_uuids}`) — pass every approver each time you set it.

**ChatOps command**

| Flag | Meaning |
|------|---------|
| `--command NAME` | The chat shortcut that opens the form (e.g. `release`, invoked as `@dailybot release`). Charset `[a-z0-9][a-z0-9_-]{0,30}`; unique per org. Invalid → `invalid_command`; taken by another form → `command_already_exists`. |
| `--no-command` | Remove the command. |

**Question seeding** (`create` only)

| Flag | Meaning |
|------|---------|
| `--questions-file PATH` | Seed questions from a JSON array (see the questions-file schema below). Max 50. |
| `--interactive` | Walk through adding questions one at a time. |
| `--ai-short-question` | Let the server auto-generate the report title for seeded questions that omit one. |

### Workflow states — write shape vs. read shape

The write shape and the read shape are deliberately asymmetric:

- **Write** (`--state "Label:#color"`): you send only `{label, color}`, ordered by flag position. The server **derives** `key` (a slugified label) and `order` (the position) for you.
- **Read** (`form get`): each state comes back as `{key, label, color, order}` inside `workflow.states` (with `workflow.enabled: true`).

```bash
# Enable a 3-state release workflow (order follows flag order):
dailybot form config <form_uuid> \
  --state "Draft:#9CA3AF" \
  --state "Review:#F59E0B" \
  --state "Released:#10B981"

# Turn the workflow off entirely:
dailybot form config <form_uuid> --no-workflow
```

- A form with `--state` flags has `workflow.enabled: true`; enabling a workflow with no states is invalid → `workflow_requires_states`. A malformed `"Label:#color"` spec → `invalid_workflow_state`.
- Max 20 states.

### Permission audiences — the three independent controls

`--can-edit`, `--can-see`, and `--can-change-states` are **independent** — a form can let everyone see responses but restrict state changes to two people. Each takes one of:

| MODE | Meaning |
|------|---------|
| `everyone` | Anyone with form access. |
| `owner_and_admins` | The form owner plus org admins. |
| `restricted` | Only the named users/teams (empty lists ⇒ owner + admins). |

```bash
# Everyone can see; only two named people can change states; owner+admins edit.
dailybot form config <form_uuid> \
  --can-see everyone \
  --can-edit owner_and_admins \
  --change-states-user jane@example.com \
  --change-states-user "John Doe" \
  --change-states-team "Release Managers"
```

Passing `--change-states-user`/`--change-states-team` above **implied** `restricted` for that audience — no separate `--can-change-states restricted` needed. Remember full-replace semantics: the next time you set that audience, list **everyone** who should be in it. Invalid audience mode → `invalid_permission_audience`.

### Approval + command

```bash
# Route new submissions through an approver team, and bind a ChatOps shortcut.
dailybot form config <form_uuid> \
  --approval \
  --approver-team "Release Managers" \
  --approver-user lead@example.com \
  --command release            # opens the form via `@dailybot release`
```

- Approvers are full-replace. `--no-approvers` clears the list; `--no-approval` turns the flow off. Invalid approver reference → `invalid_approvers`.
- The command name is unique per org: `command_already_exists` if another form already claims it, `invalid_command` if it violates the charset. `--no-command` unbinds it.

### Public forms and `public_url`

When `--public` is on, `form get` (and the output right after `form config --public`) includes a `public_url` — an absolute, shareable link anyone can open to submit a response:

```
https://app.dailybot.com/forms/<form-uuid>/responses/create/
```

`public_url` is `null` when `--no-public`. Pair `--public` with `--require-identity` if you need submitter email + name, and `--brand` to show the org logo.

```bash
# Anonymous public NPS survey with a branded, shareable link:
dailybot form create -n "Q3 NPS Survey" \
  --anonymous --public --brand --require-identity \
  --report-channel <channel-uuid>
# → the response includes public_url — share it with respondents.
```

### Question authoring

Questions are managed with the `form questions` subgroup. The question model is **identical to check-in questions**.

```bash
dailybot form questions add <form_uuid> --type TYPE --question TEXT [flags]
dailybot form questions edit <form_uuid> <question_uuid> [flags]
dailybot form questions delete <form_uuid> <question_uuid>
dailybot form questions reorder <form_uuid> <q_uuid> <q_uuid> ...
```

**Types** — the complete catalog is exactly four:

| `--type` | Notes |
|----------|-------|
| `text` | Free-text answer. |
| `multiple_choice` | Requires `--options "A,B,C"` (comma-separated). |
| `boolean` | Yes/No. **No options.** |
| `numeric` | Integer or decimal. |

**Common flags**

| Flag | Meaning |
|------|---------|
| `--question TEXT` | The question prompt. |
| `--required` / `--optional` | Whether an answer is mandatory. |
| `--blocker` / `--no-blocker` | Whether leaving it blank blocks submission. |
| `--short-question "Title"` | **Report title** (≤ 512 chars). **Required on `add`** — see below. |
| `--ai-short-question` | Let the server generate the report title instead of `--short-question`. |
| `--variation TEXT` | Alternate phrasing shown to different respondents. **Repeatable, up to 10.** |
| `--options "A,B,C"` | Choices for `multiple_choice`. |
| `--logic-file PATH` / inline jump flags | Conditional logic — see below. |

> **Report title is mandatory on `add`.** Every question needs a report title: pass **either** `--short-question "Title"` **or** `--ai-short-question`. Explicit titles are preserved; AI only fills blanks. Passing neither → `short_question_required`. On `edit` the report title is **not** required (edits are partial).

**Conditional logic** lets a question jump forward, or trigger another check-in or form, based on the answer. Provide it inline (simple single-rule jump) or via `--logic-file` (full control):

```bash
# Inline: if the answer equals "No", jump to question index 5; else jump to 3.
dailybot form questions add <form_uuid> \
  --type multiple_choice --options "Yes,No" \
  --question "Did all tests pass?" \
  --short-question "Tests passed" \
  --jump-if-equals "No" --jump-to 5 --else-jump-to 3
```

The full logic object (what `--logic-file` contains, and what the inline flags build under the hood):

```json
{
  "rules": {
    "rules_if": [
      {
        "conditions": [
          {"operator": "is_equal_to", "comparison_value": "No", "logic_connector": "and"}
        ],
        "then": {"action": "jump_to", "target": 5}
      }
    ],
    "rules_else": {"action": "jump_to", "target": -1}
  }
}
```

- `rules_else` is **required**. `target: -1` means "jump to the end" (finish the form).
- **Jumps are forward-only**: `target` must be greater than the current question index, or `-1`. On delete/reorder the server **auto-clamps** dangling targets so logic never points at a removed/moved question.

**Operators** allowed per question type:

| Type | Operators |
|------|-----------|
| `text` | `is_equal_to`, `is_not_equal_to`, `contains`, `not_contains`, `begins_with`, `not_begins_with`, `ends_with`, `not_ends_with` |
| `numeric` | `is_equal_to`, `is_not_equal_to`, `lower_than`, `lower_or_equal_than`, `greater_than`, `greater_or_equal_than` |
| `multiple_choice` / `boolean` | `is_equal_to`, `is_not_equal_to` |

**Logic connectors** (`logic_connector` on each condition):

| Type | Connectors |
|------|------------|
| `text`, `numeric`, `boolean` | `and` / `or` |
| `multiple_choice` | `or` only |

> `boolean` comparison values are JSON `true` / `false` (not strings).

**Actions** (`then.action` and `rules_else.action`):

| Action | `target` |
|--------|----------|
| `jump_to` | An integer question index (forward-only, or `-1` for end). |
| `trigger_checkin` | A check-in UUID — firing this question routes the respondent into that check-in. |
| `trigger_form` | A form UUID — a form question can chain into **another form**. |

A `trigger_form` example — when the release is a hotfix, chain into the hotfix intake form:

```json
{
  "rules": {
    "rules_if": [
      {
        "conditions": [
          {"operator": "is_equal_to", "comparison_value": "Hotfix", "logic_connector": "or"}
        ],
        "then": {"action": "trigger_form", "target": "<hotfix-form-uuid>"}
      }
    ],
    "rules_else": {"action": "jump_to", "target": -1}
  }
}
```

**Editing and reordering**

```bash
# Partial edit — report title NOT required here:
dailybot form questions edit <form_uuid> <question_uuid> \
  --question "Did every test pass in CI?" --required

# Reorder — you MUST pass the COMPLETE set of question UUIDs in the new order.
dailybot form questions reorder <form_uuid> <q3> <q1> <q2>
```

An incomplete `reorder` (missing any of the form's question UUIDs) → `question_uuids_incomplete`.

### `--questions-file` schema (seed on `create`)

A JSON array (max 50 objects). Each object accepts these keys (aliases shown with `/`):

| Key | Meaning |
|-----|---------|
| `question_type` / `type` | One of `text`, `multiple_choice`, `boolean`, `numeric`. |
| `question` / `label` | The prompt text. |
| `options` | Choices array (for `multiple_choice`). |
| `required` | Boolean. |
| `is_blocker` | Boolean. |
| `short_question` | Report title (omit + rely on `--ai-short-question` to auto-fill). |
| `variations` | Array of alternate phrasings (≤ 10). |
| `logic` | The conditional-logic object (same shape as above). |

```json
[
  {
    "question_type": "text",
    "question": "What service is being released?",
    "short_question": "Service",
    "required": true,
    "is_blocker": true
  },
  {
    "type": "multiple_choice",
    "label": "Release kind?",
    "options": ["Standard", "Hotfix"],
    "short_question": "Kind",
    "logic": {
      "rules": {
        "rules_if": [
          {"conditions": [{"operator": "is_equal_to", "comparison_value": "Hotfix", "logic_connector": "or"}],
           "then": {"action": "trigger_form", "target": "<hotfix-form-uuid>"}}
        ],
        "rules_else": {"action": "jump_to", "target": -1}
      }
    }
  }
]
```

```bash
dailybot form create -n "Code Release Form" \
  --questions-file ./release-questions.json --ai-short-question
```

### `form get` — canonical detail JSON

`dailybot form get <form_uuid> --json` returns the full authoritative shape. This is the read contract for everything the authoring flags write:

```json
{
  "uuid": "<form-uuid>",
  "name": "Code Release Form",
  "is_active": true,
  "is_archived": false,
  "is_anonymous": false,
  "allow_public_responses": true,
  "public_url": "https://app.dailybot.com/forms/<form-uuid>/responses/create/",
  "require_email_and_name": true,
  "brand_with_logo": true,
  "allow_reopen_from_final_state": false,
  "workflow": {
    "enabled": true,
    "states": [
      {"key": "draft",    "label": "Draft",    "color": "#9CA3AF", "order": 0},
      {"key": "review",   "label": "Review",   "color": "#F59E0B", "order": 1},
      {"key": "released", "label": "Released", "color": "#10B981", "order": 2}
    ]
  },
  "who_can_edit":            {"mode": "owner_and_admins"},
  "who_can_see_responses":   {"mode": "everyone"},
  "who_can_change_states":   {"mode": "restricted", "user_uuids": ["<uuid>"], "team_uuids": ["<uuid>"]},
  "use_for_approval": true,
  "approvers": {"user_uuids": ["<uuid>"], "team_uuids": ["<uuid>"]},
  "command_enabled": true,
  "command": "release",
  "report_channels": [
    {"id": "<channel-uuid>", "name": "releases", "platform": "slack", "type": "channel"}
  ],
  "questions": [
    {
      "uuid": "<question-uuid>",
      "index": 0,
      "question": "What service is being released?",
      "question_type": "text",
      "required": true,
      "is_blocker": true,
      "short_question": "Service",
      "choices": [],
      "variations": [],
      "logic": null
    }
  ]
}
```

- `workflow` is `null` for non-workflow forms, else `{enabled, states:[{key,label,color,order}]}`.
- `who_can_edit` / `who_can_see_responses` / `who_can_change_states` each carry `{mode}` and, when `restricted`, `{user_uuids, team_uuids}`.
- `multiple_choice` questions expose `choices: [{label, value}]`; other types return `choices: []`.

### Archiving a form

```bash
dailybot form archive <form_uuid> --yes
```

Soft-deletes the form (`is_archived: true`). Confirm before invoking — archived forms disappear from `form list`. This does not hard-delete responses.

### Authoring error codes

| Server `code` | Meaning / fix |
|---------------|---------------|
| `questions_required` | `create` had no questions. A form needs ≥ 1 question at create time — seed with `--questions-file`/`--interactive`. |
| `too_many_report_channels` | More than 3 `--report-channel` values. Trim to ≤ 3. |
| `short_question_required` | A `questions add` omitted both `--short-question` and `--ai-short-question`. Supply one. |
| `workflow_requires_states` | Tried to enable a workflow with no states. Pass at least one `--state`. |
| `invalid_workflow_state` | A `--state "Label:#color"` spec is malformed. Fix the label/color. |
| `invalid_permission_audience` | A `--can-*` MODE is not `everyone`/`owner_and_admins`/`restricted`. |
| `invalid_approvers` | An approver reference didn't resolve. Check the name/email/UUID. |
| `invalid_command` | ChatOps command violates `[a-z0-9][a-z0-9_-]{0,30}`. |
| `command_already_exists` | Another form already owns that command name. Pick another. |
| `form_name_too_short` | `--name` is below the minimum length. |
| `question_uuids_incomplete` | `reorder` didn't include every question UUID. Pass the complete set. |
| `unknown_field` | An unrecognized key in `--questions-file` / `--logic-file`. Remove it. |

### End-to-end authoring examples

**A — Release checklist form with workflow, permissions, and a ChatOps command**

```bash
# 1. Create the shell.
FID=$(dailybot form create -n "Code Release Form" --active --json | jq -r '.uuid')

# 2. Wire the workflow, permissions, report channel, and command in one config call.
dailybot form config "$FID" \
  --state "Draft:#9CA3AF" --state "Review:#F59E0B" --state "Released:#10B981" \
  --can-see everyone \
  --can-edit owner_and_admins \
  --change-states-team "Release Managers" \
  --report-channel <channel-uuid> \
  --command release

# 3. Add questions.
dailybot form questions add "$FID" --type text \
  --question "What service is being released?" --short-question "Service" --required --blocker
dailybot form questions add "$FID" --type multiple_choice --options "Standard,Hotfix" \
  --question "Release kind?" --short-question "Kind"

# 4. Verify.
dailybot form get "$FID" --json | jq '{workflow, command, questions: (.questions|length)}'
```

**B — Anonymous public NPS survey (shareable link)**

```bash
dailybot form create -n "Q3 NPS Survey" \
  --anonymous --public --brand --require-identity \
  --report-channel <channel-uuid> --json | jq -r '.public_url'
# → share the printed public_url with respondents.

# Add the score question:
dailybot form questions add <form_uuid> --type numeric \
  --question "How likely are you to recommend us (0–10)?" --short-question "NPS score" --required
```

**C — Approval-routing intake form**

```bash
# A workflow + approval routing form. Even routing forms need >= 1 question at
# create time (questions_required), so seed one with --questions-file.
dailybot form create -n "Budget Approval" \
  --questions-file budget-questions.json \
  --approval \
  --approver-user finance-lead@example.com \
  --approver-team "Finance" \
  --state "Requested:#9CA3AF" --state "Approved:#10B981" \
  --can-change-states restricted \
  --change-states-team "Finance"
```

---

## Step 6 — Find In-Progress Responses

Before submitting a new response, check whether there's an in-progress one to continue:

```bash
dailybot form responses <form_uuid> --latest --json
```

### Continue-or-start idiom

The standard shell pattern for "continue if there's an in-progress response, otherwise create one":

```bash
RID=$(dailybot form responses <form_uuid> --latest --json | jq -r '.[0].uuid // empty')
if [ -z "$RID" ]; then
  RID=$(dailybot form submit <form_uuid> --content '{...}' --yes --json | jq -r '.uuid')
fi
# $RID is now the response UUID — pass it to subsequent update / transition calls.
```

Useful flags:

| Flag | Description |
|------|-------------|
| `--latest` | Return only the most recent response visible to the caller. |
| `--state STATE` | Filter to responses in a specific workflow state. Pass the **state key** (`draft`), not the label (`Draft`) — read the keys from `workflow.states[].key` on `form get`. Filtering is server-side. On a form with no workflow the API returns `400 invalid_workflow_state`. |
| `--all` | List everyone's responses (requires VIEW_REPORTS permission — admin/owner only; a member receives 403). |
| `--search TEXT` | Search response content and submitter name/email. Max 256 chars. Does **not** search anonymous member identities (privacy preserved). |
| `--json` | Machine-readable output (stable shape). |

> **`form responses` search.** The `--search` / `--grep` flag
> filters responses case-insensitively — handy for finding a past response by a
> service name or keyword. Like `form list`, this endpoint
> (`GET /v1/forms/<uuid>/responses/`) returns the `{count, next, previous,
> results}` envelope with a `Showing X of N` footer. It also takes `--page` /
> `--page-size` / `--limit`. Careful: `--all` here means **every author's**
> responses (admin/owner only), not every page.
> See [`../shared/list-query-and-errors.md`](../shared/list-query-and-errors.md).

### Advanced response filters

| Flag | Values | Description |
|------|--------|-------------|
| `--source` | CSV: `member`, `anonymous`, `automation`, `public` | Filter by submission origin (OR semantics within the group). |
| `--submitter` | CSV of UUIDs (max 50) | Filter by specific submitter user UUIDs. |
| `--flow-status` | `pending`, `approved`, `denied` | Approval flow status filter. Silently ignored if the form has no approval flow. |
| `--order` | `recent`, `oldest` | Sort by creation time. |
| `--ascending` / `--asc` | flag | Sort ascending (alias for `--order oldest`). |
| `--user UUID` | single UUID | Filter to one user's responses (admin/owner only). |
| `--from DATE` | YYYY-MM-DD | Responses on/after this date. |
| `--to DATE` | YYYY-MM-DD | Responses on/before this date. |

**Submission sources** — every response belongs to exactly one bucket:

| Source | Meaning |
|--------|---------|
| `member` | Identified org member submitted normally. |
| `anonymous` | Org member submitted anonymously (`collect_responses_anonymously=true`). |
| `automation` | Submitted via API/CLI with `--automation` (`is_dailybot_bot=true`). |
| `public` | Submitted via the public form URL by an external guest. |

All filters compose with **AND** across groups and **OR** within each group:
`--source "member,automation" --flow-status pending --search "deploy"` → responses that are `(member OR automation) AND pending AND contain "deploy"`.

```bash
# All automation submissions:
dailybot form responses <form_uuid> --all --source automation --json

# Multiple sources (OR): automation OR public:
dailybot form responses <form_uuid> --all --source "automation,public" --json

# Approval: only pending:
dailybot form responses <form_uuid> --all --flow-status pending --json

# Combined: member responses, approved, containing "sprint":
dailybot form responses <form_uuid> --all --source member --flow-status approved --search "sprint" --json

# Sorted oldest first in a date range:
dailybot form responses <form_uuid> --all --order oldest --from 2026-07-01 --to 2026-07-10 --json
```

### JSON shape (single response)

```json
{
  "uuid": "<response-uuid>",
  "form_id": "<form-uuid>",
  "current_state": "review",
  "allowed_transitions": [
    {"to_state": "released", "label": "Mark released"},
    {"to_state": "draft",    "label": "Back to draft"}
  ],
  "can_change_state": true,
  "state_history": [
    {"from_state": null,     "to_state": "draft",  "actor_name": "Sergio F.", "at": "2026-05-25T14:22:11Z"},
    {"from_state": "draft",  "to_state": "review", "actor_name": "Sergio F.", "at": "2026-05-26T09:05:42Z"}
  ],
  "content": {
    "<question-uuid>": "Auth service v2.1",
    "<question-uuid>": "Sergio, Carolina"
  }
}
```

### Reading a single response

```bash
dailybot form response get <form_uuid> <response_uuid> --json
```

---

## Step 7 — Custom-skill Resolver (`vars.custom_form_skills`)

If the developer's repo registers a custom skill for the form being worked with, **load and follow that custom skill instead of continuing the generic flow**. This is what keeps form-specific logic out of this universal file.

### Where the mapping lives

In `.dailybot/profile.json` at the repo root, under the CLI's free-form `vars` namespace:

```json
{
  "name": "My Team",
  "default_metadata": { "repo": "my-service" },
  "vars": {
    "active_organization_uuid": "<your-org-uuid>",
    "custom_form_skills": {
      "by_uuid": {
        "<form-uuid>": ".agents/skills/dailybot-custom/coderelease-form"
      },
      "by_slug": {
        "code-release-form": ".agents/skills/dailybot-custom/coderelease-form"
      }
    }
  }
}
```

> `vars` is the CLI's official escape hatch for repo-local data the CLI carries but doesn't act on — see [DailybotHQ/cli README → Repo-level profile](https://github.com/DailybotHQ/cli#repo-level-profile-dailybotprofilejson). Nesting under `vars` keeps this convention from colliding with future top-level CLI keys.

### Resolution algorithm

Run this **after** `dailybot form get` (you need the slug):

```python
def resolve_custom_form_skill(profile, form):
    custom = ((profile or {}).get("vars") or {}).get("custom_form_skills") or {}
    by_uuid = custom.get("by_uuid") or {}
    by_slug = custom.get("by_slug") or {}

    # 1) UUID-first — exact match against the form's current UUID.
    if form["id"] in by_uuid:
        return by_uuid[form["id"]]

    # 2) Slug fallback — survives across dev / staging / prod where UUIDs differ.
    slug = form.get("slug")
    if slug and slug in by_slug:
        return by_slug[slug]

    # 3) None — caller continues with the generic flow.
    return None
```

### Behavior rules

- Resolver runs **after** `dailybot form get` returns the form payload (slug must be available).
- If the resolver returns a path, **load `<path>/SKILL.md`** and follow its instructions instead of continuing here.
- If no profile / no `custom_form_skills` block / no match → generic flow continues.
- If the registered path does **not** exist on disk → emit a warning to the developer and fall through to the generic flow. Do **not** hard-fail; missing custom skills must not block form work.
- Never read other paths under `.agents/skills/dailybot-custom/`. Only resolve the exact path the profile registered.

### Why two maps

`by_uuid` is environment-specific (the UUID rotates between dev / staging / prod). `by_slug` is portable across environments because slugs are stable. Customers running both staging and prod want the same routing in both environments; that's what the slug map gives them. Recommend both maps — UUID for exact matches, slug for cross-environment robustness.

---

## Markdown Content Rules — read before composing any answer

> [!IMPORTANT]
> The Dailybot webapp renders a **constrained Markdown subset** on form-response answers. Submitted content that uses unsupported syntax falls through as plain text — usually visually broken. Both `dailybot form submit` and `dailybot form update` send `--content` strings through this same renderer.
>
> These rules apply to every value inside the `--content` JSON map.

### Headings — single level only

- ✅ `# Service name` — renders as a title.
- ❌ `## Subsection`, `### Detail` — only one heading level renders. Nested headings fall through as plain text (`##` becomes the literal characters in the output).

**If you need section structure**, use a single `#` heading with bold paragraph leads beneath it, not multiple heading levels.

### Newlines — must be real `\n`

- ✅ JSON `"line 1\nline 2"` → renders as two lines.
- ❌ JSON `"line 1 line 2"` → renders as one paragraph (the space is just a space).

When building `--content` strings from a heredoc or programmatic source, ensure the encoder emits literal `\n` characters in the JSON string (a real line break in a properly-escaped JSON value).

### Supported inline syntax

- `**bold**`
- `*italic*`
- `` `inline code` ``
- `[link text](https://example.com)`

### Supported block syntax

- `- bullet` lists
- `1. numbered` lists
- Fenced code blocks (```` ```language ```` … ```` ``` ````)
- `| col | col |` tables (GFM-style)

### Authoring rule for the LLM

When composing any answer that the agent will submit on behalf of the developer:

1. Use **at most one** `#` heading per answer.
2. Insert **real `\n` newlines** between paragraphs and after each list item.
3. Stick to the inline + block elements listed above. Do not reach for `##`, `>` block quotes, footnotes, definition lists, or HTML.
4. Show the developer a preview before submitting — `--content` is also Markdown, so what you build is what they'll see.

LLMs default to multi-level headings (`##`, `###`). That's the most common authoring mistake here. Pre-flatten the structure before composing.

---

## Step 8 — Submit a New Response

Use this when no in-progress response exists for the developer (or when the form has no workflow).

> Every `text_field` answer is rendered as Markdown. See **Markdown Content Rules** above before composing — the most common mistake is using `##` headings, which fall through as plain text.

### 8a. Guided mode (recommended)

Walk through each question in order. Match the answer format to the question type:

| `question_type` | How to handle |
|-----------------|---------------|
| `text_field`   | Free-text answer — ask the developer or draft from session context |
| `numeric`       | Integer or decimal — validate before sending |
| `boolean`       | Yes/No |
| `choice`        | Pick from the form's predefined choices |

For each question:

> "**Code Release Form** — Question 1 of 8:
>
> *Service name?* (text)
>
> Your answer?"

### 8b. Non-interactive submission

If you already have the full answer set from context:

```bash
dailybot form submit <form_uuid> \
  --content '{"<question-uuid>":"Auth service v2.1","<question-uuid>":"Sergio, Carolina"}' \
  --yes
```

> **Timeout**: Allow at least 30 seconds for CLI commands to complete.

### Confirm before submitting

Always show the complete answer set before sending:

> "Here's what I'll submit for **Code Release Form**:
>
> 1. *Service name?* — "Auth service v2.1"
> 2. *Released by?* — "Sergio, Carolina"
> 3. *Migration notes?* — "None"
>
> **Submit?** (yes / edit / cancel)"

### CLI flags

| Flag | Short | Description |
|------|-------|-------------|
| `--content` | `-c` | JSON map `{"<question_uuid>": "<answer>"}`. Prompts when omitted. |
| `--state` | `-s` | Optional initial state (workflow forms only). Defaults to the form's initial state. |
| `--yes` | `-y` | Skip confirmation. |
| `--json` |     | Machine-readable JSON output. |
| `--automation` | | Submit as an automation — channel notifications show no submitter name. |
| `--anonymous` | | Submit anonymously — channel notifications show a random generated name. |
| `--guest-name` | | Guest submitter full name (used with `--automation` for third-party submissions). |
| `--guest-email` | | Guest submitter email (validated client-side). |
| `--source` | | Provenance label, max 512 chars (e.g. `workflow:release-pipeline`). Works with any mode. |

> **`--automation` vs `--anonymous`:** Both are independent booleans. `--automation` hides the submitter entirely; `--anonymous` replaces them with a random name. When combined, `automation` takes precedence for the channel display. Neither flag affects who owns the response in the dashboard — it only controls the notification appearance.

### Submission modes

| Mode | Flags | Channel notification |
|------|-------|---------------------|
| Normal | (none) | Shows your name + avatar |
| Anonymous | `--anonymous` | Random generated name (e.g. "Purple Elephant") |
| Automation | `--automation` | No submitter shown |
| Automation + Guest | `--automation --guest-name "X" --guest-email "x@y"` | Guest name/email in body, no submitter avatar |
| Any + Source | `--source "label"` | Provenance label attached (works with any mode) |

```bash
# Automation with guest identity and source tracking:
dailybot form submit <form_uuid> \
  --content '{"<q_uuid>":"done"}' --yes --automation \
  --guest-name "Release Bot" --guest-email "releases@example.com" \
  --source "workflow:production-deploy"
```

**Validation rules:**
- If the form has `require_email_and_name` enabled and you use `--automation`, both `--guest-name` and `--guest-email` are required (API returns `guest_user_required`).
- `--guest-email` is validated client-side for format.
- `--source` max length: 512 characters.

After submit, **re-read `current_state` and `allowed_transitions` on the returned payload** to decide the next step.

---

## Step 9 — Update an Existing Response

Use when there's an in-progress response and the developer wants to add / change answers without changing the workflow state.

> Updates are **strictly own-only** server-side. Org admins are NOT elevated to edit another user's response through this endpoint. If the response doesn't belong to the caller, the server returns `form_response_not_found` rather than leaking ownership.
>
> Updated answer values pass through the same Markdown renderer as new submissions — see **Markdown Content Rules** above.

```bash
dailybot form update <form_uuid> <response_uuid> \
  --content '{"<question-uuid>":"Auth service v2.1.1"}' \
  --yes
```

Updates merge into the existing `content`. If the server returns `form_response_change_state_forbidden` on a separate transition call, the update itself is still valid — the audience check is on the transition, not the edit (subject to the form's `edit_permission`).

### CLI flags

| Flag | Short | Description |
|------|-------|-------------|
| `--content` | `-c` | JSON map merged into the existing `content`. |
| `--yes` | `-y` | Skip confirmation. |
| `--json` |     | Machine-readable JSON output. |

After update, re-read `current_state` and `allowed_transitions` on the returned payload.

---

## Step 10 — Transition a Response

When the form is workflow-enabled and `allowed_transitions` is non-empty:

```bash
dailybot form transition <form_uuid> <response_uuid> <to_state> --yes
```

> **You can pass either `to_state` (machine key) or `label` (display text).**
> The CLI resolves labels to keys automatically — e.g.
> `"Mark released"` → `released`. In `allowed_transitions`, `to_state` is the
> machine key (`released`) and `label` is display text (`Mark released`). Both
> are accepted; the CLI performs a case-insensitive lookup and translates labels
> to keys before calling the API. On older CLIs, only the machine key works.

Confirm with the developer before transitioning:

> "I'll transition response **#a1b2** of **Code Release Form** from `review` → `released` ("Mark released"). The action will be attributed to you in the state history. Confirm? (yes / cancel)"

### CLI flags

| Flag | Short | Description |
|------|-------|-------------|
| `--note` | `-n` | Optional free-text note attached to the state-history entry. |
| `--yes` | `-y` | Skip confirmation. |
| `--json` |     | Machine-readable JSON output. |

After a successful transition, surface the new `current_state` and the latest `state_history` entry.

---

## Step 11 — Delete a Response

```bash
dailybot form delete <form_uuid> <response_uuid> --yes
```

Only the **author, form owner, or org admin** can delete a response (server-enforced). Always confirm before invoking — deletion is irreversible. Use a strong confirmation prompt; the developer must type the response UUID or "yes":

> "This will permanently delete response **#a1b2** of **Code Release Form**. This cannot be undone.
>
> Type the response UUID to confirm, or 'cancel'."

---

## Step 12 — Multi-turn Lifecycle Examples

### Example A — Non-workflow form ("Team Feedback")

```
1. dailybot form list --json                  → find UUID for "Team Feedback"
2. dailybot form get <uuid> --json            → workflow: null
3. Resolver: no entry in custom_form_skills   → continue generic flow
4. Guided submission:
     - Question 1: "How was your week?"       → developer answer
     - Question 2: "Rate workload"            → "7"
5. Confirm answer set → dailybot form submit  → done.
```

Response stored. No further lifecycle moves required.

### Example B — Workflow form ("Code Release Form")

```
1. dailybot form list --json                  → find UUID + slug
2. dailybot form get <uuid> --json            → workflow: {enabled: true, ...}
3. Resolver: by_slug["code-release-form"]     → ".agents/skills/dailybot-custom/coderelease-form"
4. Load that custom SKILL.md and follow it    → it drives the whole release flow
   (the custom skill handles questions, per-state required fields, default
    values, channel routing, transition cadence, etc.)
```

If the custom skill path **does not exist**, warn the developer and continue with the generic flow (Steps 8–11) — the form is still usable, just without the customer-specific logic.

---

## Step 13 — Error Handling

Map every server `code` to a clear agent action. The error shape is `{detail, code}` across all 4xx responses.

### `--json` structured error shape

When any `dailybot form ...` command is invoked with `--json`, errors print as:

```json
{
  "error": "...",
  "status": 403,
  "code": "form_response_change_state_forbidden",
  "detail": "Caller is not in the state_change_permission audience."
}
```

Match on `code` (not `detail`) — `detail` is human-readable and may evolve. The CLI exits with a stable, code-aligned exit value (table below).

### Code / HTTP / exit / action

| Server `code` | HTTP | CLI exit | Agent action |
|---------------|------|----------|--------------|
| `form_does_not_exists` | 404 | 5 | Wrong UUID. Re-run `dailybot form list` and confirm the target. |
| `form_response_not_found` | 404 | 5 | The response doesn't exist **or** belongs to another user (update is own-only). Treat as a clean miss — no information leak. Offer to start a new response. |
| `form_response_change_state_forbidden` | 403 | 4 | Stop the transition flow. The caller is not in the form's `state_change_permission` audience — even on their own response. Suggest contacting the form owner if the move is needed. |
| `final_state_locked` | 403 | 4 | Stop. The response is in a final state and `allow_reopen_from_final_state` is `false`. Explain the policy. Offer to PATCH `allow_reopen_from_final_state=true` only if the developer is the form owner. |
| `form_response_delete_forbidden` | 403 | 4 | Stop the delete flow. Explain the author / owner / admin invariant. |
| `user_can_not_see_form_responses` | 403 | 4 | Stop. The form's `view_reports_permission` audience excludes the caller. |
| `payload_too_large` | 400 | 2 | Trim `--content`. For very long answers, split into multiple updates. |
| Any other 4xx with a `detail` | — | — | Surface the `detail` text verbatim to the developer. |
| Not authenticated | 401 | 3 | Guide through `dailybot login`. |
| Rate limited | 429 | 6 | Slow down. Do not retry in a tight loop. |

If the server returns a body without a `code` (network error, gateway error, malformed response), warn briefly and fall back to the non-blocking rule.

---

## Step 14 — HTTP Fallback (when CLI is unavailable)

See [`../shared/http-fallback.md`](../shared/http-fallback.md) for base patterns.

**Important:** Form endpoints accept **either** Bearer token or `X-API-KEY` auth.

### List forms (with questions)

```bash
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  "https://api.dailybot.com/v1/forms/?include=questions"
```

### Get a single form

```bash
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  "https://api.dailybot.com/v1/forms/<form_uuid>/"
```

### List responses for a form

```bash
curl -s -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  "https://api.dailybot.com/v1/forms/<form_uuid>/responses/?latest=true"
```

### Submit a response

```bash
curl -s -X POST \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.dailybot.com/v1/forms/<form_uuid>/responses/ \
  -d '{"content": {"<question_uuid>": "Auth service v2.1"}}'
```

### Update a response

```bash
curl -s -X PATCH \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.dailybot.com/v1/forms/<form_uuid>/responses/<response_uuid>/ \
  -d '{"content": {"<question_uuid>": "Auth service v2.1.1"}}'
```

### Transition a response

```bash
curl -s -X POST \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.dailybot.com/v1/forms/<form_uuid>/responses/<response_uuid>/transition/ \
  -d '{"to_state": "released"}'
```

### Delete a response

```bash
curl -s -X DELETE \
  -H "Authorization: Bearer $DAILYBOT_BEARER_TOKEN" \
  https://api.dailybot.com/v1/forms/<form_uuid>/responses/<response_uuid>/
```

---

## Step 15 — JSON Output Stability

Every `dailybot form ...` command supports `--json`. The shapes documented above are the **stable** machine-readable contract: agents and downstream tooling can rely on them across releases. Table output (the default without `--json`) is human-only and may evolve — never parse it.

For the canonical CLI command + payload contract, see the `CLI_AGENT_HANDOFF.md` companion document in the planning folder.

---

## Step 16 — Confirm

After every mutating command:

- **Success** — briefly confirm the outcome and the new state (when applicable). Example: *"Submitted your Code Release Form response. It's now in `draft`."*
- **Failure** — warn briefly. Map the `code` to a concrete next step per the table in Step 13.
- **Skipped** — say nothing.

---

## Non-Blocking Rule

Form operations must **never block your primary work**. If the CLI is missing, auth fails, the network is down, or any command errors:

1. Warn the developer briefly.
2. Continue with the primary task.
3. Do not retry automatically.
4. Do not enter a diagnostic loop.

---

## Additional Resources

- [`../shared/auth.md`](../shared/auth.md) — authentication setup
- [`../shared/http-fallback.md`](../shared/http-fallback.md) — HTTP API fallback patterns
- [`../shared/dashboard-urls.md`](../shared/dashboard-urls.md) — full dashboard URL catalog (forms, check-ins, kudos, agents)
- [`_custom-template/SKILL.md`](_custom-template/SKILL.md) — starter template for authoring a custom per-form skill (copy into `.agents/skills/dailybot-custom/<your-name>/` in your own repo)
- **Live API spec:** `https://api.dailybot.com/api/swagger/`
- **Full agent API skill:** `https://www.dailybot.com/skill.md`
