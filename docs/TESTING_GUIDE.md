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
| Read tiers | `bats tests/execute-read-contract.bats tests/resume-read-contract.bats` | measurement, authoring, final review |
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
