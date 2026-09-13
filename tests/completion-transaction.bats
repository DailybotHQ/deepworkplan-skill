#!/usr/bin/env bats
@test "candidate publication validates real artifacts and recovers interruptions" {
  run python3 "$BATS_TEST_DIRNAME/completion_test.py" -v
  echo "$output"
  [ "$status" -eq 0 ]
}
