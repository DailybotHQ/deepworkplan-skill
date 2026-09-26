#!/usr/bin/env bats
# Regression coverage for the frozen-baseline snapshot integrity checker
# (tests/evaluation/v6/baselines/verify_snapshot.py).
#
# Self-contained by design: every case builds a synthetic snapshot in a
# scratch directory and points the checker at it with --baseline. No case
# reads, writes, or depends on the real lab snapshot, so the suite runs in CI
# where that snapshot does not exist.

setup() {
  CHECKER="${BATS_TEST_DIRNAME}/evaluation/v6/baselines/verify_snapshot.py"
  SCRATCH="$(mktemp -d)"
  SNAPSHOT="${SCRATCH}/snapshot"
  BASELINE_JSON="${SCRATCH}/latest-v5.json"
  mkdir -p "${SNAPSHOT}/pack"
  printf 'demo payload\n' > "${SNAPSHOT}/pack/a.txt"
  printf -- '---\nname: demo\nversion: "9.9.9"\n---\nbody\n' > "${SNAPSHOT}/pack/SKILL.md"
  printf 'MIT\n' > "${SNAPSHOT}/LICENSE.txt"
  # Freeze the synthetic snapshot with the same procedure the real freeze
  # used, then record its digest in a baseline record for the checker. The
  # manifest is written OUTSIDE the snapshot and moved in, so the enumeration
  # can never race with the manifest's own creation.
  ( cd "$SNAPSHOT" && find . -type f ! -name SHA256SUMS | LC_ALL=C sort | xargs sha256sum > "$SCRATCH/manifest.tmp" )
  mv "$SCRATCH/manifest.tmp" "$SNAPSHOT/SHA256SUMS"
}

teardown() {
  rm -rf "$SCRATCH"
}

write_baseline() {
  local digest version="${1:-9.9.9}"
  digest="$(sha256sum "${SNAPSHOT}/SHA256SUMS" | cut -d' ' -f1)"
  cat > "$BASELINE_JSON" <<EOF
{
  "comparator": "test",
  "tag": "vTest.0.0",
  "peeled_commit": "0123456789abcdef0123456789abcdef01234567",
  "snapshot": {
    "path": "$SNAPSHOT",
    "digest": "$digest",
    "files": 3,
    "manifest": "SHA256SUMS"
  },
  "pack": { "path": "pack", "version": "$version" }
}
EOF
}

verify() {
  python3 "$CHECKER" --baseline "$BASELINE_JSON"
}

@test "intact snapshot verifies OK" {
  write_baseline
  run verify
  [ "$status" -eq 0 ]
  [[ "$output" == *"OK test frozen"* ]]
}

@test "a modified file fails verification" {
  write_baseline
  printf 'tampered\n' >> "${SNAPSHOT}/pack/a.txt"
  run verify
  [ "$status" -eq 1 ]
  [[ "$output" == *"FAIL snapshot changed"* ]]
}

@test "an added file fails verification" {
  write_baseline
  printf 'extra\n' > "${SNAPSHOT}/pack/extra.txt"
  run verify
  [ "$status" -eq 1 ]
  [[ "$output" == *"FAIL snapshot changed"* ]]
}

@test "a deleted file fails verification" {
  write_baseline
  rm "${SNAPSHOT}/pack/a.txt"
  run verify
  [ "$status" -eq 1 ]
  [[ "$output" == *"FAIL snapshot changed"* ]]
}

@test "a live symlink inside the snapshot fails verification" {
  write_baseline
  ln -s /etc/hostname "${SNAPSHOT}/pack/link.txt"
  run verify
  [ "$status" -eq 1 ]
  [[ "$output" == *"live symlinks"* ]]
}

@test "a wrong frozen pack version fails the semantic spot-check" {
  write_baseline "8.8.8"
  run verify
  [ "$status" -eq 1 ]
  [[ "$output" == *"does not match recorded"* ]]
}

@test "a digest recorded from a different snapshot fails" {
  write_baseline
  python3 - "$BASELINE_JSON" <<'PYEOF'
import json, sys
path = sys.argv[1]
record = json.loads(open(path, encoding="utf-8").read())
record["snapshot"]["digest"] = "0" * 64
open(path, "w", encoding="utf-8").write(json.dumps(record, indent=2))
PYEOF
  run verify
  [ "$status" -eq 1 ]
  [[ "$output" == *"does not match recorded"* ]]
}

@test "a missing snapshot directory fails" {
  write_baseline
  mv "$SNAPSHOT" "${SNAPSHOT}-gone"
  run verify
  [ "$status" -eq 1 ]
  [[ "$output" == *"missing"* ]]
}

@test "--write re-freezes a deliberately changed snapshot and it verifies again" {
  write_baseline
  printf 'new content\n' > "${SNAPSHOT}/pack/replacement.txt"
  rm "${SNAPSHOT}/pack/a.txt"
  run python3 "$CHECKER" --baseline "$BASELINE_JSON" --write
  # The digest recorded in the baseline is now stale, so verification itself
  # still fails until the record is refreshed -- a re-freeze is a new identity.
  [ "$status" -eq 1 ]
  new_digest="$(sha256sum "${SNAPSHOT}/SHA256SUMS" | cut -d' ' -f1)"
  python3 - "$BASELINE_JSON" "$new_digest" <<'PYEOF'
import json, sys
path, digest = sys.argv[1], sys.argv[2]
record = json.loads(open(path, encoding="utf-8").read())
record["snapshot"]["digest"] = digest
open(path, "w", encoding="utf-8").write(json.dumps(record, indent=2))
PYEOF
  run verify
  [ "$status" -eq 0 ]
}
