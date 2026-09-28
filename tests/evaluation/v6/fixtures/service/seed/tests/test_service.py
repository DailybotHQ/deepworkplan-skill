"""Behavioral tests for the ledger service (stdlib unittest, no dependencies).

Every test boots the real server on an ephemeral port with its own disposable
SQLite database and talks HTTP to it. Concurrency is aligned with the service's
own deterministic barriers — there are no timing-sensitive sleeps.
"""
import json
import os
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request


class Client:
    def __init__(self, base):
        self.base = base

    def request(self, method, path, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read())

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, body=None, **kw):
        return self.request("POST", path, body, **kw)


class ServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["LEDGER_DB"] = os.path.join(cls.tmp.name, "ledger.db")
        os.environ["LEDGER_PORT"] = "0"
        import server
        server.DB_PATH = os.environ["LEDGER_DB"]
        server.CONN = server.connect()
        server.init_schema(server.CONN)
        cls.server = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.client = Client(f"http://127.0.0.1:{cls.server.server_address[1]}")
        cls.admin = {"X-Admin-Token": "dev-admin-token"}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.tmp.cleanup()

    # ------------------------------------------------------------ helpers
    def account(self, ident, balance):
        status, _ = self.client.post("/accounts", {"id": ident, "balance": balance})
        self.assertIn(status, (201, 409))

    def entry_count(self):
        db = sqlite3.connect(os.environ["LEDGER_DB"])
        n = db.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0]
        db.close()
        return n

    # -------------------------------------------------------------- tests
    def test_idempotent_replay_creates_exactly_one_record_and_replays_response(self):
        key = "idem-replay-1"
        body = {"kind": "charge", "amount": 10}
        s1, b1 = self.client.post("/events", body, headers={"Idempotency-Key": key})
        s2, b2 = self.client.post("/events", body, headers={"Idempotency-Key": key})
        self.assertEqual(s1, 201)
        self.assertEqual(s2, 200)
        self.assertTrue(b2.get("replay"))
        self.assertEqual(b1["id"], b2["id"])
        self.assertEqual(b1["payload"], b2["payload"])
        s3, b3 = self.client.get("/events?limit=100")
        matches = [e for e in b3["events"] if e["id"] == b1["id"]]
        self.assertEqual(len(matches), 1, "replay created a second record")

    def test_overdraw_transfer_refused_and_recorded_nothing(self):
        self.account("over-src", 5)
        self.account("over-dst", 100)
        before = self.entry_count()
        status, body = self.client.post("/transfers", {"from": "over-src", "to": "over-dst", "amount": 6})
        self.assertEqual(status, 409)
        self.assertEqual(body.get("balance"), 5)
        _, src = self.client.get("/accounts/over-src")
        _, dst = self.client.get("/accounts/over-dst")
        self.assertEqual((src["balance"], dst["balance"]), (5, 100))
        self.assertEqual(self.entry_count(), before, "a refused transfer must record nothing")

    def test_zero_and_negative_amounts_rejected(self):
        self.account("zero-src", 10)
        self.account("zero-dst", 10)
        for amount in (0, -3):
            status, _ = self.client.post("/transfers", {"from": "zero-src", "to": "zero-dst", "amount": amount})
            self.assertEqual(status, 400)

    def test_transactional_transfer_moves_funds_atomically(self):
        self.account("ok-src", 50)
        self.account("ok-dst", 10)
        status, _ = self.client.post("/transfers", {"from": "ok-src", "to": "ok-dst", "amount": 20})
        self.assertEqual(status, 200)
        _, src = self.client.get("/accounts/ok-src")
        _, dst = self.client.get("/accounts/ok-dst")
        self.assertEqual((src["balance"], dst["balance"]), (30, 30))

    def test_unauthorized_admin_read_is_401(self):
        status, _ = self.client.get("/admin/schema")
        self.assertEqual(status, 401)
        status, _ = self.client.get("/admin/schema", headers={"X-Admin-Token": "wrong"})
        self.assertEqual(status, 401)
        status, body = self.client.get("/admin/schema", headers=self.admin)
        self.assertEqual(status, 200)
        self.assertEqual(body["version"], 2)

    def test_pagination_is_stable_and_total(self):
        for i in range(5):
            self.client.post("/events", {"n": i}, headers={"Idempotency-Key": f"page-{i}"})
        seen, cursor, pages = [], None, 0
        while True:
            status, body = self.client.get(f"/events?limit=2" + (f"&cursor={cursor}" if cursor else ""))
            self.assertEqual(status, 200)
            seen.extend(e["id"] for e in body["events"])
            pages += 1
            if not body["nextCursor"]:
                break
            cursor = body["nextCursor"]
        self.assertEqual(len(seen), len(set(seen)), "pagination duplicated records")
        self.assertEqual(seen, sorted(seen), "pagination order is not stable")
        self.assertGreaterEqual(pages, 3)

    def test_schema_v2_optional_field_accepted_and_unknown_version_rejected(self):
        status, _ = self.client.post("/events", {"kind": "v2", "extra": "optional-field"},
                                     headers={"Idempotency-Key": "schema-ok"})
        self.assertEqual(status, 201)
        status, body = self.client.post("/events", {"kind": "v3", "schemaVersion": 3},
                                        headers={"Idempotency-Key": "schema-future"})
        self.assertEqual(status, 409)
        self.assertEqual(body["current"], 2)

    def test_concurrent_duplicate_delivery_creates_exactly_one_record(self):
        # Deterministic interleaving via the service's own barrier: four
        # workers arrive, then all deliver the same idempotency key.
        key = "idem-concurrent-1"
        results = []

        def worker():
            s, _ = self.client.post("/admin/barriers/conc-1?waiters=4", headers=self.admin)
            results.append(("arrive", s))
            s, _ = self.client.get("/admin/barriers/conc-1?wait=1", headers=self.admin)
            results.append(("released", s))
            s, _ = self.client.post("/events", {"kind": "webhook"}, headers={"Idempotency-Key": key})
            results.append(("deliver", s))

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len([r for r in results if r == ("deliver", 201)]), 1,
                         "exactly one delivery may create the record")
        _, body = self.client.get("/events?limit=100")
        self.assertEqual(len([e for e in body["events"] if e["id"] == "evt_" + key]), 1)


if __name__ == "__main__":
    unittest.main()
