#!/usr/bin/env python3
"""Ledger service — a minimal stateful HTTP service for the v6 evaluation lab.

Python 3.9+ standard library only: http.server + sqlite3. The data store is a
single disposable SQLite file (LEDGER_DB env var, default ./ledger.db) created
on boot — never a shared or external service.

Interface (all JSON; see README.md for the developer-facing contract):

    POST /events                ingest an event; requires an `Idempotency-Key`
                                header. Replaying the same key returns the
                                ORIGINAL response and creates nothing new.
                                Optional integer `schemaVersion` <= current is
                                accepted (new optional fields are compatible);
                                a version greater than current is rejected 409.
    GET  /events?limit&cursor   keyset pagination, stable order by id.
    POST /accounts              create an account {id, balance} (fixture setup).
    GET  /accounts/{id}         read one account.
    POST /transfers             {from, to, amount}: atomic single-transaction
                                debit+credit. Overdraft and non-positive amounts
                                are rejected and recorded NOTHING.
    POST /admin/barriers/{name}?waiters=N
                                deterministic concurrency barrier: arrives one
                                waiter; releases everything when N arrived.
                                Requires the admin token.
    GET  /admin/schema          schema version (requires the admin token).

Admin endpoints require header `X-Admin-Token` (env LEDGER_ADMIN_TOKEN,
documented development default "dev-admin-token"). Missing/wrong token is 401.
"""
import json
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DB_PATH = os.environ.get("LEDGER_DB", "ledger.db")
ADMIN_TOKEN = os.environ.get("LEDGER_ADMIN_TOKEN", "dev-admin-token")
SCHEMA_VERSION = 2

_lock = threading.RLock()
_release = threading.Condition(_lock)


def connect():
    # One shared connection, serialized by the module lock; the server is
    # thread-per-request, so cross-thread use is required.
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            idem_key TEXT NOT NULL UNIQUE,
            payload TEXT NOT NULL,
            response_code INTEGER NOT NULL,
            response_body TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            balance INTEGER NOT NULL CHECK (balance >= 0)
        );
        CREATE TABLE IF NOT EXISTS ledger_entries (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            from_acct TEXT NOT NULL,
            to_acct TEXT NOT NULL,
            amount INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS barriers (
            name TEXT PRIMARY KEY,
            waiters INTEGER NOT NULL,
            arrived INTEGER NOT NULL DEFAULT 0,
            released INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    conn.commit()


CONN = connect()
init_schema(CONN)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body):
        raw = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _authorized(self):
        return self.headers.get("X-Admin-Token") == ADMIN_TOKEN

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    # ------------------------------------------------------------- routing
    def do_GET(self):
        url = urlparse(self.path)
        parts = [p for p in url.path.split("/") if p]
        query = parse_qs(url.query)
        if url.path == "/schema/version":
            return self._send(200, {"version": SCHEMA_VERSION})
        if parts[:2] == ["admin", "schema"]:
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            return self._send(200, {"version": SCHEMA_VERSION})
        if parts[:2] == ["admin", "barriers"]:
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            return self._barrier_wait(parts[2], query)
        if parts[:1] == ["events"]:
            return self._list_events(query)
        if parts[:1] == ["accounts"] and len(parts) == 2:
            return self._get_account(parts[1])
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        parts = [p for p in url.path.split("/") if p]
        query = parse_qs(url.query)
        if parts[:1] == ["events"] and len(parts) == 1:
            return self._ingest_event()
        if parts[:1] == ["accounts"] and len(parts) == 1:
            return self._create_account(self._body())
        if parts[:1] == ["transfers"] and len(parts) == 1:
            return self._transfer(self._body())
        if parts[:2] == ["admin", "barriers"] and len(parts) == 3:
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            return self._barrier_arrive(parts[2], query)
        return self._send(404, {"error": "not found"})

    # ------------------------------------------------------------ handlers
    def _ingest_event(self):
        key = self.headers.get("Idempotency-Key")
        if not key:
            return self._send(400, {"error": "Idempotency-Key header required"})
        body = self._body()
        version = body.get("schemaVersion", SCHEMA_VERSION)
        if not isinstance(version, int) or version > SCHEMA_VERSION or version < 1:
            return self._send(409, {"error": "unsupported schemaVersion", "current": SCHEMA_VERSION})
        with _lock:
            row = CONN.execute("SELECT * FROM events WHERE idem_key = ?", (key,)).fetchone()
            if row:
                # Replay: 200 with the ORIGINAL id, payload and schema version,
                # plus the replay marker. Creates nothing new.
                return self._send(200, {
                    "id": row["id"], "replay": True,
                    "payload": json.loads(row["payload"]),
                    "schemaVersion": row["schema_version"],
                })
            event_id = "evt_" + key  # deterministic id from the idempotency key
            payload = {k: v for k, v in body.items() if k != "schemaVersion"}
            code = 201
            response = {"id": event_id, "payload": payload, "schemaVersion": version}
            CONN.execute(
                "INSERT INTO events (id, idem_key, payload, response_code, response_body, schema_version)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (event_id, key, json.dumps(payload), code, json.dumps(response), version),
            )
            CONN.commit()
        return self._send(code, response)

    def _list_events(self, query):
        limit = min(int(query.get("limit", ["20"])[0]), 100)
        cursor = query.get("cursor", [None])[0]
        with _lock:
            if cursor:
                rows = CONN.execute(
                    "SELECT id, payload, schema_version, created_at FROM events"
                    " WHERE id > ? ORDER BY id LIMIT ?", (cursor, limit + 1)).fetchall()
            else:
                rows = CONN.execute(
                    "SELECT id, payload, schema_version, created_at FROM events"
                    " ORDER BY id LIMIT ?", (limit + 1,)).fetchall()
        has_more = len(rows) > limit
        rows = rows[:limit]
        return self._send(200, {
            "events": [
                {"id": r["id"], "payload": json.loads(r["payload"]),
                 "schemaVersion": r["schema_version"], "createdAt": r["created_at"]}
                for r in rows
            ],
            "nextCursor": rows[-1]["id"] if has_more and rows else None,
        })

    def _create_account(self, body):
        if not body.get("id") or not isinstance(body.get("balance"), int):
            return self._send(400, {"error": "id and integer balance required"})
        with _lock:
            try:
                CONN.execute("INSERT INTO accounts (id, balance) VALUES (?, ?)",
                             (body["id"], body["balance"]))
                CONN.commit()
            except sqlite3.IntegrityError:
                return self._send(409, {"error": "account exists"})
        return self._send(201, {"id": body["id"], "balance": body["balance"]})

    def _get_account(self, account_id):
        with _lock:
            row = CONN.execute("SELECT id, balance FROM accounts WHERE id = ?",
                               (account_id,)).fetchone()
        if not row:
            return self._send(404, {"error": "account not found"})
        return self._send(200, {"id": row["id"], "balance": row["balance"]})

    def _transfer(self, body):
        src, dst = body.get("from"), body.get("to")
        amount = body.get("amount")
        if not src or not dst or not isinstance(amount, int):
            return self._send(400, {"error": "from, to and integer amount required"})
        if amount <= 0:
            return self._send(400, {"error": "amount must be positive"})
        with _lock:
            try:
                CONN.execute("BEGIN IMMEDIATE")
                src_row = CONN.execute("SELECT balance FROM accounts WHERE id = ?",
                                       (src,)).fetchone()
                dst_row = CONN.execute("SELECT balance FROM accounts WHERE id = ?",
                                       (dst,)).fetchone()
                if not src_row or not dst_row:
                    CONN.execute("ROLLBACK")
                    return self._send(404, {"error": "account not found"})
                if src_row["balance"] < amount:
                    # The invariant: refuse, and record NOTHING.
                    CONN.execute("ROLLBACK")
                    return self._send(409, {"error": "insufficient funds",
                                            "balance": src_row["balance"]})
                CONN.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?",
                             (amount, src))
                CONN.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?",
                             (amount, dst))
                CONN.execute("INSERT INTO ledger_entries (from_acct, to_acct, amount)"
                             " VALUES (?, ?, ?)", (src, dst, amount))
                CONN.commit()
            except Exception:
                CONN.execute("ROLLBACK")
                raise
        return self._send(200, {"transferred": amount, "from": src, "to": dst})

    def _barrier_arrive(self, name, query):
        waiters = int(query.get("waiters", ["2"])[0])
        with _release:
            row = CONN.execute("SELECT * FROM barriers WHERE name = ?", (name,)).fetchone()
            if not row:
                CONN.execute("INSERT INTO barriers (name, waiters, arrived, released)"
                             " VALUES (?, ?, 1, ?)", (name, waiters, 1 if waiters <= 1 else 0))
            else:
                arrived = row["arrived"] + 1
                released = 1 if arrived >= row["waiters"] else row["released"]
                CONN.execute("UPDATE barriers SET arrived = ?, released = ? WHERE name = ?",
                             (arrived, released, name))
            CONN.commit()
            row = CONN.execute("SELECT * FROM barriers WHERE name = ?", (name,)).fetchone()
            if row["released"]:
                _release.notify_all()
            return self._send(200, {"name": name, "arrived": row["arrived"],
                                    "released": bool(row["released"])})

    def _barrier_wait(self, name, query):
        with _release:
            row = CONN.execute("SELECT released FROM barriers WHERE name = ?",
                               (name,)).fetchone()
            if not row:
                return self._send(404, {"error": "barrier not found"})
            if not row["released"] and query.get("wait", ["0"])[0] == "1":
                _release.wait(timeout=30)
                row = CONN.execute("SELECT released FROM barriers WHERE name = ?",
                                   (name,)).fetchone()
            return self._send(200, {"name": name, "released": bool(row["released"])})


def serve():
    server = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("LEDGER_PORT", "8971"))), Handler)
    print(f"ledger service on http://127.0.0.1:{server.server_address[1]} (db: {DB_PATH})")
    server.serve_forever()


if __name__ == "__main__":
    serve()
