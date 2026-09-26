#!/usr/bin/env bats
# tests/evaluation-score-pilot.bats — end-to-end coverage for
# tests/evaluation/v6/oracles/score_pilot.py on a synthetic service-family
# lab: inventory parsing, terminal/eligible bucketing, oracle resolution,
# unscored-case handling, atomic report writes, --list dryness, and the
# structural exit codes. The oracles are the REAL calibrated ones; only the
# lab inventory and workspaces are synthetic.

setup() {
  REPO="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  SCORER="$REPO/tests/evaluation/v6/oracles/score_pilot.py"
  SEED="$REPO/tests/evaluation/v6/fixtures/service/seed"
  CASES="$REPO/tests/evaluation/v6/oracles/cases"
}

_build_lab() {
  # $1: lab root. Six cells covering every bucket the scorer distinguishes:
  # ok (eligible PASS), bad (eligible FAIL, sabotaged workspace), tampered
  # (completed but canary tripped -> recorded, never eligible), timeout
  # (terminal, ineligible, missing workspace -> ERROR that must NOT count),
  # running (non-terminal -> SKIPPED), tea (unknown case token -> unscored).
  LAB="$1"
  SVC="$LAB/service"
  mkdir -p "$SVC/att1/workspaces" "$SVC/att2/workspaces" "$SVC/att3/workspaces"
  cp -r "$SEED" "$SVC/att1/workspaces/cell-ok"
  cp -r "$SEED" "$SVC/att3/workspaces/cell-tampered"

  # cell-bad: the case module's own sabotage guarantees a FAIL verdict.
  PYTHONDONTWRITEBYTECODE=1 python3 - "$CASES/service_sc2_sc4.py" \
    "$SEED" "$SVC/att2/workspaces/cell-bad" <<'PY'
import importlib.util
import shutil
import sys
from pathlib import Path

case_py, seed, dst = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
shutil.copytree(seed, dst)
spec = importlib.util.spec_from_file_location("svc_case", case_py)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.sabotage_sc2(dst)
PY

  PYTHONDONTWRITEBYTECODE=1 python3 - "$SVC/attempts.jsonl" <<'PY'
import json
import sys

rows = [
    {"cell_id": "cell-ok", "arm": "v5", "stratum": "claude-code", "repeat": 1,
     "task": "SC-2 add a lookup endpoint", "attempt": "att1",
     "workspace": "workspaces/cell-ok", "status": "completed",
     "exit_code": 0, "canary_intact": True},
    {"cell_id": "cell-bad", "arm": "no-dwp", "stratum": "claude-code", "repeat": 1,
     "task": "SC-2 add a lookup endpoint", "attempt": "att2",
     "workspace": "workspaces/cell-bad", "status": "completed",
     "exit_code": 0, "canary_intact": True},
    {"cell_id": "cell-tampered", "arm": "no-dwp", "stratum": "codex", "repeat": 1,
     "task": "SC-2 add a lookup endpoint", "attempt": "att3",
     "workspace": "workspaces/cell-tampered", "status": "completed",
     "exit_code": 0, "canary_intact": False},
    {"cell_id": "cell-timeout", "arm": "v5", "stratum": "codex", "repeat": 2,
     "task": "SC-2 add a lookup endpoint", "attempt": "att4",
     "workspace": "workspaces/cell-timeout", "status": "timeout",
     "exit_code": 124, "canary_intact": None},
    {"cell_id": "cell-running", "arm": "v5", "stratum": "codex", "repeat": 2,
     "task": "SC-2 add a lookup endpoint", "attempt": "att5",
     "workspace": "workspaces/cell-running", "status": "running",
     "exit_code": None, "canary_intact": None},
    {"cell_id": "cell-tea", "arm": "v5", "stratum": "claude-code", "repeat": 3,
     "task": "ZZ-9 make tea", "attempt": "att6",
     "workspace": "workspaces/cell-tea", "status": "completed",
     "exit_code": 0, "canary_intact": True},
]
with open(sys.argv[1], "w", encoding="utf-8") as fh:
    for row in rows:
        fh.write(json.dumps(row) + "\n")
PY
}

@test "score_pilot: scores a synthetic service lab end-to-end" {
  _build_lab "$BATS_TEST_TMPDIR/lab"

  run python3 "$SCORER" --lab-root "$BATS_TEST_TMPDIR/lab" --families service
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "oracle registry:"
  echo "$output" | grep -q "SC-2: function score_sc2 in service_sc2_sc4.py"
  echo "$output" | grep -q "AC-6: built-in oracle score_astro_ac6 (reference case reference/astro_ac6_skip_link.py)"
  echo "$output" | grep -q "SC-9: built-in oracle score_service_sc9"
  echo "$output" | grep -q "LC-3: built-in oracle score_legacy_lc3"

  SVC="$BATS_TEST_TMPDIR/lab/service"
  [ -f "$SVC/SCORES.json" ]
  [ -f "$SVC/SUMMARY.json" ]
  [ ! -e "$SVC/SCORES.json.tmp" ]

  PYTHONDONTWRITEBYTECODE=1 python3 - "$SVC" <<'PY'
import json
import sys
from pathlib import Path

svc = Path(sys.argv[1])
scores = json.loads((svc / "SCORES.json").read_text(encoding="utf-8"))
summary = json.loads((svc / "SUMMARY.json").read_text(encoding="utf-8"))

by_cell = {row["cell_id"]: row for row in scores["cells"]}

# Verdicts per bucket.
assert by_cell["cell-ok"]["verdict"] == "PASS", by_cell["cell-ok"]
assert by_cell["cell-ok"]["eligible"] is True
assert by_cell["cell-bad"]["verdict"] == "FAIL", by_cell["cell-bad"]
assert by_cell["cell-bad"]["eligible"] is True
assert by_cell["cell-bad"]["reasons"], "FAIL must carry reasons"

# Tampered canary: score recorded, eligibility withheld.
assert by_cell["cell-tampered"]["eligible"] is False
assert by_cell["cell-tampered"]["verdict"] in ("PASS", "FAIL")

# Timeout: terminal, ineligible; a missing workspace yields ERROR, which
# must not reach the errors counter because eligibility precedes bucketing.
assert by_cell["cell-timeout"]["terminal"] is True
assert by_cell["cell-timeout"]["eligible"] is False
assert by_cell["cell-timeout"]["verdict"] == "ERROR"

# Non-terminal and unscored cells are listed, never scored.
assert by_cell["cell-running"]["verdict"] == "SKIPPED"
assert by_cell["cell-tea"]["verdict"] == "SKIPPED"
assert by_cell["cell-tea"]["unscored_case"] is True

all_counts = summary["summary"]["ALL"]
assert all_counts["cells"] == 5, all_counts       # terminal cells only
assert all_counts["eligible"] == 2, all_counts
assert all_counts["passed"] == 1, all_counts
assert all_counts["failed"] == 1, all_counts
assert all_counts["errors"] == 0, all_counts      # ERROR on ineligible cell
assert all_counts["timeout"] == 1, all_counts
assert all_counts["not_terminal"] == 1, all_counts
assert all_counts["unscored"] == ["ZZ-9"], all_counts

v5 = summary["summary"]["v5"]
# v5 has four records but only three terminal cells (cell-running is not
# terminal): ok + timeout + tea.
assert v5["cells"] == 3 and v5["eligible"] == 1 and v5["passed"] == 1, v5
nod = summary["summary"]["no-dwp"]
assert nod["cells"] == 2 and nod["eligible"] == 1 and nod["failed"] == 1, nod

cases = {entry["case"] for entry in summary["unscored_cases"]}
assert cases == {"ZZ-9"}, summary["unscored_cases"]
print("summary assertions OK")
PY
}

@test "score_pilot: --list resolves and writes nothing" {
  _build_lab "$BATS_TEST_TMPDIR/lab-list"

  run python3 "$SCORER" --lab-root "$BATS_TEST_TMPDIR/lab-list" --families service --list
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "SC-2: function score_sc2 in service_sc2_sc4.py"
  echo "$output" | grep -q "AC-6: built-in oracle score_astro_ac6"
  echo "$output" | grep -q "LISTED"
  echo "$output" | grep -q "ZZ-9"

  SVC="$BATS_TEST_TMPDIR/lab-list/service"
  [ ! -e "$SVC/SCORES.json" ]
  [ ! -e "$SVC/SUMMARY.json" ]
}

@test "score_pilot: structural failures exit 2" {
  run python3 "$SCORER" --lab-root "$BATS_TEST_TMPDIR/does-not-exist"
  [ "$status" -eq 2 ]

  mkdir -p "$BATS_TEST_TMPDIR/empty-lab"
  run python3 "$SCORER" --lab-root "$BATS_TEST_TMPDIR/empty-lab" --families bogus
  [ "$status" -eq 2 ]
}

@test "score_pilot: oracle identity — dump, verify, refuse on tamper (D15 F1)" {
  _build_lab "$BATS_TEST_TMPDIR/lab-id"
  ID="$BATS_TEST_TMPDIR/id"
  mkdir -p "$ID"

  # Freeze the current oracle-identity table.
  run python3 "$SCORER" --dump-oracle-commitments "$ID/commitments.json"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "oracle commitments written"
  python3 - "$ID/commitments.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["schema"] == "deepworkplan-skill/evaluation/v6/oracle-commitments/1"
assert d["oracles"], "empty commitments table"
for token, prov in d["oracles"].items():
    assert prov["digest"] and len(prov["digest"]) == 64, token
    assert all(s["sha256"] and s["path"].endswith(".py") for s in prov["sources"]), token
print("commitments shape OK")
PY

  # A clean verification scores normally and stamps identities per record.
  run python3 "$SCORER" --lab-root "$BATS_TEST_TMPDIR/lab-id" --families service \
    --oracle-commitments "$ID/commitments.json"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "oracle commitments verified"
  python3 - "$BATS_TEST_TMPDIR/lab-id/service/SCORES.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d["oracle_commitments"]["mode"] == "verified", d["oracle_commitments"]
assert d["oracle_provenance"], "no report-level provenance"
stamped = [c for c in d["cells"] if c.get("oracle", {}).get("digest")]
assert stamped, "no per-cell oracle digest stamped"
for cell in stamped:
    assert len(cell["oracle"]["digest"]) == 64 and cell["oracle"]["sources"]
print("score records carry oracle identities")
PY

  # A tampered commitment table refuses before scoring, exit 1, nothing written.
  python3 - "$ID/commitments.json" "$ID/tampered.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
token = sorted(d["oracles"])[0]
d["oracles"][token]["digest"] = "0" * 64
json.dump(d, open(sys.argv[2], "w"))
PY
  rm -f "$BATS_TEST_TMPDIR/lab-id/service/SCORES.json" "$BATS_TEST_TMPDIR/lab-id/service/SUMMARY.json"
  run python3 "$SCORER" --lab-root "$BATS_TEST_TMPDIR/lab-id" --families service \
    --oracle-commitments "$ID/tampered.json"
  [ "$status" -eq 1 ]
  echo "$output" | grep -q "REFUSING TO SCORE"
  [ ! -e "$BATS_TEST_TMPDIR/lab-id/service/SCORES.json" ]
  [ ! -e "$BATS_TEST_TMPDIR/lab-id/service/SUMMARY.json" ]

  # A frozen token missing from the live registry also refuses.
  python3 - "$ID/commitments.json" "$ID/extra.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
d["oracles"]["ZZ-0"] = {"digest": "1" * 64, "sources": []}
json.dump(d, open(sys.argv[2], "w"))
PY
  run python3 "$SCORER" --lab-root "$BATS_TEST_TMPDIR/lab-id" --families service \
    --oracle-commitments "$ID/extra.json"
  [ "$status" -eq 1 ]
  echo "$output" | grep -q "missing from the live registry"
}
