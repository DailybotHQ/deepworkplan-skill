"""Shared structural and evidence semantics; stdlib-only, never executes gates."""
import json
from pathlib import Path
import re

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


def gate_findings(tasks, state_layer):
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
            if state_layer and (not task.get('completed_at') or not latest):
                errors.append(f'completed state-layer task {task.get("id")} requires '
                              f'completed_at and gate evidence')
    if malformed:
        errors.append(f'{malformed} gate record(s) do not carry the documented `passes` boolean '
                      f'(PLAN_STATE.md §4.2) — their result cannot be read')
    return errors



def derive_status(state):
    tasks = state['tasks']
    if state.get('blocked') or any(t['status'] == 'blocked' for t in tasks):
        return 'blocked'
    if all(t['status'] == 'completed' for t in tasks):
        return 'completed'
    if any(t['status'] != 'pending' for t in tasks):
        return 'in_progress'
    return 'pending'


def state_errors(state, strict=False):
    if not isinstance(state, dict):
        return ['state must be an object']
    url = state.get('schema', '')
    era = next((v for v in (1, 2, 5) if url == f'https://deepworkplan.com/schema/plan-state/v{v}.json'), None)
    if era is None:
        return ['unsupported state schema']
    suffix = '' if era == 1 else f'-v{era}'
    schema = json.loads((Path(__file__).parent.parent/'spec/schema'/f'plan-state{suffix}.schema.json').read_text())
    errors = shape_errors(state, schema, schema)
    if errors:
        return errors
    tasks = state['tasks']
    ids = [t['id'] for t in tasks]
    if ids != list(range(1, len(tasks)+1)) or len(tasks) != state['task_count']:
        errors.append('task identity/count mismatch')
    if state['completed_count'] != sum(t['status'] == 'completed' for t in tasks):
        errors.append('completed_count mismatch')
    if era != 1:
        locators = [t['locator']['value'] for t in tasks]
        if len(set(locators)) != len(locators):
            errors.append('duplicate locator')
        for t in tasks:
            loc = t['locator']; value = loc['value']
            expected = '#task-'+str(t['id']) if loc['kind'] == 'inline' else str(t['id'])+'.task_'
            if not (value == expected if loc['kind'] == 'inline' else value.startswith(expected)):
                errors.append('locator disagrees with task identity')
            if loc['kind'] != ('inline' if state['format'] == 'lite' else 'file'):
                errors.append('locator disagrees with plan format')
    errors.extend(gate_findings(tasks, True))
    blocker = state.get('blocked')
    if blocker and (blocker['task'] not in ids or tasks[blocker['task']-1]['status'] != 'blocked'):
        errors.append('active blocker does not identify a blocked task')
    if strict and any(t['status'] == 'blocked' for t in tasks) and not blocker:
        errors.append('blocked task requires an explicit blocker record')
    if state['status'] != derive_status(state):
        errors.append('plan status disagrees with task/blocker state')
    cp = state.get('checkpoint')
    if cp and cp['task'] not in ids:
        errors.append('checkpoint references missing task')
    if strict and state['status'] == 'completed' and (not cp or cp.get('step') != 'done' or cp['task'] != ids[-1]):
        errors.append('completed state requires terminal checkpoint')
    return errors
