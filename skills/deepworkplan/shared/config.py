#!/usr/bin/env python3
"""DeepWorkPlan configuration reader and writer (spec/CONFIG.md).

One parser for the two top-level keys of ``.dwp/config.json``:

  * ``benchmark`` — the opt-in field-metrics switch (spec/BENCHMARK.md §1).
    Resolved wholesale: a repository file that carries the object overrides
    the user file; one that omits it defers.
  * ``addons`` — the addon registry (spec/CONFIG.md §3). Resolved **per
    addon key**: the repository entry wins over the user entry for that
    key; a repository file that omits a key defers to the user file.

Locations (highest precedence first): ``<repo>/.dwp/config.json`` — the
repository that owns the plan or the directory given — then
``~/.dwp/config.json``; absent means disabled.

Fail-closed, never raising: a missing file, an unreadable path, invalid
JSON or a wrong-typed value resolves to *disabled* for what it affects,
with exactly one warning naming the file, the key and the reason. An addon
key the pack does not ship (the set of in-pack addon directory names) is
ignored with one warning — forward compatibility. Nothing here imports an
addon, opens an addon file or decides anything a plan depends on: the
registry is informative input to flows that may *offer* or *amplify*,
never to anything that gates conformance.

Usage::

    config.py show [--repo DIR] [--plan DIR]       # resolved view (JSON)
    config.py enabled [--repo DIR] [--plan DIR]    # enabled addon keys, one per line
    config.py enable  KEY [--version vX.Y.Z] --repo DIR   # onboarding writer
    config.py disable KEY --repo DIR
    config.py keys                                 # in-pack addon keys
    config.py descriptors                          # audit every addon.json (opens them)
    config.py self-test

Standard library only (Python 3.9+).
"""

import argparse
import json
import os
import re
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True

CONFIG_SCHEMA_URL = 'https://deepworkplan.com/schema/dwp-config/v1.json'
VERSION_RE = re.compile(r'^v\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?$')
REPO_LABEL = '.dwp/config.json'
USER_LABEL = '~/.dwp/config.json'

_HERE = os.path.dirname(os.path.abspath(__file__))
ADDONS_DIR = os.path.normpath(os.path.join(_HERE, '..', 'addons'))


# ---------------------------------------------------------------------------
# discovery


def addon_keys(addons_dir: str = ADDONS_DIR) -> List[str]:
    """The registry key set: the in-pack addon directory names (contract A1).

    Lists directories only — it never opens a file inside an addon.
    """
    try:
        names = os.listdir(addons_dir)
    except OSError:
        return []
    return sorted(n for n in names
                  if not n.startswith('.')
                  and os.path.isdir(os.path.join(addons_dir, n)))


def find_dwp_root(plan_dir: str) -> Optional[str]:
    """Walk up from a plan directory to its owning ``.dwp`` directory."""
    current = os.path.abspath(plan_dir)
    while True:
        parent = os.path.dirname(current)
        if current == parent:
            return None
        if (os.path.basename(parent) == 'plans'
                and os.path.basename(os.path.dirname(parent)) == '.dwp'):
            return os.path.dirname(parent)
        current = parent


def config_paths(dwp_root: Optional[str],
                 home: Optional[str] = None) -> List[Tuple[str, str]]:
    """(label, path) pairs in precedence order; the repo file only with a root."""
    pairs = []
    if dwp_root is not None:
        pairs.append((REPO_LABEL, os.path.join(dwp_root, 'config.json')))
    home_dir = home if home is not None else os.path.expanduser('~')
    pairs.append((USER_LABEL, os.path.join(home_dir, '.dwp', 'config.json')))
    return pairs


def read_config(path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """(parsed object or None, reason or None) for one file; never raises.

    A missing file is the ordinary "omits everything" case: no reason.
    """
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, 'unreadable (%s); treating as absent' % exc
    if not isinstance(data, dict):
        return None, 'is not a JSON object; treating as absent'
    return data, None


def load_files(dwp_root: Optional[str], home: Optional[str] = None
               ) -> List[Tuple[str, str, Optional[Dict[str, Any]], Optional[str]]]:
    """Read both files once: [(label, path, data, reason)] in precedence order."""
    out = []
    for label, path in config_paths(dwp_root, home):
        data, reason = read_config(path)
        out.append((label, path, data, reason))
    return out


# ---------------------------------------------------------------------------
# benchmark key (behaviour pinned by spec/BENCHMARK.md §1)


def benchmark_section(files, warnings: List[str]) -> Optional[Dict[str, Any]]:
    """The winning ``benchmark`` object (repo over user, wholesale), or None."""
    for label, path, data, reason in files:
        if reason:
            warnings.append('benchmark: benchmark config %s %s' % (path, reason))
        if data is None or 'benchmark' not in data:
            continue
        section = data['benchmark']
        if not isinstance(section, dict):
            warnings.append('benchmark: %s "benchmark" is not an object; '
                            'benchmark disabled' % label)
            return None
        return section
    return None


def resolve_benchmark(files) -> Tuple[bool, bool, List[str]]:
    """(benchmark enabled, learnings enabled, warnings) — fail-closed per key."""
    warnings: List[str] = []
    section = benchmark_section(files, warnings)
    if section is None:
        return False, False, warnings
    enabled = section.get('enabled')
    if not isinstance(enabled, bool):
        warnings.append('benchmark: "benchmark.enabled" is not a boolean; '
                        'benchmark disabled')
        return False, False, warnings
    if not enabled:
        return False, False, warnings
    learnings = section.get('learnings')
    if learnings is None:
        return True, False, warnings
    if not isinstance(learnings, bool):
        warnings.append('benchmark: "benchmark.learnings" is not a boolean; '
                        'learnings disabled (metrics unaffected)')
        return True, False, warnings
    return True, learnings, warnings


# ---------------------------------------------------------------------------
# addons key (spec/CONFIG.md §3)


def _entry_error(value: Any) -> Optional[str]:
    """Why one registry entry is unusable, or None when it is well formed."""
    if not isinstance(value, dict):
        return 'entry is not an object'
    extra = sorted(set(value) - {'enabled', 'version'})
    if extra:
        return 'carries unknown field(s) %s' % ', '.join(extra)
    if 'enabled' not in value:
        return '"enabled" is missing'
    if not isinstance(value['enabled'], bool):
        return '"enabled" is not a boolean'
    if 'version' in value:
        version = value['version']
        if not isinstance(version, str) or not VERSION_RE.match(version):
            return '"version" is not a tag like v1.2.3 or v1.2.3-beta.1'
    return None


def resolve_addons(files, keys: Optional[List[str]] = None
                   ) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Resolve every in-pack addon key; return ({key: view}, warnings).

    A view is ``{"enabled": bool, "version": str|None, "source": label|None}``.
    Per-key precedence: the first file (repo, then user) whose ``addons``
    object **names** the key decides it — a malformed entry there resolves
    to not-enabled (fail-closed) and does not fall through.
    """
    known = list(keys) if keys is not None else addon_keys()
    warnings: List[str] = []
    registries = []
    for label, path, data, reason in files:
        if reason:
            warnings.append('addons: %s %s' % (path, reason))
            continue
        if data is None or 'addons' not in data:
            continue
        reg = data['addons']
        if not isinstance(reg, dict):
            warnings.append('addons: %s "addons" is not an object; no addon '
                            'enabled from this file' % label)
            continue
        for name in sorted(reg):
            if name not in known:
                warnings.append('addons: %s key %r is not an addon this pack '
                                'ships; ignored' % (label, name))
        registries.append((label, reg))
    view: Dict[str, Dict[str, Any]] = {}
    for key in known:
        view[key] = {'enabled': False, 'version': None, 'source': None}
        for label, reg in registries:
            if key not in reg:
                continue
            problem = _entry_error(reg[key])
            if problem:
                warnings.append('addons: %s key %r %s; not enabled'
                                % (label, key, problem))
                view[key]['source'] = label
            else:
                view[key] = {'enabled': reg[key]['enabled'],
                             'version': reg[key].get('version'),
                             'source': label}
            break
    return view, warnings


def resolve(dwp_root: Optional[str], home: Optional[str] = None,
            keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """Both keys from one read of both files."""
    files = load_files(dwp_root, home)
    bench_on, learn_on, bench_warn = resolve_benchmark(files)
    addons, addon_warn = resolve_addons(files, keys)
    return {'benchmark': {'enabled': bench_on, 'learnings': learn_on},
            'addons': addons,
            'warnings': bench_warn + addon_warn}


def enabled_addons(dwp_root: Optional[str], home: Optional[str] = None,
                   keys: Optional[List[str]] = None) -> Tuple[List[str], List[str]]:
    """(sorted enabled addon keys, warnings)."""
    files = load_files(dwp_root, home)
    view, warnings = resolve_addons(files, keys)
    return sorted(k for k, v in view.items() if v['enabled']), warnings


# ---------------------------------------------------------------------------
# addon descriptors (spec/ADDONS.md §7) — opened only for an addon a caller
# already decided to consult (an enabled key, or an explicit audit)


DESCRIPTOR_SCHEMA_URL = 'https://deepworkplan.com/schema/addon-descriptor/v1.json'
ABILITIES = ('stop_agent', 'meter_spend', 'meter_tokens', 'meter_wall_clock',
             'cancel_children', 'model_routing', 'subagents', 'telemetry')
GRANTS = ('gate_command_exec', 'fs_write_plan_scope', 'fs_write_repo_scope',
          'git_operations', 'network_access', 'host_adapter_metering',
          'agent_delegation', 'context_export')
TRANSPORTS = ('headless', 'interactive')
_KEY_RE = re.compile(r'^[a-z][a-z0-9-]{0,63}$')
_REPO_RE = re.compile(r'^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$')
_COMMAND_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._/ -]*$')
_PATH_RE = re.compile(r'^(~/)?[A-Za-z0-9._][A-Za-z0-9._/-]*$')
_IFACE_RE = re.compile(r'^(json:[A-Za-z_][A-Za-z0-9_]*|regex:.+|'
                       r'file-json:(~/)?[A-Za-z0-9._/-]+#[A-Za-z_][A-Za-z0-9_]*)$')


def descriptor_errors(doc: Any, dirname: Optional[str] = None) -> List[str]:
    """Runtime half of schema/addon-descriptor-v1 (closed object)."""
    errs: List[str] = []
    if not isinstance(doc, dict):
        return ['descriptor is not an object']
    allowed = {'schema', 'key', 'product', 'detect', 'provides_abilities',
               'requires_grants', 'transport'}
    for extra in sorted(set(doc) - allowed):
        errs.append('unknown field %r' % extra)
    for req in ('schema', 'key', 'detect', 'provides_abilities', 'requires_grants'):
        if req not in doc:
            errs.append('missing %r' % req)
    if doc.get('schema', DESCRIPTOR_SCHEMA_URL) != DESCRIPTOR_SCHEMA_URL:
        errs.append('schema is not %s' % DESCRIPTOR_SCHEMA_URL)
    key = doc.get('key')
    if 'key' in doc and (not isinstance(key, str) or not _KEY_RE.match(key)):
        errs.append('key is not a kebab-case name')
    if dirname is not None and key != dirname:
        errs.append('key %r does not equal its directory %r' % (key, dirname))
    if 'product' in doc:
        prod = doc['product']
        if not isinstance(prod, dict):
            errs.append('product is not an object')
        else:
            for extra in sorted(set(prod) - {'repo', 'tag', 'interface'}):
                errs.append('product: unknown field %r' % extra)
            if not isinstance(prod.get('repo'), str) or not _REPO_RE.match(prod['repo']):
                errs.append('product.repo is not owner/name')
            if not isinstance(prod.get('tag'), str) or not VERSION_RE.match(prod['tag']):
                errs.append('product.tag is not an exact tag')
            if 'interface' in prod and (type(prod['interface']) is not int
                                        or prod['interface'] < 1):
                errs.append('product.interface is not an integer >= 1')
    if 'detect' in doc:
        det = doc['detect']
        if not isinstance(det, dict):
            errs.append('detect is not an object')
        else:
            for extra in sorted(set(det) - {'command', 'paths', 'interface_from'}):
                errs.append('detect: unknown field %r' % extra)
            if ('command' in det) == ('paths' in det):
                errs.append('detect needs exactly one of command or paths')
            if 'command' in det and (not isinstance(det['command'], str)
                                     or len(det['command']) > 200
                                     or not _COMMAND_RE.match(det['command'])):
                errs.append('detect.command is not a plain argv line')
            if 'paths' in det:
                paths = det['paths']
                if (not isinstance(paths, list) or not paths
                        or len(set(map(str, paths))) != len(paths)
                        or not all(isinstance(x, str) and _PATH_RE.match(x)
                                   for x in paths)):
                    errs.append('detect.paths is not a non-empty list of plain paths')
            if 'interface_from' in det and (not isinstance(det['interface_from'], str)
                                            or not _IFACE_RE.match(det['interface_from'])):
                errs.append('detect.interface_from has an unknown form')
    for field, vocab in (('provides_abilities', ABILITIES), ('requires_grants', GRANTS)):
        if field in doc:
            vals = doc[field]
            if (not isinstance(vals, list) or len(set(map(str, vals))) != len(vals)
                    or not all(v in vocab for v in vals)):
                errs.append('%s holds an unknown or repeated value' % field)
    if 'transport' in doc:
        if doc['transport'] not in TRANSPORTS:
            errs.append('transport is not headless|interactive')
        else:
            if 'subagents' not in (doc.get('provides_abilities') or []):
                errs.append('a transport addon must provide subagents')
            if 'agent_delegation' not in (doc.get('requires_grants') or []):
                errs.append('a transport addon must require agent_delegation')
    return errs


def load_descriptor(key: str, addons_dir: str = ADDONS_DIR
                    ) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """(descriptor or None, errors) for one addon key. Never raises."""
    path = os.path.join(addons_dir, key, 'addon.json')
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            doc = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, ['%s unreadable (%s)' % (path, exc)]
    errs = descriptor_errors(doc, key)
    return (doc if not errs else None), errs


# ---------------------------------------------------------------------------
# writer (onboarding consent; spec/CONFIG.md §4)


class ConfigError(Exception):
    """A write that would clobber or invent — refused, never applied."""


def write_addon(dwp_root: str, key: str, enabled: bool,
                version: Optional[str] = None,
                keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """Set ``addons.<key>`` in the repository file, reconciling, atomically.

    Every other byte of meaning is preserved: other top-level keys, other
    addon entries. An existing file that is not a JSON object is refused —
    a writer never clobbers what it cannot read.
    """
    known = list(keys) if keys is not None else addon_keys()
    if key not in known:
        raise ConfigError('%r is not an addon this pack ships (%s)'
                          % (key, ', '.join(known)))
    if version is not None and not VERSION_RE.match(version):
        raise ConfigError('version %r is not a tag like v1.2.3' % version)
    path = os.path.join(dwp_root, 'config.json')
    data: Dict[str, Any] = {}
    if os.path.exists(path):
        parsed, reason = read_config(path)
        if parsed is None:
            raise ConfigError('%s %s — fix or remove it by hand; the writer '
                              'never overwrites a file it cannot read'
                              % (path, reason or 'unreadable'))
        data = parsed
    reg = data.get('addons')
    if reg is None:
        reg = {}
    if not isinstance(reg, dict):
        raise ConfigError('%s "addons" is not an object — refusing to replace '
                          'it' % path)
    entry: Dict[str, Any] = {'enabled': enabled}
    if version is not None:
        entry['version'] = version
    reg[key] = entry
    data['addons'] = reg
    os.makedirs(dwp_root, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=dwp_root, prefix='.config-')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as out:
            json.dump(data, out, indent=2, sort_keys=True)
            out.write('\n')
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise
    return entry


# ---------------------------------------------------------------------------
# CLI


def _root_from_args(args) -> Optional[str]:
    if getattr(args, 'plan', None):
        return find_dwp_root(args.plan)
    if getattr(args, 'repo', None):
        return os.path.join(os.path.abspath(args.repo), '.dwp')
    return os.path.join(os.getcwd(), '.dwp')


def _emit_warnings(warnings: List[str]) -> None:
    for line in warnings:
        print('WARNING: ' + line, file=sys.stderr)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog='config.py', description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command')
    for name in ('show', 'enabled'):
        p = sub.add_parser(name)
        p.add_argument('--repo')
        p.add_argument('--plan')
    for name in ('enable', 'disable'):
        p = sub.add_parser(name)
        p.add_argument('key')
        p.add_argument('--repo', required=True)
        if name == 'enable':
            p.add_argument('--version')
    sub.add_parser('keys')
    sub.add_parser('descriptors')
    sub.add_parser('self-test')
    args = parser.parse_args(argv)
    if args.command == 'show':
        result = resolve(_root_from_args(args))
        _emit_warnings(result.pop('warnings'))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == 'enabled':
        keys, warnings = enabled_addons(_root_from_args(args))
        _emit_warnings(warnings)
        for key in keys:
            print(key)
        return 0
    if args.command in ('enable', 'disable'):
        try:
            entry = write_addon(_root_from_args(args), args.key,
                                args.command == 'enable',
                                getattr(args, 'version', None))
        except ConfigError as exc:
            print('ERROR: %s' % exc, file=sys.stderr)
            return 2
        print('OK: addons.%s = %s' % (args.key, json.dumps(entry, sort_keys=True)))
        return 0
    if args.command == 'descriptors':
        bad = 0
        for key in addon_keys():
            _doc, errs = load_descriptor(key)
            print('%s %s' % ('OK  ' if not errs else 'FAIL', key)
                  + ('' if not errs else ': ' + '; '.join(errs)))
            bad += bool(errs)
        return 1 if bad else 0
    if args.command == 'keys':
        for key in addon_keys():
            print(key)
        return 0
    if args.command == 'self-test':
        return self_test()
    parser.print_help()
    return 2


# ---------------------------------------------------------------------------
# self-test


SELF_TEST_PROBES = 33


def self_test() -> int:
    import shutil
    failures: List[str] = []
    probes = 0

    def check(name: str, ok: bool, detail: str = '') -> None:
        nonlocal probes
        probes += 1
        if not ok:
            failures.append('%s %s' % (name, detail))

    keys = ['agentkit', 'herdr', 'vim']
    tmp = tempfile.mkdtemp(prefix='dwp-config-selftest-')
    try:
        repo = os.path.join(tmp, 'repo', '.dwp')
        home = os.path.join(tmp, 'home')
        os.makedirs(repo)
        os.makedirs(os.path.join(home, '.dwp'))
        user = os.path.join(home, '.dwp', 'config.json')
        repo_cfg = os.path.join(repo, 'config.json')

        def put(path, text):
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(text)

        def run():
            files = load_files(repo, home)
            return resolve_addons(files, keys)

        # 1. nothing anywhere: everything disabled, no warning
        view, warn = run()
        check('absent', not any(v['enabled'] for v in view.values()) and not warn,
              repr((view, warn)))
        # 2. user file enables herdr
        put(user, '{"addons": {"herdr": {"enabled": true, "version": "v0.1.0"}}}')
        view, warn = run()
        check('user enables', view['herdr'] == {'enabled': True, 'version': 'v0.1.0',
                                                'source': USER_LABEL}, repr(view))
        # 3. repo file omitting the key defers to the user file
        put(repo_cfg, '{"addons": {"vim": {"enabled": true}}}')
        view, warn = run()
        check('repo omits defers', view['herdr']['enabled'] and view['vim']['enabled'],
              repr(view))
        check('repo source', view['vim']['source'] == REPO_LABEL, repr(view))
        # 4. repo entry wins per key
        put(repo_cfg, '{"addons": {"herdr": {"enabled": false}}}')
        view, warn = run()
        check('repo wins', view['herdr'] == {'enabled': False, 'version': None,
                                             'source': REPO_LABEL}, repr(view))
        # 5. wrong-typed enabled fails closed, one warning, no fall-through
        put(repo_cfg, '{"addons": {"herdr": {"enabled": "yes"}}}')
        view, warn = run()
        check('wrong type closed', not view['herdr']['enabled'], repr(view))
        check('wrong type one warning', len(warn) == 1 and 'herdr' in warn[0]
              and REPO_LABEL in warn[0], repr(warn))
        # 6. bad version string fails closed
        put(repo_cfg, '{"addons": {"vim": {"enabled": true, "version": "latest"}}}')
        view, warn = run()
        check('bad version closed', not view['vim']['enabled'] and len(warn) == 1,
              repr((view, warn)))
        # 7. pre-release version accepted
        put(repo_cfg, '{"addons": {"vim": {"enabled": true, "version": "v7.0.0-beta.1"}}}')
        view, warn = run()
        check('prerelease version', view['vim']['enabled'] and not warn, repr((view, warn)))
        # 8. missing "enabled" is not enabled
        put(repo_cfg, '{"addons": {"vim": {"version": "v0.4.0"}}}')
        view, warn = run()
        check('missing enabled', not view['vim']['enabled'] and len(warn) == 1,
              repr(warn))
        # 8b. an unknown field inside an entry fails closed (closed entry)
        put(repo_cfg, '{"addons": {"vim": {"enabled": true, "pin": "main"}}}')
        view, warn = run()
        check('closed entry', not view['vim']['enabled'] and len(warn) == 1
              and 'pin' in warn[0], repr(warn))
        # 9. unknown key ignored with exactly one warning
        put(repo_cfg, '{"addons": {"teleport": {"enabled": true}}}')
        view, warn = run()
        check('unknown ignored', 'teleport' not in view and len(warn) == 1
              and 'teleport' in warn[0], repr(warn))
        # 10. invalid JSON in repo: one warning, user file still applies
        put(repo_cfg, '{"addons": {"vim": {"enabled": tru')
        view, warn = run()
        check('invalid json warns once', len(warn) == 1 and 'unreadable' in warn[0],
              repr(warn))
        check('invalid json defers', view['herdr']['enabled'], repr(view))
        # 11. "addons" not an object
        put(repo_cfg, '{"addons": ["vim"]}')
        view, warn = run()
        check('addons not object', len(warn) == 1 and not view['vim']['enabled'],
              repr(warn))
        # 12. a non-object top level
        put(repo_cfg, '[1, 2]')
        view, warn = run()
        check('top not object', len(warn) == 1, repr(warn))
        # 13. benchmark resolution unchanged and independent of addons
        put(repo_cfg, '{"benchmark": {"enabled": true}, "addons": {"vim": {"enabled": true}}}')
        files = load_files(repo, home)
        check('benchmark on', resolve_benchmark(files)[:2] == (True, False),
              repr(resolve_benchmark(files)))
        put(repo_cfg, '{"benchmark": {"enabled": "yes"}}')
        b = resolve_benchmark(load_files(repo, home))
        check('benchmark wrong type', b[0] is False and len(b[2]) == 1, repr(b))
        # 14. writer reconciles: preserves other keys and entries
        put(repo_cfg, '{"benchmark": {"enabled": true}, "addons": {"herdr": {"enabled": false}}}')
        write_addon(repo, 'vim', True, 'v0.4.0', keys)
        with open(repo_cfg, encoding='utf-8') as fh:
            data = json.load(fh)
        check('writer preserves', data['benchmark'] == {'enabled': True}
              and data['addons']['herdr'] == {'enabled': False}
              and data['addons']['vim'] == {'enabled': True, 'version': 'v0.4.0'},
              repr(data))
        # 15. writer refuses an unknown key, a bad version, an unreadable file
        for label, call in (
                ('writer unknown', lambda: write_addon(repo, 'teleport', True, None, keys)),
                ('writer version', lambda: write_addon(repo, 'vim', True, 'latest', keys))):
            try:
                call()
                check(label, False, 'accepted')
            except ConfigError:
                check(label, True)
        put(repo_cfg, '{oops')
        try:
            write_addon(repo, 'vim', True, None, keys)
            check('writer unreadable', False, 'clobbered')
        except ConfigError:
            with open(repo_cfg, encoding='utf-8') as fh:
                check('writer unreadable', fh.read() == '{oops', 'file changed')
        # 16. writer creates a fresh file
        os.unlink(repo_cfg)
        write_addon(repo, 'agentkit', False, None, keys)
        with open(repo_cfg, encoding='utf-8') as fh:
            check('writer fresh', json.load(fh) == {'addons': {'agentkit': {'enabled': False}}})
        # 17. key set is directory names only, and the shipped set is non-empty
        check('addon keys', 'vim' in addon_keys() and all(
            os.path.isdir(os.path.join(ADDONS_DIR, k)) for k in addon_keys()),
            repr(addon_keys()))
        # 17b. descriptor validator: the shipped set is valid; mutants refused
        good = {'schema': DESCRIPTOR_SCHEMA_URL, 'key': 'herdr',
                'product': {'repo': 'DailybotHQ/herdr-peers', 'tag': 'v0.1.0',
                            'interface': 1},
                'detect': {'command': 'herdr-peers --version'},
                'provides_abilities': ['subagents'],
                'requires_grants': ['agent_delegation'],
                'transport': 'interactive'}
        check('descriptor ok', descriptor_errors(good, 'herdr') == [],
              repr(descriptor_errors(good, 'herdr')))
        for label, mutate in (
                ('key mismatch', lambda d: d.update(key='vim')),
                ('shell command', lambda d: d['detect'].update(command='ak doctor | sh')),
                ('both detect', lambda d: d['detect'].update(paths=['x'])),
                ('unknown ability', lambda d: d.update(provides_abilities=['root'])),
                ('transport without grant', lambda d: d.update(requires_grants=[])),
                ('floating tag', lambda d: d['product'].update(tag='main'))):
            bad = json.loads(json.dumps(good))
            mutate(bad)
            check('descriptor ' + label, bool(descriptor_errors(bad, 'herdr')))
        # 18. find_dwp_root
        plan = os.path.join(repo, 'plans', 'PLAN_x')
        os.makedirs(plan)
        check('find root', find_dwp_root(plan) == os.path.abspath(repo),
              repr(find_dwp_root(plan)))
        check('no root', find_dwp_root(tmp) is None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if probes != SELF_TEST_PROBES:
        failures.append('probe count %d != pinned %d' % (probes, SELF_TEST_PROBES))
    for line in failures:
        print('FAIL: ' + line)
    if failures:
        return 1
    print('OK: config self-test (%d probes)' % probes)
    return 0


if __name__ == '__main__':
    sys.exit(main())
