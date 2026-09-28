# movement.md — knowing you are inside Herdr, and the safe subset

## 1. Detection

```bash
herdr pane current
```

Success (a pane id comes back) → this session is a Herdr pane: it can send
granted prompts and receive replies addressed to `(machine_id, pane_id)`.
Failure → this session can still SEND, but cannot be addressed for replies;
it says so once and continues single-agent. It never pretends a reply will
arrive.

`herdr --machine <id> pane get <pane>` across enabled machines identifies
which machine hosts the pane when the session needs its own machine id.

## 2. The safe subset (always allowed inside Herdr)

- Read own pane, list machines, list agents, read workspace/tab labels.
- Send a granted prompt to another pane (protocol.md §3-§5).
- Describe where it is (machine label, pane id) in delegation records.

## 3. Forbidden without an explicit, plan-recorded delegation of that pane

- Closing or resizing the human's panes.
- Stealing focus.
- Renaming machines, panes, or the human's session.
- Killing or restarting another agent's session.
- Writing outside the workspace the delegation granted.

Identity rule: a machine's label may change under you; identity is the
machine id plus the SSH target. Never act on a pane because its TITLE
looked right — titles are labels.

## 4. When a peer misbehaves

A peer that ignores the stop rule (answers a reply, loops, or escalates
without cause) is recorded in the delegation record and excluded from the
next round — the orchestrator does not punitive-strike panes. Persistent
misbehavior after one exclusion escalates to the human with the evidence
trail.
