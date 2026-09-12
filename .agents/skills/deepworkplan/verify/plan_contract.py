#!/usr/bin/env python3
"""Offline plan invariants; read-only, Python standard library only.

Two eras share this one implementation (DWP_SPECIFICATION.md §6.5):

  * current — state.json declares the v2 schema. The full v4 contract applies:
    typed locators, gate evidence, README/state correspondence, Lite or Full.
  * legacy  — a v1 state layer or none at all. Plans authored before 2.4.0 are
    ACCEPTED against the shape they were written under (single Final Review for
    2.3.0+, the three-task ending before it), exactly as the shell checker did.

Shape validation implements only the vocabulary used by the shipped schemas; it
is not a general JSON Schema implementation. Contributor tests cross-check its
decisions with jsonschema.

Output contract: one finding per line on stdout, prefixed by outcome —
'+ ' passed (MUST holds), '~ ' advisory (SHOULD), anything else failed (MUST).
Exit 1 iff a failure was printed, so advisories never turn a plan red. The
caller renders the prefixes; keeping the granular lines here is deliberate:
`verify` reports what it checked, not just what broke.
"""
import json
from pathlib import Path
import re
import sys

# The newest DWP spec this checker implements; keep in sync with conformance.sh
# SUPPORTED_SPEC and DWP_SPECIFICATION.md "Version".
SUPPORTED_SPEC = '4.0.0'
# The standard's released series: 2.x is historical (plans authored before the
# 4.x jump stay valid, §6.5), 4.x is current. There is no 3.x standard — the
# v3 launch was a product release, not a standard bump.
SPEC_SERIES = (2, 4)
STATE_V2 = 'https://deepworkplan.com/schema/plan-state/v2.json'
MANIFEST_V2 = 'https://deepworkplan.com/schema/plan-manifest/v2.json'
STATUSES = ('pending', 'in_progress', 'completed', 'blocked', 'skipped')


def version(text):
    """Dotted numeric version as a comparable tuple; () when unparseable."""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)$', str(text or ''))
    return tuple(int(g) for g in match.groups()) if match else ()


def shape_errors(value, rule, schema, path='$'):
    if '$ref' in rule:
        target = schema
        for key in rule['$ref'].removeprefix('#/').split('/'):
            target = target[key]
        return shape_errors(value, target, schema, path)
    errors = []
    types = {'object': dict, 'array': list, 'string': str, 'integer': int,
             'boolean': bool, 'null': type(None)}
    expected = rule.get('type')
    if expected:
        expected = expected if isinstance(expected, list) else [expected]
        if not any(type(value) is types[t] for t in expected):
            return [f'{path}: expected {expected}']
    if 'const' in rule and value != rule['const']:
        errors.append(f'{path}: expected {rule["const"]!r}')
    if 'enum' in rule and value not in rule['enum']:
        errors.append(f'{path}: unknown value {value!r}')
    if isinstance(value, dict):
        for key in rule.get('required', []):
            if key not in value:
                errors.append(f'{path}: missing {key}')
        properties = rule.get('properties', {})
        for key, item in value.items():
            if key in properties:
                errors.extend(shape_errors(item, properties[key], schema, path+'.'+key))
            elif rule.get('additionalProperties') is False:
                errors.append(f'{path}: unexpected field {key}')
    if isinstance(value, list):
        if len(value) < rule.get('minItems', 0):
            errors.append(f'{path}: too few entries')
        for i, item in enumerate(value):
            errors.extend(shape_errors(item, rule.get('items', {}), schema, f'{path}[{i}]'))
    if isinstance(value, str):
        if 'pattern' in rule and not re.search(rule['pattern'], value):
            errors.append(f'{path}: invalid value {value!r}')
        if len(value) > rule.get('maxLength', len(value)):
            errors.append(f'{path}: exceeds maximum length')
    if type(value) is int and value < rule.get('minimum', value):
        errors.append(f'{path}: below minimum')
    for item in rule.get('allOf', []):
        errors.extend(shape_errors(value, item, schema, path))
    if 'if' in rule:
        branch = 'else' if shape_errors(value, rule['if'], schema) else 'then'
        errors.extend(shape_errors(value, rule.get(branch, {}), schema, path))
    return errors


def unfenced(text):
    """Keep line positions while excluding fenced examples from task metadata."""
    fence = None
    lines = []
    for line in text.splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            lines.append('')
        else:
            lines.append('' if fence else line)
    return '\n'.join(lines)


def field_content(body, name):
    # Both **Goal:** and **Goal**: are ordinary Markdown labels. Emphasis
    # inside a field is content, not another field (e.g. **Not applicable**).
    labels = ('Context', 'Goal', 'Touched Surface', 'Acceptance Criteria',
              'Validation', 'Instructions', 'Read Before Starting',
              'Completion & Log', 'Completion log', 'Skills disposition')
    def label_pattern(label):
        return r'\*\*(?:'+label+r')\s*:?\*\*[ \t]*[:·-]?'

    pattern = r'(?im)(?:^#{2,6}[ \t]+(?:\d+[.]?[ \t]*)?'+re.escape(name)+r'[ \t]*$|'+label_pattern(re.escape(name))+')'
    match = re.search(pattern, body)
    if not match:
        return ''
    rest = body[match.end():]
    boundary = re.search(r'(?im)^#{2,6}[ \t]|'+label_pattern('|'.join(map(re.escape, labels))), rest)
    return (rest[:boundary.start()] if boundary else rest).strip(' \n\r`·:-')


def collapse(problems):
    """Group shape errors that repeat across array entries.

    One malformed record shape repeated over thirty tasks is one defect, not
    thirty findings; report it once, with the first concrete path and a count.
    """
    grouped = {}
    for problem in problems:
        grouped.setdefault(re.sub(r'\[\d+\]', '[]', problem), []).append(problem)
    return [(found[0], len(found)) for found in grouped.values()]


def declared_standard(clean, manifest):
    """The standard the plan executes: README declaration wins, then manifest."""
    found = re.search(r'\*\*Standard:\*\*\s*DWP spec\s*(\d+\.\d+\.\d+)', clean)
    return found[1] if found else manifest.get('spec_version')


def security_findings(plan):
    """Completed-plan security artifact gate (DWP_SPECIFICATION §6.1).

    Read whole-file, not line by line: the acceptance wording that clears a
    finding ("no unresolved critical") often sits in a different line from the
    mention that raised it.
    """
    security = plan/'analysis_results/SECURITY_REVIEW.md'
    if not security.is_file():
        return ['completed plan missing analysis_results/SECURITY_REVIEW.md '
                '(DWP_SPECIFICATION §6.1) — Final Review must write it even when clean']
    text = security.read_text()
    cleared = r'no unresolved critical|without (?:an )?unresolved critical|0 unresolved critical|zero unresolved critical'
    if re.search(r'open critical finding|critical finding remains|unresolved critical finding:', text, re.I) \
            or (re.search(r'unresolved critical', text, re.I) and not re.search(cleared, text, re.I)):
        return ['completed plan SECURITY_REVIEW.md still reports an unresolved critical finding '
                '(DWP_SPECIFICATION §6.1) — fix it or record explicit acceptance']
    if re.search(r'(?m)(^|[|\s])critical([|\s]|$)|🚨\s*critical', text, re.I) and not re.search(
            cleared + r'|0 critical|zero critical|explicitly accepted|accepted by the (?:user|developer)'
            r'|criticals?:\s*0|no findings|no criticals?\b|criticals?:?\**\s*none'
            r'|\bfixed in\b|\bresolved in\b', text, re.I):
        return ['completed plan SECURITY_REVIEW.md mentions critical findings without a clear '
                'resolution/acceptance (DWP_SPECIFICATION §6.1)']
    return []


def gate_findings(tasks, v2):
    """Execution evidence, identical in both eras (PLAN_STATE.md §7).

    A record missing the documented `passes` boolean is malformed, not failing:
    report the shape once rather than accusing every task of a failed gate.
    """
    errors, malformed = [], 0
    for task in tasks:
        if not isinstance(task, dict):
            errors.append('state task must be an object')
            continue
        latest = {}
        for gate in task.get('gates', []):
            if not isinstance(gate, dict):
                malformed += 1
                continue
            if not isinstance(gate.get('passes'), bool):
                malformed += 1
                continue
            latest[gate.get('command')] = gate
            if gate['passes'] and re.search(
                    r'(ran|selected|executed)\s*=\s*0(?:\b|/)|no tests? (ran|found|collected)',
                    str(gate.get('evidence', '')), re.I):
                errors.append('passing gate has zero-selection evidence')
        if task.get('status') == 'completed':
            if any(not g['passes'] or g.get('exit_code', 0) != 0 for g in latest.values()):
                errors.append(f'completed task {task.get("id")} has a failing gate without a '
                              f'later passing run')
            if v2 and (not task.get('completed_at') or not latest):
                errors.append(f'completed v2 task {task.get("id")} requires completed_at '
                              f'and gate evidence')
    if malformed:
        errors.append(f'{malformed} gate record(s) do not carry the documented `passes` boolean '
                      f'(PLAN_STATE.md §4.2) — their result cannot be read')
    return errors


class Report:
    """Ordered pass/advisory/failure lines, rendered by conformance.sh."""

    def __init__(self):
        self.lines = []
        self.failed = False

    def ok(self, message):
        self.lines.append('+ ' + message)

    def note(self, message):
        self.lines.append('~ ' + message)

    def bad(self, message):
        self.lines.append(message)
        self.failed = True

    def verdict(self, held, message, otherwise=None):
        self.ok(message) if held else self.bad(otherwise or message)
        return held

    def extend(self, messages, otherwise=None):
        """Fold a helper's failures in, or record the all-clear line."""
        for message in messages:
            self.bad(message)
        if not messages and otherwise:
            self.ok(otherwise)
        return not messages


def check(plan, is_git=True):
    report = Report()
    documents = {}
    for label in ('state', 'manifest'):
        path = plan / (label+'.json')
        if path.exists():
            try:
                documents[label] = json.loads(path.read_text())
                if not isinstance(documents[label], dict):
                    raise ValueError('expected object')
            except (ValueError, OSError) as exc:
                report.bad(f'{label}.json parses: {exc}')
    if report.failed:
        return report
    for label, doc in documents.items():
        url = doc.get('schema')
        known = [f'https://deepworkplan.com/schema/plan-{label}/v{v}.json' for v in (1, 2)]
        if url is not None and url not in known:
            report.bad(f'unknown {label} schema URL {url!r} — upgrade the installed skill')
    if report.failed:
        return report
    state, manifest = documents.get('state', {}), documents.get('manifest', {})
    if state.get('schema') == STATE_V2:
        current(plan, state, manifest, report)
    else:
        legacy(plan, state, manifest, is_git, report)
    return report


# ------------------------------------------------------------------- current
def current(plan, state, manifest, report):
    """The v4 contract: v2 state, typed locators, Lite or Full."""
    if manifest.get('schema') != MANIFEST_V2:
        return report.bad('v2 state requires its v2 creation manifest — recover with create/refine')
    shape = []
    for label, doc in (('state', state), ('manifest', manifest)):
        schema = json.loads((Path(__file__).parent.parent/'spec/schema'/f'plan-{label}-v2.schema.json').read_text())
        for problem, count in collapse(shape_errors(doc, schema, schema)):
            shape.append(f'{label}.json {problem}'
                         + (f' (and {count - 1} more record(s) alike)' if count > 1 else ''))
    for problem in shape:
        report.bad(problem)
    if state.get('approval') not in (None, 'pending', 'approved', 'pre_approved'):
        report.bad('plan has an unknown approval value')
    # A malformed gate record must not hide the rest of the plan: it leaves the
    # task skeleton intact, so keep checking. Any other shape error can make the
    # structural checks read fields that are not there — stop there instead.
    if report.failed and not all('.gates[' in problem for problem in shape):
        return None
    if not shape:
        report.ok('state.json and manifest.json parse against the v2 schemas')
    if state.get('promotion') is not None or state.get('materialization') == 'promoting':
        return report.bad('plan has an unresolved promotion marker — finish it with '
                          '/dwp-refine promote before execution; execute and resume must not '
                          'run a mixed representation')
    if state.get('materialization') != 'ready':
        return report.bad('plan materialization is not ready — complete or discard this partial '
                          'materialization with create/refine before execution')
    if not (plan/'README.md').is_file():
        return report.bad('plan has no README.md — its task records live there; complete or '
                          'discard this partial materialization with create/refine')
    for filename in ('PROGRESS.md', 'PROMPTS.md'):
        if not (plan/filename).is_file():
            report.bad('partial materialization: missing '+filename+' — recover with create/refine')
    if not (plan/'analysis_results').is_dir():
        report.bad('partial materialization: missing analysis_results/')
    readme = (plan/'README.md').read_text()
    clean = unfenced(readme)
    standard = declared_standard(clean, manifest)
    if not version(standard):
        report.note('plan standard undeclared — add the README Standard line (PLAN_STATE.md §6.1)')
    elif version(standard) > version(SUPPORTED_SPEC):
        report.bad(f'plan declares DWP spec {standard}, newer than this checker supports '
                   f'({SUPPORTED_SPEC}) — upgrade the installed skill before executing it')
    elif version(standard)[0] not in SPEC_SERIES:
        report.bad(f'plan declares DWP spec {standard}, which is not a DWP standard (the series '
                   f'are 2.x historical and 4.x current; there is no 3.x) — correct the '
                   f'Standard line (PLAN_STATE.md §6.1)')
    else:
        report.ok(f'plan standard: DWP spec {standard}'
                  + (' (historical, accepted)' if version(standard)[0] != 4 else ''))
    if 'Plan Status: materializing' in clean:
        report.bad('partial materialization — recover with create/refine')
    report.verdict(state.get('plan') == plan.name and manifest.get('name') == plan.name,
                   'plan identity matches its directory',
                   'plan identity disagrees with its directory')
    # The v2 Goal+Context pair is required at plan level too (guide/authoring.md
    # §4.1 items 1–2): Goal says what, Context says where the work lives.
    report.verdict(bool(field_content(clean, 'Goal')) and bool(field_content(clean, 'Context')),
                   'plan README carries the Goal+Context pair (v2 shape restored)',
                   'plan README lacks a non-empty Context section alongside Goal — the v2 '
                   'Goal+Context pair is required (guide/authoring.md §4.1)')
    tasks = state.get('tasks', [])
    if not isinstance(tasks, list):
        return report.bad('state tasks must be an array')
    checks = re.findall(r'^\s*- \[([ xX])\].*?\bTask\s+(\d+)\b', clean, re.M | re.I)
    ids = [t['id'] for t in tasks]
    report.verdict(ids == list(range(1, len(tasks)+1)) and len(tasks) >= 2,
                   f'task ids are contiguous 1..{len(tasks)} (numeric order)',
                   'task ids are not contiguous or ordered: a plan needs at least one user task '
                   'plus the Final Review')
    if state['task_count'] != len(tasks):
        report.bad('state task_count disagrees with task records')
    if [int(i) for _, i in checks] != ids:
        report.bad('README canonical task index disagrees with state task IDs/order')
    checked = {int(i): c.lower() == 'x' for c, i in checks}
    for task in tasks:
        if checked.get(task['id']) != (task['status'] == 'completed'):
            report.bad('state status disagrees with README: Task '+str(task['id']))
    if state['completed_count'] != sum(t['status'] == 'completed' for t in tasks):
        report.bad('completed_count disagrees with task statuses')
    summary = re.search(r'Plan Status:\s*(\d+)\s*/\s*(\d+)', clean)
    if not summary or (int(summary[1]), int(summary[2])) != (
            sum(c.lower() == 'x' for c, _ in checks), len(tasks)):
        report.bad('README Plan Status count disagrees with task checkboxes/state')
    lite = state['format'] == 'lite'
    before = report.failed
    for task in tasks:
        locator = task['locator']
        if locator['kind'] != ('inline' if lite else 'file'):
            report.bad('task locator kind disagrees with plan format')
        if locator['kind'] == 'file':
            target = (plan/locator['value']).resolve()
            if not target.is_relative_to(plan.resolve()):
                report.bad('task locator escapes the plan through a symlink')
            if not target.is_file():
                report.bad('missing task file: '+locator['value'])
            elif not locator['value'].startswith(str(task['id'])+'.task_'):
                report.bad('task id disagrees with filename')
            else:
                body = target.read_text()
                for name in ('Goal', 'Touched Surface', 'Acceptance Criteria', 'Validation'):
                    if not field_content(body, name):
                        report.bad(f'Task {task["id"]} lacks non-empty {name}')
                # Context is a starting requirement, not a history requirement:
                # a task still to be run must be startable from it, while a
                # completed task's record stays as authored (DWP_SPECIFICATION
                # §6.5 evidence history).
                if task['status'] != 'completed' and not field_content(body, 'Context'):
                    report.bad(f'Task {task["id"]} lacks non-empty Context — task-specific '
                               f'background; the agent MUST be able to start from this section '
                               f'alone (DWP_SPECIFICATION §5)')
                if task['id'] == len(tasks):
                    if 'task_final_review' not in locator['value'] or not all(
                            term in body.lower() for term in ('security', 'final-state', 'skills')):
                        report.bad('Full final task must be the Final Review, naming its security '
                                   'pass, final-state validation and skills reconciliation')
                elif 'task_final_review' in locator['value']:
                    report.bad('Final Review must be last')
        elif locator['value'] != '#task-'+str(task['id']) or clean.count('{'+locator['value']+'}') != 1:
            report.bad('Lite task anchor is missing or duplicated: '+str(task['id']))
    if not lite:
        expected = {t['locator']['value'] for t in tasks}
        actual = {p.name for p in plan.glob('[0-9]*.task_*.md')}
        if expected != actual:
            report.bad('Full task files disagree with state inventory')
        for filename in sorted(expected):
            if not re.search(r'\]\((?:\./)?'+re.escape(filename)+r'\)', clean):
                report.bad('README missing task link: '+filename)
    else:
        headers = list(re.finditer(r'^##\s+Task\s+(\d+)([^\n]*)\{#task-(\d+)\}[^\n]*$', clean, re.M))
        finals = [int(h[1]) for h in headers if re.search(r'Final Review', h[2], re.I)]
        if finals != [len(tasks)]:
            report.bad('Lite plan lacks Final Review as the unique last task')
        for header in headers:
            if header[1] != header[3]:
                report.bad('Lite task heading disagrees with its anchor')
            # Inspect raw task content so commands in fenced gates count.
            body = re.search(r'(?ms)^##\s+Task\s+'+header[1]+r'[^\n]*\{#task-'+header[3]+r'\}(.*?)(?=^## |\Z)', readme)
            if body:
                for name in ('Goal', 'Touched Surface', 'Acceptance Criteria', 'Validation'):
                    if not field_content(body[1], name):
                        report.bad('Lite task lacks '+name+': '+header[1])
                status = next((t.get('status') for t in tasks
                               if isinstance(t, dict) and t.get('id') == int(header[1])), None)
                if status != 'completed' and not field_content(body[1], 'Context'):
                    report.bad('Lite task lacks Context: '+header[1]+' — task-specific '
                               'background; the agent MUST be able to start from this section '
                               'alone (DWP_SPECIFICATION §5)')
                if int(header[1]) == len(tasks) and not all(
                        term in body[1].lower() for term in ('security', 'final-state', 'skills')):
                    report.bad('Lite Final Review lacks its security, final-state validation or skills part')
        if len(headers) != len(tasks):
            report.bad('Lite task records do not match the state inventory')
        if list(plan.glob('[0-9]*.task_*.md')):
            report.bad('Lite plan contains Full task files without a promotion transaction')
    if report.failed == before:
        report.ok('Lite task anchors, records and Final Review are valid' if lite else
                  'Full task files, records and Final Review are valid')
    report.extend(gate_findings(tasks, True), 'task gate evidence supports every completed task')
    complete = bool(tasks) and all(isinstance(t, dict) and t.get('status') == 'completed' for t in tasks)
    report.verdict(complete == (state.get('status') == 'completed'),
                   'plan execution status agrees with task completion',
                   'plan execution status disagrees with task completion')
    if complete:
        report.extend(security_findings(plan),
                      'completed plan SECURITY_REVIEW.md has no unresolved critical finding')
    approval = state.get('approval')
    if approval in (None, 'pending'):
        report.note('valid proposal awaiting approval — an explicit execute request approves '
                    'its current scope')
    else:
        report.ok(f'plan is {approval.replace("_", "-")} for execution')
    return None
# -------------------------------------------------------------------- legacy
def legacy(plan, state, manifest, is_git, report):
    """Plans written before the v2 state layer.

    Accepted against the shape they were authored under (DWP_SPECIFICATION §6.5):
    a single Final Review last for 2.3.0+, the three-final-task ending before it.
    This path only reads; it never asks an old plan to become a new one.
    """
    for filename in ('README.md', 'PROMPTS.md', 'PROGRESS.md'):
        report.verdict((plan/filename).is_file(), filename)
    if not (plan/'README.md').is_file():
        return report.bad('plan has no README.md — its task list lives there; complete or '
                          'discard this partial materialization with create/refine')
    readme = (plan/'README.md').read_text()
    clean = unfenced(readme)
    standard = declared_standard(clean, manifest)

    if re.search(r'Plan Status: *materializing', clean):
        present = len(list(plan.glob('[0-9]*.task_*.md')))
        return report.bad(
            f"partial materialization: README says 'Plan Status: materializing' (manifest "
            f"declares {manifest.get('task_count', '?')} tasks, {present} task files present) — "
            f"complete or discard it with create/refine; never execute it")
    if not manifest and version(standard) >= (2, 3, 0):
        report.note('harness-version finding: manifest.json missing (plans authored under '
                    '2.3.0 write it first, PLAN_STATE.md §2)')
    report.verdict((plan/'analysis_results').is_dir(), 'analysis_results/')

    # ---- task inventory: numeric ids, unique, contiguous 1..N
    files = sorted(p.name for p in plan.glob('[0-9]*.task_*.md'))
    ids, nonnumeric = [], 0
    for name in files:
        head_part = name.split('.', 1)[0]
        ids.append(int(head_part)) if head_part.isdigit() else None
        nonnumeric += 0 if head_part.isdigit() else 1
    if nonnumeric:
        report.bad(f'task ids are numeric ({nonnumeric} file(s) with a non-numeric prefix)')
    duplicates = len(ids) - len(set(ids))
    report.verdict(not duplicates, 'task ids are unique',
                   f'task ids are unique ({duplicates} duplicate id(s))')
    highest = max(ids, default=0)
    missing = sum(1 for k in range(1, highest+1) if k not in ids)
    report.verdict(not missing and not duplicates and not nonnumeric and highest == len(files),
                   f'task ids are contiguous 1..{highest} (numeric order)',
                   f'task ids are contiguous 1..N ({missing} missing id(s); {len(files)} files, '
                   f'highest id {highest})')

    # ---- lifecycle shape (DWP_SPECIFICATION §6.5)
    migrated = bool(re.search(r'\*\*Standard:\*\*.*\(migrated from', clean))

    def ids_matching(pattern):
        return sorted(int(f.name.split('.', 1)[0]) for f in plan.glob(pattern)
                      if f.name.split('.', 1)[0].isdigit())

    finals = ids_matching('[0-9]*.task_final_review*.md')
    security = (ids_matching('[0-9]*.task_security_review.md') or [None])[0]
    discovery = (ids_matching('[0-9]*.task_skills_agents_discovery.md') or [None])[0]
    report_task = (ids_matching('[0-9]*.task_executive_report.md') or [None])[0]

    if not version(standard):
        report.note('plan standard undeclared (no README Standard line, no manifest) — '
                    'treated as legacy')
    elif version(standard) > version(SUPPORTED_SPEC):
        report.bad(f'plan declares DWP spec {standard}, newer than this checker supports '
                   f'({SUPPORTED_SPEC}) — upgrade the installed skill before executing it')
    elif version(standard)[0] not in SPEC_SERIES:
        report.bad(f'plan declares DWP spec {standard}, which is not a DWP standard (the series '
                   f'are 2.x historical and 4.x current; there is no 3.x) — correct the '
                   f'Standard line (PLAN_STATE.md §6.1)')
    else:
        report.ok(f'plan standard: DWP spec {standard}'
                  + (' (declared migration)' if migrated else ''))

    shape = ''
    if len(finals) > 1:
        report.bad(f'exactly one Final Review task ({len(finals)} found)')
    elif finals and (discovery is not None or report_task is not None):
        report.bad('mixed lifecycle: a Final Review task coexists with legacy '
                   'skills_agents_discovery/executive_report tasks — pick one shape '
                   '(DWP_SPECIFICATION §6.5)')
    elif finals:
        shape = 'new'
        report.verdict(finals[0] == highest,
                       f'mandatory final task: Final Review is task {highest} (last)',
                       f'mandatory final task: Final Review must be the last task '
                       f'(found id {finals[0]}, highest id {highest})')
        if security is not None:
            done = re.search(r'(?m)^\s*- \[x\].*(?:%d\.task_security_review|[Tt]ask\s+%d\b)'
                             % (security, security), clean)
            report.verdict(bool(migrated and security == highest - 1 and done),
                           f'migrated plan keeps its completed Security Review as task '
                           f'{security} before the Final Review',
                           'mixed lifecycle: security_review task alongside a Final Review is '
                           'valid only for a declared migration with the security review already '
                           'completed (refine migrate, step 3)')
        report.verdict(len(files) >= 2, f'task files present ({len(files)})',
                       f'task files present ({len(files)}; need >= 1 user task + the Final Review)')
        if version(standard) and version(standard) <= (2, 2, 0):
            report.note(f'plan uses the 2.3.0 shape but declares {standard} — add the README '
                        f'declared-migration line (PLAN_STATE §6.1)')
    elif security is not None or discovery is not None or report_task is not None:
        shape = 'legacy'
        if version(standard) >= (2, 3, 0) and not migrated:
            report.bad(f'plan declares DWP spec {standard} but carries the pre-2.3.0 '
                       f'three-final-task shape — a declared new plan must end with a single '
                       f'Final Review')
        for label, found, want in (('security review', security, highest-2),
                                   ('skills & agents discovery', discovery, highest-1),
                                   ('executive report', report_task, highest)):
            report.verdict(found == want, f'mandatory task: {label}',
                           f'mandatory task: {label} (legacy shape: must be task {want}'
                           + (f', found {found}' if found is not None else '') + ')')
        report.verdict(len(files) >= 4, f'task files present ({len(files)})',
                       f'task files present ({len(files)}; legacy shape needs >= 1 user task + '
                       f'3 mandatory final tasks)')
    else:
        report.bad('mandatory final task missing — accepted shapes: {N}.task_final_review.md '
                   'last (DWP 2.3.0+), or {N-2}.task_security_review.md + '
                   '{N-1}.task_skills_agents_discovery.md + {N}.task_executive_report.md '
                   '(pre-2.3.0)')

    # Objective structure of the Final Review (the filename alone proves nothing).
    if shape == 'new':
        absent = []
        for path in plan.glob('[0-9]*.task_final_review*.md'):
            body = path.read_text().lower()
            absent += [label for label, present in (
                ('security-pass', 'security' in body),
                ('final-state-validation',
                 bool(re.search(r'final-state|full (validation|suite|gate)|complete applicable', body))),
                ('skills-reconciliation', 'skills' in body)) if not present]
        report.verdict(not absent, 'Final Review names its three parts (security pass, '
                       'final-state validation, skills reconciliation)',
                       'Final Review file does not mention: ' + ' '.join(absent)
                       + ' (DWP_SPECIFICATION §6.1) — the filename alone does not prove coverage')

    # ---- completed-plan security artifact (DWP_SPECIFICATION §6.1)
    boxes = re.findall(r'(?m)^\s*- \[([ xX])\]', clean)
    summary = re.search(r'Plan Status: *(\d+)\s*/\s*(\d+)', clean)
    complete = bool(boxes) and all(b.lower() == 'x' for b in boxes) and bool(
        summary and summary[1] == summary[2] and int(summary[2]) > 0)
    if complete:
        if (plan/'analysis_results/SECURITY_REVIEW.md').is_file():
            report.ok('completed plan has analysis_results/SECURITY_REVIEW.md')
            report.extend(security_findings(plan),
                          'completed plan SECURITY_REVIEW.md has no unresolved critical finding')
        else:
            report.bad('completed plan missing analysis_results/SECURITY_REVIEW.md '
                       '(DWP_SPECIFICATION §6.1) — Final Review must write it even when clean')

    # ---- README <-> files correspondence
    report.verdict(bool(summary), 'README has a Plan Status count')
    linked = re.findall(r'\]\(\./([0-9]+\.task_[A-Za-z0-9_]+\.md)\)', clean)
    if not linked:
        report.note('README task list carries no task-file links (finding — pre-2.3.0 READMEs '
                    'may list tasks without links; correspondence not checked)')
    else:
        unreferenced = sum(1 for name in files if name not in clean)
        broken = sum(1 for name in set(linked) if not (plan/name).is_file())
        report.verdict(not unreferenced and not broken,
                       'README task list matches the task files',
                       f'README task list matches the task files ({unreferenced} file(s) not '
                       f'referenced, {broken} README link(s) broken)')

    # Dependency references named in a Read Before Starting section must exist.
    badref = 0
    for name in files:
        section = re.search(r'(?ms)^## [0-9.]* *Read Before Starting(.*?)(?=^## |\Z)',
                            unfenced((plan/name).read_text()))
        if section:
            badref += sum(1 for n in set(re.findall(r'[Tt]ask (\d+)', section[1]))
                          if int(n) not in ids)
    if badref:
        report.note(f'Read Before Starting references {badref} task number(s) that do not exist '
                    f'(finding — check renumbering)')
    else:
        report.ok('Read Before Starting references resolve to existing tasks')

    gateless = sum(1 for name in files
                   if not re.search(r'(?im)^#+ .*validation', (plan/name).read_text()))
    report.verdict(not gateless, 'every task declares a Validation section',
                   f'every task declares a Validation section ({gateless} missing)')

    if shape == 'new':
        nots = sum(1 for name in files if 'task_final_review' not in name and not re.search(
            r'(?im)^#+ .*touched surface|^\*\*touched surface', (plan/name).read_text()))
        if nots:
            report.note(f'{nots} task(s) without a Touched Surface section (finding — required '
                        f'for behavior-changing tasks, DWP_SPECIFICATION §5.0.2; docs/research '
                        f'tasks may state not applicable)')
        else:
            report.ok('every task carries a Touched Surface section')
        if (plan/'analysis_results/SKILLS_CANDIDATES.md').is_file():
            report.ok('analysis_results/SKILLS_CANDIDATES.md present')
        else:
            report.note('analysis_results/SKILLS_CANDIDATES.md missing (finding — acceptable '
                        'until the first candidate exists; task logs may record "none")')

    # ---- state layer: optional in a git repo, REQUIRED without git
    if not state:
        if is_git:
            report.note('no state layer (state.json) — RECOMMENDED for new plans')
        else:
            report.bad('state.json (REQUIRED in a workspace without git, PLAN_STATE.md §2.1)')
        return None
    report.ok('state.json parses')
    report.verdict(bool(manifest), 'manifest.json parses',
                   'manifest.json present and parses (required alongside state.json)')
    legacy_state(plan, state, clean, files, ids, report)
    return None


def legacy_state(plan, state, clean, files, ids, report):
    """v1 state layer.

    A minimal v1 projection may carry only `completed_count`; the desync check
    still applies to it. Task correspondence is checked only once the state
    declares a `task_count`, matching what pre-v2 plans actually wrote.
    """
    tasks = state.get('tasks', [])
    if not isinstance(tasks, list) or any(not isinstance(t, dict) for t in tasks):
        return report.bad('state.json tasks must be an array of task objects')

    checks = {}
    for line in clean.splitlines():
        box = re.match(r'^\s*- \[([ xX])\]\s*(.*)', line)
        if not box:
            continue
        found = re.search(r'\b[Tt]ask\s+(\d+)\b|(?:^|\[)(\d+)\.task_', box[2])
        if found:
            ident = int(found[1] or found[2])
            if ident in checks:
                report.bad('README has duplicate task checkbox: ' + str(ident))
            checks[ident] = box[1].lower() == 'x'

    # Markdown wins: the README checkbox count is the progress of record.
    if state.get('completed_count') is not None:
        md_done = sum(1 for value in checks.values() if value)
        report.verdict(md_done == state['completed_count'],
                       f'state.json completed_count matches README '
                       f'({state["completed_count"]} completed)',
                       f'state.json desync: README shows {md_done} completed, state.json says '
                       f'{state["completed_count"]} (markdown wins — regenerate state.json, '
                       f'PLAN_STATE.md §5)')
    if state.get('task_count') is None:
        return None
    report.verdict(state['task_count'] == len(files),
                   f'state.json task_count matches the task files ({len(files)})',
                   f'state.json task_count ({state["task_count"]}) differs from the task files '
                   f'on disk ({len(files)}) — regenerate state.json (PLAN_STATE.md §5)')
    listed = [t.get('file') for t in tasks]
    if any(not isinstance(f, str) for f in listed):
        return report.bad('state.json task entries require a task-file locator')

    stale = ' (markdown wins — regenerate state.json when stale)'
    before = report.failed
    if len(tasks) != len(files) or set(listed) != set(files):
        report.bad('state.json task entries do not match the task files one-to-one' + stale)
    if len(set(listed)) != len(listed):
        report.bad('state.json has duplicate task entries' + stale)
    state_ids = [t.get('id') for t in tasks]
    if any(type(i) is not int for i in state_ids):
        report.bad('state.json task ids must be integers' + stale)
    elif len(set(state_ids)) != len(state_ids):
        report.bad('state.json has duplicate task ids' + stale)
    for task, name in zip(tasks, listed):
        head = re.match(r'^(\d+)\.task_', name)
        if head and task.get('id') != int(head[1]):
            report.bad('state.json task id disagrees with file: ' + name + stale)
        if task.get('status') not in STATUSES:
            report.bad('state.json invalid task status: ' + name + stale)
    if set(checks) != set(ids):
        report.bad('README task checkboxes do not match the task ids on disk' + stale)
    for task in tasks:
        ident = task.get('id')
        if type(ident) is int and ident in checks:
            if (task.get('status') == 'completed') != checks[ident]:
                report.bad('state.json task status disagrees with README: Task '
                           + str(ident) + stale)
    done = sum(t.get('status') == 'completed' for t in tasks)
    if state.get('completed_count') is not None and state['completed_count'] != done:
        report.bad('state.json completed_count disagrees with task statuses' + stale)
    summary = re.search(r'Plan Status: *(\d+)\s*/\s*(\d+)', clean)
    if summary and (int(summary[1]), int(summary[2])) != (sum(checks.values()), len(files)):
        report.bad('README Plan Status count disagrees with task checkboxes/files' + stale)
    for problem in gate_findings(tasks, False):
        report.bad(problem)
    if report.failed == before:
        report.ok('state.json task entries and statuses match README and task files')
    return None


if __name__ == '__main__':
    try:
        outcome = check(Path(sys.argv[1]), is_git=(sys.argv[2:3] or ['git'])[0] == 'git')
        lines, failed = outcome.lines, outcome.failed
    except (OSError, ValueError, KeyError, TypeError) as exc:
        lines, failed = [f'plan contract cannot be verified: {exc}'], True
    for line in lines:
        print(line)
    sys.exit(1 if failed else 0)
