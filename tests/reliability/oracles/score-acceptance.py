#!/usr/bin/env python3
"""Score a v5 reliability acceptance run against the pre-registered oracles.

Reads the run's ARTIFACTS, not the agent's narration. A claim the files do not
support scores FAIL; a missing field scores UNVERIFIED, never PASS.

Usage:
    python3 tests/reliability/oracles/score-acceptance.py <run-dir> [--json out.json]

Run directory shape (see ../PROTOCOL.md):
    META.json                 run id, flow, pack revision, host, entry path
    ACCEPTANCE_REPORT.json    agent-written: commands, exit codes, files read
    repo/                     the disposable workspace as the run left it

Exit code: 0 when every required oracle PASSes, 1 otherwise. UNVERIFIED is a
failure — an unproven oracle is never a pass.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

PASS, FAIL, UNVER = "PASS", "FAIL", "UNVERIFIED"

# Oracles A7 applies only to a run that was interrupted and resumed.
RESUME_ONLY = {"A7"}


def read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def find_plan(repo):
    plans = sorted((repo / ".dwp" / "plans").glob("PLAN_*")) if repo.is_dir() else []
    return plans[0] if len(plans) == 1 else (plans[0] if plans else None)


def a1_flow_entry(ctx):
    """The agent entered create: the folder has the shape only create writes."""
    plan = ctx["plan"]
    if plan is None:
        return FAIL, "no plan folder under repo/.dwp/plans/"
    required = ["README.md", "manifest.json", "PROGRESS.md", "state.json"]
    missing = [f for f in required if not (plan / f).is_file()]
    if missing:
        return FAIL, f"plan folder missing created-shape files: {missing}"
    readme = (plan / "README.md").read_text()
    if "Plan Status:" not in readme:
        return FAIL, "README.md has no 'Plan Status:' line"
    if not re.search(r"^- \[[ x]\] Task \d+", readme, re.M):
        return FAIL, "README.md has no task index"
    if not (plan / "analysis_results").is_dir():
        return FAIL, "no analysis_results/ directory"
    report = ctx["report"]
    if report is None:
        return UNVER, "no ACCEPTANCE_REPORT.json to corroborate the reads"
    reads = report.get("pack_files_read")
    if not isinstance(reads, list) or not reads:
        return UNVER, "report does not list the pack files read"
    pack_reads = [r for r in reads if "skills/deepworkplan" in str(r.get("path", r))]
    if not pack_reads:
        return FAIL, "report lists no read of the pack under evaluation"
    return PASS, f"created shape present; {len(pack_reads)} pack file(s) read"


def a2_conformance(ctx):
    """The shipped read-only checker accepts the terminal plan."""
    plan, pack = ctx["plan"], ctx["pack"]
    if plan is None:
        return FAIL, "no plan to check"
    checker = pack / "verify" / "conformance.sh"
    if not checker.is_file():
        return UNVER, "conformance.sh not found in the pack"
    # conformance.sh --plan PLAN_NAME [TARGET_DIR]
    proc = subprocess.run(["bash", str(checker), "--plan", plan.name, str(ctx["repo"])],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-6:]
        return FAIL, f"conformance exit {proc.returncode}: " + " | ".join(tail)
    return PASS, "conformance checker exit 0"


LEDGER_PROBE = r"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(sys.argv[1])))
from src.ledger import Ledger
l = Ledger()
l.add("cash", 100)
try:
    l.transfer("cash", "savings", 500)
except ValueError:
    ok = (l.balance("cash") == 100 and l.balance("savings") == 0)
    print("RAISED_AND_CLEAN" if ok else "RAISED_BUT_RECORDED")
else:
    print("NOT_RAISED")
"""


def _probe(repo):
    proc = subprocess.run([sys.executable, "-c", LEDGER_PROBE, str(repo)],
                          capture_output=True, text=True, cwd=str(repo))
    return proc.stdout.strip(), proc


def a3_defect_fixed(ctx):
    """Behavioral: an overdrawing transfer raises and records nothing."""
    repo = ctx["repo"]
    if not (repo / "src" / "ledger.py").is_file():
        return FAIL, "src/ledger.py missing from the workspace"
    out, proc = _probe(repo)
    if out == "RAISED_AND_CLEAN":
        return PASS, "overdraw raises ValueError and records nothing"
    if out == "RAISED_BUT_RECORDED":
        return FAIL, "raised, but a partial entry was recorded"
    if out == "NOT_RAISED":
        return FAIL, "overdrawing transfer still succeeds — the defect is not fixed"
    return FAIL, f"probe failed: {(proc.stderr or proc.stdout).strip()[:200]}"


def a4_test_encodes_behavior(ctx):
    """Revert the fix: the run's own suite must fail. Restore it: must pass."""
    repo = ctx["repo"]
    src = repo / "src" / "ledger.py"
    if not src.is_file():
        return FAIL, "src/ledger.py missing"
    suite = ["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."]
    clean = subprocess.run(suite, capture_output=True, text=True, cwd=str(repo))
    if clean.returncode != 0:
        return FAIL, "the run's own suite does not pass on its final tree"
    original = src.read_text()
    # Revert to the seeded-defect implementation of transfer, keeping the rest.
    broken = re.sub(
        r"(    def transfer\(self, source, target, cents\):\n)(?:.*?)(?=\n    def |\Z)",
        r"\1        self.add(source, -cents)\n        self.add(target, cents)\n",
        original, count=1, flags=re.S)
    if broken == original:
        return UNVER, "could not locate transfer() to revert; coverage unproven"
    try:
        src.write_text(broken)
        reverted = subprocess.run(suite, capture_output=True, text=True, cwd=str(repo))
    finally:
        src.write_text(original)
    if reverted.returncode == 0:
        return FAIL, "suite still passes with the fix reverted — no test encodes the behavior"
    restored = subprocess.run(suite, capture_output=True, text=True, cwd=str(repo))
    if restored.returncode != 0:
        return FAIL, "suite did not pass after restoring the fix (unstable workspace)"
    return PASS, "suite fails with the fix reverted and passes with it restored"


def a5_terminal_state(ctx):
    plan = ctx["plan"]
    if plan is None:
        return FAIL, "no plan"
    state = read_json(plan / "state.json")
    if state is None:
        return UNVER, "state.json missing or unreadable"
    if state.get("status") != "completed":
        return FAIL, f"state.status is {state.get('status')!r}, not 'completed'"
    if state.get("completed_count") != state.get("task_count"):
        return FAIL, (f"completed_count {state.get('completed_count')} != "
                      f"task_count {state.get('task_count')}")
    tasks = state.get("tasks") or []
    if not tasks:
        return FAIL, "state records no tasks"
    for t in tasks:
        if t.get("status") != "completed":
            return FAIL, f"task {t.get('id')} is {t.get('status')!r}"
        gates = t.get("gates") or []
        if not gates:
            return FAIL, f"task {t.get('id')} carries no gate record"
        if not any(g.get("passes") and g.get("exit_code") == 0 for g in gates):
            return FAIL, f"task {t.get('id')} has no passing gate with exit_code 0"
    readme = (plan / "README.md").read_text()
    if re.search(r"^- \[ \] Task \d+", readme, re.M):
        return FAIL, "README still carries an unchecked task"
    return PASS, f"{len(tasks)} task(s) completed with passing gate records"


def a6_completion_transaction(ctx):
    plan = ctx["plan"]
    if plan is None:
        return FAIL, "no plan"
    receipts = list(plan.rglob("FINALIZATION.json"))
    markers = list(plan.rglob(".finalizing.json"))
    if markers:
        return FAIL, f"a .finalizing.json marker remains: {[str(m.name) for m in markers]}"
    if not receipts:
        return FAIL, "no FINALIZATION.json receipt — completion was not a transaction"
    return PASS, "receipt present, no failure marker left behind"


def a7_no_repeated_work(ctx):
    repo, plan = ctx["repo"], ctx["plan"]
    if plan is None:
        return FAIL, "no plan"
    log = subprocess.run(["git", "log", "--format=%H%x09%s"],
                         capture_output=True, text=True, cwd=str(repo))
    if log.returncode != 0:
        return UNVER, "no git history to inspect"
    lines = [l for l in log.stdout.strip().split("\n") if l.strip()]
    subjects = [l.split("\t", 1)[1] for l in lines if "\t" in l]
    seen, dupes = set(), []
    for s in subjects:
        key = s.strip().lower()
        if key in seen:
            dupes.append(s)
        seen.add(key)
    if dupes:
        return FAIL, f"repeated commit subject(s): {dupes[:3]}"
    state = read_json(plan / "state.json") or {}
    commits = [t.get("commit") for t in (state.get("tasks") or []) if t.get("commit")]
    if len(commits) != len(set(commits)):
        return FAIL, "two tasks recorded the same commit"
    return PASS, f"{len(subjects)} commit(s), none repeated"


def a8_unattended(ctx):
    report = ctx["report"]
    if report is None:
        return UNVER, "no report to read"
    if "questions_asked" not in report:
        return UNVER, "report does not record questions_asked"
    q = report["questions_asked"]
    if q:
        return FAIL, f"the run asked {len(q)} question(s): {q[:2]}"
    return PASS, "no question asked"


ORACLES = [
    ("A1", "flow entry", a1_flow_entry),
    ("A2", "terminal plan conformance", a2_conformance),
    ("A3", "defect actually fixed", a3_defect_fixed),
    ("A4", "a test encodes the fixed behavior", a4_test_encodes_behavior),
    ("A5", "terminal state coherent", a5_terminal_state),
    ("A6", "completion was a transaction", a6_completion_transaction),
    ("A7", "resume repeated nothing", a7_no_repeated_work),
    ("A8", "run was unattended", a8_unattended),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--pack", help="pack root (default: derived from this file)")
    ap.add_argument("--json", help="write the scored result here")
    a = ap.parse_args()

    run = pathlib.Path(a.run_dir).resolve()
    pack = pathlib.Path(a.pack).resolve() if a.pack else \
        pathlib.Path(__file__).resolve().parents[3] / "skills" / "deepworkplan"
    meta = read_json(run / "META.json") or {}
    ctx = {
        "run": run, "pack": pack, "repo": run / "repo",
        "plan": find_plan(run / "repo"),
        "report": read_json(run / "ACCEPTANCE_REPORT.json"),
        "meta": meta,
    }
    interrupted = bool(meta.get("interrupted"))

    results, failed = [], 0
    for oid, name, fn in ORACLES:
        if oid in RESUME_ONLY and not interrupted:
            results.append({"id": oid, "name": name, "verdict": "N/A",
                            "detail": "run was not interrupted"})
            continue
        try:
            verdict, detail = fn(ctx)
        except Exception as exc:  # an oracle that crashes proves nothing
            verdict, detail = UNVER, f"oracle error: {exc}"
        results.append({"id": oid, "name": name, "verdict": verdict, "detail": detail})
        if verdict != PASS:
            failed += 1

    out = {
        "run": str(run),
        "run_id": meta.get("run_id"),
        "flow": meta.get("flow"),
        "pack_revision": meta.get("pack_revision"),
        "interrupted": interrupted,
        "results": results,
        "verdict": "PASS" if failed == 0 else "FAIL",
    }
    width = max(len(r["name"]) for r in results)
    print(f"# acceptance run {meta.get('run_id', run.name)} "
          f"({meta.get('flow', 'unknown flow')}) @ {meta.get('pack_revision', '?')}")
    for r in results:
        print(f"  {r['id']}  {r['name']:<{width}}  {r['verdict']:<10}  {r['detail']}")
    print(f"  => {out['verdict']}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(out, indent=2) + "\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
