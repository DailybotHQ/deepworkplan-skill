# Reproducing what was actually run

Confirmation, long-horizon and external campaigns **were not run**.
This package reproduces development r1, ablation r2 fragments, and
the blocked freeze. It does not reproduce a G5 result.

## Tree

- Branch: `feat/dwp-v6-verified-autonomy`
- Candidate: `skills/deepworkplan/` (149 files). Manifest:
  `.dwp/plans/PLAN_v6_verified_autonomy/analysis_results/CANDIDATE_MANIFEST.json`
  (gitignored working copy; digest `e8d44eebf27a710a29c1b88a58e75521fa5db42e29566910d1fe1a917c04d66e`).
- Ablation configs: `tests/evaluation/v6/campaigns/ablations*.json` (commit `24d0927`).
- Oracle commitments: plan `analysis_results/lab/oracle-commitments-4ebff28.json`.
- Frozen cases: `tests/evaluation/v6/baselines/` (do not open hidden cases).

## Replay development scoring (no new paid cells)

```bash
# Configs only (r2):
python3 scripts/evaluation/v6/lab.py validate \
  --config tests/evaluation/v6/campaigns/ablations2-service-full.json

# Calibrated score of an existing campaign directory (example):
# requires the gitignored lab tree under
# .dwp/plans/PLAN_v6_verified_autonomy/analysis_results/lab/ablations/
```

Inventories live under gitignored `.dwp/`. A third party with only the
git tree can re-validate configs, oracles, and unit suites; they cannot
recompute campaign scores without the `.dwp/` lab export.

## Suites (no actors)

```bash
python3 scripts/validate-frontmatter.py
python3 scripts/check-schema-contract.py
python3 scripts/check-guide-migration.py
bats tests/
shellcheck setup.sh skills/deepworkplan/shared/context.sh \
  skills/deepworkplan/verify/conformance.sh scripts/*.sh
```

This session: frontmatter 16/16; schema-contract 25/25; guide-migration
OK; bats 595 ok / 0 not ok; shellcheck clean.

## What not to replay until unblocked

Do not invent `confirmation.json` and launch it. Task 25 freeze status
is `blocked` (`PREREGISTRATION.md`, `FREEZE_RECORD.json`). A future run
needs Claude quota after 2026-10-03, a live custodian, and a **new**
freeze identity.
