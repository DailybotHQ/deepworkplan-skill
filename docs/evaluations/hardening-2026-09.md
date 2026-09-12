# Final-hardening evaluation record — 2026-09

This record documents what was **actually measured** during the final hardening
pass on branch `fix/methodology-final-hardening` (parser repairs, lifecycle and
orchestrator contracts, addon-consent reconciliation, long-plan machinery,
Context enforcement, the 4.x standard alignment, the `/dwp-upgrade` sub-skill).
It lists the exact commands, baseline revisions, digests and results so a future
evaluator can reproduce every number in the reproducible sections below. It
**adds to** the evaluation history; it does not rewrite it. The older records
keep their own scope and limits:

- [`token-efficiency.md`](token-efficiency.md) — the 2.3.0-era trials stay
  frozen at `d4ffe58` (pre-2.4.0 draft-first flow); zero completed pairs.
- [`cross-agent-handoff.md`](cross-agent-handoff.md),
  [`adoption-pilot.md`](adoption-pilot.md),
  [`lite-plan-lifecycle.md`](lite-plan-lifecycle.md) — unchanged.

## Standing limits, stated plainly

- **Live-agent superiority remains unverified.** No paired agent experiment ran
  during this hardening — not for speed, quality, token use or cost. Nothing in
  this record may be cited as one.
- The instruction numbers are **filesystem bytes** of Markdown files. They are
  not provider tokens, not cost; the script's `/4` column is a labeled estimate.
- The growth documented below is the byte cost of hardening the pack **chose to
  add** (corpus-proven long-plan machinery, always-declared parallelization,
  Context enforcement, standard 4.x alignment, upgrade routing). Progressive
  loading is preserved: no flow's compulsory read set gained a file.

## Baselines

| Label | Revision | What it is |
|---|---|---|
| v3.0.0 | tag `v3.0.0` | the released v3 product baseline |
| 4.0.3 | `1e23cc9` | package 4.0.3 exactly as released, before this hardening began |
| final | `6847ea1` | the hardening branch after its last `skills/deepworkplan/` change (task 16 commit; tasks 17–18 add only measurement and this record) |

The measurement script is byte-identical at all three revisions —
`tests/efficiency/measure-instruction-load.sh` has md5
`da7709ce883306638ea66f41c1189337` at `v3.0.0`, `1e23cc9` and `6847ea1` — so
the three columns are directly comparable.

## Method

For each revision: export the committed tree with `git archive` into a scratch
directory (no working tree, no dirty state), then run the committed script
against that export. The script reads only files under `skills/deepworkplan/`
and reports, per flow, the compulsory read set: the router `SKILL.md`, the
sub-skill `SKILL.md`, and the shared-resource files the sub-skill names as
essential.

## Instruction load per flow (filesystem bytes)

| Flow | v3.0.0 | 4.0.3 (`1e23cc9`) | final (`6847ea1`) | final vs 4.0.3 | final vs v3.0.0 |
|---|---:|---:|---:|---:|---:|
| create | 85,271 | 95,647 | 99,573 | +4.1 % | +16.8 % |
| execute | 79,300 | 82,309 | 83,615 | +1.6 % | +5.4 % |
| resume | 74,965 | 77,251 | 78,315 | +1.4 % | +4.5 % |
| onboard | 68,849 | 68,767 | 69,903 | +1.7 % | +1.5 % |

Read-set **composition** is unchanged in every flow across all three baselines:
each flow reads the same files at v3.0.0, 4.0.3 and final. Growth is byte growth
in already-read files, never a new always-read file. The new
`upgrade/SKILL.md` sub-skill adds zero bytes to every flow — it is read only
when `/dwp-upgrade` is invoked (pinned by `tests/upgrade-subskill.bats`).

Per-file attribution of the 4.0.3 → final growth (compulsory-read files only):

| File | Bytes | Why it grew |
|---|---:|---|
| `guide/authoring.md` | +2,626 | Stage Gates §4.3 + enriched Plan Variables (long-plan machinery); sequential-declaration teaching; Context pointers |
| `create/SKILL.md` | +843 | always-declared parallelization decision (Step 2.10); Stage Gates trigger; 4.0.0 stamps |
| `onboard/SKILL.md` | +679 | addon-consent wording; 4.0.0 stamps; upgrade wording |
| `execute/SKILL.md` | +590 | approval wording; sequential execution rule; 4.0.0 stamps |
| `SKILL.md` (router) | +457 | upgrade routing row + description + harness-upgrade paragraph |
| `spec/PLAN_STATE.md` | +259 | version-series note (read by the execute flow) |
| `resume/SKILL.md` | +17 | approval wording |

This table is a different measurement from the frozen 2.3.0-era static record
in [`token-efficiency.md`](token-efficiency.md); do not mix the two.

## Candidate content digest

The shipped pack at the final revision, as a digest any evaluator can recompute:

```text
git archive --format=tar 6847ea1 -- skills/deepworkplan | sha256sum
1f291db896524c012059564e41772eefb615689d26fac98a87613c945f5b8312
```

The commit that carries this record adds only this file and touches nothing
under `skills/deepworkplan/`, so the digest is equally valid at that commit —
verify with `git diff --stat 6847ea1 <this-commit> -- skills/deepworkplan`
(expected: empty).

## Contract suite at the candidate

At `6847ea1` (and unchanged at this record's commit, which is docs-only):

- `bats tests/` — 253 tests, all passing (includes the mutants that pin the
  parser repairs, orchestrator template execution, addon-consent matrix,
  long-plan machinery, Context enforcement, standard-series rule, and the
  upgrade sub-skill).
- `python3 scripts/validate-frontmatter.py` — 15 SKILL.md files valid.
- `python3 tests/efficiency/summarize-paired.py` — still reports the frozen
  trials with **zero completed pairs** (the honest denominator; this hardening
  added none).
- `python3 scripts/check-schema-contract.py` — 16 checks, 0 problems.

## Observed during the hardening, not reproducible from this repository

Recorded for completeness, explicitly **not** reproducible here because the
corpus lives in a consumer repository's private, gitignored `.dwp/`:

- Re-running the repaired checker over that repository's 11 real plans moved
  the reported findings from 69 (before the parser repairs) to 48, with the
  remainder categorized as genuine historical records left as authored. The
  parser repairs themselves are pinned deterministically in
  `tests/lifecycle_contract_test.py`.
- Landing Context enforcement (plan-level Goal+Context pair, task-level
  Context for v2+ tasks not yet completed) changed that same recheck count by
  **zero** — completed records stayed as authored, by design.

No number in this section is evidence of anything about live agent behavior.

## Reproduce

From a contributor checkout of this repository:

```bash
# instruction load, three baselines (script byte-identical across refs)
for r in v3.0.0 1e23cc9 6847ea1; do
  git show "$r:tests/efficiency/measure-instruction-load.sh" | md5sum   # da7709ce…
done
rm -rf /tmp/m && mkdir -p /tmp/m/v3 /tmp/m/v403 /tmp/m/final
git archive v3.0.0  | tar -x -C /tmp/m/v3
git archive 1e23cc9 | tar -x -C /tmp/m/v403
git archive 6847ea1 | tar -x -C /tmp/m/final
bash /tmp/m/v3/tests/efficiency/measure-instruction-load.sh /tmp/m/v3
bash /tmp/m/v403/tests/efficiency/measure-instruction-load.sh /tmp/m/v403
bash /tmp/m/final/tests/efficiency/measure-instruction-load.sh /tmp/m/final

# candidate digest
git archive --format=tar 6847ea1 -- skills/deepworkplan | sha256sum

# contract suite at the candidate (isolated worktree; leave your checkout alone)
git worktree add /tmp/hardening-eval 6847ea1
cd /tmp/hardening-eval
bats tests/
python3 scripts/validate-frontmatter.py
python3 tests/efficiency/summarize-paired.py
python3 scripts/check-schema-contract.py
```

Numbers may legitimately differ only if `skills/deepworkplan/` changed since
`6847ea1`; the digest comparison above detects exactly that.

## Released tree (v5.0.0 — `ab1337d`)

The "final" baseline above is `6847ea1`, the hardening branch after its last
`skills/deepworkplan/` change. The release then landed one more pack commit
(`199ec1b`: author-sub-skill hardening, plan-local `analysis_results` contract —
the latter edited `shared/dwp-paths.md`, which is in every flow's compulsory
read set) plus the version stamp. For the released tag the numbers are:

| Flow | final (`6847ea1`) | **released v5.0.0 (`ab1337d`)** | delta |
|---|---:|---:|---:|
| create | 99,573 | 100,012 | +439 |
| execute | 83,615 | 84,128 | +513 |
| resume | 78,315 | 78,754 | +439 |
| onboard | 69,903 | 70,342 | +439 |

Measured with the same method (git-archive export, committed script — md5
`da7709ce…` unchanged at `ab1337d`); read-set composition is unchanged —
growth is byte growth in already-read files. Digest of the released pack:

```text
git archive --format=tar ab1337d -- skills/deepworkplan | sha256sum
ae8c1577cc6bb08c638464af06a8ea768b216618894a4fc45c22585239819f2b
```

Contract suite at the released tag: **258 tests, 257 passing** — the release
stamp rewrote every `version:` frontmatter to `5.0.0` but no test literals,
leaving one hardcoded `4.0.3` pin red (`tests/upgrade-subskill.bats` test 1;
the stamp commit is `[skip ci]`, so CI did not surface it). Fixed on branch
`feat/v5-phase2` by deriving the pin from the router's own frontmatter. That
branch also adds the two missing command-kit templates and Lite-Context
authoring fixes, touching `onboard/SKILL.md` and `create/SKILL.md` — the next
release should cut a fresh row here rather than extrapolate.

Recorded 2026-09-12 during the v5 phase-2 field validation (finding F1-1:
the record previously stopped at `6847ea1` and called it "final" while the
shipped tree differed).
