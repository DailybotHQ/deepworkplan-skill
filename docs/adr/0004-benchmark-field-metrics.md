# ADR 0004 — Opt-in benchmark field metrics, derived never imputed

Status: Accepted for implementation in v6.1.0 (spec `BENCHMARK.md`).

## Decision and limits

Ship a per-plan metrics subsystem as **opt-in infrastructure, never a
conformance gate**. Four load-bearing choices:

1. **Config flag, fail-closed.** `.dwp/config.json` → `~/.dwp/config.json` →
   disabled. Any malformed input resolves to disabled with one warning line.
   A disabled repository must be byte-identical to a pack without the
   subsystem — the owner's request was a personal flag, not a new default.
2. **Derived, never imputed.** The record is computed from records the plan
   already owns (journal events, manifest, contract, state, best-effort git
   diff). Tokens/spend exist only when `resource_sample` events exist; the
   journal's missing-data rule carries over verbatim. No estimation from
   context bytes — that would smuggle a model of token economics into a
   measurement artifact.
3. **v6 only.** v5 is a frozen line; the aggregator lists v5 plans as
   `not_collected` and nothing more.
4. **Counts vector, no composite index.** Complexity surfaces as named raw
   counts. Any weighted index would embed unjustifiable weights and break
   version-over-version comparability the day the weights change.

## Why field data (and what it does not replace)

The evaluation lab runs designed comparisons; this subsystem passively
collects what real executions already record. The maintainer's stated goal —
"guarantee the next version is measurably better" (v7 vs v6) — needs both:
field evidence for coverage and direction, lab experiments for causal
claims. The aggregator therefore carries a permanent non-causality note;
workloads differ across versions and the report must not manufacture
certainty.

## Rejected alternatives

- **Always-on metrics** — changes every consumer's artifact surface and the
  pack's privacy posture without consent; rejected.
- **A new journal event type per emission** — the record is derived state,
  not protocol history; journaling it would make replays nondeterministic
  (emission timestamp) and double-count on re-runs.
- **Central server / CSV upload** — network dependency and privacy
  regression the stdlib-only, local-first posture forbids; `--csv` export
  covers offline analysis.
- **Measuring via `verify`** — conformance and measurement are different
  questions; coupling them would make evidence optional-ness ambiguous.

## Consequences

- One new shipped helper (`shared/benchmark.py`, stdlib-only, Python 3.9+
  floor, `self-test`) and one published schema
  (`spec/schema/benchmark-record.schema.json`, URL
  `https://deepworkplan.com/schema/benchmark-record/v1.json`).
- The execute completion path gains one conditional step after the receipt;
  with the flag off, zero instruction bytes are added before the completion
  trigger (progressive loading is preserved).
- Schema additions are new versions (v2), never in-place edits — the
  published-line immutability rule applies.
