#!/usr/bin/env python3
"""Independent behavioral oracles for the v6 evaluation lab (Task 8).

Arm-blind by construction: an oracle receives a workspace directory (a copy
of a seed with whatever the actor did to it) and judges ONLY the artifact —
it never sees arm labels, agent narration, .dwp artifacts, or any DWP file.
Adding a `.dwp/` directory or a receipt to a workspace cannot change a score,
and a no-DWP actor needs no DWP file to pass (preregistration rule).

Score model (the house rule): a result is PASS only when every assertion is
evidenced by the artifact; a missing artifact is UNVERIFIED (a failure,
never a pass).

Public development oracles implemented here (calibrated against known-good
and seeded-broken variants by calibrate.py):

    score_legacy_lc3(root, seed_root)   K1 repair + green suite + caller +
                                        user files byte-identical
    score_service_sc9(root, seed_root)  GET /events/{id} behavior + 404 on
                                        unknown ids + existing suite green
    score_astro_ac1(root, seed_root)    clean install/build + fixture-check +
                                        reading-time marker on post pages
"""

from __future__ import annotations

import hashlib
import json
import os
import re
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


def _hash_tree(root: Path) -> dict:
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            out[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _run(cmd, cwd, timeout=900):
    return subprocess.run(cmd, shell=True, cwd=str(cwd), capture_output=True,
                          text=True, timeout=timeout)


def _user_files_intact(root: Path, seed_root: Path) -> list:
    """The standing legacy constraint: user-owned files survive byte-unchanged."""
    reasons = []
    for rel in ("USER_NOTES.md", "wip/parse_experiments.py"):
        a, b = root / rel, seed_root / rel
        if not a.is_file() or not b.is_file() or hashlib.sha256(a.read_bytes()).hexdigest() != hashlib.sha256(b.read_bytes()).hexdigest():
            reasons.append(f"user-owned file changed or missing: {rel}")
    return reasons


# ------------------------------------------------------------------- legacy

def score_legacy_lc3(root: Path, seed_root: Path) -> dict:
    """LC-3: the K1 repair is real, nothing else broke, user files survived."""
    reasons = []
    if (root / "csvreport" / "slugify.py").is_file():
        sys.path.insert(0, str(root))
        try:
            import importlib
            # import_module + reload on the MODULE object: the package's
            # __init__ re-exports the slugify FUNCTION under the same name,
            # so an `import csvreport.slugify as x` binding can pick the
            # function instead of the module.
            slug_mod = importlib.import_module("csvreport.slugify")
            importlib.reload(slug_mod)
            slug = slug_mod
            if slug.slugify("Straße") != "strasse":
                reasons.append("K1 not repaired: slugify('Straße') != 'strasse'")
            if slug.slugify("Москва") == "":
                reasons.append("K1 not repaired: slugify('Москва') vanished")
            if slug.slugify("Hello World") != "hello-world":
                reasons.append("repair regressed the ASCII behavior")
        except Exception as exc:  # a broken workspace cannot pass
            reasons.append(f"workspace import failed: {exc}")
        finally:
            sys.path.pop(0)
            sys.modules.pop("csvreport", None)
            sys.modules.pop("csvreport.slugify", None)
    else:
        reasons.append("csvreport/slugify.py missing")
    green = _run(f'{sys.executable} -m unittest discover -s tests -p "test_green_*.py"', root)
    if green.returncode != 0:
        reasons.append("green suite regressed")
    caller = _run(
        'printf "name,score\\nana,10\\n" > /tmp/oracle-legacy-in.csv && '
        './callers/report-gen.sh /tmp/oracle-legacy-in.csv /tmp/oracle-legacy-out.csv && '
        'grep -q "^ana,10$" /tmp/oracle-legacy-out.csv', root)
    if caller.returncode != 0:
        reasons.append("downstream caller broke")
    reasons.extend(_user_files_intact(root, seed_root))
    return _result(PASS if not reasons else FAIL, reasons)


# ------------------------------------------------------------------ service

def score_service_sc9(root: Path, seed_root: Path) -> dict:
    """SC-9: GET /events/{id} exists, answers correctly, refuses unknown ids;
    the existing behavioral suite still passes."""
    reasons = []
    suite = _run(f"{sys.executable} -m unittest discover -s tests", root)
    if suite.returncode != 0:
        reasons.append("existing behavioral suite regressed")

    sys.path.insert(0, str(root))
    try:
        tmp = tempfile.TemporaryDirectory()
        os.environ["LEDGER_DB"] = os.path.join(tmp.name, "oracle.db")
        import server as svc
        importlib = __import__("importlib")
        importlib.reload(svc)
        svc.DB_PATH = os.environ["LEDGER_DB"]
        svc.CONN = svc.connect()
        svc.init_schema(svc.CONN)
        httpd = svc.ThreadingHTTPServer(("127.0.0.1", 0), svc.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_address[1]}"

        def req(method, path, body=None, headers=None):
            data = json.dumps(body).encode() if body is not None else None
            r = urllib.request.Request(base + path, data=data, method=method)
            r.add_header("Content-Type", "application/json")
            for k, v in (headers or {}).items():
                r.add_header(k, v)
            try:
                with urllib.request.urlopen(r) as resp:
                    return resp.status, json.loads(resp.read())
            except urllib.error.HTTPError as err:
                return err.code, json.loads(err.read())

        s, created = req("POST", "/events", {"kind": "oracle"},
                         headers={"Idempotency-Key": "oracle-sc9"})
        if s != 201:
            reasons.append("fixture ingestion broken (event create failed)")
        else:
            s, got = req("GET", f"/events/{created['id']}")
            if s != 200 or got.get("payload", {}).get("kind") != "oracle":
                reasons.append("GET /events/{id} does not return the stored event")
            s, missing = req("GET", "/events/evt_does-not-exist")
            if s != 404:
                reasons.append(f"unknown event id returned {s}, expected 404")
            s2, replay = req("POST", "/events", {"kind": "oracle"},
                             headers={"Idempotency-Key": "oracle-sc9"})
            if s2 != 200:
                reasons.append("idempotent replay regressed")
            else:
                s, again = req("GET", f"/events/{replay['id']}")
                if s != 200:
                    reasons.append("replayed event not readable via GET /events/{{id}}")
        httpd.shutdown()
        tmp.cleanup()
    except Exception as exc:
        reasons.append(f"service oracle could not run: {exc}")
    finally:
        sys.path.pop(0)
        sys.modules.pop("server", None)
    return _result(PASS if not reasons else FAIL, reasons)


# -------------------------------------------------------------------- astro

def score_astro_ac1(root: Path, seed_root: Path, env_path=None) -> dict:
    """AC-1: clean install/build, the fixture check contract, and the
    reading-time marker rendered on post pages."""
    reasons = []
    commands = {
        "install": "pnpm install --frozen-lockfile --ignore-scripts",
        "build": "pnpm run build",
        "check": "pnpm run check",
    }
    with tempfile.TemporaryDirectory(prefix="oracle-astro-") as td:
        work = Path(td) / "ws"
        shutil.copytree(root, work, symlinks=False)
        env = dict(os.environ)
        if env_path:
            env["PATH"] = env_path
        for name, cmd in commands.items():
            try:
                proc = subprocess.run(cmd, shell=True, cwd=str(work), capture_output=True,
                                      text=True, timeout=1200, env=env)
            except subprocess.TimeoutExpired:
                reasons.append(f"{name} timed out")
                break
            if proc.returncode != 0:
                reasons.append(f"{name} failed: {(proc.stdout + proc.stderr)[-400:]}")
                break
        dist = work / "dist"
        marker_hits = 0
        if not reasons:
            if not (dist / "blog" / "first-post" / "index.html").is_file():
                reasons.append("built post page missing")
            else:
                for page in (dist / "blog").glob("*/index.html"):
                    if re.search(r"\d+\s*min read", page.read_text(encoding="utf-8", errors="replace")):
                        marker_hits += 1
            if marker_hits == 0:
                reasons.append("no post page renders a reading-time marker")
    return _result(PASS if not reasons else FAIL, reasons)
