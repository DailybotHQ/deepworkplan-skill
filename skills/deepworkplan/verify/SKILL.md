---
name: deepworkplan-verify
description: Verify that a repository is DeepWorkPlan-conformant (AI-first) and that its plans are well-formed, producing an objective pass/fail report. Use when the developer asks to verify, audit, or check conformance of a repo or a plan.
version: "4.0.2"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob
---

# DeepWorkPlan — Verify (conformance check)

Check, objectively, whether a repository is **DeepWorkPlan-conformant** (AI-first
and agent-pilotable) and whether its Deep Work Plans are well-formed. This
sub-skill is **read-only**: it reports pass/fail, it does not change files. The
normative criteria are defined in the specification's Conformance document
(<https://deepworkplan.com/spec>).

## Shared resources (read these)

- [`../shared/context.sh`](../shared/context.sh) — resolve the repo root and `.dwp/`.
- [`../shared/dwp-paths.md`](../shared/dwp-paths.md) — plans live at `.dwp/plans/PLAN_{name}/`.
- [`conformance.sh`](conformance.sh) — the mechanical conformance layer (run it first).
- [`../spec/PLAN_STATE.md`](../spec/PLAN_STATE.md) — the machine-readable state layer the desync checks enforce.
- **Guide (essential — read for this flow):** none — the spec is the standard being checked.
- **Guide (conditional — read only when the trigger fires):** [`../guide/structure.md`](../guide/structure.md) §1–§2 when a naming or layout finding needs the rationale.

## Run the mechanical layer first

Start every verification by running the automated checker — it covers the
structural checks below objectively, exits `0`/`1`, and detects
markdown-vs-`state.json` desync:

```bash
bash {skill_dir}/verify/conformance.sh            # repo + every plan
bash {skill_dir}/verify/conformance.sh --repo-only
bash {skill_dir}/verify/conformance.sh --plan PLAN_{name}
```

The checker resolves the git root even when invoked from a subdirectory and
honors the absolute `DWP_DIR` override for repository, all-plan and named-plan
checks. An in-repository output directory must be gitignored; an external one
is already outside the checkout.

Its exit code is CI-friendly: a repo can run it as a pipeline gate. It accepts both plan lifecycle shapes (the 2.3.0 single Final Review and the pre-2.3.0 three-final-task ending) and reports harness-version findings for repositories onboarded under an earlier standard. Then layer
the judgment checks (real commands, real toolchain, catalog-matches-disk) on
top — the script verifies *structure*; you verify *substance*.

## Parameter support

- `/dwp-verify` — verify the repository (the default).
- `/dwp-verify plan {name}` — also verify a specific plan's well-formedness.
- `/dwp-verify all` — verify the repository and every plan under `.dwp/plans/`.

## Trust boundary (write scope)

This skill is **read-only by contract**. `allowed-tools` lists `Bash` (to run
the repo's own read-only inspection and validation commands), not `Edit` or
`Write`: verification produces a **report**, never a repair.

**It MUST NOT:** create, modify, or delete any file; "fix" a failing criterion;
or let a failed check silently pass. Findings are reported with evidence and
fixed through the proper sub-skill (`onboard`, `refine`, or a plan).

## The overriding rule

Report what is **true on disk**, not what should be true. A criterion passes only
if the artifact exists *and* carries real, repository-specific content. A generic
stub, a placeholder, or a command that cannot run in this repository **fails** the
criterion — say so explicitly. Never mark a check passed without evidence.

## Repository checks

Run these from the repo root and record each result. Prefer the mechanical check;
fall back to reading the file when judgment is required (for example, deciding
whether `AGENTS.md` commands are real).

```bash
# 1. AGENTS.md at the root, with a Quick Commands block
test -f AGENTS.md && grep -qiE 'quick commands|## commands' AGENTS.md && echo "AGENTS.md: ok" || echo "AGENTS.md: FAIL"

# 2. CLAUDE.md resolves to AGENTS.md (symlink or equivalent single source)
[ -L CLAUDE.md ] && [ "$(readlink CLAUDE.md)" = "AGENTS.md" ] && echo "CLAUDE.md symlink: ok" || echo "CLAUDE.md symlink: CHECK"

# 3. docs/ with the standard categories
test -d docs && echo "docs/: present" || echo "docs/: FAIL"
for d in PRODUCT_SPEC ARCHITECTURE STANDARDS TESTING_GUIDE DEVELOPMENT_COMMANDS SECURITY AI_AGENT_ONBOARDING; do
  ls docs/ 2>/dev/null | grep -qi "$d" && echo "  docs/$d: ok" || echo "  docs/$d: missing"
done

# 4. .agents/ home with agents/ commands/ skills/ + a docs catalog; .claude resolves
for d in .agents/agents .agents/commands .agents/skills .agents/docs; do
  test -d "$d" && echo "$d: ok" || echo "$d: FAIL"
done
[ -e .claude ] && echo ".claude resolves: ok" || echo ".claude resolves: FAIL"
[ -e .cursor ] && echo ".cursor resolves: ok" || echo ".cursor resolves: FAIL"

# 5. dwp-* commands are thin delegators (≤ ~30 lines, reference the skill)
for f in .agents/commands/dwp-*.md; do
  [ -f "$f" ] || continue
  lines=$(wc -l < "$f")
  grep -qi 'deepworkplan' "$f" && [ "$lines" -le 40 ] && echo "$(basename "$f"): thin ok" || echo "$(basename "$f"): CHECK ($lines lines)"
done

# 6. .dwp/ gitignored with plans/; tmp/ gitignored
git check-ignore .dwp >/dev/null 2>&1 && echo ".dwp gitignored: ok" || echo ".dwp gitignored: FAIL"
test -d .dwp/plans && echo ".dwp structure: ok" || echo ".dwp structure: FAIL"
git check-ignore tmp >/dev/null 2>&1 && echo "tmp gitignored: ok" || echo "tmp gitignored: SHOULD"

# 7. AI Diff Reviewer local review installed (required since DWP standard 2.3.0; a finding on legacy repos)
test -f .agents/skills/ai-diff-reviewer/SKILL.md && echo "ai-diff-reviewer skill: ok" || echo "ai-diff-reviewer skill: MISSING"
{ test -f .review/extension.md || test -f .github/ai-diff-reviewer/extension.md || test -f .github/ai-pr-reviewer/extension.md; } && echo "review extension: ok" || echo "review extension: MISSING"
```

Then, by reading rather than grepping:

- **Real commands.** Open `AGENTS.md` and confirm the Quick Commands actually correspond to this repo (the real package manager, test, lint, and build commands). Flag any command that could not run here.
- **Testing toolchain defined.** Open `docs/TESTING_GUIDE.md` and confirm it describes either a **real** test/lint setup (framework, file convention, how to run, coverage expectation) or — for a repo without one — a concrete **proposed** stack-appropriate setup (`../spec/DOCUMENTATION_STANDARD.md` §3.3). An empty file, a generic stub, or "no tests" **fails** this check: the repo then has no objective validation gate for future plans.
- **Repository standard and harness version.** `AGENTS.md` should carry a `DWP standard: X.Y.Z (…)` provenance line (`../spec/DOCUMENTATION_STANDARD.md` §3.5). A repository that **declares 2.3.0 or later** must have the §3.4 content in `docs/TESTING_GUIDE.md` (full and scoped commands with a repository example, source-to-test mapping, consumer policy, blind spots, escalation, explicit fallback, posture) — missing content **fails**. A repository with no declaration, or an older one, whose guide lacks that content receives a **harness-version finding** naming the upgrade path (run the `onboard` sub-skill in `upgrade` mode) — a finding, never a failure. A declared standard newer than this skill supports fails with an upgrade message.
- **Semantic limits (disclosed).** The mechanical layer checks structure: names, order, counts, links, headings, keywords. Whether a Touched Surface is *correct*, a scoped command *actually selects* the right tests, or a Final Review *actually reviewed* the diff is judged by reading — report those as manual review items with evidence, never as automatic passes.
- **Catalog matches disk.** Confirm `.agents/docs/` (the skills/agents catalog) lists exactly the skills, agents, and commands that exist under `.agents/` — no dead links, no missing entries.
- **Skill resolvable.** Confirm the DeepWorkPlan skill is installed or referenced so its sub-skills can be invoked.
- **Local reviewer present.** The AI Diff Reviewer local review (`../spec/ADDONS.md` §6.5) is part of the baseline since 2.3.0: the vendored skill at `.agents/skills/ai-diff-reviewer/` plus an extension file at a recognized path. Missing pieces are a **failure** for a repository declaring 2.3.0 or newer and a harness-version **finding** for a legacy one; a declared exception recorded in `AGENTS.md` is reported, not excused. The CI surface (`pr-review.yml`) is optional and never checked as required.

## Plan checks (when verifying a plan)

For each plan under `.dwp/plans/PLAN_{name}/`:

- Every task file declares an explicit scope, **acceptance criteria**, and at least one **validation gate** (a runnable command or check).
- **Test discipline.** Tasks that add new core functionality or change product behavior require automated test coverage in their Acceptance Criteria and run the repo's tests + lint/type-check in their Validation (`DWP_SPECIFICATION.md` §5.1.1). A behavior-changing plan with zero test work is a finding, not a pass.
- **Security discipline.** Tasks that touch auth, input handling, secrets/config, network surface, or dependencies carry security expectations in their Acceptance Criteria (`DWP_SPECIFICATION.md` §5.1.2); where the plan has a dedicated security-hardening task, it is ordered before the comprehensive-tests task.
- `PROGRESS.md` exists and is updated, so the plan is resumable.
- **Lifecycle shape (one of two, never mixed — `DWP_SPECIFICATION.md` §6, §6.5).** The plan's standard is read from its README `**Standard:**` line, else `manifest.json` `spec_version`, else it is legacy (`PLAN_STATE.md` §6.1). A **2.3.0** plan ends with exactly one `{N}.task_final_review*.md` as the last task, and that file names its three parts (security pass, final-state validation, skills reconciliation) — the filename alone proves nothing. A **legacy** plan ends with `security_review` (N-2), `skills_agents_discovery` (N-1), `executive_report` (N). A **declared migration** may keep an already-completed `security_review` as N-1 before the Final Review. Mixed, missing, duplicate or misordered final tasks fail; task ids must be unique and contiguous (sorted numerically — 10 comes after 9). A plan that declares a standard **newer** than this skill supports fails with an upgrade message and is **not** executed as legacy. On a completed plan, `analysis_results/SECURITY_REVIEW.md` exists and reports no unresolved critical finding.
- **Correspondence.** Every task file is referenced from the README and every README task link resolves; when the state layer is present, `state.json`'s `task_count`, unique numeric IDs and unique task entries match the files on disk one-to-one. Each task's completed status agrees with its README checkbox; `completed_count` and the README summary agree with those tasks. `Read Before Starting` references to nonexistent tasks are findings.
- **2.3.0 findings (never failures).** Tasks without a `Touched Surface` section (required for behavior-changing tasks; documentation/research tasks may state not applicable) and a missing `analysis_results/SKILLS_CANDIDATES.md` (acceptable until the first candidate exists — task logs may record `none`) are reported as findings. Legacy plans are not asked for either.
- Tasks re-anchor to the plan goal before executing.
- **State layer (when present).** `state.json` and `manifest.json` parse, and
  `state.json` agrees with the README checkboxes — on desync the markdown wins
  and the state file must be regenerated (`../spec/PLAN_STATE.md` §5).
  `conformance.sh` automates this. In a workspace without git
  (`../spec/ARCHETYPES.md` §4) the state layer is REQUIRED, not optional.

## Output

Produce a concise report:

```
DeepWorkPlan conformance — {repo name}

Repository
  [x] AGENTS.md (real Quick Commands)
  [x] CLAUDE.md -> AGENTS.md
  [ ] docs/ — missing SECURITY.md
  [x] .agents/ + catalog matches disk
  [x] .cursor -> .agents
  [x] .dwp/ gitignored (plans/)
  [x] tmp/ gitignored
  [x] skill resolvable

Verdict: NOT CONFORMANT — 1 issue.
Next: run /dwp-create "fix conformance gaps" to plan the remediation, then /dwp-execute.
```

End with one of: **CONFORMANT** (all MUST criteria pass) or **NOT CONFORMANT — N issue(s)**, listing each failure. If gaps exist, offer to capture the fixes as a Deep Work Plan with `/dwp-create` — do not fix them silently inside this read-only check.

> **Unsupported newer plan.** If a plan (or `AGENTS.md`) declares a DWP
> standard newer than this skill implements, the checker fails with an upgrade
> message. Do not execute such a plan as if it were legacy: upgrade the installed
> skill (`npx --yes skills add DailybotHQ/deepworkplan-skill@<newer tag> --skill deepworkplan -y`), then
> re-run `verify`.

> **Large repo / in-progress onboarding.** A big repo may be mid-onboarding via
> the plan-driven path (onboard Phase 2b) — its documentation is being generated
> task-by-task by an onboarding Deep Work Plan rather than all at once. If you
> find a `PLAN_onboard_*` under `.dwp/plans/`, report conformance gaps as
> **in progress, not failures**, and point the developer at `/dwp-status` and
> `/dwp-resume` to finish that plan rather than starting a new remediation plan.
