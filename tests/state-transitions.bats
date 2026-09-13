#!/usr/bin/env bats
@test "state writer rejects invalid transitions and preserves evidence" {
  run python3 "$BATS_TEST_DIRNAME/state_transitions_test.py" -v
  echo "$output"
  [ "$status" -eq 0 ]
}
