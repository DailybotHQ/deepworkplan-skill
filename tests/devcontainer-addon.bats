#!/usr/bin/env bash
# The devcontainer addon — a vendor-neutral thin integrator of
# devcontainer-kit (`dck`) (spec/ADDONS.md §6.1). Policy under test: opt-in,
# never required; pinned devcontainer-kit by exact tag in descriptor and
# docs; no copy of the layout, entrypoint or images in the pack; no
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
}

@test "vendor-neutral: no company-specific requirement anywhere in the pack" {
  # (the dailybot addon itself legitimately owns `.dailybot/profile.json`)
  run grep -rnE --exclude-dir=dailybot 'dailybot-project-network|dailybot\.dailybot|\.dailybot/profile\.json|DOCKER_DEV_ENV' "$SK"
  [ "$status" -ne 0 ]
  doc_has "$ADDON/SPEC.md" '**MUST NOT** require any company-specific network, volume, CLI or profile file'
  doc_has "$ADDON/SPEC.md" 'The `dailybot` layer is enabled **only** when the `dailybot` addon is enabled and asks for it.'
}

@test "pin: descriptor and every spelled ref name one devcontainer-kit tag, interface 1" {
  python3 - "$ADDON/addon.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
assert d['product']['repo'] == 'DailybotHQ/devcontainer-kit', d
assert d['product']['interface'] == 1, d
assert d['detect'] == {'command': 'dck doctor --json', 'interface_from': 'json:interface'}, d
assert d['provides_abilities'] == [] and d['requires_grants'] == [], d
open('/dev/stdout', 'w').write(d['product']['tag'] + '\n')
PY
  tag="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["product"]["tag"])' "$ADDON/addon.json")"
  run bash -c "{ grep -rhoE -- '--branch v[0-9]+\.[0-9]+\.[0-9]+ https://github.com/DailybotHQ/devcontainer-kit' '$ADDON' '$ONBOARD'; grep -rhoE 'pinned \`v[0-9]+\.[0-9]+\.[0-9]+\`' '$ONBOARD' | grep -F devcontainer || true; } | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | sort -u"
  [ "$output" = "$tag" ]
  grep -qF "git clone --branch $tag https://github.com/DailybotHQ/devcontainer-kit" "$ADDON/SKILL.md"
}

@test "security: no bypass flag, no pipeline, no privileged options proposed" {
  run grep -rnE 'dangerously|--yolo|skip-permissions|(curl|wget)[^|]*\| *(ba)?sh' "$ADDON"
  [ "$status" -ne 0 ]
  doc_has "$ADDON/SKILL.md" 'pass `dck init --yes` without the developer'"'"'s explicit acceptance'
  doc_has "$ADDON/SKILL.md" 'pass `--trust` on the developer'"'"'s behalf'
  doc_has "$ADDON/SPEC.md" 'private keys are never copied into an image or container'
  doc_has "$ADDON/SPEC.md" '`dck herdr add` writes the user'"'"'s `~/.ssh/config` include and **MUST** be run only with its own explicit approval.'
}

@test "reconcile, never clobber: dry-run first, consented diffs, kit backups" {
  doc_has "$ADDON/SPEC.md" 'The addon **MUST** show `dck init --dry-run` first'
  doc_has "$ADDON/SPEC.md" '`<file>.dck-bak-<timestamp>`'
  doc_has "$ONBOARD" '**existing devcontainer — never clobbered**'
}

@test "opt-in and documented: onboard row, ADDONS §6.1, README row; never required" {
  grep -qF '| **Devcontainer support** | [`../addons/devcontainer/`](../addons/devcontainer/SKILL.md) |' "$ONBOARD"
  grep -q '^### 6\.1 Devcontainer Support (first addon — thin integrator of devcontainer-kit)$' "$SK/spec/ADDONS.md"
  grep -F '| Devcontainer support |' "$SK/addons/README.md" | grep -qF 'vendor-neutral thin integrator'
  doc_has "$ADDON/SKILL.md" 'never required for a repo to be AI-first and never a conformance gate'
}
