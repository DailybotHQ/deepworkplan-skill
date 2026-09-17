# Testing guide

Run contributor commands from the repository root. The installed artifact is
`skills/deepworkplan/`; tests and contributor scripts must never be runtime
requirements. Python helpers use Python 3.9+ stdlib; shell supports Bash 3.2.

## Full validation commands

```bash
bats tests/
python3 scripts/validate-frontmatter.py
python3 scripts/check-schema-contract.py
python3 scripts/check-guide-migration.py
shellcheck setup.sh skills/deepworkplan/shared/context.sh skills/deepworkplan/verify/conformance.sh scripts/*.sh
git diff --check
```

Test-only Python dependencies: PyYAML (frontmatter), jsonschema (independent
Draft 2020-12 validation and several Bats cases). Bats and ShellCheck are
contributor tools. Missing dependencies are unavailable validation, not a pass.
The runtime validator must still work without third-party Python packages.

## Scoped invocation and source-to-test mapping

| Changed surface | Scoped command | Affected consumers |
|---|---|---|
| State updater | `bats tests/state-updater.bats tests/state-evidence.bats tests/state-transitions.bats` | execute, resume, verifier; widen to full for shared semantics |
| Plan verifier / schema | `bats tests/conformance-sh.bats tests/schema-contract.bats tests/lite-plans.bats` | all plan readers/writers; full suite required |
| Context/path detection | `bats tests/context-sh.bats` | every flow; shellcheck required |
| Installer | `bats tests/setup-sh.bats` | all host adapters; Linux/macOS setup CI |
| Guide links | `python3 scripts/check-guide-migration.py` | flow read paths |
| Read tiers | `bats tests/execute-read-contract.bats tests/resume-read-contract.bats tests/context-accounting.bats` | measurement, authoring, final review |
| Instruction accounting | `bats tests/context-accounting.bats` + `bash tests/efficiency/measure-instruction-load.sh` | the read tiers of every flow, `tests/efficiency/paths.tsv`, the published evidence record |
| Activation / routing surface | `bats tests/activation-contract.bats` | router, onboard flow, delegator templates, generated command kits, capability docs |
| Claims / version stamps / helper inventory | `bats tests/claims-consistency.bats` | TRUST.md, spec footers, contributor docs, the published claim table |
| Lifecycle end to end (writer + finalizer + checker) | `bats tests/reliability-acceptance.bats` | every flow that closes a task or publishes a plan; widen to full Bats |
| CI workflow | `bats tests/ci-guarantees.bats` | every suite CI runs; the installer's sub-skill list; the documented Python floor |
| Packaging / ship boundary | `bats tests/packaging-reliability.bats` | everything a downstream user installs; the dogfood mirror; the published schemas |
| Working-principles onboarding / upgrade | `bats tests/packaging-reliability.bats tests/activation-contract.bats` then full Bats | installed resource discovery, routing, contributor `AGENTS.md` budget and links; inspect semantic coverage and reconciliation separately |
| Frontmatter | `python3 scripts/validate-frontmatter.py` | all sub-skill discovery |

Repository example: a change to `shared/update-state.py` starts with the
state-updater/state-evidence selection above, then runs full Bats because
execution and verification consume the same state. A documentation-only
spelling fix uses link/frontmatter checks when relevant and `git diff --check`.

## Selection, blind spots and escalation

Require a nonempty TAP plan and actual executed assertions. Bats exits zero
for some empty/filtered selections: zero selected is never success. Review
skips explicitly; the existing installer auto-detection scenario may skip when
an agent binary is present, but required schema/lifecycle cases must execute.

Consumer policy: instruction files, templates, fixtures, schemas and CI can
change behavior despite their extension. Dynamic relative references, generated
dogfood files and model interpretation are blind spots of file mapping. Widen
to the full suite for shared/core, configuration, schema, dependency or toolchain
changes, unknown consumers or unavailable scoped selection. Explicit fallback:
use `bats tests/` and all applicable full commands above; if those cannot run,
record a blocker. Never use no-test or missing-tool flags to create a pass.

## Validation posture

Unit and subprocess tests prove helper behavior. Text-presence tests protect
instructions, not model compliance. Independent schema validation checks
serialization, not semantic acceptance. Live agent observations require actual
flow entry and fresh context, with pinned inputs and complete attempt records.
Final Review runs all applicable full checks on the final source and mirror.
Record command, cwd, selection, source/dirty fingerprint, dependency versions,
exit code, counts and recoverable evidence. Reuse only equivalent inputs.

## Completion transaction

`bats tests/completion-transaction.bats` runs independent Lite/Full publication
fixtures and before/after-publication fault injection. Run full Bats for changes
to the shared validator, writer or finalizer. Required tests must not be skipped.

## Scope and evidence truth

`bats tests/scope-evidence.bats` runs the checker and the guarded writer
against sanitized contradictions derived from the historical false-completion
case: passing evidence that admits non-execution, a completed task whose log
says pending, and refine-invalidated evidence that must be rerun before
closure. Its last case is a labeled contract-presence check on the docs. Widen
to full Bats for any change to `shared/state_contract.py`, `update-state.py`
or `verify/plan_contract.py`.

## Resume integrity and workspace persistence

`bats tests/resume-integrity.bats` runs hostile-but-valid paths (spaces,
metacharacters, quotes, backslashes) through `shared/context.sh` and a JSON
parser, exercises a fresh `git clone` without the gitignored `.dwp/` against
a complete transferred plan folder, and refuses dangling or escaping `log=`
evidence pointers at both the guarded writer and the read-only checker. The
state-replacement desync boundary is asserted in both directions; the last
case is a labeled contract-presence check on the resume flow, `dwp-paths.md`
and the specs. Widen to full Bats for any change to `shared/context.sh`,
`shared/state_contract.py` or the resume flow.

## Flow activation and portability

`bats tests/activation-contract.bats` checks that every delegator template
(and this repository's own generated `.agents/commands/` kit) routes to a
sub-skill that actually ships, placeholder-free and thin, with by-name
invocation for hosts without slash commands; that the intent-to-flow routing
block onboarding installs carries every activation property (planning
creates, execute/resume invoke, status/verify read-only, direct edits never
silently become plans, trust is not a flow selector, local discovery); that
capability fallbacks and the no-parity-claim rule are stated; and that the
activation surface is vendor-model-neutral and free of stale series claims.
Tests over real template and kit files are behavioral oracles on those
artifacts; the intent-mapping and wording cases are labeled
contract-presence checks — they prove the contract is taught, never that a
model routes live requests reliably (that is behavioral evidence, recorded
per harness in `docs/COMPATIBILITY.md`). Widen to full Bats for any change
to the router, the onboard flow or the command templates.

## Instruction accounting

`bats tests/context-accounting.bats` guards the two numbers the pack
publishes about its own instruction surface: the **entry bundle** a flow loads
at t0, and the **end-to-end paths** its named triggers add. The paths, their
phases and their literal triggers live in `tests/efficiency/paths.tsv`; the
suite fails when the manifest names a file the pack does not have, or one the
governing flow's `## Shared resources` section does not declare — so the
measurement can never drift from the read contract it models. It also asserts
the disclosures (`Repeated reads`, `Phase triggers`, `Exclusions`, `What this
measurement is not`), that a path total equals the sum of its **distinct**
files, and that a create simplification is a real path change rather than a
relabel: a Lite creation must load no guide file, and the Full path must still
count the companions it loads. Its injected-failure control appends a row
naming a nonexistent file and requires a nonzero exit — a broken reference
must never measure as zero bytes. Widen to full Bats for any change to a
flow's read tiers, the measurement script or the manifest. Results and their
limits: `docs/evaluations/v5-reliability.md`.

## Claims consistency

`bats tests/claims-consistency.bats` pins the statements the pack makes about
itself to the pack itself: the quoted sub-skill count is counted from the tree,
the helper inventory in `TRUST.md` is derived from the shipped `*.py`/`*.sh`
files, and every spec document's methodology footer is compared against the
standard the checker enforces (`SUPPORTED_SPEC` in `verify/plan_contract.py`) —
so a superseded stamp fails rather than lingering. It also asserts that
documentation closure is stated as **one** policy (current inside the task that
touched the surface; swept, not deferred, by the Final Review) and that the
retired absolutes do not return: guaranteed local/CI output parity, and the
two adaptation ratios that were quoted as if measured (the suite carries the
exact patterns; naming them again here would trip its own scan). Finally it requires every row of the published
claim table in `docs/evaluations/v5-reliability.md` to carry an explicit
limitation. Widen to full Bats for any change to the spec documents, `TRUST.md`
or the closure rules in `execute/SKILL.md`.

## Lifecycle acceptance

`bats tests/reliability-acceptance.bats` drives a whole plan through the
shipped helpers over a real workspace — the guarded writer, the completion
transaction and the read-only checker together — rather than testing each in
isolation. F0 is the clean control: implement, test, log, commit, close, publish,
verify, all passing. F1–F8 inject one fault each at the moment it would really
occur (non-execution evidence, a zero-test selection, malformed state, evidence
a `refine` invalidated, a log that still says pending, an unresolvable `log=`
pointer, a finalization interrupted after its marker, unrelated dirty work) and
require the refusal at the **named** boundary — which is not always the one an
author would assume, so each scenario asserts where the refusal actually comes
from. The protocol, workload and oracles are frozen in `tests/reliability/`.
Widen to full Bats for any change to `shared/state_contract.py`,
`shared/update-state.py`, `shared/finalize_plan.py` or `verify/plan_contract.py`.

The **live** fresh-context runs behind the same protocol are scored by
`python3 tests/reliability/oracles/score-acceptance.py <run-dir>` and recorded,
separately labelled, in `docs/evaluations/v5-reliability.md`. Deterministic
scenarios are never reported as if they were live evidence.

## CI actually running what it claims

`bats tests/ci-guarantees.bats` pins the workflow's own guarantees, because a
CI job has two ways to go **green while verifying nothing** and neither looks
like a failure: its required cases can all *skip* for want of a dependency, and
its selection can match *no tests at all*. Both happened here — the bats job
ran without `jsonschema`, so every schema, lifecycle and Lite-plan case skipped
silently.

The workflow now installs the test-only Python packages, reads the TAP plan and
fails below a floor, and fails on any `# skip` other than the single documented
environment-dependent case. The suite derives its expectations from the
repository rather than from a second copy of the workflow: the dependency list
comes from what the tests actually import under a skip guard, the installer's
sub-skill list from `setup.sh`'s own `SKILLS` array, and the shell-lint
coverage from every `*.sh` the repo ships. It also asserts that the
deterministic gate needs **no** secret, no credential and nothing from the
gitignored `.dwp/` — the reliability guarantees must reproduce from a clean
checkout alone. Live agent evaluations stay local and on-demand by design
(`tests/reliability/PROTOCOL.md`); CI reproduces only the deterministic half.

A `python-floor` job runs the shipped helpers on Python 3.9 with no
third-party package installed — asserting `jsonschema` is *absent* so the
stdlib-only path is the one under test — compiles each helper, runs the
read-only checker over a real fixture plan, and fails if any `__pycache__`
survives inside the hash-pinned pack. Before it existed, the "Python 3.9+
stdlib" claim in this guide was never exercised: every other job runs 3.11 with
both optional packages present.

## Packaging integrity

`bats tests/packaging-reliability.bats` runs the shipped helpers from an
**exported** copy of `skills/deepworkplan/` in a scratch directory, with no
`tests/`, `scripts/`, contributor docs or repository checkout anywhere near it
— the shape a downstream user actually installs. A helper that quietly reaches
back into this repository passes every other suite and fails for everyone else,
so this one checks the boundary from the outside: no contributor file inside the
pack, no runtime reference to one, no network call, a missing interpreter
producing **UNVERIFIED** rather than a pass, byte-unchanged published schema
snapshots, a byte-identical dogfood mirror, and sanitized evidence files that
each record their round and real tree state. Widen to full Bats for any change
to the ship boundary, the schemas or `scripts/refresh-dogfood-skill.sh`.
