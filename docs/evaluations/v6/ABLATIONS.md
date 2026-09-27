# v6 component ablations — which mechanisms earn their complexity

> Task 22 of the v6 verified-autonomy plan. Predeclared design (written
> before any ablation cell ran): `.dwp/plans/PLAN_v6_verified_autonomy/22.task_run_component_ablations.md`
> §"Design (predeclared 2026-09-27)". Raw evidence:
> `.dwp/plans/PLAN_v6_verified_autonomy/analysis_results/lab/ablations/`
> (campaign inventories, `JOIN-abl.md`, pack manifests) and
> `tests/evaluation/v6/campaigns/ablations*.json` (configs + index).

## What was asked

The plan's task 22 asks which v6 mechanisms earn their complexity: compare the
full v6 candidate with one-factor-removed variants on development-only cases,
keeping model, task, initial snapshot, reviewer version/extension and the total
resource envelope matched; add a no-DWP-plus-same-reviewer sensitivity cell;
report interactions and uncertainty rather than additive causal percentages;
remove complexity only with evidence, and revalidate the final candidate after
any removal.

## The three mechanisms under test

| Factor | v6 increment | Files carrying it | One-factor-removed variant |
|---|---|---|---|
| Adaptive scheduling | deterministic authorization core: model proposes `select`/`adapt`, `scheduler.py` decides, journal records decisions | `shared/scheduler.py`, execute/v6.md steps 1 & "Mid-run adaptations", status/SKILL.md | fixed plan-order dispatch, no proposals — v5 repair-and-rerun discipline |
| Outcome verification | controlled criteria close only on a discriminating (old FAIL, new PASS) control pair | `shared/outcomes.py`, execute/v6.md steps 5–6, create/v6.md evidence class | no controlled criteria; gate evidence alone closes criteria |
| Context/state automation | context manifest, generated views, ledger projections | `shared/context_manifest.py`, `shared/views.py`, `shared/ledger.py project`, execute/v6.md steps 0/8 | no manifest, no generated views; hand-maintained records over the journal |

All variants keep the mandatory v5 safety checks intact (gates through the
runner, no completion without evidence, workspace-local `.dwp/`).

## Design

- **Grid:** 3 families (astro, service, legacy) × 2 development cases each
  (AC-2/AC-5, SC-5/SC-9, LC-1/LC-6 — the same cases and verbatim prompts as
  development r1) × 5 treatments × 1 repeat × claude-code stratum = 30 cells.
- **Treatments:** full / nosched / nooutcome / noautom / reviewer. The first
  four share one base pack; the reviewer cell is the no-DWP sensitivity arm
  carrying only the candidate's `ai-diff-reviewer` addon (byte-identical copy),
  so "same reviewer" holds by construction.
- **Driver vocabulary:** lab.py's measurement arms are fixed at (A, B, C), so
  each treatment runs as its own single-arm campaign with the treatment pack in
  the C slot and the treatment encoded in the campaign name. No tooling treats
  these as pilot A/B semantics.
- **Envelope match:** same model, same adapter, same seeds and snapshots as
  development r1; ceiling 2700 s per cell (see the r1-grid caveat below);
  oracle scoring through the same frozen oracle commitments
  (`oracle-commitments-4ebff28.json`) and calibrated pilot scorer.
- **Manipulation check (predeclared):** per-cell mechanism traces harvested
  from each workspace — journal decision events (select/adapt), control pairs,
  gate runs, generated views, projected state.json, and a plan-shape census
  (v6 shape = journal/contract chain; legacy = v5/v2 shape). An ablation that
  did not actually ablate, or a "full" cell whose mechanisms never ran, is a
  failed manipulation check, not a data point.

## What happened first: the grid that could not measure (r1 attempt)

The first execution of the predeclared grid was **stopped before completion**
and is retained as evidence, not as measurement. Two defects, both caught by
the manipulation check before conclusions were drawn:

1. **The v6 loop never engaged.** The r1 candidate's router `SKILL.md` shipped
   `version: "5.5.4"` while create/SKILL.md Step 0.3 routes new plans to the v6
   contract only "if this pack's line is 6+ or the developer explicitly asked
   for a v6 plan". Neither condition can fire in evaluation conditions: the
   pack line was 5.x and the neutral task prompts never say "v6". Every actor
   built a v5/v2-shape plan (a sweep of all development-r1 workspaces found 54
   v5 + 1 v2 manifests, zero journals, zero contract chains). One-factor-removed
   variants of a loop that never runs are behaviorally identical — the grid
   would have measured noise at full price.
2. **An under-provisioned ceiling.** The lanes called `lab.py run` without
   `--timeout-s`, inheriting the 900 s default while the development envelope
   ran 2700 s. Two documentation cells (AC-2, LC-6) timed out at exactly
   900.03 s — ceiling artifacts, not task outcomes.

The stop decision, the workspace sweep, and the redesign are logged in the task
log (18:40Z–18:55Z entries); the interrupted campaign outputs remain under
`lab/ablations/ablations-*/` untouched.

**Lesson recorded for the architecture-retention question:** a mechanism that
cannot be reached by real agents in real conditions is complexity without
effect until its routing is fixed. Measured, not assumed — the manipulation
check is what turned "v6 works in principle" into "v6 never ran once".

## The r2 candidate (routing repaired)

`packs/v6/v6-candidate-r2-43c01a8d53a72d77` — the frozen r1 pack plus exactly
two repair sets (`CANDIDATE_R2_MANIFEST.json`, sha256 per patch):

- **R2-1 routing:** `version: "5.5.4"` → `"6.0.0"` in all 16 SKILL.md files
  (synchronized, mirroring the upstream auto-release), making the Step 0.3
  6-line gate reachable. Existing v5 plans still execute via shape-based
  detection, so the repair is additive for already-onboarded repositories.
- **R2-2 symlinks:** the onboarding `.claude`/`.cursor` instruction (the task-21
  T21-6 defect site) now pins the working directory to the repository root,
  forbids creating the links inside `.agents/`/`.claude/`/`.cursor/` themselves,
  and adds a readlink verification with an explicit misplaced-link repair path.

The routing chain was then verified statically, hop by hop: router line
`version: "6.0.0"` → Step 0.3 gate text present → v6-contract instruction →
execute's shape-based detection (`contract.json` / `contracts/` chain) →
`create/v6.md`, `execute/v6.md`, and all five `shared/` mechanism files present.
The three one-factor-removed variants were rebuilt **from r2** with the same
asserted patch triples (their patch sites are disjoint from the r2 repairs):
`v6-abl2-nosched-9bb5988f32d08e6f`, `v6-abl2-nooutcome-bcb3d020d134b44f`,
`v6-abl2-noautom-308c97b2063eee24`, `v6-abl2-reviewer-05ee02a0bcf7cefb`.

## Results (grid stopped 2026-09-27 21:15Z)

The r2 grid did **not** finish. After three full-arm completions, Claude
returned `429 Weekly/Monthly Limit Exhausted` with reset
**2026-10-03 04:48:05** (service-reviewer SC-5 log, `api_error_status 429`).
A 60-minute lab cooldown would not recover that cap. The armed 21:25Z
resume was killed at 21:15Z so 24 further starts would not all 429-and-bill.

Calibrated scoring used frozen oracle commitments
`oracle-commitments-4ebff28.json` (14/14 digests verified before any oracle
ran). Join: `lab/ablations/JOIN-abl.md`. Configs: 15/15 `ablations2-*.json`
`lab.py validate` OK.

| grid | family | treatment | case | status | verdict | usd | v6 plans | control pairs | views |
|---|---|---|---|---|---|---:|---:|---:|---:|
| r2 | service | full | SC-5 | completed | **PASS** | 2.695102 | 1 | 0 | 4 |
| r2 | service | full | SC-9 | completed | **PASS** | 4.961538 | 1 | 4 | 8 |
| r2 | legacy | full | LC-1 | completed | **FAIL** | 4.882626 | 1 | 0 | 8 |
| r2 | astro | full | AC-2 | timeout 2700.05 s | ineligible | — | 1 | 0 | 4 |
| r2 | remaining | nosched/nooutcome/noautom/reviewer + LC-6/AC-5 | 21× `provider_refused` + 5 reviewer slots never inventoried | not scored | — | — | — | — |

r2 invoiced **$18.487963** (three completions $12.54 + three refused cells
that still billed $5.95). Combined with the r1 drain ($1.78) and development
live ($77.90): **$98.17** metered in this ledger scope.

LC-1 FAIL is mechanism-active: v6 plan `spec_version` 6.0.0, CLI already had
`--format json`, `callers/report-gen.sh` never forwarded it. Oracle LC-1b
requires the caller JSON mode. Visible seed TASK.md asked for `--in`/`--out`
only. AC-2 timeout was progress-positive (T-2 in flight at SIGKILL, canary
intact), not a hang.

## Manipulation check

| cell | plan shape | adapt events | control pairs | views | state_proj |
|---|---|---:|---:|---:|---|
| SC-5/full r2 | v6 (journal/contract, 6.0.0) | 0 | 0 | 4 | False |
| SC-9/full r2 | v6 | 0 | 4 | 8 | False |
| LC-1/full r2 | v6 | 0 | 0 | 8 | False |
| AC-2/full r2 (timeout) | v6 | 0 | 0 | 4 | False |
| r1 six-cell drain | 0 v6 / 2 v5-lite / 4 planless | 0 | 0 | 0 | False |

The r2 routing repair is confirmed on every finished full-arm cell. The r1
drain remains routing-failure evidence, not a mechanism contrast. One-factor
variants never produced a scored completed cell, so they cannot support
keep/remove.

## Reading the numbers

No additive percentages. n=1 per finished cell. Development-r1 sibling band
(median 1.42×, max 6.48×) is unused because no paired variant cells exist.
SC-9's 4 control pairs show outcome verification *can* fire once routing
works — reachability, not effect size. Remaining 26/30 slots are environment
class (quota or mid-cell kill), not agent failures.

## Architecture retention verdict

**Retain all three v6 increments and the r2 routing repair.** Removal
requires a measured no-loss on the one-factor-removed grid; that grid is
not measurable until the Claude weekly/monthly cap resets. Default retain
is the predeclared rule when evidence is absent. Details:
`analysis_results/ARCHITECTURE_RETENTION.md`.

## Limits

- One repeat per cell: single-cell differences are observations, not rates;
  the uncertainty rule from the predeclared design (sibling-variance band from
  the two-repeat development-r1 cells) governs every comparison below.
- Development cases only; no confirmation-case claims (sealed cases belong to
  later tasks and are never touched here).
- The reviewer sensitivity cell shares the reviewer surface by byte identity;
  it cannot isolate reviewer *quality*, only the presence of the DWP method
  with tooling held constant.
- r2 differs from r1 by the two documented repairs; any r1↔r2 comparison
  confounds those repairs with the grid rerun. This document does not make
  r1↔r2 comparisons — the r1 grid is evidence of non-engagement only.
