#!/usr/bin/env bats

@test "installed verifier enforces lifecycle contracts across Lite and Full" {
  run python3 "$BATS_TEST_DIRNAME/lifecycle_contract_test.py"
  [ "$status" -eq 0 ]
}
