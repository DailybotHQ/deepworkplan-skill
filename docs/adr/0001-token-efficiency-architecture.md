# ADR 0001 — Token-efficiency architecture for Deep Work Plans

| Field | Value |
|-------|-------|
| **Status** | Accepted (design ratified before implementation) |
| **Date** | 2026-09-09 |
| **Skill baseline** | `eaf54994ac5894b74849f1b8d2b6137df8d83e30` (v2.17.1) |
| **Website baseline** | `661c431108e5704fa3f46a35ad9744b94845f6d9` |
| **Scope** | `skills/deepworkplan/` (the installed runtime) and its two dogfood consumers |
| **Supersedes** | — (first ADR in this repository) |

## 1. Context

After months of production use, Deep Work Plan (DWP) executes reliably but pays
avoidable cost on every plan: the whole methodology guide is loaded to write an
ordinary task; the full test suite runs after every task; two mandatory closing
tasks re-derive information that was in context when each task finished; the plan
is composed twice in trust mode; and the working log is re-read in full as it
grows. None of these costs buys quality. This ADR fixes the architecture that
removes them **without** reducing task detail, gate strength, or recoverability.

Governing principle: **compress the scaffolding, never the instructions.** Savings
come from loading less, repeating less, and running expensive gates once — never
from vaguer plans or terser requirements.

### 1.1 Reproduced baseline (filesystem bytes, not tokens)

Measured at the skill baseline above (`wc -c`):

| Artifact | Bytes |
|---|---:|
| `guide/GUIDE.md` | 99,480 |
| — of which §13 Orchestrator | 34,339 |
| — of which §14 Team agents | 11,062 |
| — of which §7–§9 create/execute/resume prompts | 8,406 |
| `onboard/SKILL.md` | 46,078 |
| `create/SKILL.md` | 22,637 |
| `execute/SKILL.md` | 19,618 |
| `refine/SKILL.md` | 6,831 |
| All installed Markdown | 738,989 |

Compulsory read set today (router + sub-skill + guide + examples): **~140.6 KB for
a `create` run** and **~126.6 KB for an `execute` run**. Byte counts divided by
four are an *estimate* of tokens, never a measurement; Task 2 reproduces these
figures with a stored command and Task 19 reports live counters only where a
harness exposes them.

## 2. Decisions

### 2.1 Operational capability floor

The portable methodology requires exactly: (a) the ability to discover and read
the skill's instruction files; (b) read/write access to the repository; (c) the
ability to run the repository's validation commands; (d) durable local files for
plan state. **Git is conditional**: when present, per-task commits and the git
log are the traceability and recovery channel; when absent, the state layer
(`state.json`) is REQUIRED and carries recovery. Hooks, slash commands,
subagents, provider caches, proprietary task APIs and paid services are
**optional enhancements with a working sequential fallback** — never a core
requirement. A missing optional tool is a recorded finding, not a question.

### 2.2 Task granularity

A task is **one coherent outcome** with a bounded write surface, concrete inputs
and outputs, validation relevant to what it changes, and partial steps that can
be checkpointed and resumed. Split when two outcomes have different failure
modes or independent deliverables that would otherwise hide behind one checkbox;
keep tightly coupled edits together. There is **no task-count quota** and no
mandatory multiplication of files, approvals, commits or reports.

### 2.3 Fluent execution

Fluency means, measurably: fewer approval requests inside an already granted
authorization; fewer repeated reads of unchanged material; fewer repeated gates on
equivalent inputs; and faster, correct recovery after interruption. `trust`
removes *confirmations*, not *permissions*: it never authorizes outward-facing
writes the plan did not list, and never upgrades an in-flight legacy plan.

### 2.4 The five levers

For each lever: mechanism · expected benefit · failure mode · recovery/safety rule
· how the benefit is falsified.

**L1 — Conditional instruction loading (progressive disclosure).**
Split the guide into flow-scoped section files behind a routing index; each
sub-skill declares its read scope; orchestrator and team-agents branches inside
`create`/`execute` move verbatim to on-demand files behind an explicit trigger.
*Benefit:* ≥40% fewer compulsory guide bytes on ordinary `create`/`execute`
paths (ratified target; Task 19 reports the measured figure). *Failure mode:* a
flow fails to load a section it needed. *Safety rule:* every moved requirement
keeps a direct link from the place that needs it; a link-resolution gate and a
line-level content-preservation gate run on the split (Task 7). *Falsified if:*
any requirement is unreachable from its consuming flow, or measured compulsory
bytes drop by less than the target.

**L2 — Affected validation.**
Each code-changing task declares its planned surface, reconciles it against the
actual diff after editing, and selects validation by **effect**: unit tests for
the changed behavior plus tests of affected consumers, integration/contract tests
at real seams, and a widening to the documented broader or full command when the
impact cannot be bounded reliably (shared/core code, toolchain or configuration
changes, schema changes, dynamic loading, zero selected tests, unverified
selector). Prefer the repository's verified affected-test tooling over ad-hoc
dependent heuristics; document its blind spots. **Full validation is a
final-state requirement** — it runs once on the final inputs (Final Review) and
earlier at integration boundaries or when risk warrants it, not on a fixed
cadence. *Benefit:* N full runs per plan become 1 plus risk-driven widenings.
*Failure mode:* a cross-module regression surfaces late. *Safety rule:* zero
selected tests is never evidence; no `--passWithNoTests`, skips or weakened
assertions; pre-existing failures and missing tools are recorded as such. A repo
with no documented scoped invocation falls back to the full suite by rule.
*Falsified if:* a seeded consumer-side fault (Task 2 fixture `shared-core-change`)
escapes the selected gate and is caught only by the final gate.

**L3 — Task-local learning and optional reporting.**
Skills decisions happen inside the owning task, before its validation and commit,
recorded by stable ID in `analysis_results/SKILLS_CANDIDATES.md` (`none` is a
valid disposition). The single mandatory Final Review checks ledger completeness
and disposition; it does not rediscover the plan. The Executive Report becomes an
on-request artifact with unchanged content, offered once at completion; an
unanswered offer never blocks. In unattended runs it is not generated by default.
*Benefit:* removes the end-of-plan re-read (~10–18k estimated tokens) and the
always-on report (~3–6k output plus its inputs). *Failure mode:* reusable patterns
go unrecorded. *Safety rule:* every task log carries an explicit disposition;
Final Review fails on a missing disposition. *Falsified if:* Task 18's evaluation
finds a warranted pattern with no ledger entry.

**L4 — Direct trust-mode creation.**
In trust mode the plan folder is materialized directly; guided mode keeps the
reviewable refined draft; explicit `refined-draft` / `from-refined-draft` modes
are unchanged. The requirements analysis and plan-quality checks that the draft
step performed are retained as internal steps. **`trust` is plan approval** for
unattended execution (`AGENT_PROTOCOL` §7.2). *Benefit:* the plan's substance is
composed once. *Failure mode:* a lower-quality plan slips through without review.
*Safety rule:* the same quality gates run on the materialized plan (numbering,
gates present, acceptance criteria present, links resolve). *Falsified if:* Task 18
scores trust-mode plans lower than guided-mode plans on the same fixture.
>
> **Superseded by DWP 2.4.0:** the refined draft, `.dwp/drafts/` and the
> explicit draft modes were removed; `create` materializes an executable Lite
> plan instead. This record is kept as the decision that was current at the time.

**L5 — Bounded working context backed by durable evidence.**
`PROGRESS.md` becomes a working index (goal/constraints, active task and next
action, unresolved blockers, current contracts, direct pointers to durable
decisions) with a soft budget of ~1,000 words; completed detail lives in task logs
and decision records and is retrieved by task, topic or dependency. Re-anchoring
reads the index, the relevant `state.json` entries and the active task plus its
named dependencies — not the whole history. *Benefit:* re-anchoring cost stops
growing with plan length. *Failure mode:* a needed decision is not in working
memory. *Safety rule:* unresolved constraints and active contracts are never
discarded to meet the budget; unknown or stale pointers trigger retrieval, never
guessing; resume after a revision change, handoff or compaction re-reads.
*Falsified if:* the `long-history-plan` fixture (50 entries) loses a decision on
cold resume.

### 2.5 Validation selection algorithm (normative input for Task 3)

1. Before editing: record planned surface and the candidate gate.
2. After editing: reconcile against the actual diff (staged, unstaged, generated).
3. Classify each change by **effect**, not extension: isolated implementation;
   contract/persistence/routing/serialization/auth/wiring; shared/core,
   toolchain/config, dependency or schema; pure prose.
4. Select: unit + affected-consumer tests and targeted static checks → add
   integration/contract tests at seams → widen to affected packages and
   transitive consumers, or full validation when impact cannot be bounded →
   prose gets link/schema/render checks with an explicit "runtime tests not
   applicable" record.
5. Defend against false confidence: zero selected tests, unknown mapping,
   dynamic loading or an unverified selector ⇒ investigate, then use the
   documented broader/full command.
6. Record one compact gate record (command, cwd, scope/reason, revision or
   fingerprint, exit code, selected/executed counts where available, evidence
   path). Reuse a passing result only with evidence of equivalent inputs.
7. Final state: run the applicable complete gate set after the last substantive
   change; later fixes invalidate affected evidence.

### 2.6 Minimal recovery and evidence contract (normative input for Tasks 4–5, 8–11)

- **Markdown authority.** README checkboxes, task logs and `PROGRESS.md` are the
  execution record; `state.json` is a projection regenerated after them. A fast
  JSON read never authorizes skipping unfinished Markdown work.
- **Write order and interruption.** Persist at task/step boundaries: task log →
  README → `state.json` (atomic replace). Materialization is resumable at any
  point: `manifest.json` first, a README skeleton with the intended task list and
  `Plan Status: materializing` second, `analysis_results/PLAN_ANALYSIS.md` third,
  task files next, and the status line flipped to `0/N completed` last — so an
  interrupted `create` leaves its shape and reasoning on disk instead of a
  half-written folder nobody can interpret. On interruption between validation,
  commit, README update and state update, inspect actual evidence (git, files)
  before replaying anything; never duplicate a commit, skill, external write or
  report.
- **Stale evidence.** A plan edit (`refine`) or a later fix invalidates gate
  results whose inputs changed, even if the checkbox is set.
- **Active decisions and pointers.** Decisions that still constrain work live in
  the working index; everything else is a pointer to a durable record.
- **Bounded retry.** After two fix attempts without new evidence, stop blind
  retries: diagnose from the stored failure, change approach, or record an
  actionable blocker (`state.json.blocked`).
- **Task-local skill disposition.** Recorded in the task log and ledger before the
  task's gate runs.
- **Unattended stops.** Only `AGENT_PROTOCOL` §7.3 boundaries stop a run; a
  materialized-with-`trust` plan is pre-approved.

### 2.7 Compatibility matrix and version policy

| Case | Policy |
|---|---|
| Old plan (three final tasks, no Touched Surface) / new executor | **Supported.** Executes under its own recorded shape; conformance accepts the legacy shape; no mid-flight retrofit. |
| Old repo (no scoped-test docs) / new onboard | **Supported.** Reconcile narrowly and non-destructively; until then plans fall back to full-suite gates by rule; missing scoped docs are a finding. |
| New plan / new executor | **Supported** — the target. |
| New plan / old executor | **Not supported; documented honestly.** An old executor expects three final tasks and will report the new shape as non-conformant. |

**Schemas.** Both v1 schemas declare `additionalProperties: false` at the top
level, so an "optional" new top-level field is **not** compatible with existing
validators. Policy: the v1 schema URLs are frozen; new per-task information goes
inside task entries (unconstrained in v1); any genuinely new top-level field ships
as a `v2` schema URL published alongside v1, with the `schema` field selecting
it. Task 5 decides whether a v2 schema is needed at all.

**Spec documents.** Each amended RFC document bumps its own "Status of This
Document" version by a **minor** (additive with back-compat); the manifest's
`spec_version` example values follow. Package SemVer, spec version and schema URL
version are three separate things and are never conflated.

**Package release.** Version fields and `CHANGELOG.md` are owned by
`auto-release.yml`. The commits in this change are additive with documented
back-compat, so their justified Conventional-Commit semantics are `feat:` (minor).
No commit uses `!` or a `BREAKING CHANGE:` footer unless a genuine public break
is discovered — in which case it is recorded and released as such, not disguised.

**Provenance, not pins.** `skills-lock.json` records a `computedHash`, not a
release pin. Downstream consumers record source commit, tree digest and local
adaptations in a tracked provenance document; the lock is updated only through a
verified compatible mechanism.

### 2.8 Unit-first testing posture

Fast, deterministic unit tests around observable behavior and meaningful
boundaries form the base; integration tests cover real collaborators, protocols,
storage and framework wiring; end-to-end tests are few and high-value. The
pyramid is a default cost/risk strategy, not a fixed ratio or a millisecond SLA.
It is also what makes L2 honest: affected validation is only fast when the unit
base is fast. Prompt procedures stored as Markdown are executable instructions;
behavioral scenarios (Tasks 2, 18–20) test them — frontmatter checks do not.

## 3. Rejected or limited alternatives

| Alternative | Verdict | Reason |
|---|---|---|
| Wholesale prose compression of instructions (caveman-style) | **Rejected** as a mechanism | Compresses the layer whose precision *is* the plan's value; its own documentation shows conditional savings (a browsing case +9.9%). Its output-style skill and input proxy are different experiments and are not imported as a DWP savings claim. Reversible log filtering and retrieval are evaluated on their merits. |
| Coarser plans / fewer tasks | **Rejected** | Hides independent failure modes behind one checkbox; loses recoverability. Granularity is a quality property. |
| Dropping the mandatory final review | **Rejected** | The security pass and final-state validation are the last line against accumulated risk. |
| Mandatory external proxy or store for context | **Rejected** | Adds a runtime dependency and a paid/opaque baseline for every downstream user. |
| Automatic low-reasoning models as a token optimization | **Rejected** | Trades reasoning quality for cost; forbidden by the quality contract. |
| Arbitrary periodic full test runs (every K tasks) | **Rejected** | Cadence is not risk; widening is driven by change effect and integration boundaries. |
| Deduplicating task-file context into README pointers | **Rejected** | Breaks the self-contained-task invariant a cold agent relies on; deep reference chains are the failure mode L5 guards against. |
| Concise wording with direct references | **Allowed** | When it demonstrably preserves every requirement and the reference is one hop away. |

## 4. Targets and falsification

Ratified initial targets (Task 2 fixes the baseline; Task 19 reports):

- ≥40% fewer compulsory guide bytes on ordinary `create` and `execute` paths.
- Zero requirements lost in the guide split (line-level preservation gate).
- No duplicate full gate on equivalent unchanged inputs.
- No failed must-pass scenario; every seeded relevant defect detected at its
  intended boundary.
- Live token and wall-clock figures are reported from the baseline comparison,
  separately for cold and warm runs, with failures and retries included — never
  achieved by removing necessary tests or reducing task detail.

If the candidate is worse in any scenario, that optimization is revised or the
claim narrowed. No universal-losslessness or market-superiority claim follows.

## 5. Consequences

- Implementation tasks (spec, guide, sub-skills, onboarding, presets, conformance)
  execute this design without weakening a gate or compressing an instruction.
- Existing plans and repositories keep working; the new shape is opt-in by
  creating a new plan or re-onboarding.
- The website mirrors the amended standard and states only measured claims.
