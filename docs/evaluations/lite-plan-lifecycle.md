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

## Behavioral boundary — an explicit acceptance gap

These checks prove **representation and guardrails**. They do **not** prove that
an agent harness makes good Lite-versus-Full recommendations, nor that ordinary
language routes to DWP.

The following scenarios are specified in the design but **have not been run in an
agent harness at this revision**, and are therefore recorded as an open gap, not
as a pass:

- ordinary-language small planning discovery (positive routing), including
  non-English phrasing;
- direct-action requests staying direct (negative routing);
- guided retain-after-review, and guided edit-then-promote;
- trust handoff with zero source writes;
- large trust Full handoff;
- interrupted promotion recovery driven by an agent rather than by a fixture;
- fresh-session Lite continuation through the Final Review.

No Lite-versus-Full efficiency comparison (artifact count, instruction bytes) was
measured here either. Nothing in this record may be cited as a token, cost or
latency saving.

A behavior-tested claim requires a fresh agent session, an isolated repository,
and the replay evidence protocol in [`../EVALUATION.md`](../EVALUATION.md). Until
such a replay is recorded, Lite recommendation quality and planning-intent
routing are reported as **structurally tested**, not behavior-tested.
