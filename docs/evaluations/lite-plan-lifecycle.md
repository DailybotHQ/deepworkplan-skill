# Lite/Full lifecycle evaluation record

This record states what the Lite/Full change proves at this revision and what it
does not. It deliberately separates deterministic contract coverage from an
agent-behavior claim.

## Deterministic scenarios

`bats tests/lite-plans.bats` builds throwaway mutants of the committed fixture at
`tests/fixtures/lite-plan/` and asserts that each unsafe shape is refused with an
actionable message, not merely that the prose describing it exists.

| Scenario | Oracle | Expected result |
| --- | --- | --- |
| Ready, approved Lite plan | `verify/conformance.sh --plan` | Passes with inline anchors, task records and Final Review; no task files required. |
| Ready but unapproved proposal | `verify/conformance.sh --plan` | Structurally valid, reported as an advisory — approval is a separate axis from validity. |
| Unknown approval value | `verify/conformance.sh --plan` | Fails rather than being coerced to a known state. |
| Interrupted materialization | `verify/conformance.sh --plan` | Fails; `create`/`refine` must complete or discard it. |
| Unresolved promotion marker | `verify/conformance.sh --plan` | Fails as a recovery boundary; execute/resume must not run a mixed shape. |
| Duplicate task anchor | `verify/conformance.sh --plan` | Fails; an ID must resolve to exactly one record. |
| Missing task anchor | `verify/conformance.sh --plan` | Fails; a locator may not dangle. |
| Gate-less Lite task | `verify/conformance.sh --plan` | Fails; Lite is compact, not ungated. |
| Non-contiguous task IDs | `verify/conformance.sh --plan` | Fails. |
| False `completed_count` | `verify/conformance.sh --plan` | Fails. |
| State claiming unchecked work | `verify/conformance.sh --plan` | Fails; the README checkbox index is canonical. |
| Missing Final Review | `verify/conformance.sh --plan` | Fails. |
| Checkboxes in a fenced example | `verify/conformance.sh --plan` | Passes — documentation is not progress. |
| Traversal / absolute / malformed locators | v2 JSON Schema | Rejected (`../escape.md`, `/etc/passwd`, `#task-0`, unknown `kind`). |
| Extra top-level state field | v2 JSON Schema | Rejected — v2 is closed, like v1. |
| Promoted Full plan (v2, `kind: file`) | v2 JSON Schema | Accepted; the locator grammar still binds. |
| Unknown future schema URL or format | v1 + v2 JSON Schemas | Refused by both — never guessed as legacy. |
| Legacy / v1 state | `scripts/check-schema-contract.py` fixtures | Unchanged; v1 documents and schema bytes are frozen. |
| Create contract | shipped-text assertions | `create/SKILL.md` names the v2 schemas and no longer offers a refined draft as the default output. |

`python3 scripts/check-schema-contract.py` additionally dispatches each plan by
its declared schema URL and rejects unknown URLs rather than treating a future
plan as legacy.

One defect was found by this suite rather than by review: the shared
`check_state_desync` helper counted `- [x]` lines without fence awareness, so a
fenced Markdown example in any plan README — Lite, Full or legacy — was reported
as a false desync. It is fixed and covered.

## Behavioral track — five scenarios actually run

| Field | Value |
| --- | --- |
| Harness | Claude Code |
| Model | Claude Opus 5 (1M context) |
| Fixture | Isolated throwaway git repo: a small Python service with a real `AGENTS.md` Quick Commands block (`pytest`, `compileall`), one pre-existing passing test, and the pack installed at `.agents/skills/deepworkplan/` |
| Oracle | `verify/conformance.sh --plan` on every artifact, plus the repo's own gates |
| Independence | **Low.** The runs were driven by the same session that authored the instructions. They prove the flow is executable and self-consistent; they are not an independent reproduction. |

| # | Scenario | Result |
| --- | --- | --- |
| B1 | `/dwp-create <small context>` (guided) | Lite plan materialized, `Approval: pending`, CONFORMANT with the proposal advisory. Six files, no task files, **nothing written under `.dwp/drafts/`**, and `git status` clean — creation touched no source. |
| B2 | `/dwp-create <small context> trust` | Lite plan, `approval: pre_approved`, CONFORMANT. Returned an execute command and did **not** execute; `git status` clean. |
| B3 | `/dwp-create full trust <large context>` | Full plan (4 tasks) materialized directly, CONFORMANT. Exercised the v2 Full path with `kind: file` locators end to end for the first time. |
| B4 | `/dwp-refine promote` on B1 | Marker → task files → authoritative switch → marker cleared last. Task IDs, acceptance criteria and gates carried over verbatim; `manifest.json` untouched (`plan_format` stays `lite` — it records the *creation* format); CONFORMANT after. While the marker was set, conformance refused the plan. |
| B5 | Execute B2's Task 1, interrupt, resume in a fresh session | Task 1 implemented against real source, gate passed and recorded; interruption left a coherent checkpoint. Resume identified Task 2 from the README index, the state locator and the checkpoint alone — no conversation history, no redo of Task 1, gate evidence preserved. The inline Final Review then closed the plan at 2/2, CONFORMANT. |

### Two defects the trials found that the test suite had not

1. **Double authoring on the `full` path.** Step 4.0's write order produced a
   Lite README and `state.json` with `format: "lite"` unconditionally, and only
   *then* branched to Step 4.4 — so `/dwp-create full trust` authored every task
   contract twice, once inline and once as a file, and wrote a state that
   contradicted its own manifest. Step 4.0 now decides the representation before
   the second write and branches; a trust Full plan never writes the Lite
   representation. This is the duplication the design requirements told the
   regression task to look for.
2. **Interrupted promotion got the wrong recovery message.** `check_lite_plan`
   tested `materialization != "ready"` before the promotion marker, so a real
   interrupted promotion — which sets *both* — always hit the generic
   "not ready … recover it with create/refine" and the dedicated promotion
   branch was unreachable. The existing test passed only because its mutant set
   the marker while leaving `materialization: ready`, an inconsistent state. The
   guards are reordered, and the test now asserts the canonical case.

### Measured artifact cost, same fixture

| Plan | Format | Files | Total | Task-contract bytes |
| --- | --- | ---: | ---: | ---: |
| B1 (small) | Lite | 6 | 6,347 B | 2,032 B |
| B2 (small) | Lite | 6 | 5,264 B | 1,637 B |
| B3 (large) | Full | 11 | 12,464 B | 6,208 B |

Lite and Full here describe *different work*, so this is not a like-for-like
comparison and no efficiency claim follows from it. What it does show is that a
small Lite plan carries a complete gated contract in ~1.6–2.0 KB with no
per-task files.

## Still not covered

These remain unexercised and are recorded as open gaps, not passes:

- **Natural-language routing (R11).** Every trial above was driven by an explicit
  `/dwp-create`. Whether "plan this small fix" activates DWP, whether a Spanish
  phrasing does, and whether "just fix this directly" correctly stays out of DWP
  were **not** tested. The routing corpus remains unrun.
- **Recommendation quality (R09).** B1–B3 confirm that a *chosen* format
  materializes correctly. They do not show that the rubric picks well on
  borderline work, and a single session cannot establish that.
- **Cross-harness reproduction.** One harness, one model, low independence.
- **Guided edit-then-promote**, as distinct from the direct promotion in B4.

A cross-harness claim requires the replay evidence protocol in
[`../EVALUATION.md`](../EVALUATION.md). Lite recommendation quality and
planning-intent routing stay reported as **not behavior-tested**.
