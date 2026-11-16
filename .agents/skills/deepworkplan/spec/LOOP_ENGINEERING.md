# Loop Engineering (normative, v8)

> Status: normative for the v8 generation. The loop's machinery lives in
> herdr-peers (`autopilot --loop --appoint --brain`, the fleet map and UI,
> the plan-queue consumer); this section defines what a **plan** records so
> the loop can carry it to the end, and nothing more. The key words MUST,
> MUST NOT, SHOULD and MAY are used as in RFC 2119.

## 1. The v8 rule

An approved plan runs to its end without a human. Autonomy is the default
**inside the plan's recorded authority**; the human is notified, never
waited on — except logins and credentials, and the plan's own gates
(C1–C7 publication, push, external messages) still stop unless the plan
records the pre-authorization. v7's rule stands: the methodology works
alone; addons only amplify.

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

Status: specified for the 8.0.0 line; the state field ships with the state
schema change that carries it (a later 8.0.0 change). Until that schema is
published, a writer MUST NOT add these fields to `state.json` (the
published `blocked` object is closed), and every blocker is the human's.

A blocked plan will record a C-class and an optional **`resolver`:
`"lead" | "human"`**; an absent resolver MUST be read as `human`. `lead`
means resolvable inside the plan's recorded authority **without** a
credential, login, consent, payment, push to main, release or deletion. The
loop (its brain included) MUST NOT ask a lead to resolve a blocker the plan
itself did not mark lead-resolvable; everything else waits for the human.

## 4. The plan queue

`.dwp/queue.json`, schema `dwp-queue-v1`. Only the pack (`shared/queue.py`)
or a human MAY write it; the daemon MUST only read it. Create appends on
approval; a human or the lead reorders; execute MUST mark `started` on a
task start while the item is still `queued` (normally the plan's first task,
once its lead has claimed it; a crash or a resume retries), together with the
lead's pane address (a `started` item without one is invalid); execute marks
`done` after the plan's closure; create/refine skip with a
one-line note. A queue MUST NOT hold more than 64 items.
One plan at a time per repository unless the queue carries
`parallel: true`. Dependencies are queue-internal (`after` names a plan
already queued). The daemon is a bounded, read-only consumer; a damaged
queue is a quiet none and never breaks the lifecycle.

## 5. What v8 keeps

Everything v7 carries — `tasks[].parallel_safe`, delegation, the journal
(the v8 event set is the v7 event set) — under one ordered generation
ladder: every feature gated "v7" MUST be available to v8 and later. A v8
plan is materialized into the v7 manifest and journal line
(`plan-manifest/v7`, `journal-event/v7`); a conformance checker MUST pair a
v7 manifest with a v8 contract.
