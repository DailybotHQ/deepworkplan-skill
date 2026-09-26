# v6 telemetry — complete run cost accounting and host adapters

The metering layer ([`scripts/evaluation/v6/adapters/`](../../../scripts/evaluation/v6/adapters/))
gives every attempted run — including failures — one closed resource record,
and reconciles record sums against expected totals with unknowns visible.

## The meter record (closed shape)

- **Identity**: run id, campaign, cell, arm; the pinned **stratum** (host +
  model + version + capability flags). A stratum mismatch is a refusal, not
  a silent model substitution.
- **Provider counters**: `input_tokens`, `output_tokens`,
  `cached_input_tokens`, `reasoning_tokens` — each recorded ONLY from an
  exposed meter, with its source named. A counter the host does not expose
  is `"unknown"`: never zero, never imputed, and a true zero stays distinct
  from unknown.
- **Cost class**: `invoiced` (provider billing), `list_price` (computed at
  dated public rates — requires the rate date) or `unavailable` (reason
  recorded). Bytes are never converted to tokens or money.
- **Behavior fields**: process time, build/test time, searches, repeated
  reads, repeated gates, workspace edits.
- **Interventions** by category (missing intent, new authority, environment
  repair, engineering rescue) and required authorization questions — counted
  separately from product outcomes.
- **Final status** for every attempted run: completed / failed / timeout /
  ineligible / blocked.

## Reconciliation

`adapters/reconcile.py` sums records and compares against expected totals
(synthetic generator before campaigns; provider billing samples when
available) at a documented tolerance (default 2%). A field with any unknown
contribution is listed as `has_unknowns` and cannot reconcile numerically —
unknown is never treated as zero. The full pipeline is validated against
synthetic usage records before a bounded real canary.

## Host adapters and counter sources

| Adapter | Launch | Counter source | Status |
| --- | --- | --- | --- |
| `fake` | deterministic synthetic actor | generated; totals reconcile by construction | validated |
| `claude` | `claude -p … --output-format json` | JSON response `usage` block (to confirm at canary) | discovered at canary |
| `codex` | `codex exec …` | session-log token usage (to confirm at canary) | discovered at canary |

Two strata (claude and codex CLIs) are the preregistered pair. If a second
host cannot be configured, cross-host claims are blocked while single-host
development stays possible — the posture is recorded per campaign, never
papered over.

## Canary policy

A canary is ONE bounded trivial call per adapter (short timeout), whose only
purpose is discovering whether counters are exposed and where. It is never a
paid campaign and never part of scoring. Results — counters available,
fields seen, or the honest reason they are not — land in the calibration
record. Credentials stay in the environment; nothing secret is written to
artifacts.

## Hygiene

Traces are sanitized at capture and export; API credentials never enter
records or logs; monetary figures name invoiced vs dated-list-rate basis;
missing data is reported missing.
