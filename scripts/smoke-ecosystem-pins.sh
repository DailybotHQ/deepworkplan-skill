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
#              `dck --version` names the tag, `dck doctor --json` .interface
#   vim        tagged clone; addon/surface.json interface and version, and the
#              surface's install.script.sha256 equals the tag's install.sh
#
# Everything runs under a throwaway HOME and temp directories: nothing is
# written to the real home, no shell rc is touched, nothing is left behind.
# Network: git and the npm `skills` CLI only. Bash 3.2 compatible.
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

smoke_herdr() {
    local repo tag iface proj skill out
    repo="$(field herdr "d['product']['repo']")"
    tag="$(field herdr "d['product']['tag']")"
    iface="$(field herdr "d['product']['interface']")"
    proj="$WORK/herdr-proj"
    mkdir -p "$proj"
    git -C "$proj" init -q
    printf '%s\n' '{"name":"dwp-pin-smoke","private":true}' > "$proj/package.json"
    ( cd "$proj" && npx --yes skills add "${repo}@${tag}" --skill herdr-peers -y >/dev/null 2>&1 ) \
        || { fail "herdr: skills add ${repo}@${tag} failed"; return; }
    skill="$(find "$proj" -path '*/herdr-peers/SKILL.md' | head -1)"
    [ -n "$skill" ] || { fail "herdr: installed SKILL.md not found"; return; }
    grep -qE "^[[:space:]]+protocol: ${iface}\$" "$skill" \
        || { fail "herdr: SKILL.md metadata.protocol is not ${iface}"; return; }
    out="$(bash "$(dirname "$skill")/scripts/herdr-peers" --version 2>&1 || true)"
    case "$out" in
        *"${tag#v} (protocol ${iface})"*) ok "herdr: ${repo}@${tag} installs; ${out}" ;;
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
    else
        fail "$key: doctor --json does not report interface ${iface}"
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
    else
        fail "vim: install.sh sha256 ${got} != surface ${want}"
    fi
}

command -v git >/dev/null || { echo "ERROR: git is required" >&2; exit 2; }
command -v python3 >/dev/null || { echo "ERROR: python3 is required" >&2; exit 2; }

for key in $SELECTED; do
    case "$key" in
        herdr)        command -v npx >/dev/null || { echo "ERROR: npx is required for herdr" >&2; exit 2; }
                      smoke_herdr ;;
        agentkit)     smoke_kit agentkit ak AGENTKIT_HOME ;;
        devcontainer) smoke_kit devcontainer dck DCK_INSTALL_DIR ;;
        vim)          smoke_vim ;;
        *) echo "ERROR: unknown pin '$key'" >&2; exit 2 ;;
    esac
done

if [ "$failures" -gt 0 ]; then
    echo "ecosystem pins: $failures failure(s)"
    exit 1
fi
echo "OK: ecosystem pins verified ($SELECTED)"
