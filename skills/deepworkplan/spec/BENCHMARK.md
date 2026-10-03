# BENCHMARK.md — Opt-in per-plan metrics (field record)

> **Status: v6 line, never a conformance gate.** This document defines the
> opt-in benchmark subsystem: a configuration flag that makes completed v6
> plans emit a metrics record derived from records the plan already owns, and
> an aggregator that combines records across plans and repositories. It binds
> only repositories that enable it. A repository with benchmark disabled —
> the default — MUST behave byte-identically to a pack without this
> subsystem: no flow reads any benchmark file, and no plan artifact differs.
> Like the evaluation lab, this is measurement infrastructure; unlike the
> lab, it collects **field data from real executions** rather than running
> controlled comparisons. Nothing here gates plan conformance (`verify`
> never checks benchmark artifacts).

All documents in this spec use RFC-2119 language.

## 1. Configuration

Benchmark mode is opt-in through a JSON configuration file:

| Precedence | Path | Scope |
|---|---|---|
| 1 (highest) | `<repo-root>/.dwp/config.json` | this repository — the repository **containing the plan** (the plan's `.dwp` ancestor), never the helper's working directory |
| 2 | `~/.dwp/config.json` | all repositories of the local user |
| 3 | absent | **disabled** |

```json
{ "benchmark": { "enabled": true } }
```

- The effective setting is resolved **per key**: a repository file that
  omits the `benchmark` object defers to the global file; a repository file
  that carries it overrides the global file wholesale for that key.
- Both files share one shape: an optional top-level `"benchmark"` object
  with an optional boolean `"enabled"`. Unknown keys inside the object are
  ignored (forward compatibility).
- **Fail-closed handling:** a missing file, unreadable path, invalid JSON,
  or a wrong-typed value (`"enabled": "yes"`) MUST resolve to **disabled**
  and emit exactly one warning line naming the file and the reason. It MUST
  NOT raise, MUST NOT abort any flow, and MUST NOT be silent.
- Config resolution happens only at the emission point (§2) and in the
  aggregator. No other flow reads these files.

## 2. Emission point and artifacts

When benchmark is enabled for the repository that owns a plan, the plan's
completion path (the v6 execute completion step, after the receipt is
produced) runs the shipped helper:

```
python3 <pack>/shared/benchmark.py report --plan <dir>
```

- **Artifacts:** `<plan>/analysis_results/benchmark.json` (the machine
   record, §4) and `<plan>/analysis_results/BENCHMARK.md` (a human summary
   rendered **from the same record** — the Markdown MUST NOT contain any
   number absent from the JSON; it is a rendering, never a second source).
- **Atomicity:** both files are written write-temp-then-rename; a partial
  write MUST NOT be observable.
- **Idempotence and determinism:** re-running `report` on an unchanged plan
  rewrites byte-identical artifacts. Record content MUST NOT depend on the
  wall clock at emission time, the executing user's environment, or map
  ordering; timestamps come from the plan's own records. The record carries
  no `emitted_at` field for exactly this reason.
- **Non-blocking (absolute):** any emission failure — unreadable records,
  unwritable `analysis_results/`, torn journal tail — MUST degrade to a
  warning line and exit status 0. Plan completion MUST NOT depend on
  benchmark emission. Emission failure is never a plan failure. Usage
  errors (bad arguments) are the only exit-2 conditions.
- **v5 stance:** v5-generation plans (no v6 manifest contract pointer) are
  never measured. `report` on a v5 plan prints one line and exits 0
  without writing artifacts. The v5 line stays frozen.

## 3. Metric provenance

Every field in the record comes from exactly one provenance class:

| Class | Source | Fields |
|---|---|---|
| journal-derived | `journal.ndjson` events | timing spans (event `ts`), friction counts (`adaptation`, `amendment`, `intervention`, `refusal`), gate outcomes (`gate_run` exit codes), evidence-class histogram (`observed` / `imported` / `asserted`), control pairs, event count |
| identity-derived | `manifest.json`, `contract.json`, `state.json` | plan name/title, generation, `contract_id`, spec version, task count, criteria/invariant counts, completion status |
| environment-derived | pack frontmatter, plan's repository | DWP skill version (the emitting pack's own `version:`), agent tool, repository name, branch |
| metered-only | `resource_sample` events | token and spend totals, per unit, `metered` flag |

- **Wall-clock is calendar span** between recorded timestamps (first event
  → last event, and per-task `task_start` → completion evidence). It is
  NOT compute time: sessions idle, hosts restart, humans review. The
  rendered summary MUST label it "calendar span", never "runtime".
- **No imputation (absolute):** a quantity without a recording source is
  `null`. Without `resource_sample` events, token and spend fields are
  `null` and `"metered": false`. Missing records degrade their section,
  never synthesize values, never default to zero — the journal rule
  (*missing data is exposed as missing, never imputed*) carries over
  verbatim.
- Diff stats (files changed / insertions / deletions for the plan window)
  are computed best-effort from the plan repository's git history between
  the first `task_start` fingerprint's revision and the emission-time
  revision. On any git failure they are `null` with `"diff_stats":
  {"available": false}` — never omitted silently, never estimated.

## 4. The record (closed field set)

`benchmark.json` validates against
[`schema/benchmark-record.schema.json`](schema/benchmark-record.schema.json)
(`https://deepworkplan.com/schema/benchmark-record/v1.json`), which is the
normative field list. Required top-level fields:

```
schema · plan · title · generation · contract_id · status
versions { dwp_skill, spec, agent_tool }
timing  { first_event_ts, last_event_ts, span_seconds, task_count_spanned }
shape   { tasks, criteria, invariants, gate_intents, events }
friction{ adaptations, amendments, interventions, refusals, retries }
gates   { runs, exit_0, exit_nonzero, evidence_histogram }
metered { flag, tokens, spend_usd }
environment { repo, branch }
diff_stats  { available, files, insertions, deletions }
```

The schema's closed-object style follows the house convention. Adding a
field is a schema revision (v2), never an in-place edit.

## 5. Complexity profile

The record's complexity signal is the **counts vector** — `shape` +
`friction` + `gates` + `diff_stats` — raw, named, self-describing counts.
Composite indices (weighted "complexity score", normalized "efficiency")
are **out of scope for v1**: any composite would embed weights the data
cannot justify, and a changed composite would silently break
version-over-version comparability. A future composite MUST arrive as its
own spec revision with its formula stated in the schema.

## 6. Aggregation

```
python3 <pack>/shared/benchmark.py aggregate --roots <repo>... [--scan <parent>]
                                          [--csv PATH] [--out PATH]
```

- Inputs are `benchmark.json` records only (glob
  `<root>/.dwp/plans/*/analysis_results/benchmark.json` and nested
  repositories under `--scan`). v5 plan folders encountered are listed
  with `generation: "v5", metrics: "not_collected"`.
- Output is **descriptive**: grouped by DWP skill version, then repository;
  per group — plan count, aggregate counts, span distribution
  (min/median/max), gate failure ratio, metered coverage. The report MUST
  carry this note verbatim: *aggregates describe recorded executions;
  workloads differ across plans, repositories and versions — this is
  evidence for discussion, not a causal comparison*.
- A version-over-version table appears only when ≥ 2 skill versions are
  present, and only with the note above.
- `--csv` writes one row per plan (the JSON record flattened) for offline
  analysis. `--out` defaults to stdout; when a file is written inside a
  git-tracked tree, it happens only because the user explicitly passed the
  path. The aggregator never writes into any `.dwp/` other than stdout
  redirection the user performs.

## 7. Privacy and security boundary

- Record fields are limited to: repository **name** (basename), branch,
  plan identity, timestamps, counts, versions, and metered totals. The
  subsystem MUST NOT record: environment variable values, secrets,
  credential names, prompt or file contents, absolute user paths, or any
  token of a prompt/context byte stream.
- All artifacts stay inside gitignored `.dwp/` trees unless the user
  explicitly directs output elsewhere (§6).
- The helper reads only: the two config files, the plan's own records, and
  (best-effort, read-only) the plan repository's git metadata. It performs
  no network access and executes no repository code.

## 8. Determinism contract

Two `report` runs over identical plan bytes produce identical artifact
bytes. Two `aggregate` runs over identical record sets produce identical
report bytes (CSV row order: plan identity sort). Tests pin both. Any
nondeterminism is a defect in the helper, never an acceptable artifact.

## 9. Version-over-version use

The record exists so a maintainer can compare skill versions on field
evidence (e.g. v7 against v6) instead of assertion. The comparison the
subsystem enables is **descriptive statistics over recorded executions**
(§6). It does not replace the evaluation lab's controlled comparisons; the
two disciplines compose — the lab for designed experiments, the benchmark
for field data. Guaranteeing "a new version is better" additionally
requires comparable workloads; the aggregator surfaces coverage and
caveats, it does not manufacture certainty.
