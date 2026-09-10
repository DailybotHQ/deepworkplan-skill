# Onboarding plan template — a reasoning aid, NOT a copy-paste

This is the **shape** of the Deep Work Plan that the `onboard` flow emits on its
**plan-driven path** (Phase 2b) for a **large** repo — when "make this repo
AI-first" is itself a multi-task job: analyze the whole codebase, document every
`docs/` category and every major module, and generate the full `.agents/` kit.

> **Reason, do not copy.** Every task below must be **derived from the real
> recon** (`.dwp/onboard/RECON.md`): the repo's actual modules, its real
> validation commands, its real test convention. A task that ships a generic
> stub or a placeholder doc is a **failure**, exactly as it is on the inline
> path. Use this file to remember the *structure and gates*; fill the *content*
> from the repo in front of you.

The plan is created with `/dwp-create`, refined with `/dwp-refine`, executed with
`/dwp-execute`, and resumed with `/dwp-resume`. It lives under
`.dwp/plans/PLAN_onboard_{repo}/` per [`../../shared/dwp-paths.md`](../../shared/dwp-paths.md)
and follows the plan/task anatomy in [`../../guide/authoring.md`](../../guide/authoring.md).

---

## Plan README (`PLAN_onboard_{repo}/README.md`)

```markdown
# Plan: Onboard {repo} — make it AI-first

## 1. Goal
Bring {repo} to DeepWorkPlan conformance: a real, repo-specific AGENTS.md +
docs/ + per-module docs + .agents/ kit, validated task-by-task. Source of truth
for every task is `.dwp/onboard/RECON.md`.

## 2. Context
- Archetype: {individual repo | orchestrator hub} (evidence in RECON.md)
- Stack / package manager: {detected}
- Real validation gate (reused by every task): {e.g. `pnpm md:check`, `ruff check`,
  `npm run lint`, the repo's link-check} — flagged CI/Docker-only where relevant.
- Non-destructive: existing hand-written artifacts are merged/backed-up, never
  clobbered (onboard Phase 0).

## 3. Global Guidelines
- No placeholders ship (`<...>`, TODO, "your command here") — zero tolerance.
- Every doc carries real, repo-specific content and runnable commands.
- Idempotent: re-running only fills gaps.

## 4. Task List & Links
- [ ] 1. AGENTS.md + CLAUDE.md symlink            → 1.task_agents_md.md
- [ ] 2. docs/PRODUCT_SPEC.md                      → 2.task_docs_product_spec.md
- [ ] 3. docs/ARCHITECTURE.md                      → 3.task_docs_architecture.md
- [ ] 4. docs/STANDARDS.md                         → 4.task_docs_standards.md
- [ ] 5. docs/TESTING_GUIDE.md (verified testing map) → 5.task_docs_testing.md
- [ ] 6. docs/DEVELOPMENT_COMMANDS.md              → 6.task_docs_commands.md
- [ ] 7. docs/SECURITY.md (+ PERFORMANCE, AI_AGENT_*) → 7.task_docs_rest.md
- [ ] 8. Per-module README: {module A}             → 8.task_module_a.md
- [ ] 9. Per-module README: {module B}             → 9.task_module_b.md
- [ ] … one task per major module from RECON.md …
- [ ] N-2. .agents/ kit (agents + skills + commands + catalogs)
- [ ] N-1. Install skill + scaffold .dwp/ and tmp/ + addons offered
- [ ] N.  MANDATORY FINAL: Final Review — Phase 8 self-check (conformance gate)
          + security pass + final-state validation + skills reconciliation
          (skills decisions are task-local; the Executive Report is optional)

## 5. Execution Rules for the Agent
Re-anchor to this goal before each task. One task at a time. Run the task's
validation gate before marking it done (docs tasks: `Touched Surface: not
applicable — documentation`; the repo's non-runtime checks are the gate). Record
the task's skills decision in its log before validating. Update PROGRESS.md
(bounded Active context) after each task so the plan is resumable.

## 6. Skills & Agents Used
deepworkplan-onboard (reference), deepworkplan-verify (final conformance), plus
any stack skills generated in task N-2.

## 7. Plan Status / Notes
{updated during execution}
```

---

## Per-task shape (`N.task_{title}.md`)

Each task follows the standard task anatomy (`../../guide/authoring.md` §5). The
onboarding-specific point is that **the Acceptance Criteria encode the Phase 0–8
rules per artifact**, and the **Validation gate is the repo's real check**.

```markdown
# Task {N}: Generate docs/{CATEGORY}.md

## 1. Context
Onboarding {repo}. Source: `.dwp/onboard/RECON.md`. This doc is one of the
standard categories (onboard Phase 4).

## 3. Goal
Produce a real, repo-specific `docs/{CATEGORY}.md` — the actual {commands /
modules / conventions} from recon, no generic stub.

## 4. Instructions
Reason the content from RECON.md and the real files. Carry forward existing
conventions; never override a working one with a generic default.

## 5. Acceptance Criteria
- [ ] File exists with real, repo-specific content (no placeholder markers).
- [ ] Every command shown actually runs in this repo (or is flagged CI/Docker-only).
- [ ] All internal links resolve.
- [ ] Existing hand-written content was merged, not clobbered.

## 7. Validation
{the repo's real gate, e.g.}
    pnpm md:check        # or: ruff check / npm run lint / link-check
    grep -rn '\[TODO\|\[TBD\|<your' docs/{CATEGORY}.md   # → zero matches
```

### Testing-guide task (the one every later plan depends on)

```markdown
# Task 5: Generate docs/TESTING_GUIDE.md — the verified testing map

## 3. Goal
Document, from the real repo, everything a plan needs to select a validation
gate (DOCUMENTATION_STANDARD §3.4): full and scoped commands, mapping, consumers,
blind spots, escalation, fallback, and the unit-first posture.

## 4. Touched Surface
not applicable — documentation (gate: the repo's markdown/link check + the
verification run below)

## 5. Acceptance Criteria
- [ ] Full-suite and full lint/format/type-check commands recorded verbatim, with cwd.
- [ ] Scoped pattern(s) with at least one concrete example from this repo; the
      example was RUN and selected a non-empty relevant set (count recorded) —
      or is marked proposed/unverified with the reason and a real fallback.
- [ ] Source-to-test mapping rule, dependent-consumer policy (tool or list),
      known blind spots, shared/core escalation paths and the explicit fallback.
- [ ] Testing posture: where each layer lives; unit-first behavioral coverage;
      real-seam integration; useful e2e; deterministic fixtures; no quotas.
- [ ] Current capabilities and any proposed setup in clearly separate sections.

## 7. Validation
    {repo link-check / md:check}
    {the scoped example command}     # must select a non-empty relevant set
    grep -rn '\[TODO\|\[TBD\|<your' docs/TESTING_GUIDE.md   # → zero matches
```

### Per-module task (the part that scales worst inline)

```markdown
# Task {N}: Per-module README — {module path}

## 3. Goal
Document {module}: its responsibility, key files / public surface, and how it is
tested (onboard Phase 5). Add a docs/ subfolder only if the module is complex
(3+ interconnected concerns).

## 5. Acceptance Criteria
- [ ] {module}/README.md describes responsibility + public surface + test approach.
- [ ] Real file/symbol names from the module — no generic boilerplate.
- [ ] Linked from the module and surfaced in the root AGENTS.md index if major.

## 7. Validation
    test -f {module}/README.md && grep -q . {module}/README.md
    {repo link-check / md:check}
```

### Mandatory final task

```markdown
# Task {N}: Final Review — conformance gate

## 3. Goal
Run onboard Phase 8 self-check across everything generated, then the plan's
single mandatory Final Review (DWP_SPECIFICATION §6.1): security pass,
final-state validation, skills reconciliation, completion with the one-time
Executive Report offer.

## 5. Acceptance Criteria
- [ ] `/dwp-verify` (or the Phase 8 checklist) reports CONFORMANT.
- [ ] Final-state validation: the repo's own full validation command runs clean once.
- [ ] `.agents/docs/` catalog matches what exists on disk (no phantom entries).
- [ ] Security pass written to `analysis_results/SECURITY_REVIEW.md`;
      `docs/SECURITY.md` verified current; no unresolved critical finding.
- [ ] Every task log carries a skills disposition; the candidates ledger is reconciled.
- [ ] `.dwp/onboard/REPORT.md` records the first usable outcome (verified command
      and mapping, skill identity/version, capability limits, next action).
- [ ] Executive Report offered once; generated only if requested.

## 7. Validation
    bash {skill-path}/deepworkplan/verify/SKILL.md   # read-only conformance
    {repo's real validation command}
```

---

## Why plan-driven instead of inline (for a large repo)

| | Inline (Phases 3–8 in one session) | Plan-driven (this template) |
|---|---|---|
| Context | One window holds everything | One task at a time |
| Resume | Lost on interruption | `/dwp-resume` from the first open task |
| Audit | One big diff | Per-task gate + PROGRESS.md |
| Per-artifact gate | Best-effort at the end | Enforced before each task completes |
| Best for | Small/medium repos | Large repos, monorepos, hubs |

The inline path stays the **default** for typical repos — this plan-driven path
is the scale escape hatch, selected in Phase 2b.
