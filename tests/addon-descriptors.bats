#!/usr/bin/env bash
# Addon descriptors (spec/ADDONS.md §7, ecosystem contract §2.5 + A1): every
# in-pack addon ships addons/<key>/addon.json, valid under the published
# schema and the shipped runtime validator, key == directory, products
# pinned by exact tag, detect commands plain argv (no shell), and the
# ability/grant/transport table exactly as the ecosystem contract froze it.
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
CFG="$SK/shared/config.py"
export PYTHONDONTWRITEBYTECODE=1

@test "every addon directory ships a descriptor and the runtime audit passes" {
  for d in "$SK"/addons/*/; do
    [ -f "$d/addon.json" ] || { echo "missing $d/addon.json"; return 1; }
  done
  run python3 "$CFG" descriptors
  [ "$status" -eq 0 ]
  ! printf '%s\n' "$output" | grep -q '^FAIL'
}

@test "key equals the directory name for every descriptor" {
  for f in "$SK"/addons/*/addon.json; do
    dir="$(basename "$(dirname "$f")")"
    key="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["key"])' "$f")"
    [ "$key" = "$dir" ] || { echo "$f: key $key != $dir"; return 1; }
  done
}

@test "the ability, grant and transport table matches the frozen contract" {
  python3 - "$SK/addons" <<'PY'
import json, os, sys
root = sys.argv[1]
expected = {
    'agentkit': (['subagents', 'cancel_children', 'model_routing'], ['agent_delegation'], 'headless'),
    'herdr': (['subagents', 'cancel_children'], ['agent_delegation'], 'interactive'),
    'dailybot': (['telemetry'], [], None),
    'ai-diff-reviewer': ([], [], None),
    'devcontainer': ([], [], None),
    'vim': ([], [], None),
    'dependency-upgrade': ([], [], None),
    'design-system': ([], [], None),
}
seen = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
assert seen == sorted(expected), seen
for key, (abil, grants, transport) in expected.items():
    doc = json.load(open(os.path.join(root, key, 'addon.json')))
    assert sorted(doc['provides_abilities']) == sorted(abil), (key, doc)
    assert sorted(doc['requires_grants']) == sorted(grants), (key, doc)
    assert doc.get('transport') == transport, (key, doc)
PY
}

@test "products are pinned by exact tag and in-pack-only addons declare none" {
  python3 - "$SK/addons" <<'PY'
import json, os, re, sys
root = sys.argv[1]
tag = re.compile(r'^v\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?$')
pins = {'agentkit': 'DailybotHQ/coding-agents-kit', 'herdr': 'DailybotHQ/herdr-peers',
        'devcontainer': 'DailybotHQ/devcontainer-kit', 'vim': 'DailybotHQ/deepworkplan-vim',
        'ai-diff-reviewer': 'DailybotHQ/ai-diff-reviewer', 'dailybot': 'DailybotHQ/agent-skill'}
for key in os.listdir(root):
    path = os.path.join(root, key, 'addon.json')
    if not os.path.isfile(path):
        continue
    doc = json.load(open(path))
    if key in pins:
        assert doc['product']['repo'] == pins[key], (key, doc)
        assert tag.match(doc['product']['tag']), (key, doc)
    else:
        assert 'product' not in doc, (key, doc)
# the four ecosystem products publish interface 1 (contract section 2.0)
for key in ('agentkit', 'herdr', 'devcontainer', 'vim'):
    doc = json.load(open(os.path.join(root, key, 'addon.json')))
    assert doc['product'].get('interface') == 1, (key, doc)
PY
}

@test "the descriptor's product tag matches the vendored copy for vendored addons" {
  # Pin parity: the reviewer and Dailybot descriptors name the versions the
  # repository vendors under .agents/skills/ (the documented pins).
  rv="$(grep -m1 '^version:' "$REPO_ROOT/.agents/skills/ai-diff-reviewer/SKILL.md" | tr -d '"' | awk '{print $2}')"
  db="$(grep -m1 '^version:' "$REPO_ROOT/.agents/skills/dailybot/SKILL.md" | tr -d '"' | awk '{print $2}')"
  grep -qF "\"tag\": \"v$rv\"" "$SK/addons/ai-diff-reviewer/addon.json"
  grep -qF "\"tag\": \"v$db\"" "$SK/addons/dailybot/addon.json"
}

@test "detect commands are plain argv lines: no pipe, redirect, substitution or chaining" {
  run python3 -c 'import json,sys
for f in sys.argv[1:]:
    c = json.load(open(f))["detect"].get("command")
    if c: print(c)' "$SK"/addons/*/addon.json
  [ "$status" -eq 0 ]
  [ -n "$output" ]
  ! printf '%s\n' "$output" | grep -qE '[|;&$`<>()]'
}

@test "spec: ADDONS.md §7 documents the descriptor and the shipped table" {
  grep -q '^## 7\. Addon Descriptors (`addon.json`)$' "$SK/spec/ADDONS.md"
  grep -qF '| `herdr` | `DailybotHQ/herdr-peers` `v0.1.0`, interface 1 | `subagents`, `cancel_children` | `agent_delegation` | `interactive` |' "$SK/spec/ADDONS.md"
  grep -qF '"$id": "https://deepworkplan.com/schema/addon-descriptor/v1.json"' "$SK/spec/schema/addon-descriptor-v1.schema.json"
}
