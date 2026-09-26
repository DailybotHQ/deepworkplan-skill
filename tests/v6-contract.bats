#!/usr/bin/env bats
# v6 contract + journal-event boundaries (Task 11, RFC draft-4 sections 3-4).
# Runtime half: skills/deepworkplan/shared/contract_v6.py (stdlib-only).
# Independent half: scripts/check-schema-contract.py v6 probes (jsonschema).
# Both halves share the committed fixtures tests/fixtures/v6/.

setup() {
    REPO_ROOT="$( cd "$BATS_TEST_DIRNAME/.." && pwd )"
    PACK="$REPO_ROOT/skills/deepworkplan"
    C6="$PACK/shared/contract_v6.py"
    FX="$REPO_ROOT/tests/fixtures/v6"
    TMPDIR_TEST="$(mktemp -d)"
    # Pack purity: importing/executing pack code must never leave bytecode.
    export PYTHONDONTWRITEBYTECODE=1
    python3 -c 'import jsonschema' 2>/dev/null || skip "jsonschema not installed"
}

teardown() {
    # The shipped pack must stay byte-clean even after this suite ran its
    # python entrypoints from inside skills/deepworkplan/.
    if find "$PACK" -name '__pycache__' -o -name '*.pyc' | grep -q .; then
        echo "PACK PURITY VIOLATION: bytecode left inside the shipped pack"
        find "$PACK" -name '__pycache__' -o -name '*.pyc'
        return 1
    fi
    rm -rf "$TMPDIR_TEST"
}

# Mutate a copy of the contract fixture with a python one-liner body.
contract_mutant() {
    cp "$FX/contract-minimal.json" "$TMPDIR_TEST/contract.json"
    python3 - "$TMPDIR_TEST/contract.json" "$1" <<'PY'
import json, sys
path, expr = sys.argv[1], sys.argv[2]
doc = json.load(open(path))
exec(expr, {"d": doc})
json.dump(doc, open(path, 'w'), indent=2)
PY
    echo "$TMPDIR_TEST/contract.json"
}

journal_mutant() {
    cp "$FX/journal-events.ndjson" "$TMPDIR_TEST/journal.ndjson"
    python3 - "$TMPDIR_TEST/journal.ndjson" "$1" <<'PY'
import json, sys
path, expr = sys.argv[1], sys.argv[2]
lines = [json.loads(l) for l in open(path) if l.strip()]
exec(expr, {"es": lines})
with open(path, 'w') as fh:
    for e in lines:
        fh.write(json.dumps(e, sort_keys=True, separators=(',', ':')) + '\n')
PY
    echo "$TMPDIR_TEST/journal.ndjson"
}

@test "shipped self-test: full catalog valid, all mutant probes caught" {
    run python3 "$C6" self-test
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "self-test: OK"
    echo "$output" | grep -qE "self-test: OK \([0-9]+ mutant probes\)"
}

@test "committed fixtures validate through the CLI in both directions" {
    run python3 "$C6" validate-contract "$FX/contract-minimal.json"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "OK: v6 contract valid"
    run python3 "$C6" validate-journal "$FX/journal-events.ndjson" --contract "$FX/contract-minimal.json"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "OK: 14 journal events valid"
    # The fixture exercises every catalog type exactly once (closed catalog).
    echo "$output" | grep -q "14 types\|approval x1"
}

@test "identity is content-addressed: compute-id reproduces the stamp; drift is a revision" {
    stamped="$(python3 -c 'import json; print(json.load(open("'"$FX"'/contract-minimal.json"))["contract_id"])')"
    run python3 "$C6" compute-id "$FX/contract-minimal.json"
    [ "$status" -eq 0 ]
    [ "$output" = "$stamped" ]
    # One changed byte under the same stamp must fail identity validation.
    m="$(contract_mutant 'd["outcome"]["statement"] += " (edited)"')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "NEW revision"
    # Re-stamping the edited bytes is legitimate and validates again.
    python3 - "$m" <<'PY'
import json, sys
sys.path.insert(0, 'skills/deepworkplan/shared')
import contract_v6
doc = json.load(open(sys.argv[1]))
doc['contract_id'] = contract_v6.compute_contract_id(doc)
json.dump(doc, open(sys.argv[1], 'w'), indent=2)
PY
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 0 ]
}

@test "revision chain: parent required for revision 2, contiguous, never identical" {
    # Revision 2 without a parent citation is invalid.
    m="$(contract_mutant 'd["revision"] = 2')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "parent_contract_id"
    # A real revision: content changed, parent cited, chain supplied.
    parent_id="$(python3 -c 'import json; print(json.load(open("'"$FX"'/contract-minimal.json"))["contract_id"])')"
    python3 - "$TMPDIR_TEST/contract.json" "$parent_id" <<'PY'
import json, sys
sys.path.insert(0, 'skills/deepworkplan/shared')
import contract_v6
doc = json.load(open(sys.argv[1]))
doc['revision'] = 2
doc['parent_contract_id'] = sys.argv[2]
doc['outcome']['statement'] += ' (amended: narrower scope)'
doc['contract_id'] = contract_v6.compute_contract_id(doc)
json.dump(doc, open(sys.argv[1], 'w'), indent=2)
PY
    run python3 "$C6" validate-contract "$TMPDIR_TEST/contract.json" --parent "$FX/contract-minimal.json"
    [ "$status" -eq 0 ]
    # An identical-bytes revision is refused even with the chain supplied.
    python3 - "$TMPDIR_TEST/contract.json" <<'PY'
import json, sys
sys.path.insert(0, 'skills/deepworkplan/shared')
import contract_v6
doc = json.load(open(sys.argv[1]))
doc['outcome']['statement'] = json.load(open('tests/fixtures/v6/contract-minimal.json'))['outcome']['statement']
doc['contract_id'] = contract_v6.compute_contract_id(doc)
json.dump(doc, open(sys.argv[1], 'w'), indent=2)
PY
    run python3 "$C6" validate-contract "$TMPDIR_TEST/contract.json" --parent "$FX/contract-minimal.json"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "identical to the parent"
}

@test "mixed-era documents are refused, never guessed into a legacy parse" {
    m="$(contract_mutant 'd["schema"] = "https://deepworkplan.com/schema/plan-state/v5.json"')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "v6 contracts only"
    j="$(journal_mutant 'es[0]["schema"] = "https://deepworkplan.com/schema/plan-state/v5.json"')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "mixed-era"
}

@test "closed objects: an extra top-level contract field is invalid" {
    m="$(contract_mutant 'd["efficiency"] = {"tokens": 1}')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "unexpected field"
}

@test "invalid graphs: dangling prerequisites and cycles are refused" {
    m="$(contract_mutant 'd["tasks"][1]["prerequisites"].append("T-missing")')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "dangling reference"
    m="$(contract_mutant 'd["tasks"][0]["prerequisites"].append("T-ship-validator")')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "prerequisite cycle"
}

@test "unauthorized criterion edits have no carrier outside the amendment path" {
    # An adaptation object cannot carry criterion content (closed object):
    # a substituted check must travel as an amendment with authority.
    j="$(journal_mutant 'es[4]["revised_criterion"] = "AC-one: easier bar"')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "revised_criterion"
    # An amendment without recorded authority is invalid (section 3.4).
    j="$(journal_mutant 'es[6]["authority"] = ""')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "amendment\|authority"
}

@test "malformed resource values and enforced limits without a metering source" {
    m="$(contract_mutant 'd["resource_envelope"]["limits"][0]["limit"] = -1')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "spend_usd"
    m="$(contract_mutant 'd["resource_envelope"]["limits"][0]["limit"] = "lots"')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "expected a number"
    m="$(contract_mutant 'd["resource_envelope"]["limits"][0].pop("metering_source")')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "metering source"
}

@test "unsupported capabilities are refused against the closed set" {
    m="$(contract_mutant 'd["permissions"]["granted"].append("time_travel")')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "unsupported capability"
    m="$(contract_mutant 'd["permissions"]["not_granted"].append(d["permissions"]["granted"][0])')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "disjoint"
}

@test "approval: exactly two mechanisms, no third value (D3-1/D3-2)" {
    m="$(contract_mutant 'd["authorization"]["mechanism"] = "migration"')"
    run python3 "$C6" validate-contract "$m"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "pre_authorization"
    j="$(journal_mutant 'es[1]["mechanism"] = "migration"')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "mechanism"
}

@test "journal catalog is closed: unknown types and unknown keys are refused" {
    j="$(journal_mutant 'es[0]["type"] = "time_travel"')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "closed catalog"
    j="$(journal_mutant 'es[0]["mystery"] = 1')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "unexpected field"
}

@test "A1: observed requires a shipped executor, a mediating agent is asserted" {
    j="$(journal_mutant 'es[2]["actor"] = {"kind": "agent", "identity": "model"}')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "A1"
    # Trust labels do not exist on non-evidence types.
    j="$(journal_mutant 'es[6]["trust"] = "asserted"')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "evidence types"
}

@test "A6/U2 counterfactual pairs: only (old FAIL, new PASS) discriminates" {
    # (PASS, PASS) recorded as discriminating is refused - never round up.
    j="$(journal_mutant '(es[9]["old_leg"].update(outcome="PASS"), es[9].update(verdict="discriminating"))')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "never rounded up"
    # (PASS, PASS) honestly recorded as non-discriminating stays valid.
    j="$(journal_mutant '(es[9]["old_leg"].update(outcome="PASS"), es[9].update(verdict="non_discriminating"))')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 0 ]
}

@test "D3-3: a dirty starting fingerprint forces control=unavailable" {
    j="$(journal_mutant 'es[9]["starting_fingerprint"]["dirty"] = "M src/x.py"')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "D3-3"
    # An unavailable old leg carries no outcome (D2-6).
    j="$(journal_mutant 'es[9]["old_leg"] = {"available": False, "outcome": "FAIL", "log": "x"}')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "never a synthesized"
}

@test "D3-4: control pairs must declare their check artifacts" {
    j="$(journal_mutant 'es[9].pop("check_artifacts")')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "check_artifacts"
}

@test "D3-11: the intervention taxonomy is closed" {
    j="$(journal_mutant 'es[7]["category"] = "vibes"')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "closed taxonomy"
}

@test "adaptations: refused proposals carry a reason; kinds stay in the enumeration" {
    j="$(journal_mutant 'es[4].update(decision="refused")')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "reason"
    j="$(journal_mutant 'es[4]["kind"] = "delete_requirement"')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "3.3"
}

@test "journal ordering is append-only: seq never goes backwards" {
    j="$(journal_mutant 'es[5].update(seq=2)')"
    run python3 "$C6" validate-journal "$j"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "append-only"
}

@test "a journal belongs to one plan: cross-plan events are refused" {
    j="$(journal_mutant 'es[3].update(plan="PLAN_someone_else")')"
    run python3 "$C6" validate-journal "$j" --contract "$FX/contract-minimal.json"
    [ "$status" -eq 1 ]
    echo "$output" | grep -q "one plan"
}

@test "historical schema bytes remain unchanged when v6 files ship" {
    # Pinned at Task 11 (2026-09-26): the published v1/v2/v5 snapshots are
    # never rewritten by a v6 generation (RFC 9.1).
    cat > "$TMPDIR_TEST/expected.sha" <<'PINNED'
99871defc2f3e1c86c14d19e9153c5a662ec42dadba1d0cd781fb02848aa8ca1  plan-manifest-v2.schema.json
0b94dee169a13cdf2694e221ec682fd7be483f5be55ec1f46b57e835af5628c0  plan-manifest-v5.schema.json
eee739d1da73cc9f875a06936099b39793c2878fd836eec175eebb52bc366975  plan-manifest.schema.json
bd1c3f9534ef7ca614934ab67332c4c503abed79bb80cd23e5817fc76135e7ad  plan-state-v2.schema.json
8159935f0ec3d8f60ad861cadc1c3ea1bfe1f5b6dcdd23e673e38d72f6a45bc1  plan-state-v5.schema.json
7fa581b867312350b20826827e40a4339a270732544e674c811f0e855376c552  plan-state.schema.json
PINNED
    ( cd "$PACK/spec/schema" && sha256sum -c "$TMPDIR_TEST/expected.sha" )
}

@test "independent half: check-schema-contract.py v6 probes agree with the runtime" {
    run python3 "$REPO_ROOT/scripts/check-schema-contract.py"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "v6: contract + journal fixtures valid under both halves"
    echo "$output" | grep -q "contract_id reproduced by an independent canonicalization"
    echo "$output" | grep -q "0 problem(s)"
}
