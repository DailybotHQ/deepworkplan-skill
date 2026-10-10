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
{ "benchmark": { "enabled": true, "learnings": true } }
```

- The effective setting is resolved **per key**: a repository file that
  omits the `benchmark` object defers to the global file; a repository file
  that carries it overrides the global file wholesale for that key.
- Both files share one shape: an optional top-level `"benchmark"` object
  with an optional boolean `"enabled"` and an optional boolean
  `"learnings"` (§10). Unknown keys inside the object are ignored (forward
  compatibility).
- `"learnings"` rides on the benchmark subsystem: `"enabled": false`
  disables the whole subsystem regardless of `"learnings"`, and
  `"learnings"` defaults to `false`. Metrics emission with learnings off
  is a supported, ordinary configuration — never a warning condition.
- **Fail-closed handling:** a missing file, unreadable path, invalid JSON,
  or a wrong-typed value (`"enabled": "yes"`) MUST resolve to **disabled**
  and emit exactly one warning line naming the file and the reason. It MUST
  NOT raise, MUST NOT abort any flow, and MUST NOT be silent. Each key
  fails closed independently: a wrong-typed `"learnings"` value disables
  learnings only, with its own single warning, while `"enabled"` resolution
  proceeds on its own merits.
- The `benchmark` key is resolved only at the emission point (§2) and in
  the aggregator; no other flow reads it. The file itself is shared with
  the addon registry: its locations, fail-closed reading and the one
  parser (`shared/config.py`) are defined in [`CONFIG.md`](CONFIG.md).

## 2. Emission point and artifacts

When benchmark is enabled for the repository that owns a plan, the plan's
completion path (the v6 execute completion step, after the receipt is
produced) runs the shipped helper:

```
python3 <pack>/shared/benchmark.py report --plan <dir>
```

- **Artifacts:** `<plan>/analysis_results/benchmark.json` (the machine
   record, §4), `<plan>/analysis_results/learnings.json` (the learnings
   record, §10 — written only when learnings is enabled) and
   `<plan>/analysis_results/DWP_REPORT.md` (the single human report,
   rendered **from the two records** — the Markdown MUST NOT contain any
   number or entry absent from the JSON files; it is a rendering, never a
   second source). The former artifact name `BENCHMARK.md` was retired
   before the first release of this subsystem; no released pack ever
   wrote it.
- **Distinct from the Executive Report:** `DWP_REPORT.md` is not the
  Executive Report (DWP_SPECIFICATION.md §6.3) and never replaces it. The
  Executive Report is the on-request stakeholder summary every conformant
  plan still offers once at completion, independent of benchmark
  configuration; this subsystem does not touch it. `DWP_REPORT.md` exists
  only in opted-in repositories and renders field metrics and learnings —
  never stakeholder narrative. A completed plan in an opted-in repository
  may carry both artifacts, each with its own trigger and audience.
- **Atomicity:** every artifact file is written write-temp-then-rename; a
  partial write MUST NOT be observable.
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
| journal-derived | `journal.ndjson` events | timing spans (event `ts`), per-task calendar spans (`task_start` → completion evidence), friction counts (`adaptation`, `amendment`, `intervention`, `refusal`), gate outcomes (`gate_run` exit codes), evidence-class histogram (`observed` / `imported` / `asserted`), control pairs, event count |
| identity-derived | `manifest.json`, `contract.json`, `state.json` | plan name/title, generation, `contract_id`, spec version, task count, criteria/invariant counts, completion status |
| environment-derived | pack frontmatter, plan's repository | DWP skill version (the emitting pack's own `version:`), agent tool, repository name, branch |
| metered-only | `resource_sample` events | token and spend, each the **latest observed** sample for its selection (AGENT_PROTOCOL §8.4), `metered` flag |
| context-manifest-derived | the plan's context accounting, recovered at emission | `context_accounting` (instruction bytes measured; tokens, cost and wall-clock each from its own recorded source) |

- **Wall-clock is calendar span** between recorded timestamps (first event
  → last event, and per-task `task_start` → completion evidence). It is
  NOT compute time: sessions idle, hosts restart, humans review. The
  rendered summary MUST label it "calendar span", never "runtime".
- **Per-task spans follow the same rule:** a task's span is the calendar
  distance from its `task_start` `ts` to its completion evidence `ts`. A
  task without completion evidence in the window has no `end_ts` and no
  `span_seconds` value — the fields are `null`, never zero, and a
  retried-interrupted pair is one span per distinct start when the journal
  records more than one `task_start` for the task.
- **No imputation (absolute):** a quantity without a recording source is
  `null`. Without `resource_sample` events, token and spend fields are
  `null` and `"metered": false`. Missing records degrade their section,
  never synthesize values, never default to zero — the journal rule
  (*missing data is exposed as missing, never imputed*) carries over
  verbatim.
- **Metered values are the latest observed sample, never a sum.** For each
  selection (tokens by `unit: "tokens"`, spend by `limit_id: "spend_usd"`),
  the `resource_sample` with the highest `seq` wins — the same selection
  rule as `context_manifest.accounting` and the envelope rule
  (AGENT_PROTOCOL §8.4: `spent` is the latest observed sample for that
  limit id). A host that samples a gauge repeatedly reports its final
  value; samples for other limit ids are advisory and leave `metered`
  false.
- **Context accounting is the four-quantity block** —
  `instruction_bytes`, `provider_tokens`, `cost_usd`, `wall_clock_hours` —
  each from its own source, missing as missing. It is populated only when
  the plan's context accounting is recoverable at emission time; when it
  is not, `context_accounting` is `{"available": false}` with all four
  values `null` — never synthesized, never estimated. The token, cost and
  wall-clock values duplicate their dedicated sections (`metered`,
  `timing`) by construction: they are the same recordings, carried once
  more so the four-quantity economy reads as one unit.
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
timing  { first_event_ts, last_event_ts, span_seconds, task_count_spanned,
          task_spans[] (optional: task, start_ts, end_ts, span_seconds) }
shape   { tasks, criteria, invariants, gate_intents, events }
friction{ adaptations, amendments, interventions, refusals, retries }
gates   { runs, exit_0, exit_nonzero, evidence_histogram }
metered { flag, tokens, spend_usd }
environment { repo, branch }
diff_stats  { available, files, insertions, deletions }
context_accounting (optional: available, instruction_bytes,
                    provider_tokens, cost_usd, wall_clock_hours)
```

The schema's closed-object style follows the house convention. Adding a
field is a schema revision (v2), never an in-place edit — with exactly one
recorded exception: `timing.task_spans` and `context_accounting` were
added to the v1 schema as **optional** fields during the pre-release
window, before any released pack had minted the v1 `$id` URL. The
exception is legitimate only because no consumer of v1 could exist when
the fields landed, and only because the fields are optional — every
record committed under the earlier v1 bytes still validates unchanged.
After the first release carrying this schema, the v2 rule applies without
exception (the decision is recorded in `docs/adr/0005-field-learnings.md`
in the skill repository).

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
  with `generation: "v5", metrics: "not_collected"`. A v6 plan folder
  whose repository had learnings off carries no `learnings.json`; in the
  learnings digest (below) such plans are listed with
  `learnings: "not_collected"` — absent evidence is named, never guessed.
- Output is **descriptive**: grouped by DWP skill version, then repository;
  per group — plan count, aggregate counts, span distribution
  (min/median/max), gate failure ratio, metered coverage. The report MUST
  carry this note verbatim: *aggregates describe recorded executions;
  workloads differ across plans, repositories and versions — this is
  evidence for discussion, not a causal comparison*.
- **Learnings digest.** When at least one input plan carries a
  `learnings.json`, the aggregate output additionally contains a learnings
  digest: curated entries grouped by DWP skill version, then category
  (the closed vocabulary of §10), with counts per category; within each
  version, the sections named by anchors are ranked by how many entries
  anchor to them (most-flagged first); entries whose anchor is `null` are
  listed separately as **unanchored** — never folded into a section, never
  dropped. Derived entries participate only as per-version friction-event
  counts already reported by the metrics half; they are never categorized
  (only curated entries carry a category). The digest carries the same
  verbatim non-causality note as the metrics groups.
- `--csv` rows gain one column per learnings quantity (total curated
  entries, per-category counts, unanchored count), `0` for plans without
  `learnings.json`; column order is fixed and row order stays plan
  identity sort.
- A version-over-version table appears only when ≥ 2 skill versions are
  present, and only with the note above.
- `--csv` writes one row per plan (the JSON record flattened) for offline
  analysis. `--out` defaults to stdout; when a file is written inside a
  git-tracked tree, it happens only because the user explicitly passed the
  path. The aggregator never writes into any `.dwp/` other than stdout
  redirection the user performs.

## 7. Privacy and security boundary

- Record fields are limited to: repository **name** (basename), branch,
  plan identity, timestamps, counts, versions, metered totals, and — for
  the learnings record — anchors (journal `seq` plus an optional section
  identifier) and the recorded reason text already present in journal
  events. The subsystem MUST NOT record: environment variable values,
  secrets, credential names, prompt or file contents, absolute user
  paths, or any token of a prompt/context byte stream.
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

## 10. Learnings (opt-in under benchmark)

Learnings are the qualitative half of the field record: what the execution
learned about the method itself. They ride on the benchmark subsystem and
share its opt-in stance — with `"learnings": true` required **in addition
to** `"enabled": true` (§1). A repository with learnings off (the default)
MUST produce no `learnings.json` and MUST NOT alter any other artifact.

### 10.1 Artifacts

- `<plan>/analysis_results/learnings.json` — the machine record, validating
  against
  [`schema/learnings-record.schema.json`](schema/learnings-record.schema.json)
  (`https://deepworkplan.com/schema/learnings-record/v1.json`).
- `DWP_REPORT.md` renders the learnings alongside the metrics (§2); it is
  the only human-facing artifact of either half.

### 10.2 The two halves

The learnings record has two halves with different disciplines:

- **Derived** (deterministic, regenerated on every run): one entry per
  friction event the journal already explains — each `adaptation`,
  `intervention` and `refusal` event, and each `gate_run` with a non-zero
  exit. An entry carries the event's `seq`, its `event_type`, and the
  event's **recorded reason, verbatim** (for a failing `gate_run`, its
  recorded exit outcome). The helper MUST NOT paraphrase, summarize,
  categorize or invent derived reasons — copying is the whole
  transformation. Derived entries never carry a category; categorization
  is judgment, and this half is mechanical.
- **Curated** (agent judgment, written once): entries the executing agent
  authors at or after the friction they interpret, each with a stable
  `id` (`LRN-nnn`), exactly one **category** from the closed vocabulary
  (10.4), an **anchor** (10.3), a `finding` (what happened, one or more
  sentences) and a `proposal` (what a future version could do about it).
  Curation MUST NOT restate what the derived half already carries
  mechanically; a curated entry exists to interpret, not to duplicate.

### 10.3 Anchor grammar

An anchor names where the learning attaches, in terms a future version's
diff can still resolve:

- `seq`: a journal event sequence number (integer ≥ 1) — the preferred
  anchor; it is immutable and unique within the plan.
- `section`: an optional short section identifier (≤ 64 characters, no
  paths) naming the document section the finding concerns — e.g. a task
  file section, a spec section number, or a skill heading stem.
- At least one of `seq` / `section` MUST be present for an anchored entry;
  an entry that has neither records `"anchor": null` and is **unanchored**
  — preserved and reported, never guessed into a section by proximity.
- Anchors MUST NOT contain repository paths, absolute paths, hostnames or
  user names (§7 carries over).

### 10.4 Closed category vocabulary (v1)

Every curated entry carries exactly one category from:

| Category | Means |
|---|---|
| `spec-gap` | the specification did not cover a situation the execution met |
| `instruction-gap` | the plan's own instructions were ambiguous, missing or misleading |
| `tooling-gap` | a shipped helper or template lacked a needed capability |
| `docs-gap` | companion documentation was stale, wrong or absent |
| `gate-false-positive` | a validation gate failed on correct behavior |
| `gate-false-negative` | a validation gap let a defect through |
| `context-miss` | context the agent needed was not where the method said it would be |

The vocabulary is closed: adding a category is a schema revision, and an
entry that fits no category is `instruction-gap` on the authoring surface
or unanchored with the mismatch stated in the `finding` — never a new
ad-hoc category.

### 10.5 Written-once (curated half only)

Re-running `report` on a plan that already carries a `learnings.json`
MUST regenerate the derived half in place and MUST preserve every curated
entry byte-for-byte — never regenerated, overwritten, merged,
deduplicated or renumbered. The helper's only curated-half write happens
when `learnings.json` does not yet exist; it creates the file with the
curated entries serialized deterministically (fixed key order, sorted by
`id`). Curation afterwards belongs to the agent and the maintainer, by
editing the file; the helper treats existing curated content as opaque.

### 10.6 Determinism split

The two halves make the determinism contract (§8) a split statement: two
`report` runs over identical plan bytes produce byte-identical
`benchmark.json` and byte-identical **derived** learnings content, while
the curated half is preserved rather than regenerated (10.5). A rerun
that changed curated bytes would be a defect; a rerun that failed to
refresh derived bytes would be the same defect.

### 10.7 Render rule

`DWP_REPORT.md` renders both halves of both records: metrics, per-task
spans where present, context accounting, the derived friction list, and
the curated table with anchors. It MUST NOT contain any number, entry,
category or anchor absent from the JSON files. The learnings categories
in the rendered report are exactly the closed vocabulary — the renderer
does not invent display categories.
