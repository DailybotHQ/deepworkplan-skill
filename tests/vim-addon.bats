#!/usr/bin/env bash
# Contract tests for the vim editor addon — a thin integrator of the
# DeepWorkPlan Vim product (DailybotHQ/deepworkplan-vim) across its
# surfaces: the addon's SKILL.md + SPEC.md + templates, spec/ADDONS.md §6.7,
# the addons/README.md registry and the onboard Phase 7b offer.
#
# The policy under test: the addon offers DeepWorkPlan Vim as an optional
# machine-level install from onboard Phase 7b (explicit opt-in, never
# required, never a conformance gate); detection, feature claims and the
# install steps come from the product's addon/surface.json (interface 1) at
# the single pinned tag; an existing Neovim config is never overwritten
# without explicit consent (a non-interactive install onto an existing
# config aborts with instructions; backups go to
# ~/.config/previous-deepworkplan-vim); the install is three separate,
# checksum-verified steps (never a fetch-and-execute pipe, never piped
# PowerShell); the Neovim plugin is the v7.1 route and is never offered for
# install before it ships; and no flow other than onboard wires the addon.
#
# Run with:  bats tests/
# Requires:  bats-core

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    SK="$REPO_ROOT/skills/deepworkplan"
    ADDON="$SK/addons/vim"
    SPEC="$SK/spec/ADDONS.md"
    README="$SK/addons/README.md"
    ONBOARD="$SK/onboard/addons.md"
    PIN_TAG="v0.4.0"
}

vim_doc_has() {
    sed 's/^[[:space:]]*>[[:space:]]\{0,1\}//' "$1" | tr '\n' ' ' | tr -s ' ' | grep -qF -- "$2"
}

@test "frontmatter: exact sibling field set, invocable, version stamped with the pack" {
    grep -q '^name: deepworkplan-addon-vim$' "$ADDON/SKILL.md"
    grep -q '^user-invocable: true$' "$ADDON/SKILL.md"
    grep -q '^documentation_url: https://deepworkplan.com/kit/vim$' "$ADDON/SKILL.md"
    grep -q '^allowed-tools:' "$ADDON/SKILL.md"
    grep -q '^metadata:' "$ADDON/SKILL.md"
    # The release stamp owns the number: the addon carries the router's version.
    router="$(grep -m1 '^version:' "$SK/SKILL.md")"
    [ "$(grep -m1 '^version:' "$ADDON/SKILL.md")" = "$router" ]
    vim_doc_has "$ADDON/SKILL.md" "a thin integrator that reads the product's own addon/surface.json (interface 1)"
    ! grep -q '^homepage:' "$ADDON/SKILL.md"
}

@test "SPEC: own version line, RFC-2119 keywords, the frozen install contract" {
    grep -q '| \*\*Version\*\* | 0\.2\.0 |' "$ADDON/SPEC.md"
    grep -q 'MUST NOT' "$ADDON/SPEC.md"
    grep -q 'SHOULD' "$ADDON/SPEC.md"
    vim_doc_has "$ADDON/SPEC.md" "three separate steps"
    vim_doc_has "$ADDON/SPEC.md" "MUST NOT appear anywhere in this pack's text"
    vim_doc_has "$ADDON/SPEC.md" "https://deepworkplan.com/vim"
    # A checksum mismatch is never run.
    vim_doc_has "$ADDON/SPEC.md" "a mismatch MUST NOT be run"
    vim_doc_has "$ADDON/SPEC.md" "never overwritten without explicit consent"
    vim_doc_has "$ADDON/SPEC.md" "aborts with instructions"
    vim_doc_has "$ADDON/SPEC.md" "never required"
}

@test "surface-driven: states, interface check and feature claims come from addon/surface.json" {
    for f in "$ADDON/SKILL.md" "$ADDON/SPEC.md" "$ADDON/templates/INTEGRATION.md"; do
        grep -qF 'addon/surface.json' "$f"
    done
    # The product's identity files decide "installed" vs "existing config".
    vim_doc_has "$ADDON/SPEC.md" "lacks either identity file (\`install.lua\`, \`lua/plugins.lua\`)"
    vim_doc_has "$ADDON/SPEC.md" "**installed without surface**"
    # An unknown interface major is one warning and "not available" — never an error.
    vim_doc_has "$ADDON/SPEC.md" "print exactly one warning line and treat the editor as **not available**"
    vim_doc_has "$ADDON/SKILL.md" "never an error of the repository or the plan"
    # Feature claims are bounded by the pinned surface, not a hand-kept list.
    vim_doc_has "$ADDON/SPEC.md" "**only** the features the pinned surface lists in \`features[]\`"
}

@test "single pin: every product tag in the addon tree is the pinned one" {
    # Every deepworkplan-vim ref the addon spells (tag pins, clone branches,
    # DWP_VIM_REF) names exactly one tag.
    run bash -c "grep -rhoE '(deepworkplan-vim@|--branch |DWP_VIM_REF=)v[0-9]+\.[0-9]+\.[0-9]+' '$ADDON' '$ONBOARD' '$README' '$SPEC' | sed -E 's/.*(v[0-9]+\.[0-9]+\.[0-9]+)$/\1/' | sort -u"
    [ "$status" -eq 0 ]
    [ "$output" = "$PIN_TAG" ]
}

@test "lexical trust: no fetch-and-execute installer strings in the addon tree" {
    # Snyk E005 / Socket W012 flag curl/wget pipe shapes lexically wherever
    # they appear under the pack (precedent 6a05ed9).
    run grep -rInE 'curl|wget' "$ADDON"
    [ "$status" -ne 0 ]
    run grep -rIn 'irm .*iex\|iwr .*iex' "$ADDON"
    [ "$status" -ne 0 ]
    run grep -rn 'deepworkplan.com/install.sh' "$ADDON"
    [ "$status" -ne 0 ]
}

@test "template: consent branch, Windows path, backup location, reconcile" {
    test -f "$ADDON/templates/INTEGRATION.md"
    vim_doc_has "$ADDON/templates/INTEGRATION.md" "aborts with instructions"
    vim_doc_has "$ADDON/templates/INTEGRATION.md" "previous-deepworkplan-vim"
    vim_doc_has "$ADDON/templates/INTEGRATION.md" "install deferred: existing config, consent required"
    vim_doc_has "$ADDON/templates/INTEGRATION.md" "Never guess consent."
    vim_doc_has "$ADDON/templates/INTEGRATION.md" "winget install Neovim.Neovim"
    vim_doc_has "$ADDON/templates/INTEGRATION.md" "Never piped PowerShell."
    vim_doc_has "$ADDON/templates/INTEGRATION.md" "Reconcile"
}

@test "two routes: the full editor now, the plugin named for v7.1 and never offered for install" {
    vim_doc_has "$ADDON/SKILL.md" "## Two routes"
    vim_doc_has "$ADDON/SKILL.md" "**The Neovim plugin (v7.1, not shipped).**"
    vim_doc_has "$ADDON/SPEC.md" "MUST NOT offer to install it or claim it exists before it ships"
    # No install line for the plugin exists anywhere in the pack.
    run grep -rnE 'deepworkplan\.nvim@|clone [^ ]*deepworkplan\.nvim' "$SK"
    [ "$status" -ne 0 ]
}

@test "registry: addons/README.md row, spec/ADDONS.md §6.7 entry" {
    grep -qF '| DeepWorkPlan Vim |' "$README"
    grep -F '| DeepWorkPlan Vim |' "$README" | grep -qF 'thin integrator, explicit opt-in'
    grep -F '| DeepWorkPlan Vim |' "$README" | grep -qF 'never impose'
    grep -F '| DeepWorkPlan Vim |' "$README" | grep -qF 'previous-deepworkplan-vim'
    grep -q '^### 6\.7 DeepWorkPlan Vim' "$SPEC"
    vim_doc_has "$SPEC" "Seven addon folders ship"
    vim_doc_has "$SPEC" "never** overwritten without explicit consent"
    vim_doc_has "$SPEC" "skills/deepworkplan/addons/vim/"
}

@test "wired as an opt-in: onboard Phase 7b offers it; no other flow references it" {
    grep -qF '| **DeepWorkPlan Vim** | [`../addons/vim/`](../addons/vim/SKILL.md) |' "$ONBOARD"
    vim_doc_has "$ONBOARD" "offer — never impose — the editor"
    vim_doc_has "$ONBOARD" "Four active addons are **explicit opt-ins**"
    run grep -rIl 'addons/vim\|addon-vim\|DeepWorkPlan Vim' \
        "$SK/execute" "$SK/create" "$SK/refine" "$SK/resume" "$SK/status" "$SK/verify"
    [ "$status" -ne 0 ]
}
