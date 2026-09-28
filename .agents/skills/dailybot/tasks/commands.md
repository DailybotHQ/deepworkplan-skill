# Tasks — complete command reference

> **Beta** — Tasks is in beta. Everything under `/tasks` in the web app, the CLI and agent skill commands for projects, goals, boards and tasks, and the `/v1/tasks/` public API may change before general availability. Want to try it with your team? Write to **support@dailybot.com**.

This file lists **every** Tasks command in `dailybot-cli >= 3.14.2`: 115 commands across
`tasks`, `task`, `board`, `project` and `goal`. It is generated from the CLI's own command
definitions, so the arguments and flags here match `--help` exactly. [SKILL.md](SKILL.md)
explains *when* and *how* to use them (untrusted content, credentials, delta cursors,
destructive previews, refusals). Use this file to look up *what exists* and *what each
command sends*. Read SKILL.md Step 0 before acting on anything these commands return.

## How to read an entry

- **Arguments.** `TASK` is a task key (`ENG-142`) or a task uuid. Every other argument
  (`BOARD`, `PROJECT`, `GOAL`, `STATE`, `VIEW`, `USER`, …) is a uuid unless the entry says
  otherwise. `[X]` means optional; `X…` means one or more.
- **API.** The endpoint the command calls under `https://api.dailybot.com`. `+key` /
  `+Idempotency-Key` means the CLI sends an `Idempotency-Key` header and prints the key after
  the write, so a retry of the **same** call (`--idempotency-key <key>`) is safe for 24 hours.
  An entry without it sends no key, so a retry can repeat the write. A dry run never sends a
  key. `(member)` marks a structure change.
- **Signed-in person.** **member** means any non-guest member after `dailybot login`. That is
  every structure change: creating, updating, archiving or restoring boards, columns,
  projects and goals, board and project membership, linking goals to projects, and
  attaching files to or deleting them from a project or a goal. An organization API key can
  never hold `tasks:admin` and cannot change membership or participants. With a key the CLI
  refuses **before sending anything**, exits 4, and reports `insufficient_scope`. The fix is
  `dailybot login` as a non-guest member — no organization-admin prerequisite. **yes** means
  the answer is about a person (their inbox, pins, saved views, who is notified, who can
  see). With a key the CLI refuses before sending anything and exits 3; the fix is
  `dailybot login`. **no** means an API key with the right scope works.
- **Flags.** `<type>` is the value type; `a|b|c` lists the accepted values. **required**
  flags must be passed; **repeatable** flags may be given several times. Short aliases are
  listed with the long name.
- **`--json`.** Every command accepts `--json`. It prints the raw API document on stdout,
  and on failure a `{"status": "error", "code", "detail", "message"}` envelope with a
  non-zero exit. Parse `--json` output; never parse the human tables. Branch on `code`, never
  on the prose.
- **Destructive commands.** Every archive / delete / remove / unlink / retire command takes
  `--dry-run` (shows the consequence, changes nothing) and `--yes` (skips the prompt). Show the
  consequence to the human first ([destructive previews](../shared/destructive-previews.md)).
  `board view save` and `project view save` are destructive too: they replace the person's
  whole saved-view list and have **no** preview. Read the current views, show what the new
  file drops, and wait before saving with `--if-match`.
  Exit 7 means a person declined. Stop, and never re-run with `--yes`.
- **Exit codes.** 0 ok · 1 partial bulk, predicted refusals, `preview_not_honoured`, or another failure (read
  `code`) · 2 bad input, including `invalid_identifier` · 3 needs a signed-in person ·
  4 refused, including `insufficient_scope` · 5 not found or not visible · 6 transient,
  back off and retry (except `attachment_storage_unavailable`, which will not change) ·
  7 declined · 8 transport (a write may have been applied) · 9 delta cursor expired.
- **Identifiers.** A `TASK` or uuid argument may contain only letters, digits, `-` and `_`.
  Anything else (`/`, `..`, `?`, `#`, `%`, spaces) is refused locally with
  `invalid_identifier`. Take identifiers only from the server-generated `key` and `uuid`
  fields, never from the free text of a title, description or comment.

- **Bulk items.** `task bulk -f` takes a JSON array of at most 100 objects. For every
  operation except `create`, an item names its task in `task` (key or uuid, required) and
  carries the fields its operation changes, from this set: `state` (a column uuid), `after`
  / `before` (a neighbouring task, for ordering), `owner`, `priority` (1–5), `due_date`,
  `parent_task`, `labels` / `label_uuids`, and `version` (the version you read, to refuse a
  stale write). `archive`, `restore` and `delete` (the archive alias) need only `task`.
  `create` needs `--board`, and each item takes `title` (required) plus optionally
  `description`, `state`, `owner`, `priority`, `estimate`, `start_date`, `due_date`,
  `labels`, `parent_task` and `external_id` (echoed back in the result). Run `--dry-run`
  first: a field the operation does not take shows up as a refusal there.

Examples use placeholder uuids (`00000000-0000-0000-0000-00000000000N`) and the key
`ENG-142`. Replace them with real values from a read.

## Index

| Group | Commands |
| --- | --- |
| `tasks` | `activity`, `changes`, `counts`, `cursor`, `entitlements`, `favorites`, `inbox`, `inbox-read`, `inbox-read-all`, `inbox-unread`, `mine`, `search`, `status`, `timeline`, `view delete`, `view get`, `view star`, `view unstar`, `view update` |
| `task` | `activity`, `archive`, `attach`, `attachment delete`, `attachment get`, `attachments`, `bulk`, `children`, `comment`, `comment-attach`, `comment-attachment delete`, `comment-attachment get`, `comment-attachments`, `comment-delete`, `comment-edit`, `comments`, `create`, `delete`, `duplicate`, `events`, `get`, `labels`, `link`, `list`, `move`, `mute`, `participants add`, `participants list`, `participants remove`, `relations`, `restore`, `set-owner`, `unlink`, `unmute`, `unwatch`, `update`, `watch` |
| `board` | `archive`, `create`, `get`, `label create`, `labels`, `list`, `member add`, `member remove`, `members`, `mentionables`, `restore`, `snapshot`, `star`, `state archive`, `state create`, `state reorder`, `state restore`, `state update`, `states`, `tasks`, `unstar`, `update`, `view save`, `views` |
| `project` | `archive`, `attach`, `attachment delete`, `attachment get`, `attachments`, `create`, `get`, `list`, `member add`, `member remove`, `members`, `milestone-complete`, `milestone-create`, `milestone-delete`, `milestone-reopen`, `milestone-update`, `milestones`, `restore`, `update`, `update-post`, `updates`, `view save`, `views` |
| `goal` | `archive`, `attach`, `attachment delete`, `attachment get`, `attachments`, `create`, `get`, `link`, `list`, `restore`, `unlink`, `update` |

## Workspace — `dailybot tasks`

Workspace-level reads, the delta cursor, the signed-in person's inbox and lists, saved views and pins.

### `dailybot tasks activity`

Show the workspace activity feed — the catch-up read after an absence.

- **API:** `GET /v1/tasks/activity/`
- **Signed-in person:** no
- **Flags:**
  - `--since` `<text>` — Only activity at or after this ISO-8601 time.
  - `--until` `<text>` — Only activity at or before this ISO-8601 time.
  - `--date` `<text>` — One day (YYYY-MM-DD).
  - `--today` — Only today.
  - `--last-week` — Monday to Sunday of last week.
  - `--type` `<text>` — Only this kind of event, e.g. task.moved.
  - `--actor` `<text>` — Only what this person did (user uuid).
  - `--project` `<text>` — Only this project (uuid).
  - `--board` `<text>` — Only this board (uuid).
  - `--task` `<text>` — Only this task (uuid).
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
- **Example:** `dailybot tasks activity --last-week --json`

### `dailybot tasks changes BOARD`

Read what changed on a board since a cursor.

- **API:** `GET /v1/tasks/boards/{b}/delta/?updated_since= (reads boards/{b}/board/ first when no cursor)`
- **Signed-in person:** no
- **Flags:**
  - `--cursor` `<text>` — Resume from this delta cursor (from a snapshot).
  - `--updated-since` `<text>` — ISO-8601 timestamp to read changes since.
  - `--resync` — If the cursor has expired, read a fresh snapshot instead of failing.
- **Example:** `dailybot tasks changes 00000000-0000-0000-0000-000000000001 --updated-since 2026-09-20T00:00:00Z --json`

### `dailybot tasks counts`

Show how many tasks are yours, by bucket.

- **API:** `GET /v1/tasks/me/tasks/counts/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot tasks counts`

### `dailybot tasks cursor`

Read or move your activity read-mark — "what is new since I last looked".

- **API:** `GET|PUT /v1/tasks/me/activity-cursor/`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--set` `<text>` — Record that you have read activity up to this ISO-8601 time.
  - `--now` — Record that you are caught up as of now.
- **Example:** `dailybot tasks cursor --now`

### `dailybot tasks entitlements`

Show what this organization's plan allows for Tasks.

- **API:** `GET /v1/tasks/entitlements/`
- **Signed-in person:** no
- **Example:** `dailybot tasks entitlements`

### `dailybot tasks favorites`

List your pinned boards and saved views.

- **API:** `GET /v1/tasks/me/favorites/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot tasks favorites --json`

### `dailybot tasks inbox`

Show your Tasks notifications.

- **API:** `GET /v1/tasks/inbox/ (?mentioned=true&type=)`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
  - `--mentioned` — Only notifications where someone mentioned you.
  - `--type` `<text>` — Only this kind of notification, e.g. task.owner_changed.
- **Example:** `dailybot tasks inbox --mentioned --json`

### `dailybot tasks inbox-read ITEM`

Mark an inbox item — and everything older — as read.

- **API:** `POST /v1/tasks/inbox/{item}/read/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot tasks inbox-read 00000000-0000-0000-0000-000000000010`

### `dailybot tasks inbox-read-all`

Mark your whole Tasks inbox as read.

- **API:** `POST /v1/tasks/inbox/read-all/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot tasks inbox-read-all`

### `dailybot tasks inbox-unread`

How many Tasks notifications you have not read.

- **API:** `GET /v1/tasks/inbox/unread-count/ (?mentioned=true&type=, same filters as the list)`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--mentioned` — Only notifications where someone mentioned you.
  - `--type` `<text>` — Only this kind of notification, e.g. task.owner_changed.
- **Example:** `dailybot tasks inbox-unread --mentioned --json`

### `dailybot tasks mine`

List the tasks that are yours.

- **API:** `GET /v1/tasks/me/tasks/?scope=owned|participating|involved`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--scope` `<text>` — owned (default): you are the owner · participating: you are on the card · involved: owned, participating or created by you.
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
- **Example:** `dailybot tasks mine --scope owned --json`

### `dailybot tasks search`

Search tasks, boards and projects by text.

- **API:** `GET /v1/tasks/search/?q=`
- **Signed-in person:** no
- **Flags:**
  - `--query`, `-q` `<text>` **required** — Text to search for across the workspace.
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
- **Example:** `dailybot tasks search -q "deploy" --json`

### `dailybot tasks status`

Show the workspace pulse — open, overdue and blocked counts.

- **API:** `GET /v1/tasks/pulse/?include=projects,attention,activity,goal_progress`
- **Signed-in person:** no
- **Example:** `dailybot tasks status --json`

### `dailybot tasks timeline`

Show a dated view of the workspace.

- **API:** `GET /v1/tasks/timeline/`
- **Signed-in person:** no
- **Flags:**
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
  - `--since`, `-S` `<text>` — Start date (YYYY-MM-DD).
  - `--until`, `-U` `<text>` — End date (YYYY-MM-DD).
  - `--date`, `-D` `<text>` — Single day (YYYY-MM-DD): sets start and end.
  - `--last-week` — Previous Monday-Sunday week.
  - `--today` — Today only.
- **Example:** `dailybot tasks timeline --today`

### `dailybot tasks view delete VIEW`

Delete one saved view.

- **API:** `DELETE /v1/tasks/views/{v}/`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot tasks view delete 00000000-0000-0000-0000-000000000013 --dry-run`

### `dailybot tasks view get VIEW`

Show one saved view.

- **API:** `GET /v1/tasks/views/{v}/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot tasks view get 00000000-0000-0000-0000-000000000013 --json`

### `dailybot tasks view star VIEW`

Pin a saved view to your favorites.

- **API:** `POST /v1/tasks/me/favorites/ {target_type: view, target_uuid} +Idempotency-Key`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot tasks view star 00000000-0000-0000-0000-000000000013`

### `dailybot tasks view unstar VIEW`

Unpin a saved view from your favorites.

- **API:** `GET /v1/tasks/me/favorites/ then DELETE /v1/tasks/me/favorites/{f}/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot tasks view unstar 00000000-0000-0000-0000-000000000013`

### `dailybot tasks view update VIEW`

Edit one saved view.

- **API:** `PATCH /v1/tasks/views/{v}/`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--name`, `-n` `<text>` — New name (max 64 characters).
  - `--view-mode` `<list|board|kanban|timeline|calendar>` — How it is drawn.
  - `--group-by` `<state|owner|priority|category>`
  - `--sort` `<text>` — Sort expression, as the web app saves it.
  - `--visibility` `<personal|shared|board_default>` — `shared` and `board_default` need a board manager.
  - `--filters-file` `<file (`-` = stdin)>` — JSON object of filters (`-` reads stdin); replaces the view's filters.
- **Example:** `dailybot tasks view update 00000000-0000-0000-0000-000000000013 --view-mode kanban --group-by owner`

## One task — `dailybot task`

Everything about a single task (`TASK` is a key such as `ENG-142`, or a uuid), plus the bulk door.

### `dailybot task activity TASK`

Show one task's activity feed — what changed, who changed it, from and to.

- **API:** `GET /v1/tasks/tasks/{t}/activity/ (?updated_since=&type=)`
- **Signed-in person:** no
- **Flags:**
  - `--updated-since` `<text>` — Only activity after this ISO-8601 timestamp.
  - `--type` `<text>` — Only this kind of activity.
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
- **Example:** `dailybot task activity ENG-142 --updated-since 2026-09-20T00:00:00Z`

### `dailybot task archive TASK`

Archive a task.

- **API:** `POST /v1/tasks/tasks/{t}/archive/?dry_run=true then POST …/archive/ +key`
- **Signed-in person:** no
- **Flags:**
  - `--dry-run` — Show the consequence and exit without acting.
  - `--yes`, `-y` — Skip the prompt (still previews).
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot task archive ENG-142 --dry-run`

### `dailybot task attach TASK FILE`

Attach a file to a task.

- **API:** `POST /v1/tasks/tasks/{t}/attachments/presign/ → PUT upload_url (storage, no Dailybot credentials) → POST …/{a}/confirm/; with --caption: POST /v1/tasks/tasks/{t}/attachments/ multipart`
- **Signed-in person:** no
- **Flags:**
  - `--caption` `<text>` — Short caption. Uses the one-request upload, limited to 5 MiB.
- **Example:** `dailybot task attach ENG-142 ./crash.log`

### `dailybot task attachment delete TASK ATTACHMENT`

Remove an attachment from a task.

- **API:** `DELETE /v1/tasks/tasks/{t}/attachments/{a}/`
- **Signed-in person:** no
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot task attachment delete ENG-142 00000000-0000-0000-0000-000000000009 --dry-run`

### `dailybot task attachment get TASK ATTACHMENT`

Download an attachment to a file.

- **API:** `GET /v1/tasks/tasks/{t}/attachments/{a}/content/ (follows one redirect to storage, no credentials)`
- **Signed-in person:** no
- **Flags:**
  - `--output`, `-o` `<file>` **required** — Where to write the file.
  - `--force` — Overwrite the output file if it exists.
- **Example:** `dailybot task attachment get ENG-142 00000000-0000-0000-0000-000000000009 -o ./crash.log`

### `dailybot task attachments TASK`

List a task's attachments.

- **API:** `GET /v1/tasks/tasks/{t}/attachments/`
- **Signed-in person:** no
- **Example:** `dailybot task attachments ENG-142 --json`

### `dailybot task bulk`

Apply one operation to up to 100 tasks in a single call.

- **API:** `POST /v1/tasks/tasks/bulk/ +key (required); --dry-run → ?dry_run=true, no key`
- **Signed-in person:** no
- **Flags:**
  - `--operation` `<create|move|update|archive|restore|set_labels|set_owner|set_priority|set_due_date|set_parent|delete>` **required** — Operation to apply to every item. `delete` is the archive alias: soft and restorable, like `task delete`.
  - `--file`, `-f` `<file (`-` = stdin)>` **required** — JSON file with the item list, or `-` for stdin.
  - `--board` `<text>` — Board (uuid or key) every created task lands on. Required for --operation create.
  - `--dry-run` — Run the batch on the server and roll it back: shows each change, writes nothing.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot task bulk --operation set_owner -f batch.json --dry-run`

### `dailybot task children TASK`

List a task's direct sub-tasks.

- **API:** `GET /v1/tasks/tasks/{t}/children/`
- **Signed-in person:** no
- **Example:** `dailybot task children ENG-142`

### `dailybot task comment TASK BODY`

Comment on a task.

- **API:** `POST /v1/tasks/tasks/{t}/comments/ +key`
- **Signed-in person:** no
- **Flags:**
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot task comment ENG-142 "Deployed. <@DB@00000000-0000-0000-0000-000000000004> can you verify?"`

### `dailybot task comment-attach TASK COMMENT FILE`

Attach a file to a comment.

- **API:** `POST /v1/tasks/tasks/{t}/comments/{c}/attachments/ (multipart, ≤5 MiB; the comment's author only)`
- **Signed-in person:** no
- **Flags:**
  - `--caption` `<text>` — Short caption shown with the file.
- **Example:** `dailybot task comment-attach ENG-142 00000000-0000-0000-0000-000000000007 ./trace.txt`

### `dailybot task comment-attachment delete TASK COMMENT ATTACHMENT`

Remove an attachment from a comment.

- **API:** `DELETE /v1/tasks/tasks/{t}/comments/{c}/attachments/{a}/ (uploader, comment author or an org admin)`
- **Signed-in person:** no
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot task comment-attachment delete ENG-142 00000000-0000-0000-0000-000000000007 00000000-0000-0000-0000-000000000009 --dry-run`

### `dailybot task comment-attachment get TASK COMMENT ATTACHMENT`

Download a comment's attachment to a file.

- **API:** `GET /v1/tasks/tasks/{t}/comments/{c}/attachments/{a}/content/`
- **Signed-in person:** no
- **Flags:**
  - `--output`, `-o` `<file>` **required** — Where to write the file.
  - `--force` — Overwrite the output file if it exists.
- **Example:** `dailybot task comment-attachment get ENG-142 00000000-0000-0000-0000-000000000007 00000000-0000-0000-0000-000000000009 -o ./trace.txt`

### `dailybot task comment-attachments TASK COMMENT`

List a comment's attachments.

- **API:** `GET /v1/tasks/tasks/{t}/comments/{c}/attachments/`
- **Signed-in person:** no
- **Example:** `dailybot task comment-attachments ENG-142 00000000-0000-0000-0000-000000000007 --json`

### `dailybot task comment-delete TASK COMMENT`

Delete a comment.

- **API:** `DELETE /v1/tasks/tasks/{t}/comments/{c}/`
- **Signed-in person:** no
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot task comment-delete ENG-142 00000000-0000-0000-0000-000000000007 --dry-run`

### `dailybot task comment-edit TASK COMMENT BODY`

Replace a comment's text.

- **API:** `PATCH /v1/tasks/tasks/{t}/comments/{c}/`
- **Signed-in person:** no
- **Example:** `dailybot task comment-edit ENG-142 00000000-0000-0000-0000-000000000007 "Deployed to prod"`

### `dailybot task comments TASK`

List a task's comments.

- **API:** `GET /v1/tasks/tasks/{t}/comments/`
- **Signed-in person:** no
- **Flags:**
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--all`, `-a` — Fetch every page (iterate until the end).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
  - `--search`, `--grep`, `-s` `<text>` — Filter by text (max 256 chars; truncated).
  - `--since`, `-S` `<text>` — Start date (YYYY-MM-DD).
  - `--until`, `-U` `<text>` — End date (YYYY-MM-DD).
  - `--date`, `-D` `<text>` — Single day (YYYY-MM-DD): sets start and end.
  - `--last-week` — Previous Monday-Sunday week.
  - `--today` — Today only.
- **Example:** `dailybot task comments ENG-142 --json`

### `dailybot task create`

Create a task.

- **API:** `POST /v1/tasks/tasks/ +Idempotency-Key`
- **Signed-in person:** no
- **Flags:**
  - `--title`, `-t` `<text>` **required** — Task title.
  - `--board`, `-b` `<text>` — Board to create it on.
  - `--description`, `-d` `<text>` — Task description.
  - `--state` `<text>` — Initial workflow state.
  - `--owner` `<text>` — Owner: a user uuid, or `me`.
  - `--due` `<text>` — Due date (YYYY-MM-DD).
  - `--priority` `<int 1–5>` — Priority 1-5: 1 urgent, 2 high, 3 medium, 4 low, 5 none.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe. Generated automatically when omitted. The server keeps it for 24h: reusing it inside that window replays the original result, reusing it after duplicates.
- **Example:** `dailybot task create -t "Fix the flaky test" -b 00000000-0000-0000-0000-000000000001 --owner me --priority 2`

### `dailybot task delete TASK`

Archive a task.

- **API:** `alias of archive (same doors)`
- **Signed-in person:** no
- **Flags:**
  - `--dry-run` — Show the consequence and exit without acting.
  - `--yes`, `-y` — Skip the prompt (still previews).
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot task delete ENG-142 --dry-run`

### `dailybot task duplicate TASK`

Copy a task into the same column, with a new key.

- **API:** `POST /v1/tasks/tasks/{t}/duplicate/ +key {include[]}`
- **Signed-in person:** no
- **Flags:**
  - `--include` `<title|description|labels|priority|estimate|owner|start_date|due_date>` repeatable — Fields to copy (repeatable). Default: title, description and labels.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe. Generated automatically when omitted.
- **Example:** `dailybot task duplicate ENG-142 --include title --include owner`

### `dailybot task events TASK`

List a task's raw event history (created, moved, owner changed, …).

- **API:** `GET /v1/tasks/tasks/{t}/events/`
- **Signed-in person:** no
- **Example:** `dailybot task events ENG-142 --json`

### `dailybot task get TASK`

Show one task.

- **API:** `GET /v1/tasks/tasks/{t}/`
- **Signed-in person:** no
- **Example:** `dailybot task get ENG-142 --json`

### `dailybot task labels TASK`

Add, remove or replace a task's labels.

- **API:** `POST /v1/tasks/tasks/{t}/labels/batch/ +key`
- **Signed-in person:** no
- **Flags:**
  - `--mode` `<add|remove|replace>` **required** — add, remove or replace the task's labels.
  - `--label` `<text>` **required** repeatable — Label uuid. Repeatable, or comma-separated.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot task labels ENG-142 --mode add --label 00000000-0000-0000-0000-000000000012`

### `dailybot task link TASK OTHER_TASK`

Relate one task to another.

- **API:** `POST /v1/tasks/tasks/{t}/relations/ +key {relation_type: blocks|relates_to|duplicates, target_task}`
- **Signed-in person:** no
- **Flags:**
  - `--type` `<text>` **required** — blocks, relates_to or duplicates.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot task link ENG-142 ENG-99 --type blocks`

### `dailybot task list`

List tasks.

- **API:** `GET /v1/tasks/tasks/ (?owner=&sort=&board=&state=&label=&include=)`
- **Signed-in person:** no
- **Flags:**
  - `--board`, `-b` `<text>` — Only tasks on this board.
  - `--state` `<text>` — Only tasks in this workflow state.
  - `--owner` `<text>` repeatable — Only tasks owned by this user (uuid, `me` or `unowned`). Repeat to OR several.
  - `--label` `<text>` — Only tasks carrying this label.
  - `--sort` `<text>` — Order by rank, priority, due_date, updated_at, created_at or completed_at; prefix with - for descending.
  - `--has-dates`, `--no-has-dates` — Only tasks that do (or do not) carry dates.
  - `--include` `<labels|participants|subtasks>` repeatable — Ask for a roll-up. Nothing is included by default — absence is a real answer.
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
- **Example:** `dailybot task list --owner me --owner unowned --sort -updated_at --json`

### `dailybot task move TASK`

Move a task to another column, or to another board.

- **API:** `POST /v1/tasks/tasks/{t}/move/ +key (state name/category resolved via GET boards/{b}/states/); with --board POST /v1/tasks/tasks/{t}/move-board/`
- **Signed-in person:** no
- **Flags:**
  - `--state` `<text>` — Target column: a name, a category (todo, in_progress, done, …) or a state uuid.
  - `--board` `<text>` — Target board, for a move to another board.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe (same-board moves; a cross-board move takes none).
- **Example:** `dailybot task move ENG-142 --state done`

### `dailybot task mute TASK`

Stop notifications from a task while staying on it.

- **API:** `GET /v1/me/ then POST /v1/tasks/tasks/{t}/participants/ {user_uuid: me, is_muted: true}`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot task mute ENG-142`

### `dailybot task participants add TASK`

Add a participant to a task.

- **API:** `POST /v1/tasks/tasks/{t}/participants/ +key`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--user` `<text>` **required** — User uuid to add as a participant.
  - `--role` `<participant|watcher>` — `participant` is on the card (default); `watcher` follows it without being on it.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot task participants add ENG-142 --user 00000000-0000-0000-0000-000000000004 --role watcher`

### `dailybot task participants list TASK`

List who is on a task and who watches it.

- **API:** `GET /v1/tasks/tasks/{t}/participants/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot task participants list ENG-142`

### `dailybot task participants remove TASK USER`

Take someone off a task.

- **API:** `DELETE /v1/tasks/tasks/{t}/participants/{u}/`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot task participants remove ENG-142 00000000-0000-0000-0000-000000000004 --dry-run`

### `dailybot task relations TASK`

List a task's links to other tasks.

- **API:** `GET /v1/tasks/tasks/{t}/relations/`
- **Signed-in person:** no
- **Example:** `dailybot task relations ENG-142 --json`

### `dailybot task restore TASK`

Restore an archived task.

- **API:** `POST /v1/tasks/tasks/{t}/restore/ +key`
- **Signed-in person:** no
- **Flags:**
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot task restore ENG-142`

### `dailybot task set-owner TASK USER`

Make someone the task's owner — the accountable person.

- **API:** `PATCH /v1/tasks/tasks/{t}/ {owner} +Idempotency-Key`
- **Signed-in person:** no
- **Flags:**
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot task set-owner ENG-142 me`

### `dailybot task unlink TASK RELATION`

Remove a link between two tasks.

- **API:** `DELETE /v1/tasks/tasks/{t}/relations/{r}/`
- **Signed-in person:** no
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot task unlink ENG-142 00000000-0000-0000-0000-000000000008 --dry-run`

### `dailybot task unmute TASK`

Resume notifications from a task you muted.

- **API:** `GET /v1/me/ then POST /v1/tasks/tasks/{t}/participants/ {user_uuid: me, is_muted: false}`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot task unmute ENG-142`

### `dailybot task unwatch TASK`

Stop following a task.

- **API:** `DELETE /v1/tasks/tasks/{t}/subscription/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot task unwatch ENG-142`

### `dailybot task update TASK`

Change fields on a task.

- **API:** `PATCH /v1/tasks/tasks/{t}/ +Idempotency-Key`
- **Signed-in person:** no
- **Flags:**
  - `--title`, `-t` `<text>` — New title.
  - `--description`, `-d` `<text>` — New description.
  - `--state` `<text>` — New workflow state.
  - `--due` `<text>` — New due date (YYYY-MM-DD).
  - `--priority` `<int 1–5>` — Priority 1-5: 1 urgent, 2 high, 3 medium, 4 low, 5 none.
  - `--owner` `<text>` — Owner: a user uuid, or `me`.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot task update ENG-142 --priority 1 --due 2026-10-01`

### `dailybot task watch TASK`

Follow a task's notifications without being on it.

- **API:** `POST /v1/tasks/tasks/{t}/subscription/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot task watch ENG-142`

## Boards — `dailybot board`

Boards, their states (columns), members, labels, views and pins.

### `dailybot board archive BOARD`

Archive a board.

- **API:** `POST /v1/tasks/boards/{b}/archive/?dry_run=true then …/archive/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--dry-run` — Show the consequence and exit without acting.
  - `--yes`, `-y` — Skip the prompt (still previews).
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot board archive 00000000-0000-0000-0000-000000000001 --dry-run`

### `dailybot board create`

Create a board in a project.

- **API:** `POST /v1/tasks/boards/ +key (member); body {name, project, key}`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--name`, `-n` `<text>` **required** — Board name.
  - `--project` `<text>` **required** — The project the board belongs to (uuid).
  - `--key` `<text>` **required** — The board's key prefix, e.g. DSN, so its tasks read DSN-1, DSN-2…
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot board create --name "Design" --project 00000000-0000-0000-0000-000000000002 --key DSN`

### `dailybot board get BOARD`

Show one board's metadata.

- **API:** `GET /v1/tasks/boards/{b}/`
- **Signed-in person:** no
- **Example:** `dailybot board get 00000000-0000-0000-0000-000000000001`

### `dailybot board label create BOARD`

Create an organization label from this board.

- **API:** `POST /v1/tasks/boards/{b}/labels/`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--name`, `-n` `<text>` **required** — Label name.
  - `--color` `<text>` — Label color, e.g. #ef4444.
  - `--description`, `-d` `<text>` — What the label means.
- **Example:** `dailybot board label create 00000000-0000-0000-0000-000000000001 -n bug --color "#ef4444"`

### `dailybot board labels BOARD`

List the labels available on a board.

- **API:** `GET /v1/tasks/boards/{b}/labels/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot board labels 00000000-0000-0000-0000-000000000001`

### `dailybot board list`

List boards.

- **API:** `GET /v1/tasks/boards/`
- **Signed-in person:** no
- **Flags:**
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--all`, `-a` — Fetch every page (iterate until the end).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
  - `--search`, `--grep`, `-s` `<text>` — Filter by text (max 256 chars; truncated).
  - `--since`, `-S` `<text>` — Start date (YYYY-MM-DD).
  - `--until`, `-U` `<text>` — End date (YYYY-MM-DD).
  - `--date`, `-D` `<text>` — Single day (YYYY-MM-DD): sets start and end.
  - `--last-week` — Previous Monday-Sunday week.
  - `--today` — Today only.
- **Example:** `dailybot board list --json`

### `dailybot board member add BOARD [USER]`

Give a person or a whole team sight of a board.

- **API:** `POST /v1/tasks/boards/{b}/members/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--team` `<text>` — A whole team (uuid) instead of one person; membership follows the team live.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot board member add 00000000-0000-0000-0000-000000000001 00000000-0000-0000-0000-000000000004`

### `dailybot board member remove BOARD USER`

Take someone's sight of a board away.

- **API:** `DELETE /v1/tasks/boards/{b}/members/{u}/ (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot board member remove 00000000-0000-0000-0000-000000000001 00000000-0000-0000-0000-000000000004 --dry-run`

### `dailybot board members BOARD`

List who can see a board, and their role on it.

- **API:** `GET /v1/tasks/boards/{b}/members/`
- **Signed-in person:** no
- **Example:** `dailybot board members 00000000-0000-0000-0000-000000000001`

### `dailybot board mentionables BOARD`

Who you can @mention on this board, with the token to write.

- **API:** `GET /v1/tasks/boards/{b}/mentionables/`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--query`, `-q` `<text>` — Only people whose name contains this text (case-insensitive).
- **Example:** `dailybot board mentionables 00000000-0000-0000-0000-000000000001 -q jane`

### `dailybot board restore BOARD`

Restore an archived board.

- **API:** `POST /v1/tasks/boards/{b}/restore/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot board restore 00000000-0000-0000-0000-000000000001`

### `dailybot board snapshot BOARD`

Show the whole board in one request — the cold-context read.

- **API:** `GET /v1/tasks/boards/{b}/board/`
- **Signed-in person:** no
- **Example:** `dailybot board snapshot 00000000-0000-0000-0000-000000000001 --json`

### `dailybot board star BOARD`

Pin a board to your favorites.

- **API:** `POST /v1/tasks/me/favorites/ {target_type: board, target_uuid} +Idempotency-Key`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot board star 00000000-0000-0000-0000-000000000001`

### `dailybot board state archive BOARD STATE`

Retire a column.

- **API:** `POST /v1/tasks/boards/{b}/states/{s}/archive/?dry_run=true then …/archive/ {migrate_to} (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--migrate-to` `<text>` — Move this column's live tasks to another live column first (state uuid).
  - `--dry-run` — Show the consequence and exit without acting.
  - `--yes`, `-y` — Skip the prompt (still previews).
- **Example:** `dailybot board state archive 00000000-0000-0000-0000-000000000001 00000000-0000-0000-0000-000000000005 --migrate-to 00000000-0000-0000-0000-000000000013 --dry-run`

### `dailybot board state create BOARD`

Add a column to a board.

- **API:** `POST /v1/tasks/boards/{b}/states/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--name`, `-n` `<text>` **required** — Column name (max 48 characters).
  - `--category` `<backlog|todo|in_progress|done|canceled>` **required** — Fixed meaning of the column; it survives renames and never changes.
  - `--position` `<int ≥ 0>` — Insert at this 1-based place among live columns (0 counts as 1; past the end goes last; omitted appends). Later columns shift right.
  - `--color` `<text>` — Column color, e.g. #3b82f6.
  - `--default` — New tasks land in this column.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot board state create 00000000-0000-0000-0000-000000000001 -n "In review" --category in_progress --position 3`

### `dailybot board state reorder BOARD STATE...`

Set the left-to-right order of every live column in one call.

- **API:** `POST /v1/tasks/boards/{b}/states/reorder/ {order[]} (every live column once) (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Example:** `dailybot board state reorder 00000000-0000-0000-0000-000000000001 00000000-0000-0000-0000-000000000005 00000000-0000-0000-0000-000000000013 00000000-0000-0000-0000-000000000014`

### `dailybot board state restore BOARD STATE`

Bring a retired column back, after the live ones.

- **API:** `POST /v1/tasks/boards/{b}/states/{s}/restore/ (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Example:** `dailybot board state restore 00000000-0000-0000-0000-000000000001 00000000-0000-0000-0000-000000000005`

### `dailybot board state update BOARD STATE`

Rename, recolor or move one column.

- **API:** `PATCH /v1/tasks/boards/{b}/states/{s}/ (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--name`, `-n` `<text>` — New column name.
  - `--color` `<text>` — New column color.
  - `--position` `<int ≥ 0>` — Move the column to this 1-based place among live columns (0 counts as 1; past the end goes last).
- **Example:** `dailybot board state update 00000000-0000-0000-0000-000000000001 00000000-0000-0000-0000-000000000005 --name Shipped`

### `dailybot board states BOARD`

List a board's states (its columns), left to right.

- **API:** `GET /v1/tasks/boards/{b}/states/ (?include_archived=true)`
- **Signed-in person:** no
- **Flags:**
  - `--include-archived` — Also list retired columns.
- **Example:** `dailybot board states 00000000-0000-0000-0000-000000000001 --include-archived`

### `dailybot board tasks BOARD`

List the tasks on one board.

- **API:** `GET /v1/tasks/boards/{b}/tasks/`
- **Signed-in person:** no
- **Flags:**
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
- **Example:** `dailybot board tasks 00000000-0000-0000-0000-000000000001 --page 2`

### `dailybot board unstar BOARD`

Unpin a board from your favorites.

- **API:** `GET /v1/tasks/me/favorites/ then DELETE /v1/tasks/me/favorites/{f}/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot board unstar 00000000-0000-0000-0000-000000000001`

### `dailybot board update BOARD`

Change a board's name, key, visibility or settings.

- **API:** `PATCH /v1/tasks/boards/{b}/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--name`, `-n` `<text>` — New board name.
  - `--key` `<text>` — New key prefix. The old key is retired and stays reserved, so old links still resolve.
  - `--visibility` `<org|members>` — `members` makes it private; you are seated as its first member.
  - `--estimate-scale` `<none|fibonacci|linear>`
  - `--archive-after-days` `<int ≥ 1>` — Auto-archive done tasks after this many days.
  - `--project` `<text>` — Move the board under this project (uuid).
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot board update 00000000-0000-0000-0000-000000000001 --key DSN --visibility members`

### `dailybot board view save BOARD`

Replace your saved views on a board with the array in a file.

- **API:** `PUT /v1/tasks/boards/{b}/views/ +If-Match (required); replaces the whole list, no preview`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--file`, `-f` `<file (`-` = stdin)>` **required** — JSON array of views (`-` reads stdin). It REPLACES your whole list.
  - `--if-match` `<text>` — The ETag `board views` showed. Protects against overwriting a concurrent save.
  - `--fetch-etag` — Read the current ETag first instead of passing --if-match (narrower protection).
- **Example:** `dailybot board view save 00000000-0000-0000-0000-000000000001 -f views.json --if-match "$ETAG"   # only after the developer saw what it replaces`

### `dailybot board views BOARD`

List your saved views on a board, with the ETag a save needs.

- **API:** `GET /v1/tasks/boards/{b}/views/ (ETag)`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--etag` — Print only the ETag `board view save --if-match` needs, and nothing else.
- **Example:** `ETAG=$(dailybot board views 00000000-0000-0000-0000-000000000001 --etag)`

## Projects — `dailybot project`

Projects, members, views, project updates and milestones.

### `dailybot project archive PROJECT`

Archive a project.

- **API:** `POST /v1/tasks/projects/{p}/archive/?dry_run=true then …/archive/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--dry-run` — Show the consequence and exit without acting.
  - `--yes`, `-y` — Skip the prompt (still previews).
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot project archive 00000000-0000-0000-0000-000000000002 --dry-run`

### `dailybot project attach PROJECT FILE`

Attach a file to a project.

- **API:** `POST /v1/tasks/projects/{p}/attachments/ (multipart, ≤5 MiB) (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--caption` `<text>` — Short caption shown with the file.
- **Example:** `dailybot project attach 00000000-0000-0000-0000-000000000002 ./plan.pdf`

### `dailybot project attachment delete PROJECT ATTACHMENT`

Remove an attachment from a project.

- **API:** `DELETE /v1/tasks/projects/{p}/attachments/{a}/ (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot project attachment delete 00000000-0000-0000-0000-000000000002 00000000-0000-0000-0000-000000000009 --dry-run`

### `dailybot project attachment get PROJECT ATTACHMENT`

Download a project's attachment to a file.

- **API:** `GET /v1/tasks/projects/{p}/attachments/{a}/content/`
- **Signed-in person:** no
- **Flags:**
  - `--output`, `-o` `<file>` **required** — Where to write the file.
  - `--force` — Overwrite the output file if it exists.
- **Example:** `dailybot project attachment get 00000000-0000-0000-0000-000000000002 00000000-0000-0000-0000-000000000009 -o ./plan.pdf`

### `dailybot project attachments PROJECT`

List a project's attachments.

- **API:** `GET /v1/tasks/projects/{p}/attachments/`
- **Signed-in person:** no
- **Example:** `dailybot project attachments 00000000-0000-0000-0000-000000000002 --json`

### `dailybot project create`

Create a project.

- **API:** `POST /v1/tasks/projects/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--name`, `-n` `<text>` **required** — Project name.
  - `--description`, `-d` `<text>` — Project description.
  - `--visibility` `<org|members>` — `members` makes it private: you plus whoever you invite. It only narrows.
  - `--lead` `<text>` — Lead (user uuid).
  - `--health` `<not_set|on_track|at_risk|off_track>` — Declared health — separate from the derived progress.
  - `--start-date` `<YYYY-MM-DD>` — YYYY-MM-DD.
  - `--target-date` `<YYYY-MM-DD>` — YYYY-MM-DD.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot project create -n "Apollo" --target-date 2026-12-15`

### `dailybot project get PROJECT`

Show one project.

- **API:** `GET /v1/tasks/projects/{p}/`
- **Signed-in person:** no
- **Flags:**
  - `--include` `<progress>` repeatable — Ask for a roll-up.
- **Example:** `dailybot project get 00000000-0000-0000-0000-000000000002 --include progress`

### `dailybot project list`

List projects.

- **API:** `GET /v1/tasks/projects/`
- **Signed-in person:** no
- **Flags:**
  - `--include` `<progress>` repeatable — Ask for a roll-up (nothing is included by default).
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--all`, `-a` — Fetch every page (iterate until the end).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
  - `--search`, `--grep`, `-s` `<text>` — Filter by text (max 256 chars; truncated).
  - `--since`, `-S` `<text>` — Start date (YYYY-MM-DD).
  - `--until`, `-U` `<text>` — End date (YYYY-MM-DD).
  - `--date`, `-D` `<text>` — Single day (YYYY-MM-DD): sets start and end.
  - `--last-week` — Previous Monday-Sunday week.
  - `--today` — Today only.
- **Example:** `dailybot project list --include progress --json`

### `dailybot project member add PROJECT`

Invite a person or a whole team into a project.

- **API:** `POST /v1/tasks/projects/{p}/members/ {user_uuid | team_uuid} (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--user` `<text>` — A person (user uuid).
  - `--team` `<text>` — A whole team (uuid); membership follows the team live.
- **Example:** `dailybot project member add 00000000-0000-0000-0000-000000000002 --team 00000000-0000-0000-0000-000000000011`

### `dailybot project member remove PROJECT USER`

Remove someone from a project.

- **API:** `DELETE /v1/tasks/projects/{p}/members/{u}/ (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot project member remove 00000000-0000-0000-0000-000000000002 00000000-0000-0000-0000-000000000004 --dry-run`

### `dailybot project members PROJECT`

List who can see a project — people and whole teams.

- **API:** `GET /v1/tasks/projects/{p}/members/`
- **Signed-in person:** **yes** (a key exits 3)
- **Example:** `dailybot project members 00000000-0000-0000-0000-000000000002`

### `dailybot project milestone-complete PROJECT MILESTONE`

Mark a milestone complete.

- **API:** `POST /v1/tasks/projects/{p}/milestones/{m}/complete/?dry_run=true then …/complete/ +key`
- **Signed-in person:** no
- **Flags:**
  - `--dry-run` — Show the consequence and exit without acting.
  - `--yes`, `-y` — Skip the prompt (still previews).
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot project milestone-complete 00000000-0000-0000-0000-000000000002 00000000-0000-0000-0000-000000000006 --dry-run`

### `dailybot project milestone-create PROJECT`

Commit a project to a dated milestone.

- **API:** `POST /v1/tasks/projects/{p}/milestones/`
- **Signed-in person:** no
- **Flags:**
  - `--name`, `-n` `<text>` **required** — Milestone name.
  - `--date` `<YYYY-MM-DD>` **required** — Due date (YYYY-MM-DD).
  - `--description`, `-d` `<text>` — What the milestone commits to.
- **Example:** `dailybot project milestone-create 00000000-0000-0000-0000-000000000002 -n Beta --date 2026-11-01`

### `dailybot project milestone-delete PROJECT MILESTONE`

Retire a milestone.

- **API:** `DELETE /v1/tasks/projects/{p}/milestones/{m}/ (retires)`
- **Signed-in person:** no
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot project milestone-delete 00000000-0000-0000-0000-000000000002 00000000-0000-0000-0000-000000000006 --dry-run`

### `dailybot project milestone-reopen PROJECT MILESTONE`

Reopen a completed milestone.

- **API:** `POST /v1/tasks/projects/{p}/milestones/{m}/reopen/ +key`
- **Signed-in person:** no
- **Flags:**
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot project milestone-reopen 00000000-0000-0000-0000-000000000002 00000000-0000-0000-0000-000000000006`

### `dailybot project milestone-update PROJECT MILESTONE`

Rename a milestone or move its date.

- **API:** `PATCH /v1/tasks/projects/{p}/milestones/{m}/`
- **Signed-in person:** no
- **Flags:**
  - `--name`, `-n` `<text>` — New name.
  - `--date` `<YYYY-MM-DD>` — New date (YYYY-MM-DD).
  - `--description`, `-d` `<text>` — New description.
- **Example:** `dailybot project milestone-update 00000000-0000-0000-0000-000000000002 00000000-0000-0000-0000-000000000006 --date 2026-11-15`

### `dailybot project milestones [PROJECT]`

List milestones, for one project or across the organization.

- **API:** `GET /v1/tasks/milestones/ | GET /v1/tasks/projects/{p}/milestones/`
- **Signed-in person:** no
- **Flags:**
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--all`, `-a` — Fetch every page (iterate until the end).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
  - `--search`, `--grep`, `-s` `<text>` — Filter by text (max 256 chars; truncated).
  - `--since`, `-S` `<text>` — Start date (YYYY-MM-DD).
  - `--until`, `-U` `<text>` — End date (YYYY-MM-DD).
  - `--date`, `-D` `<text>` — Single day (YYYY-MM-DD): sets start and end.
  - `--last-week` — Previous Monday-Sunday week.
  - `--today` — Today only.
- **Example:** `dailybot project milestones 00000000-0000-0000-0000-000000000002`

### `dailybot project restore PROJECT`

Bring an archived project back.

- **API:** `POST /v1/tasks/projects/{p}/restore/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot project restore 00000000-0000-0000-0000-000000000002`

### `dailybot project update PROJECT`

Change a project's name, lead, health, dates or visibility.

- **API:** `PATCH /v1/tasks/projects/{p}/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--name`, `-n` `<text>` — New project name.
  - `--description`, `-d` `<text>` — New project description.
  - `--visibility` `<org|members>` — `members` makes it private: you plus whoever you invite. It only narrows.
  - `--lead` `<text>` — Lead (user uuid).
  - `--health` `<not_set|on_track|at_risk|off_track>` — Declared health — separate from the derived progress.
  - `--start-date` `<YYYY-MM-DD>` — YYYY-MM-DD.
  - `--target-date` `<YYYY-MM-DD>` — YYYY-MM-DD.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot project update 00000000-0000-0000-0000-000000000002 --health at_risk`

### `dailybot project update-post PROJECT BODY`

Post a project update — how the team sees what was done.

- **API:** `POST /v1/tasks/projects/{p}/updates/ +key {body, health}`
- **Signed-in person:** no
- **Flags:**
  - `--health` `<not_set|on_track|at_risk|off_track>` — What you claim about the project today. Does not change the project's own health.
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe. Generated automatically when omitted.
- **Example:** `dailybot project update-post 00000000-0000-0000-0000-000000000002 "Shipped the retry fix" --health on_track`

### `dailybot project updates [PROJECT]`

Read project updates: the batched digest, or one project's updates.

- **API:** `GET /v1/tasks/projects/updates/ | GET /v1/tasks/projects/{p}/updates/`
- **Signed-in person:** no
- **Flags:**
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--all`, `-a` — Fetch every page (iterate until the end).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
  - `--search`, `--grep`, `-s` `<text>` — Filter by text (max 256 chars; truncated).
  - `--since`, `-S` `<text>` — Start date (YYYY-MM-DD).
  - `--until`, `-U` `<text>` — End date (YYYY-MM-DD).
  - `--date`, `-D` `<text>` — Single day (YYYY-MM-DD): sets start and end.
  - `--last-week` — Previous Monday-Sunday week.
  - `--today` — Today only.
- **Example:** `dailybot project updates 00000000-0000-0000-0000-000000000002 --json`

### `dailybot project view save PROJECT`

Replace your saved views on a project with the array in a file.

- **API:** `PUT /v1/tasks/projects/{p}/views/ +If-Match (required); replaces the whole list, no preview`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--file`, `-f` `<file (`-` = stdin)>` **required** — JSON array of views (`-` reads stdin). It REPLACES your whole list.
  - `--if-match` `<text>` — The ETag `project views` showed.
  - `--fetch-etag` — Read the current ETag first (narrower).
- **Example:** `dailybot project view save 00000000-0000-0000-0000-000000000002 -f views.json --if-match "$ETAG"   # only after the developer saw what it replaces`

### `dailybot project views PROJECT`

List your saved views on a project, with the ETag a save needs.

- **API:** `GET /v1/tasks/projects/{p}/views/ (ETag)`
- **Signed-in person:** **yes** (a key exits 3)
- **Flags:**
  - `--etag` — Print only the ETag `project view save --if-match` needs.
- **Example:** `dailybot project views 00000000-0000-0000-0000-000000000002 --etag`

## Goals — `dailybot goal`

Goals, their status and the projects linked to them.

### `dailybot goal archive GOAL`

Archive a goal.

- **API:** `POST /v1/tasks/goals/{g}/archive/?dry_run=true then …/archive/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--dry-run` — Show the consequence and exit without acting.
  - `--yes`, `-y` — Skip the prompt (still previews).
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot goal archive 00000000-0000-0000-0000-000000000003 --dry-run`

### `dailybot goal attach GOAL FILE`

Attach a file to a goal.

- **API:** `POST /v1/tasks/goals/{g}/attachments/ (multipart, ≤5 MiB) (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--caption` `<text>` — Short caption shown with the file.
- **Example:** `dailybot goal attach 00000000-0000-0000-0000-000000000003 ./okr.pdf`

### `dailybot goal attachment delete GOAL ATTACHMENT`

Remove an attachment from a goal.

- **API:** `DELETE /v1/tasks/goals/{g}/attachments/{a}/ (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot goal attachment delete 00000000-0000-0000-0000-000000000003 00000000-0000-0000-0000-000000000009 --dry-run`

### `dailybot goal attachment get GOAL ATTACHMENT`

Download a goal's attachment to a file.

- **API:** `GET /v1/tasks/goals/{g}/attachments/{a}/content/`
- **Signed-in person:** no
- **Flags:**
  - `--output`, `-o` `<file>` **required** — Where to write the file.
  - `--force` — Overwrite the output file if it exists.
- **Example:** `dailybot goal attachment get 00000000-0000-0000-0000-000000000003 00000000-0000-0000-0000-000000000009 -o ./okr.pdf`

### `dailybot goal attachments GOAL`

List a goal's attachments.

- **API:** `GET /v1/tasks/goals/{g}/attachments/`
- **Signed-in person:** no
- **Example:** `dailybot goal attachments 00000000-0000-0000-0000-000000000003 --json`

### `dailybot goal create`

Create a goal.

- **API:** `POST /v1/tasks/goals/ +key (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--name`, `-n` `<text>` **required** — Goal name.
  - `--period-start` `<YYYY-MM-DD>` **required** — First day of the goal's period (YYYY-MM-DD).
  - `--period-end` `<YYYY-MM-DD>` **required** — Last day of the goal's period (YYYY-MM-DD).
  - `--description`, `-d` `<text>` — Goal description.
  - `--owner` `<text>` — Accountable person (user uuid).
  - `--team` `<text>` — Team the goal belongs to (uuid).
  - `--idempotency-key` `<text>` — Reuse a key to make a retry safe.
- **Example:** `dailybot goal create -n "Q4 reliability" --period-start 2026-10-01 --period-end 2026-12-31`

### `dailybot goal get GOAL`

Show one goal, with its progress and linked projects.

- **API:** `GET /v1/tasks/goals/{g}/`
- **Signed-in person:** no
- **Example:** `dailybot goal get 00000000-0000-0000-0000-000000000003 --json`

### `dailybot goal link GOAL PROJECT`

Make a project count toward a goal.

- **API:** `POST /v1/tasks/goals/{g}/projects/ {project} (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Example:** `dailybot goal link 00000000-0000-0000-0000-000000000003 00000000-0000-0000-0000-000000000002`

### `dailybot goal list`

List goals.

- **API:** `GET /v1/tasks/goals/`
- **Signed-in person:** no
- **Flags:**
  - `--include` `<progress|projects>` repeatable — Ask for a roll-up (nothing is included by default).
  - `--page`, `-P` `<int>` — Page number to fetch.
  - `--page-size`, `-z` `<int>` — Items per page (max 100).
  - `--all`, `-a` — Fetch every page (iterate until the end).
  - `--limit`, `-l` `<int>` — Stop after collecting N items.
  - `--search`, `--grep`, `-s` `<text>` — Filter by text (max 256 chars; truncated).
  - `--since`, `-S` `<text>` — Start date (YYYY-MM-DD).
  - `--until`, `-U` `<text>` — End date (YYYY-MM-DD).
  - `--date`, `-D` `<text>` — Single day (YYYY-MM-DD): sets start and end.
  - `--last-week` — Previous Monday-Sunday week.
  - `--today` — Today only.
- **Example:** `dailybot goal list --include progress --include projects`

### `dailybot goal restore GOAL`

Bring an archived goal back.

- **API:** `POST /v1/tasks/goals/{g}/restore/ (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Example:** `dailybot goal restore 00000000-0000-0000-0000-000000000003`

### `dailybot goal unlink GOAL PROJECT`

Stop a project counting toward a goal.

- **API:** `DELETE /v1/tasks/goals/{g}/projects/{p}/ (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--dry-run` — Say what would happen and send nothing.
  - `--yes`, `-y` — Skip the confirmation.
- **Example:** `dailybot goal unlink 00000000-0000-0000-0000-000000000003 00000000-0000-0000-0000-000000000002 --dry-run`

### `dailybot goal update GOAL`

Change a goal, or declare its status.

- **API:** `PATCH /v1/tasks/goals/{g}/ (member)`
- **Signed-in person:** **member** (a key exits 4)
- **Flags:**
  - `--name`, `-n` `<text>` — New goal name.
  - `--description`, `-d` `<text>` — New description.
  - `--period-start` `<YYYY-MM-DD>` — YYYY-MM-DD.
  - `--period-end` `<YYYY-MM-DD>` — YYYY-MM-DD.
  - `--owner` `<text>` — Accountable person (user uuid).
  - `--team` `<text>` — Team (uuid).
  - `--status` `<not_started|on_track|at_risk|off_track|achieved|missed>` — Declare where the goal stands. Not derived from progress.
- **Example:** `dailybot goal update 00000000-0000-0000-0000-000000000003 --status at_risk`
