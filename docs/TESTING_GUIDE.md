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
