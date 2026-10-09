#!/usr/bin/env bash
# The devcontainer addon — a vendor-neutral thin integrator of
# devcontainer-kit (`dck`) (spec/ADDONS.md §6.1). Policy under test: opt-in,
# never required; pinned devcontainer-kit by exact tag (interface 2) in
# descriptor and docs, and its dck-dockerfile skill offered through the
# same tag's tree-URL `skills add`; the per-repository layout is documented
# and no shared base image is required; no copy of the layout, Dockerfile
# template, compose file, entrypoint, dev.sh or images in the pack; no
# company-specific requirement; reconcile through `dck init` consent and
# backups, never clobber; the kit's security defaults are never weakened;
# no bypass flag or fetch-and-execute text. (The entrypoint library and its
# regression tests now live in devcontainer-kit; the retired in-pack
# template took tests/devcontainer-entrypoint.bats with it.)
bats_require_minimum_version 1.5.0

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
SK="$REPO_ROOT/skills/deepworkplan"
ADDON="$SK/addons/devcontainer"
ONBOARD="$SK/onboard/addons.md"
export PYTHONDONTWRITEBYTECODE=1

doc_has() { tr '\n' ' ' < "$1" | tr -s ' ' | grep -qF -- "$2"; }

@test "components ship; the retired templates and the entrypoint copy are gone" {
  for f in SKILL.md SPEC.md addon.json templates/INTEGRATION.md; do
    [ -s "$ADDON/$f" ] || { echo "missing $f"; return 1; }
  done
  for gone in devcontainer.json.md docker-compose.md Dockerfile.md entrypoint.md presets.md custom_commands.md; do
    [ ! -e "$ADDON/templates/$gone" ] || { echo "retired template still ships: $gone"; return 1; }
  done
  [ ! -e "$REPO_ROOT/tests/devcontainer-entrypoint.bats" ]
  # The Dockerfile template lives in devcontainer-kit (dck-dockerfile); the
  # pack keeps no copy of any rendered file, in any form.
  run find "$ADDON" \( -iname '*dockerfile*' -o -iname 'entrypoint*' -o -iname 'devcontainer.json*' \
    -o -iname 'docker-compose*' -o -iname 'dev.sh*' -o -iname 'versions.env*' \) -print
  [ -z "$output" ] || { echo "template copy in the pack: $output"; return 1; }
  run grep -rlE '^FROM [a-z0-9./-]+(:[^ ]+)?(@sha256:[0-9a-f]{64})?' "$SK"
  [ "$status" -ne 0 ] || { echo "a Dockerfile body ships in the pack: $output"; return 1; }
}

@test "vendor-neutral: no company-specific requirement anywhere in the pack" {
  # (the dailybot addon itself legitimately owns `.dailybot/profile.json`)
  run grep -rnE --exclude-dir=dailybot 'dailybot-project-network|dailybot\.dailybot|\.dailybot/profile\.json|DOCKER_DEV_ENV' "$SK"
  [ "$status" -ne 0 ]
  doc_has "$ADDON/SPEC.md" '**MUST NOT** require any company-specific network, volume, CLI or profile file'
  doc_has "$ADDON/SPEC.md" 'The `dailybot` layer is enabled **only** when the `dailybot` addon is enabled and asks for it.'
}

@test "pin: descriptor and every spelled ref name one devcontainer-kit tag, interface 2" {
  python3 - "$ADDON/addon.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d['product']['repo'] == 'DailybotHQ/devcontainer-kit', d
assert d['product']['interface'] == 2, d
assert d['detect'] == {'command': 'dck doctor --json', 'interface_from': 'json:interface'}, d
assert d['provides_abilities'] == [] and d['requires_grants'] == [], d
open('/dev/stdout', 'w').write(d['product']['tag'] + '\n')
PY
  tag="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["product"]["tag"])' "$ADDON/addon.json")"
  run bash -c "{ grep -rhoE -- '--branch v[0-9]+\.[0-9]+\.[0-9]+ https://github.com/DailybotHQ/devcontainer-kit' '$ADDON' '$ONBOARD'; grep -rhoE 'devcontainer-kit/tree/v[0-9]+\.[0-9]+\.[0-9]+' '$ADDON' '$ONBOARD' '$SK/spec/ADDONS.md'; grep -rhoE 'devcontainer-kit[^|]{0,20}pinned \`v[0-9]+\.[0-9]+\.[0-9]+\`' '$ONBOARD' || true; } | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | sort -u"
  [ "$output" = "$tag" ]
  grep -qF "git clone --branch $tag https://github.com/DailybotHQ/devcontainer-kit" "$ADDON/SKILL.md"
  grep -qF "| \`devcontainer\` | \`DailybotHQ/devcontainer-kit\` \`$tag\`, interface 2 |" "$SK/spec/ADDONS.md"
}

@test "skill: dck-dockerfile is offered through the tag-pinned tree-URL skills add" {
  tag="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["product"]["tag"])' "$ADDON/addon.json")"
  line="npx --yes skills add https://github.com/DailybotHQ/devcontainer-kit/tree/$tag --skill dck-dockerfile -y"
  for f in "$ADDON/SKILL.md" "$ADDON/SPEC.md" "$ONBOARD" "$SK/spec/ADDONS.md"; do
    doc_has "$f" "$line" || { echo "$f: no pinned dck-dockerfile install line"; return 1; }
  done
  # never the floating forms the skills CLI would resolve to the default branch
  run grep -rnE 'skills add (DailybotHQ/)?devcontainer-kit|devcontainer-kit@' "$ADDON" "$ONBOARD" "$SK/spec/ADDONS.md"
  [ "$status" -ne 0 ]
  doc_has "$ADDON/SKILL.md" '(repo-local, recorded in `skills-lock.json`)'
}

@test "layout: the per-repository files are documented and no shared base image is required" {
  for p in '.devcontainer/devcontainer.json' 'docker/local/<service>/Dockerfile' 'docker/local/docker-compose.yml' 'dev.sh'; do
    for f in "$ADDON/SKILL.md" "$ADDON/SPEC.md" "$ONBOARD" "$SK/spec/ADDONS.md"; do
      grep -qF -- "$p" "$f" || { echo "$f does not name $p"; return 1; }
    done
  done
  doc_has "$ADDON/SKILL.md" '**No shared base image is required**'
  doc_has "$ADDON/SPEC.md" 'The addon **MUST NOT** require or propose the kit'"'"'s GHCR base image.'
  doc_has "$SK/spec/ADDONS.md" 'the kit'"'"'s GHCR base image is not required'
  doc_has "$ONBOARD" 'no shared base image is required'
  # the retired base-image flavours are gone from the addon
  run grep -rnE -- '--flavour|node-24|python-3\.13' "$ADDON" "$ONBOARD"
  [ "$status" -ne 0 ]
}

@test "security: no bypass flag, no pipeline, no privileged options proposed" {
  run grep -rnE 'dangerously|--yolo|skip-permissions|(curl|wget)[^|]*\| *(ba)?sh' "$ADDON"
  [ "$status" -ne 0 ]
  doc_has "$ADDON/SKILL.md" 'pass `dck init --yes` without the developer'"'"'s explicit acceptance'
  doc_has "$ADDON/SKILL.md" 'pass `--trust` on the developer'"'"'s behalf'
  doc_has "$ADDON/SPEC.md" 'private keys are never copied into an image or container'
  doc_has "$ADDON/SPEC.md" 'in particular no host `~/.ssh`, `~/.gitconfig` or `${HOME}` mount'
  doc_has "$ADDON/SKILL.md" 'a failed build is a failed run, never a success'
  doc_has "$ADDON/SPEC.md" '`dck herdr add` writes the user'"'"'s `~/.ssh/config` include and **MUST** be run only with its own explicit approval.'
}

@test "reconcile, never clobber: dry-run first, consented diffs, kit backups" {
  doc_has "$ADDON/SPEC.md" 'The addon **MUST** show the render as a plan and diffs first (`dck init --dry-run`, or the skill'"'"'s confirmation step)'
  doc_has "$ADDON/SPEC.md" '`<file>.dck-bak-<timestamp>`'
  doc_has "$ONBOARD" '**existing devcontainer — never clobbered**'
}

@test "opt-in and documented: onboard row, ADDONS §6.1, README row; never required" {
  grep -qF '| **Devcontainer support** | [`../addons/devcontainer/`](../addons/devcontainer/SKILL.md) |' "$ONBOARD"
  grep -q '^### 6\.1 Devcontainer Support (first addon — thin integrator of devcontainer-kit)$' "$SK/spec/ADDONS.md"
  grep -F '| Devcontainer support |' "$SK/addons/README.md" | grep -qF 'vendor-neutral thin integrator'
  doc_has "$ADDON/SKILL.md" 'never required for a repo to be AI-first and never a conformance gate'
}
