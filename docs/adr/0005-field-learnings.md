# ADR 0005 — Field learnings, DWP_REPORT.md and the pre-release v1 amendment

Status: Accepted for implementation in v6.1.0 (spec `BENCHMARK.md` §10).

Extends ADR 0004 (opt-in benchmark field metrics) with the qualitative
half: what an execution learned about the method itself.

## Decision and limits

Five load-bearing choices:

1. **Learnings ride on the benchmark subsystem.** A nested sub-flag
   `{"benchmark": {"enabled": true, "learnings": true}}`; default off for
   everyone. A repository with learnings off produces no `learnings.json`
   and changes no other artifact. Fail-closed resolution is per key: a
   wrong-typed `learnings` value disables learnings only, with one warning.
2. **Two halves with different disciplines.** The **derived** half is
   mechanical: one entry per journal-explained friction event (adaptation,
   intervention, refusal, non-zero gate_run) carrying the recorded reason
   verbatim — regenerated deterministically on every run, never
   categorized. The **curated** half is agent judgment (closed category
   vocabulary, anchor, finding, proposal) and is **written once**: after
   the file exists, reruns regenerate the derived half and preserve every
   curated entry byte-for-byte. This split is what lets the determinism
   contract survive qualitative content: determinism governs derived
   bytes, written-once governs curated bytes.
3. **Anchors, not paths.** A curated entry attaches to a journal `seq`
   (immutable, unique) and/or a ≤64-character section identifier — never a
   repository path. Entries with neither are recorded unanchored and
   reported separately. Anchors are the join key the future
   pattern-mining step aggregates on; paths would break across versions
   and leak the privacy boundary (ADR 0004 §privacy).
4. **Closed category vocabulary (v1).** Exactly seven categories:
   spec-gap, instruction-gap, tooling-gap, docs-gap, gate-false-positive,
   gate-false-negative, context-miss. Machine-comparable across ~50 plans
   requires a closed set; adding a category is a schema revision, never an
   ad-hoc label.
5. **One human artifact.** `BENCHMARK.md` (the rendered summary) is
   renamed **`DWP_REPORT.md`** and becomes the render of both records —
   metrics, spans, context accounting, derived friction, curated table.
   The Markdown remains a rendering, never a second source.

## The pre-release v1 amendment (and why it is legal exactly once)

House rule: adding a field to a record schema is a revision (v2), never an
in-place edit. This decision amends `benchmark-record/v1.json` in place
with two **optional** fields — `timing.task_spans` and
`context_accounting` — and that is legitimate only under all three of:

- **No released pack minted the v1 `$id` URL.** The URL exists only inside
  this repository; the schemas are not yet published on
  deepworkplan.com, v6.1.0 has not been tagged, and the branch carrying
  the v1 schema is unpushed. No consumer of v1-bytes-can-change can exist.
- **The fields are optional.** Every record already committed under the
  earlier v1 bytes still validates unchanged; the committed fixtures are
  the regression proof.
- **The exception is recorded here.** After the first release carrying
  this schema, the v2 rule applies without exception.

The same window is what makes the `BENCHMARK.md` → `DWP_REPORT.md` rename
free: no released pack ever wrote the old artifact name.

The maintainer additionally requires this whole line of work to release
**within the v6 line** (never v7): all changes stay additive, commits
carry `feat(...)`/`fix(...)` prefixes only (auto-release maps `!`/
`BREAKING CHANGE:` to MAJOR), and no schema change is breaking.

## Why per-task spans and context accounting (and what stays out)

Per-task calendar spans turn the plan-level span into a distribution —
the input the pattern-mining step needs to correlate structure with
friction. Context accounting (the four-quantity block:
`instruction_bytes`, `provider_tokens`, `cost_usd`, `wall_clock_hours`)
surfaces the token-efficiency economy per execution, honest to
`available: false` when unrecoverable. Both are **optional** record
fields; both follow derived-never-imputed — absent evidence is an absent
value, never zero. Out of scope, deliberately: a host sampler
(`resource_sample` emission — the prerequisite for real token/spend
data), cross-repo `diff_stats`, publishing the schemas on
deepworkplan.com, and the PATTERN_REPORT synthesis ritual that will
consume the aggregate output.

## Rejected alternatives

- **Learnings as journal events** — rejected: no new protocol state; the
  journal is history, learnings are derived + curated state
  (INV-no-protocol-change).
- **One free-form Markdown learnings file, no JSON** — rejected: the
  pattern-mining goal needs machine-comparable structure (closed
  categories, anchors); prose alone cannot be aggregated.
- **Curated entries regenerated or merged by the helper** — rejected: the
  executing agent's judgment is evidence; a rerun that rewrites it destroys
  the record and invites deduplication drift (INV-written-once).
- **An `emitted_at` / curated-timestamp field** — rejected: any emission
  clock breaks byte-identical reruns of the derived half.
