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

def _astro_build_and_check(root: Path, reasons: list, env=None, inspect=None) -> bool:
    """Build in a disposable copy; `inspect(work)` runs BEFORE the copy is
    deleted - a path returned from inside the with-block would point at a
    removed directory (a defect a peer reviewer caught)."""
    commands = {
        "install": "pnpm install --frozen-lockfile --ignore-scripts",
        "build": "pnpm run build",
        "check": "pnpm run check",
    }
    with tempfile.TemporaryDirectory(prefix="oracle-astro-build-") as td:
        work = Path(td) / "ws"
        shutil.copytree(root, work, symlinks=False)
        for name, cmd in commands.items():
            try:
                proc = subprocess.run(cmd, shell=True, cwd=str(work), capture_output=True,
                                      text=True, timeout=1200, env=env)
            except subprocess.TimeoutExpired:
                reasons.append(f"{name} timed out")
                return False
            if proc.returncode != 0:
                reasons.append(f"{name} failed: {(proc.stdout + proc.stderr)[-400:]}")
                return False
        if inspect:
            inspect(work)
    return True



# Properties that can make an offscreen or clipped skip link reachable and
# visible on focus. A :focus rule touching only cosmetic properties (color,
# font-weight, ...) leaves an offscreen link offscreen: that is a stub, not
# a visible focus style.
_AC6_VISIBILITY_PROPS = {
    "position", "inset", "left", "right", "top", "bottom",
    "transform", "translate", "clip", "clip-path",
    "opacity", "visibility", "display", "overflow",
    "width", "height", "max-width", "max-height",
}


def _ac6_skip_link_focus(css_text: str, reasons: list) -> None:
    """Hardened .skip-link focus check. A substring test ('.skip-link' and
    ':focus' both appear somewhere) passes cosmetic stubs; this parses the
    actual rule blocks and demands a :focus rule on .skip-link whose
    declarations change a visibility or geometry property, and a base state
    that does not hard-hide the link in a way focus never undoes."""
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", css_text)
    focus_props, base_hard_hidden = set(), False
    saw_skip_rule = saw_focus_rule = False
    for selector, decls in rules:
        if ".skip-link" not in selector:
            continue
        saw_skip_rule = True
        if ":focus" in selector:
            saw_focus_rule = True
            for part in decls.split(";"):
                if ":" in part:
                    focus_props.add(part.split(":", 1)[0].strip().lower())
        else:
            flat = re.sub(r"\s+", "", decls).lower()
            if "display:none" in flat or "visibility:hidden" in flat:
                base_hard_hidden = True
    if not saw_skip_rule:
        reasons.append("no .skip-link rule in built CSS")
        return
    if not saw_focus_rule:
        reasons.append("no :focus rule selects .skip-link in built CSS")
        return
    if not focus_props:
        reasons.append(".skip-link :focus rule has empty declarations (stub)")
    elif not focus_props & _AC6_VISIBILITY_PROPS:
        reasons.append(
            ".skip-link :focus rule changes no visibility or geometry property "
            f"(stub; only {sorted(focus_props)})")
    if base_hard_hidden and not focus_props & {"display", "visibility"}:
        reasons.append(".skip-link is display:none/visibility:hidden and no "
                       ":focus rule restores it")


def score_astro_ac6(root: Path, seed_root: Path, env_path=None) -> dict:
    """AC-6: every built page starts its body with a working skip link to an
    existing #main target, with a visible :focus style in the built CSS.
    Hardened against stubs: the :focus rule must really change visibility or
    geometry, the anchor must carry the skip class, and tabindex=-1 or a
    hard-hidden base state fails."""
    reasons = []

    def inspect(work: Path):
        dist = work / "dist"
        pages = sorted(dist.rglob("index.html"))
        if len(pages) < 5:
            reasons.append(f"expected at least 5 built pages, found {len(pages)}")
        for page in pages:
            html = page.read_text(encoding="utf-8", errors="replace")
            body = html.split("<body", 1)[-1]
            first_tag = re.search(r"<a\b[^>]*>", body)
            if not first_tag:
                reasons.append(f"{page.name}: no anchor in body")
            else:
                tag = first_tag.group(0)
                href = re.search(r'href\s*=\s*["\']([^"\']*)["\']', tag)
                if not href:
                    reasons.append(f"{page.name}: first anchor has no href")
                elif href.group(1) != "#main":
                    reasons.append(f"{page.name}: first focusable link is not the skip link (href={href.group(1)!r})")
                cls = re.search(r'class\s*=\s*["\']([^"\']*)["\']', tag)
                if not cls or "skip" not in cls.group(1).lower():
                    reasons.append(f"{page.name}: first anchor carries no skip class")
                if re.search(r'tabindex\s*=\s*["\']?\s*-1', tag):
                    reasons.append(f"{page.name}: skip link removed from tab order (tabindex=-1)")
            if 'id="main"' not in html:
                reasons.append(f"{page.name}: missing #main target")
        # Astro inlines small stylesheets into the pages (inlineStylesheets
        # 'auto'): styles live in both .css bundles and inline <style> blocks.
        css_text = "".join(p.read_text(encoding="utf-8", errors="replace")
                           for p in dist.rglob("*.css"))
        for page in pages:
            for style in re.findall(r"<style[^>]*>(.*?)</style>",
                                    page.read_text(encoding="utf-8", errors="replace"), re.S):
                css_text += style
        _ac6_skip_link_focus(css_text, reasons)

    _astro_build_and_check(root, reasons, inspect=inspect)
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
