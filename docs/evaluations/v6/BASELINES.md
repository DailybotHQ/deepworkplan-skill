# v6 evaluation baselines — frozen comparators

This directory records the frozen comparators used by the v6 evaluation
campaigns, and how their integrity is enforced. Raw evidence lives in the
owning plan's `analysis_results/lab/`; this file is the sanitized,
contributor-facing methods record.

## What "latest v5" means

The v5 comparator is the **highest stable published v5 SemVer tag** of the
upstream repository (`DailybotHQ/deepworkplan-skill`), resolved from live
upstream refs at the freeze boundary, with prereleases excluded. It is never
the vendored dogfood mirror (`.agents/skills/deepworkplan/`, which lags the
shipped source by design), never a mutable `main`, and never a cached web
page.

The tag's **peeled commit** and a full-pack checksum are recorded so the
export is reproducible and auditable. The comparator never changes during a
campaign. If a newer v5 exists at the confirmation freeze, it becomes a **new
recorded comparator** and the affected calibration is redone — the old freeze
is retained as history, not silently replaced.

## Current freeze (baseline freeze, 2026-09-26)

| Field | Value |
| --- | --- |
| Comparator | latest-v5 |
| Tag | `v5.5.4` |
| Peeled commit | `7d571cef0bde3955bf5fb9593ab1a209cbe237b3` |
| Resolution source | live `git ls-remote origin` (highest stable v5 tag; prereleases excluded) |
| Snapshot | `tmp/repositories/dwp-v6-lab/packs/v5/v5.5.4-2f1c7e62017b6b60` |
| Snapshot digest (SHA-256 of `SHA256SUMS`) | `2f1c7e62017b6b60fdc082e93e86c2e785aaab02c4f9801be3c99a5fcb91b267` |
| Files in snapshot | 131 |
| Contents | `pack/` (shipped DWP v5.5.4), `ai-diff-reviewer/` (v3.1.1, the skills-lock pin), `review/extension.md`, licenses and provenance |
| Export method | `git archive <peeled commit> skills/deepworkplan \| tar -x` — a real copy; live symlinks are prohibited |
| Integrity check | `python3 tests/evaluation/v6/baselines/verify_snapshot.py` |
| Machine-readable record | [`tests/evaluation/v6/baselines/latest-v5.json`](../../../tests/evaluation/v6/baselines/latest-v5.json) |

Provenance and license notes live inside the snapshot itself
(`PROVENANCE.md`, `LICENSE-repo-root`; the source repository is MIT).

## Version drift visible at this freeze

These are recorded harness facts, not comparator choices:

| Surface | Version | Role |
| --- | --- | --- |
| Shipped source (`skills/deepworkplan/`) | 5.5.4 | equals the v5.5.4 tag; the **comparator** |
| Vendored dogfood (`.agents/skills/deepworkplan/`) | 5.4.0 | repo-adapted working copy; **never** the benchmark comparator |
| Vendored `ai-diff-reviewer` | 3.1.1 | control reviewer differences explicitly |
| Vendored `dailybot` | 3.16.1 (refreshed 2026-09-26; 3.14.0 at baseline) | reporting addon; not used in scoring |

Both addon rows are the freeze snapshot of 2026-09-26. Since the freeze the
vendored copies moved to `ai-diff-reviewer` 3.2.2 and `dailybot` 3.23.2
(2026-10-01); neither is used in scoring, so the freeze values stand.

The shipped-source and dogfood drift is owned by the repo's normal
refresh procedure (`scripts/refresh-dogfood-skill.sh`), not by the evaluation
lab; it is recorded here because it is the reason a naive reader could mistake
the dogfood for the baseline.

## Verifying integrity

```bash
python3 tests/evaluation/v6/baselines/verify_snapshot.py
```

The checker re-hashes every snapshot file, compares against the snapshot's
`SHA256SUMS` manifest and the recorded digest, refuses any symlink inside the
snapshot, and spot-checks the frozen pack's `version:` frontmatter. A
mismatch fails with a nonzero exit and lists the differing manifest lines —
a changed snapshot invalidates any campaign evidence that relied on it.

A deliberate re-freeze (for example, a newer v5 at the confirmation freeze)
updates `latest-v5.json` and regenerates the manifest with
`verify_snapshot.py --write` into a **new** `<tag>-<digest>` directory; the
previous freeze is kept.

## Recheck policy

The upstream tag list was re-checked live at this baseline freeze. It is
re-checked again before the confirmation campaign freezes its final inputs;
a changed latest-v5 at that boundary requires a new recorded comparator and
recalibration of the affected experiment blocks before any confirmation run.
