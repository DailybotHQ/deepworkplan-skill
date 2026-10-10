#!/usr/bin/env bash
set -euo pipefail

# Smoke-install the ecosystem products the pack pins, exactly at the tags its
# addon descriptors name (skills/deepworkplan/addons/*/addon.json), and check
# each reports the interface integer the descriptor expects.
#
#   herdr      skills CLI install of the pinned herdr-peers skill into a temp
#              project; its SKILL.md metadata.protocol and its helper's
#              `--version` "(protocol N)" must equal the interface
#   agentkit   tagged clone + install.sh --no-rc into a temp HOME;
#              `ak --version` names the tag, `ak doctor --json` .interface
#   devcontainer  tagged clone + install.sh --no-rc into a temp HOME;
#              `dck --version` names the tag, `dck doctor --json` .interface;
#              then the skills CLI installs the tag's dck-dockerfile skill
#              into a temp project (the line the addon offers)
#   vim        tagged clone; addon/surface.json interface and version, and the
#              surface's install.script.sha256 equals the tag's install.sh
#
# Every pin: the release's SHA256SUMS asset is downloaded and each listed file
# present in the tagged tree must match, and the digest of SHA256SUMS itself
# must equal the one pinned in expected_sums (addon descriptors carry none).
#
# Everything runs under a throwaway HOME and temp directories: nothing is
# written to the real home, no shell rc is touched, nothing is left behind.
# Network: git, curl (release SHA256SUMS) and the npm `skills` CLI only. Bash 3.2 compatible.
#
# Usage: scripts/smoke-ecosystem-pins.sh [herdr|agentkit|devcontainer|vim ...]
# Exit:  0 every selected pin verified · 1 a pin failed · 2 environment error

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ADDONS="$REPO_ROOT/skills/deepworkplan/addons"
SELECTED="${*:-herdr agentkit devcontainer vim}"

WORK="$(mktemp -d)"
cleanup() { chmod -R u+w "$WORK" 2>/dev/null || true; rm -rf "$WORK"; }
trap cleanup EXIT
export HOME="$WORK/home"
mkdir -p "$HOME"

field() {  # field <key> <python expression over d=descriptor>
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(eval(sys.argv[2]))' \
        "$ADDONS/$1/addon.json" "$2"
}

json_field() {  # json_field <field>  (stdin: one JSON object)
    python3 -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"
}

failures=0
ok()   { echo "OK   $1"; }
fail() { echo "FAIL $1"; failures=$((failures + 1)); }

expected_sums() {  # expected_sums <key>: sha256 of the pinned release's SHA256SUMS asset
    # Pinned here, per addon tag (the descriptor schema carries no digest):
    # bumping a tag in addon.json without updating its digest fails this smoke.
    case "$1" in
        herdr)        echo 373823f4ceb1891032a474f776ad502c2d745d45318b42eb8f38f8c4aaf2a6d1 ;;
        agentkit)     echo d38d4f989bd7c05826a142067b92010c390045094b046641984d20d33894e9fa ;;
        devcontainer) echo 417475d8ee48a393acf8661c682af2b61f38df13db72e96fcb1416a4bfa6c543 ;;
        vim)          echo 3e9b8ff04f0dd6cfdc40dc99f29bdfdca5da1eac9029d6428a98cbe0813b4dbd ;;
        *)            echo "" ;;
    esac
}

verify_sums() {  # verify_sums <key> [tagged-clone]
    # The release's SHA256SUMS asset, checked against the tagged tree: every
    # listed file present in the clone must match (release-only assets such
    # as tarballs are skipped), at least one must be checked, and the digest
    # of SHA256SUMS itself must equal expected_sums <key>.
    local key="$1" src="${2:-}" repo tag sums
    repo="$(field "$key" "d['product']['repo']")"
    tag="$(field "$key" "d['product']['tag']")"
    if [ -z "$src" ]; then
        src="$WORK/$key-sums-src"
        git clone -q --depth 1 --branch "$tag" "https://github.com/${repo}" "$src" 2>/dev/null \
            || { fail "$key: git clone --branch $tag ${repo} failed"; return; }
    fi
    sums="$WORK/$key.SHA256SUMS"
    curl -fsSL "https://github.com/${repo}/releases/download/${tag}/SHA256SUMS" -o "$sums" 2>/dev/null \
        || { fail "$key: ${repo}@${tag} release has no SHA256SUMS asset"; return; }
    python3 - "$sums" "$src" "$key" "$repo" "$tag" "$(expected_sums "$key")" <<'PY' || failures=$((failures + 1))
import hashlib, os, sys
sums, src, key, repo, tag, expected = sys.argv[1:]
digest = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
# Trust the downloaded file only once its pinned digest matches.
if digest(sums) != expected:
    print("FAIL %s: sha256(SHA256SUMS)=%s, expected %s" % (key, digest(sums), expected or "(none pinned)"))
    sys.exit(1)
root = os.path.realpath(src)
checked, bad = 0, []
for line in open(sums):
    parts = line.split(None, 1)
    if len(parts) != 2:
        continue
    want, name = parts[0], parts[1].strip().lstrip("*")
    path = os.path.realpath(os.path.join(root, name))
    if os.path.isabs(name) or not path.startswith(root + os.sep):
        bad.append(name + " (outside the clone)")
        continue
    if os.path.isfile(path):
        checked += 1
        if digest(path) != want:
            bad.append(name)
if bad or not checked:
    print("FAIL %s: SHA256SUMS mismatch %s (checked %d)" % (key, ", ".join(bad) or "-", checked))
    sys.exit(1)
print("OK   %s: %s@%s SHA256SUMS verified (%d files); sha256(SHA256SUMS)=%s"
      % (key, repo, tag, checked, digest(sums)))
PY
}

smoke_herdr() {
    local repo tag iface proj skill out
    repo="$(field herdr "d['product']['repo']")"
    tag="$(field herdr "d['product']['tag']")"
    iface="$(field herdr "d['product']['interface']")"
    proj="$WORK/herdr-proj"
    mkdir -p "$proj"
    git -C "$proj" init -q
    printf '%s\n' '{"name":"dwp-pin-smoke","private":true}' > "$proj/package.json"
    ( cd "$proj" && npx --yes skills add "https://github.com/${repo}/tree/${tag}" --skill herdr-peers -y >/dev/null 2>&1 ) \
        || { fail "herdr: skills add https://github.com/${repo}/tree/${tag} failed"; return; }
    skill="$(find "$proj" -path '*/herdr-peers/SKILL.md' | head -1)"
    [ -n "$skill" ] || { fail "herdr: installed SKILL.md not found"; return; }
    grep -qE "^[[:space:]]+protocol: ${iface}\$" "$skill" \
        || { fail "herdr: SKILL.md metadata.protocol is not ${iface}"; return; }
    out="$(bash "$(dirname "$skill")/scripts/herdr-peers" --version 2>&1 || true)"
    case "$out" in
        *"${tag#v} (protocol ${iface})"*) ok "herdr: ${repo}@${tag} installs; ${out}"
                                          verify_sums herdr ;;
        *) fail "herdr: helper --version said '${out}', expected ${tag#v} (protocol ${iface})" ;;
    esac
}

smoke_kit() {  # smoke_kit <key> <binary> <install-dir-variable>
    local key="$1" bin="$2" var="$3" repo tag iface src dest ver doc
    repo="$(field "$key" "d['product']['repo']")"
    tag="$(field "$key" "d['product']['tag']")"
    iface="$(field "$key" "d['product']['interface']")"
    src="$WORK/$key-src"
    dest="$WORK/$key-install"
    git clone -q --depth 1 --branch "$tag" "https://github.com/${repo}" "$src" 2>/dev/null \
        || { fail "$key: git clone --branch $tag ${repo} failed"; return; }
    env "$var=$dest" bash "$src/install.sh" --no-rc >/dev/null 2>&1 \
        || { fail "$key: install.sh --no-rc failed"; return; }
    ver="$(env "$var=$dest" "$dest/bin/$bin" --version 2>&1 || true)"
    case "$ver" in
        *"${tag#v}"*) : ;;
        *) fail "$key: '$bin --version' said '$ver', expected ${tag#v}"; return ;;
    esac
    doc="$(env "$var=$dest" "$dest/bin/$bin" doctor --json 2>/dev/null || true)"
    if [ "$(printf '%s' "$doc" | json_field interface 2>/dev/null || true)" = "$iface" ]; then
        ok "$key: ${repo}@${tag} installs; '$ver'; doctor --json interface ${iface}"
        verify_sums "$key" "$src"
    else
        fail "$key: doctor --json does not report interface ${iface}"
    fi
}

smoke_dck_skill() {
    local repo tag proj skill
    repo="$(field devcontainer "d['product']['repo']")"
    tag="$(field devcontainer "d['product']['tag']")"
    proj="$WORK/dck-skill-proj"
    mkdir -p "$proj"
    git -C "$proj" init -q
    printf '%s\n' '{"name":"dwp-pin-smoke","private":true}' > "$proj/package.json"
    ( cd "$proj" && npx --yes skills add "https://github.com/${repo}/tree/${tag}" --skill dck-dockerfile -y >/dev/null 2>&1 ) \
        || { fail "devcontainer: skills add https://github.com/${repo}/tree/${tag} --skill dck-dockerfile failed"; return; }
    skill="$(find "$proj" -path '*/dck-dockerfile/SKILL.md' | head -1)"
    if [ -n "$skill" ] && grep -qE '^name: dck-dockerfile$' "$skill"; then
        ok "devcontainer: ${repo}@${tag} dck-dockerfile skill installs"
    else
        fail "devcontainer: installed dck-dockerfile SKILL.md not found or misnamed"
    fi
}

smoke_vim() {
    local repo tag iface src want got
    repo="$(field vim "d['product']['repo']")"
    tag="$(field vim "d['product']['tag']")"
    iface="$(field vim "d['product']['interface']")"
    src="$WORK/vim-src"
    git clone -q --depth 1 --branch "$tag" "https://github.com/${repo}" "$src" 2>/dev/null \
        || { fail "vim: git clone --branch $tag ${repo} failed"; return; }
    [ "$(json_field interface < "$src/addon/surface.json")" = "$iface" ] \
        || { fail "vim: addon/surface.json interface is not ${iface}"; return; }
    [ "$(json_field version < "$src/addon/surface.json")" = "$tag" ] \
        || { fail "vim: addon/surface.json version is not ${tag}"; return; }
    want="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["install"]["script"]["sha256"])' "$src/addon/surface.json")"
    got="$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$src/install.sh")"
    if [ "$want" = "$got" ]; then
        ok "vim: ${repo}@${tag} surface interface ${iface}, version ${tag}, install.sh sha256 matches"
        verify_sums vim "$src"
    else
        fail "vim: install.sh sha256 ${got} != surface ${want}"
    fi
}

command -v git >/dev/null || { echo "ERROR: git is required" >&2; exit 2; }
command -v python3 >/dev/null || { echo "ERROR: python3 is required" >&2; exit 2; }
command -v curl >/dev/null || { echo "ERROR: curl is required" >&2; exit 2; }

for key in $SELECTED; do
    case "$key" in
        herdr)        command -v npx >/dev/null || { echo "ERROR: npx is required for herdr" >&2; exit 2; }
                      smoke_herdr ;;
        agentkit)     smoke_kit agentkit ak AGENTKIT_HOME ;;
        devcontainer) smoke_kit devcontainer dck DCK_INSTALL_DIR
                      command -v npx >/dev/null || { echo "ERROR: npx is required for devcontainer" >&2; exit 2; }
                      smoke_dck_skill ;;
        vim)          smoke_vim ;;
        *) echo "ERROR: unknown pin '$key'" >&2; exit 2 ;;
    esac
done

if [ "$failures" -gt 0 ]; then
    echo "ecosystem pins: $failures failure(s)"
    exit 1
fi
echo "OK: ecosystem pins verified ($SELECTED)"
