#!/usr/bin/env python3
"""v6 opt-in benchmark field metrics and learnings (spec/BENCHMARK.md).

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
    *disabled* with exactly one warning line per key. Disabled repositories
    behave byte-identically to a pack without this subsystem.
  * **Learnings ride on benchmark** (spec section 10). The nested
    ``benchmark.learnings`` flag defaults off; ``enabled: false`` forces it
    off regardless. Two halves: the **derived** half copies each friction
    event's recorded reason verbatim and regenerates deterministically; the
    **curated** half is written once — an existing ``curated`` array is
    preserved byte-for-byte by reruns, never merged or rewritten.
  * **Never blocking.** Any derivation or emission failure degrades to a
    warning and exit status 0 — emission failure is never plan failure.
    Usage errors (bad arguments) are the only exit-2 conditions.
  * **Deterministic (with the learnings split).** No emission timestamp, no
    wall clock, sorted keys; two runs over identical plan bytes produce
    identical bytes for ``benchmark.json``, the derived learnings content
    and ``DWP_REPORT.md``, while curated learnings are preserved (10.5-10.6).
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

try:
    import context_manifest  # noqa: E402  (sibling module, same directory)
except ImportError:  # pragma: no cover - executed from another cwd
    try:
        import context_manifest  # noqa: E402
    except ImportError:
        context_manifest = None  # type: ignore[assignment]

SCHEMA_URL = 'https://deepworkplan.com/schema/benchmark-record/v1.json'
LEARNINGS_URL = 'https://deepworkplan.com/schema/learnings-record/v1.json'
MANIFEST_V6_URL = 'https://deepworkplan.com/schema/plan-manifest/v6.json'

RECORD_FIELDS = ('schema', 'plan', 'title', 'generation', 'contract_id',
                 'status', 'versions', 'timing', 'shape', 'friction',
                 'gates', 'metered', 'environment', 'diff_stats',
                 'context_accounting')
RECORD_OPTIONAL_FIELDS = ('context_accounting',)

LEARNINGS_FIELDS = ('schema', 'plan', 'generation', 'contract_id',
                    'derived', 'curated')

LEARNINGS_CATEGORIES = ('spec-gap', 'instruction-gap', 'tooling-gap',
                        'docs-gap', 'gate-false-positive',
                        'gate-false-negative', 'context-miss')

# The derived learnings half copies one recorded field per friction event
# type, verbatim (spec section 10.2). Each field is required by the journal
# event schema, so a schema-valid journal always carries it; the bracketed
# fallback asserts absence and invents nothing.
_DERIVED_REASON_FIELDS = {'refusal': 'reason', 'adaptation': 'rationale',
                          'intervention': 'description'}

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


def _benchmark_section(plan_dir: str, warnings: List[str]
                       ) -> Optional[Dict[str, Any]]:
    """Resolve the winning ``benchmark`` object (repo over global), or None.

    A repository file that carries the object overrides the global file
    wholesale (both flags come from that one file); a repository file that
    omits it defers to the global file (spec section 1, per-key resolution).
    """
    dwp_root = find_dwp_root(plan_dir)
    if dwp_root is None:
        warnings.append('benchmark: plan directory has no .dwp ancestor; '
                        'benchmark disabled')
        return None
    for label, path in (
            ('.dwp/config.json', os.path.join(dwp_root, 'config.json')),
            ('~/.dwp/config.json', os.path.join(os.path.expanduser('~'),
                                                '.dwp', 'config.json'))):
        cfg, warn = _read_config(path)
        if warn:
            warnings.append('benchmark: ' + warn)
        if cfg is None or 'benchmark' not in cfg:
            continue
        section = cfg['benchmark']
        if not isinstance(section, dict):
            warnings.append('benchmark: %s "benchmark" is not an object; '
                            'benchmark disabled' % label)
            return None
        return section
    return None


def resolve_config(plan_dir: str) -> Tuple[bool, bool, List[str]]:
    """Resolve (benchmark enabled, learnings enabled, warnings).

    Fail-closed per key (spec section 1): ``enabled`` must be an explicit
    boolean in the winning section; ``learnings`` defaults false, rides on
    ``enabled``, and a wrong-typed value disables learnings only — one
    warning — while metrics resolution is unaffected.
    """
    warnings: List[str] = []
    section = _benchmark_section(plan_dir, warnings)
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


def resolve_enabled(plan_dir: str) -> Tuple[bool, List[str]]:
    """Back-compatible view of :func:`resolve_config` (metrics flag only)."""
    enabled, _learnings, warnings = resolve_config(plan_dir)
    return enabled, warnings


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


def _fmt_ts(value: Optional[datetime]) -> Optional[str]:
    return value.strftime('%Y-%m-%dT%H:%M:%SZ') if value else None


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


def _context_accounting(plan_dir: str) -> Dict[str, Any]:
    """The four-quantity context accounting block, or honest unavailability.

    Recovered through the shipped ``context_manifest`` helper (it derives
    from the same persisted records — journal, contract, manifest — and
    MEASURES the manifest bytes). Any failure degrades to
    ``available: false`` with null values — never synthesized (spec
    section 3).
    """
    empty: Dict[str, Any] = {'available': False, 'instruction_bytes': None,
                             'provider_tokens': None, 'cost_usd': None,
                             'wall_clock_hours': None}
    if context_manifest is None:
        return empty
    try:
        acct = context_manifest.accounting(plan_dir)
    except Exception:  # noqa: BLE001 — degradation, never a crash
        return empty
    if not isinstance(acct, dict):
        return empty

    def _num(value: Any) -> Optional[float]:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return value

    try:
        measured = acct.get('instruction_bytes')
        bytes_map = measured.get('bytes') if isinstance(measured, dict) else None
        total = (sum(v for v in bytes_map.values() if isinstance(v, int))
                 if isinstance(bytes_map, dict) else None)
        if not isinstance(total, int):
            return empty  # a recovered block always measures its bytes
        tokens = acct.get('provider_tokens')
        spend = acct.get('cost_usd')
        wall = acct.get('wall_clock_hours')
        return {
            'available': True,
            'instruction_bytes': total,
            'provider_tokens': _num(tokens.get('value')) if isinstance(tokens, dict) else None,
            'cost_usd': _num(spend.get('value')) if isinstance(spend, dict) else None,
            'wall_clock_hours': _num(wall.get('value')) if isinstance(wall, dict) else None,
        }
    except Exception:  # noqa: BLE001 — degradation, never a crash
        return empty


# ---------------------------------------------------------------------------
# derivation (spec sections 3-4)


def _task_spans(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Per-task calendar spans, one entry per distinct ``task_start``.

    A start's completion evidence is the first exit-0 ``gate_run`` bound to
    the same task after that start and before the task's next start. No
    evidence in the window -> ``end_ts``/``span_seconds`` null — never zero
    (spec section 3). Order: first-start appearance (deterministic).
    """
    starts_by_task: Dict[str, List[Dict[str, Any]]] = {}
    order: List[str] = []
    passes_by_task: Dict[str, List[Dict[str, Any]]] = {}
    for event in events:
        kind = event.get('type')
        if kind == 'task_start':
            task = str(event.get('task') or '')
            if task and task not in starts_by_task:
                order.append(task)
            starts_by_task.setdefault(task, []).append(event)
        elif kind == 'gate_run' and event.get('exit_code') == 0:
            passes_by_task.setdefault(str(event.get('task') or ''), []).append(event)
    spans: List[Dict[str, Any]] = []
    for task in order:
        starts = starts_by_task.get(task, [])
        passes = passes_by_task.get(task, [])
        for index, start in enumerate(starts):
            start_ts = _parse_ts(str(start.get('ts')))
            next_start_seq = (starts[index + 1].get('seq')
                              if index + 1 < len(starts) else None)
            end_ts = None
            for gate in passes:
                gate_seq = gate.get('seq')
                after_start = (gate_seq is not None and start.get('seq') is not None
                               and gate_seq > start.get('seq'))
                before_next = (next_start_seq is None
                               or gate_seq is None or gate_seq < next_start_seq)
                if after_start and before_next:
                    end_ts = _parse_ts(str(gate.get('ts')))
                    break
            span = (int((end_ts - start_ts).total_seconds())
                    if start_ts and end_ts and end_ts >= start_ts else None)
            spans.append({'task': task, 'start_ts': _fmt_ts(start_ts),
                          'end_ts': _fmt_ts(end_ts), 'span_seconds': span})
    return spans


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
    task_spans = _task_spans(events)

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

    timing: Dict[str, Any] = {
        'first_event_ts': _fmt_ts(first_ts),
        'last_event_ts': _fmt_ts(last_ts),
        'span_seconds': span,
        'task_count_spanned': len(spanned_tasks),
    }
    if task_spans:
        timing['task_spans'] = task_spans

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
        'timing': timing,
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
        'context_accounting': _context_accounting(plan_dir),
    }


# ---------------------------------------------------------------------------
# learnings derivation (spec section 10)


def _derived_reason(event: Dict[str, Any]) -> str:
    """The event's recorded reason, verbatim — never paraphrased.

    One recorded field per event type (each required by the journal event
    schema); a failing ``gate_run`` carries its recorded exit outcome. The
    bracketed fallback asserts absence and invents nothing.
    """
    kind = str(event.get('type'))
    if kind == 'gate_run':
        return 'exit_code=%s' % event.get('exit_code')
    field = _DERIVED_REASON_FIELDS.get(kind, 'reason')
    text = str(event.get(field) or '').strip()
    return text if text else '(no recorded %s)' % field


def derive_learnings(contract: Dict[str, Any],
                     events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Derive the learnings record's identity + derived half (spec 10.2).

    The curated half is NOT derived — it is written once at file creation
    and preserved afterwards; callers assemble it separately.
    """
    plan_name = contract.get('plan') or ''
    derived: List[Dict[str, Any]] = []
    for event in events:
        kind = event.get('type')
        if kind in ('adaptation', 'intervention', 'refusal'):
            derived.append({'seq': int(event.get('seq') or 0),
                            'event_type': str(kind),
                            'reason': _derived_reason(event)})
        elif kind == 'gate_run' and event.get('exit_code') != 0:
            derived.append({'seq': int(event.get('seq') or 0),
                            'event_type': 'gate_run',
                            'reason': _derived_reason(event)})
    return {
        'schema': LEARNINGS_URL,
        'plan': plan_name,
        'generation': 'v6',
        'contract_id': str(contract.get('contract_id') or ''),
        'derived': derived,
    }


# ---------------------------------------------------------------------------
# record validation (runtime half; the jsonschema half is the fixtures')


def validate_record(record: Any) -> List[str]:
    """Closed-field structural check mirroring the published schema."""
    problems: List[str] = []
    if not isinstance(record, dict):
        return ['record is not a JSON object']
    extra = sorted(set(record) - set(RECORD_FIELDS))
    missing = sorted(set(RECORD_FIELDS) - set(record) - set(RECORD_OPTIONAL_FIELDS))
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
    timing = record['timing']
    spans = timing.get('task_spans')
    if spans is not None:
        if not isinstance(spans, list):
            problems.append('timing.task_spans is not an array')
        else:
            for item in spans:
                if not isinstance(item, dict):
                    problems.append('task span entry is not an object')
                    continue
                if sorted(item) != ['end_ts', 'span_seconds', 'start_ts', 'task']:
                    problems.append('task span entry fields')
                    continue
                if not re.match(r'^T-[a-z0-9]+(-[a-z0-9]+)*$',
                                str(item.get('task') or '')):
                    problems.append('task span task id grammar')
                if (item.get('end_ts') is None) != (item.get('span_seconds') is None):
                    problems.append('task span end/span presence mismatch '
                                    '(span null exactly when end null)')
                elif item.get('span_seconds') is not None:
                    if not isinstance(item['span_seconds'], int) or item['span_seconds'] < 0:
                        problems.append('task span seconds shape')
    accounting = record.get('context_accounting')
    if accounting is not None:
        if not isinstance(accounting, dict):
            problems.append('context_accounting is not an object')
        elif sorted(accounting) != ['available', 'cost_usd', 'instruction_bytes',
                                    'provider_tokens', 'wall_clock_hours']:
            problems.append('context_accounting fields')
        else:
            if not isinstance(accounting.get('available'), bool):
                problems.append('context_accounting.available is not a boolean')
            if not accounting.get('available') and any(
                    accounting.get(k) is not None
                    for k in ('instruction_bytes', 'provider_tokens',
                              'cost_usd', 'wall_clock_hours')):
                problems.append('unavailable context_accounting carries values '
                                '(imputation)')
            if accounting.get('available') and not isinstance(
                    accounting.get('instruction_bytes'), int):
                problems.append('available context_accounting lacks measured '
                                'instruction bytes')
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


def validate_learnings(record: Any) -> List[str]:
    """Closed-field structural check mirroring the learnings schema."""
    problems: List[str] = []
    if not isinstance(record, dict):
        return ['learnings record is not a JSON object']
    extra = sorted(set(record) - set(LEARNINGS_FIELDS))
    missing = sorted(set(LEARNINGS_FIELDS) - set(record))
    if extra:
        problems.append('extra field(s): %s' % ', '.join(extra))
    if missing:
        problems.append('missing field(s): %s' % ', '.join(missing))
    if record.get('schema') != LEARNINGS_URL:
        problems.append('schema const mismatch')
    if not re.match(r'^PLAN_([0-9]{3,}_)?[a-z0-9]+(_[a-z0-9]+){1,4}$',
                    str(record.get('plan') or '')):
        problems.append('plan name grammar')
    if record.get('generation') != 'v6':
        problems.append('generation must be v6')
    if not re.match(r'^[0-9a-f]{64}$', str(record.get('contract_id') or '')):
        problems.append('contract_id shape')
    for half in ('derived', 'curated'):
        if not isinstance(record.get(half), list):
            problems.append('%s is not an array' % half)
    if problems:
        return problems
    for entry in record['derived']:
        if not isinstance(entry, dict):
            problems.append('derived entry is not an object')
            continue
        if sorted(entry) != ['event_type', 'reason', 'seq']:
            problems.append('derived entry fields')
            continue
        if not isinstance(entry.get('seq'), int) or entry.get('seq', 0) < 1:
            problems.append('derived entry seq shape')
        if entry.get('event_type') not in ('adaptation', 'intervention',
                                           'refusal', 'gate_run'):
            problems.append('derived entry event_type enum')
        if not isinstance(entry.get('reason'), str) or not entry.get('reason'):
            problems.append('derived entry reason must be non-empty text')
    for entry in record['curated']:
        if not isinstance(entry, dict):
            problems.append('curated entry is not an object')
            continue
        if sorted(entry) != ['anchor', 'category', 'finding', 'id', 'proposal']:
            problems.append('curated entry fields')
            continue
        if not re.match(r'^LRN-[0-9]{3}$', str(entry.get('id') or '')):
            problems.append('curated entry id grammar (LRN-nnn)')
        if entry.get('category') not in LEARNINGS_CATEGORIES:
            problems.append('curated entry category not in the closed vocabulary')
        anchor = entry.get('anchor')
        if anchor is not None:
            if not isinstance(anchor, dict):
                problems.append('curated anchor is not an object or null')
            else:
                if sorted(anchor) not in (['seq'], ['section'], ['section', 'seq']):
                    problems.append('curated anchor fields (seq and/or section, '
                                    'at least one)')
                else:
                    if 'seq' in anchor and (not isinstance(anchor['seq'], int)
                                            or anchor['seq'] < 1):
                        problems.append('curated anchor seq shape')
                    if 'section' in anchor and (not isinstance(anchor['section'], str)
                                                or not anchor['section']
                                                or len(anchor['section']) > 64
                                                or '/' in anchor['section']):
                        problems.append('curated anchor section shape (<=64 chars, '
                                        'no paths)')
        for text_key in ('finding', 'proposal'):
            if not isinstance(entry.get(text_key), str) or not entry.get(text_key):
                problems.append('curated entry %s must be non-empty text' % text_key)
    return problems


# ---------------------------------------------------------------------------
# rendering (DWP_REPORT.md is a render of the JSON records, never a source)


def render_markdown(record: Dict[str, Any],
                    learnings: Optional[Dict[str, Any]] = None) -> str:
    """Human report rendered from the records - never a second source."""
    timing = record['timing']
    shape = record['shape']
    friction = record['friction']
    gates = record['gates']
    metered = record['metered']
    env = record['environment']
    diff = record['diff_stats']
    lines = [
        '# DWP report — %s' % record['title'],
        '',
        'Opt-in field record derived from this plan\'s own records '
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
    ]
    task_spans = timing.get('task_spans')
    if task_spans:
        lines += [
            '## Per-task spans (calendar)',
            '',
            '| Task | Start | End | Span (s) |',
            '|---|---|---|---|',
        ]
        for item in task_spans:
            lines.append('| %s | %s | %s | %s |' % (
                item['task'], item['start_ts'],
                item['end_ts'] if item['end_ts'] is not None else 'null',
                item['span_seconds'] if item['span_seconds'] is not None else 'null'))
        lines.append('')
    lines += [
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
    accounting = record.get('context_accounting')
    if accounting is not None:
        lines += [
            '',
            '## Context accounting',
            '',
        ]
        if accounting.get('available'):
            lines.append('- Instruction bytes (measured): %s' % accounting['instruction_bytes'])
            lines.append('- Provider tokens: %s · cost (USD): %s' % (
                accounting['provider_tokens'] if accounting['provider_tokens'] is not None else 'null',
                accounting['cost_usd'] if accounting['cost_usd'] is not None else 'null'))
            lines.append('- Wall-clock (hours, recorded span): %s' % (
                accounting['wall_clock_hours'] if accounting['wall_clock_hours'] is not None else 'null'))
        else:
            lines.append('- Context accounting unavailable (values null, never '
                         'synthesized).')
    if learnings is not None:
        lines += [
            '',
            '## Friction explained (derived)',
            '',
        ]
        if learnings['derived']:
            for entry in learnings['derived']:
                lines.append('- seq %d · %s · %s' % (
                    entry['seq'], entry['event_type'], entry['reason']))
        else:
            lines.append('- No friction events recorded.')
        lines += [
            '',
            '## Learnings (curated)',
            '',
        ]
        if learnings['curated']:
            lines += [
                '| Id | Category | Anchor | Finding | Proposal |',
                '|---|---|---|---|---|',
            ]
            for entry in learnings['curated']:
                anchor = entry['anchor']
                if anchor is None:
                    anchor_text = 'unanchored'
                elif 'seq' in anchor and 'section' in anchor:
                    anchor_text = 'seq %d / %s' % (anchor['seq'], anchor['section'])
                elif 'seq' in anchor:
                    anchor_text = 'seq %d' % anchor['seq']
                else:
                    anchor_text = anchor['section']
                lines.append('| %s | %s | %s | %s | %s |' % (
                    entry['id'], entry['category'], anchor_text,
                    entry['finding'].replace('|', '\\|'),
                    entry['proposal'].replace('|', '\\|')))
        else:
            lines.append('- No curated entries yet.')
    lines += [
        '',
        '---',
        '',
        'Rendered from benchmark.json%s — a rendering, never a second '
        'source. Aggregates over such records describe recorded executions; '
        'they are evidence for discussion, not a causal comparison.' % (
            ' and learnings.json' if learnings is not None else ''),
        '',
    ]
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
# learnings emission (written-once curated half — spec sections 10.5-10.6)


def _extract_top_level_array(raw: str, key: str) -> Optional[str]:
    """Return the raw text of a top-level ``"key": [ ... ]`` array, or None.

    A conservative scanner: strings and escapes are honored, bracket depth
    is matched, and any surprise returns None (the caller then refuses to
    rewrite rather than risk damaging curated content).
    """
    index = 0
    total = len(raw)
    depth = 0
    while index < total:
        char = raw[index]
        if char == '"':
            end = raw.find('"', index + 1)
            while end != -1 and raw[end - 1] == '\\':
                end = raw.find('"', end + 1)
            if end == -1:
                return None
            if depth == 1 and raw[index + 1:end] == key:
                cursor = end + 1
                while cursor < total and raw[cursor] in ' \t\r\n':
                    cursor += 1
                if cursor >= total or raw[cursor] != ':':
                    return None
                cursor += 1
                while cursor < total and raw[cursor] in ' \t\r\n':
                    cursor += 1
                if cursor >= total or raw[cursor] != '[':
                    return None
                bracket = 0
                in_string = False
                escaped = False
                start = cursor
                while cursor < total:
                    char = raw[cursor]
                    if in_string:
                        if escaped:
                            escaped = False
                        elif char == '\\':
                            escaped = True
                        elif char == '"':
                            in_string = False
                    elif char == '"':
                        in_string = True
                    elif char == '[':
                        bracket += 1
                    elif char == ']':
                        bracket -= 1
                        if bracket == 0:
                            return raw[start:cursor + 1]
                    cursor += 1
                return None
            index = end + 1
            continue
        if char in '{[':
            depth += 1
        elif char in '}]':
            depth -= 1
        index += 1
    return None


def _learnings_payload(plan_dir: str, derived_doc: Dict[str, Any]
                       ) -> Tuple[Optional[bytes], bool]:
    """Assemble the learnings file bytes honoring written-once semantics.

    Returns (payload-or-None, first_creation). When the file already
    exists, its ``curated`` array text is spliced verbatim into the freshly
    serialized document — preserved byte-for-byte, never merged, rewritten
    or normalized (spec 10.5). Any surprise (unreadable, unparseable,
    unscannable) returns None and the caller leaves the file untouched.
    """
    path = os.path.join(plan_dir, 'analysis_results', 'learnings.json')
    if not os.path.isfile(path):
        draft = dict(derived_doc)
        draft['curated'] = []
        return _serialize(draft), True
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            raw = handle.read()
        existing = json.loads(raw)
    except (OSError, ValueError) as exc:
        print('benchmark: existing learnings.json unreadable (%s); left '
              'untouched' % exc)
        return None, False
    if not isinstance(existing, dict):
        print('benchmark: existing learnings.json is not a JSON object; left '
              'untouched')
        return None, False
    curated_raw = _extract_top_level_array(raw, 'curated')
    if curated_raw is None:
        print('benchmark: curated entries in learnings.json could not be '
              'located verbatim; file left untouched')
        return None, False
    draft = dict(derived_doc)
    draft['curated'] = []  # the raw slice is spliced in below, never re-serialized
    payload = _serialize(draft)
    needle = b'"curated": []'
    if needle not in payload:
        print('benchmark: curated splice point missing; learnings.json left '
              'untouched')
        return None, False
    payload = payload.replace(
        needle, b'"curated": ' + curated_raw.encode('utf-8'), 1)
    try:
        json.loads(payload.decode('utf-8'))
    except ValueError:
        print('benchmark: curated splice produced invalid JSON; learnings.json '
              'left untouched')
        return None, False
    return payload, False


# ---------------------------------------------------------------------------
# commands


def cmd_report(plan_dir: str) -> int:
    enabled, learnings_on, warnings = resolve_config(plan_dir)
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
        learnings_record: Optional[Dict[str, Any]] = None
        if learnings_on:
            events, _torn = parse_journal(plan_dir)
            contract = _load_json(os.path.join(plan_dir, 'contract.json'))
            if isinstance(contract, dict):
                derived_doc = derive_learnings(contract, events)
                if not validate_learnings(dict(derived_doc, curated=[])):
                    learnings_payload, first = _learnings_payload(plan_dir, derived_doc)
                    if learnings_payload is not None:
                        _atomic_write(os.path.join(plan_dir, 'analysis_results',
                                                   'learnings.json'),
                                      learnings_payload)
                        if first:
                            print('benchmark: learnings record created -> '
                                  'analysis_results/learnings.json (curated '
                                  'entries are the completing agent\'s to '
                                  'author: category, anchor, finding, proposal '
                                  '— spec section 10)')
                        else:
                            print('benchmark: learnings derived half refreshed '
                                  '(%d entries); curated preserved byte-for-byte'
                                  % len(derived_doc['derived']))
                        learnings_record = json.loads(
                            learnings_payload.decode('utf-8'))
                else:
                    print('benchmark: derived learnings half failed validation; '
                          'learnings emission skipped')
        _atomic_write(os.path.join(plan_dir, 'analysis_results', 'DWP_REPORT.md'),
                      render_markdown(record, learnings_record).encode('utf-8'))
    except Exception as exc:  # noqa: BLE001 — emission failure never blocks the plan
        print('benchmark: emission skipped after derivation failure (%s); '
              'plan completion is unaffected' % exc)
        return 0
    print('benchmark: record emitted (%d tasks, %d events, calendar span %d s) '
          '-> analysis_results/benchmark.json + DWP_REPORT.md'
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
        {'type': 'adaptation', 'ts': '2026-01-02T10:25:00Z', 'seq': 4,
         'kind': 'retry', 'rationale': 'first gate run failed; rerun after fix'},
        {'type': 'gate_run', 'ts': '2026-01-02T10:40:00Z', 'seq': 5, 'task': 'T-one',
         'criterion': 'AC-one', 'exit_code': 0, 'trust': 'observed'},
        {'type': 'task_start', 'ts': '2026-01-02T11:00:00Z', 'seq': 6, 'task': 'T-two',
         'fingerprint': {'revision': '1' * 40, 'dirty': ''}},
        {'type': 'gate_run', 'ts': '2026-01-02T11:30:00Z', 'seq': 7, 'task': 'T-two',
         'criterion': 'AC-two', 'exit_code': 0, 'trust': 'observed'},
        {'type': 'refusal', 'ts': '2026-01-02T11:35:00Z', 'seq': 8,
         'subject': 'ledger', 'stage': 'complete',
         'reason': 'criteria lacked in-window evidence'},
        {'type': 'resource_sample', 'ts': '2026-01-02T11:36:00Z', 'seq': 9,
         'limit_id': 'spend_usd', 'value': 3.25, 'unit': 'USD'},
        {'type': 'resource_sample', 'ts': '2026-01-02T11:37:00Z', 'seq': 10,
         'limit_id': 'tokens', 'value': 41000, 'unit': 'tokens'},
    ]
    with open(os.path.join(plan_dir, 'journal.ndjson'), 'w', encoding='utf-8') as handle:
        for event in events:
            handle.write(json.dumps(event) + '\n')
    return plan_dir


def _rewrite_journal(plan_dir: str, events: List[Dict[str, Any]]) -> None:
    with open(os.path.join(plan_dir, 'journal.ndjson'), 'w', encoding='utf-8') as handle:
        for event in events:
            handle.write(json.dumps(event) + '\n')


def self_test() -> Tuple[bool, List[str], int]:
    checks: List[Tuple[str, bool]] = []

    def check(name: str, condition: bool) -> None:
        checks.append((name, bool(condition)))

    with tempfile.TemporaryDirectory() as root:
        # sandbox HOME so config precedence probes are host-independent
        home_sandbox = os.path.join(root, 'home')
        os.makedirs(home_sandbox, exist_ok=True)
        previous_home = os.environ.get('HOME')
        os.environ['HOME'] = home_sandbox
        try:
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

            # per-task spans (calendar, completion evidence = passing gate)
            spans = record['timing'].get('task_spans')
            check('task spans: one entry per start with evidence-backed ends',
                  spans == [
                      {'task': 'T-one', 'start_ts': '2026-01-02T10:05:00Z',
                       'end_ts': '2026-01-02T10:40:00Z', 'span_seconds': 2100},
                      {'task': 'T-two', 'start_ts': '2026-01-02T11:00:00Z',
                       'end_ts': '2026-01-02T11:30:00Z', 'span_seconds': 1800}])
            no_evidence_dir = _fixture_plan(os.path.join(root, 'repo_ne'), 'v6')
            events_ne = [event for event in parse_journal(no_evidence_dir)[0]
                         if not (event.get('type') == 'gate_run'
                                 and event.get('task') == 'T-two')]
            _rewrite_journal(no_evidence_dir, events_ne)
            spans_ne = derive_record(no_evidence_dir)['timing'].get('task_spans')
            check('task spans: absent evidence means null end and null span, '
                  'never zero',
                  spans_ne is not None and spans_ne[1]['end_ts'] is None
                  and spans_ne[1]['span_seconds'] is None
                  and spans_ne[0]['span_seconds'] == 2100)
            no_start_dir = _fixture_plan(os.path.join(root, 'repo_ns'), 'v6')
            events_ns = [event for event in parse_journal(no_start_dir)[0]
                         if event.get('type') != 'task_start']
            _rewrite_journal(no_start_dir, events_ns)
            check('task spans: omitted when the journal records no task_start',
                  'task_spans' not in derive_record(no_start_dir)['timing'])

            # context accounting: recovered or honestly unavailable
            accounting = record.get('context_accounting')
            check('context accounting: block present and well-formed',
                  isinstance(accounting, dict)
                  and isinstance(accounting.get('available'), bool))
            if accounting and accounting.get('available'):
                check('context accounting: measured bytes, meters never imputed',
                      isinstance(accounting['instruction_bytes'], int)
                      and accounting['instruction_bytes'] > 0
                      and accounting['provider_tokens'] is None
                      and accounting['cost_usd'] is None
                      and abs(accounting['wall_clock_hours'] - 5820 / 3600) < 0.01)
            else:
                check('context accounting: degradation carries null values only',
                      all(accounting.get(k) is None for k in
                          ('instruction_bytes', 'provider_tokens',
                           'cost_usd', 'wall_clock_hours')))
            check('context accounting: deterministic across derivations',
                  _context_accounting(plan_dir) == _context_accounting(plan_dir))

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
            mutant = json.loads(json.dumps(record))
            mutant['timing']['task_spans'][1]['end_ts'] = None  # span stays numeric
            check('mutant: task span end/span presence mismatch caught',
                  bool(validate_record(mutant)))
            mutant = json.loads(json.dumps(record))
            mutant['context_accounting'] = {'available': False,
                                            'instruction_bytes': 12,
                                            'provider_tokens': None,
                                            'cost_usd': None,
                                            'wall_clock_hours': None}
            check('mutant: unavailable context accounting with values caught',
                  bool(validate_record(mutant)))

            # learnings derived half: verbatim reasons in seq order
            events = parse_journal(plan_dir)[0]
            contract = _load_json(os.path.join(plan_dir, 'contract.json'))
            derived_doc = derive_learnings(contract, events)
            check('learnings derived: friction explained in seq order with '
                  'verbatim reasons',
                  derived_doc['derived'] == [
                      {'seq': 3, 'event_type': 'gate_run',
                       'reason': 'exit_code=1'},
                      {'seq': 4, 'event_type': 'adaptation',
                       'reason': 'first gate run failed; rerun after fix'},
                      {'seq': 8, 'event_type': 'refusal',
                       'reason': 'criteria lacked in-window evidence'}])
            check('learnings derived: identity comes from the contract',
                  (derived_doc['plan'], derived_doc['contract_id'])
                  == ('PLAN_001_self_test_probe', 'a' * 64))
            check('learnings: validate_learnings accepts the derived doc',
                  not validate_learnings(dict(derived_doc, curated=[])))

            # learnings mutants (closed vocabulary, anchor grammar, ids)
            bad_learnings = json.loads(json.dumps(dict(derived_doc, curated=[
                {'id': 'LRN-001', 'category': 'performance-gap',
                 'anchor': {'seq': 3}, 'finding': 'f', 'proposal': 'p'}])))
            check('learnings mutant: category outside the closed vocabulary caught',
                  bool(validate_learnings(bad_learnings)))
            bad_learnings['curated'][0]['category'] = 'spec-gap'
            bad_learnings['curated'][0]['id'] = 'lrn-1'
            check('learnings mutant: malformed id caught',
                  bool(validate_learnings(bad_learnings)))
            bad_learnings['curated'][0]['id'] = 'LRN-001'
            bad_learnings['curated'][0]['anchor'] = {}
            check('learnings mutant: anchor without seq or section caught',
                  bool(validate_learnings(bad_learnings)))
            bad_learnings['curated'][0]['anchor'] = {'section': 'a/b'}
            check('learnings mutant: anchor section with a path caught',
                  bool(validate_learnings(bad_learnings)))
            bad_learnings['curated'][0]['anchor'] = None
            bad_learnings['derived'][0]['reason'] = ''
            check('learnings mutant: empty derived reason caught',
                  bool(validate_learnings(bad_learnings)))

            # config: nested learnings key, per-key fail-closed matrix
            repo_cfg = os.path.join(root, '.dwp', 'config.json')
            with open(repo_cfg, 'w', encoding='utf-8') as handle:
                handle.write('{"benchmark": {"enabled": true}}')
            enabled_flag, learnings_flag, warns = resolve_config(plan_dir)
            check('nested config: enabled without learnings -> metrics only',
                  (enabled_flag, learnings_flag, warns) == (True, False, []))
            with open(repo_cfg, 'w', encoding='utf-8') as handle:
                handle.write('{"benchmark": {"enabled": true, "learnings": true}}')
            enabled_flag, learnings_flag, warns = resolve_config(plan_dir)
            check('nested config: enabled+learnings -> both on',
                  (enabled_flag, learnings_flag, warns) == (True, True, []))
            with open(repo_cfg, 'w', encoding='utf-8') as handle:
                handle.write('{"benchmark": {"enabled": true, "learnings": "yes"}}')
            enabled_flag, learnings_flag, warns = resolve_config(plan_dir)
            check('nested config: wrong-typed learnings disables learnings only '
                  '(one warning, metrics unaffected)',
                  (enabled_flag, learnings_flag) == (True, False)
                  and len(warns) == 1 and 'learnings' in warns[0])
            with open(repo_cfg, 'w', encoding='utf-8') as handle:
                handle.write('{"benchmark": {"enabled": false, "learnings": true}}')
            enabled_flag, learnings_flag, warns = resolve_config(plan_dir)
            check('nested config: enabled false forces learnings off',
                  (enabled_flag, learnings_flag, warns) == (False, False, []))
            with open(repo_cfg, 'w', encoding='utf-8') as handle:
                handle.write('{not json')
            enabled_flag, learnings_flag, warns = resolve_config(plan_dir)
            check('malformed repo config fails closed with one warning',
                  (enabled_flag, learnings_flag) == (False, False)
                  and len(warns) == 1)
            with open(repo_cfg, 'w', encoding='utf-8') as handle:
                handle.write('{"benchmark": {"enabled": "yes"}}')
            enabled_flag, learnings_flag, warns = resolve_config(plan_dir)
            check('wrong-typed enabled fails closed',
                  (enabled_flag, learnings_flag) == (False, False) and bool(warns))
            os.unlink(repo_cfg)

            # emission: metrics-only repository writes no learnings artifact
            with open(repo_cfg, 'w', encoding='utf-8') as handle:
                handle.write('{"benchmark": {"enabled": true}}')
            check('emission (metrics only): exit 0 and no learnings.json',
                  cmd_report(plan_dir) == 0
                  and not os.path.exists(os.path.join(
                      plan_dir, 'analysis_results', 'learnings.json')))
            check('emission (metrics only): DWP_REPORT.md is the render target',
                  os.path.isfile(os.path.join(plan_dir, 'analysis_results',
                                             'DWP_REPORT.md')))

            # emission with learnings: template creation + invitation semantics
            with open(repo_cfg, 'w', encoding='utf-8') as handle:
                handle.write('{"benchmark": {"enabled": true, "learnings": true}}')
            check('emission (learnings on): exit 0',
                  cmd_report(plan_dir) == 0)
            learnings_path = os.path.join(plan_dir, 'analysis_results',
                                          'learnings.json')
            emitted = _load_json(learnings_path)
            check('learnings file: template with derived populated and '
                  'curated empty',
                  isinstance(emitted, dict)
                  and emitted.get('curated') == []
                  and len(emitted.get('derived') or []) == 3)

            # written-once: curated survives a rerun byte-for-byte while the
            # derived half refreshes from a grown journal
            curated_entry = {'id': 'LRN-001', 'category': 'instruction-gap',
                             'anchor': {'seq': 3, 'section': 'Validation'},
                             'finding': 'gate intent wording ambiguous',
                             'proposal': 'state the exact command in the task'}
            edited = json.loads(open(learnings_path, encoding='utf-8').read())
            edited['curated'] = [curated_entry]
            with open(learnings_path, 'w', encoding='utf-8') as handle:
                json.dump(edited, handle, indent=4)  # non-canonical hand format
            curated_raw_before = _extract_top_level_array(
                open(learnings_path, encoding='utf-8').read(), 'curated')
            grown = parse_journal(plan_dir)[0] + [
                {'type': 'refusal', 'ts': '2026-01-02T12:00:00Z', 'seq': 11,
                 'subject': 'scheduler', 'stage': 'dispatch',
                 'reason': 'invariant evaluated before task start'}]
            _rewrite_journal(plan_dir, grown)
            check('learnings rerun: exit 0 after journal growth',
                  cmd_report(plan_dir) == 0)
            after = open(learnings_path, encoding='utf-8').read()
            check('written-once: curated array preserved byte-for-byte',
                  _extract_top_level_array(after, 'curated') == curated_raw_before)
            refreshed = _load_json(learnings_path)
            check('written-once: derived half refreshed from the grown journal',
                  len(refreshed['derived']) == 4
                  and refreshed['derived'][-1]['seq'] == 11)
            report_after = open(os.path.join(plan_dir, 'analysis_results',
                                             'DWP_REPORT.md'),
                                encoding='utf-8').read()
            check('render: curated entry and anchors render from the JSON only',
                  'LRN-001' in report_after
                  and 'instruction-gap' in report_after
                  and 'seq 3 / Validation' in report_after)
            check('render: derived friction reasons render verbatim',
                  'invariant evaluated before task start' in report_after)

            # determinism with curated present: a rerun rewrites identical bytes
            first_json = open(os.path.join(plan_dir, 'analysis_results',
                                           'benchmark.json'), 'rb').read()
            first_report = open(os.path.join(plan_dir, 'analysis_results',
                                             'DWP_REPORT.md'), 'rb').read()
            first_learnings = open(learnings_path, 'rb').read()
            cmd_report(plan_dir)
            check('determinism: rerun rewrites byte-identical artifacts '
                  '(record, report, learnings)',
                  first_json == open(os.path.join(plan_dir, 'analysis_results',
                                                  'benchmark.json'), 'rb').read()
                  and first_report == open(os.path.join(plan_dir, 'analysis_results',
                                                        'DWP_REPORT.md'), 'rb').read()
                  and first_learnings == open(learnings_path, 'rb').read())

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

            # v5 refusal: one line, no artifacts
            v5_dir = _fixture_plan(os.path.join(root, 'repo4'), 'v5')
            manifest_v5 = _load_json(os.path.join(v5_dir, 'manifest.json'))
            check('v5 fixture detected as non-v6 by manifest pointer',
                  manifest_v5 is not None and manifest_v5.get('schema') != MANIFEST_V6_URL)

            # aggregate: grouping + the verbatim note + csv determinism
            out_dir = os.path.join(plan_dir, 'analysis_results')
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, 'benchmark.json'), 'wb') as handle:
                handle.write(_serialize(derive_record(plan_dir)))
            records, v5_names, skipped_names = _iter_plan_records(root)
            check('aggregate collects the emitted record', len(records) == 1)
            report = _aggregate_report(records, v5_names, skipped_names)
            check('aggregate carries the non-causality note verbatim',
                  AGGREGATE_NOTE in report)
            csv_one = '\n'.join(','.join(_csv_row(row)) for row in records)
            csv_two = '\n'.join(','.join(_csv_row(row)) for row in _iter_plan_records(root)[0])
            check('aggregate CSV rows deterministic', csv_one == csv_two)
        finally:
            if previous_home is None:
                del os.environ['HOME']
            else:
                os.environ['HOME'] = previous_home

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
