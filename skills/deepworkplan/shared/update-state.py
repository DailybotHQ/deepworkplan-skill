#!/usr/bin/env python3
"""Apply a targeted mutation to a Deep Work Plan state.json (state layer).

The state layer stays JSON (ADR 0002); this helper exists so an executing
agent applies a task-close or status change as a bounded delta — set one
task's status, attach its gate records and outcome, recompute counts and the
checkpoint — instead of re-emitting the whole file from context. It writes
atomically (temp file + rename) and only ever assigns fields the closed v2/v5
schema shape knows (the v5 schema is a generation snapshot of v2), and never
touches the declared `schema` URL, so its output validates where the input
did.

Stdlib only (Python 3.9+). It mutates exactly one file: the state.json given
as the first argument. Whole-file regeneration (create, refine recount,
markdown-wins reconciliation) stays a manual, documented operation.

Usage:
  update-state.py STATE.json --task N --status completed \
      [--gate "command|exit_code|evidence"] [--gate ...] \
      [--worked "one line"] [--notes "pointer"] [--commit <sha>] \
      [--checkpoint-step "step"] [--checkpoint-note "note"] \
      [--agent <name>] [--model <name>]

Exit codes: 0 applied · 1 validation error (nothing written) · 2 usage.
"""
import argparse
import datetime
import json
import os
import re
import sys
import tempfile
from pathlib import Path
import hashlib

sys.dont_write_bytecode = True
from state_contract import derive_status, invalidated, state_errors

TASK_STATUSES = ("pending", "in_progress", "completed", "blocked", "skipped")
PLAN_STATUSES = ("pending", "in_progress", "completed", "blocked")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
# Closed-schema field budgets (plan-state-v2/v5 schema shape) enforced on write.
LIMITS = {
    "gate.command": 500, "gate.evidence": 500,
    "outcome.worked": 500, "outcome.notes": 1000,
    "checkpoint.step": 200, "checkpoint.note": 500,
    "updated_by.agent": 100, "updated_by.model": 100,
}


def die(msg, code=1):
    print(f"update-state: {msg}", file=sys.stderr)
    sys.exit(code)


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def parse_gates(raw):
    """Each --gate is 'command|exit_code|evidence'."""
    gates = []
    for spec in raw:
        parts = spec.split("|", 2)
        if len(parts) != 3:
            die(f"--gate expects 'command|exit_code|evidence', got: {spec!r}")
        command, exit_code, evidence = (p.strip() for p in parts)
        try:
            code = int(exit_code)
        except ValueError:
            die(f"--gate exit_code is not an integer: {exit_code!r}")
        if len(command) > LIMITS["gate.command"]:
            die(f"gate command exceeds {LIMITS['gate.command']} chars")
        if len(evidence) > LIMITS["gate.evidence"]:
            die(f"gate evidence exceeds {LIMITS['gate.evidence']} chars")
        gates.append({"command": command, "passes": code == 0,
                      "last_run": now(), "exit_code": code,
                      "evidence": evidence})
    return gates


def derive_plan_status(state):
    return derive_status(state)


def next_checkpoint(state, task_id, step, note):
    pending = [t["id"] for t in state["tasks"]
               if t["status"] != "completed"]
    if pending:
        target = min(pending)
        step = step or "start"
        note = note or f"Task {task_id} closed. Next: Task {target}."
    else:
        target = task_id
        step = step or "done"
        note = note or "Plan completed."
    if len(step) > LIMITS["checkpoint.step"]:
        die(f"checkpoint step exceeds {LIMITS['checkpoint.step']} chars")
    if len(note) > LIMITS["checkpoint.note"]:
        die(f"checkpoint note exceeds {LIMITS['checkpoint.note']} chars")
    return {"task": target, "step": step, "at": now(), "note": note}


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("state", help="path to the plan's state.json")
    ap.add_argument("--task", type=int, required=True, metavar="N")
    ap.add_argument("--status", required=True, choices=TASK_STATUSES)
    ap.add_argument("--gate", action="append", default=[], metavar="CMD|EXIT|EVIDENCE")
    ap.add_argument("--gate-json", action="append", default=[], help="JSON gate object; preserves pipes in commands")
    ap.add_argument("--block-reason", default="")
    ap.add_argument("--block-needs", default="")
    ap.add_argument("--resolve-blocker", action="store_true")
    ap.add_argument("--reopen-reason", default="")
    ap.add_argument("--expected-sha256", default="", help="reject stale source state")
    ap.add_argument("--worked", default="")
    ap.add_argument("--notes", default="")
    ap.add_argument("--commit", default="")
    ap.add_argument("--checkpoint-step", default="")
    ap.add_argument("--checkpoint-note", default="")
    ap.add_argument("--agent", default="")
    ap.add_argument("--model", default="")
    args = ap.parse_args()

    for field, value in (("outcome.worked", args.worked), ("outcome.notes", args.notes)):
        if len(value) > LIMITS[field]:
            die(f"--{field.split('.')[1]} exceeds {LIMITS[field]} chars")
    if args.commit and not COMMIT_RE.match(args.commit):
        die(f"--commit is not a commit hash: {args.commit!r}")
    if args.state not in ("", ) and not os.path.isfile(args.state):
        die(f"state file not found: {args.state}")

    try:
        with open(args.state, encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        die(f"cannot read state: {exc}")

    original = Path(args.state).read_bytes()
    if args.expected_sha256 and hashlib.sha256(original).hexdigest() != args.expected_sha256:
        die("stale state snapshot")
    errors = state_errors(state, plan_dir=Path(args.state).parent)
    if errors:
        die("invalid input: " + "; ".join(errors))
    if state.get("materialization", "ready") != "ready" or state.get("promotion"):
        die("plan is not ready")
    if state.get("approval", "approved") not in ("approved", "pre_approved"):
        die("plan is not approved")
    tasks = state.get("tasks") or []
    task = next((t for t in tasks if t.get("id") == args.task), None)
    if task is None:
        die(f"no task {args.task} in this plan "
            f"(have: {[t.get('id') for t in tasks]})")

    if task['status'] == 'completed' and args.status != 'completed' and not args.reopen_reason:
        die("completed task requires an explicit refine/reopen reason")
    if args.status in ('in_progress', 'completed') and any(t['status'] != 'completed' for t in tasks if t['id'] < args.task):
        die("prior required task is not completed")
    if args.resolve_blocker:
        if not state.get('blocked') or state['blocked']['task'] != args.task:
            die("cannot resolve an unrelated or absent blocker")
        if args.status not in ('in_progress', 'completed'):
            die("blocker resolution must resume or complete its task")
        state['blocked'] = None
    if state.get('blocked') and args.status != 'blocked':
        die("resolve the active blocker explicitly first")
    if args.status == 'blocked':
        if not args.block_reason.strip():
            die("blocking requires a reason")
        if state.get('blocked') and state['blocked']['task'] != args.task:
            die("cannot replace an unrelated blocker")
        state['blocked'] = {'task': args.task, 'reason': args.block_reason,
                            'since': (state.get('blocked') or {}).get('since', now()), 'needs': args.block_needs}
    stamp = now()
    if task["status"] != args.status:
        # Idempotence: timestamps record when a transition happened, so a
        # replayed invocation keeps the original reading.
        if args.status in ("in_progress", "completed", "blocked") and not task.get("started_at"):
            task["started_at"] = stamp
        if args.status == "completed" and not task.get("completed_at"):
            task["completed_at"] = stamp
    task["status"] = args.status
    if args.commit:
        task["commit"] = args.commit
    if args.worked or args.notes:
        outcome = dict(task.get("outcome") or {})
        if args.worked:
            outcome["worked"] = args.worked
        if args.notes:
            outcome["notes"] = args.notes
        task["outcome"] = outcome
    incoming = parse_gates(args.gate)
    for raw in args.gate_json:
        try:
            gate = json.loads(raw)
        except ValueError:
            die("invalid --gate-json")
        if not isinstance(gate, dict):
            die("--gate-json must be an object")
        incoming.append(gate)
    if incoming:
        # Retain unrelated results; latest record for a command wins. Logs keep history.
        records = list(task.get('gates', []))
        for gate in incoming:
            previous = next((g for g in reversed(records) if g.get('command') == gate.get('command')), None)
            if previous and {k:v for k,v in previous.items() if k != 'last_run'} == {k:v for k,v in gate.items() if k != 'last_run'}:
                continue
            records.append(gate)
        task['gates'] = records
    if args.status == 'completed':
        latest = {g.get('command'): g for g in task.get('gates', []) if isinstance(g, dict)}
        if not latest or any(not str(g.get('command', '')).strip() or not str(g.get('evidence', '')).strip()
                             or g.get('passes') is not True or g.get('exit_code') != 0 for g in latest.values()):
            die("completion requires successful gates with command, exit code and evidence")
        stale = [c for c, g in latest.items() if invalidated(g)]
        if stale:
            die("completion requires rerunning evidence invalidated by refine: " + ", ".join(map(str, stale)))

    state["completed_count"] = sum(1 for t in tasks if t["status"] == "completed")
    # Plan-level `blocked` carries its own record (reason/since) authored by
    # the blocked protocol; this helper never guesses it.
    state["status"] = derive_plan_status(state)
    state["updated_at"] = stamp
    state["checkpoint"] = next_checkpoint(state, args.task,
                                          args.checkpoint_step, args.checkpoint_note)
    if args.agent or args.model:
        updated_by = dict(state.get("updated_by") or {})
        if args.agent:
            if len(args.agent) > LIMITS["updated_by.agent"]:
                die(f"--agent exceeds {LIMITS['updated_by.agent']} chars")
            updated_by["agent"] = args.agent
        if args.model:
            if len(args.model) > LIMITS["updated_by.model"]:
                die(f"--model exceeds {LIMITS['updated_by.model']} chars")
            updated_by["model"] = args.model
        state["updated_by"] = updated_by

    if state["status"] not in PLAN_STATUSES:
        die(f"internal: derived invalid plan status {state['status']!r}")

    # Sanity guards for the fields this tool owns, before anything is written.
    for t in tasks:
        if t["status"] not in TASK_STATUSES:
            die(f"task {t.get('id')} has invalid status {t['status']!r}")
    if not 0 <= state["completed_count"] <= state.get("task_count", len(tasks)):
        die("completed_count out of range")

    errors = state_errors(state, strict=True, plan_dir=Path(args.state).parent)
    if errors:
        die("invalid candidate: " + "; ".join(errors))
    if state['status'] == 'completed':
        from finalize_plan import publish
        try:
            publish(Path(args.state).parent, state, hashlib.sha256(original).hexdigest())
        except (OSError, ValueError, KeyError, TypeError) as exc:
            die(str(exc))
        print(f"task {args.task} → completed · plan completed and verified")
        return
    directory = os.path.dirname(os.path.abspath(args.state))
    payload = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
    lock = args.state + '.lock'
    try:
        os.mkdir(lock)
    except FileExistsError:
        die("state is locked; inspect interrupted writer before recovering lock")
    if Path(args.state).read_bytes() != original:
        os.rmdir(lock)
        die("state changed during update")
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".state.json.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp_path, args.state)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    finally:
        os.rmdir(lock)

    print(f"task {args.task} → {args.status} · "
          f"{state['completed_count']}/{state['task_count']} completed · "
          f"plan {state['status']}")


if __name__ == "__main__":
    main()
