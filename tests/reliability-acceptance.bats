#!/usr/bin/env bats
# Lifecycle-level acceptance scenarios F0-F8 (tests/reliability/PROTOCOL.md).
#
# F0 is the clean control; F9 was added after the live runs found that a plan
# authored exactly as the pack documents could not pass the pack itself.
#: a whole plan driven through the shipped writer,
# completion transaction and read-only checker over a real workspace. F1-F8
# inject one fault each at the moment it would really occur and require the
# refusal at the named boundary, with the plan still recoverable.
#
# Run with:  bats tests/
# Requires:  bats-core, git, python3

@test "lifecycle acceptance scenarios F0-F8 (clean control + injected faults)" {
  run python3 -m unittest tests.reliability_acceptance_test -v
  echo "$output"
  [ "$status" -eq 0 ]
  # A suite that silently selected nothing is never a pass.
  [[ "$output" == *"Ran 16 tests"* ]]
}
