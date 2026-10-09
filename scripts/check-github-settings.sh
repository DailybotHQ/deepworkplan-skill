#!/usr/bin/env bash
set -euo pipefail

# Read-only check of a repository's GitHub settings against the ecosystem
# public repository standard (parent amendment A3, S2). Uses `gh api` (the
# caller's existing GitHub CLI login); changes nothing.
#
# Usage: scripts/check-github-settings.sh OWNER/REPO
# Exit:  0 compliant · 1 a setting differs · 2 usage/environment error

REPO="${1:-}"
[ -n "$REPO" ] || { echo "usage: $0 OWNER/REPO" >&2; exit 2; }
command -v gh >/dev/null || { echo "ERROR: gh is required" >&2; exit 2; }

repo_json="$(gh api "repos/$REPO")" || { echo "ERROR: cannot read repos/$REPO" >&2; exit 2; }
# On failure gh still prints the error body on stdout: assign, then fall back.
prot_json="$(gh api "repos/$REPO/branches/main/protection" 2>/dev/null)" || prot_json='{}'
pvr_json="$(gh api "repos/$REPO/private-vulnerability-reporting" 2>/dev/null)" || pvr_json='{}'
if gh api "repos/$REPO/vulnerability-alerts" >/dev/null 2>&1; then alerts=true; else alerts=false; fi

REPO_JSON="$repo_json" PROT_JSON="$prot_json" PVR_JSON="$pvr_json" ALERTS="$alerts" python3 - <<'PY'
import json, os, sys
repo = json.loads(os.environ['REPO_JSON'])
prot = json.loads(os.environ['PROT_JSON'])
pvr = json.loads(os.environ['PVR_JSON'])
fails = []
def need(ok, what):
    print(('OK   ' if ok else 'FAIL ') + what)
    if not ok:
        fails.append(what)
desc = (repo.get('description') or '').strip()
need(bool(desc) and desc.count('. ') == 0, 'description is one sentence')
home = (repo.get('homepage') or '').rstrip('/')
need(home.startswith('https://deepworkplan.com'), 'homepage on deepworkplan.com')
topics = repo.get('topics') or []
need('deepworkplan' in topics and 4 <= len(topics) <= 7, 'topics: deepworkplan + 3-6 specific (%s)' % ','.join(topics))
need(repo.get('default_branch') == 'main', 'default branch main')
need(repo.get('delete_branch_on_merge') is True, 'automatically delete head branches')
need(repo.get('has_wiki') is False, 'wiki off')
need(repo.get('has_discussions') is False, 'discussions off')
sa = repo.get('security_and_analysis') or {}
need((sa.get('secret_scanning') or {}).get('status') == 'enabled', 'secret scanning on')
need((sa.get('secret_scanning_push_protection') or {}).get('status') == 'enabled', 'secret scanning push protection on')
need(pvr.get('enabled') is True, 'private vulnerability reporting on')
need(os.environ['ALERTS'] == 'true', 'Dependabot alerts on')
checks = ((prot.get('required_status_checks') or {}).get('contexts')) or []
need(len(checks) > 0, 'branch protection requires CI checks (%s)' % ', '.join(checks))
reviews = (prot.get('required_pull_request_reviews') or {}).get('required_approving_review_count', 0)
need(reviews >= 1, 'branch protection requires one review')
need((prot.get('enforce_admins') or {}).get('enabled') is False, 'admins may bypass')
need((prot.get('allow_force_pushes') or {}).get('enabled') is False, 'force pushes blocked on main')
need((prot.get('allow_deletions') or {}).get('enabled') is False, 'deletion of main blocked')
sys.exit(1 if fails else 0)
PY
