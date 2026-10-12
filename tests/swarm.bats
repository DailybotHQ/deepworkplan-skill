#!/usr/bin/env bats
# Swarm autonomy helper (guide/swarm.md §17, shared/swarm.py): the own-capacity
# decision table over a fake `ak`, honest degradation without one, hysteresis
# and context pressure; the dwp-handoff-v1 packet (fields, 0600, secret and
# closed-set refusals, cross-host rule) and its acceptance checks (plan,
# contract, branch, head and dirty-set mismatches record nothing).
# Every `[[ ]]` ends in `|| false`: bash 3.2 (macOS) does not errexit on a
# failed `[[ ]]`, so without it an assertion can pass vacuously.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
SWARM="$SK/shared/swarm.py"
SCHEMA="$SK/spec/schema/dwp-handoff-v1.schema.json"
export PYTHONDONTWRITEBYTECODE=1

setup() {
    WORK="$(cd "$(mktemp -d)" && pwd -P)"
    mkdir -p "$WORK/bin"
    # A PATH with git and python3 but no real ak: each test installs its own.
    printf '#!/bin/sh\nexec "%s" "$@"\n' "$(command -v python3)" > "$WORK/bin/python3"
    printf '#!/bin/sh\nexec "%s" "$@"\n' "$(command -v git)" > "$WORK/bin/git"
    chmod +x "$WORK/bin/python3" "$WORK/bin/git"
    export PATH="$WORK/bin:/usr/bin:/bin"
    rm -f "$WORK/bin/ak"
    REPO="$WORK/repo"
    PLAN="$REPO/.dwp/plans/PLAN_001_swarm_fixture"
    mkdir -p "$PLAN/analysis_results" "$REPO/src"
    printf '{"contract_id": "c1", "revision": 1, "scheduling": {"handoff": {"fresh_context": "context pressure at 60%%"}}}\n' > "$PLAN/contract.json"
    printf 'x = 1\n' > "$REPO/src/a.py"
    printf '.dwp/\n' > "$REPO/.gitignore"
    git -C "$REPO" init -q -b main
    git -C "$REPO" add -A
    git -C "$REPO" -c user.email=t@t -c user.name=t commit -qm init
    cd "$REPO"
}

teardown() { rm -rf "$WORK"; }

# fake_ak VERSION [CAPACITY_JSON] [EXIT]: `ak --version` and `ak capacity`.
fake_ak() {
    printf '%s' "${2:-}" > "$WORK/capacity.json"
    cat > "$WORK/bin/ak" <<SH
#!/bin/sh
case "\$1" in
  --version) echo "agentkit $1 (interface 1)" ;;
  capacity) [ "\$2 \$3" = "--self --json" ] || exit 9
            cat "$WORK/capacity.json"; exit ${3:-0} ;;
  *) echo "ak: unknown kind '\$1'" >&2; exit 2 ;;
esac
SH
    chmod +x "$WORK/bin/ak"
}

cap() { printf '{"schema":"capacity-v1","interface":1,"cli":"claude","profile":"@work1","headroom_pct":%s,"binding_window":"5h","resets_at":"2026-10-12T18:00:00Z","verdict":"%s","thresholds":{"low":25,"critical":10},"source":"cache","age_s":42,"leases":1}' "$1" "$2"; }

packet_input() {
    cat <<'JSON'
{"step": "gate ran, commit pending", "done": ["swarm.py written"],
 "verified": ["tests/swarm.bats: 20 ok (gates/T-helper/004.log)"],
 "not_verified": ["schema publication on the site"],
 "next": ["commit the helper", "run bats tests/"],
 "open_asks": [{"id": "01ABC", "peer": "local:w13:p1", "awaits": "exit codes"}],
 "decisions": ["D2: capacity exits 0 for every decision"],
 "lead": "local:wP:pC", "epoch": 1,
 "from": {"agent": "claude", "vendor": "anthropic", "profile": "@work2", "pane": "w15:p1", "capacity": "critical 8%"}}
JSON
}

write_packet() { packet_input | python3 "$SWARM" handoff write --plan "$PLAN" --task T-helper --reason capacity_critical --json - "$@"; }

# ------------------------------------------------------------------ capacity

@test "capacity: no ak means continue with capacity unknown, never ok" {
    run python3 "$SWARM" capacity --json
    [ "$status" -eq 0 ]
    [[ "$output" == *'"decision": "continue"'* ]] || false
    [[ "$output" == *'"verdict": "unknown"'* ]] || false
    [[ "$output" == *'ak not installed'* ]] || false
}

@test "capacity: ak older than 0.6.0 degrades to unknown without calling capacity" {
    fake_ak 0.5.3 "$(cap 90 ok)"
    run python3 "$SWARM" capacity
    [ "$status" -eq 0 ]
    [[ "$output" == "continue: capacity unknown: ak 0.5.3 has no capacity verb"* ]] || false
}

@test "capacity: the decision table maps ok, low, critical and unknown" {
    fake_ak 0.6.0 "$(cap 64 ok)"
    run python3 "$SWARM" capacity
    [[ "$output" == "continue: capacity ok: 64% headroom (5h window"* ]] || false
    fake_ak 0.6.0 "$(cap 20 low)"
    run python3 "$SWARM" capacity
    [[ "$output" == "prepare: capacity_low: 20% headroom"* ]] || false
    fake_ak 0.6.1 "$(cap 8 critical)"
    run python3 "$SWARM" capacity --json
    [[ "$output" == *'"decision": "handoff"'* ]] || false
    [[ "$output" == *'"headroom_pct": 8'* ]] || false
    fake_ak 1.0.0 '{"schema":"capacity-v1","verdict":"unknown","cli":"cursor"}'
    run python3 "$SWARM" capacity
    [[ "$output" == "continue: capacity unknown: no quota source"* ]] || false
}

@test "capacity: outside an ak launch (exit 3) and malformed output are unknown" {
    fake_ak 0.6.0 'unknown account' 3
    run python3 "$SWARM" capacity
    [ "$status" -eq 0 ]
    [[ "$output" == *'not launched through ak'* ]] || false
    fake_ak 0.6.0 '{"schema":"usage-v1"}'
    run python3 "$SWARM" capacity --json
    [[ "$output" == *'"verdict": "unknown"'* ]] || false
    [[ "$output" == *'without a capacity-v1 record'* ]] || false
    fake_ak 0.6.0 "$(cap 50 bogus)"
    run python3 "$SWARM" capacity
    [[ "$output" == "continue: capacity unknown: unrecognized verdict"* ]] || false
}

@test "capacity: context pressure at the contract's threshold hands off" {
    run python3 "$SWARM" capacity --plan "$PLAN" --context-pct 59
    [[ "$output" == continue:* ]] || false
    run python3 "$SWARM" capacity --plan "$PLAN" --context-pct 60
    [[ "$output" == "handoff: context_pressure: 60% of context used (handoff at 60%)" ]] || false
}

@test "capacity: hysteresis binds the packet's author; a successor gets its real verdict" {
    fake_ak 0.6.0 "$(cap 95 ok)"
    run write_packet          # from.pane is w15:p1
    [ "$status" -eq 0 ]
    # the author, even with a recovered account, never resumes the task
    run python3 "$SWARM" capacity --plan "$PLAN" --pane w15:p1
    [[ "$output" == "handoff: hysteresis: your handoff packet is pending"* ]] || false
    HERDR_PANE_ID=w15:p1 run python3 "$SWARM" capacity --plan "$PLAN"
    [[ "$output" == handoff:* ]] || false
    # a successor in another pane (drill F7/F18) — or a caller with no pane —
    # gets its real verdict, with the pending packet named
    run python3 "$SWARM" capacity --plan "$PLAN" --pane w9:p1
    [[ "$output" == "continue: capacity ok: 95% headroom"*"a handoff packet from another pane is pending"* ]] || false
    run python3 "$SWARM" capacity --plan "$PLAN" --json
    [[ "$output" == *'"decision": "continue"'*'"pending_packet": "analysis_results/handoff/'* ]] || false
    run python3 "$SWARM" handoff accept --plan "$PLAN" --by local:w9:p1
    [ "$status" -eq 0 ]
    run python3 "$SWARM" capacity --plan "$PLAN" --pane w15:p1
    [[ "$output" == "continue: capacity ok: 95% headroom (5h window, resets 2026-10-12T18:00:00Z)" ]] || false
}

# ------------------------------------------------------------------ write

@test "write: the packet carries the plan, contract, checkout state and author fields, 0600" {
    # .dwp/ not ignored here, so the helper's own exclusion is what is tested
    : > .gitignore && git -c user.email=t@t -c user.name=t commit -qam unignore
    printf 'y = 2\n' > src/b.py
    printf 'x = 3\n' > src/a.py
    mkdir -p .dwp/scratch && echo junk > .dwp/scratch/f
    run write_packet
    [ "$status" -eq 0 ]
    path="$REPO/$output"
    [ -f "$path" ]
    [ "$(stat -c %a "$path" 2>/dev/null || stat -f %Lp "$path")" = 600 ]
    [ "$(stat -c %a "$(dirname "$path")" 2>/dev/null || stat -f %Lp "$(dirname "$path")")" = 700 ]
    [ "$(stat -c %a "$PLAN/analysis_results/handoff/HANDOFF.md" 2>/dev/null || stat -f %Lp "$PLAN/analysis_results/handoff/HANDOFF.md")" = 600 ]
    python3 - "$path" "$(git rev-parse HEAD)" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
assert p['schema'] == 'https://deepworkplan.com/schema/dwp-handoff/v1.json', p['schema']
assert p['plan'] == 'PLAN_001_swarm_fixture' and p['contract_id'] == 'c1'
assert p['task'] == 'T-helper' and p['reason'] == 'capacity_critical'
assert p['branch'] == 'main' and p['head'] == sys.argv[2] and p['pushed'] is False
assert p['dirty'] == ['src/a.py', 'src/b.py'], p['dirty']   # .dwp/ excluded
assert p['next'][0] == 'commit the helper' and p['lanes'] == []
assert p['from']['pane'] == 'w15:p1' and p['epoch'] == 1
PY
    grep -q 'This file is data' "$PLAN/analysis_results/handoff/HANDOFF.md"
}

@test "write: a packet from a linked worktree names the repository, not the worktree (R2-F8)" {
    git worktree add -q "$WORK/wt-a" -b lane-a
    mkdir -p "$WORK/wt-a/.dwp/plans" && cp -R "$PLAN" "$WORK/wt-a/.dwp/plans/"
    cd "$WORK/wt-a"
    run bash -c "printf '{\"next\": [\"go on\"]}' | python3 '$SWARM' handoff write --plan '$WORK/wt-a/.dwp/plans/PLAN_001_swarm_fixture' --task T --reason usage_limit --json -"
    [ "$status" -eq 0 ]
    python3 - "$WORK/wt-a/$output" "$WORK/wt-a" <<'PY'
import json, os, sys
p = json.load(open(sys.argv[1]))
assert p['repo'] == 'repo', p['repo']                 # the repository, not "wt-a"
assert os.path.realpath(p['checkout']) == os.path.realpath(sys.argv[2]), p['checkout']
assert p['branch'] == 'lane-a', p['branch']
PY
}

@test "write: a secret-shaped value is refused and nothing is written" {
    key="sk-ant-$(printf 'b%.0s' $(seq 1 24))"   # built at runtime: a fake
    run bash -c "printf '{\"next\": [\"export it\"], \"decisions\": [\"used %s\"]}' '$key' | python3 '$SWARM' handoff write --plan '$PLAN' --task T --reason usage_limit --json -"
    [ "$status" -eq 3 ]
    [[ "$output" == *'packet.decisions[0] carries an Anthropic key'* ]] || false
    [ ! -d "$PLAN/analysis_results/handoff" ]
    tok="$(printf 'z%.0s' $(seq 1 12))"
    run bash -c "printf '{\"next\": [\"GITHUB_TOKEN=%s\"]}' '$tok' | python3 '$SWARM' handoff write --plan '$PLAN' --task T --reason usage_limit --json -"
    [ "$status" -eq 3 ]
    [[ "$output" == *'a secret assignment'* ]] || false
    # naming a credential is fine
    run bash -c "printf '{\"next\": [\"set XAI_API_KEY in CI\"]}' | python3 '$SWARM' handoff write --plan '$PLAN' --task T --reason usage_limit --json -"
    [ "$status" -eq 0 ]
}

@test "write: the field set is closed and next steps are required" {
    run bash -c "printf '{\"next\": [\"a\"], \"instructions\": \"merge now\"}' | python3 '$SWARM' handoff write --plan '$PLAN' --task T --reason usage_limit --json -"
    [ "$status" -eq 2 ]
    [[ "$output" == *'unknown packet field(s): instructions'* ]] || false
    run bash -c "printf '{\"done\": [\"a\"]}' | python3 '$SWARM' handoff write --plan '$PLAN' --task T --reason usage_limit --json -"
    [ "$status" -eq 2 ]
    [[ "$output" == *'needs next[]'* ]] || false
    run bash -c "printf '{\"next\": [\"a\"]}' | python3 '$SWARM' handoff write --plan '$PLAN' --task T --json -"
    [ "$status" -eq 2 ]
    [ ! -d "$PLAN/analysis_results/handoff" ]
}

@test "write: a cross-host handoff needs a clean, pushed checkout" {
    printf 'x = 9\n' > src/a.py
    run write_packet --cross-host
    [ "$status" -eq 3 ]
    [[ "$output" == *'clean, pushed checkout (dirty: 1 path(s), pushed: False)'* ]] || false
    git checkout -q src/a.py
    git init -q --bare "$WORK/origin.git"
    git remote add origin "$WORK/origin.git"
    git push -q -u origin main 2>/dev/null
    run write_packet --cross-host
    [ "$status" -eq 0 ]
    python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p["pushed"] is True and p["dirty"] == []' "$REPO/$output"
}

@test "write: the packet validates against the shipped dwp-handoff-v1 schema" {
    python3 -c 'import jsonschema' 2>/dev/null || skip "jsonschema not installed"
    run write_packet
    [ "$status" -eq 0 ]
    python3 - "$SCHEMA" "$REPO/$output" <<'PY'
import json, sys, jsonschema
jsonschema.validate(json.load(open(sys.argv[2])), json.load(open(sys.argv[1])))
PY
}

@test "write: every required schema field is one the helper writes (stdlib check)" {
    run write_packet
    [ "$status" -eq 0 ]
    python3 - "$SCHEMA" "$REPO/$output" <<'PY'
import json, sys
schema, packet = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
missing = [k for k in schema['required'] if k not in packet]
extra = [k for k in packet if k not in schema['properties']]
assert not missing and not extra, (missing, extra)
PY
}

# ------------------------------------------------------------------ accept / show

@test "accept: a matching packet is accepted once, recorded 0600, no longer pending" {
    printf 'x = 5\n' > src/a.py
    run write_packet
    packet="$REPO/$output"
    run python3 "$SWARM" handoff show --plan "$PLAN" --pending
    [ "$status" -eq 0 ]
    [[ "$output" == *'(pending)'* ]] || false
    run python3 "$SWARM" handoff accept --plan "$PLAN" --by local:w9:p1
    [ "$status" -eq 0 ]
    [[ "$output" == *'- commit the helper'* ]] || false
    side="${packet%.json}.accepted.json"
    [ "$(stat -c %a "$side" 2>/dev/null || stat -f %Lp "$side")" = 600 ]
    python3 -c 'import json,sys,hashlib; s=json.load(open(sys.argv[1])); assert s["by"]=="local:w9:p1" and s["packet_sha256"]==hashlib.sha256(open(sys.argv[2],"rb").read()).hexdigest()' "$side" "$packet"
    run python3 "$SWARM" handoff show --plan "$PLAN" --pending
    [ "$status" -eq 1 ]
    run python3 "$SWARM" handoff accept --plan "$PLAN" --packet "$packet"
    [ "$status" -eq 3 ]
    [[ "$output" == *'already accepted'* ]] || false
}

@test "accept: head, branch, dirty set and contract mismatches are refused and record nothing" {
    run write_packet
    packet="$REPO/$output"
    printf 'z\n' > src/new.py
    run python3 "$SWARM" handoff accept --plan "$PLAN"
    [ "$status" -eq 3 ]
    [[ "$output" == *'dirty set differs'* ]] || false
    git add -A && git -c user.email=t@t -c user.name=t commit -qm moved
    run python3 "$SWARM" handoff accept --plan "$PLAN"
    [ "$status" -eq 3 ]
    [[ "$output" == *"head '"* ]] || false
    git checkout -q -b other
    run python3 "$SWARM" handoff accept --plan "$PLAN"
    [[ "$output" == *"branch 'main' is not the checkout's 'other'"* ]] || false
    git checkout -q main && git reset -q --hard HEAD~1
    printf '{"contract_id": "c2", "revision": 2}\n' > "$PLAN/contract.json"
    run python3 "$SWARM" handoff accept --plan "$PLAN"
    [ "$status" -eq 3 ]
    [[ "$output" == *'contract c1 is not the live contract c2'* ]] || false
    [ ! -e "${packet%.json}.accepted.json" ]
}

@test "accept: a packet from another plan is refused" {
    run write_packet
    packet="$REPO/$output"
    other="$REPO/.dwp/plans/PLAN_002_other"
    mkdir -p "$other/analysis_results/handoff" && cp "$PLAN/contract.json" "$other/"
    cp "$packet" "$other/analysis_results/handoff/"
    run python3 "$SWARM" handoff accept --plan "$other"
    [ "$status" -eq 3 ]
    [[ "$output" == *"plan 'PLAN_001_swarm_fixture' is not this plan (PLAN_002_other)"* ]] || false
}

@test "a later packet supersedes an earlier pending one; the newest is accepted" {
    run write_packet
    first="$REPO/$output"
    git -c user.email=t@t -c user.name=t commit -q --allow-empty -m moved
    # the first packet no longer matches the checkout: write a fresh one
    run write_packet
    second="$REPO/$output"
    [ "$first" != "$second" ]
    [ -e "${first%.json}.superseded.json" ]
    run python3 "$SWARM" handoff show --plan "$PLAN" --pending
    [[ "$output" == *"$(basename "$second")"* ]] || false
    run python3 "$SWARM" handoff accept --plan "$PLAN"
    [ "$status" -eq 0 ]
    [ -e "${second%.json}.accepted.json" ]
    run python3 "$SWARM" capacity --plan "$PLAN"
    [[ "$output" == continue:* ]] || false
    run python3 "$SWARM" handoff accept --plan "$PLAN" --packet "$first"
    [ "$status" -eq 3 ]
    [[ "$output" == *'superseded by a later packet'* ]] || false
}

@test "packet names sort in write order, even within one second" {
    for i in 1 2 3; do run write_packet; [ "$status" -eq 0 ]; done
    newest="$(ls "$PLAN/analysis_results/handoff/" | grep -vE '(accepted|superseded)\.json$' | grep '\.json$' | sort | tail -1)"
    run python3 "$SWARM" handoff show --plan "$PLAN" --pending
    [[ "$output" == *"$newest"* ]] || false
    [ "$(ls "$PLAN/analysis_results/handoff/" | grep -c 'superseded.json$')" -eq 2 ]
}

@test "inputs are validated: packet path, input file, field types" {
    printf '{}\n' > "$WORK/elsewhere.json"
    run python3 "$SWARM" handoff accept --plan "$PLAN" --packet "$WORK/elsewhere.json"
    [ "$status" -eq 2 ]
    [[ "$output" == *'a packet is a .json file in'* ]] || false
    run python3 "$SWARM" handoff write --plan "$PLAN" --task T --reason usage_limit --json "$WORK/missing.json"
    [ "$status" -eq 2 ]
    [[ "$output" == *'cannot read the packet input'* ]] || false
    run bash -c "printf '{\"next\": [\"a\"], \"step\": 3}' | python3 '$SWARM' handoff write --plan '$PLAN' --task T --reason usage_limit --json -"
    [ "$status" -eq 2 ]
    run bash -c "printf '{\"next\": [\"a\"], \"from\": {\"pane\": 7}}' | python3 '$SWARM' handoff write --plan '$PLAN' --task T --reason usage_limit --json -"
    [ "$status" -eq 2 ]
}

@test "context pressure reads the live (amended) contract, as the ledger does" {
    mkdir -p "$PLAN/contracts"
    printf '{"contract_id": "c2", "revision": 2, "scheduling": {"handoff": {"fresh_context": "context pressure at 40%%"}}}\n' > "$PLAN/contracts/r2.json"
    run python3 "$SWARM" capacity --plan "$PLAN" --context-pct 45
    [[ "$output" == "handoff: context_pressure: 45% of context used (handoff at 40%)" ]] || false
}

@test "show: no packet is a quiet zero; --pending with none exits 1" {
    run python3 "$SWARM" handoff show --plan "$PLAN"
    [ "$status" -eq 0 ]
    [ "$output" = "no handoff packet" ]
    run python3 "$SWARM" handoff show --plan "$PLAN" --pending
    [ "$status" -eq 1 ]
}

# ------------------------------------------------------------------ the guide

doc_has() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }

@test "guide §17 teaches every swarm topic the design names" {
    G="$SK/guide/swarm.md"
    for heading in '## 17. Swarm Autonomy' '### 17.1. Roles' '### 17.2. The lane contract' \
        '### 17.3. The capacity loop' '### 17.4. Scheduling and the declared pool' \
        '### 17.5. The handoff packet' '### 17.6. Lane handoff (proactive)' '### 17.7. Lead succession' \
        '### 17.8. Messaging' '### 17.9. Escalation in a swarm' '### 17.10. Release train' \
        '### 17.11. The record' '### 17.12. Drilling it'; do
        grep -qxF "$heading" "$G" || { echo "missing: $heading"; return 1; }
    done
    for phrase in '**Deputy**' '**Reviewer**' 'Several leads' 'Several instances of one kind' \
        'Hysteresis.' 'Context pressure is capacity too.' 'The pool is the developer' \
        'herdr-peers lead takeover --plan <P>' 'Fencing.' 'Lane ↔ lane' 'herdr-peers notify' \
        'blocks its dependency chain, not the swarm' 'AGENTKIT_CAPACITY_CAP=@<profile>=8' \
        'swarm.py capacity --plan' 'swarm.py handoff accept --plan' 'Never an admin merge' \
        'Every herdr-peers call names the lane'"'"'s own pane.' 'and `check`, which records a received reply or ask'; do
        doc_has "$G" "$phrase" || { echo "missing: $phrase"; return 1; }
    done
}

@test "guide §17 is routed from GUIDE.md and §16, and loads only on its trigger" {
    grep -qF '| ## 17. Swarm Autonomy | [`swarm.md`](./swarm.md) |' "$SK/guide/GUIDE.md"
    doc_has "$SK/guide/GUIDE.md" '[`swarm.md`](./swarm.md) for capacity checks, handoff packets and lead succession'
    doc_has "$SK/guide/orchestration-at-scale.md" 'read §17 ([`swarm.md`](swarm.md))'
    doc_has "$SK/execute/SKILL.md" '[`../guide/swarm.md`](../guide/swarm.md) §17 — read only when the agentkit addon is enabled'
    # never part of any flow's compulsory read set
    run bash "$REPO_ROOT/tests/efficiency/measure-instruction-load.sh" "$REPO_ROOT"
    [ "$status" -eq 0 ]
    ! printf '%s\n' "$output" | grep -E '^(create|execute|resume|refine|onboard|status|verify) ' | grep -q 'guide/swarm.md' || false
}

@test "§17 carries the live-drill fixes (round 1)" {
    G="$SK/guide/swarm.md"
    doc_has "$G" 'its author never resumes that task'                         # F7/F18
    doc_has "$G" 'A successor in another pane gets its real verdict'
    doc_has "$G" '**A lane is not depth-marked.**'                              # F5
    doc_has "$G" '**Claim first, then launch.**'                                # F6
    grep -qF "herdr-peers notify lead \$'done PR #12" "$G"                     # F9
    grep -qF "| herdr-peers notify lead - --pane" "$G"
    doc_has "$G" '`status` accepts it from herdr-peers `v0.3.1`'               # F15
    doc_has "$G" 'under the plan'"'"'s `analysis_results/delegations/<id>/` the moment it arrives'   # F16
    doc_has "$G" '**Edge-case inputs are part of the brief.**'                 # F17
    doc_has "$SK/spec/DWP_SPECIFICATION.md" 'names its edge-case inputs (empty, multi-line, leading or trailing whitespace)'
    doc_has "$G" '**Known limitation:** the v7 journal has no event shape of its own for a handoff or a succession.'   # F8/F11
    doc_has "$G" 'the lane'"'"'s address owns its lease'                       # F4 (docs)
}

@test "§17, the spec and the guides carry the live-drill fixes (round 2)" {
    G="$SK/guide/swarm.md"
    doc_has "$G" '**Never poll for a message.**'                                   # R2-F5
    doc_has "$G" "**Never give a lane the lead's own account.**"                   # R2-F7
    doc_has "$G" '| a notice | `NOTICE` — recorded, never reply | `3` |'            # R2-F4/F14
    doc_has "$G" '| a lead notice already current | `LEAD NOTICE … current` | `0` |'
    doc_has "$G" '**`DWP_PLAN` holds the plan directory**'                          # R2-F10
    doc_has "$G" '**Epoch bookkeeping.**'                                          # R2-F13
    doc_has "$G" 'the release `N+2` (lead none)'
    doc_has "$G" '`lead show` from `v0.3.2`'                                       # R2-F3
    doc_has "$SK/guide/execution.md" 're-gate the fixed task'                      # R2-F11
    doc_has "$SK/spec/DWP_SPECIFICATION.md" 'A test of exact output checks it with a sentinel'   # R2-F15
    doc_has "$SK/guide/authoring.md" '**Exact output needs a sentinel.**'
}

@test "§16 lets lanes coordinate with each other and keeps the reactive path as the safety net" {
    O="$SK/guide/orchestration-at-scale.md"
    ! doc_has "$O" 'Lanes never message each other' || false
    doc_has "$O" 'Lane ↔ lane asks are for information and coordination'
    doc_has "$O" 'never for assigning work'
    doc_has "$O" 'Hand off before the limit'
    doc_has "$O" 'What follows is the reactive safety net'
    doc_has "$O" 'Work moves only among the accounts the developer declared for it'
}

# ------------------------------------------------------------------ escalation

@test "AGENT_PROTOCOL §7.5 names C1-C7, decide-and-record, and per-chain blocking" {
    A="$SK/spec/AGENT_PROTOCOL.md"
    grep -qxF '### 7.5. Escalation Taxonomy' "$A"
    for c in '**C1 Authority**' '**C2 Consent screen**' '**C3 Irreducible ambiguity**' \
        '**C4 Quality conflict**' '**C5 Damage**' '**C6 Terms**' '**C7 Capacity exhausted**'; do
        grep -qF "$c" "$A" || { echo "missing $c"; return 1; }
    done
    doc_has "$A" 'an escalation **MUST** name its class'
    doc_has "$A" '**records the decision**'
    doc_has "$A" 'a critical item blocks its dependency chain, not the run'
    doc_has "$A" '**Autonomy never closes a human gate.**'
    doc_has "$A" "**The developer's literal words win.**"
    doc_has "$A" '**Authority is not transitive.**'
    doc_has "$A" '**Batch the questions.**'
    doc_has "$A" 'recording a failure proven to exist on the base branch'
}

@test "the working principles and execute checkpoints carry the taxonomy, ten behaviors intact" {
    WP="$SK/shared/working-principles.md"
    n="$(sed -n '/^```markdown$/,/^```$/p' "$WP" | grep -c '^- \*\*')"
    [ "$n" -eq 10 ]
    doc_has "$WP" 'take the recommended option, and record consequential decisions'
    doc_has "$WP" 'Escalate only what is critical, and name its class'
    doc_has "$WP" '`AGENT_PROTOCOL.md` §7.5'
    # this repository's own AGENTS.md dogfoods the same two behaviors
    doc_has "$REPO_ROOT/AGENTS.md" 'Escalate only what is critical, and name its class'
    doc_has "$SK/execute/SKILL.md" 'They are classes C1–C2 of the escalation taxonomy'
    doc_has "$SK/execute/SKILL.md" 'is decided, recorded, never asked'
}

# ------------------------------------------------------------------ quality bar

@test "the quality bar is normative in the spec and taught where gates are written and reviewed" {
    S="$SK/spec/DWP_SPECIFICATION.md"
    grep -qxF '### 5.1.4. The Quality Bar — Verified, Not Asserted' "$S"
    for phrase in '**Gates are hypotheses.**' '**Compare to the base.**' '**Measure first.**' \
        '**Design before build.**' '**Environment honesty.**' '**Review before the irreversible step.**' \
        '**Lean evidence.**' '**Continuity never lowers the bar.**' 'A vacuous pass'; do
        doc_has "$S" "$phrase" || { echo "spec missing: $phrase"; return 1; }
    done
    A="$SK/guide/authoring.md"
    grep -qxF '#### 5.3.1. Writing a gate that can fail' "$A"
    for phrase in '**Prove it can fail.**' '**Pins are data.**' '**Declare the environment.**' '|| false'; do
        doc_has "$A" "$phrase" || { echo "authoring missing: $phrase"; return 1; }
    done
    E="$SK/guide/execution.md"
    for phrase in 'Runs **before the irreversible step**' '**Promote load-bearing helpers on second use:**' \
        '**Records coherence**' 'never a blanket `git add -A`'; do
        doc_has "$E" "$phrase" || { echo "execution missing: $phrase"; return 1; }
    done
    doc_has "$SK/create/v6.md" '(`relayed by <agent>`)'
}

# ------------------------------------------------------------------ the flows

@test "execute checks capacity at each task boundary and resume reads a pending packet first" {
    doc_has "$SK/execute/v6.md" '0. **Capacity** (agentkit addon enabled) — `python3 ../shared/swarm.py capacity --plan <dir> --pane <pane> [--context-pct N]`'
    doc_has "$SK/execute/v6.md" 'Capacity *unknown* is not *ok*'
    doc_has "$SK/execute/SKILL.md" '(agentkit enabled: the §17 capacity check first)'
    doc_has "$SK/resume/SKILL.md" 'A pending **handoff packet** comes first'
    doc_has "$SK/resume/SKILL.md" '[`../guide/swarm.md`](../guide/swarm.md) §17 — read only when the plan holds a pending handoff packet'
    doc_has "$SK/resume/v6.md" '0. **Pending handoff packet.**'
    # every generation checks for a packet before classifying the plan
    doc_has "$SK/resume/SKILL.md" '**Step 2.0a — Pending handoff packet (every generation).**'
    # a pending packet is never overwritten by a second write
    doc_has "$SK/execute/v6.md" '`handoff` with reason `hysteresis` (your packet is already pending) → stop, never write another'
    doc_has "$SK/execute/v6.md" 'A `pending_packet` from another pane → accept it through resume before working'
    doc_has "$SK/execute/v6.md" '`swarm.py handoff write` **once**'
    # the execution guide's own templates follow its staging rule
    ! grep -qE '^ *git add -A *$' "$SK/guide/execution.md" || false
    # every command the flows cite exists in the helper's CLI
    run python3 "$SWARM" handoff show --help
    [ "$status" -eq 0 ]
    [[ "$output" == *'--pending'* ]] || false
}

# ------------------------------------------------------------------ the addons

@test "the agentkit and herdr addons teach the new verbs, version-gated, pins unchanged" {
    AK="$SK/addons/agentkit"; HP="$SK/addons/herdr"
    grep -qxF '## Capacity and leases (coding-agents-kit `v0.6.0` and later)' "$AK/SKILL.md"
    grep -qxF '## 5.2. Capacity and Leases (kit `v0.6.0` and later)' "$AK/SPEC.md"
    for phrase in 'ak capacity --self --json' 'ak lease <kind> @<profile> --owner <addr>' \
        'AGENTKIT_CAPACITY_CAP=@p=PCT' '../../shared/swarm.py capacity'; do
        doc_has "$AK/SKILL.md" "$phrase" || { echo "agentkit missing: $phrase"; return 1; }
    done
    doc_has "$AK/SPEC.md" 'never as *ok*'
    grep -qxF '## Notices and leadership (herdr-peers `v0.3.0` and later)' "$HP/SKILL.md"
    grep -qxF '## 6.2. Notices and Leadership (herdr-peers `v0.3.0` and later)' "$HP/SPEC.md"
    for phrase in 'herdr-peers notify <addr|lead>' 'herdr-peers lead claim --plan P' \
        '`lead takeover --plan P [--reason R]`' '`usage_limit`' 'Lanes may ask each other'; do
        doc_has "$HP/SKILL.md" "$phrase" || { echo "herdr missing: $phrase"; return 1; }
    done
    ! doc_has "$HP/SKILL.md" 'Lanes talk only to the lead' || false
    ! doc_has "$HP/SPEC.md" 'coordinate only with the lead' || false
}
