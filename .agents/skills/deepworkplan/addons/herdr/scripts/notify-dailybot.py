#!/usr/bin/env python3
"""Plan-loop event notifier for the Dailybot CLI (herdr addon, DWP pack).

Companion to `herdr-peers autopilot --loop --notify <command>` (herdr-peers
1.3.0): the daemon runs this script with a `plan-event-v1` JSON document on
stdin whenever a watched plan is stalled, blocked, left without a lead, or
completed. The script turns that event into one human-readable Dailybot
report when the Dailybot CLI is installed and logged in.

Design contract (see ../SPEC.md, "Plan loop"):

- **Never breaks the daemon.** Every exit path is `0` and silent unless a
  report was actually sent: missing CLI, not logged in, invalid JSON, an
  unknown event, or a failed send are all quiet no-ops.
- **Stdlib only** (python3 >= 3.9), no network of its own — the Dailybot
  CLI owns auth and transport.
- **Human-first messages**: repository *basename*, plan *basename*, machine
  and lead — never raw filesystem paths.

Event fields (`plan-event-v1`): schema, event
(plan_stalled | plan_blocked | plan_no_lead | plan_completed), plan, machine,
lead, repo_root, blocker_class, at.
"""

import json
import os
import shutil
import subprocess
import sys

SCHEMA = "plan-event-v1"
AGENT_NAME = "deepworkplan-loop"
# The daemon runs this command without a shell under a 20 s timeout; stay
# below it so the script exits 0 by itself instead of being killed.
SEND_TIMEOUT_SECONDS = 15

# Human-readable summary per event class. Placeholders: plan, repo, machine,
# lead, blocker. Kept short on purpose — this is a notification, not a report.
MESSAGES = {
    "plan_completed": (
        "Loop finished a plan: '{plan}' in {repo} ran to completion "
        "(lead {lead}, machine {machine})."
    ),
    "plan_stalled": (
        "Loop stopped nudging a plan: '{plan}' in {repo} made no progress "
        "after repeated prompts (lead {lead}, machine {machine}). "
        "It needs a human look."
    ),
    "plan_blocked": (
        "A plan is waiting on its human: '{plan}' in {repo} is blocked "
        "(class {blocker}; lead {lead}, machine {machine})."
    ),
    "plan_no_lead": (
        "A plan has nobody leading it: '{plan}' in {repo} lost its lead and "
        "no successor is reachable (machine {machine})."
    ),
}


def _basename(value):
    """Last path segment of a plan id or repo root, '' when unusable.

    The daemon may pass an id ('PLAN_x') or a path; either way the basename
    is the piece a human recognizes, and it never leaks a machine's
    filesystem layout into a report.
    """
    if not isinstance(value, str) or not value.strip():
        return ""
    return value.rstrip("/").rsplit("/", 1)[-1].strip()


def _looks_like_event(document):
    """Shape check only — tolerate extra fields, never trust them."""
    return (
        isinstance(document, dict)
        and isinstance(document.get("event"), str)
    )


def build_message(event):
    """Map one plan-event-v1 document to a notification string, or None."""
    if not _looks_like_event(event):
        return None
    kind = event.get("event")
    template = MESSAGES.get(kind)
    if template is None:
        return None
    blocker = event.get("blocker_class")
    return template.format(
        plan=_basename(event.get("plan")) or "(unnamed plan)",
        repo=_basename(event.get("repo_root")) or "(unknown repo)",
        machine=event.get("machine") or "unknown machine",
        lead=event.get("lead") or "none",
        blocker=blocker if isinstance(blocker, str) and blocker else "unspecified",
    )


def send(message, event):
    """One best-effort `dailybot agent update`; the outcome never exits non-zero."""
    cli = shutil.which("dailybot")
    if cli is None:
        return
    metadata = {
        "repo": _basename(event.get("repo_root")),
        "machine": event.get("machine"),
        "event": event.get("event"),
        "agent_tool": "herdr-peers-autopilot",
    }
    command = [
        cli, "agent", "update", message,
        "--name", AGENT_NAME,
        "--metadata", json.dumps({k: v for k, v in metadata.items() if v}),
    ]
    try:
        subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=SEND_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main():
    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
    except (ValueError, OSError):
        return 0
    if not isinstance(event, dict) or event.get("schema") not in (None, SCHEMA):
        return 0
    message = build_message(event)
    if message is None:
        return 0
    send(message, event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
