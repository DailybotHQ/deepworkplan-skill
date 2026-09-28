#!/usr/bin/env bats
# Regression coverage for the v6 experiment preregistration tooling:
# tests/evaluation/v6/protocol/design.json + cost_calculator.py.
# Self-contained: the calculator's self-test and validate/cost/gate modes run
# against the real tracked design and synthetic copies; no network, no agents.

setup() {
  CALC="${BATS_TEST_DIRNAME}/evaluation/v6/protocol/cost_calculator.py"
  DESIGN="${BATS_TEST_DIRNAME}/evaluation/v6/protocol/design.json"
  ASSUMPTIONS="${BATS_TEST_DIRNAME}/evaluation/v6/protocol/cost_assumptions.example.json"
  SCRATCH="$(mktemp -d)"
}

teardown() {
  rm -rf "$SCRATCH"
}

modify_design() {
  # $1 = python expression operating on `d` (the parsed design dict)
  python3 - "$DESIGN" "$SCRATCH/design.json" "$1" <<'PYEOF'
import json, sys
src, dst, expr = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.loads(open(src, encoding="utf-8").read())
exec(expr, {}, {"d": d})
open(dst, "w", encoding="utf-8").write(json.dumps(d, indent=2))
PYEOF
}

@test "calculator self-test passes" {
  run python3 "$CALC" self-test
  [ "$status" -eq 0 ]
  [[ "$output" == *"self-test OK"* ]]
}

@test "the tracked preregistered design validates" {
  run python3 "$CALC" validate "$DESIGN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK design.json"* ]]
}

@test "a partition count mismatch is refused" {
  modify_design "d['partitions']['confirmation']['starts'] = 999"
  run python3 "$CALC" validate "$SCRATCH/design.json"
  [ "$status" -eq 1 ]
  [[ "$output" == *"999"* ]]
}

@test "a launch-bar row without a limitation is refused" {
  modify_design "d['launch_bar'][0]['limitation'] = ''"
  run python3 "$CALC" validate "$SCRATCH/design.json"
  [ "$status" -eq 1 ]
}

@test "an estimand without a denominator is refused" {
  modify_design "d['estimands'][0]['denominator'] = ''"
  run python3 "$CALC" validate "$SCRATCH/design.json"
  [ "$status" -eq 1 ]
}

@test "cost projection refuses assumptions that are not dated planning estimates" {
  python3 - "$ASSUMPTIONS" "$SCRATCH/bad.json" <<'PYEOF'
import json, sys
a = json.loads(open(sys.argv[1], encoding="utf-8").read())
a["basis"] = "we made these numbers up"
open(sys.argv[2], "w", encoding="utf-8").write(json.dumps(a))
PYEOF
  run python3 "$CALC" cost "$DESIGN" --assumptions "$SCRATCH/bad.json"
  [ "$status" -eq 1 ]
  [[ "$output" == *"dated public list rates"* ]]
}

@test "cost projection computes confirmation totals from the assumptions" {
  total="$(python3 - "$DESIGN" "$ASSUMPTIONS" <<'PYEOF'
import json, sys
d = json.loads(open(sys.argv[1], encoding="utf-8").read())
a = json.loads(open(sys.argv[2], encoding="utf-8").read())
starts = d["partitions"]["confirmation"]["starts"]
rate = a["cost_per_start_usd"]["confirmation"]
print(round(rate * starts, 2))
PYEOF
)"
  run python3 "$CALC" cost "$DESIGN" --assumptions "$ASSUMPTIONS"
  [ "$status" -eq 0 ]
  [[ "$output" == *"$total"* ]]
}

@test "the launch gate refuses a synthetic unset envelope" {
  modify_design "d['resource_envelope'].update({'status': 'UNSET', 'per_run_cap': None, 'total_cap': None})"
  run python3 "$CALC" gate "$SCRATCH/design.json"
  [ "$status" -eq 1 ]
  [[ "$output" == *"LAUNCH REFUSED"* ]]
}

@test "the launch gate accepts the authorized real envelope" {
  run python3 "$CALC" gate "$DESIGN"
  [ "$status" -eq 0 ]
  [[ "$output" == *"envelope set"* ]]
}

@test "the launch gate accepts a set envelope" {
  modify_design "d['resource_envelope'].update({'status': 'SET', 'per_run_cap': 5.0, 'total_cap': 500.0})"
  run python3 "$CALC" gate "$SCRATCH/design.json"
  [ "$status" -eq 0 ]
}
