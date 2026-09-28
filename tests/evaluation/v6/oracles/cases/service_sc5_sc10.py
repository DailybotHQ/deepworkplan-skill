#!/usr/bin/env python3
"""Calibrated oracles for the v6 service family: pilot case SC-5 and the new
public case SC-10. Self-contained: scoring functions, reference fix, sabotage
variants, and a calibration runner in __main__. Standard library only.

First audit of SC-5 (pristine seed tests/evaluation/v6/fixtures/service/seed)
---------------------------------------------------------------------------
The pristine seed ALREADY satisfies SC-5: the seed's /events handler
deduplicates deliveries of one Idempotency-Key under its write lock, replays
the original response, and the seed's own suite ships a barrier-aligned
concurrent duplicate-delivery test
(tests/test_service.py::test_concurrent_duplicate_delivery_creates_exactly_one_record).
SC-5 is therefore a verify-and-harden case, not a missing-behavior case:
its oracle (score_sc5) must PASS the pristine seed and still FAIL a broken
variant (sabotage_sc5, below). The family's missing-behavior calibrated case
is SC-10: reference apply()/sabotage() live here and follow the same calling
convention as tests/evaluation/v6/oracles/reference/*.py (apply(workspace_root)
/ sabotage(workspace_root) over a copy of the seed).

SC-10 public objective + acceptance contract (public material; the
orchestrator appends this row to tests/evaluation/v6/fixtures/service/CASES.md)
-----------------------------------------------------------------------------
| SC-10 | pagination | medium | Add `GET /accounts` listing accounts with `limit`/`cursor` keyset pagination in stable id order. | Every page honors `limit`; concatenated pages contain every account exactly once in stable id order; `nextCursor` terminates; account balances are returned with their accounts; `GET /accounts/{id}` and the existing behavioral suite still pass. |

Prose form: the ledger service exposes the account listing over HTTP.
GET /accounts supports limit/cursor keyset pagination with the same contract
as GET /events: accounts come back in stable ascending id order, at most
`limit` per page (default 20, cap 100), `nextCursor` carries the last id of
the page while more remain, and walking the pages yields every account
exactly once (no duplicates, no loss).

Score model (the house rule, mirroring tests/evaluation/v6/oracles/oracles.py):
PASS only when every assertion is evidenced by the live artifact; missing
evidence is a failure reason, never a pass. Oracles are arm-blind: each one
boots the workspace's real server in-process and judges only HTTP behavior
and stored state — never arm labels or narration.

Calibration matrix (python3 tests/evaluation/v6/oracles/cases/service_sc5_sc10.py):

    SC-5 pristine seed            -> PASS  (audit: the seed already satisfies SC-5)
    SC-5 sabotaged dedup          -> FAIL  (the oracle catches a broken repair)
    SC-10 pristine seed           -> FAIL  (GET /accounts does not exist yet)
    SC-10 + reference apply()     -> PASS
    SC-10 + reference sabotage()  -> FAIL  (cross-page record leak + unstable order)

Exit 0 iff all five hold ("CALIBRATION OK").
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

PASS, FAIL = "PASS", "FAIL"


def _result(verdict, reasons):
    return {"verdict": verdict, "reasons": reasons}


def _req(base, method, path, body=None, headers=None):
    """One JSON HTTP round trip; returns (status, parsed body)."""
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def _boot_service(root: Path):
    """Boot the workspace's real ledger server in-process on an ephemeral
    port with a disposable SQLite database (pattern: the seed's own test
    harness). The caller must eventually call _shutdown(boot)."""
    prior_db = os.environ.get("LEDGER_DB")
    db_tmp = tempfile.TemporaryDirectory(prefix="oracle-service-db-")
    os.environ["LEDGER_DB"] = os.path.join(db_tmp.name, "oracle.db")
    sys.modules.pop("server", None)  # never reuse a previous workspace's module
    path_entry = str(root)
    sys.path.insert(0, path_entry)
    import server as svc
    importlib.reload(svc)  # drop import-time state if the module object survived
    svc.DB_PATH = os.environ["LEDGER_DB"]
    svc.CONN = svc.connect()
    svc.init_schema(svc.CONN)
    httpd = svc.ThreadingHTTPServer(("127.0.0.1", 0), svc.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return {
        "svc": svc,
        "httpd": httpd,
        "base": f"http://127.0.0.1:{httpd.server_address[1]}",
        "db_path": svc.DB_PATH,
        "path_entry": path_entry,
        "db_tmp": db_tmp,
        "prior_db": prior_db,
    }


def _shutdown(boot):
    try:
        boot["httpd"].shutdown()
        boot["httpd"].server_close()
    except Exception:
        pass
    if boot["path_entry"] in sys.path:
        sys.path.remove(boot["path_entry"])
    sys.modules.pop("server", None)
    try:
        boot["db_tmp"].cleanup()
    except Exception:
        pass
    if boot["prior_db"] is None:
        os.environ.pop("LEDGER_DB", None)
    else:
        os.environ["LEDGER_DB"] = boot["prior_db"]


# ------------------------------------------------------------------- SC-5

def _aligned_duplicate_delivery_round(base, admin, key, n, round_no, db_path):
    """Deliver one Idempotency-Key from n threads aligned by the service's
    own barrier (arrive via POST, block via GET ?wait=1 — no sleeps) and
    return the failure reasons for the exactly-once contract."""
    reasons = []
    name = f"oracle-sc5-b{round_no}"
    arrive_status = []
    arrive_states = []
    released_flags = []
    deliveries = []
    errors = []

    def worker():
        try:
            s, body = _req(base, "POST", f"/admin/barriers/{name}?waiters={n}",
                           headers=admin)
            arrive_status.append(s)
            if s == 200 and isinstance(body, dict):
                arrive_states.append((body.get("arrived"), bool(body.get("released"))))
            s, body = _req(base, "GET", f"/admin/barriers/{name}?wait=1", headers=admin)
            released_flags.append(bool(isinstance(body, dict) and body.get("released")))
            s, body = _req(base, "POST", "/events", {"kind": "webhook", "round": round_no},
                           headers={"Idempotency-Key": key})
            deliveries.append((s, body))
        except Exception as exc:
            errors.append(f"round {round_no}: worker transport error: {exc}")

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    reasons.extend(errors)
    if len(arrive_status) != n or any(s != 200 for s in arrive_status):
        reasons.append(f"round {round_no}: barrier arrival failed "
                       f"(statuses {arrive_status}, expected {n} x 200)")
    if len(arrive_states) == n:
        arrivals = sorted(a for a, _ in arrive_states if isinstance(a, int))
        if arrivals != list(range(1, n + 1)):
            reasons.append(f"round {round_no}: barrier arrival sequence {arrive_states} "
                           f"is not 1..{n}")
        early = [a for a, r in arrive_states if r and a != n]
        if early:
            reasons.append(f"round {round_no}: barrier released at arrival {early}, "
                           f"expected release only at arrival {n}")
    if len(released_flags) != n or not all(released_flags):
        reasons.append(f"round {round_no}: barrier did not release all workers; "
                       "deliveries were not simultaneous")

    created = [(s, b) for s, b in deliveries if s == 201]
    if len(created) != 1:
        reasons.append(f"round {round_no}: expected exactly one 201 among {n} duplicate "
                       f"deliveries, saw {len(created)}")
        return reasons
    created_id = created[0][1].get("id")
    for pos, (s, b) in enumerate(deliveries):
        if s == 201:
            continue
        if s != 200:
            reasons.append(f"round {round_no}: delivery {pos} returned {s}, "
                           "expected a 200 replay")
            continue
        if not b.get("replay"):
            reasons.append(f"round {round_no}: delivery {pos} lacks the replay marker")
        if b.get("id") != created_id:
            reasons.append(f"round {round_no}: delivery {pos} replayed id {b.get('id')!r}, "
                           f"expected the original {created_id!r}")

    s, body = _req(base, "GET", "/events?limit=100")
    if s != 200 or not isinstance(body, dict):
        reasons.append(f"round {round_no}: GET /events returned {s}; the stored "
                       "record is not verifiable over HTTP")
    else:
        hits = [e for e in body.get("events", []) if e.get("id") == created_id]
        if len(hits) != 1:
            reasons.append(f"round {round_no}: the event listing shows {len(hits)} "
                           "records for the delivery, expected exactly one")
    try:
        db = sqlite3.connect(db_path)
        stored = db.execute("SELECT COUNT(*) FROM events WHERE idem_key = ?",
                            (key,)).fetchone()[0]
        db.close()
        if stored != 1:
            reasons.append(f"round {round_no}: stored row count for the key is {stored}, "
                           "expected 1")
    except sqlite3.Error as exc:
        reasons.append(f"round {round_no}: stored state not inspectable in the fixture "
                       f"schema: {exc}")
    return reasons


def score_sc5(root: Path, seed_root: Path) -> dict:
    """SC-5: N simultaneous duplicate deliveries of one Idempotency-Key,
    aligned by the service's own barriers (no sleeps), create exactly one
    record — exactly one delivery returns 201, the rest replay the original
    response, and stored state holds a single record for the key."""
    reasons = []
    try:
        boot = _boot_service(root)
    except Exception as exc:
        return _result(FAIL, [f"service could not boot: {exc}"])
    try:
        admin = {"X-Admin-Token": boot["svc"].ADMIN_TOKEN}
        # Round 1 uses the public contract's N=4; round 2 checks the behavior
        # generalizes (a correct implementation handles any waiter count).
        for round_no, (key, workers) in enumerate(
                [("oracle-sc5-r1", 4), ("oracle-sc5-r2", 6)], start=1):
            reasons.extend(_aligned_duplicate_delivery_round(
                boot["base"], admin, key, workers, round_no, boot["db_path"]))
    except Exception as exc:
        reasons.append(f"service oracle could not run: {exc}")
    finally:
        _shutdown(boot)
    return _result(PASS if not reasons else FAIL, reasons)


def sabotage_sc5(workspace_root: Path):
    """Broken variant for the SC-5 audit: a plausible wrong repair of
    /events in which every redelivery of a known key mints a NEW sibling
    record and returns 201 instead of replaying the original response."""
    path = workspace_root / "server.py"
    text = path.read_text(encoding="utf-8")
    old = '''                return self._send(200, {
                    "id": row["id"], "replay": True,
                    "payload": json.loads(row["payload"]),
                    "schemaVersion": row["schema_version"],
                })'''
    new = '''                # sabotage: no replay — every redelivery creates a
                # sibling record and reports 201.
                n = CONN.execute("SELECT COUNT(*) FROM events").fetchone()[0]
                sibling_id = row["id"] + "-dup-" + str(n)
                sibling_key = row["idem_key"] + "-dup-" + str(n)
                payload = json.loads(row["payload"])
                response = {"id": sibling_id, "payload": payload,
                            "schemaVersion": row["schema_version"]}
                CONN.execute(
                    "INSERT INTO events (id, idem_key, payload, response_code,"
                    " response_body, schema_version) VALUES (?, ?, ?, ?, ?, ?)",
                    (sibling_id, sibling_key, json.dumps(payload), 201,
                     json.dumps(response), row["schema_version"]))
                CONN.commit()
                return self._send(201, response)'''
    assert old in text, "sc5 sabotage anchor not found"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ------------------------------------------------------------------ SC-10

def score_sc10(root: Path, seed_root: Path) -> dict:
    """SC-10: GET /accounts lists accounts with limit/cursor keyset
    pagination in stable id order; walking the pages yields every account
    exactly once; nextCursor terminates; GET /accounts/{id} and the existing
    behavioral suite still pass."""
    reasons = []
    try:
        suite = subprocess.run(
            f'"{sys.executable}" -m unittest discover -s tests',
            shell=True, cwd=str(root), capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        reasons.append("existing behavioral suite timed out")
    else:
        if suite.returncode != 0:
            reasons.append("existing behavioral suite regressed")
    try:
        boot = _boot_service(root)
    except Exception as exc:
        reasons.append(f"service could not boot: {exc}")
        return _result(FAIL, reasons)
    try:
        base = boot["base"]
        # Deliberately inserted in non-sorted order: an insertion-ordered or
        # rowid-ordered listing must not pass the stable-order contract.
        catalog = [
            ("acct-m04", 13), ("acct-a01", 3), ("acct-x99", 21), ("acct-b07", 8),
            ("acct-k15", 5), ("acct-z02", 34), ("acct-f33", 1),
        ]
        balances = dict(catalog)
        expected_ids = sorted(balances)
        for ident, balance in catalog:
            s, _ = _req(base, "POST", "/accounts", {"id": ident, "balance": balance})
            if s != 201:
                reasons.append(f"fixture setup failed: POST /accounts {ident} "
                               f"returned {s}")
        if any(r.startswith("fixture setup failed") for r in reasons):
            return _result(FAIL, reasons)

        limit = 3
        seen_ids = []
        cursor = None
        for page_no in range(1, 11):  # hard bound: pagination must terminate
            path = f"/accounts?limit={limit}" + (f"&cursor={cursor}" if cursor else "")
            s, body = _req(base, "GET", path)
            if s != 200 or not isinstance(body, dict) or not isinstance(body.get("accounts"), list):
                reasons.append(f"GET {path} returned {s}; expected 200 with an "
                               "accounts list")
                break
            page = body["accounts"]
            if len(page) > limit:
                reasons.append(f"page {page_no} returned {len(page)} accounts with "
                               f"limit={limit}")
            for entry in page:
                if not isinstance(entry, dict) or "id" not in entry or "balance" not in entry:
                    reasons.append(f"page {page_no}: account entry missing id or "
                                   f"balance: {entry!r}")
                elif balances.get(entry.get("id")) != entry.get("balance"):
                    reasons.append(f"page {page_no}: account {entry.get('id')!r} has "
                                   f"balance {entry.get('balance')!r}, expected "
                                   f"{balances.get(entry.get('id'))!r}")
            seen_ids.extend(e.get("id") for e in page)
            next_cursor = body.get("nextCursor")
            if not next_cursor:
                break
            if next_cursor == cursor:
                reasons.append("pagination replayed the same cursor; it does not advance")
                break
            cursor = next_cursor
        else:
            reasons.append("pagination did not terminate within 10 pages")

        duplicates = len(seen_ids) - len(set(seen_ids))
        if duplicates:
            reasons.append(f"pages duplicated {duplicates} account(s)")
        if set(seen_ids) != set(expected_ids):
            missing = sorted(set(expected_ids) - set(seen_ids))
            extra = sorted(set(seen_ids) - set(expected_ids))
            if missing:
                reasons.append(f"pages lost accounts: {missing}")
            if extra:
                reasons.append(f"pages contain unknown accounts: {extra}")
        if len(seen_ids) == len(set(seen_ids)) and seen_ids != sorted(seen_ids):
            reasons.append("listing order is not stable ascending id order across pages")

        s, body = _req(base, "GET", "/accounts")
        if s != 200 or not isinstance(body, dict) or not isinstance(body.get("accounts"), list):
            reasons.append(f"GET /accounts (no params) returned {s}; expected 200")
        elif sorted(e.get("id") for e in body["accounts"]) != expected_ids:
            reasons.append("the unparameterized listing does not return every account "
                           "exactly once in stable order")

        s, body = _req(base, "GET", "/accounts/acct-a01")
        if s != 200 or body.get("balance") != 3:
            reasons.append("GET /accounts/{id} regressed")
    except Exception as exc:
        reasons.append(f"service oracle could not run: {exc}")
    finally:
        _shutdown(boot)
    return _result(PASS if not reasons else FAIL, reasons)


def apply(workspace_root: Path):
    """Reference fix for SC-10: add GET /accounts with the same keyset
    pagination contract as GET /events (stable order by id, limit default 20
    and cap 100, nextCursor when more remain). Idempotent."""
    path = workspace_root / "server.py"
    text = path.read_text(encoding="utf-8")
    if "def _list_accounts" in text:
        return  # idempotent
    anchor = '''        if parts[:1] == ["accounts"] and len(parts) == 2:
            return self._get_account(parts[1])'''
    replacement = '''        if parts[:1] == ["accounts"] and len(parts) == 1:
            return self._list_accounts(query)
        if parts[:1] == ["accounts"] and len(parts) == 2:
            return self._get_account(parts[1])'''
    assert anchor in text, "routing anchor not found"
    text = text.replace(anchor, replacement, 1)

    handler = '''    def _list_accounts(self, query):
        limit = min(int(query.get("limit", ["20"])[0]), 100)
        cursor = query.get("cursor", [None])[0]
        with _lock:
            if cursor:
                rows = CONN.execute(
                    "SELECT id, balance FROM accounts WHERE id > ? ORDER BY id LIMIT ?",
                    (cursor, limit + 1)).fetchall()
            else:
                rows = CONN.execute(
                    "SELECT id, balance FROM accounts ORDER BY id LIMIT ?",
                    (limit + 1,)).fetchall()
        has_more = len(rows) > limit
        rows = rows[:limit]
        return self._send(200, {
            "accounts": [{"id": r["id"], "balance": r["balance"]} for r in rows],
            "nextCursor": rows[-1]["id"] if has_more and rows else None,
        })

'''
    anchor2 = "    def _get_account(self, account_id):"
    assert anchor2 in text, "handler anchor not found"
    text = text.replace(anchor2, handler + anchor2, 1)
    path.write_text(text, encoding="utf-8")


def sabotage(workspace_root: Path):
    """Broken variant of SC-10: the listing exists but leaks records across
    page scopes and loses the stable order — the cursor is ignored, so every
    page re-serves the first `limit` accounts (rows belonging to other pages
    leak into each listing — the single-store analog of leaking other
    tenants' accounts), and rows come back in insertion (rowid) order
    instead of stable id order."""
    apply(workspace_root)
    path = workspace_root / "server.py"
    text = path.read_text(encoding="utf-8")
    old = '''        cursor = query.get("cursor", [None])[0]
        with _lock:
            if cursor:
                rows = CONN.execute(
                    "SELECT id, balance FROM accounts WHERE id > ? ORDER BY id LIMIT ?",
                    (cursor, limit + 1)).fetchall()
            else:
                rows = CONN.execute(
                    "SELECT id, balance FROM accounts ORDER BY id LIMIT ?",
                    (limit + 1,)).fetchall()'''
    new = '''        cursor = query.get("cursor", [None])[0]
        with _lock:
            # sabotage: the cursor is ignored and rows come back in
            # insertion order — pages leak each other's records and the
            # stable id order is lost.
            rows = CONN.execute(
                "SELECT id, balance FROM accounts ORDER BY rowid LIMIT ?",
                (limit,)).fetchall()'''
    assert old in text, "sabotage anchor not found"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ----------------------------------------------------------------- runner

def _prepare(seed_root: Path, op) -> Path:
    """A disposable workspace: a copy of the seed with the variant applied."""
    work_parent = Path(tempfile.mkdtemp(prefix="sc5-sc10-case-"))
    work = work_parent / "ws"
    shutil.copytree(seed_root, work, symlinks=False)
    if op is not None:
        op(work)
    return work


def main() -> int:
    repo = Path(__file__).resolve().parents[5]
    seed = repo / "tests" / "evaluation" / "v6" / "fixtures" / "service" / "seed"
    rounds = [
        # (case id, variant op or None, scorer, expected verdict)
        ("SC-5/pristine (audit)", None, score_sc5, PASS),
        ("SC-5/sabotage (discrimination)", sabotage_sc5, score_sc5, FAIL),
        ("SC-10/pristine", None, score_sc10, FAIL),
        ("SC-10/apply (reference fix)", apply, score_sc10, PASS),
        ("SC-10/sabotage", sabotage, score_sc10, FAIL),
    ]
    all_ok = True
    for case_id, op, score, expected in rounds:
        work = _prepare(seed, op)
        try:
            result = score(work, seed)
        except Exception as exc:
            result = _result(FAIL, [f"oracle raised: {exc}"])
        ok = result["verdict"] == expected
        all_ok = all_ok and ok
        print(f"{'OK  ' if ok else 'FAIL'} {case_id}: {result['verdict']} "
              f"(expected {expected})")
        for reason in result["reasons"]:
            print(f"       {reason}")
        shutil.rmtree(work.parent, ignore_errors=True)
    print("CALIBRATION " + ("OK" if all_ok else "FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
