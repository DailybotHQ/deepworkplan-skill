# v6 evaluation lab — driver interface and isolation posture

The lab driver is [`scripts/evaluation/v6/lab.py`](../../../scripts/evaluation/v6/lab.py)
(contributor-only; never shipped in the pack). It implements the interface the
[lab blueprint](https://github.com/DailybotHQ/deepworkplan-skill) proposed and
Task 4 owns. Regression coverage: `tests/evaluation/v6/test_runner.py`
(`python3 -m unittest discover -s tests/evaluation/v6 -p 'test_*.py'`).

## Interface

```bash
python3 scripts/evaluation/v6/lab.py self-test
python3 scripts/evaluation/v6/lab.py validate  --config tests/evaluation/v6/campaigns/smoke.json
python3 scripts/evaluation/v6/lab.py prepare   --family <name> [--dry-run] --config <campaign.json>
python3 scripts/evaluation/v6/lab.py run       --config <campaign.json> --output <dir> [--resume <attempt-id>]
python3 scripts/evaluation/v6/lab.py score     --config <campaign.json> --output <dir>
python3 scripts/evaluation/v6/lab.py analyze   --config <campaign.json> --output <dir>
```

The driver itself never opens a network connection. Live campaign tasks run
`prepare` → `run` → `score` → `analyze`, in that order; scoring on absent or
fabricated data fails (`analyze` refuses without `SCORES.json`).

## What validate refuses

- **Incomplete budgets:** a campaign marked `paid` while the preregistered
  `design.json` resource envelope is `UNSET` (the same rule as
  `cost_calculator.py gate`).
- **Mutable pack references:** arm packs must be real directories named
  `<tag>-<digest>` under the lab `packs/`; a symlink to an evolving checkout,
  or a ref-shaped path, is refused.
- **Escape and traversal:** seed or output paths containing `..`, paths
  escaping the repository, and symlinks anywhere inside a seed.
- **Unsupported isolation claims:** a campaign with
  `requires_enforced_isolation: true` is refused on a host that cannot enforce
  it (see the posture below).
- **Collisions:** `run` into a non-empty output directory, or `prepare` over an
  existing seed identity — a rerun gets a new identity, it never overwrites.

## Isolation posture (stated, not implied)

| Capability | Status on a plain contributor host |
| --- | --- |
| Workspace isolation | provided: fresh disposable per-cell workspaces, unique attempt IDs |
| Memory/env isolation | provided at process level: scrubbed minimal environment, scratch `HOME`, pinned `TZ=UTC`/`LC_ALL=C` |
| Host-enforced isolation (containers, separate enforced users) | **not claimed**; reported as `false` unless a real enforcement mechanism wrote the `custodian/ENFORCED` marker |
| Enforced custodian separation | **not claimed** by default; campaigns requiring it are refused (confirmation stays blocked per the preregistration) |

Every attempt records this posture in its `ISOLATION.json`.

## Contamination canaries

Each attempt writes a random-token canary into `actor_invisible/` outside the
workspace but inside the attempt. After every actor run the driver verifies
(1) the canary file is byte-unchanged, and (2) the token appears in **no**
workspace file — catching both tampering and exfiltration reads. Either
check failing marks the cell `ineligible` with the reason recorded; failed
cells are retained, never deleted.

## Attempt inventory, timeouts, recovery

Results append to `attempts.jsonl` (one closed JSON record per cell: hashes
before/after, exit code, duration, canary result, env keys, log pointer).
Actors run with `start_new_session` and a per-cell timeout; on expiry the
whole process group is killed and the cell records `timeout`. `--resume
<attempt-id>` skips cells that already have terminal records — interrupted
campaigns recover without repeating completed work, and records prove what
was skipped.

## Scoring and analysis

`score` applies the campaign's oracles to the artifacts, never to narration:
`file_contains`, `file_exists`, `exit_zero_file`. A missing artifact scores
`UNVERIFIED` — a failure, never a pass — matching the house oracle rule
(`tests/reliability/oracles/score-acceptance.py`). `analyze` aggregates
per-arm eligible/passed counts and lists ineligible cells.

## The fake-actor boundary

The smoke campaign (`tests/evaluation/v6/campaigns/smoke.json`) drives the
whole pipeline with a deterministic fake actor and the real frozen v5 pack
snapshot as arm B's reference. Fake-actor runs are **orchestration evidence
(reproduction level 2)**: they prove the apparatus, never agent behavior.
Live-agent runs (level 3) require the `exec` launch mode, a real campaign
config, and the resource envelope; confirmation-grade claims additionally
require enforced custodian separation, which must come from the host.
