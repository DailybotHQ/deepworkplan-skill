# Efficiency evaluation of the proposed DWP 2.3.0 contract

The upgrade reduces the declared mandatory instruction surface for creating and
executing a plan. The evidence does **not** establish a general reduction in
provider tokens, billing, or end-to-end time. Detailed requirements, fault
detection and final validation remain constraints on any efficiency claim.

This evaluation compares the installed pack at baseline
`eaf54994ac5894b74849f1b8d2b6137df8d83e30` with the review-corrected candidate identified by
[its static provenance record](token-efficiency-data/static-candidate-provenance.json).
The instrumented trials below remain pinned to `d4ffe58`; they were not rerun.
Package version, methodology version and schema URL version are distinct; this
candidate is an unreleased branch snapshot. Later instruction edits require new
static measurements and affected behavioral checks before making a final-release
claim. Source revisions and content digests are in
[the protocol](token-efficiency-data/protocol.json).

## Reproduce the observations

From the contributor checkout:

```bash
python3 tests/efficiency/summarize-paired.py
bash tests/efficiency/measure-instruction-load.sh
bats tests/efficiency-fixtures.bats
```

The summarizer reads committed baseline/candidate records and reports every pair.
It fails on inputs that are unexpectedly absent, and reports — without failing —
the arms the protocol explicitly records as never run, so an unfinished
experiment stays visible instead of quietly shrinking the denominator. The shell script measures the current pack, so its output
may differ after later edits. To reproduce a historical static row, export that
exact revision's `skills/deepworkplan` into an isolated directory and pass the
export root to the shell script. An export is labeled as such; the enclosing git
checkout's HEAD is not its provenance. The script's byte/4 field is only an
estimate; this report uses filesystem bytes throughout.

## Declared mandatory instruction surface

The metric counts the router, selected sub-skill and Markdown links in its
explicit essential-resource section. It includes routing overhead. It excludes
conditional reads, repository files, tool output and generated plans. It is a
one-level static inventory, not a reconstruction of everything an agent loads.

| Flow | Baseline bytes | Candidate bytes | Change |
| --- | ---: | ---: | ---: |
| Create | 145,087 | 85,020 | −41.4% |
| Execute | 142,506 | 77,996 | −45.3% |
| Resume | 38,186 | 73,659 | +92.9% |
| Refine | 122,761 | 61,352 | −50.0% |
| Onboard | 157,503 | 68,522 | −56.5% |
| Status | 13,363 | 17,222 | +28.9% |
| Verify | 29,581 | 42,563 | +43.9% |

[Baseline records](token-efficiency-data/static-baseline.txt) and
[candidate records](token-efficiency-data/static-candidate.txt) include every
counted file. Create and execute meet the preregistered 40% static target.
Resume's increase partly reflects explicit execution-resource links absent from
the baseline's direct resource list; it does not prove an 85% increase in actual
resume cost. Status and verification contain additional recovery/compatibility
instructions. Total installed Markdown grows from 738,989 to 981,895 bytes
(+32.9%): progressive loading trades a larger complete pack for narrower common
entry paths. No claim that the whole package became smaller is supported.

## Agent replay interpretation

Historical Claude Code replays supplied useful behavioral evidence and exposed
read-scope defects. They used self-reported byte counts and included corrections
between runs. Their single-pair percentages cannot support a general quantitative
session claim; the corrected candidate must not be pooled with its earlier
revision. The retained scorecard is historical evidence, not a provider meter.

An instrumented comparison was preregistered for three fresh-context Codex pairs
with identical initial repositories and a frozen pack per arm. **It was not
completed, and it produces no claim.** Three of the six arms
(`pair2-candidate`, `pair3-baseline`, `pair3-candidate`) were never run. The
three arms that did run — `pair1-baseline`, `pair1-candidate`, `pair2-baseline` —
were each cut off by orchestration before final closure, at *different* points
in the fixture plan (4, 1 and 1 completed tasks respectively).

Every attempted arm is retained in
[the records](token-efficiency-data/protocol.json) with `outcome: "stopped"`,
because deleting an inconvenient run is how an evaluation lies. But a byte
difference between two runs that stopped at unequal progress measures how far
each got, not how efficiently it worked. The summarizer therefore withholds a
delta for any pair whose arms did not both complete, and reports
`instrumented_claim_eligible: false`. For the record and against our own
interest: in the one attempted pair, the candidate arm read *more* pack bytes
(179,503) than the baseline (145,388) while completing *fewer* fixture tasks —
which is exactly what a truncated, non-comparable run looks like, and is
reported here rather than discarded. A failed or partial outcome cannot become
a successful efficiency result merely by reading fewer bytes, and this dataset
supports no session-level conclusion in either direction.

Runs share a host and overlap, so wall-clock measurements are descriptive and
cannot demonstrate latency improvement. Provider input, output, cached-input and
reasoning counters are unavailable. The exact provider model identifier and cache
state are not independently instrumented. Capture covers file reads and shell
output; harness framing, reasoning and editing-tool responses are outside that
measurement. These observations concern this harness and fixture only.

## Validation cost and counterexamples

[Command records](token-efficiency-data/gate-observations.json) contain three
pairs for an isolated seeded fault and three for a shared-core consumer fault.
The candidate selects the relevant module for the isolated case and widens to the
full suite for shared-core; the baseline uses the full suite. All twelve actual
commands detect their seeded fault. These are fixed command-policy experiments,
separate from autonomous selection in a replay.

The suites are tiny. Process startup and selection overhead can outweigh any
reduction in test count; running the full suite can be the simpler sound choice.
The shared-core fixture covers a real multi-module dependency, but does not model
a costly production suite. No production-test-time claim follows. Cold resume and
long-history recovery have historical candidate behavioral evidence; they do not
yet have a three-pair instrumented efficiency comparison. Do not extrapolate a
create result to those workloads or describe the static difference as a universal
upper bound on actual savings.

## Claims that can ship

| Claim | Evidence and boundary |
| --- | --- |
| Declared create/execute instruction bytes fall by 41.4%/45.3% in this snapshot | Reproducible static inventory; not tokens or live-session savings |
| Conditional loading avoids requiring the complete guide on the common entry path | Explicit resource declarations plus the static file list |
| Relevant fault detection must survive narrower validation | Seeded isolated and shared-core command records; behavior remains a hard gate |
| Any instrumented live-session comparison (reads, output, commands) | **Not established.** The preregistered three-pair run was not completed: 3 of 6 arms never ran, the other 3 were truncated at unequal progress. Records retained; no delta computed |
| General token, billing, latency or cross-harness savings | Unsupported; do not publish |
| Savings for costly production suites or long-history execution | Not established by this bounded dataset |
| Universal losslessness or superiority over another methodology | Not established and not a goal of this evaluation |

Direct plan creation removes the intermediate draft only in trust mode;
conditional instruction loading changes required input; affected validation
changes command selection; bounded context changes historical retrieval. These
mechanisms interact. This evaluation does not causally assign a percentage to
each one. Security review, final validation, bookkeeping, retries and optional
work requested by a user remain part of a completed outcome.
