#!/usr/bin/env python3
"""Calibrated oracles for the v6 service family: pilot cases SC-2 (overdraw
refusal, transactional-invariant) and SC-4 (stable pagination). Self-
contained: scoring functions, discriminating sabotage variants, and a
calibration runner in __main__. Standard library only.

First audit of SC-2 and SC-4 (pristine seed
tests/evaluation/v6/fixtures/service/seed, 2026-09-26)
------------------------------------------------------
The pristine seed ALREADY satisfies both cases, so neither may be scored as
a missing-behavior build (pristine would PASS and the matrix could not hold):

* SC-2 — server.py `_transfer` wraps the debit+credit+ledger write in one
  BEGIN IMMEDIATE transaction, refuses an overdrawing transfer with
  `409 {"error": "insufficient funds", "balance": <current>}` after ROLLBACK,
  and records nothing on the refusal path; the seed's own suite ships
  tests/test_service.py::test_overdraw_transfer_refused_and_recorded_nothing,
  which passes on the pristine seed.
* SC-4 — server.py `_list_events` implements keyset pagination
  (`WHERE id > cursor ORDER BY id LIMIT limit+1`, `nextCursor` = last id of
  the page while more remain, stable ascending id order); the seed's suite
  ships test_pagination_is_stable_and_total, which passes on the pristine
  seed.

Both cases are therefore verify-and-harden regression guards in the SC-5
mold: each score must PASS the pristine seed and FAIL a discriminating
sabotage. Per the family's fairness notes, sealed confirmation variants
change the instance, not the contract — this file pins the public contract.

Contracts enforced (HTTP behavior + stored state; arm-blind)
------------------------------------------------------------
score_sc2 — the transactional-invariant contract of /transfers:
  * account setup works (POST /accounts returns 201);
  * an overdrawing transfer is refused with 409, a clear non-empty error,
    and the CURRENT balance named in the body — probed twice, before and
    after a valid transfer changes the balance;
  * a refusal records nothing: both account balances are unchanged and the
    ledger_entries row count is unchanged (read directly from the SQLite
    store, not via an API);
  * a valid transfer still works and stays ledger-consistent: 200, balances
    move by exactly the amount, and EXACTLY ONE ledger row is appended.
    (The seed suite checks refusal bookkeeping and end balances but never
    the ledger row count of a successful transfer — this predicate is the
    oracle's own discrimination beyond the suite.)
  * the existing behavioral suite still passes.

score_sc4 — the pagination contract of GET /events:
  * seven events are seeded; the pages are walked with limit=2 following
    nextCursor, with a hard 10-page bound (a cursor loop must terminate);
  * every page honors the limit; no page is empty (a keyset listing never
    yields an empty page);
  * concatenated pages contain every seeded event exactly once — no
    duplicates, no loss — in stable ascending id order;
  * nextCursor terminates (None on the final page);
  * the existing behavioral suite still passes.

Calibration matrix (python3 tests/evaluation/v6/oracles/cases/service_sc2_sc4.py):

    SC-2 pristine seed   -> PASS  (audit: the invariant already holds)
    SC-2 sabotage        -> FAIL  (double-entry bookkeeping: a successful
                                 transfer logs two ledger rows; balances and
                                 the refusal path stay correct, so the seed
                                 suite stays GREEN — only the oracle's
                                 ledger-consistency predicate catches it)
    SC-4 pristine seed   -> PASS  (audit: the contract already holds)
    SC-4 sabotage        -> FAIL  (boundary duplicates: the keyset cursor
                                 comparison regresses `id > ?` -> `id >= ?`,
                                 so every page re-serves the previous page's
                                 last record)

Exit 0 iff all four hold ("CALIBRATION OK").

Purity: every subprocess runs with PYTHONDONTWRITEBYTECODE=1 and the
in-process boot scopes sys.dont_write_bytecode, so no __pycache__ appears in
the seed, the workspace, or the pack from an oracle run; nothing is imported
from the shipped pack. The store is always a disposable SQLite file
(LEDGER_DB in a temp directory) — never shared, never external.
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
    prior_dwb = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # pack purity: no __pycache__ in the workspace
    try:
        import server as svc
        importlib.reload(svc)  # drop import-time state if the module object survived
    finally:
        sys.dont_write_bytecode = prior_dwb
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
        boot["svc"].CONN.close()
    except Exception:
        pass
    try:
        boot["db_tmp"].cleanup()
    except Exception:
        pass
    if boot["prior_db"] is None:
        os.environ.pop("LEDGER_DB", None)
    else:
        os.environ["LEDGER_DB"] = boot["prior_db"]


def _ledger_count(db_path) -> int:
    """Ledger row count, read directly from the store (bypasses the API)."""
    db = sqlite3.connect(db_path)
    try:
        return db.execute("SELECT COUNT(*) FROM ledger_entries").fetchone()[0]
    finally:
        db.close()


def _suite_reasons(root: Path) -> list:
    """The existing behavioral suite must still pass (its own ephemeral
    server and disposable DB, in a subprocess with the purity env)."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        suite = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=str(root), capture_output=True, text=True, timeout=600, env=env)
    except (subprocess.TimeoutExpired, OSError):
        return ["existing behavioral suite timed out or could not start"]
    return [] if suite.returncode == 0 else ["existing behavioral suite regressed"]


def _balance(base, ident):
    s, body = _req(base, "GET", f"/accounts/{ident}")
    return s, body.get("balance") if isinstance(body, dict) else None


def _assert_balances(base, expected, reasons):
    for ident, want in expected.items():
        s, got = _balance(base, ident)
        if s != 200 or got != want:
            reasons.append(f"GET /accounts/{ident} returned {s} with balance "
                           f"{got!r}, expected {want}")


# ------------------------------------------------------------------- SC-2

def score_sc2(root: Path, seed_root: Path) -> dict:
    """SC-2: an overdrawing transfer is refused with 409 + current balance
    and records nothing; a valid transfer moves funds and records exactly
    one ledger row; the existing behavioral suite still passes."""
    reasons = _suite_reasons(root)
    try:
        boot = _boot_service(root)
    except Exception as exc:
        reasons.append(f"service could not boot: {exc}")
        return _result(FAIL, reasons)
    try:
        base, db_path = boot["base"], boot["db_path"]

        s, _ = _req(base, "POST", "/accounts", {"id": "oracle-src", "balance": 5})
        s2, _ = _req(base, "POST", "/accounts", {"id": "oracle-dst", "balance": 100})
        if (s, s2) != (201, 201):
            reasons.append(f"fixture setup failed: POST /accounts returned {(s, s2)}, "
                           "expected 201 for both")
            return _result(FAIL, reasons)

        baseline = _ledger_count(db_path)

        # Overdraw refusal, before any balance moved: 409, clear error,
        # current balance named, and nothing recorded anywhere.
        s, body = _req(base, "POST", "/transfers",
                       {"from": "oracle-src", "to": "oracle-dst", "amount": 6})
        if s != 409:
            reasons.append(f"overdraw transfer returned {s}, expected 409")
        if not isinstance(body, dict) or not isinstance(body.get("error"), str) \
                or not body["error"].strip():
            reasons.append("the overdraw refusal carries no clear error message")
        if not isinstance(body, dict) or body.get("balance") != 5:
            reasons.append(f"the overdraw refusal does not name the current balance 5 "
                           f"(body: {body!r})")
        _assert_balances(base, {"oracle-src": 5, "oracle-dst": 100}, reasons)
        if _ledger_count(db_path) != baseline:
            reasons.append("a refused transfer recorded a ledger entry; a refusal "
                           "must record nothing")

        # The happy path must still work AND stay ledger-consistent.
        s, body = _req(base, "POST", "/transfers",
                       {"from": "oracle-src", "to": "oracle-dst", "amount": 3})
        if s != 200:
            reasons.append(f"a valid transfer returned {s}, expected 200")
        _assert_balances(base, {"oracle-src": 2, "oracle-dst": 103}, reasons)
        after_valid = _ledger_count(db_path)
        if after_valid != baseline + 1:
            reasons.append(f"a successful transfer must record exactly one ledger "
                           f"row (ledger went {baseline} -> {after_valid})")

        # Second refusal, now against the moved balance: the 409 must name
        # the CURRENT balance and still record nothing. The expectation is
        # anchored to the post-valid-transfer count, so this predicate stays
        # about the refusal itself no matter what the happy path did.
        s, body = _req(base, "POST", "/transfers",
                       {"from": "oracle-src", "to": "oracle-dst", "amount": 3})
        if s != 409:
            reasons.append(f"second overdraw transfer returned {s}, expected 409")
        if not isinstance(body, dict) or body.get("balance") != 2:
            reasons.append(f"the second overdraw refusal does not name the current "
                           f"balance 2 (body: {body!r})")
        _assert_balances(base, {"oracle-src": 2, "oracle-dst": 103}, reasons)
        if _ledger_count(db_path) != after_valid:
            reasons.append("the second refused transfer changed the ledger; a "
                           "refusal must record nothing")
    except Exception as exc:
        reasons.append(f"service oracle could not run: {exc}")
    finally:
        _shutdown(boot)
    return _result(PASS if not reasons else FAIL, reasons)


def sabotage_sc2(workspace_root: Path):
    """Broken variant for the SC-2 audit: a plausible double-entry
    bookkeeping regression — every SUCCESSFUL transfer logs two ledger rows
    (one per leg) while balances and the refusal path stay correct. The
    seed's behavioral suite stays green (it never counts a successful
    transfer's ledger rows); only the oracle's ledger-consistency predicate
    catches it."""
    path = workspace_root / "server.py"
    text = path.read_text(encoding="utf-8")
    if text.count("INSERT INTO ledger_entries") > 1:
        return  # idempotent
    old = ('''                CONN.execute("INSERT INTO ledger_entries (from_acct, to_acct, amount)"
                             " VALUES (?, ?, ?)", (src, dst, amount))
                CONN.commit()''')
    new = ('''                # sabotage: the transfer is logged twice (debit and credit
                # each get their own ledger row); balances stay correct and
                # the refusal path is untouched.
                CONN.execute("INSERT INTO ledger_entries (from_acct, to_acct, amount)"
                             " VALUES (?, ?, ?)", (src, dst, amount))
                CONN.execute("INSERT INTO ledger_entries (from_acct, to_acct, amount)"
                             " VALUES (?, ?, ?)", (src, dst, amount))
                CONN.commit()''')
    assert old in text, "sc2 sabotage anchor not found"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ------------------------------------------------------------------- SC-4

def score_sc4(root: Path, seed_root: Path) -> dict:
    """SC-4: walking GET /events pages by nextCursor yields every event
    exactly once in stable ascending id order; every page honors the limit;
    no page is empty; the cursor terminates; the existing behavioral suite
    still passes."""
    reasons = _suite_reasons(root)
    try:
        boot = _boot_service(root)
    except Exception as exc:
        reasons.append(f"service could not boot: {exc}")
        return _result(FAIL, reasons)
    try:
        base = boot["base"]

        seeded = sorted(f"evt_oracle-page-{i}" for i in range(7))
        setup_failed = False
        for i in range(7):
            s, _ = _req(base, "POST", "/events", {"n": i},
                        headers={"Idempotency-Key": f"oracle-page-{i}"})
            if s != 201:
                reasons.append(f"fixture setup failed: POST /events page-{i} "
                               f"returned {s}")
                setup_failed = True
        if setup_failed:
            return _result(FAIL, reasons)

        limit = 2
        seen = []
        cursor = None
        empty_pages = []
        for page_no in range(1, 11):  # hard bound: pagination must terminate
            path = f"/events?limit={limit}" + (f"&cursor={cursor}" if cursor else "")
            s, body = _req(base, "GET", path)
            if s != 200 or not isinstance(body, dict) or not isinstance(body.get("events"), list):
                reasons.append(f"GET {path} returned {s}; expected 200 with an "
                               "events list")
                break
            page = body["events"]
            if len(page) > limit:
                reasons.append(f"page {page_no} returned {len(page)} events with "
                               f"limit={limit}")
            if not page:
                empty_pages.append(page_no)
            for entry in page:
                if not isinstance(entry, dict) or not entry.get("id"):
                    reasons.append(f"page {page_no}: malformed event entry: {entry!r}")
            seen.extend(e.get("id") for e in page if isinstance(e, dict))
            next_cursor = body.get("nextCursor")
            if not next_cursor:
                break  # terminated
            if next_cursor == cursor:
                reasons.append("pagination replayed the same cursor; it does not "
                               "advance")
                break
            cursor = next_cursor
        else:
            reasons.append("pagination did not terminate within 10 pages; "
                           "nextCursor never became None")
        if empty_pages:
            reasons.append(f"pagination served empty page(s) {empty_pages}; a "
                           "keyset listing never yields an empty page")

        duplicates = len(seen) - len(set(seen))
        if duplicates:
            reasons.append(f"pages duplicated {duplicates} event(s)")
        if set(seen) != set(seeded):
            missing = sorted(set(seeded) - set(seen))
            extra = sorted(set(seen) - set(seeded))
            if missing:
                reasons.append(f"pages lost events: {missing}")
            if extra:
                reasons.append(f"pages contain unknown events: {extra}")
        if len(seen) == len(set(seen)) and seen != sorted(seen):
            reasons.append("listing order is not stable ascending id order across "
                           "pages")
    except Exception as exc:
        reasons.append(f"service oracle could not run: {exc}")
    finally:
        _shutdown(boot)
    return _result(PASS if not reasons else FAIL, reasons)


def sabotage_sc4(workspace_root: Path):
    """Broken variant for the SC-4 audit: the classic keyset off-by-one —
    the cursor comparison regresses from `id > ?` to `id >= ?`, so every
    page after the first re-serves the previous page's last record. The
    listing still terminates and never loses a record, but the concatenated
    pages contain boundary duplicates."""
    path = workspace_root / "server.py"
    text = path.read_text(encoding="utf-8")
    old = '" WHERE id > ? ORDER BY id LIMIT ?", (cursor, limit + 1)).fetchall()'
    new = '" WHERE id >= ? ORDER BY id LIMIT ?", (cursor, limit + 1)).fetchall()'
    if old not in text:
        if new in text:
            return  # idempotent
        raise AssertionError("sc4 sabotage anchor not found")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# ----------------------------------------------------------------- runner

def _prepare(seed_root: Path, op) -> Path:
    """A disposable workspace: a copy of the seed with the variant applied."""
    work_parent = Path(tempfile.mkdtemp(prefix="sc2-sc4-case-"))
    work = work_parent / "ws"
    shutil.copytree(seed_root, work, symlinks=False)
    if op is not None:
        op(work)
    return work


def main() -> int:
    repo = Path(__file__).resolve().parents[5]
    seed = repo / "tests" / "evaluation" / "v6" / "fixtures" / "service" / "seed"
    if not seed.is_dir():
        print(f"seed fixture not found: {seed}", file=sys.stderr)
        return 2
    rounds = [
        # (case id, variant op or None, scorer, expected verdict)
        ("SC-2/pristine (audit)", None, score_sc2, PASS),
        ("SC-2/sabotage (discrimination)", sabotage_sc2, score_sc2, FAIL),
        ("SC-4/pristine (audit)", None, score_sc4, PASS),
        ("SC-4/sabotage (discrimination)", sabotage_sc4, score_sc4, FAIL),
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
              f"(expected {expected})", flush=True)
        for reason in result["reasons"]:
            print(f"       {reason}", flush=True)
        shutil.rmtree(work.parent, ignore_errors=True)
    print("CALIBRATION " + ("OK" if all_ok else "FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
