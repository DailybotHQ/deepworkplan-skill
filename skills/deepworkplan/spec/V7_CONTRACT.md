# V7_CONTRACT.md — Contract generation v7: delegation records (Normative)

> Status: **7.0.0**. A new **contract generation** of the v6
> record layer, not a new lifecycle: everything in
> [`V6_CONTRACT.md`](V6_CONTRACT.md), [`V6_LIFECYCLE.md`](V6_LIFECYCLE.md),
> [`V6_CONTEXT.md`](V6_CONTEXT.md) and [`V6_RESOURCES.md`](V6_RESOURCES.md)
> applies unchanged unless this document says otherwise. Published as
> `schema/plan-contract-v7`, `schema/journal-event-v7` and
> `schema/plan-manifest-v7`. The v1/v2/v5/v6 schema files are byte-for-byte
> unchanged. RFC-2119 language.

## 1. Generation

- The contract's `schema` URL names the generation:
  `https://deepworkplan.com/schema/plan-contract/v7.json` is v7,
  `…/plan-contract/v6.json` is v6. Detection MUST use this URL (and the
  manifest/journal URLs that mirror it), never the pack version.
- A v7 plan's manifest carries `…/plan-manifest/v7.json` and **every**
  journal event carries `…/journal-event/v7.json`. A journal that mixes
  generations, or a v7 event under a v6 contract, MUST be refused.
- New plans created by the 7.x pack are v7 by default; an explicit `v6`
  request materializes a v6 contract. A plan never changes generation: v6
  plans keep v6 forever and run unchanged.
- v7 plans project into the unchanged `plan-snapshot/v6` shape (its
  `positions` are keyed by event type, so the `delegation` type needs no new
  snapshot schema).
- `shared/benchmark.py` measures v6 plans only: the published
  `benchmark-record/v1` and `learnings-record/v1` pin `generation: "v6"`,
  so a v7 plan is reported as not measured — one line, never mislabelled,
  never blocking. A v7 record shape is a later release.

## 2. The contract: `tasks[].parallel_safe`

`plan-contract/v7` = `plan-contract/v6` plus one optional task field:

- `parallel_safe` (boolean, default `false`) — set by `create`, never
  inferred during execution. It asserts that the task can run in a
  delegate without interleaving with sibling work: its touched surface
  does not overlap a sibling that may be in progress, it declares a bounded
  output, and its gates run in this plan. `create` marks tasks only when
  the repository has a delegation addon enabled (`CONFIG.md` §3) — the
  marker is otherwise noise.
- Marking a task changes no authority: delegation additionally needs the
  `agent_delegation` grant (§4). A contract without the grant may still
  carry markers; they authorize nothing.

## 3. The journal: the `delegation` event

`journal-event/v7` = `journal-event/v6` plus one type. One event per state
transition of one delegate:

| Field | Required | Meaning |
|---|---|---|
| `task` | yes | the `T-*` task the delegate works for |
| `delegation_id` | yes | correlates a launch with its terminal transition |
| `transport` | yes | `headless` (agentkit) or `interactive` (herdr) |
| `via` | yes | the addon key that carried it |
| `state` | yes | `launched`, then exactly one of `completed`, `failed`, `cancelled` |
| `kind`, `profile` | no | the coding-agent kind and profile |
| `target` | no | `cwd` (headless) or `machine:pane` (interactive) |
| `worktree` | no | the delegate's own git worktree; `null` for a read-only delegate |
| `prompt_digest` | on launch | `sha256:<hex>` of the prompt — recorded before the delegate is relied on |
| `result_path`, `result_digest` | completed/failed only | the collected result, relative to the plan or repository, and its digest |

- A delegation is **not evidence**. It carries no trust label and no
  `evidence_path`, and no closure reads it: a criterion is satisfied only
  by the evidence the v6 rules accept. A delegate's result stays
  **`asserted`** until this plan's own gate runner observes it — the parent
  runs the task's gate on the collected work (`ledger.py gate`), which is
  what mints `observed`.
- Transitions are closed: one `launched` per `delegation_id`, then exactly
  one terminal state. A raw `append --type delegation` MUST be refused —
  delegation events exist only through the gated writer (§4).

## 4. The record-layer gate and the verbs

`python3 <pack>/shared/ledger.py --plan <dir> delegate <op> --task <T-id>
[--json OBJECT] [--caps HOST_ABILITIES]`:

| Op | Writes | Effect |
|---|---|---|
| `launch` | yes | records `launched` after the gate below |
| `observe` | no | prints the latest state of each delegation (read-only) |
| `collect` | yes | records `completed` or `failed`, with `result_path` and its digest |
| `cancel` | yes | records `cancelled` |

`launch` MUST be refused — and the refusal recorded as a `refusal` event,
exit 5 — unless **all** hold:

1. the contract is v7;
2. the contract grants `agent_delegation`;
3. the task exists, has started, and is not complete;
4. the task is marked `parallel_safe`, **or** the delegate is read-only
   (`worktree` null);
5. `via` names an in-pack addon whose valid descriptor declares the
   requested `transport` (`ADDONS.md` §7);
6. the effective abilities ([`V7_ABILITIES.md`](V7_ABILITIES.md)) list
   that addon as a source of `subagents` — it is enabled, detected and on
   a compatible interface.

`collect` and `cancel` MUST be refused for an unknown `delegation_id`,
one of another task, or one already terminal. Nothing in the ledger runs a
delegate: the transport addon does (agentkit `ak run` in a dedicated
worktree; herdr-peers in a pane), and the flows decide when to use one
(`execute/v6.md`).

## 5. Orchestrators

The v6 hand-off rule stands: an orchestrator never delegates a **child
plan's** tasks — children run in their own sessions. Intra-plan delegation
of a plan's **own** tasks (§4) is a different thing and is allowed under
the conditions above, in orchestrator and individual plans alike.

## 6. Conformance

- Human sign-off (`ledger.py signoff`) and the human-authority marker are
  generation-neutral: they use the v6 record shapes unchanged
  (`V6_CONTRACT.md` §3), so v6 and v7 plans close asserted criteria the
  same way.

- v6 schema bytes, v6 plans and their lifecycle are unchanged
  (`tests/v6-contract.bats` pins the schema hashes).
- The v7 schemas and the runtime validator agree on the v7 fixtures and
  mutants (`scripts/check-schema-contract.py`, `tests/v7-contract.bats`).
- A plan that never delegates is indistinguishable from a v6 plan except
  for its URLs; the methodology runs with no addon at all
  (`tests/standalone-methodology.bats`).
