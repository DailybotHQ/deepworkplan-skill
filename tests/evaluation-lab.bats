# Lab runner guarantees: pack content chain (D15 F4), confirmation partition
# requirements (D15 F1/F6), inventory chain tamper-evidence (D15 F3), and the
# orchestration self-test with manifest-verified packs.
#
# Self-contained: every fixture is synthesized under BATS_TEST_TMPDIR; the
# repository's real packs, seeds and campaign configs are never touched.

REPO="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
LAB="${LAB:-$REPO/scripts/evaluation/v6/lab.py}"
WORK=""

setup() {
  WORK="$BATS_TEST_TMPDIR/work"
  # The seed must live at a repo-relative path (absolute paths are refused
  # as escapes); tmp/ is the repo's gitignored scratch space.
  SEED_REL="tmp/lab-bats/$(basename "$BATS_TEST_TMPDIR")/seed"
  SEED_ABS="$REPO/$SEED_REL"
  rm -rf "$REPO/tmp/lab-bats/$(basename "$BATS_TEST_TMPDIR")"
  mkdir -p "$SEED_ABS/src" "$WORK/labroot/packs/vtest"
  printf 'smoke seed\n' > "$SEED_ABS/README.md"
  printf "print('hello')\n" > "$SEED_ABS/src/app.py"
}

# Build a pack with a REAL export-form manifest under
# $WORK/labroot/packs/vtest/<tag>-<digest16> and echo the directory name.
_make_pack() {
  local tag="$1" mutate="${2:-}"
  local stage="$WORK/labroot/packs/vtest/${tag}-staging"
  rm -rf "$stage" "$WORK/labroot/packs/vtest/${tag}-"*
  mkdir -p "$stage"
  printf '%s\n' "$tag" > "$stage/PACK_MARKER"
  python3 - "$stage" <<'PY'
import hashlib, sys
from pathlib import Path
stage = Path(sys.argv[1])
entries = sorted(
    (p for p in stage.rglob("*") if p.is_file()),
    key=lambda p: ("./" + p.relative_to(stage).as_posix()).encode(),
)
lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  ./{p.relative_to(stage).as_posix()}"
         for p in entries]
manifest = "\n".join(lines) + "\n"
digest = hashlib.sha256(manifest.encode()).hexdigest()
(stage / "SHA256SUMS").write_text(manifest)
# the digest is read back below from the stored manifest
PY
  local digest16
  digest16="$(python3 - "$stage" <<'PY'
import hashlib, sys
from pathlib import Path
stage = Path(sys.argv[1])
print(hashlib.sha256((stage / "SHA256SUMS").read_bytes()).hexdigest()[:16])
PY
)"
  mv "$stage" "$WORK/labroot/packs/vtest/${tag}-${digest16}"
  if [ -n "$mutate" ]; then
    printf 'tampered\n' >> "$WORK/labroot/packs/vtest/${tag}-${digest16}/PACK_MARKER"
  fi
  echo "${tag}-${digest16}"
}

# Write a development-partition campaign config referencing the named pack.
_write_cfg() {
  local pack="$1" extra="${2:-}" out="$3"
  python3 - "$pack" "$extra" "$out" "$SEED_REL" <<'PY'
import json, sys
from pathlib import Path
pack, extra, out, seed_rel = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
cfg = {
    "schema": "deepworkplan-skill/evaluation/v6/campaign/1",
    "name": "labtest",
    "paid": False,
    "arms": {"A": None, "B": {"pack": f"packs/vtest/{pack}"}},
    "seed": {"path": seed_rel, "family": "labtest"},
    "tasks": [{"id": "T-1", "prompt": "produce solution.txt"}],
    "strata": [{"name": "fake", "launch": {"mode": "fake", "command": "/bin/true"}}],
    "repeats": 1,
    "oracles": [{"id": "O1", "kind": "exit_zero_file", "path": "solution.txt"}],
}
if extra:
    cfg.update(json.loads(extra))
Path(out).write_text(json.dumps(cfg))
PY
}

@test "lab validate: pack content is re-hashed and a mutated snapshot is refused (D15 F4)" {
  local good bad
  good="$(_make_pack good)"
  bad="$(_make_pack bad mutate)"
  _write_cfg "$good" "" "$WORK/good.json"
  _write_cfg "$bad" "" "$WORK/bad.json"

  run python3 "$LAB" validate --lab-root "$WORK/labroot" --config "$WORK/good.json"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "config valid"

  run python3 "$LAB" validate --lab-root "$WORK/labroot" --config "$WORK/bad.json"
  [ "$status" -eq 1 ]
  echo "$output" | grep -q "pack content digest"
  echo "$output" | grep -q "snapshot changed after export"
}

@test "lab validate: a pack without SHA256SUMS cannot verify its content (D15 F4)" {
  mkdir -p "$WORK/labroot/packs/vtest/bare-deadbeefdeadbeef"
  printf 'x\n' > "$WORK/labroot/packs/vtest/bare-deadbeefdeadbeef/PACK_MARKER"
  _write_cfg "bare-deadbeefdeadbeef" "" "$WORK/bare.json"
  run python3 "$LAB" validate --lab-root "$WORK/labroot" --config "$WORK/bare.json"
  [ "$status" -eq 1 ]
  echo "$output" | grep -q "carries no SHA256SUMS manifest"
}

@test "lab validate: confirmation partition requires quota protections and frozen oracle bindings (D15 F1/F6)" {
  local pack
  pack="$(_make_pack conf)"

  # Nothing frozen yet: all four requirement errors fire.
  _write_cfg "$pack" '{"partition": "confirmation"}' "$WORK/conf-empty.json"
  run python3 "$LAB" validate --lab-root "$WORK/labroot" --config "$WORK/conf-empty.json"
  [ "$status" -eq 1 ]
  echo "$output" | grep -q "max_starts_per_hour"
  echo "$output" | grep -q "budget_stop_per_provider"
  echo "$output" | grep -q "cooldown_on_quota_minutes"
  echo "$output" | grep -q "oracle_bindings"

  # Quota fields present, bindings malformed: per-entry errors fire.
  local quota='{"partition": "confirmation", "quota_protections": {"max_starts_per_hour": 6, "budget_stop_per_provider": 300, "cooldown_on_quota_minutes": 300}, "oracle_bindings": [{"case": "NOPE", "digest": "xyz"}]}'
  _write_cfg "$pack" "$quota" "$WORK/conf-bad.json"
  run python3 "$LAB" validate --lab-root "$WORK/labroot" --config "$WORK/conf-bad.json"
  [ "$status" -eq 1 ]
  echo "$output" | grep -q "matches no task id"
  echo "$output" | grep -q "64-hex sha256"
  echo "$output" | grep -q "missing cases present in the campaign"

  # Fully frozen: valid.
  local ok='{"partition": "confirmation", "quota_protections": {"max_starts_per_hour": 6, "budget_stop_per_provider": 300, "cooldown_on_quota_minutes": 300}, "oracle_bindings": [{"case": "T-1", "digest": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"}]}'
  _write_cfg "$pack" "$ok" "$WORK/conf-ok.json"
  run python3 "$LAB" validate --lab-root "$WORK/labroot" --config "$WORK/conf-ok.json"
  [ "$status" -eq 0 ]
}

@test "lab analyze: a broken inventory chain refuses analysis (D15 F3)" {
  local out="$WORK/out"
  mkdir -p "$out"
  python3 - "$out" "$SEED_REL" <<'PY'
import hashlib, json, sys
from pathlib import Path
out, seed_rel = Path(sys.argv[1]), sys.argv[2]
cfg = {
    "schema": "deepworkplan-skill/evaluation/v6/campaign/1", "name": "chainlab",
    "paid": False, "arms": {"A": None},
    "seed": {"path": seed_rel, "family": "chainlab"},
    "tasks": [{"id": "T-1", "prompt": "p"}],
    "strata": [{"name": "fake", "launch": {"mode": "fake", "command": "/bin/true"}}],
    "repeats": 1, "oracles": [],
}
(out.parent / "chainlab.json").write_text(json.dumps(cfg))
(out / "SCORES.json").write_text(json.dumps({
    "c1": {"arm": "A", "status": "completed", "canary_intact": True,
           "oracles": {"O1": ["PASS", "ok"]}},
    "c2": {"arm": "A", "status": "completed", "canary_intact": True,
           "oracles": {"O1": ["PASS", "ok"]}},
}))
rows = [{"cell_id": "c1", "status": "completed", "canary_intact": True, "chain": None},
        {"cell_id": "c2", "status": "completed", "canary_intact": True}]
raws = [json.dumps(r) for r in rows]
raws[1] = json.dumps({**rows[1], "chain": hashlib.sha256(raws[0].encode()).hexdigest()})
(out / "attempts.jsonl").write_text("\n".join(raws) + "\n")
PY
  run python3 "$LAB" analyze --config "$WORK/chainlab.json" --output "$out"
  [ "$status" -eq 0 ]
  [ -f "$out/ANALYSIS.md" ]

  # Relabel the first record; the second record's chain no longer reproduces.
  python3 - "$out" <<'PY'
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
lines = (out / "attempts.jsonl").read_text().splitlines()
first = json.loads(lines[0]); first["cell_id"] = "cX"
lines[0] = json.dumps(first)
(out / "attempts.jsonl").write_text("\n".join(lines) + "\n")
PY
  run python3 "$LAB" analyze --config "$WORK/chainlab.json" --output "$out"
  [ "$status" -ne 0 ]
  echo "$output" | grep -q "inventory chain broken"
}

@test "lab self-test: orchestration passes with manifest-verified packs" {
  run python3 "$LAB" self-test
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "self-test OK"
}

# The r3 pilot recovery, replayed in miniature: quota-killed cells leave
# workspace and scratch-HOME residue behind while the contaminated inventory
# is renamed away. A resume must re-run those cells from the seed and never
# inherit (or crash on) the killed predecessor's tree.
@test "lab run --resume: a re-run cell wipes killed-predecessor residue and rebuilds from the seed" {
  local pack attempt cells cell
  pack="$(_make_pack runres)"
  _write_cfg "$pack" "" "$WORK/runres.json"
  # A minimal fake actor: writes its artifact and exits 0 (mode "fake"
  # prepends sys.executable to the repo-relative command path).
  rm -rf "$REPO/tmp/lab-bats/actor"
  mkdir -p "$REPO/tmp/lab-bats/actor"
  cat > "$REPO/tmp/lab-bats/actor/actor.py" <<'PYACTOR'
import sys
from pathlib import Path
ws = Path(sys.argv[sys.argv.index('--workspace') + 1])
(ws / 'solution.txt').write_text('ok')
PYACTOR
  python3 - "$WORK/runres.json" <<'PY'
import json, sys
from pathlib import Path
cfg_path = Path(sys.argv[1])
cfg = json.loads(cfg_path.read_text())
cfg["strata"][0]["launch"]["command"] = "tmp/lab-bats/actor/actor.py"
cfg_path.write_text(json.dumps(cfg))
PY

  # run refuses output paths that escape the repository: keep the attempt
  # tree repo-relative, like the seed (tmp/ is gitignored scratch).
  local out_rel out_abs
  out_rel="tmp/lab-bats/$(basename "$BATS_TEST_TMPDIR")/out"
  out_abs="$REPO/$out_rel"
  cd "$REPO"
  run python3 "$LAB" run --lab-root "$WORK/labroot" --config "$WORK/runres.json" --output "$out_rel"
  [ "$status" -eq 0 ]
  [ "$(wc -l < "$out_abs/attempts.jsonl")" -eq 2 ]

  # Quota-contamination procedure, exactly as r3: inventory renamed away,
  # residue stays on disk. Poison it so inheritance would be visible.
  mv "$out_abs/attempts.jsonl" "$out_abs/attempts.jsonl.quota-contaminated"
  attempt="$(ls "$out_abs" | grep -v jsonl | head -1)"
  for cell in T-1-fake-r1-A T-1-fake-r1-B; do
    # A killed predecessor leaves residue behind (a completed run deletes
    # the scratch HOME; a quota-killed one dies before that cleanup).
    mkdir -p "$out_abs/$attempt/workspaces/$cell" "$out_abs/$attempt/homes/$cell"
    echo POISON > "$out_abs/$attempt/workspaces/$cell/POISON.txt"
    echo POISON > "$out_abs/$attempt/homes/$cell/stale.session"
  done

  run python3 "$LAB" run --lab-root "$WORK/labroot" --config "$WORK/runres.json" --output "$out_rel" --resume "$attempt"
  [ "$status" -eq 0 ]
  [ "$(wc -l < "$out_abs/attempts.jsonl")" -eq 2 ]
  grep -q '"status": "completed"' "$out_abs/attempts.jsonl"
  for cell in T-1-fake-r1-A T-1-fake-r1-B; do
    [ ! -e "$out_abs/$attempt/workspaces/$cell/POISON.txt" ]
    [ ! -e "$out_abs/$attempt/homes/$cell/stale.session" ]
    [ -f "$out_abs/$attempt/workspaces/$cell/TASK.md" ]
    [ -f "$out_abs/$attempt/workspaces/$cell/solution.txt" ]
  done
}
