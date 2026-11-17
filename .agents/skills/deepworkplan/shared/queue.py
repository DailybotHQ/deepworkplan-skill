#!/usr/bin/env python3
"""The plan queue (``dwp-queue-v1``) — ``.dwp/queue.json``, written only by
the pack.

Contract (PLAN_024 item 3.5, agreed with the herdr-peers side 2026-11-15):

- Schema ``dwp-queue-v1``; the document is closed (no unknown keys) so every
  consumer — the herdr-peers daemon, the fleet UI, the vim plan browser —
  reads one stable shape, the way it reads the manifest today.
- Items: ``{plan, after (plan id | null), state: queued|started|done|skipped,
  lead (a pane address | null), start: prompt-lead|launch}``; the queue may
  carry ``parallel: true`` (default: one plan at a time per repository).
- Writers, and only these: `create` appends on approval (with the lead the
  daemon prompts, ``--lead``); the developer or the lead names or renames a
  queued plan's lead (``set-lead``) and reorders (the file is theirs to edit); `execute` flips ``started`` on a
  task start while the item is still queued (with the lead address) and ``done`` after the plan's
  closure; `create`/`refine` flip ``skipped`` with a one-line note. The
  daemon is a bounded, read-only consumer and never writes.
- The write is atomic (temp file + rename) with mode 0600, the lead records'
  discipline. A read of anything that is not a valid, bounded document is a
  quiet None — a damaged queue must never break the plan lifecycle.

Usage (the flows call it the way they call the other state helpers)::

    python3 shared/queue.py --dwp <dir> show
    python3 shared/queue.py --dwp <dir> append --plan PLAN_x [--after PLAN_y] [--start prompt-lead] [--lead local:w1:p2]
    python3 shared/queue.py --dwp <dir> set-lead --plan PLAN_x --lead local:w1:p2
    python3 shared/queue.py --dwp <dir> set-state --plan PLAN_x --state started --lead local:w1:p2
    python3 shared/queue.py --dwp <dir> set-state --plan PLAN_x --state done
    python3 shared/queue.py --dwp <dir> set-state --plan PLAN_x --state skipped --note "reason"
"""

import argparse
import json
import os
import re
import stat
import sys
import tempfile
import time

SCHEMA = "dwp-queue-v1"
STATES = ("queued", "started", "done", "skipped")
# The lifecycle (spec/LOOP_ENGINEERING.md section 4): a queued plan starts,
# finishes or is skipped (outside Herdr it is marked done straight from
# queued); a started plan finishes or is skipped; done and skipped are
# terminal, because plan ids are one-shot.
TRANSITIONS = {
    "queued": ("started", "done", "skipped"),
    "started": ("done", "skipped"),
    "done": (),
    "skipped": (),
}
STARTS = ("prompt-lead", "launch")
MAX_BYTES = 64 * 1024
# The consumer's own caps (herdr-peers fleet_report): a queue above 64 items,
# or 64 KiB, is refused wholesale by the daemon — the writer enforces the
# same ceilings so a producer-valid document is always consumer-valid.
MAX_ITEMS = 64
# herdr-peers' exact form, the same as contract_v6.PANE_ADDRESS (a test pins them
# equal): a machine id is passed to Herdr as an argument, so it cannot start with '-'.
PANE_ADDRESS = re.compile(r"^(?:local|[A-Za-z0-9][A-Za-z0-9._-]{0,63}):[A-Za-z0-9]{1,32}:[A-Za-z0-9]{1,32}$")
PANE_ID = re.compile(r"^[A-Za-z0-9]{1,32}:[A-Za-z0-9]{1,32}$")
PLAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
NOTE_MAX = 200


def norm_lead(value):
    """A lead as written by a caller: a full pane address stays as it is; a
    bare Herdr pane id (`w9:p1`, what $HERDR_PANE_ID may hold) becomes
    `local:w9:p1`; surrounding blanks are dropped. The result is still checked
    against PANE_ADDRESS by the caller."""
    if not isinstance(value, str):
        return value
    value = value.strip()
    return "local:" + value if PANE_ID.fullmatch(value) else value


def _iso_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def queue_path(dwp_dir):
    return os.path.join(dwp_dir, "queue.json")


def valid_doc(doc):
    """True when doc is a closed, well-formed dwp-queue-v1 document."""
    if not isinstance(doc, dict):
        return False
    allowed = {"schema", "updated_at", "items", "parallel"}
    if set(doc) - allowed or doc.get("schema") != SCHEMA:
        return False
    if not isinstance(doc.get("items"), list) or len(doc["items"]) > MAX_ITEMS:
        return False
    if "parallel" in doc and not isinstance(doc["parallel"], bool):
        return False
    for item in doc["items"]:
        if not isinstance(item, dict):
            return False
        keys = set(item)
        base = {"plan", "after", "state", "lead", "start"}
        note = {"note"}
        if not keys <= base | note or not keys >= base:
            return False
        if not isinstance(item["plan"], str) or not PLAN_ID.fullmatch(item["plan"]):
            return False
        after = item["after"]
        if after is not None and (not isinstance(after, str) or not PLAN_ID.fullmatch(after)):
            return False
        if item["state"] not in STATES or item["start"] not in STARTS:
            return False
        lead = item["lead"]
        if lead is not None and (not isinstance(lead, str) or not PANE_ADDRESS.fullmatch(lead)):
            return False
        if item["state"] == "started" and lead is None:
            return False
        if "note" in item and (not isinstance(item["note"], str)
                               or not item["note"].strip() or len(item["note"]) > NOTE_MAX):
            return False
    plans = [i["plan"] for i in doc["items"]]
    return len(plans) == len(set(plans))


def _safe_dwp(dwp_dir):
    """Refuse a symlinked .dwp: the write must land inside the repository's
    own .dwp, never in whatever a link points at (fleet_report's consumer
    reads the repository's queue; a redirected write is data loss)."""
    if os.path.islink(dwp_dir):
        raise SystemExit("queue.py: %s is a symlink; the queue lives in the "
                         "repository's own .dwp" % dwp_dir)


def read(dwp_dir):
    """The validated document, or None (a damaged queue never breaks the
    lifecycle; the caller may warn once)."""
    path = queue_path(dwp_dir)
    try:
        # O_NOFOLLOW + fstat on the descriptor itself: a queue.json that is
        # a symlink is refused (it would read another file), and the stat
        # never races through the path.
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                return None
            raw = os.read(fd, MAX_BYTES + 1)
        finally:
            os.close(fd)
        if len(raw) > MAX_BYTES:
            return None
        doc = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError):
        return None
    return doc if valid_doc(doc) else None


def _write(dwp_dir, doc):
    doc["updated_at"] = _iso_now()
    doc.setdefault("schema", SCHEMA)
    if not valid_doc(doc):
        raise SystemExit("queue.py: refusing to write a document that would "
                         "not validate (dwp-queue-v1 is closed)")
    path = queue_path(dwp_dir)
    fd, tmp = tempfile.mkstemp(dir=dwp_dir, prefix=".queue.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _load_or_new(dwp_dir):
    doc = read(dwp_dir)
    if doc is None:
        if os.path.exists(queue_path(dwp_dir)):
            raise SystemExit("queue.py: %s is not a valid dwp-queue-v1 document; "
                             "not touching it" % queue_path(dwp_dir))
        return {"schema": SCHEMA, "updated_at": _iso_now(), "items": []}
    return doc


def append(dwp_dir, plan, after=None, start="prompt-lead", lead=None):
    _safe_dwp(dwp_dir)
    lead = norm_lead(lead)
    if lead is not None and (not isinstance(lead, str) or not PANE_ADDRESS.fullmatch(lead)):
        raise SystemExit("queue.py: --lead is not a pane address "
                         "(local|<machine>):<workspace>:<pane>")
    doc = _load_or_new(dwp_dir)
    for item in doc["items"]:
        if item["plan"] == plan:
            raise SystemExit("queue.py: %s is already in the queue (%s); plan "
                             "ids are one-shot — re-queuing is an error, use a "
                             "new plan" % (plan, item["state"]))
    if after is not None:
        if after == plan:
            raise SystemExit("queue.py: --after must not name the plan itself")
        if not any(i["plan"] == after for i in doc["items"]):
            raise SystemExit("queue.py: --after names %s, which is not in the "
                             "queue; dependencies are queue-internal" % after)
    if len(doc["items"]) >= MAX_ITEMS:
        raise SystemExit("queue.py: the queue holds at most %d items (the "
                         "consumer refuses more)" % MAX_ITEMS)
    doc["items"].append({"plan": plan, "after": after, "state": "queued",
                         "lead": lead, "start": start})
    _write(dwp_dir, doc)
    return doc


def set_lead(dwp_dir, plan, lead):
    """Name (or rename) the lead the daemon prompts to start a queued plan."""
    _safe_dwp(dwp_dir)
    lead = norm_lead(lead)
    if not isinstance(lead, str) or not PANE_ADDRESS.fullmatch(lead):
        raise SystemExit("queue.py: --lead is not a pane address "
                         "(local|<machine>):<workspace>:<pane>")
    doc = _load_or_new(dwp_dir)
    item = next((i for i in doc["items"] if i["plan"] == plan), None)
    if item is None:
        raise SystemExit("queue.py: %s is not in the queue" % plan)
    if item["state"] != "queued":
        raise SystemExit("queue.py: only a queued plan's lead can be named (got %s)" % item["state"])
    item["lead"] = lead
    _write(dwp_dir, doc)
    return doc


def set_state(dwp_dir, plan, state, lead=None, note=None):
    _safe_dwp(dwp_dir)
    lead = norm_lead(lead)
    doc = _load_or_new(dwp_dir)
    if state == "started" and lead is None:
        raise SystemExit("queue.py: started needs --lead (the lead that claimed the plan)")
    if lead is not None:
        if state != "started":
            raise SystemExit("queue.py: --lead belongs to the started state")
        if not isinstance(lead, str) or not PANE_ADDRESS.fullmatch(lead):
            raise SystemExit("queue.py: --lead is not a pane address "
                             "(local|<machine>):<workspace>:<pane>")
    item = next((i for i in doc["items"] if i["plan"] == plan), None)
    if item is None:
        raise SystemExit("queue.py: %s is not in the queue" % plan)
    if item["state"] == "done":
        raise SystemExit("queue.py: %s is already done; the queue is append-only history" % plan)
    if state == "started" and item["state"] != "queued":
        raise SystemExit("queue.py: only a queued plan starts (got %s)" % item["state"])
    if state not in TRANSITIONS.get(item["state"], ()):
        raise SystemExit("queue.py: %s cannot go from %s to %s (allowed: %s)"
                         % (plan, item["state"], state,
                            ", ".join(TRANSITIONS.get(item["state"], ())) or "none, it is terminal"))
    if state == "skipped":
        if not note or not note.strip():
            raise SystemExit("queue.py: skipping needs a one-line note")
        item["note"] = note.strip()[:NOTE_MAX]
    item["state"] = state
    if state == "started":
        item["lead"] = lead
    _write(dwp_dir, doc)
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(prog="queue.py", description=__doc__.splitlines()[0])
    ap.add_argument("--dwp", required=True, help="the .dwp directory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show", help="print the queue document (exit 1 when unusable)")
    p = sub.add_parser("append", help="append a queued plan (create, on approval)")
    p.add_argument("--plan", required=True)
    p.add_argument("--after", default=None, help="a plan id this one waits for")
    p.add_argument("--start", default="prompt-lead", choices=STARTS)
    p.add_argument("--lead", default=None,
                   help="the pane address the daemon prompts to start it (without one it waits for a human to name one)")
    p = sub.add_parser("set-lead", help="name the lead the daemon prompts to start a queued plan")
    p.add_argument("--plan", required=True)
    p.add_argument("--lead", required=True)
    p = sub.add_parser("set-state", help="flip a state (execute, create/refine)")
    p.add_argument("--plan", required=True)
    p.add_argument("--state", required=True, choices=STATES)
    p.add_argument("--lead", default=None, help="the lead pane address (with started)")
    p.add_argument("--note", default=None, help="the one-line reason (with skipped)")
    args = ap.parse_args(argv)
    if args.cmd == "show":
        doc = read(args.dwp)
        if doc is None:
            print("queue.py: no usable queue at %s" % queue_path(args.dwp), file=sys.stderr)
            return 1
        print(json.dumps(doc, indent=2, sort_keys=True))
        return 0
    if args.cmd == "set-lead":
        if not PLAN_ID.fullmatch(args.plan):
            raise SystemExit("queue.py: --plan is not a plan id")
        set_lead(args.dwp, args.plan, args.lead)
        return 0
    if args.cmd == "append":
        if not PLAN_ID.fullmatch(args.plan):
            raise SystemExit("queue.py: --plan is not a plan id")
        append(args.dwp, args.plan, args.after, args.start, args.lead)
        return 0
    if not PLAN_ID.fullmatch(args.plan):
        raise SystemExit("queue.py: --plan is not a plan id")
    set_state(args.dwp, args.plan, args.state, args.lead, args.note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
