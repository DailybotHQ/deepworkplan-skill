# ADR 0002 — Plan-state file format: retain JSON, ship a targeted updater

| Field | Value |
|-------|-------|
| **Status** | Accepted (applied on `feat/v5-phase2`) |
| **Date** | 2026-09-12 |
| **Skill baseline** | `ab1337d` (released `v5.0.0`) |
| **Scope** | `skills/deepworkplan/spec/` (state-layer contract), `skills/deepworkplan/shared/` (new updater), flow texts that instruct `state.json` writes |
| **Relates to** | [ADR 0001](0001-token-efficiency-architecture.md) (token-efficiency architecture — same governing principle) |
| **Supersedes** | — (first decision on plan-file syntax) |

## 1. Context

DWP plans carry two JSON artifacts: `manifest.json` (identity, written once at
create) and `state.json` (live execution state, updated at every protocol
point). A 2026-09-12 review asked whether a more agent-friendly serialization
— specifically **TOON** (Token-Oriented Object Notation, spec v4.1), alongside
TOML, YAML, and JSONL/per-task splits — would materially cut token cost for
long plans. The review measured the predecessor 25-task plan's files directly
(filesystem bytes; no token or cost conversions) and evaluated each candidate
against the pack's hard floors.

### 1.1 Measured reality (predecessor plan, 25 tasks completed)

| Fact | Value |
|------|-------|
| `manifest.json` | 331 B, 10 lines — written **once**, read by 11 skill/spec surfaces |
| `state.json` | 60,329 B, 1,194 lines — whole-file rewritten at every protocol point |
| Composition of `state.json` | per-task `gates[]` evidence 56% · bare task skeleton 11% · outcome/timestamps/commit 33% |
| Agent-emit across the plan's life | ≈ 843 KB — **quadratic**: at task *k* the executor re-emits ≈ 6.7 KB + 2.26 KB·k, so every evidence string is re-emitted once per later completion |
| Compact-JSON bracket on the same file | 48,425 B = 20% byte saving (the honest floor any whitespace-based swap at least matches) |
| Key-elimination (tabular) bracket | ≈ 33 KB ≈ 45% byte saving |
| Verifier parse floor | `verify/conformance.sh` → `plan_contract.py` reads both files with **Python 3.9+ stdlib `json`** — the honest-verifier contract (no capable interpreter → exit 2 `UNVERIFIED`) |

## 2. Decision

1. **`manifest.json` and `state.json` stay JSON.** Schemas
   (`spec/schema/plan-{manifest,state}-v2.schema.json`), the verifier, and all
   32 documentation surfaces are unchanged.
2. **The pack ships a targeted state updater** —
   `skills/deepworkplan/shared/update-state.py`, stdlib-only (Python 3.9+),
   atomic (temp file + rename), idempotent modulo timestamps — so an executor
   applies a task close as a bounded delta (status, gate records, outcome,
   commit, counts, checkpoint) instead of re-emitting the whole file.
   Emit cost across the same 25-task plan drops from ≈ 843 KB to ≈ 62 KB
   (**−93%**), removing the quadratic term entirely: evidence is emitted
   exactly once, when earned.
3. **Flow texts point at it.** `execute` (task close), `resume` (update-order
   tail), and `spec/PLAN_STATE.md` §5.1 teach the one-line invocation; a
   whole-file rewrite remains the documented fallback, and markdown-wins
   reconciliation (§5) stays a whole-file regeneration by design.

## 3. Why the alternatives lost

- **TOON** — no stdlib parser in any language (official SDK is TypeScript;
  the Python implementation is a separate, unverified package), spec v4.1
  self-describes as "an idea in progress", multi-line string escaping is
  unspecified, and DWP's `tasks[]` is *semi-uniform* (optional keys, 0–4
  gates, evidence strings containing commas/colons/quotes) — exactly the shape
  their own limitations section says shrinks or reverses savings. It optimizes
  files *fed into prompts*; DWP state files are *emitted by agents and read by
  tooling*. Breaking the verifier's stdlib floor would convert the honesty
  guarantee into an install step.
- **TOML** — `tomllib` is 3.11+ and read-only; below the 3.9 floor there is no
  stdlib story at all.
- **YAML** — a PyYAML dependency plus the classic indentation failure mode
  under agent edits, for the same whole-file rewrite cost.
- **JSONL / per-task split** — keeps stdlib parsing and makes emits O(task),
  but sacrifices closed top-level invariants (`completed_count`, derived plan
  status) and restructures every consumer for a benefit the updater already
  delivers against the unchanged layout.
- **Pure syntax swap (compact JSON)** — the 20–45% byte bracket shrinks the
  base but keeps the quadratic emit term; the updater removes it.

The governing principle is ADR 0001's: **compress the scaffolding, never the
instructions.** The cost was never JSON's syntax; it was the whole-file
rewrite pattern.

## 4. Consequences

- Executors emit one bounded delta per completion; gate evidence stops being
  re-emitted by every later task.
- New runtime surface: one script inside the pack (`shared/update-state.py`),
  covered by contract tests (`tests/state-updater.bats`) that run the real
  script against a fixture plan and assert schema validity, atomicity, and
  idempotence modulo timestamps.
- The updater never authors plan-level `blocked` (that record carries a reason
  and timestamp owned by the blocked protocol), never touches `manifest.json`,
  and never invents fields — its output validates against the closed v2 schema
  wherever its input did.
- Markdown remains the source of truth; reconciliation stays whole-file by
  design (PLAN_STATE.md §5).

## 5. What would reopen this decision

- TOON (or a successor) ships a **stdlib-grade or vendored-zero-dependency
  Python parser with write support** and schema tooling, and freezes
  multi-line string escaping; or
- plan files become agent-*read* hot paths whose bytes actually enter prompts
  (e.g. a future flow inlining state into prompts); or
- measurements (the evaluation record's reproduce commands, plus the updater's
  own usage) show agents bypassing the updater and still whole-file rewriting —
  then a harder structural change (per-task split) reopens.

Unverified and quarantined as such: the exact TOON byte delta on a real
`state.json` (no stdlib encoder available to measure honestly — the 20%/45%
figures are JSON-compact and key-elimination arithmetic, not a TOON
measurement) and `toon-python`'s PyPI name/version/write support.
