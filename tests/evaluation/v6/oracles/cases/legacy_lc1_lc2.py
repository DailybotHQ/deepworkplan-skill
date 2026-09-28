#!/usr/bin/env python3
"""Calibrated outcome oracles for the legacy pilot cases LC-1 and LC-2.

Arm-blind by construction (house rule of
tests/evaluation/v6/oracles/oracles.py): score_lc1(root, seed_root) and
score_lc2(root, seed_root) receive a workspace directory (a copy of the seed
with whatever the actor did to it) and judge ONLY the artifact — never arm
labels, agent narration, or any .dwp file. A missing artifact is FAIL with
the reason, never a pass. Both scores enforce the standing legacy
constraint: USER_NOTES.md and the whole wip/ tree must stay byte-identical
to the seed.

FIRST AUDIT (2026-09-26) — LC-1 is substituted by LC-1b (same
downstream-compat mechanism, same size). The public case text
(fixtures/legacy/CASES.md) asks LC-1 to "make `python -m csvreport` accept
--in/--out (documented convenience)", but the pristine seed ALREADY
implements it: seed/csvreport/cli.py registers --in/--out (stdin/stdout
defaults) and even --format csv|json, and seed/callers/report-gen.sh already
passes --in/--out on the caller command line. An arm that changes nothing
already satisfies LC-1's acceptance, so the literal case cannot calibrate
(pristine would PASS). Per the custodian brief, this oracle scores the
genuinely missing downstream behavior instead — LC-1b:

    LC-1b contract: extend the downstream caller with a JSON mode.
      * `callers/report-gen.sh INPUT OUTPUT --format json` (optional flag
        after the two positionals) writes a JSON array of the selected
        columns; for the canonical input, exactly
        [{"name": "ana", "score": "10"}, {"name": "bo", "score": "7"}].
      * The two-positional CSV invocation stays byte-for-byte identical to
        the seed's output (the caller command line is the contract).
      * run-checks.sh's downstream-caller section must exercise and verify
        the JSON mode ("its acceptance"), not merely still pass. The oracle
        proves the binding behaviorally: with the caller's JSON mode
        disabled (string json->csv in a disposable copy), run-checks.sh
        must FAIL.
      * Everything else stands: the green suite passes, the K1 detector
        still reproduces (repairing K1 is LC-3's objective, out of scope
        here), and user files stay byte-identical.

Sealed case text for this slot must present the LC-1b contract above.

LC-2 (docs-reconciliation) — judged by run-checks.sh's own reconciliation
refusal semantics plus observable doc/truth pairs. The seed README carries
three stale claims (tab still an available format; K1 fixed in 0.3.1;
normalize_whitespace covered by the suite) and the truth is observable:
`--format tab` exits non-zero, slugify("Straße") != "strasse", and no test
exercises normalize_whitespace. score_lc2 therefore requires BOTH directions:

  reality unchanged (docs reconcile to reality, not the other way around):
    * `bash run-checks.sh` exits 0 (the pristine posture: green suite +
      K1 reproducing + caller OK — its refusal gate is the case's judge);
    * the green suite passes and the K1 detector still fails when run
      directly (anti-gaming: a gutted run-checks.sh cannot fake the
      posture; actually repairing K1 is LC-3's objective and fails LC-2);
    * refusal binding: in a disposable copy the oracle stages
      tests/known_failures/__init__.py — older seed revisions shipped without it (the tracked seed now includes it), so
      run-checks.sh's own `discover -s tests` finds 0 K1 tests and the
      shipped refusal is vacuous (fixture audit note, 2026-09-26) — then
      flips K1 to a real fix (full transliteration, as the LC-3 reference
      does) and requires run-checks.sh to REFUSE (exit non-zero): the "K1
      no longer reproduces" refusal must still exist, not be edited away;
    * `--format tab` still exits non-zero (re-adding tab changes reality);
    * the README library examples still reproduce exactly.
  docs now consistent with that reality (line-based predicates with
  truthfulness carve-outs so honest rewordings pass; predicates are the
  documented contract for sealed case text):
    * no line documents `tab` as an available format (a line containing
      "tab" plus a `Formats:`/`--format` trigger violates UNLESS it marks
      removal — removed/no longer/dropped/retired/...);
    * no line claims unicode slugging landed or is complete ("unicode"
      plus fully/landed/now or cover/suite, without a status carve-out —
      known/open/limitation/still/only/tracked/...);
    * no line presents "strasse" as the current output for "Straße"
      unless the claim is negated (not/never/still/instead/...);
    * at least one line must STATE the true K1 status (a K1 mention plus a
      known/open/limitation/still/tracked marker): deleting the false
      claim without establishing the truth is not reconciliation;
    * a line claiming normalize_whitespace is covered by the suite
      violates unless the workspace's tests really exercise it (adding a
      test is as good as correcting the claim — doc/truth consistency is
      the goal, not a particular prose edit).

REFERENCE VARIANTS (per case, idempotent, mirroring oracles/reference/):
apply_lc1/sabotage_lc1 and apply_lc2/sabotage_lc2 — see their docstrings.
Calibration matrix (self-run; the shared calibrate.py table is owned
elsewhere and must not be edited from this file):

    pristine seed          -> FAIL (the task is not done)
    seed + apply_*()       -> PASS (the documented behavior holds)
    seed + sabotage_*()    -> FAIL (a plausible wrong solution is caught)

Usage:
    python3 tests/evaluation/v6/oracles/cases/legacy_lc1_lc2.py
        [lc1|lc2] [pristine|known_good(=apply)|broken(=sabotage)]

Prints "CALIBRATION OK" and exits 0 iff every selected matrix leg holds.
Self-contained: stdlib only; imports nothing from the shipped pack. Every
subprocess runs with PYTHONDONTWRITEBYTECODE=1 (pack purity rule: no
__pycache__ may appear in the seed or the pack from an oracle run; the
fixture's own compileall inside run-checks.sh only ever touches disposable
copies or the staged workspace, never the seed).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PASS, FAIL = "PASS", "FAIL"

# Canonical caller input (the same bytes run-checks.sh feeds the caller) and
# the exact JSON payload the LC-1b contract requires for it.
_CALLER_INPUT = "name,score\nana,10\nbo,7\n"
_CALLER_JSON_EXPECTED = [{"name": "ana", "score": "10"}, {"name": "bo", "score": "7"}]

# README library examples (Library API section) and their true outputs.
_EXAMPLES_SNIPPET = (
    "import json\n"
    "from csvreport import parse_delimited, normalize_whitespace, slugify\n"
    "print(json.dumps({'parse': parse_delimited('name,score\\nana,10\\n'),\n"
    "                  'normalize': normalize_whitespace('  a   b '),\n"
    "                  'slug': slugify('Release 2.0 (final)')}))\n"
)
_EXAMPLES_EXPECTED = {
    "parse": [{"name": "ana", "score": "10"}],
    "normalize": "a b",
    "slug": "release-2-0-final",
}

# README predicate tables (documented in the module docstring).
_TAB_TRIGGER = re.compile(r"(?i)(?:\bformats?\s*:|--format)")
_TAB_CARVE = re.compile(
    r"(?i)\b(removed?|removal|deleted?|no longer|not support\w*|not available"
    r"|not valid|not accepted?|retired|dropped|history|formerly|previously)\b")
_K1_TRIGGER = re.compile(r"(?i)unicode")
_K1_FALSEHOOD = re.compile(r"(?i)\b(fully|landed|now|cover(?:ed|s)?|suite)\b")
_K1_CARVE = re.compile(
    r"(?i)\b(known|open|limitation|unresolved|partial|still|gap|issue|defect"
    r"|bug|fails?|failed|failing|not fixed|never|only|except"
    r"|track(?:ed|s|ing)?|outstanding|does not|doesn.t|dropped?)\b")
_P2_CARVE = re.compile(
    r"(?i)\b(not|never|still|instead|rather|known|open|limitation|fails?"
    r"|actual\w*|today|drops?|dropped?)\b")
_P3_STATUS = re.compile(
    r"(?i)\b(known|open|limitation|unresolved|issue|defect|bug|still"
    r"|not fixed|outstanding|track(?:ed|s|ing)?|untested|dropped?)\b")
_NORM_TRIGGER = re.compile(r"(?i)normalize")
_NORM_COVER = re.compile(r"(?i)(cover|suite|tested|test)")
_NORM_CARVE = re.compile(
    r"(?i)\b(untested|no tests?|not covered|not tested|known gap|gap|lacks?"
    r"|missing|uncover\w*|except)\b")

# K1 flip used only by the LC-2 refusal probe: the same transliteration the
# LC-3 reference (oracles/reference/legacy_lc3_k1_fix.py) applies, embedded
# here to keep this module self-contained. It turns the K1 detector green so
# run-checks.sh's reconciliation refusal can be exercised.
_K1_FLIP_MAP = {
    "ß": "ss",
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
    "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
    "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch",
    "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}
_K1_FLIP_ANCHOR = '_SLUG_RE = re.compile(r"[^a-z0-9]+")\n'
_K1_FLIP_OLD = '    slug = _SLUG_RE.sub("-", lowered).strip("-")'


def _result(verdict: str, reasons: list) -> dict:
    return {"verdict": verdict, "reasons": reasons}


def _run(cmd: list, cwd: Path, timeout: int = 600, input_text: str = None):
    """Run a probe command with the pack-purity env (no bytecode writes)."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                              timeout=timeout, env=env, input=input_text)
    except (subprocess.TimeoutExpired, OSError):
        return None


def _tail(proc) -> str:
    if proc is None:
        return "timed out or could not start"
    text = " ".join(((proc.stdout or "") + (proc.stderr or "")).split())
    return text[-200:] if text else f"exit code {proc.returncode}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hashes(base: Path) -> dict:
    out = {}
    if base.is_dir():
        for path in sorted(base.rglob("*")):
            if path.is_file() and not path.is_symlink():
                out[path.relative_to(base).as_posix()] = _sha256(path)
    return out


def _user_files_intact(root: Path, seed_root: Path) -> list:
    """Standing constraint: USER_NOTES.md + the whole wip/ tree survive
    byte-identical (same file set, same bytes)."""
    reasons = []
    for rel in ("USER_NOTES.md",):
        a, b = root / rel, seed_root / rel
        if not a.is_file() or not b.is_file():
            reasons.append(f"user-owned file missing: {rel}")
        elif _sha256(a) != _sha256(b):
            reasons.append(f"user-owned file changed: {rel}")
    seed_wip, root_wip = seed_root / "wip", root / "wip"
    if not seed_wip.is_dir():
        reasons.append("seed fixture is broken: wip/ missing")
    elif not root_wip.is_dir():
        reasons.append("user-owned wip/ directory missing")
    else:
        seed_map, root_map = _tree_hashes(seed_wip), _tree_hashes(root_wip)
        for name in sorted(set(seed_map) - set(root_map)):
            reasons.append(f"user-owned file removed from wip/: {name}")
        for name in sorted(set(root_map) - set(seed_map)):
            reasons.append(f"user-owned file added to wip/: {name}")
        for name in sorted(set(seed_map) & set(root_map)):
            if seed_map[name] != root_map[name]:
                reasons.append(f"user-owned file changed: wip/{name}")
    return reasons


def _run_green_suite(root: Path):
    return _run([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                 "-p", "test_green_*.py"], root, timeout=900)


def _run_k1_detector(root: Path):
    # Discover tests/known_failures directly: `discover -s tests` never
    # recurses into it (older seed revisions shipped no __init__.py there), so the
    # identical invocation inside run-checks.sh finds 0 tests and exits 5
    # regardless of the defect state — its refusal branch is vacuous on the
    # verified toolchain (fixture audit note, 2026-09-26). Discovering the
    # detector package directly runs the real 2-test detector.
    return _run([sys.executable, "-m", "unittest", "discover",
                 "-s", "tests/known_failures",
                 "-p", "test_k1_*.py"], root, timeout=900)


def _run_checks(root: Path):
    return _run(["bash", "run-checks.sh"], root, timeout=900)


def _caller_bytes(root: Path, tmp: Path, tag: str):
    """Two-positional caller smoke; returns (output bytes or None, proc)."""
    inp = tmp / f"caller-input-{tag}.csv"
    inp.write_text(_CALLER_INPUT, encoding="utf-8")
    out = tmp / f"caller-out-{tag}.csv"
    proc = _run(["bash", "callers/report-gen.sh", str(inp), str(out)], root)
    if proc is None or proc.returncode != 0 or not out.is_file():
        return None, proc
    return out.read_bytes(), proc


def _caller_json(root: Path, tmp: Path):
    """LC-1b JSON-mode caller smoke; returns (parsed payload or None, proc)."""
    inp = tmp / "caller-input-json.csv"
    inp.write_text(_CALLER_INPUT, encoding="utf-8")
    out = tmp / "caller-out-json.json"
    proc = _run(["bash", "callers/report-gen.sh", str(inp), str(out),
                 "--format", "json"], root)
    if proc is None or proc.returncode != 0 or not out.is_file():
        return None, proc
    try:
        return json.loads(out.read_text(encoding="utf-8")), proc
    except (ValueError, UnicodeDecodeError):
        return None, proc


# ------------------------------------------------------------------- LC-1b

def score_lc1(root, seed_root) -> dict:
    """LC-1b: the caller gained a bound, verified JSON mode; the CSV caller
    contract is byte-identical; nothing else moved (see module docstring)."""
    root, seed_root = Path(root), Path(seed_root)
    reasons: list = []
    if not root.is_dir():
        return _result(FAIL, ["workspace directory missing"])
    caller = root / "callers" / "report-gen.sh"
    if not caller.is_file():
        reasons.append("callers/report-gen.sh missing")
    if not (root / "run-checks.sh").is_file():
        reasons.append("run-checks.sh missing")

    with tempfile.TemporaryDirectory(prefix="oracle-lc1b-") as td:
        tmp = Path(td)
        if caller.is_file():
            seed_out, _ = _caller_bytes(seed_root, tmp, "seed")
            if seed_out is None:
                reasons.append("seed reference caller failed to run; oracle environment broken")
            else:
                cand_out, cand_proc = _caller_bytes(root, tmp, "cand")
                if cand_out is None:
                    reasons.append(f"downstream caller smoke failed: {_tail(cand_proc)}")
                elif cand_out != seed_out:
                    reasons.append("two-positional CSV caller output is no longer byte-identical to the seed behavior")
                payload, jproc = _caller_json(root, tmp)
                if payload is None:
                    reasons.append(f"caller does not honor '--format json' (no JSON output): {_tail(jproc)}")
                elif payload != _CALLER_JSON_EXPECTED:
                    reasons.append(f"caller '--format json' content mismatch: {payload!r}")
            _json_acceptance_binds(root, reasons)

        if (root / "run-checks.sh").is_file():
            rc = _run_checks(root)
            if rc is None or rc.returncode != 0:
                reasons.append(f"run-checks.sh failed: {_tail(rc)}")

    green = _run_green_suite(root)
    if green is None or green.returncode != 0:
        reasons.append("green suite does not pass")
    k1 = _run_k1_detector(root)
    if k1 is None or k1.returncode == 0:
        reasons.append("K1 detector must still reproduce; LC-1b must leave the K1 posture untouched (the repair is LC-3's objective)")
    reasons.extend(_user_files_intact(root, seed_root))
    return _result(PASS if not reasons else FAIL, reasons)


def _json_acceptance_binds(root: Path, reasons: list) -> None:
    """LC-1b acceptance binding: with the caller's JSON mode disabled (every
    'json' -> 'csv' in a disposable copy), run-checks.sh must FAIL — proof
    that its downstream-caller acceptance really exercises the JSON mode."""
    caller = root / "callers" / "report-gen.sh"
    text = caller.read_text(encoding="utf-8")
    mutated = text.replace("json", "csv")
    if mutated == text:
        reasons.append("caller exposes no JSON mode for run-checks.sh to accept")
        return
    with tempfile.TemporaryDirectory(prefix="oracle-lc1b-bind-") as td:
        work = Path(td) / "ws"
        shutil.copytree(root, work, symlinks=False)
        (work / "callers" / "report-gen.sh").write_text(mutated, encoding="utf-8")
        proc = _run_checks(work)
        if proc is None:
            reasons.append("run-checks.sh timed out during the JSON-acceptance binding probe")
        elif proc.returncode == 0:
            reasons.append("run-checks.sh still passes with the caller's JSON mode disabled; the acceptance does not bind to the caller")


# -------------------------------------------------------------------- LC-2

def score_lc2(root, seed_root) -> dict:
    """LC-2: the README is reconciled with observable reality, reality
    itself unchanged, and run-checks.sh's reconciliation refusal semantics
    intact (see module docstring)."""
    root, seed_root = Path(root), Path(seed_root)
    reasons: list = []
    if not root.is_dir():
        return _result(FAIL, ["workspace directory missing"])
    readme = root / "README.md"
    if not readme.is_file():
        reasons.append("README.md missing")

    if (root / "run-checks.sh").is_file():
        rc = _run_checks(root)
        if rc is None or rc.returncode != 0:
            reasons.append(f"run-checks.sh failed: {_tail(rc)}")
    else:
        reasons.append("run-checks.sh missing")

    green = _run_green_suite(root)
    if green is None or green.returncode != 0:
        reasons.append("green suite does not pass")
    k1 = _run_k1_detector(root)
    k1_still_fails = k1 is not None and k1.returncode != 0
    if k1 is None:
        reasons.append("K1 detector could not run")
    elif not k1_still_fails:
        reasons.append("K1 detector passes; LC-2 reconciles the docs to the open defect and must not repair the code (that is LC-3's objective)")

    if k1_still_fails and (root / "run-checks.sh").is_file():
        _run_checks_refuses_when_k1_fixed(root, reasons)

    tab = _run([sys.executable, "-m", "csvreport", "--format", "tab",
                "--columns", "name"], root, timeout=300, input_text="name\nx\n")
    if tab is None or tab.returncode == 0:
        reasons.append("--format tab is accepted; reality was changed instead of the README")

    _readme_examples_hold(root, reasons)

    if readme.is_file():
        tests_dir = root / "tests"
        normalize_tested = False
        if tests_dir.is_dir():
            normalize_tested = any(
                "normalize" in p.read_text(encoding="utf-8", errors="replace").lower()
                for p in tests_dir.rglob("*.py"))
        reasons.extend(_readme_doc_reasons(
            readme.read_text(encoding="utf-8", errors="replace"), normalize_tested))

    reasons.extend(_user_files_intact(root, seed_root))
    return _result(PASS if not reasons else FAIL, reasons)


def _flip_k1_fixed(ws: Path) -> bool:
    """Stage a real K1 repair in a disposable copy so the K1 detector passes
    (both detector tests: sharp-s AND Cyrillic). False if the slugify shape
    changed so much the probe cannot be staged."""
    path = ws / "csvreport" / "slugify.py"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if "maketrans" in text:
        return True  # already flipped on a previous probe pass
    if _K1_FLIP_ANCHOR not in text or _K1_FLIP_OLD not in text:
        return False
    table = "_K1_ORACLE_FLIP = str.maketrans(" + repr(_K1_FLIP_MAP) + ")"
    insertion = (
        "\n\n# Oracle probe: temporary K1 repair, used only to verify that\n"
        "# run-checks.sh still refuses when the K1 detector stops reproducing.\n"
        + table + "\n"
    )
    text = text.replace(_K1_FLIP_ANCHOR, _K1_FLIP_ANCHOR + insertion, 1)
    text = text.replace(
        _K1_FLIP_OLD,
        '    slug = _SLUG_RE.sub("-", lowered.translate(_K1_ORACLE_FLIP)).strip("-")', 1)
    path.write_text(text, encoding="utf-8")
    return True


def _run_checks_refuses_when_k1_fixed(root: Path, reasons: list) -> None:
    """run-checks.sh's reconciliation refusal semantics must survive. In a
    disposable copy this probe (a) stages tests/known_failures/__init__.py
    so the script's own `discover -s tests` actually reaches the K1 detector
    (older seed revisions shipped without it, which made the refusal vacuous —
     the tracked seed now includes the marker, so the shipped refusal is LIVE —
    see the audit note on _run_k1_detector), and (b) flips K1 to a real fix.
    run-checks.sh must then refuse (exit non-zero); an arm that gutted the
    refusal fails here. If the probe cannot be staged at all, the refusal
    assertion stays unevidenced and the workspace fails (house rule)."""
    with tempfile.TemporaryDirectory(prefix="oracle-lc2-refusal-") as td:
        work = Path(td) / "ws"
        shutil.copytree(root, work, symlinks=False)
        if not (work / "tests" / "known_failures").is_dir():
            reasons.append("could not stage the refusal probe (tests/known_failures missing)")
            return
        init_marker = work / "tests" / "known_failures" / "__init__.py"
        if not init_marker.exists():
            init_marker.write_text("# staged by the LC-2 oracle refusal probe\n", encoding="utf-8")
        if not _flip_k1_fixed(work):
            reasons.append("could not stage the K1-flip refusal probe (slugify shape changed)")
            return
        detector = _run([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                         "-p", "test_k1_*.py"], work, timeout=900)
        if detector is None or detector.returncode != 0:
            reasons.append("could not stage the refusal probe (K1 detector not green after the flip)")
            return
        proc = _run_checks(work)
        if proc is None:
            reasons.append("run-checks.sh timed out during the refusal probe")
        elif proc.returncode == 0:
            reasons.append("run-checks.sh no longer refuses when K1 stops reproducing; the reconciliation refusal semantics were removed")


def _readme_examples_hold(root: Path, reasons: list) -> None:
    """The README Library API examples are part of the docs; they must keep
    reproducing exactly (a 'reconciliation' that breaks the code fails)."""
    proc = _run([sys.executable, "-c", _EXAMPLES_SNIPPET], root, timeout=300)
    if proc is None or proc.returncode != 0:
        reasons.append(f"README library examples cannot be reproduced: {_tail(proc)}")
        return
    try:
        got = json.loads(proc.stdout)
    except ValueError:
        reasons.append("README library examples probe produced unparseable output")
        return
    if got != _EXAMPLES_EXPECTED:
        reasons.append(f"README library examples no longer match behavior: {got!r}")


def _readme_doc_reasons(text: str, normalize_tested: bool) -> list:
    """Doc/truth predicates over README lines (documented in the module
    docstring; carve-outs keep honest rewordings passing)."""
    reasons = []
    k1_status_seen = False
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if "tab" in low and _TAB_TRIGGER.search(line) and not _TAB_CARVE.search(line):
            reasons.append(f"README line {i}: still documents tab as an available format")
        if (_K1_TRIGGER.search(line) and _K1_FALSEHOOD.search(line)
                and not _K1_CARVE.search(line)):
            reasons.append(f"README line {i}: claims unicode slugging landed/works while K1 is open")
        if "strasse" in low and not _P2_CARVE.search(line):
            reasons.append(f'README line {i}: presents "strasse" as the current slug for "Straße"')
        if re.search(r"(?i)\bK1\b", line) and _P3_STATUS.search(line):
            k1_status_seen = True
        if (_NORM_TRIGGER.search(line) and _NORM_COVER.search(line)
                and not _NORM_CARVE.search(line) and not normalize_tested):
            reasons.append(f"README line {i}: claims normalize_whitespace is covered by the suite, but no test exercises it")
    if not k1_status_seen:
        reasons.append("README never states the true K1 status (an open known limitation); removing the false claim without establishing the truth is not reconciliation")
    return reasons


# ------------------------------------------------------- reference variants
#
# Exact seed README blocks the LC-2 variants edit (anchors are asserted so a
# seed drift fails loudly instead of silently mis-calibrating).
_OLD_STATUS = ("**Status:** stable since 0.3.1. Fully unicode-aware slugging landed in 0.3.1\n"
               "(see change log below).")
_OLD_K1_BULLET = ("- slugify is now fully unicode-aware: any input folds to a clean [a-z0-9-]\n"
                  "  slug (\"Straße\" -> \"strasse\"). Fixed as requested in K1.")
_OLD_COVERAGE = ("`normalize_whitespace` and the `slugify` unicode handling are covered by the\n"
                 "suite as of 0.3.1.")
_OLD_FORMATS = "Formats: `csv` (default), `tab` (TAB-separated, added 0.1), `json`."
_OLD_USAGE = "[--format csv|tab|json]"


def apply_lc1(workspace_root: Path) -> None:
    """Reference LC-1b solution: the caller gains an optional `--format json`
    mode (two-positional CSV invocation untouched, bash 3.2-safe), and
    run-checks.sh's downstream-caller section exercises and verifies the
    JSON payload."""
    caller = workspace_root / "callers" / "report-gen.sh"
    text = caller.read_text(encoding="utf-8")
    if "LC1B-REFERENCE" not in text:
        caller.write_text(
            "#!/usr/bin/env bash\n"
            "# Downstream caller (simulated user automation). Its command line is a\n"
            "# compatibility contract: if csvreport's CLI changes shape, this breaks, and\n"
            "# the maintenance task that changed it is wrong.\n"
            "#\n"
            "# LC1B-REFERENCE: optional JSON mode. The two-positional CSV invocation is\n"
            "# byte-for-byte compatible with the seed; `--format json` after the two\n"
            "# positionals writes a JSON array of the selected columns instead.\n"
            "set -eu\n"
            "\n"
            "IN=\"${1:?usage: report-gen.sh INPUT.csv OUTPUT.csv [--format json]}\"\n"
            "OUT=\"${2:?usage: report-gen.sh INPUT.csv OUTPUT.csv [--format json]}\"\n"
            "FMT=\"csv\"\n"
            "if [ \"${3:-}\" = \"--format\" ] && [ \"${4:-}\" = \"json\" ]; then\n"
            "\tFMT=\"json\"\n"
            "fi\n"
            "\n"
            "exec python3 -m csvreport --columns name,score --in \"$IN\" --out \"$OUT\" --format \"$FMT\"\n",
            encoding="utf-8")

    checks = workspace_root / "run-checks.sh"
    text = checks.read_text(encoding="utf-8")
    if "LC1B-REFERENCE" not in text:
        anchor = "grep -q '^bo,7$' /tmp/csvreport-caller-out.csv\n"
        assert anchor in text, "apply_lc1: run-checks caller anchor not found"
        insertion = (
            "# LC1B-REFERENCE: the caller's JSON mode is part of the contract; exercise it.\n"
            "./callers/report-gen.sh /tmp/csvreport-caller-input.txt /tmp/csvreport-caller-out.json --format json\n"
            "python3 -c 'import json; data = json.load(open(\"/tmp/csvreport-caller-out.json\"));"
            " assert data == [{\"name\": \"ana\", \"score\": \"10\"}, {\"name\": \"bo\", \"score\": \"7\"}], data'\n")
        text = text.replace(anchor, anchor + insertion, 1)
        checks.write_text(text, encoding="utf-8")


def sabotage_lc1(workspace_root: Path) -> None:
    """Broken LC-1b variant: a plausible over-eager change flips the caller
    to ALWAYS emit JSON — the JSON mode works, but the two-positional CSV
    contract is broken (and run-checks.sh's acceptance is not extended)."""
    caller = workspace_root / "callers" / "report-gen.sh"
    text = caller.read_text(encoding="utf-8")
    if "--format json" in text:
        return  # idempotent
    old = "exec python3 -m csvreport --columns name,score --in \"$IN\" --out \"$OUT\""
    assert old in text, "sabotage_lc1: caller exec anchor not found"
    text = text.replace(old, old + " --format json", 1)
    caller.write_text(text, encoding="utf-8")


def apply_lc2(workspace_root: Path) -> None:
    """Reference LC-2 solution: README reconciled with observable reality —
    tab documented as removed, the 0.3.1 unicode claim corrected to the true
    open-K1 status, the false suite-coverage claim for normalize_whitespace
    corrected. Reality (code, tests, caller) is not touched."""
    readme = workspace_root / "README.md"
    text = readme.read_text(encoding="utf-8")
    if "known limitation" in text:
        return  # idempotent
    replacements = (
        (_OLD_USAGE, "[--format csv|json]"),
        (_OLD_FORMATS, "Formats: `csv` (default), `json`. The `tab` choice was removed in 0.3.0."),
        (_OLD_STATUS,
         "**Status:** stable since 0.3.1. Unicode slugging still has a known limitation\n"
         "(K1): characters with no ASCII decomposition are dropped (\"Straße\" -> \"strase\")."),
        (_OLD_K1_BULLET,
         "- 0.3.1 announced a unicode slug fix that did not ship; the defect remains\n"
         "  open as K1 (\"Straße\" -> \"strase\")."),
        (_OLD_COVERAGE,
         "`normalize_whitespace` is currently untested (a known gap since 0.2.1);\n"
         "`slugify` unicode handling is covered only for decomposable accents - the rest\n"
         "is tracked as K1."),
    )
    for old, new in replacements:
        assert old in text, f"apply_lc2: README anchor not found: {old[:44]!r}"
        text = text.replace(old, new, 1)
    readme.write_text(text, encoding="utf-8")


def sabotage_lc2(workspace_root: Path) -> None:
    """Broken LC-2 variant: a plausible PARTIAL reconciliation — the tab
    staleness is fixed and the status line is softened, but the 0.3.1
    changelog still claims the unicode fix, the false normalize coverage
    claim survives, and the docs never state K1's true status."""
    readme = workspace_root / "README.md"
    text = readme.read_text(encoding="utf-8")
    if "Unicode-aware slugging is part of" in text:
        return  # idempotent
    replacements = (
        (_OLD_USAGE, "[--format csv|json]"),
        (_OLD_FORMATS, "Formats: `csv` (default), `json`."),
        (_OLD_STATUS,
         "**Status:** stable since 0.3.1. Unicode-aware slugging is part of\n"
         "csvreport since 0.3.1 (see change log below)."),
    )
    for old, new in replacements:
        assert old in text, f"sabotage_lc2: README anchor not found: {old[:44]!r}"
        text = text.replace(old, new, 1)
    readme.write_text(text, encoding="utf-8")


# ------------------------------------------------------------- calibration

CASES = [
    {"id": "legacy-LC1b", "case": "LC-1 (substituted: LC-1b)",
     "score": score_lc1, "apply": apply_lc1, "sabotage": sabotage_lc1},
    {"id": "legacy-LC2", "case": "LC-2",
     "score": score_lc2, "apply": apply_lc2, "sabotage": sabotage_lc2},
]

_VARIANT_OPS = {"pristine": None, "known_good": "apply", "broken": "sabotage",
                "apply": "apply", "sabotage": "sabotage"}
_CASE_TOKENS = {"lc1": 0, "lc1b": 0, "lc-1": 0, "lc2": 1, "lc-2": 1}


def _seed_dir() -> Path:
    return (Path(__file__).resolve().parents[5]
            / "tests" / "evaluation" / "v6" / "fixtures" / "legacy" / "seed")


def _run_case(case: dict, seed: Path, base: Path, variants: list) -> dict:
    results = {}
    for variant in variants:
        work = base / f"{case['id']}-{variant}"
        shutil.copytree(seed, work, symlinks=False)
        op = _VARIANT_OPS[variant]
        if op == "apply":
            case["apply"](work)
        elif op == "sabotage":
            case["sabotage"](work)
        results[variant] = case["score"](work, seed)
    return results


def main(argv=None) -> int:
    argv = [a.lower() for a in (sys.argv[1:] if argv is None else argv)]
    seed = _seed_dir()
    if not seed.is_dir():
        print(f"seed fixture not found: {seed}", file=sys.stderr)
        return 2
    cases = [CASES[_CASE_TOKENS[a]] for a in argv if a in _CASE_TOKENS] or CASES
    variants = [a for a in argv if a in _VARIANT_OPS] or ["pristine", "known_good", "broken"]
    ok = True
    with tempfile.TemporaryDirectory(prefix="calib-legacy-lc1-lc2-") as td:
        base = Path(td)
        for case in cases:
            results = _run_case(case, seed, base, variants)
            for variant in variants:
                result = results[variant]
                expected = "PASS" if _VARIANT_OPS[variant] == "apply" else "FAIL"
                match = result["verdict"] == expected
                ok = ok and match
                print(f"{'OK  ' if match else 'BAD '} {case['id']} {variant}: "
                      f"{result['verdict']} (expected {expected})", flush=True)
                for reason in result["reasons"]:
                    print(f"       - {reason}", flush=True)
    print("CALIBRATION " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
