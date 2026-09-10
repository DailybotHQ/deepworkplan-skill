# DWP_SPECIFICATION.md — Deep Work Plan Specification

## Abstract

This document specifies the **Deep Work Plan (DWP)** workflow: a framework-agnostic,
agent-agnostic methodology for AI coding agents to execute complex, multi-step work
reliably over hours or days. A Deep Work Plan is a directory of markdown files — a
plan overview, per-task instruction files, a running progress log, and utility
prompts — that together hold all state an agent needs to begin, continue, and
complete a body of work. Plans are single-task focused, validation-first,
git-native, and resume-safe.

The DWP system in v2 is delivered as an **installable skill** (`deepworkplan`,
modeled on the `dailybot` skill in `repositories/agent-skill`), not an embedded
per-repo folder. Its outputs land in a gitignored **`.dwp/`** directory at repo
root. This document is implementation-independent; `deepworkplan` is the reference
implementation.

This specification applies to **all three archetypes** (`ARCHETYPES.md`): the
individual repo (the default case), the orchestrator hub, and the agent
workspace. Archetype-specific behavior is called out inline, especially in §8
(orchestrator) and §10 (state layer, required where git is absent).

---

## Status of This Document

| Field | Value |
|-------|-------|
| **Version** | 2.3.0 |
| **Status** | Stable |
| **Supersedes** | `DWP_SPECIFICATION.md` 2.2.0; `PLAN_build_deepworkplan_brand/.../deepworkplan/spec/DWP_SPECIFICATION.md` (v1.0.0) |
| **Companions** | `DOCUMENTATION_STANDARD.md`, `AGENT_PROTOCOL.md`, `ARCHETYPES.md`, `ADDONS.md`, `PLAN_STATE.md` |
| **License** | MIT |

> **Additive in 2.2.0.** Four additive capabilities, no breaking changes:
> (1) the **machine-readable plan state layer** (`manifest.json` + `state.json`,
> §10, normatively defined in `PLAN_STATE.md`); (2) **proportional rigor tiers**
> (micro / standard / deep, §11); (3) the optional **Delta section** in the task
> anatomy for brownfield behavior changes (§5); and (4) §5.3 is promoted to the
> named, citable **DWP Resume Protocol**. Existing 2.1.0 plans remain conformant.

> **Divergence from 2.2.0 (overview).** 2.3.0 is additive with compatibility:
> (1) the **Touched Surface** and gate selection by risk class, with full
> validation as a final-state requirement (§5); (2) one mandatory **Final
> Review** replacing the three closing tasks, with skills decisions made in the
> owning task and an optional, on-request Executive Report (§6); (3) a
> **mode-aware** create flow — trust mode materializes directly (§3); (4) task
> size, adaptive execution, and an explicit compatibility matrix (§6.4–§6.5).
> Plans and repositories from 2.2.0 remain conformant (§6.5).

> **Divergence from v1 (overview).** Three breaking changes drive the major bump:
> (1) the **create flow is single-step** — one refined draft, dropping the v1
> draft → refined two-step (`RECONCILIATION.md` divergence #3); (2) plan output
> relocates to **`.dwp/`** at repo root, replacing
> `.agent_commands/agent_deep_work_plans/results/plans/` (divergence #2); (3) the
> system is an **installed skill**, not an embedded folder (divergence #1). The
> task anatomy, validation gates, completion protocol, mandatory final tasks,
> orchestrator, and team-agents model are **kept** from v1 with path/flow edits.

---

## 1. Conventions and Terminology

### 1.1. RFC 2119 Keywords

The keywords **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** are to be
interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

### 1.2. Terms

| Term | Definition |
|------|-----------|
| **Plan** | A directory of markdown files specifying an objective and its tasks. Named `PLAN_{snake_case_name}/`. |
| **Task** | An atomic unit of work, defined in `{N}.task_{title}.md`. |
| **Refined draft** | The single reviewable artifact produced by `create` in guided mode (or on explicit request), written to `.dwp/drafts/`. Trust mode materializes the plan directly (§3). |
| **Plan README** | The `README.md` inside a plan; source of truth for "what is done". |
| **Final Review** | The single mandatory final task every new plan ends with: the security pass, the final-state validation, and the reconciliation of task-local skills decisions (§6.1). Plans authored under earlier versions end with three mandatory tasks and remain conformant (§6.5). |
| **Skills candidate** | A task-local record (stable ID, evidence, disposition) of a reusable pattern decided inside the owning task (§6.2). |
| **Executive Report** | An optional, on-request stakeholder artifact generated after completion (§6.3). |
| **Orchestrator plan** | A plan in an orchestrator hub that creates and coordinates **child DWPs** in sub-repos. |
| **`.dwp/`** | The gitignored repo-root output directory: `.dwp/plans/`, `.dwp/drafts/`. |

---

## 2. The `.dwp/` Output Convention

- A repository using the DWP workflow **MUST** locate all plans and drafts under a
  single repo-root directory named `.dwp/`:

  ```
  .dwp/
  ├── plans/      ← PLAN_{name}/ directories (executed plans)
  └── drafts/     ← PLAN_{name}_draft_refined.md (the create-flow artifact)
  ```

- `.dwp/` **MUST** be git-ignored (added to the repo's `.gitignore`). Plan
  execution artifacts are working state, not tracked deliverables.
- The legacy `.agent_commands/agent_deep_work_plans/results/` tree **MUST NOT** be
  used by v2 plans. On migration, existing plans **MUST** be relocated or archived,
  and **MUST NOT** be blind-deleted (`ORCHESTRATOR_MANIFEST.md` key decision).
- A plan **MUST** be located at `.dwp/plans/PLAN_{name}/`.

> **Divergence from v1.** v1's normative spec mandated
> `.agent_commands/agent_deep_work_plans/results/plans/PLAN_{name}/` even though the
> v1 `dwp-create` command and INIT hint already used `.dwp/`. v2 makes the spec and
> the commands consistent on `.dwp/` (`RECONCILIATION.md` divergence #2).

---

## 3. The Create Flow — Single Step, Mode-Aware

The `create` flow gathers the objective, context, constraints, and task outline
once, performs its **requirements analysis** (scope, dependency ordering between
tasks, validation selection per §5, proportional-rigor tier per §11), and then
materializes according to the mode the developer chose:

- **Guided mode (default).** The flow **MUST** produce exactly **one** artifact
  for user review: a **refined draft** written to
  `.dwp/drafts/PLAN_{name}_draft_refined.md`, containing enough structure (goal,
  context, variables, task outline, archetype, tier) for the user to approve or
  request changes in one pass. The plan folder `.dwp/plans/PLAN_{name}/` is
  materialized only after approval.
- **Trust mode (`trust` / `auto`).** The flow **MAY** materialize
  `.dwp/plans/PLAN_{name}/` **directly**, without writing a draft file, because
  the developer has waived the intermediate review. The requirements analysis,
  dependency ordering, and a **plan-quality check** (numbering, links, every task
  carrying acceptance criteria and a validation gate, the Final Review present)
  **MUST** still run — trust waives the *review*, not the *analysis*. The approved
  objective, context, and task outline are captured in the plan README (§4), so
  nothing reviewable is lost. A plan materialized with `trust` is **pre-approved**
  for unattended execution (`AGENT_PROTOCOL.md` §7.2).
- **Explicit draft modes.** `refined-draft {name}` (produce only the draft) and
  `from-refined-draft {file}` (materialize from an existing draft) **MUST** remain
  available in both modes; a developer who asks for a draft gets one.

In every mode the flow **MUST NOT** produce an intermediate non-refined draft as
a separate reviewable step. The legacy `[1/3] Creating draft → [2/3] Refining
draft` sequence is removed.

> **Divergence from v1.** v1's `dwp-create` was explicitly two-step. v2 collapses
> it to a single refined draft (`RECONCILIATION.md` divergence #3).
> **Divergence from v2.2.** v2.2 required the refined draft in every mode; v2.3
> makes the flow mode-aware — trust mode materializes directly while keeping the
> analysis and quality check — so the plan's substance is composed once.

---

## 4. Plan Folder Structure

A conformant plan directory **MUST** contain:

```text
.dwp/plans/PLAN_{name}/
├── README.md                              ← overview, task list, rules, status (source of truth)
├── PROMPTS.md                             ← copy-paste execute / resume / status prompts
├── PROGRESS.md                            ← running narrative, one entry per completed task
├── analysis_results/                      ← task-produced artifacts (MAY start empty)
│   ├── SKILLS_CANDIDATES.md               ← task-local skills decisions ledger (§6.2)
│   ├── SECURITY_REVIEW.md                 ← written by the Final Review (§6.1)
│   └── EXECUTIVE_REPORT.md                ← OPTIONAL, on request after completion (§6.3)
├── 1.task_{title}.md                      ← first user-defined task
├── …
└── {N}.task_final_review.md               ← mandatory: last (§6.1)
```

> Plans authored under earlier versions end with
> `{N-2}.task_security_review.md`, `{N-1}.task_skills_agents_discovery.md`, and
> `{N}.task_executive_report.md` instead; that shape remains conformant (§6.5).

- Plan names **MUST** follow `PLAN_{snake_case_name}` (lowercase, underscore-separated, 2–5 words).
- `README.md`, `PROMPTS.md`, `PROGRESS.md`, and `analysis_results/` **MUST** all be present.
- At least one user-defined task plus the Final Review (§6.1) **MUST** be present in a plan authored under this version; the legacy three-task ending is accepted per §6.5.

The plan `README.md` **MUST** contain: title + goal; context; plan variables (if
the tasks reference `{{...}}`); global guidelines; a task list with checkboxes and a
`Plan Status: X/N completed` count; execution rules; and an analysis-outputs table.
The checkbox list is the resume checkpoint: `[x]` means complete-and-committed, and
the agent **MUST** trust `[x]` marks without re-verifying.

---

## 5. Task File Anatomy — The 10 Sections

Each `{N}.task_{title}.md` **MUST** contain the following ten sections. Heading
text **MAY** vary; the semantic content **MUST** be present and in this order.

| # | Section | Requirement |
|---|---------|-------------|
| 1 | **Title** — `# Task {N}: {Title}` | **MUST** |
| 2 | **Context** — task-specific background; the agent **MUST** be able to start from this section alone. | **MUST** |
| 3 | **Read Before Starting** — files the agent **MUST** read first, each with why it matters (including re-anchoring to the plan README §Goal). | **MUST** |
| 4 | **Goal** — 1–2 sentences, unambiguous and testable. | **MUST** |
| 5 | **Touched Surface** — the change's footprint and the validation it implies (§5.0.2): planned paths/modules; after editing, the reconciled actual paths; affected consumers; risk class; the test mapping used; the selected gate and its reason. | **MUST** for any task that changes behavior (code, configuration, schemas, templates, fixtures, migrations, generated inputs, or agent instructions that alter behavior); **MAY** state `not applicable` with a reason for pure prose or research tasks |
| 6 | **Instructions** — numbered, concrete steps, including an explicit **re-anchor** step (re-read the plan README §Goal at task start). Vague steps **MUST NOT** appear. | **MUST** |
| 7 | **Acceptance Criteria** — a verifiable checkbox list; the task **MUST NOT** be marked complete until every box can honestly be checked. | **MUST** |
| 8 | **Outputs** — table of files the task produces with paths (under `analysis_results/` or source). | **MUST** when the task produces artifacts |
| 9 | **Validation** — the stack-specific commands that **MUST** pass before completion, selected per §5.1 from the Touched Surface; a task with no automated command **MUST** carry a specific manual checklist. | **MUST** |
| 10 | **Execution Checklist** + **Completion & Log** — the procedural walk-through plus the post-task log the agent fills (status, timestamp, summary, outputs, validation results, notes). The log **MUST NOT** retain placeholder values after completion. | **MUST** |

A task **MAY** additionally include a **Rollback** section (RECOMMENDED for
migrations, breaking changes, infra, or deployment), a **Team Agents Metadata**
section when it participates in a parallel group (§9), and a **Delta** section
(§5.0.1, RECOMMENDED for brownfield behavior changes).

> **Legacy shape.** A task file authored under an earlier version of this
> specification carries nine sections and no Touched Surface. It remains
> conformant (§6.5) and is validated under the fallback rule of §5.1: the full
> applicable suite. An executor **MUST NOT** add a Touched Surface to a legacy
> task mid-flight; a `refine` session **MAY** add one deliberately.

### 5.0.1. The Delta Section (brownfield changes)

Most real work modifies existing behavior rather than creating new behavior. A
task that changes how an existing system behaves **SHOULD** carry a **Delta**
section describing the change as an explicit before/after contract, using three
list headings:

- **ADDED** — behavior that exists after the task and did not before.
- **MODIFIED** — behavior that exists in both, stated as `was: … → now: …`.
- **REMOVED** — behavior that existed before and is intentionally gone after.

Each entry **MUST** be observable behavior (an endpoint's response, a CLI flag, a
UI state, a default value) — not an implementation detail. The Delta section is
the reviewer's diff at the *behavior* level: acceptance criteria verify the
ADDED/MODIFIED entries, and the REMOVED entries are the explicit license to
delete — anything not listed as REMOVED **MUST** keep working, and the task's
validation gate (existing tests staying green, §5.1.1) is what enforces it.

> **Divergence from v1.** v1 specified the same content across ~11 numbered
> subsections (Title, Context, Read Before Starting, Goal, Instructions,
> Acceptance Criteria, Outputs, Validation, Rollback, Execution Checklist,
> Completion & Log). v2 consolidated to a **9-section canonical anatomy** —
> folding Rollback into optional and merging Execution Checklist with Completion &
> Log — and made the **re-anchoring** step explicit inside Instructions
> (`RECONCILIATION.md` §"Specs"). v2.3 adds the **Touched Surface** section
> (§5.0.2), making it ten. Content parity is preserved.

### 5.0.2. The Touched Surface Section

The Touched Surface is the contract between what a task changes and what must be
validated. It exists so that validation is **selected by effect**, not by habit,
and so that a later reader can see why a gate was chosen. A behavior-changing task
**MUST** record, in this section:

- **Planned surface** — the paths, modules, packages, or configuration the task
  intends to change, written before editing.
- **Actual surface** — the reconciled list after editing, taken from the real
  diff (staged, unstaged, and relevant untracked or generated files). The agent
  **MUST** reconcile the planned and actual surfaces before selecting the gate;
  a gate chosen from the planned surface alone is not valid evidence.
- **Affected consumers** — modules, packages, templates, or services that import,
  load, render, or otherwise depend on the actual surface, as far as the
  repository's documented mapping (`DOCUMENTATION_STANDARD.md` §3.1) or its
  affected-test tooling can establish. Where the mapping cannot establish them,
  the entry **MUST** say so and the risk class below **MUST** reflect it.
- **Risk class** — one of: *isolated* (the change is confined to one module and
  its own tests); *seam* (the change alters a contract, persistence, routing,
  serialization, authentication, or framework wiring between real collaborators);
  *shared/core* (the surface is imported or loaded widely, or is a dependency,
  migration, build/test configuration, schema, or toolchain change); *unknown*
  (the mapping is missing, stale, dynamic, or unverified).
- **Test mapping used** — which documented mapping or tool produced the selection
  (a file-to-test convention, a marker, an affected-tests command), and whether it
  was verified for this repository.
- **Selected gate and reason** — the exact commands in Validation and, in one
  line each, why they cover the actual surface and its consumers, or why the
  fallback (§5.1) was taken.

Configuration files, schemas, dependency manifests, templates, fixtures,
migrations, generated inputs, and agent instruction files **can change behavior**
and **MUST** be classified by their effect, never by file extension. A task that
changes only prose, comments, or research artifacts **MAY** declare
`Touched Surface: not applicable — <reason>` and still runs whatever
non-runtime checks the repository defines (links, schema, rendering).

### 5.1. Validation Gates

A task **MUST NOT** be marked complete unless every command in its Validation
section has been run and passed. On any failure the agent **MUST** stop, report the
command + output + suspected cause, **MUST NOT** mark the task complete, and **MUST**
await guidance — or, under the unattended profile (`AGENT_PROTOCOL.md` §7.2),
attempt a fix within the task's authorized scope and otherwise populate
`state.json.blocked` and halt (`AGENT_PROTOCOL.md` §7.3). Validation commands
**MUST** be runnable shell commands, deterministic, and scoped; they **MUST NOT**
require human judgment to interpret. The concrete commands are repo-specific (see
`DOCUMENTATION_STANDARD.md` §7) and **MUST** be reasoned about per repo.

When the repository has a test, lint, or type-check toolchain (per
`DOCUMENTATION_STANDARD.md` §7), a task that changes product behavior **MUST** run
the relevant suite as part of its validation gate. "It builds" or "the file
exists" is **NOT** a sufficient gate for a behavior change.

#### 5.1.a. Selecting the gate from the Touched Surface

The gate of a behavior-changing task **MUST** be selected from its reconciled
Touched Surface (§5.0.2), by risk class:

| Risk class | Required validation |
|---|---|
| *isolated* | The tests of the changed behavior **and** the tests of its affected consumers, plus the static checks (lint, type-check, format) that cover the actual surface. |
| *seam* | The above, **plus** the integration or contract tests for that seam — added in this task if none exist — and, where the repository defines one, a high-value user-flow check. Integration checks at a seam **MUST NOT** be deferred to the end of the plan. |
| *shared/core* | Widen to the affected packages and their transitive consumers; where the impact cannot be bounded reliably, run the repository's documented full validation. |
| *unknown* | Investigate and correct the selection (refresh the mapping, §5.1.b); if it still cannot be established, run the documented broader or full command. |
| *not applicable* (prose/research) | The repository's non-runtime checks (links, schema, content, rendering), with the reason runtime tests do not apply recorded in the Touched Surface. |

Selection **MUST** use the repository's verified mapping or affected-test tooling
where one exists, and **MUST** account for the blind spots such tooling has:
dynamic loading, templates, fixtures, generated inputs, and configuration are
not visible to static import analysis and require explicit handling or a broader
run. The agent **MUST NOT** approximate consumer coverage with an arbitrary
import-count threshold or with first-order dependents alone when the repository
offers a verified affected-test mechanism.

#### 5.1.b. Stale or missing test mapping

Where the repository's documented testing map (`DOCUMENTATION_STANDARD.md` §3.1)
is stale or lacks the command a task needs, and the correct invocation is
reasonably derivable from the actual tool configuration within the task's scope,
the agent **MUST** derive it, use it, and record the mapping update in the task
log (and in the testing guide when the task owns documentation). A small missing
command **MUST NOT** require a full onboarding run. Where no supported scoped
invocation exists or can be derived, the task **MUST** fall back to the
repository's full applicable suite. A repository or plan with **no** scope
contract at all — for example a plan authored before this version — is
validated with the full applicable suite; this is the legacy behavior and it is
never an error.

#### 5.1.c. Zero-test defense

A behavior change **MUST** produce a non-empty, relevant test selection. An
invalid selector, a missing tool, a filter that matches nothing, or a runner that
exits 0 having selected zero tests is **not** successful coverage; the agent
**MUST** investigate whether tests are genuinely absent (then §5.1.1 applies and
tests are added) or the filter is wrong (then it is corrected), and **MUST NOT**
use `--passWithNoTests`, skips, filtered failures, or weakened assertions to make
a gate pass. Pre-existing failures and missing tools **MUST** be recorded as such,
never as passing checks; the repository's existing waiver policy, where one is
documented, applies unchanged.

#### 5.1.d. Static checks

Lint, format, and type checks **SHOULD** run scoped to the actual surface where
the toolchain supports it, and **MAY** run whole-project where that is necessary
for correctness or is the cheaper option (for example a single project-wide
type-check). An agent **MUST NOT** fabricate a single-file variant of a check the
toolchain does not support, and **MUST NOT** introduce new tooling merely to
scope a check.

### 5.1.1. Test Discipline — New and Changed Behavior

Tests are a first-class part of the loop, not an optional add-on: they are what
makes the code a Deep Work Plan ships **reliable** and verifiable. Whenever a task
implements new core functionality or materially changes existing behavior, the
agent **MUST**:

- Include, in the task's **Acceptance Criteria**, automated test coverage for the
  new or changed behavior (the happy path plus the meaningful edge/error cases),
  following the repository's test convention and coverage expectation
  (`DOCUMENTATION_STANDARD.md` §2.3, §3.1).
- Include, in the task's **Validation**, the repository's relevant **tests** *and*
  its **lint / type-check / format** checks, selected per §5.1 from the Touched
  Surface — the code-quality check the repository defines for that surface (e.g.
  `codecheck`, `npm run test -- <path> && npm run lint`, `pytest tests/<module> &&
  ruff check`), not the build alone.
- Keep existing tests **green**: if a behavior change breaks a test that covers the
  affected code, the agent **MUST** update that test to reflect the intended new
  behavior — it **MUST NOT** delete, skip, or weaken a test merely to force the gate
  to pass.

**Unit-first, integration where it matters.** Coverage **SHOULD** be built from
the base of the testing pyramid upward:

- Prefer fast, deterministic **unit tests** around observable behavior and
  meaningful boundaries — the smallest unit that has a contract, exercised
  without I/O, network, or a live environment, covering errors, edge cases, and
  regressions. Do not assert internal call sequences, and do not write a test per
  private function merely to inflate counts. Mock external boundaries when it
  clarifies the test, without mocking away the behavior under test.
- Use **integration tests** deliberately where real collaborators, protocols,
  storage, or framework wiring matter — at the seams the Touched Surface
  classifies as *seam* — and add them **in the task that changes the seam**
  (§5.1.a), never as a catch-all deferred to the end of the plan. Do not rename
  integration tests as units to satisfy a ratio.
- Keep **end-to-end** tests few and high-value.

The pyramid is a default cost-and-risk strategy, not a fixed percentage, a
test-count quota, or a universal speed target. Its practical consequence is that
a fast, isolated unit base is what makes selected gates (§5.1.a) fast — a suite
dominated by slow integration tests defeats that. Existing valuable tests are
preserved; blanket rewrites are not part of this discipline.

Pure-documentation, configuration, or research tasks are **exempt** from creating
tests but still **MUST** run whatever validation gate the repo defines. The *depth*
of testing is **proportional** to the size of the change and the repository's
maturity (`SHOULD` scale, not `MUST` reach a fixed number); what is non-negotiable
is that a behavior change ships with the coverage and the green checks the
repository's standard calls for. Where the repository has **no** test or lint
toolchain, the agent **MUST NOT** silently skip this discipline — it surfaces the
gap and relies on the toolchain established or **proposed** during onboarding
(`DOCUMENTATION_STANDARD.md` §3.1, §7).

### 5.1.2. Security Discipline — Risk-Touching Changes

Security follows the same two-layer model as testing: per-task discipline while
the work happens, plus the mandatory Security Review gate (§6.1) over the full
accumulated change set at the end. Whenever a task touches authentication or
authorization, input handling, secrets or configuration, network/file/shell
surface, or dependencies, the agent **MUST**:

- Include, in the task's **Acceptance Criteria**, the security expectations of
  the change (input validated/escaped, no secret material in code or fixtures,
  auth checks preserved or strengthened), consistent with `docs/SECURITY.md`.
- Confirm, before each commit, that the diff contains **no secrets or
  credentials** — test fixtures and documentation examples included. A secret in
  a pushed commit **MUST** be treated as leaked and rotated, not merely removed.
- Where the security-sensitive work is substantial, prefer a dedicated
  `N.task_security_hardening_{feature}.md` task placed **immediately after the
  implementation tasks and before the comprehensive-tests task** — so findings
  are fixed before tests encode the behavior, and each finding becomes a
  regression test case rather than rework.

Pure-documentation or research tasks are exempt unless they handle sensitive
material. This discipline does **not** replace the Security Review final task
(§6.1): per-task checks catch issues in the commit where they are born; the
final gate audits the whole plan, including the tests and docs tasks themselves.

### 5.1.3. Final-State Validation and Gate Evidence

Per-task gates (§5.1.a) validate what each task touched. They do not replace
validation of the plan as a whole:

- **Final-state requirement.** Before a plan can complete, the repository's
  **complete applicable** validation — the full test suite and the full static
  checks the repository defines — **MUST** run and pass on the **final relevant
  state**, after the last substantive change. This runs in the mandatory Final
  Review (§6). It is a requirement on the final state, not an "exactly once"
  quota: a later fix invalidates the affected results and they **MUST** be rerun.
- **Risk-based earlier checkpoints.** The agent **SHOULD** run the broader or full
  validation earlier at integration boundaries, after a *shared/core* change, or
  whenever risk or uncertainty warrants it. It **MUST NOT** insert periodic full
  runs merely because a number of tasks elapsed. Where the full suite is short, it
  **MAY** simply be the selected gate — measure and use the simpler sound option.
- **Reuse of evidence.** A passing result **MAY** be reused instead of rerun only
  with evidence that the relevant inputs are equivalent: repository, command and
  options, test selection, source snapshot (including staged, unstaged, and
  relevant untracked or generated files), dependency, configuration and tool
  versions, and relevant environment. `HEAD` alone is **not** a sufficient
  fingerprint when the working tree is dirty. If equivalence cannot be
  established, the check is rerun. Existing CI results count as evidence only for
  the matching revision and equivalent gates; the agent **MUST NOT** disable
  required CI or override branch protection to satisfy a gate.
- **Gate record.** Each gate run **MUST** leave one concise record (in the task's
  Completion & Log and, where the state layer is present, in `state.json` per
  `PLAN_STATE.md` §4.2): command, working directory, scope and reason, revision or
  fingerprint, result and exit code, selected and executed test counts when the
  runner reports them, and an evidence path. Large logs stay in local artifacts
  and **MUST** remain recoverable; the record carries a compact result and the
  actionable failures. Exit status **MUST** be preserved when output is piped. A
  missing or truncated log is **not** a successful result; when a summary is
  ambiguous the original output is read.
- **One run, several mentions.** A command referenced in Instructions, Validation,
  and the Execution Checklist describes the **same** run; mentioning it more than
  once does not require executing it more than once.

Nothing in this section weakens §5.1: stop on failure, no silent skipping, no
weakened tests, and no missing tool reported as a pass remain in force.

> **Divergence from v2.2.** v2.2 required the relevant suite and the full
> code-quality check on every behavior-changing task and said nothing about how
> a gate is scoped. v2.3 adds the **Touched Surface** (§5.0.2), selects gates by
> risk class with explicit fallbacks and a zero-test defense (§5.1.a–d), makes
> full validation a **final-state** requirement with evidence-reuse rules
> (§5.1.3), and states the **unit-first** posture (§5.1.1). Plans and repositories
> authored under earlier versions remain conformant and are validated with the
> full applicable suite (§5.1.b, §6.5). No previous testing or security
> requirement is removed; rewordings preserve their substance.

### 5.2. Task Completion Protocol

After passing validation and before advancing, the agent **MUST**, in order:
(1) mark the task `[x]` in the plan README; (2) increment the `Plan Status` count;
(3) fill the task's Completion & Log with no placeholders; (4) add a 3–5 bullet
entry to `PROGRESS.md`; (5) commit (where the plan commits) with
`{type}({scope}): {description} - Task {N} of PLAN_{name}`; (6) where the plan
carries the state layer (§10), rewrite `state.json` atomically — task `completed`,
gate records, outcome record, commit hash. The agent **MUST** then verify the
README mark, the status count, the filled log, the PROGRESS entry, and a clean git
state before proceeding.

The six steps form one logical transaction. An agent interrupted mid-protocol
**MUST NOT** start the next task; on its next turn it **MUST** finish or unwind
the partial completion first (the README mark and the `Plan Status` count
disagreeing, or a filled log with an unmarked checkbox, are the desync signals —
see `PLAN_STATE.md` §5 for reconciliation).

### 5.3. The DWP Resume Protocol

Resume **MUST** be possible from only the plan's files plus the git log, with
**no external state**. (In a workspace without git — `ARCHETYPES.md` §4 — the
plan's `state.json` is REQUIRED and stands in for the git log.)

A resuming agent — a new session, a different agent, a scheduled daemon turn, or
a cloud session waking — **MUST** perform this ritual, in order:

1. **Re-anchor.** Read the plan README: §Goal, global guidelines, the task list.
2. **Locate the checkpoint.** Find the first `[ ]` task in the README; read the
   git log and `git status` (or `state.json`'s `checkpoint` where git is absent).
3. **Reconcile state.** Where `state.json` exists, compare it against the README
   checkboxes; on desync, regenerate it from the markdown before continuing
   (`PLAN_STATE.md` §5).
4. **Inspect the seam.** Read the resume-point task's Completion & Log and the
   last `PROGRESS.md` entry — the previous session's last verified ground.
5. **Smoke-test.** Run the repository's cheapest standing validation (the smoke
   or quick-check command from `AGENTS.md` Quick Commands) to confirm the world
   still works *before* building on it. A failing smoke test is investigated
   first, not built upon.
6. **Continue atomically.** Execute exactly the next task; do not batch ahead.

The agent **MUST** trust `[x]` marks and **MUST NOT** re-validate completed tasks
unless the user explicitly requests it, or step 5's smoke test fails in a way
that implicates a completed task.

---

## 6. Plan Lifecycle — Final Review, Task-Local Skills, Optional Report

Every conformant plan authored under this version **MUST** end with exactly
**one** mandatory task, the **Final Review** (task N). Two responsibilities that
earlier versions placed in separate closing tasks are relocated: skills
decisions move **into the task that produced the pattern** (§6.2), and the
Executive Report becomes an **optional artifact generated on request** (§6.3).
Nothing in the security pass is relaxed.

### 6.1. Task N — Final Review

The Final Review **MUST**, in this order:

**(a) Security pass — unchanged in substance.**
- **MUST** review the plan's full accumulated change set (every commit the plan
  produced, plus staged, unstaged, and relevant untracked intended changes) for:
  hardcoded secrets or credentials, injection risks and unsafe input handling,
  new attack surface (endpoints, file/network access, shell execution), weakened
  authentication/authorization, and sensitive data leaking into logs, docs, or
  plan outputs.
- **MUST** review dependencies the plan introduced or upgraded; where the
  ecosystem provides an audit command (e.g. `npm audit`, `pip-audit`,
  `cargo audit`), run it best-effort and record the result.
- **MUST** verify `docs/SECURITY.md` still reflects reality and update it when
  the plan changed secrets handling, the auth model, or sensitive-data
  boundaries (`DOCUMENTATION_STANDARD.md` §3, category 5). If the repo lacks
  `docs/SECURITY.md` entirely, record a finding recommending onboarding.
- **MUST** write `analysis_results/SECURITY_REVIEW.md`, even when the conclusion
  is "no findings."
- A **critical** finding (e.g. a committed secret, an exposed credential, an
  unauthenticated sensitive endpoint) **MUST** be fixed — or explicitly
  escalated to and accepted by the user — before the plan can complete.
  Non-critical findings are recorded in `SECURITY_REVIEW.md` and, when an
  Executive Report is requested, carried into it.
- Where an installed addon augments the security pass (for example a local AI
  diff review), it runs here under the addon's own never-block rule
  (`ADDONS.md`); a completed review's critical findings keep the blocking
  semantics above.

**(b) Final-state validation.** The repository's complete applicable validation
**MUST** run and pass on the final relevant state per §5.1.3. Fixes made during
the review invalidate affected results, which **MUST** be rerun; the order is
review → fixes and mirror/consumer refresh → final gates → closure. No
substantive change ships after its last applicable validation.

**(c) Skills reconciliation — no rediscovery.** The Final Review **MUST** check
that every task carries a skills disposition (§6.2) and that every candidate in
`analysis_results/SKILLS_CANDIDATES.md` has a recorded disposition; any warranted
authoring still open **MUST** be completed and validated before (b) is final. It
**MUST NOT** re-read the whole plan to rediscover patterns and **MUST NOT**
produce a second, separate discovery report; the ledger is the record.

**(d) Completion.** After (a)–(c) pass, the agent reports completion (deliverables,
validation evidence, limitations, and any pull-request links), offers the
Executive Report **once** (§6.3), and — where a reporting channel is configured
(`AGENT_PROTOCOL.md` §5) — sends the completion report. The plan is complete at
this point regardless of whether the offer is answered.

The Final Review **MUST** run sequentially after all other tasks (including any
parallel groups) and **MUST NOT** be placed in a parallel group.

### 6.2. Task-Local Skills Decisions

The question "did this work create a reusable pattern worth a skill or agent?"
**MUST** be answered inside the task that produced the pattern, while its
evidence is in context — not re-derived at the end of the plan.

- Every task's Completion & Log **MUST** carry a **skills disposition**: `none`,
  `update <existing skill/agent>`, `create <name>`, or `defer — <reason and
  owner>`. `none` in the log is sufficient; a task **MUST NOT** be required to
  add a no-op row to the ledger.
- When a pattern is worth recording, the task **MUST** append an entry to
  `analysis_results/SKILLS_CANDIDATES.md` with a **stable candidate ID**
  (`T{task}-{seq}`), the evidence pointer, the disposition, and either the
  artifact produced or the deferral reason. On resume the agent **MUST** update
  an existing candidate by its ID rather than duplicate it.
- Warranted, in-scope authoring (a new or updated skill/agent and its catalog
  entry, per `DOCUMENTATION_STANDARD.md` §4) **MUST** happen **inside that task,
  before its validation gate and commit**, so the artifact is covered by the same
  evidence. Before creating anything the task **MUST** check the existing
  `.agents/` skills/agents catalog for duplicates. Prefer updating an existing
  capability; a single routine change does not justify a new skill. Out-of-scope work is an explicit deferral with an
  owner, never an unrequested installation.

### 6.3. Executive Report — Optional, On Request

The Executive Report is **no longer a mandatory task**. Its content specification
is unchanged: when produced, `analysis_results/EXECUTIVE_REPORT.md` **MUST** be a
stakeholder-ready summary covering at minimum executive summary, plan overview,
deliverables table, product impact, technical details, QA/verification guide,
key decisions and trade-offs, risks/open questions (including non-critical
security findings), and next steps.

- At completion (§6.1 d) the agent **MUST** offer the report **once**. It
  **MUST** generate it only on an explicit request — either that answer, or a
  request the developer made earlier in the plan (for example in the plan's
  guidelines), or a later request at any time.
- A later request **MUST** be satisfied from durable evidence (task logs,
  `PROGRESS.md`, `analysis_results/`, the state layer, and pull-request
  summaries) without replaying the plan or reloading its entire history.
- No answer, a declined offer, or an **unattended** run (`AGENT_PROTOCOL.md`
  §7.2) leaves the plan **complete** with **no** report generated; the unanswered
  offer is not a stop condition and does not block completion. Completion
  reporting through the configured channel (§6.1 d) is separate and remains.

### 6.4. Task Size and Adaptive Execution

- **Granularity.** A task is one coherent outcome with a bounded write surface,
  concrete inputs and outputs, validation relevant to what it changes (§5.0.2),
  and partial steps that can be checkpointed and resumed. The `create` flow
  **SHOULD** split work when distinct outcomes carry different failure modes or
  independent evidence that would otherwise hide behind one checkbox, and
  **SHOULD** keep tightly coupled edits together; a larger cohesive task **MAY**
  keep resumable sub-steps. There is **no** task-count quota, and the flow
  **MUST NOT** multiply approvals, commits, or reports by splitting minor edits
  into separate tasks.
- **Adaptive execution within authorization.** Once a plan is approved, the agent
  **SHOULD** proceed from a passing gate to the next task without asking for
  confirmation, **SHOULD** attempt repairs within the task's authorized scope
  when a gate fails (with a concrete hypothesis, stopping blind retries after two
  attempts without new evidence), and **MUST** pause only at a genuine approval
  boundary or an unresolved blocker (`AGENT_PROTOCOL.md` §7.3). This is portable
  behavior expressed in the plan and the protocol, not a host-specific
  auto-approval setting; it never grants permissions the plan did not list.

### 6.5. Compatibility

| Case | Rule |
|---|---|
| **Plan authored under an earlier version** (three mandatory final tasks; nine-section tasks without a Touched Surface) executed by an agent following this version | **Supported.** The plan **MUST** be executed under its own recorded shape: the executor **MUST NOT** add, remove, or reorder its final tasks and **MUST NOT** add a Touched Surface mid-flight; validation falls back to the full applicable suite (§5.1.b). A `refine` session **MAY** migrate it deliberately. A conformance checker **MUST** accept this shape. |
| **Repository onboarded under an earlier version** (no scoped-invocation documentation) with this version's `onboard` or `create` | **Supported.** Plans fall back to full-suite gates (§5.1.b); the missing documentation is a **finding** that names the targeted, non-destructive, idempotent harness upgrade (`DOCUMENTATION_STANDARD.md`), never a failure. |
| **Plan authored under this version** with an agent following this version | **Supported** — the target. |
| **Plan authored under this version** with an agent following an earlier version | **Not supported; documented.** Such an agent expects three final tasks and will report the plan as non-conformant. Repositories that pin an older skill **SHOULD** upgrade the skill before adopting new plans. |

A tool that checks conformance **MUST** distinguish a known legacy artifact
(accepted) from an artifact that declares this version and is objectively
invalid under it (rejected); legacy acceptance does not make this version's
**MUST** requirements permanent warnings.

> **Divergence from v2.13.** Security Review added as a third mandatory final
> task: completion now requires an explicit security pass over the plan's own
> changes, keeping `docs/SECURITY.md` (a conformance-floor MUST) current instead
> of write-once.
> **Divergence from v2.2.** v2.3 folds the security pass, the final-state
> validation, and skills reconciliation into a single mandatory **Final Review**;
> moves skills decisions into the owning task (§6.2); makes the Executive Report
> optional and on-request with its content unchanged (§6.3); states task-size and
> adaptive-execution rules (§6.4); and codifies compatibility (§6.5). Plans and
> repositories from earlier versions remain conformant.

---

## 7. Archetype Behavior in Plans

- For the **individual repo** (99% case), a plan operates entirely within one
  repository; all validation, commits, and outputs stay in that repo.
- For the **orchestrator hub**, a plan **MAY** be an orchestrator plan (§8) that
  spawns child DWPs in sub-repos. The hub plan **MUST NOT** commit sub-project code
  from the hub root; each sub-repo commits independently.
- An onboarding agent **MUST** determine the archetype (per `ARCHETYPES.md`) before
  deciding whether orchestrator capabilities apply.

---

## 8. Orchestrator Plans (optional capability)

The orchestrator mode is an **optional** capability primarily for the orchestrator
hub archetype. A repository **MAY** use it; an individual repo typically does not.

- An orchestrator plan **MUST** include, in the parent plan, a child-DWP tracking
  table (repository, child plan name, status) and an `ORCHESTRATOR_MANIFEST.md`
  carrying the shared cross-repo context, dependency graph, and output contracts
  (so each child inherits global decisions without re-deriving them).
- Each target sub-repo **MUST** have a dedicated `create_child_dwp` task in the
  parent plan that: navigates into the sub-repo, reads that sub-repo's `AGENTS.md`,
  creates `repositories/{repo}/.dwp/plans/PLAN_{child}/` with all required files,
  and ensures the child's tasks use **that sub-repo's** validation commands.
- Child DWPs **MUST** reference `ORCHESTRATOR_MANIFEST.md` and **MUST** follow this
  specification independently. They **MAY** be created and executed in
  **Distributed**, **Sequential-with-handoff**, or **Sequential-basic** mode.
- After all child plans complete, the parent plan **SHOULD** include an integration
  checkpoint task.

> **Divergence from v1.** Kept from v1 §10 with the path update
> `repositories/{repo}/.dwp/plans/` (was `.../.agent_commands/.../results/plans/`),
> per `RECONCILIATION.md` divergence #2. This plan and its `ORCHESTRATOR_MANIFEST.md`
> are the live worked example.

---

## 9. Team Agents (optional capability)

Team-agents metadata is an **OPTIONAL**, additive extension for agents that support
parallel execution (currently Claude Code only). Plans **MUST** function correctly
when executed sequentially; team-agents metadata is purely additive.

- A plan using team agents **SHOULD** declare Parallel Task Groups in its README
  (group → task numbers → teammates → description).
- A participating task **SHOULD** carry a Team Agents Metadata section (parallel
  group, role, file ownership, concurrency, blocks).
- Tasks in the same parallel group **MUST NOT** write to the same files (declared
  file ownership). The mandatory final tasks (§6) **MUST** remain sequential.

Non-Claude agents **MUST** ignore team-agents metadata and execute every task
sequentially (see `AGENT_PROTOCOL.md`).

---

## 10. Machine-Readable Plan State (optional layer)

A plan **MAY** carry the machine-readable state layer — `manifest.json` (static
identity) and `state.json` (live per-task state, validation-gate records, outcome
records, checkpoint, blocked state) — normatively defined in **`PLAN_STATE.md`**
with published JSON Schemas in [`schema/`](schema/).

- The markdown plan remains the source of truth; the JSON layer is a **derived
  projection**, regenerated at the protocol points of §5.2 and reconciled on
  resume (§5.3 step 3).
- The layer is **RECOMMENDED** for new plans, **REQUIRED** for unattended
  execution (`AGENT_PROTOCOL.md` §7) and for agent workspaces without git
  (`ARCHETYPES.md` §4).

---

## 11. Proportional Rigor — Plan Tiers

Rigor **MUST** be proportional to the work. Ceremony on trivial changes is a
methodology failure, not extra safety. Every piece of work falls in exactly one
tier, declared in the manifest's `rigor` field when the state layer is present:

| Tier | When | Form |
|------|------|------|
| **micro** | A single atomic change: one concern, roughly one sitting, no coordination — a bug fix, a copy change, a config tweak. | **No plan folder.** The agent states the goal, the acceptance criteria, and the validation gate inline in conversation, executes, validates, commits. |
| **standard** | Multi-step work with real scope: a feature, a refactor, a migration within one repo. The default tier. | A full plan per §4–§6: plan folder, 10-section tasks (§5), the Final Review (§6.1). |
| **deep** | Long-horizon work spanning parallel groups, child repositories, or multiple unattended sessions. | A standard plan plus the orchestrator (§8) and/or team-agents (§9) capabilities, and the state layer (§10). |

- An agent asked to "create a plan" for micro-tier work **MUST** say that a plan
  is disproportionate and offer the inline form instead. In the **interactive**
  profile a plan folder **MUST NOT** be created for a trivial single-file change
  unless the developer, having been told, still asks for one. In the
  **unattended** profile (`AGENT_PROTOCOL.md` §7.2 — including a plan requested
  with `trust`) there is nobody to answer the offer: the agent **MUST NOT** stop
  to ask and **MUST NOT** silently produce nothing. It **MUST** record the micro
  judgment and the inline alternative in the plan README (the tier, why it is
  disproportionate, and the goal + acceptance criteria + validation gate the
  developer could run inline instead) and materialize the plan, which the
  developer can discard on sight. The disproportion is **stated**, never
  concealed — that is the requirement; the folder is the lesser evil when the
  alternative is an unanswered question.
- Micro-tier work still keeps the non-negotiables: an explicit goal, a
  validation gate that runs and passes (§5.1), and test discipline for behavior
  changes (§5.1.1). The tier changes the *packaging*, never the *gates*.
- When scope grows mid-flight — a micro task uncovers real scope, a standard
  plan sprouts sub-repos — the agent **MUST** stop and promote the work to the
  next tier rather than stretching the current one.
- Tier selection is part of plan creation: the `create` flow **SHOULD** state
  the chosen tier and why in the refined draft (guided mode) or in the plan
  README (trust mode, §3).

---

## 12. References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119)
- `DOCUMENTATION_STANDARD.md`, `AGENT_PROTOCOL.md`, `ARCHETYPES.md`, `ADDONS.md`, `PLAN_STATE.md`
- `../RECONCILIATION.md` (divergences #1–#3 drive this spec), `../../ORCHESTRATOR_MANIFEST.md`
- [Conventional Commits](https://www.conventionalcommits.org/)

---

*Part of the DeepWorkPlan methodology v2.3.0, MIT License, by [Dailybot](https://dailybot.com) / dailybotops.*
