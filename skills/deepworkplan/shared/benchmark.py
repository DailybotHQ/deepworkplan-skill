#!/usr/bin/env python3
"""v6 opt-in benchmark field metrics (spec/BENCHMARK.md).

Derives, never imputes: the per-plan record is computed entirely from records
the plan already owns — ``journal.ndjson`` events, ``manifest.json``,
``contract.json``, ``state.json`` — plus best-effort, read-only git diff
stats for the plan window. Tokens and spend exist only when a metering host
journaled ``resource_sample`` events; otherwise they are ``null`` with
``metered: false`` (the journal rule — missing data is exposed as missing,
never imputed — carries over verbatim).

Contract highlights (all normative in spec/BENCHMARK.md):

  * **Opt-in, fail-closed.** ``<repo>/.dwp/config.json`` overrides
    ``~/.dwp/config.json``; absent/malformed/wrong-typed input resolves to
    *disabled* with exactly one warning line. Disabled repositories behave
    byte-identically to a pack without this subsystem.
  * **Never blocking.** Any derivation or emission failure degrades to a
    warning and exit status 0 — emission failure is never plan failure.
    Usage errors (bad arguments) are the only exit-2 conditions.
  * **Deterministic.** No emission timestamp, no wall clock, sorted keys;
    two runs over identical plan bytes produce identical artifact bytes.
  * **v6 only.** v5-generation plans are refused with one line and exit 0;
    the v5 line is frozen.
  * **Never a conformance gate.** ``verify`` does not read these artifacts.

Stdlib-only, Python 3.9+ floor, like every shipped helper.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import ledger
except ImportError:  # pragma: no cover - direct execution from another cwd
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import ledger  # noqa: E402

SCHEMA_URL = 'https://deepworkplan.com/schema/benchmark-record/v1.json'
MANIFEST_V6_URL = 'https://deepworkplan.com/schema/plan-manifest/v6.json'

RECORD_FIELDS = ('schema', 'plan', 'title', 'generation', 'contract_id',
                 'status', 'versions', 'timing', 'shape', 'friction',
                 'gates', 'metered', 'environment', 'diff_stats')

AGGREGATE_NOTE = ('aggregates describe recorded executions; workloads differ '
                  'across plans, repositories and versions - this is evidence '
                  'for discussion, not a causal comparison')

# limit_id values the record understands; unknown ids are ignored with their
# unit named (V6_RESOURCES: an unknown counter family is advisory).
_METER_SPEND_IDS = ('spend_usd',)
_METER_TOKEN_IDS = ('tokens', 'token_count')


# ---------------------------------------------------------------------------
# configuration (spec section 1)


def _read_config(path: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Return (parsed-object-or-None, warning-or-None) for one config file."""
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, 'benchmark config %s unreadable (%s); treating as absent' % (path, exc)
    if not isinstance(data, dict):
        return None, 'benchmark config %s is not a JSON object; treating as absent' % path
    return data, None


def resolve_enabled(plan_dir: str) -> Tuple[bool, List[str]]:
    """Resolve the benchmark flag for the repository that owns ``plan_dir``.

    Precedence per spec section 1: repo ``.dwp/config.json`` (per key, the
    ``benchmark`` object overrides wholesale) then ``~/.dwp/config.json``,
    then disabled. Fail-closed: any malformed input is disabled + warning.
    """
    warnings: List[str] = []
    dwp_root = find_dwp_root(plan_dir)
    if dwp_root is None:
        return False, ['benchmark: plan directory has no .dwp ancestor; benchmark disabled']
    repo_cfg, warn = _read_config(os.path.join(dwp_root, 'config.json'))
    if warn:
        warnings.append('benchmark: ' + warn)
    if repo_cfg is not None and 'benchmark' in repo_cfg:
        section = repo_cfg['benchmark']
        if not isinstance(section, dict):
            return False, warnings + [
                'benchmark: .dwp/config.json "benchmark" is not an object; benchmark disabled']
        enabled = section.get('enabled')
        if isinstance(enabled, bool):
            return enabled, warnings
        return False, warnings + [
            'benchmark: .dwp/config.json "benchmark.enabled" is not a boolean; benchmark disabled']
    home_cfg, warn = _read_config(os.path.join(os.path.expanduser('~'), '.dwp', 'config.json'))
    if warn:
        warnings.append('benchmark: ' + warn)
    if home_cfg is not None and 'benchmark' in home_cfg:
        section = home_cfg['benchmark']
        if not isinstance(section, dict):
            return False, warnings + [
                'benchmark: ~/.dwp/config.json "benchmark" is not an object; benchmark disabled']
        enabled = section.get('enabled')
        if isinstance(enabled, bool):
            return enabled, warnings
        return False, warnings + [
            'benchmark: ~/.dwp/config.json "benchmark.enabled" is not a boolean; benchmark disabled']
    return False, warnings


def find_dwp_root(plan_dir: str) -> Optional[str]:
    """Walk up from ``plan_dir`` to the owning ``.dwp`` directory."""
    current = os.path.abspath(plan_dir)
    while True:
        parent = os.path.dirname(current)
        if current == parent:
            return None
        if os.path.basename(parent) == 'plans' and os.path.basename(os.path.dirname(parent)) == '.dwp':
            return os.path.dirname(parent)
        current = parent


# ---------------------------------------------------------------------------
# plan records (read-only)


def _load_json(path: str) -> Optional[Any]:
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def parse_journal(plan_dir: str) -> Tuple[List[Dict[str, Any]], int]:
    """Parse ``journal.ndjson``; stop at the first unreadable line.

    Returns (events, torn_lines). A torn tail is data loss, not a crash: the
    record derives from the valid prefix and the caller surfaces the count.
    """
    path = os.path.join(plan_dir, 'journal.ndjson')
    events: List[Dict[str, Any]] = []
    torn = 0
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    torn += 1
                    break
                if not isinstance(event, dict):
                    torn += 1
                    break
                events.append(event)
    except OSError:
        return [], 0
    return events, torn


def _parse_ts(value: str) -> Optional[datetime]:
    try:
        parsed = datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
        return parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def detect_agent_tool() -> str:
    """Best-effort agent detection; mirrors the context.sh families."""
    override = os.environ.get('DWP_AGENT_TOOL')
    if override:
        return override
    if os.environ.get('CLAUDECODE'):
        return 'claude-code'
    if os.environ.get('CURSOR'):
        return 'cursor'
    if os.environ.get('OPENAI_CODEX') or os.environ.get('CODEX_HOME'):
        return 'codex'
    return 'unknown'


def pack_version() -> str:
    """Version of the emitting pack, from its SKILL.md frontmatter."""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        skill = os.path.join(current, 'SKILL.md')
        if os.path.isfile(skill):
            try:
                with open(skill, 'r', encoding='utf-8') as handle:
                    match = re.search(r'^version:\s*"?([0-9]+\.[0-9]+\.[0-9]+)"?',
                                      handle.read(4096), re.MULTILINE)
                if match:
                    return match.group(1)
            except OSError:
                pass
        current = os.path.dirname(current)
    return 'unknown'


def _git(repo_root: str, args: List[str]) -> Optional[str]:
    """Run one read-only git query; None on any failure (best-effort)."""
    try:
        proc = subprocess.run(['git', '-C', repo_root] + args,
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _repo_branch(repo_root: str) -> str:
    out = _git(repo_root, ['rev-parse', '--abbrev-ref', 'HEAD'])
    if out is None:
        return 'unknown'
    branch = out.strip()
    if branch == 'HEAD':  # detached
        sha = _git(repo_root, ['rev-parse', '--short', 'HEAD'])
        return sha.strip() if sha else 'unknown'
    return branch or 'unknown'


def _diff_stats(repo_root: str, base_revision: Optional[str],
                events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Files/insertions/deletions from the first task_start revision to HEAD.

    Any git failure -> available false and null counts (never zero, never
    omitted - spec section 3).
    """
    stats: Dict[str, Any] = {'available': False, 'files': None,
                             'insertions': None, 'deletions': None}
    if not base_revision:
        return stats
    out = _git(repo_root, ['diff', '--numstat', base_revision + '..HEAD'])
    if out is None:
        return stats
    files = insertions = deletions = 0
    for line in out.splitlines():
        parts = line.split('\t')
        if len(parts) < 3:
            continue
        added, removed = parts[0], parts[1]
        files += 1
        if added != '-':
            insertions += int(added)
        if removed != '-':
            deletions += int(removed)
    stats.update({'available': True, 'files': files,
                  'insertions': insertions, 'deletions': deletions})
    return stats


# ---------------------------------------------------------------------------
# derivation (spec sections 3-4)


def derive_record(plan_dir: str) -> Dict[str, Any]:
    """Derive the closed benchmark record from the plan's own records."""
    manifest = _load_json(os.path.join(plan_dir, 'manifest.json'))
    contract = _load_json(os.path.join(plan_dir, 'contract.json'))
    state = _load_json(os.path.join(plan_dir, 'state.json'))
    if not isinstance(manifest, dict) or not isinstance(contract, dict):
        raise ValueError('plan records missing or malformed (manifest/contract)')

    events, torn = parse_journal(plan_dir)
    if torn:
        print('benchmark: journal tail torn (%d unreadable line(s)); deriving '
              'from the valid prefix' % torn)

    plan_name = contract.get('plan') or os.path.basename(os.path.normpath(plan_dir))

    # timing - calendar span between recorded timestamps, never compute time
    stamps = [_parse_ts(str(event.get('ts'))) for event in events]
    stamps = [stamp for stamp in stamps if stamp is not None]
    first_ts = stamps[0] if stamps else None
    last_ts = stamps[-1] if stamps else None
    span = int((last_ts - first_ts).total_seconds()) if first_ts and last_ts and last_ts >= first_ts else 0
    task_starts = [event for event in events if event.get('type') == 'task_start']
    spanned_tasks = sorted({str(event.get('task')) for event in task_starts if event.get('task')})

    # shape - identity-derived counts from the contract
    tasks = contract.get('tasks') if isinstance(contract.get('tasks'), list) else []
    criteria_names = set()
    gate_intents = 0
    for task in tasks:
        if not isinstance(task, dict):
            continue
        intents = task.get('gate_intent') if isinstance(task.get('gate_intent'), list) else []
        gate_intents += len(intents)
        for intent in intents:
            if isinstance(intent, dict) and intent.get('criterion'):
                criteria_names.add(str(intent['criterion']))
    acceptance = contract.get('acceptance')
    if isinstance(acceptance, list):
        for item in acceptance:
            if isinstance(item, dict) and item.get('criterion'):
                criteria_names.add(str(item['criterion']))
            elif isinstance(item, str):
                criteria_names.add(item)
    invariants = contract.get('invariants')
    invariant_count = len(invariants) if isinstance(invariants, list) else 0

    # friction and gates - journal-derived
    friction = {'adaptations': 0, 'amendments': 0, 'interventions': 0,
                'refusals': 0, 'retries': 0}
    type_counts = {'adaptation': 'adaptations', 'amendment': 'amendments',
                   'intervention': 'interventions', 'refusal': 'refusals'}
    gate_runs = 0
    exit_0 = 0
    exit_nonzero = 0
    histogram = {'observed': 0, 'imported': 0, 'asserted': 0}
    failed_pairs = set()
    for event in events:
        kind = event.get('type')
        if kind in type_counts:
            friction[type_counts[kind]] += 1
        elif kind == 'gate_run':
            gate_runs += 1
            code = event.get('exit_code')
            if code == 0:
                exit_0 += 1
            else:
                exit_nonzero += 1
            trust = str(event.get('trust') or 'asserted')
            if trust in histogram:
                histogram[trust] += 1
            key = (str(event.get('task')), str(event.get('criterion')))
            if code != 0:
                failed_pairs.add(key)
            elif key in failed_pairs:
                friction['retries'] += 1

    # metered - only what a metering host journaled; never synthesized
    tokens: Optional[int] = None
    spend: Optional[float] = None
    metered = False
    for event in events:
        if event.get('type') != 'resource_sample':
            continue
        limit_id = str(event.get('limit_id') or '')
        value = event.get('value')
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        metered = True
        if limit_id in _METER_TOKEN_IDS:
            tokens = (tokens or 0) + int(value)
        elif limit_id in _METER_SPEND_IDS:
            spend = round((spend or 0.0) + float(value), 2)

    # status - projected from state.json
    status = 'ready'
    if isinstance(state, dict):
        state_tasks = state.get('tasks') if isinstance(state.get('tasks'), list) else []
        statuses = [str(item.get('status')) for item in state_tasks
                    if isinstance(item, dict) and item.get('status')]
        blocker = state.get('blocker')
        if blocker:
            status = 'blocked'
        elif 'in_progress' in statuses:
            status = 'in_progress'
        elif statuses and all(name == 'completed' for name in statuses):
            status = 'completed'

    # environment + diff window
    dwp_root = find_dwp_root(plan_dir)
    repo_root = os.path.dirname(dwp_root) if dwp_root else os.path.dirname(
        os.path.abspath(plan_dir))
    base_revision = None
    for event in events:
        if event.get('type') == 'task_start':
            fingerprint = event.get('fingerprint')
            if isinstance(fingerprint, dict) and fingerprint.get('revision'):
                base_revision = str(fingerprint['revision'])
                break

    return {
        'schema': SCHEMA_URL,
        'plan': plan_name,
        'title': str(contract.get('title') or plan_name),
        'generation': 'v6',
        'contract_id': str(contract.get('contract_id') or ''),
        'status': status,
        'versions': {
            'dwp_skill': pack_version(),
            'spec': str(contract.get('spec_version') or 'unknown'),
            'agent_tool': detect_agent_tool(),
        },
        'timing': {
            'first_event_ts': first_ts.strftime('%Y-%m-%dT%H:%M:%SZ') if first_ts else None,
            'last_event_ts': last_ts.strftime('%Y-%m-%dT%H:%M:%SZ') if last_ts else None,
            'span_seconds': span,
            'task_count_spanned': len(spanned_tasks),
        },
        'shape': {
            'tasks': len(tasks) or len(spanned_tasks),
            'criteria': len(criteria_names),
            'invariants': invariant_count,
            'gate_intents': gate_intents,
            'events': len(events),
        },
        'friction': friction,
        'gates': {
            'runs': gate_runs,
            'exit_0': exit_0,
            'exit_nonzero': exit_nonzero,
            'evidence_histogram': histogram,
        },
        'metered': {'flag': metered, 'tokens': tokens, 'spend_usd': spend},
        'environment': {
            'repo': os.path.basename(os.path.normpath(repo_root)) or 'unknown',
            'branch': _repo_branch(repo_root),
        },
        'diff_stats': _diff_stats(repo_root, base_revision, events),
    }


# ---------------------------------------------------------------------------
# record validation (runtime half; the jsonschema half is Task 4's fixtures)


def validate_record(record: Any) -> List[str]:
    """Closed-field structural check mirroring the published schema."""
    problems: List[str] = []
    if not isinstance(record, dict):
        return ['record is not a JSON object']
    extra = sorted(set(record) - set(RECORD_FIELDS))
    missing = sorted(set(RECORD_FIELDS) - set(record))
    if extra:
        problems.append('extra top-level field(s): %s' % ', '.join(extra))
    if missing:
        problems.append('missing top-level field(s): %s' % ', '.join(missing))
    if record.get('schema') != SCHEMA_URL:
        problems.append('schema const mismatch')
    if not re.match(r'^PLAN_([0-9]{3,}_)?[a-z0-9]+(_[a-z0-9]+){1,4}$',
                    str(record.get('plan') or '')):
        problems.append('plan name grammar')
    if record.get('generation') != 'v6':
        problems.append('generation must be v6')
    if not re.match(r'^[0-9a-f]{64}$', str(record.get('contract_id') or '')):
        problems.append('contract_id shape')
    if record.get('status') not in ('ready', 'in_progress', 'blocked', 'completed'):
        problems.append('status enum')
    for section in ('versions', 'timing', 'shape', 'friction', 'gates',
                    'metered', 'environment', 'diff_stats'):
        if not isinstance(record.get(section), dict):
            problems.append('%s is not an object' % section)
    if problems:
        return problems
    for key in ('adaptations', 'amendments', 'interventions', 'refusals', 'retries'):
        if not isinstance(record['friction'].get(key), int):
            problems.append('friction.%s is not an integer' % key)
    metered = record['metered']
    if not isinstance(metered.get('flag'), bool):
        problems.append('metered.flag is not a boolean')
    if not metered.get('flag') and (metered.get('tokens') is not None
                                    or metered.get('spend_usd') is not None):
        problems.append('unmetered record carries token/spend values (imputation)')
    if metered.get('flag') and metered.get('tokens') is None and metered.get('spend_usd') is None:
        problems.append('metered flag without any metered value')
    diff = record['diff_stats']
    if not diff.get('available') and any(diff.get(k) is not None
                                         for k in ('files', 'insertions', 'deletions')):
        problems.append('unavailable diff_stats carry counts')
    if diff.get('available') and any(diff.get(k) is None
                                     for k in ('files', 'insertions', 'deletions')):
        problems.append('available diff_stats lack counts')
    return problems


# ---------------------------------------------------------------------------
# rendering


def render_markdown(record: Dict[str, Any]) -> str:
    """Human summary rendered from the record - never a second source."""
    timing = record['timing']
    shape = record['shape']
    friction = record['friction']
    gates = record['gates']
    metered = record['metered']
    env = record['environment']
    diff = record['diff_stats']
    lines = [
        '# Benchmark record — %s' % record['title'],
        '',
        'Opt-in field metrics derived from this plan\'s own records '
        '(spec/BENCHMARK.md). Calendar span is elapsed time between recorded '
        'timestamps, not compute time. Never a conformance gate.',
        '',
        '| Field | Value |',
        '|---|---|',
        '| Plan | `%s` |' % record['plan'],
        '| Contract | `%s` |' % record['contract_id'],
        '| Status | %s |' % record['status'],
        '| Skill / spec / agent | %s / %s / %s |' % (
            record['versions']['dwp_skill'], record['versions']['spec'],
            record['versions']['agent_tool']),
        '| Repository / branch | %s / %s |' % (env['repo'], env['branch']),
        '',
        '## Timing (calendar span)',
        '',
        '- First event: %s' % timing['first_event_ts'],
        '- Last event: %s' % timing['last_event_ts'],
        '- Span: %d s' % timing['span_seconds'],
        '- Tasks spanned: %d' % timing['task_count_spanned'],
        '',
        '## Shape',
        '',
        '- Tasks: %d · criteria: %d · invariants: %d · gate intents: %d' % (
            shape['tasks'], shape['criteria'], shape['invariants'],
            shape['gate_intents']),
        '- Journal events: %d' % shape['events'],
        '',
        '## Friction',
        '',
        '- Adaptations: %d · amendments: %d · interventions: %d · refusals: %d' % (
            friction['adaptations'], friction['amendments'],
            friction['interventions'], friction['refusals']),
        '- Gate retries after a failure: %d' % friction['retries'],
        '',
        '## Gates',
        '',
        '- Runs: %d (exit 0: %d, nonzero: %d)' % (
            gates['runs'], gates['exit_0'], gates['exit_nonzero']),
        '- Evidence: observed %d · imported %d · asserted %d' % (
            gates['evidence_histogram']['observed'],
            gates['evidence_histogram']['imported'],
            gates['evidence_histogram']['asserted']),
        '',
        '## Resources',
        '',
    ]
    if metered['flag']:
        lines.append('- Metered: tokens %s · spend %s USD' % (
            metered['tokens'] if metered['tokens'] is not None else 'null',
            metered['spend_usd'] if metered['spend_usd'] is not None else 'null'))
    else:
        lines.append('- Not metered: tokens and spend are null — never imputed.')
    lines += [
        '',
        '## Diff window',
        '',
    ]
    if diff['available']:
        lines.append('- Files changed: %d · insertions: %d · deletions: %d' % (
            diff['files'], diff['insertions'], diff['deletions']))
    else:
        lines.append('- Diff window unavailable (counts null, never estimated).')
    lines.append('')
    return '\n'.join(lines)


def _serialize(record: Dict[str, Any]) -> bytes:
    return (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False)
            + '\n').encode('utf-8')


def _atomic_write(path: str, data: bytes) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    handle, temp = tempfile.mkstemp(dir=directory, prefix='.benchmark-')
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(data)
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# commands


def cmd_report(plan_dir: str) -> int:
    enabled, warnings = resolve_enabled(plan_dir)
    for warning in warnings:
        print(warning)
    if not enabled:
        print('benchmark: disabled for this repository; nothing emitted')
        return 0
    manifest = _load_json(os.path.join(plan_dir, 'manifest.json'))
    if not isinstance(manifest, dict) or manifest.get('schema') != MANIFEST_V6_URL:
        print('benchmark: plan is not v6-generation (no v6 manifest contract '
              'pointer); not measured — the v5 line is frozen')
        return 0
    try:
        record = derive_record(plan_dir)
        problems = validate_record(record)
        if problems:
            print('benchmark: derived record failed closed-field validation: %s'
                  % '; '.join(problems))
            return 0
        payload = _serialize(record)
        _atomic_write(os.path.join(plan_dir, 'analysis_results', 'benchmark.json'), payload)
        _atomic_write(os.path.join(plan_dir, 'analysis_results', 'BENCHMARK.md'),
                      render_markdown(record).encode('utf-8'))
    except Exception as exc:  # noqa: BLE001 — emission failure never blocks the plan
        print('benchmark: emission skipped after derivation failure (%s); '
              'plan completion is unaffected' % exc)
        return 0
    print('benchmark: record emitted (%d tasks, %d events, calendar span %d s) '
          '-> analysis_results/benchmark.json + BENCHMARK.md'
          % (record['shape']['tasks'], record['shape']['events'],
             record['timing']['span_seconds']))
    return 0


def _iter_plan_records(root: str) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    """Collect records + v5 plan names under one repository root."""
    plans_dir = os.path.join(root, '.dwp', 'plans')
    records: List[Dict[str, Any]] = []
    v5: List[str] = []
    skipped: List[str] = []
    if not os.path.isdir(plans_dir):
        return records, v5, skipped
    for name in sorted(os.listdir(plans_dir)):
        plan_dir = os.path.join(plans_dir, name)
        record_path = os.path.join(plan_dir, 'analysis_results', 'benchmark.json')
        if os.path.isfile(record_path):
            record = _load_json(record_path)
            if isinstance(record, dict) and not validate_record(record):
                records.append(record)
            else:
                skipped.append(name)
            continue
        manifest = _load_json(os.path.join(plan_dir, 'manifest.json'))
        if isinstance(manifest, dict) and manifest.get('schema') != MANIFEST_V6_URL:
            v5.append(name)
    return records, v5, skipped


def _median(values: List[int]) -> int:
    ordered = sorted(values)
    if not ordered:
        return 0
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) // 2


def _aggregate_report(records: List[Dict[str, Any]], v5: List[str],
                      skipped: List[str]) -> str:
    lines: List[str] = ['# DWP benchmark aggregate', '']
    lines.append('Note: %s.' % AGGREGATE_NOTE)
    lines.append('')
    versions: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for record in records:
        skill = record['versions']['dwp_skill']
        repo = record['environment']['repo']
        versions.setdefault(skill, {}).setdefault(repo, []).append(record)
    for skill in sorted(versions):
        lines.append('## Skill %s' % skill)
        lines.append('')
        for repo in sorted(versions[skill]):
            group = versions[skill][repo]
            spans = [record['timing']['span_seconds'] for record in group]
            gate_runs = sum(record['gates']['runs'] for record in group)
            gate_fail = sum(record['gates']['exit_nonzero'] for record in group)
            metered = sum(1 for record in group if record['metered']['flag'])
            lines.append('- `%s`: %d plan(s); span min/median/max %d/%d/%d s; '
                         'gate failure ratio %d/%d; metered %d/%d'
                         % (repo, len(group), min(spans), _median(spans), max(spans),
                            gate_fail, gate_runs, metered, len(group)))
        lines.append('')
    if len(versions) >= 2:
        lines.append('## Version over version')
        lines.append('')
        lines.append('| Skill | Plans | Gate failures | Median span (s) |')
        lines.append('|---|---|---|---|')
        for skill in sorted(versions):
            group = [record for repo_groups in versions[skill].values()
                     for record in repo_groups]
            spans = [record['timing']['span_seconds'] for record in group]
            lines.append('| %s | %d | %d/%d | %d |' % (
                skill, len(group), sum(record['gates']['exit_nonzero'] for record in group),
                sum(record['gates']['runs'] for record in group), _median(spans)))
        lines.append('')
        lines.append('Note: %s.' % AGGREGATE_NOTE)
        lines.append('')
    if v5:
        lines.append('## Not collected (v5, frozen line)')
        lines.append('')
        lines.append(', '.join('`%s`' % name for name in v5))
        lines.append('')
    if skipped:
        lines.append('## Skipped (invalid records)')
        lines.append('')
        lines.append(', '.join('`%s`' % name for name in skipped))
        lines.append('')
    return '\n'.join(lines)


CSV_COLUMNS = ['plan', 'repo', 'branch', 'dwp_skill', 'spec', 'agent_tool',
               'status', 'span_seconds', 'task_count_spanned', 'tasks',
               'criteria', 'invariants', 'gate_intents', 'events',
               'adaptations', 'amendments', 'interventions', 'refusals',
               'retries', 'gate_runs', 'exit_0', 'exit_nonzero',
               'evidence_observed', 'evidence_imported', 'evidence_asserted',
               'metered', 'tokens', 'spend_usd', 'diff_available', 'files',
               'insertions', 'deletions']


def _csv_row(record: Dict[str, Any]) -> List[str]:
    return [str(record['plan']), record['environment']['repo'],
            record['environment']['branch'], record['versions']['dwp_skill'],
            record['versions']['spec'], record['versions']['agent_tool'],
            record['status'], str(record['timing']['span_seconds']),
            str(record['timing']['task_count_spanned']),
            str(record['shape']['tasks']), str(record['shape']['criteria']),
            str(record['shape']['invariants']),
            str(record['shape']['gate_intents']), str(record['shape']['events']),
            str(record['friction']['adaptations']),
            str(record['friction']['amendments']),
            str(record['friction']['interventions']),
            str(record['friction']['refusals']),
            str(record['friction']['retries']), str(record['gates']['runs']),
            str(record['gates']['exit_0']), str(record['gates']['exit_nonzero']),
            str(record['gates']['evidence_histogram']['observed']),
            str(record['gates']['evidence_histogram']['imported']),
            str(record['gates']['evidence_histogram']['asserted']),
            str(record['metered']['flag']), str(record['metered']['tokens']),
            str(record['metered']['spend_usd']),
            str(record['diff_stats']['available']),
            str(record['diff_stats']['files']),
            str(record['diff_stats']['insertions']),
            str(record['diff_stats']['deletions'])]


def cmd_aggregate(roots: List[str], scan: Optional[str], csv_path: Optional[str],
                  out_path: Optional[str]) -> int:
    all_roots = list(roots)
    if scan:
        for name in sorted(os.listdir(scan)):
            candidate = os.path.join(scan, name)
            if os.path.isdir(os.path.join(candidate, '.dwp')) and candidate not in all_roots:
                all_roots.append(candidate)
    records: List[Dict[str, Any]] = []
    v5: List[str] = []
    skipped: List[str] = []
    for root in all_roots:
        root_records, root_v5, root_skipped = _iter_plan_records(os.path.abspath(root))
        records.extend(root_records)
        v5.extend('%s/%s' % (os.path.basename(os.path.normpath(root)), name)
                  for name in root_v5)
        skipped.extend('%s/%s' % (os.path.basename(os.path.normpath(root)), name)
                       for name in root_skipped)
    records.sort(key=lambda record: (record['environment']['repo'], record['plan']))
    report = _aggregate_report(records, v5, skipped)
    if csv_path:
        lines = [','.join(CSV_COLUMNS)]
        lines.extend(','.join('"%s"' % value.replace('"', '""')
                              for value in _csv_row(record)) for record in records)
        _atomic_write(csv_path, ('\n'.join(lines) + '\n').encode('utf-8'))
        print('benchmark: CSV written (%d row(s)) -> %s' % (len(records), csv_path))
    payload = report.encode('utf-8')
    if out_path:
        _atomic_write(out_path, payload)
        print('benchmark: aggregate written -> %s' % out_path)
    else:
        sys.stdout.write(payload.decode('utf-8'))
    if not records:
        print('benchmark: no records found under the given roots', file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# self-test


def _fixture_plan(root: str, generation: str = 'v6') -> str:
    """Materialize a minimal synthetic plan folder and return its path."""
    plan_dir = os.path.join(root, '.dwp', 'plans', 'PLAN_001_self_test_probe')
    os.makedirs(plan_dir, exist_ok=True)
    contract_id = 'a' * 64
    manifest = {'schema': MANIFEST_V6_URL if generation == 'v6'
                else 'https://deepworkplan.com/schema/plan-manifest/v5.json',
                'plan': 'PLAN_001_self_test_probe',
                'contract': {'path': 'contract.json', 'id': contract_id}}
    contract = {
        'schema': 'https://deepworkplan.com/schema/plan-contract/v6.json',
        'plan': 'PLAN_001_self_test_probe', 'title': 'self test probe',
        'contract_id': contract_id, 'spec_version': '6.0.0', 'revision': 1,
        'tasks': [
            {'id': 'T-one', 'title': 'one', 'prerequisites': [],
             'gate_intent': [{'criterion': 'AC-one', 'check': 'true'}]},
            {'id': 'T-two', 'title': 'two', 'prerequisites': ['T-one'],
             'gate_intent': [{'criterion': 'AC-two', 'check': 'true'}]},
        ],
        'acceptance': [{'criterion': 'AC-one'}, {'criterion': 'AC-two'}],
        'invariants': [{'id': 'INV-one', 'statement': 'stay stdlib-only'}],
    }
    state = {'schema': 'https://deepworkplan.com/schema/plan-state/v5.json',
             'plan': 'PLAN_001_self_test_probe', 'contract_id': contract_id,
             'blocker': None,
             'tasks': [{'id': 'T-one', 'status': 'completed', 'title': 'one'},
                       {'id': 'T-two', 'status': 'completed', 'title': 'two'}]}
    with open(os.path.join(plan_dir, 'manifest.json'), 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle)
    with open(os.path.join(plan_dir, 'contract.json'), 'w', encoding='utf-8') as handle:
        json.dump(contract, handle)
    with open(os.path.join(plan_dir, 'state.json'), 'w', encoding='utf-8') as handle:
        json.dump(state, handle)
    events = [
        {'type': 'approval', 'ts': '2026-01-02T10:00:00Z', 'seq': 1},
        {'type': 'task_start', 'ts': '2026-01-02T10:05:00Z', 'seq': 2, 'task': 'T-one',
         'fingerprint': {'revision': '0' * 40, 'dirty': ''}},
        {'type': 'gate_run', 'ts': '2026-01-02T10:20:00Z', 'seq': 3, 'task': 'T-one',
         'criterion': 'AC-one', 'exit_code': 1, 'trust': 'observed'},
        {'type': 'adaptation', 'ts': '2026-01-02T10:25:00Z', 'seq': 4},
        {'type': 'gate_run', 'ts': '2026-01-02T10:40:00Z', 'seq': 5, 'task': 'T-one',
         'criterion': 'AC-one', 'exit_code': 0, 'trust': 'observed'},
        {'type': 'task_start', 'ts': '2026-01-02T11:00:00Z', 'seq': 6, 'task': 'T-two',
         'fingerprint': {'revision': '1' * 40, 'dirty': ''}},
        {'type': 'gate_run', 'ts': '2026-01-02T11:30:00Z', 'seq': 7, 'task': 'T-two',
         'criterion': 'AC-two', 'exit_code': 0, 'trust': 'observed'},
        {'type': 'refusal', 'ts': '2026-01-02T11:35:00Z', 'seq': 8},
        {'type': 'resource_sample', 'ts': '2026-01-02T11:36:00Z', 'seq': 9,
         'limit_id': 'spend_usd', 'value': 3.25, 'unit': 'USD'},
        {'type': 'resource_sample', 'ts': '2026-01-02T11:37:00Z', 'seq': 10,
         'limit_id': 'tokens', 'value': 41000, 'unit': 'tokens'},
    ]
    with open(os.path.join(plan_dir, 'journal.ndjson'), 'w', encoding='utf-8') as handle:
        for event in events:
            handle.write(json.dumps(event) + '\n')
    return plan_dir


def self_test() -> Tuple[bool, List[str], int]:
    checks: List[Tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, bool(condition)))

    with tempfile.TemporaryDirectory() as root:
        plan_dir = _fixture_plan(root)
        record = derive_record(plan_dir)
        check('derived record passes closed-field validation',
              not validate_record(record))
        check('timing span is the calendar difference (5820 s)',
              record['timing']['span_seconds'] == 5820)
        check('task_count_spanned counts distinct tasks once',
              record['timing']['task_count_spanned'] == 2)
        check('shape counts tasks/criteria/invariants/gate intents',
              (record['shape']['tasks'], record['shape']['criteria'],
               record['shape']['invariants'], record['shape']['gate_intents'],
               record['shape']['events']) == (2, 2, 1, 2, 10))
        check('friction counts adaptation+refusal and the retry after failure',
              (record['friction']['adaptations'], record['friction']['refusals'],
               record['friction']['retries']) == (1, 1, 1))
        check('gate outcomes split by exit code',
              (record['gates']['runs'], record['gates']['exit_0'],
               record['gates']['exit_nonzero']) == (3, 2, 1))
        check('evidence histogram counts trust labels',
              record['gates']['evidence_histogram'] ==
              {'observed': 3, 'imported': 0, 'asserted': 0})
        check('metered values come only from resource samples',
              record['metered'] == {'flag': True, 'tokens': 41000, 'spend_usd': 3.25})
        check('status projected from state.json',
              record['status'] == 'completed')

        # determinism: two derivations serialize byte-identically
        check('deterministic serialization (two runs, same bytes)',
              _serialize(record) == _serialize(derive_record(plan_dir)))

        # markdown renders only numbers the record carries
        markdown = render_markdown(record)
        check('markdown is a rendering of the record (span present verbatim)',
              ('Span: %d s' % record['timing']['span_seconds']) in markdown)
        check('markdown labels calendar span, never runtime',
              'calendar span' in markdown and 'runtime' not in markdown)

        # mutants against the closed field set / no-imputation rule
        mutant = json.loads(json.dumps(record))
        del mutant['metered']
        check('mutant: missing field caught', bool(validate_record(mutant)))
        mutant = json.loads(json.dumps(record))
        mutant['extra'] = 1
        check('mutant: extra field caught', bool(validate_record(mutant)))
        mutant = json.loads(json.dumps(record))
        mutant['metered']['flag'] = False  # tokens still set -> imputation
        check('mutant: unmetered record with values caught (imputation)',
              bool(validate_record(mutant)))
        mutant = json.loads(json.dumps(record))
        mutant['contract_id'] = 'zz'
        check('mutant: bad contract_id shape caught', bool(validate_record(mutant)))
        mutant = json.loads(json.dumps(record))
        mutant['diff_stats'] = {'available': False, 'files': 0,
                                'insertions': None, 'deletions': None}
        check('mutant: unavailable diff with counts caught', bool(validate_record(mutant)))

        # unmetered fixture: tokens/spend stay null, never zero
        plan_dir_unmetered = _fixture_plan(os.path.join(root, 'repo2'), 'v6')
        with open(os.path.join(plan_dir_unmetered, 'journal.ndjson'), 'w',
                  encoding='utf-8') as handle:
            for event in json.loads(json.dumps(
                    [e for e in parse_journal(plan_dir_unmetered)[0]
                     if e['type'] != 'resource_sample'])):
                handle.write(json.dumps(event) + '\n')
        unmetered = derive_record(plan_dir_unmetered)
        check('unmetered plan: flag false, tokens/spend null (no imputation)',
              unmetered['metered'] == {'flag': False, 'tokens': None,
                                       'spend_usd': None})

        # torn tail: valid prefix derives, torn count surfaced
        torn_dir = _fixture_plan(os.path.join(root, 'repo3'), 'v6')
        with open(os.path.join(torn_dir, 'journal.ndjson'), 'a', encoding='utf-8') as handle:
            handle.write('{"type": "gate_run", "ts": "2026-01-02T1')
        events, torn = parse_journal(torn_dir)
        check('torn journal tail: prefix kept, torn counted',
              torn == 1 and len(events) == 10)

        # config: precedence and fail-closed
        repo_cfg = os.path.join(root, '.dwp', 'config.json')
        with open(repo_cfg, 'w', encoding='utf-8') as handle:
            handle.write('{"benchmark": {"enabled": true}}')
        enabled, warnings = resolve_enabled(plan_dir)
        check('repo config enables benchmark', enabled and not warnings)
        with open(repo_cfg, 'w', encoding='utf-8') as handle:
            handle.write('{"benchmark": {"enabled": true}}')
        with open(repo_cfg, 'w', encoding='utf-8') as handle:
            handle.write('{not json')
        enabled, warnings = resolve_enabled(plan_dir)
        check('malformed repo config fails closed with one warning',
              not enabled and len(warnings) == 1)
        with open(repo_cfg, 'w', encoding='utf-8') as handle:
            handle.write('{"benchmark": {"enabled": "yes"}}')
        enabled, warnings = resolve_enabled(plan_dir)
        check('wrong-typed enabled fails closed', not enabled and warnings)
        os.unlink(repo_cfg)

        # v5 refusal: one line, no artifacts
        v5_dir = _fixture_plan(os.path.join(root, 'repo4'), 'v5')
        manifest_v5 = _load_json(os.path.join(v5_dir, 'manifest.json'))
        check('v5 fixture detected as non-v6 by manifest pointer',
              manifest_v5 is not None and manifest_v5.get('schema') != MANIFEST_V6_URL)

        # aggregate: grouping + the verbatim note + csv determinism
        out_dir = os.path.join(plan_dir, 'analysis_results')
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, 'benchmark.json'), 'wb') as handle:
            handle.write(_serialize(record))
        records, v5_names, skipped_names = _iter_plan_records(root)
        check('aggregate collects the emitted record', len(records) == 1)
        report = _aggregate_report(records, v5_names, skipped_names)
        check('aggregate carries the non-causality note verbatim',
              AGGREGATE_NOTE in report)
        csv_one = '\n'.join(','.join(_csv_row(row)) for row in records)
        csv_two = '\n'.join(','.join(_csv_row(row)) for row in _iter_plan_records(root)[0])
        check('aggregate CSV rows deterministic', csv_one == csv_two)

    failures = [name for name, ok_flag in checks if not ok_flag]
    return (not failures), failures, len(checks)


# ---------------------------------------------------------------------------


def main(argv: List[str]) -> int:
    usage = ('usage: benchmark.py report --plan DIR | aggregate --roots R ... '
             '[--scan DIR] [--csv FILE] [--out FILE] | self-test')
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('command')
    parser.add_argument('--plan')
    parser.add_argument('--roots', nargs='+')
    parser.add_argument('--scan')
    parser.add_argument('--csv')
    parser.add_argument('--out')
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print(usage)
        return 2
    if args.command in ('-h', '--help'):
        print(usage)
        return 0
    if args.command == 'self-test':
        ok, failures, probes = self_test()
        for failure in failures:
            print('FAIL', failure)
        print('self-test: %s (%d probes)' % ('OK' if ok else 'FAILED', probes))
        return 0 if ok else 1
    if args.command == 'report':
        if not args.plan:
            print(usage)
            return 2
        plan = ledger.find_plan_dir(args.plan)
        return cmd_report(plan)
    if args.command == 'aggregate':
        if not args.roots and not args.scan:
            print(usage)
            return 2
        return cmd_aggregate(args.roots or [], args.scan, args.csv, args.out)
    print(usage)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
