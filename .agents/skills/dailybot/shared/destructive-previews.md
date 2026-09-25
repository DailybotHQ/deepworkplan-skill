# Destructive operations — state the consequence, do not ask "are you sure"

"Are you sure?" is not a safety control. It asks the person to supply information they do
not have. The server knows what an operation will do; ask it, and show the answer.

## The mechanism

Archive doors accept `?dry_run=true`, and the CLI uses it automatically before every
destructive call:

```bash
dailybot task archive <task-uuid> --dry-run
dailybot board archive <board-uuid> --dry-run
```

The preview writes no rows and no audit events. It returns:

| Field | What it tells you |
| --- | --- |
| `consequence` | a human sentence — **this is the headline; surface it verbatim** |
| `affects` | the counts, e.g. `{"boards": 1, "tasks_cascaded": 12}` |
| `reversible` | whether it can be undone at all |
| `restore_path` | how, when it can |

**Do not summarise the consequence away.** "Archives the board and cascade-archives 12 live
tasks" is the sentence that changes someone's mind; "this will archive the board" is not.

## Facts that surprise people

- **Archiving a board cascade-archives its live tasks**, and restoring the board does
  **not** bring them back. They are restored one by one.
- **`task delete` is an alias of archive.** Nothing is destroyed; it is reversible and
  audited as `task.archived`. Do not tell a developer their data is gone.
- **`--yes` skips the prompt, not the preview.** The record of what was about to happen is
  the point, and the flag is advisory anyway — the server bounds blast radius per call.
- **A failed preview means stop.** Not knowing the blast radius is not permission to
  proceed.
- **An irreversible operation offers no restore path**, because there is none.

## Under `--json`, stdout is the document and stderr is the record

`--json` promises one parseable document on stdout, and the preview panel would break it.
So the panel goes to **stderr** and stdout carries exactly one JSON object:

| Invocation | stdout | stderr |
| --- | --- | --- |
| `--dry-run --json` | the preview (`consequence`, `affects`, `reversible`, `restore_path`) | — |
| `--yes --json` | the write result | the consequence panel |
| preview failed, `--json` | `{"status": "error", "code", "detail", "message"}`, exit 1 | — |

Read the `consequence` from stdout under `--dry-run --json`; never scrape the panel. And
note that a failed preview still gives you a parseable stdout — an agent that branches on
stdout for every exit code does not need a special case here.

## Bulk has no dry run

Its blast radius is bounded by a **100-item cap** instead (`too_many_items` above it).

```bash
dailybot task bulk --operation archive -f batch.json --yes --json
```

Bulk reports **per item**. A partial failure exits non-zero — do not read exit 0 as "all
applied" without checking the per-item results.

## What to do as an agent

1. Run the preview.
2. Show the developer the `consequence` sentence and the `affects` counts.
3. Wait for an actual answer.
4. Only then act.

Never chain a destructive call behind a read in a single unattended step.
