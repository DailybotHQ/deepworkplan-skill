# Ledger service (fixture seed)

A minimal stateful HTTP service: JSON API over a disposable SQLite database.
Python 3.9+ standard library only — no packages to install, no external
services. Every run gets its own database file (`LEDGER_DB`, default
`./ledger.db`), created on boot.

## Run it

```bash
python3 server.py                     # serves http://127.0.0.1:8971 (LEDGER_PORT to change)
LEDGER_DB=/tmp/demo.db python3 server.py
```

## Interface

| Method & path | Auth | Behavior |
| --- | --- | --- |
| `POST /events` | — | Ingest an event. Requires `Idempotency-Key` header. Replaying a key returns 200 with the original id and payload (`replay: true`) and creates nothing. Optional integer `schemaVersion` ≤ 2 accepted; greater is 409. |
| `GET /events?limit&cursor` | — | Keyset pagination, stable order by id, `nextCursor` when more remain. |
| `POST /accounts` | — | Create `{id, balance}` (integer balance ≥ 0 enforced by the schema). |
| `GET /accounts/{id}` | — | Read one account. |
| `POST /transfers` | — | `{from, to, amount}`: atomic single-transaction debit+credit with a ledger entry. Overdraft → 409 and nothing recorded. Non-positive amount → 400. |
| `POST /admin/barriers/{name}?waiters=N` | token | Deterministic barrier: arrives one waiter, releases all when N arrived. |
| `GET /admin/barriers/{name}?wait=1` | token | Blocks until the barrier releases. |
| `GET /admin/schema` | token | Schema version (currently 2). |

Admin endpoints require `X-Admin-Token` (development default
`dev-admin-token`, override with `LEDGER_ADMIN_TOKEN`). Missing/wrong token →
401.

## Test it

```bash
python3 -m unittest discover -s tests -v
```

The tests boot the real server on an ephemeral port with a disposable
database and verify behavior over HTTP and in the stored state — including
replay-after-timeout idempotency, refused transfers recording nothing,
unauthorized reads, stable pagination, and barrier-aligned concurrent
duplicate delivery.
