# Lite/Full lifecycle evaluation record

This record states what the Lite/Full change proves at this revision and what it
does not. It deliberately separates deterministic contract coverage from an
agent-behavior claim.

## Deterministic scenarios

`bats tests/lite-plans.bats` exercises these scenarios against the installed-pack
paths:

| Scenario | Oracle | Expected result |
| --- | --- | --- |
| Ready Lite plan | `verify/conformance.sh --plan` | Passes with inline anchors, task records and Final Review; no task files required. |
| Unsafe Lite locator | v2 JSON Schema | Fails; `../escape.md` cannot escape the plan. |
| Boundary grammar | create skill text contract | Documents `trust`/`auto`, `lite`/`full`, either-edge ordering, conflict rejection and direct-edit protection. |
| Legacy state | schema-contract fixtures | Retains the v1 schema path. |

`python3 scripts/check-schema-contract.py` additionally dispatches each plan by
its declared schema URL and rejects unknown schema URLs rather than treating a
future plan as legacy. Its v2 probe covers the Lite schema and an invalid
locator.

## Behavioral boundary

These checks prove representation and guardrails, not that every agent harness
will make the same complexity recommendation. A behavior-tested claim requires a
fresh agent session, an isolated repository, and the replay evidence protocol in
[`../EVALUATION.md`](../EVALUATION.md). Until such a replay is recorded, Lite
recommendation quality is reported as **structurally tested**, not
behavior-tested.
