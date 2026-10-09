#!/usr/bin/env bash
set -euo pipefail

# Public-hygiene check (ecosystem public repository standard, amendment A3 S3).
#
# Fails when a tracked file carries content a public repository must not:
# personal absolute paths, the private organization or private repository
# names, internal tooling and mesh names, @dailybot.com addresses other than
# the public role aliases, or secret-shaped strings. Bash + grep only, no
# network, bash 3.2 compatible.
#
# Scope: `git ls-files` of the repository (or of $1), excluding vendored
# third-party skill copies under .agents/skills/ (pinned, owned upstream),
# this script and the allowlist itself.
#
# Allowlist: .public-hygiene-allow — one entry per line,
#   <tracked path><TAB or spaces><reason>
# An allowlisted file may carry name-rule hits (with the stated reason). A
# secret-shaped hit is accepted only when the matching line ALSO looks
# obviously fake (contains fake, test, planted or example) — a real-looking
# secret never passes, allowlisted or not.
#
# Usage: scripts/check-public-hygiene.sh [repo_root]
# Exit:  0 clean · 1 findings · 2 usage/environment error

ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: $ROOT is not a git work tree" >&2
    exit 2
fi
ALLOW="$ROOT/.public-hygiene-allow"

# label<TAB>extended regex. Bracketed letters keep these patterns from
# matching this file's own text when the file is scanned elsewhere.
RULES=""
read -r -d '' RULES <<'EOF' || true
personal-path	(/Users/[A-Za-z][A-Za-z0-9._-]+|/home/[a-z][a-z0-9._-]+/)
private-org	DailyBot-[I]nc
private-repo	(dailybot-[c]ore|coding-agent-host-[k]it|dailybot-private-[s]kills|api-[s]ervices|chatbot-[f]unctions|discord-[g]ateway|msteams-app-[m]anifesto|labs-[p]rojects)
internal-tooling	((^|[^A-Za-z0-9_-])db[d]ev([^A-Za-z0-9_-]|$)|dailybot-[d]ev([^A-Za-z0-9_-]|$)|dailybot-[p]eers|dailybot-[w]orkspaces|dailybot-[w]s-|\[dailybot-[m]esh\])
private-email	[A-Za-z0-9._%+-]+@dailybot\.[c]om
EOF
SECRETS=""
read -r -d '' SECRETS <<'EOF' || true
aws-key	AKI[A][0-9A-Z]{16}
github-token	(gh[p]_[A-Za-z0-9]{36}|github_pa[t]_[A-Za-z0-9_]{40,})
openai-anthropic	(s[k]-ant-[A-Za-z0-9_-]{20,}|s[k]-[A-Za-z0-9]{32,})
slack-token	xo[x][baprs]-[A-Za-z0-9-]{10,}
google-key	AI[z]a[0-9A-Za-z_-]{35}
private-key	-----BEGIN [A-Z ]*PRIVATE [K]EY-----
quoted-assignment	(api[_-]?key|secret|token|passw(or)?d)[A-Za-z_]*["']?[[:space:]]*[:=][[:space:]]*["'][^"'[:space:]]{16,}["']
EOF
PUBLIC_ALIASES='^(security|support|ops|conduct)@dailybot\.com$'

allowlisted() {  # $1 = path
    [ -f "$ALLOW" ] || return 1
    grep -vE '^[[:space:]]*(#|$)' "$ALLOW" | awk '{print $1}' | grep -qxF -- "$1"
}

files_list="$(mktemp)"
trap 'rm -f "$files_list"' EXIT
git -C "$ROOT" ls-files -z \
    | tr '\0' '\n' \
    | grep -vE '^\.agents/skills/' \
    | grep -vxF 'scripts/check-public-hygiene.sh' \
    | grep -vxF '.public-hygiene-allow' > "$files_list" || true

findings=0

while IFS= read -r rel; do
    file="$ROOT/$rel"
    [ -f "$file" ] || continue
    # Skip binary files.
    grep -Iq . "$file" 2>/dev/null || continue
    while IFS="$(printf '\t')" read -r label pattern; do
        [ -n "$label" ] || continue
        hits="$(grep -nE -- "$pattern" "$file" 2>/dev/null || true)"
        [ -n "$hits" ] || continue
        if [ "$label" = "private-email" ]; then
            hits="$(printf '%s\n' "$hits" | while IFS= read -r line; do
                bad=0
                for addr in $(printf '%s' "$line" | grep -oE '[A-Za-z0-9._%+-]+@dailybot\.[c]om'); do
                    printf '%s' "$addr" | grep -qE "$PUBLIC_ALIASES" || bad=1
                done
                [ "$bad" -eq 1 ] && printf '%s\n' "$line"
            done || true)"
            [ -n "$hits" ] || continue
        fi
        if allowlisted "$rel"; then
            continue
        fi
        printf '%s\n' "$hits" | head -3 | while IFS= read -r line; do
            echo "FAIL [$label] $rel:$line"
        done
        findings=$((findings + 1))
    done <<EOF_RULES
$RULES
EOF_RULES
    while IFS="$(printf '\t')" read -r label pattern; do
        [ -n "$label" ] || continue
        hits="$(grep -nE -- "$pattern" "$file" 2>/dev/null || true)"
        [ -n "$hits" ] || continue
        real="$(printf '%s\n' "$hits" | grep -viE 'fake|test|planted|example' || true)"
        if [ -z "$real" ] && allowlisted "$rel"; then
            continue
        fi
        [ -n "$real" ] || real="$hits"
        printf '%s\n' "$real" | head -3 | while IFS= read -r line; do
            echo "FAIL [$label] $rel:$(printf '%s' "$line" | cut -c1-12)… (value not printed)"
        done
        findings=$((findings + 1))
    done <<EOF_SECRETS
$SECRETS
EOF_SECRETS
done < "$files_list"

if [ "$findings" -gt 0 ]; then
    echo "public hygiene: $findings finding(s) — fix them, or list an obviously fake fixture in .public-hygiene-allow with a reason"
    exit 1
fi
echo "OK: public hygiene ($(wc -l < "$files_list" | tr -d ' ') tracked files scanned)"
