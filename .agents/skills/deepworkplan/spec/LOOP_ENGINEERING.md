# Loop Engineering (normative, v8)

> Status: normative for the v8 generation. The loop's machinery lives in
> herdr-peers (`autopilot --loop --appoint --brain`, optionally `--revive`,
> the fleet map and UI,
> the plan-queue consumer); this section defines what a **plan** records so
> the loop can carry it to the end, and nothing more. The key words MUST,
> MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. The v8 rule

An approved plan MUST run to completion without routine human intervention,
inside the authority recorded in that plan. The human MUST be notified, not
waited on, except when a login or credential is required or a plan's own C1–C7
gate requires human input and pre-authorization is absent. At those exceptions,
execution MUST stop at the gate until the required input is available. The
methodology works alone; addons only amplify.

### 1.1. Loop semantics

Loop engineering describes how an optional daemon carries an approved,
registered plan forward. It does not expand the plan's authority.

**Registration and succession.** Registration uses a lead claim, which MUST
record the lead and its succession list. The peer holding the highest lead
epoch is the lead. With `autopilot --loop`, a plan with a readable state and a
lead record MAY be watched; the daemon MAY prompt an idle lead to continue
within the plan's recorded authority. If the lead pane is gone, the daemon MAY
prompt the first reachable successor to run `lead takeover`; the helper MUST
check whether takeover is allowed. The daemon MUST NOT write the lead record.
A peer outside the recorded succession MAY become lead only through
Appointment or Revive below, by its own takeover, never by the daemon.

**Human-started daemon and authority.** A human MUST start autopilot. The
background daemon MAY cover enabled machines and sends fixed prompts; a prompt
MUST NOT be treated as a new approval or authority grant. In particular, a
continuation nudge asks the lead to respect the plan's existing gates and
authority. A human MUST provide logins and credentials.

**Appointment.** Lead appointment MUST require both a human's recorded grant
on the lead claim and a human start of the daemon with `--appoint`. After the
lead and its successors meet the documented gone-and-no-progress checks, the
daemon MAY prompt the first eligible live lane to request appointment; the
helper MUST check the conditions again. A new lead MUST run `lead verify`
before a merge, tag, or release.

**Revive.** Revive MUST require a human start of the daemon with
`--revive`; that start is the grant. When a plan's lead and every member of
its succession and lanes are gone and none can take over, the daemon MAY
launch one fresh agent in the plan's checkout and brief it to run `lead
takeover --reason revive`. The helper MUST accept that takeover only with the
daemon's one-time ticket and only after its own checks find every member
gone, and the record is adopted only on the daemon's machine. A stalled plan
whose lead is live MUST NOT be taken over: the daemon MAY ask that lead once
to hand over. Revive is capped per plan and fleet-wide, and a revived lead,
like an appointed one, MUST run `lead verify` before a merge, tag, or release.

**Queue, events, and fleet map.** When a queued item is ready (its `after`
plan is completed, or it has none) and its start is `prompt-lead`, the daemon
MAY prompt its named lead to start it through the plan tool's execute flow;
its start gate MUST check approval again. The daemon MAY report plan events as `plan-event-v1`
JSON to the configured `--notify` command. The `fleet-v1` map reports agents,
plans, and their roles; `fleet ui` shows the map live. The daemon MAY read
the queue and MUST NOT write it.

These behaviors are the optional Herdr integration, documented in
[herdr-peers v2.2.1 `autopilot.md` §§1–9](https://github.com/DailybotHQ/herdr-peers/blob/v2.2.1/skills/herdr-peers/autopilot.md)
and [herdr-peers v2.2.1 `protocol.md` §12](https://github.com/DailybotHQ/herdr-peers/blob/v2.2.1/skills/herdr-peers/protocol.md#12-leadership-lead-notices-and-fencing).

## 2. The `autonomy` block (plan-contract/v8)

Optional, top-level, closed: a validator MUST refuse an unknown key, and
MUST refuse the block on any contract generation other than v8. Every
absent key has one recorded default, and a consumer MUST apply it, never a
guess of its own:

| Key | Type | Absent means |
|---|---|---|
| `stall_budget` | integer 1–10 | `3` (herdr-peers' `MAX_PLAN_PROMPTS`) |
| `promptable` | non-empty list of pane addresses | the plan's **lead only** |
| `notify` | non-empty list of targets | no target (the loop still records) |
| `brain` | boolean | `false` — no brain may act on this plan |
| `queue` | `prompt-lead` \| `launch` \| `none` | `none` — the plan is not queued |

A pane address MUST match herdr-peers' exact form
`(?:local|[A-Za-z0-9][A-Za-z0-9._-]{0,63}):[A-Za-z0-9]{1,32}:[A-Za-z0-9]{1,32}`
— a machine id never starts with `-` (it is passed to Herdr as an
argument). An absent block means all five defaults: the human is the
resolver, the lead is the only promptable pane, nothing is notified, no
brain acts, the plan is not queued.

## 3. Structured blockers

A v8 plan records why it cannot continue as data, so the loop, the fleet and
a resuming agent read the same fields instead of scraping prose.

### 3.1. The blocker record

A blocker MUST be recorded through the ledger's helper (`ledger.py block`
to raise, `ledger.py unblock` to resolve) as a `blocker` event of
`journal-event/v8`; a raw append of a `blocker` event MUST be refused, and
every refused raise or resolution MUST be recorded as a refusal. A raise
carries:

| Field | Rule |
|---|---|
| `task` | the blocked task of this contract; a task its evidence already closed MUST NOT be blocked |
| `reason` | non-empty, at most 1000 characters: why the task cannot continue |
| `needs` | exactly one non-empty line, at most 500 characters: what unblocks it |
| `class` | REQUIRED, one of `C1`–`C7` ([`AGENT_PROTOCOL.md`](AGENT_PROTOCOL.md) §7.5) |
| `resolver` | OPTIONAL, `"lead"` or `"human"`; an absent resolver MUST be read as `human` |

`lead` means resolvable inside the plan's recorded authority **without** a
credential, login, consent, payment, push to main, release or deletion.
`resolver: "lead"` MUST be refused for `C1`, `C2`, `C5` and `C6` (approval,
a consent or login screen, damage, terms are the human's). A resolution
carries only the task (and an optional note).

At most one blocker MUST be active per plan: a raise on another task MUST be
refused until the active one is resolved. A re-raise on the same task MAY
update `reason`, `needs`, `class` and `resolver`; the episode keeps the
`since` of its first raise. While a blocker is unresolved its task MUST NOT
complete: completion MUST be refused, and evidence that lands meanwhile does
not close the task.

### 3.2. Where readers find it

The plan's `state.json` is `plan-snapshot/v8`: the `plan-snapshot/v6` shape
with `blocker` as the active blocker — `{task, reason, since, needs, class,
resolver?}` — or `null`, and `blocked` as a derived task status that wins over
the others while the blocker is unresolved. Like every snapshot field it is
projected by the ledger, never written by hand.

`PROGRESS.md` SHOULD open with a structured header of four fixed lines
directly under its title, written by create and refreshed on every
transition (`shared/progress_header.py`):

```text
Goal: <one line>
Current task: <task id> - <title> (<status>)
Next action: <one line>
Needs: none | <class> (<resolver>): <needs>
```

`Current task` and `Needs` are derived from the snapshot (the blocked task
first, else the first task not completed); `Goal` and `Next action` are the
executing agent's words. The rest of `PROGRESS.md` stays the agents' working
index.

### 3.3. What the loop may do with it

The loop (its brain included) MUST NOT ask a lead to resolve a blocker the
plan itself did not mark `resolver: "lead"`; everything else waits for the
human. v6 and v7 plans record no `blocker` events, keep `plan-snapshot/v6`
(whose `blocker` stays `null`), and every blocker they report is the
human's.

## 4. The plan queue

`.dwp/queue.json`, schema `dwp-queue-v1`. Only the pack (`shared/queue.py`)
or a human MAY write it; the daemon MUST only read it. Create appends on
approval; a human or the lead reorders. Inside Herdr, where the lead's pane
address exists, execute MUST mark `started` on a task start while the item is
still `queued` (normally the plan's first task, once its lead has claimed it;
a crash or a resume retries), together with that address (a `started` item
without one is invalid); outside Herdr the item stays `queued` and a consumer
reads the journal's task start as in flight. Execute marks
`done` after the plan's closure; create/refine skip with a
one-line note. A queue MUST NOT hold more than 64 items.
One plan at a time per repository unless the queue carries
`parallel: true`. Dependencies are queue-internal (`after` names a plan
already queued). The daemon is a bounded, read-only consumer; a damaged
queue is a quiet none and never breaks the lifecycle.

## 5. What v8 keeps

Everything v7 carries — `tasks[].parallel_safe`, delegation and the full v7
event set — under one ordered generation ladder: every feature gated "v7"
MUST be available to v8 and later. A v8 plan MUST record its events under
`journal-event/v8` (the v7 event set plus `blocker`, §3) and project into
`plan-snapshot/v8`; a journal that mixes generations MUST be refused. A v8
plan MUST keep the v7 manifest line (`plan-manifest/v7`): the manifest's
shape and its contract pointer do not change, so a new manifest URL would
add a generation without a difference. A conformance checker MUST pair a v7
manifest with a v8 contract. v6 and v7 plans keep their records byte for
byte.

**Erratum (8.0.1).** The `description` of the frozen
`schema/plan-contract-v8.schema.json` says the journal-event set is unchanged
from v7. That sentence predates the structured blocker (§3): this section and
`schema/journal-event-v8.schema.json` are normative, and a v8 journal carries
the `blocker` event. The schema's bytes stay frozen; only the prose of its
description is superseded.
