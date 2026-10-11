#!/usr/bin/env python3
"""DeepWorkPlan addon sync planner (onboard Phase 7b, "all addons" and upgrade).

Read-only. For every addon the pack ships it reports what is installed, at
which version, what the repository's registry (``.dwp/config.json``)
recorded, the pack's pin, and the one next action:

  install         absent — offer it; install on acceptance
  upgrade         installed older than the pack's pin
  record          installed at the pin, but the registry is missing or stale
  available       a machine-level tool is present, but this repository never
                  enabled it — offered only in a full setup, never recorded
                  on an upgrade
  current         installed at the pin and recorded — nothing to do
  newer           installed newer than the pin — keep it, never downgrade
  reconcile       hand-written work is present (a docker setup without dck):
                  reconcile through the addon's diff-and-consent flow
  verify          detected, version unreadable — re-check by hand
  declined        the registry records a decline — do not re-offer
  evaluate        the addon decides applicability from the repository
                  (design-system: an interface surface) — run its detection
  not-applicable  nothing to install for (no dependency manifest)

Nothing here installs, upgrades, renders or writes: the onboarding agent
runs each addon's own flow, then records the result with ``config.py
enable``. Running the planner twice on an unchanged repository prints the
same plan. ``pending`` lists only what the repository uses or requires and
is not yet at the pin; ``offers`` lists what fits but was never chosen here,
and ``evaluate`` what the addon itself must decide.

Usage::

    addon_sync.py plan --repo DIR [--json] [--keys k1,k2]
    addon_sync.py self-test

Standard library only (Python 3.9+).
"""

import argparse
import glob
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as dwp_config  # noqa: E402  (sibling module)
import resources  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
PACK_ROOT = os.path.normpath(os.path.join(_HERE, '..'))
TAG_RE = re.compile(r'v?(\d+)\.(\d+)\.(\d+)')
NOTHING_PENDING = ('current', 'newer', 'available', 'declined', 'evaluate',
                   'not-applicable')

# Repository-level copies a skills CLI install leaves behind.
VENDORED = {'ai-diff-reviewer': 'ai-diff-reviewer', 'dailybot': 'dailybot'}

# Any of these marks a repository with declared dependencies.
MANIFESTS = ('package.json', 'pyproject.toml', 'requirements.txt', 'setup.py',
             'Pipfile', 'Cargo.toml', 'go.mod', 'Gemfile', 'composer.json',
             'pom.xml', 'build.gradle', 'build.gradle.kts', 'mix.exs',
             'pubspec.yaml', 'Package.swift')

# A dev-container setup somebody wrote by hand: the paths dck init would
# reconcile. A production Dockerfile or compose file elsewhere is not one —
# it is reported (``docker_files``) and the row stays an offer.
DEVCONTAINER_FILES = ('.devcontainer/devcontainer.json',
                      'docker/local/docker-compose.yaml')
APP_DOCKER_FILES = ('Dockerfile', 'docker-compose.yml', 'docker-compose.yaml',
                    'compose.yml', 'compose.yaml')


def parse_tag(text: Optional[str]) -> Optional[Tuple[int, int, int]]:
    match = TAG_RE.search(text or '')
    return tuple(int(g) for g in match.groups()) if match else None


def as_tag(text: Optional[str]) -> Optional[str]:
    parsed = parse_tag(text)
    return 'v%d.%d.%d' % parsed if parsed else None


def compare(installed: Optional[str], pin: Optional[str]) -> Optional[int]:
    """-1 older, 0 equal, 1 newer, None when either side is unknown."""
    a, b = parse_tag(installed), parse_tag(pin)
    if a is None or b is None:
        return None
    return (a > b) - (a < b)


def skill_version(path: str) -> Optional[str]:
    try:
        with open(path, encoding='utf-8', errors='replace') as handle:
            head = handle.read(4096)
    except OSError:
        return None
    match = re.search(r'(?m)^version:\s*["\']?([^"\'\s]+)', head)
    return as_tag(match.group(1)) if match else None


def surface_version(det: Dict[str, Any]) -> Optional[str]:
    """The ``version`` of a detected JSON surface file (vim's surface.json)."""
    for path in det.get('paths', []):
        if not path.endswith('.json'):
            continue
        try:
            with open(os.path.expanduser(path), encoding='utf-8') as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict) and isinstance(doc.get('version'), str):
            return as_tag(doc['version'])
    return None


def lock_ref(repo: str, name: str) -> Optional[str]:
    try:
        with open(os.path.join(repo, 'skills-lock.json'), encoding='utf-8') as fh:
            doc = json.load(fh)
        return as_tag((doc.get('skills') or {}).get(name, {}).get('ref'))
    except (OSError, ValueError, AttributeError):
        return None


def registry(repo: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """The repository registry (addons object) and a warning, never raising."""
    path = os.path.join(repo, '.dwp', 'config.json')
    if not os.path.exists(path):
        return {}, None
    parsed, reason = dwp_config.read_config(path)
    if parsed is None:
        return {}, '%s %s — rows ignore the registry' % (path, reason)
    reg = parsed.get('addons')
    return (reg if isinstance(reg, dict) else {}), None


def devcontainer_layout(repo: str) -> Tuple[str, Optional[str]]:
    """('dck', stamp tag) | ('handwritten', None) | ('none', None)."""
    if os.path.isfile(os.path.join(repo, '.devcontainer', 'dck.toml')):
        stamp = None
        for path in sorted(glob.glob(os.path.join(
                repo, 'docker', 'local', '*', 'dck', 'VERSION'))):
            if os.path.isfile(path) and not os.path.islink(path):
                with open(path, encoding='utf-8', errors='replace') as fh:
                    match = re.match(r'^devcontainer-kit (v\S+)', fh.read())
                stamp = as_tag(match.group(1)) if match else None
                break
        return 'dck', stamp
    if any(os.path.exists(os.path.join(repo, p)) for p in DEVCONTAINER_FILES):
        return 'handwritten', None
    return 'none', None


def version_action(version: Optional[str], pin: Optional[str]) -> str:
    order = compare(version, pin)
    if order is None:
        return 'verify'
    return {-1: 'upgrade', 0: 'current', 1: 'newer'}[order]


def with_registry(action: str, entry: Any, pin: Optional[str],
                  version: Optional[str]) -> str:
    """Promote ``current``/``newer`` to ``record`` when the registry lags."""
    if action not in ('current', 'newer'):
        return action
    expected = version if action == 'newer' else pin
    if not isinstance(entry, dict) or entry.get('enabled') is not True:
        return 'record'
    if expected and as_tag(entry.get('version')) != expected:
        return 'record'  # stale, or enabled without the version it runs
    return action


def plan_row(key: str, repo: str, reg: Dict[str, Any]) -> Dict[str, Any]:
    doc, errs = dwp_config.load_descriptor(key)
    product = (doc or {}).get('product') or {}
    pin = product.get('tag')
    det = (doc or {}).get('detect') or {}
    machine = 'command' in det or any(p.startswith('~/') for p in det.get('paths', []))
    entry = reg.get(key)
    row: Dict[str, Any] = {
        'key': key, 'scope': 'machine' if machine else 'repo', 'pin': pin,
        'installed': False, 'version': None, 'registry': entry,
        'action': None, 'reason': None,
        'skill': 'addons/%s/SKILL.md' % key,
    }
    if errs:
        row.update(action='verify', reason='invalid descriptor (%s)' % errs[0])
        return row
    if isinstance(entry, dict) and entry.get('enabled') is False:
        row.update(action='declined', reason='the registry records a decline')
        return row

    if key in VENDORED:
        skill = os.path.join(repo, '.agents', 'skills', VENDORED[key], 'SKILL.md')
        if os.path.isfile(skill):
            version = skill_version(skill) or lock_ref(repo, VENDORED[key])
            row.update(installed=True, version=version, scope='repo')
            row['action'] = version_action(version, pin)
        else:
            row['action'] = 'install'
            row['reason'] = ('required local review (Phase 7a)'
                             if key == 'ai-diff-reviewer' else
                             'offer only when the team uses Dailybot')
        if key == 'dailybot':
            present, _out, _why = resources._run_detect(det['command'])
            row['cli'] = 'present' if present else 'absent'
    elif key == 'devcontainer':
        layout, stamp = devcontainer_layout(repo)
        kit = resources.addon_status(key, repo)
        kit_version = kit.get('version') if kit.get('detected') else None
        row.update(scope='machine+repo', layout=layout, stamp=stamp,
                   kit=kit_version, installed=layout == 'dck',
                   version=stamp,
                   docker_files=[p for p in APP_DOCKER_FILES
                                 if os.path.exists(os.path.join(repo, p))])
        if layout == 'handwritten':
            row.update(action='reconcile',
                       reason='a docker setup without dck markers: dck init '
                              '--dry-run shows each replace as a diff; nothing '
                              'changes without consent, and a backup first')
        elif layout == 'none':
            row['action'] = 'install'
            if row['docker_files']:
                row['reason'] = ('an application docker setup is present (%s); '
                                 'dck renders its own files beside it'
                                 % ', '.join(row['docker_files']))
        else:
            worst = min((compare(v, pin) for v in (stamp, kit_version)
                         if compare(v, pin) is not None), default=None)
            row['action'] = ('verify' if worst is None else
                             {-1: 'upgrade', 0: 'current', 1: 'newer'}[worst])
            if kit_version is None:
                row.update(action='install', reason='layout present; the dck '
                           'kit is not installed on this machine')
    elif key == 'dependency-upgrade':
        present = os.path.isfile(os.path.join(repo, '.agents', 'commands',
                                              'lib-upgrade.md'))
        row['installed'] = present
        if present:
            row['action'] = 'current'  # a reasoned delegator: no version to compare
        elif any(os.path.exists(os.path.join(repo, m)) for m in MANIFESTS):
            row.update(action='install', reason='near-default: declared '
                       'dependencies; the delegator is inert')
        else:
            row.update(action='not-applicable', reason='no dependency manifest')
    elif key == 'design-system':
        present = any(os.path.isfile(os.path.join(repo, p))
                      for p in det.get('paths', []))
        row['installed'] = present
        row['action'] = 'current' if present else 'evaluate'
        if not present:
            row['reason'] = 'offer only when an interface surface is detected'
    else:  # machine-level products: agentkit, herdr, vim, and future ones
        status = resources.addon_status(key, repo)
        enabled = isinstance(entry, dict) and entry.get('enabled') is True
        if status.get('state') == 'installed-without-surface':
            row.update(installed=True, reason=status['reason'],
                       action='upgrade' if enabled else 'available')
        elif status.get('detected'):
            row.update(installed=True,
                       version=status.get('version') or surface_version(det))
            row['action'] = version_action(row['version'], pin)
            if not status.get('compatible') and row['action'] == 'current':
                row.update(action='verify', reason=status.get('reason'))
            if not enabled:
                # present on this machine (perhaps for another project), never
                # enabled here: the registry records only this repo's choices
                row.update(action='available',
                           reason='on this machine (%s, pin %s); not enabled '
                                  'for this repository' % (row['version'] or
                                                           'version unknown', pin))
        else:
            row.update(action='install', reason=status.get('reason'))
    base = row['action']
    row['action'] = with_registry(base, entry, pin, row['version'])
    # The record to run after an accepted step succeeds; never for a tool that
    # is merely present on the machine (`available`): the repository's
    # registry records only what it chose.
    if row['action'] in ('install', 'upgrade', 'record', 'reconcile'):
        tag = row['version'] if base == 'newer' else pin
        row['record'] = ('python3 <pack>/shared/config.py enable %s%s --repo %s'
                         % (key, ' --version %s' % tag if tag else '', repo))
    elif row['action'] == 'available':
        # run only when the developer accepts it in a full setup
        tag = as_tag(row['version']) if compare(row['version'], pin) == 1 else pin
        row['on_accept'] = ('python3 <pack>/shared/config.py enable %s%s --repo %s'
                            % (key, ' --version %s' % tag if tag else '', repo))
    return row


def build_plan(repo: str, keys: Optional[List[str]] = None) -> Dict[str, Any]:
    repo = os.path.abspath(repo)
    reg, warning = registry(repo)
    known = dwp_config.addon_keys()
    selected = [k for k in (keys or known) if k in known]
    rows = [plan_row(k, repo, reg) for k in selected]
    pack = skill_version(os.path.join(PACK_ROOT, 'SKILL.md'))
    vendored = skill_version(os.path.join(repo, '.agents', 'skills',
                                          'deepworkplan', 'SKILL.md'))
    # pending: what this repository uses or requires and is not yet at the
    # pin. offers: what fits but was never chosen here — made once; a
    # decline writes nothing, so an offer never blocks "nothing pending".
    def required(r):
        entry = r['registry']
        return r['key'] == 'ai-diff-reviewer' or (
            isinstance(entry, dict) and entry.get('enabled') is True)
    offer_like = ('install', 'reconcile')
    pending = [r['key'] for r in rows if r['action'] not in NOTHING_PENDING
               and (r['action'] not in offer_like or required(r))]
    offers = [r['key'] for r in rows if r['action'] == 'available'
              or (r['action'] in offer_like and not required(r))]
    to_evaluate = [r['key'] for r in rows if r['action'] == 'evaluate']
    return {'schema': 'dwp-addon-sync/v1', 'repo': repo, 'pack': pack,
            'vendored_pack': vendored,
            'pack_action': (None if vendored is None
                            else version_action(vendored, pack)),
            'rows': rows, 'pending': pending, 'offers': offers,
            'evaluate': to_evaluate,
            'warnings': [warning] if warning else []}


def render(plan: Dict[str, Any]) -> str:
    lines = ['addon               scope         installed   pin         action',
             '------------------  ------------  ----------  ----------  ----------']
    for r in plan['rows']:
        lines.append('%-18s  %-12s  %-10s  %-10s  %s' % (
            r['key'], r['scope'], r['version'] or ('yes' if r['installed'] else '-'),
            r['pin'] or '(in pack)', r['action']))
        if r.get('reason'):
            lines.append('%-18s  %s' % ('', r['reason']))
    if plan['vendored_pack']:
        lines.append('deepworkplan pack   repo          %-10s  %-10s  %s' % (
            plan['vendored_pack'], plan['pack'], plan['pack_action']))
    lines.append('pending: %s' % (', '.join(plan['pending']) or 'nothing'))
    if plan['offers']:
        lines.append('offers: %s (only where they fit; a decline writes nothing)'
                     % ', '.join(plan['offers']))
    if plan['evaluate']:
        lines.append('evaluate: %s (run its detection before reporting done)'
                     % ', '.join(plan['evaluate']))
    for w in plan['warnings']:
        lines.append('warning: %s' % w)
    return '\n'.join(lines)


def self_test() -> int:
    ok = True
    for text, want in (('v1.2.3', (1, 2, 3)), ('herdr-peers 0.1.0 (protocol 1)',
                        (0, 1, 0)), ('x', None)):
        ok &= parse_tag(text) == want
    ok &= compare('v0.4.0', 'v0.5.0') == -1 and compare('v1.0.0', 'v1.0.0') == 0
    ok &= with_registry('current', None, 'v1.0.0', 'v1.0.0') == 'record'
    ok &= with_registry('current', {'enabled': True, 'version': 'v1.0.0'},
                        'v1.0.0', 'v1.0.0') == 'current'
    print('OK: addon_sync self-test' if ok else 'FAIL: addon_sync self-test')
    return 0 if ok else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog='addon_sync.py')
    sub = parser.add_subparsers(dest='command')
    p = sub.add_parser('plan')
    p.add_argument('--repo', required=True)
    p.add_argument('--json', action='store_true')
    p.add_argument('--keys')
    sub.add_parser('self-test')
    args = parser.parse_args(argv)
    if args.command == 'self-test':
        return self_test()
    if args.command != 'plan':
        parser.print_help()
        return 2
    if not os.path.isdir(args.repo):
        print('addon_sync: %s is not a directory' % args.repo, file=sys.stderr)
        return 2
    keys = args.keys.split(',') if args.keys else None
    plan = build_plan(args.repo, keys)
    print(json.dumps(plan, indent=2, sort_keys=True) if args.json else render(plan))
    return 0


if __name__ == '__main__':
    sys.exit(main())
