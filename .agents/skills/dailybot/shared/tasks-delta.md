# The delta cursor — reading what changed without re-reading everything

Polling a board for changes is the loop an unattended agent runs forever, and it has one
failure mode that turns into an infinite loop if you get it wrong.

## The lifecycle

```
board snapshot  ──►  delta_cursor  ──►  tasks changes --cursor …  ──►  a NEW delta_cursor
                                              │
                                              └─ expired after 7 days
                                                      └─►  re-snapshot (exit 9, or --resync)
```

```bash
dailybot board snapshot <board-uuid> --json          # → delta_cursor
dailybot tasks changes <board-uuid> --cursor "<c>" --json   # → a new delta_cursor
```

**Persist the new cursor each time.** The delta door's own refusal for a missing cursor does
**not** say where to get one — the snapshot is the only source.

## The 7-day window

A cursor older than seven days is refused **permanently**. It will never be accepted again.

- exit code **9**, code `delta_window_expired`, with `full_resync_required: true`;
- **retrying is an infinite loop**;
- the only correct response is a fresh snapshot.

```bash
dailybot tasks changes <board-uuid> --cursor "<old>" --resync
```

An agent offline over a long weekend comes back to exactly this. Handle it before it
happens.

## One read per invocation — the loop is yours

`dailybot tasks changes` performs **one** delta read and exits. There is deliberately no
`--follow`.

That is not an omission. The rate limit is yours to respect — the server publishes **240
delta reads per minute** — and a CLI that slept and retried internally would hide both the
ceiling and the expiry window from whoever is accountable for them. Sleep between calls in
your own loop.

## The timestamp trap

If you are building a cursor yourself rather than passing one back:

```
?updated_since=2026-09-19T13:13:37+00:00      → 400   (the `+` decoded to a space)
?updated_since=2026-09-19T13:13:37Z           → 200
```

`datetime.now(timezone.utc).isoformat()` ends in `+00:00`. Unencoded in a query string that
`+` becomes a space, and the server refuses a value that **is** valid ISO-8601 — with a
message saying it is not. Use the `Z` form, or percent-encode.

The CLI normalises this for you. Direct HTTP callers must not forget it.

## What the poll costs

Confirmed by the API team (2026-09-20): an **empty** delta poll costs **13 queries**
with an organization API key, and the cost is flat between 2 and 40 tasks.

An organization API key costs **3–4 more queries per door** than a signed-in session,
because the server resolves the key, its organization, the plan, the owner and the
feature gate on every request. The credential an unattended agent holds is the expensive
one. Not a reason to avoid polling — a reason not to poll every second when every thirty
would do.

## Deep walks are approximate

`--all` follows every page, but pagination under **concurrent modification** is not
asserted by the API. Walking a large project while other people edit it cannot promise
exactly-once. When you need to know what *changed*, use the cursor rather than
re-walking the list.

## The other two refusals

| Condition | Code | Fix |
| --- | --- | --- |
| no cursor given | `invalid_filter_value` (`parameter: updated_since`) | read the snapshot first |
| cursor unparseable | `invalid_filter_value` | fix the value you are sending |
