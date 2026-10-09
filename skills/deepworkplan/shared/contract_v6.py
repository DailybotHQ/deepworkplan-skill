#!/usr/bin/env python3
"""v6 outcome/authority contract and journal-event validation; stdlib-only.

Validates the two v6 record surfaces defined by the v6 architecture RFC
(docs/evaluations/v6/ARCHITECTURE_RFC.md, draft-4):

  * ``contract.json``  - the outcome and authority contract (section 3),
    identified by the SHA-256 of its canonical bytes;
  * ``journal.ndjson`` - the append-only event log (section 4), whose full
    event catalog is finalized here (section 14.1).

This module is the RUNTIME half of a two-implementation contract: the
published JSON Schemas under ``spec/schema/`` are validated independently
with jsonschema by a contributor-side checker that lives outside the
pack; this module adds the semantics a
schema cannot express - identity, graph acyclicity, closed enumerations
cross-checked between sections, trust-label/actor consistency, and
control-pair verdict arithmetic. Both halves are exercised against the same
committed v6 fixtures so drift between them is a test failure, not a
silent divergence.

Python 3.9+ stdlib only; never executes gates; never writes files.
"""
import json
import re
import sys

sys.dont_write_bytecode = True  # never leave caches inside an installed pack

CONTRACT_SCHEMA_URL = 'https://deepworkplan.com/schema/plan-contract/v6.json'
JOURNAL_SCHEMA_URL = 'https://deepworkplan.com/schema/journal-event/v6.json'

# The v7 generation (spec/V7_CONTRACT.md) is a strict superset recorded under
# its own URLs: plan-contract/v7 = v6 + optional tasks[].parallel_safe;
# journal-event/v7 = v6 + the `delegation` event. Generation is detected by
# the contract's schema URL - never by pack version - and a plan's events
# carry exactly its generation's journal URL (mixed generations refused).
CONTRACT_SCHEMA_URL_V7 = 'https://deepworkplan.com/schema/plan-contract/v7.json'
JOURNAL_SCHEMA_URL_V7 = 'https://deepworkplan.com/schema/journal-event/v7.json'
CONTRACT_GENERATIONS = {CONTRACT_SCHEMA_URL: 'v6', CONTRACT_SCHEMA_URL_V7: 'v7'}
JOURNAL_GENERATIONS = {JOURNAL_SCHEMA_URL: 'v6', JOURNAL_SCHEMA_URL_V7: 'v7'}
JOURNAL_URL_BY_GENERATION = {'v6': JOURNAL_SCHEMA_URL, 'v7': JOURNAL_SCHEMA_URL_V7}
CONTRACT_URL_BY_GENERATION = {'v6': CONTRACT_SCHEMA_URL,
                              'v7': CONTRACT_SCHEMA_URL_V7}

# v7 delegation (spec/V7_CONTRACT.md section 3; ecosystem contract 2.5).
DELEGATION_TRANSPORTS = ('headless', 'interactive')
DELEGATION_STATES = ('launched', 'completed', 'failed', 'cancelled')
ID_DELEGATION = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')
ID_ADDON = re.compile(r'^[a-z][a-z0-9-]{0,63}$')
DIGEST = re.compile(r'^sha256:[0-9a-f]{64}$')


def contract_generation(doc):
    """'v6' or 'v7' from the contract's schema URL, else None."""
    if not isinstance(doc, dict):
        return None
    return CONTRACT_GENERATIONS.get(doc.get('schema'))


def journal_url_for(contract):
    """The journal-event URL every event of this contract's plan carries."""
    return JOURNAL_URL_BY_GENERATION.get(contract_generation(contract),
                                         JOURNAL_SCHEMA_URL)

# Section 3.3: the closed adaptation enumeration. Anything outside it is
# refused by the authorization core; this module refuses it at the record.
ADAPTATION_KINDS = ('split', 'reorder', 'insert', 'change_strategy', 'retry')

# Section 3.1 / D3-1 / D3-2: exactly two approval mechanisms exist and
# migration re-uses pre_authorization - there is no third value.
MECHANISMS = ('plan_authorship', 'pre_authorization')

# D3-11: intervention taxonomy, source of record
# docs/evaluations/v6/TELEMETRY.md (A13 - one taxonomy for campaigns and
# product records).
INTERVENTION_CATEGORIES = ('missing_intent', 'new_authority',
                           'environment_repair', 'engineering_rescue')

# Section 3.2 Permissions: the closed capability set (see the schema's
# $defs.capability for the per-name meaning). Names outside it are
# unsupported capabilities and are refused.
CAPABILITIES = ('gate_command_exec', 'fs_write_plan_scope',
                'fs_write_repo_scope', 'git_operations', 'network_access',
                'host_adapter_metering', 'agent_delegation', 'context_export',
                'model_routing')

# Section 4.5 trust labels.
TRUST_LABELS = ('observed', 'imported', 'asserted')

# Actor kinds that may carry trust=observed: a shipped helper itself
# executed the check, or a host adapter read a real meter (A1 - an agent
# actor mediates a write, not an execution).
EXECUTING_ACTORS = ('helper', 'host_adapter')

# Section 4.1 catalog, finalized (RFC 14.1): the eleven named types plus
# task_start (fixes each task's starting journal position, D2-9b), refusal
# (section 5: every refusal is a recorded event) and selection (the
# section-5 starvation priority boost).
JOURNAL_EVENT_TYPES = ('task_start', 'approval', 'gate_run', 'observation',
                       'adaptation', 'amendment', 'intervention',
                       'resource_sample', 'control_pair', 'selection',
                       'refusal', 'view_render', 'reconciliation',
                       'journal_repair')

# v7 catalog: the v6 catalog plus `delegation` (V7_CONTRACT.md section 3).
JOURNAL_EVENT_TYPES_V7 = JOURNAL_EVENT_TYPES + ('delegation',)

# Types whose payload carries evidence and therefore a trust label.
EVIDENCE_TYPES = ('gate_run', 'observation', 'resource_sample',
                  'control_pair')

ID_TASK = re.compile(r'^T-[a-z0-9]+(-[a-z0-9]+)*$')
ID_CRITERION = re.compile(r'^AC-[a-z0-9]+(-[a-z0-9]+)*$')
ID_INVARIANT = re.compile(r'^INV-[a-z0-9]+(-[a-z0-9]+)*$')
ID_PLAN = re.compile(
    r'^PLAN_(?:[0-9]{3,}_)?[a-z0-9]+(?:_[a-z0-9]+){1,4}$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')
DATETIME = re.compile(
    r'^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$')
LIMIT_ID = re.compile(r'^[a-z][a-z0-9_]*$')


def canonical_bytes(obj):
    """Section 3.1 canonical form: sorted keys, no insignificant whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode('utf-8')


def compute_contract_id(doc):
    """SHA-256 of the canonical bytes WITHOUT the contract_id field.

    Every helper - preview, migration, guarded writer - computes identity
    through this one function, so the same bytes always yield the same id.
    """
    body = {k: v for k, v in doc.items() if k != 'contract_id'}
    import hashlib
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


# Chain metadata is identity bookkeeping, not substance: a revision is
# "identical to its parent" when nothing but these fields differs.
CHAIN_FIELDS = ('contract_id', 'parent_contract_id', 'revision')


def revision_content_bytes(doc):
    """Canonical bytes with the chain fields stripped (substance only)."""
    body = {k: v for k, v in doc.items() if k not in CHAIN_FIELDS}
    return canonical_bytes(body)


def _is_num(value):
    """True for real JSON numbers (bool is an int subclass - exclude it)."""
    return type(value) in (int, float)


def _is_int(value):
    return type(value) is int


def _str_list(value, path, errors, minimum=0):
    if not isinstance(value, list) or len(value) < minimum:
        errors.append('%s: expected a list with at least %d entr%s' %
                      (path, minimum, 'y' if minimum == 1 else 'ies'))
        return False
    for i, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append('%s[%d]: expected a non-empty string' % (path, i))
            return False
    return True


def _field(doc, key, expected, path, errors, optional=False):
    """Type-check one closed-object field; returns the value or None."""
    if key not in doc:
        if not optional:
            errors.append('%s: missing required field %r' % (path, key))
        return None
    value = doc[key]
    if expected == 'str':
        if not isinstance(value, str) or not value.strip():
            errors.append('%s.%s: expected a non-empty string' % (path, key))
            return None
    elif expected == 'str?':
        if not isinstance(value, str):
            errors.append('%s.%s: expected a string' % (path, key))
            return None
    elif expected == 'datetime':
        if not isinstance(value, str) or not DATETIME.match(value):
            errors.append('%s.%s: expected an RFC 3339 timestamp' %
                          (path, key))
            return None
    elif expected == 'hex64':
        if not isinstance(value, str) or not HEX64.match(value):
            errors.append('%s.%s: expected a 64-character lowercase sha256 '
                          'hex digest' % (path, key))
            return None
    return value


def _closed(obj, known, path, errors):
    for key in obj:
        if key not in known:
            errors.append('%s: unexpected field %r (closed object)' %
                          (path, key))


# ---------------------------------------------------------------- contract

def contract_errors(doc, parents=None):
    """All validation errors for one v6 contract document.

    ``parents`` maps parent contract_id -> parent document; pass it when
    validating a revision so the chain can be checked. Returns a list of
    human-readable error strings; empty means valid.
    """
    errors = []
    if not isinstance(doc, dict):
        return ['contract: expected a JSON object']
    _closed(doc, {'schema', 'spec_version', 'plan', 'revision',
                  'contract_id', 'parent_contract_id', 'created_at', 'title',
                  'outcome', 'acceptance', 'invariants', 'scope',
                  'authorization', 'permissions', 'dependencies',
                  'resource_envelope', 'scheduling', 'tasks'}, 'contract',
            errors)
    declared = doc.get('schema')
    if declared not in CONTRACT_GENERATIONS:
        # Mixed-era refusal (section 9.1): v5 and older documents keep their
        # own recorded tooling; the v6 reader never guesses a legacy parse.
        # The v7 generation (V7_CONTRACT.md) is read by the same reader.
        errors.append("contract.schema: expected %r, found %r - the v6 "
                      "contract reader validates v6 contracts only (and "
                      "their v7 superset %r); older plans keep their "
                      "recorded lifecycle (section 9.1)" %
                      (CONTRACT_SCHEMA_URL, declared, CONTRACT_SCHEMA_URL_V7))
        return errors
    for key in ('spec_version', 'plan', 'revision', 'created_at', 'outcome',
                'acceptance', 'invariants', 'scope', 'authorization',
                'permissions', 'dependencies', 'resource_envelope', 'tasks'):
        if key not in doc:
            errors.append('contract: missing required field %r' % key)
    if errors:
        return errors
    if not re.match(r'^\d+\.\d+\.\d+$', str(doc['spec_version'])):
        errors.append('contract.spec_version: expected dotted-numeric')
    if not ID_PLAN.match(str(doc['plan'])):
        errors.append('contract.plan: expected a PLAN_* identifier')
    if not _is_int(doc['revision']) or doc['revision'] < 1:
        errors.append('contract.revision: expected an integer >= 1')
    if not DATETIME.match(str(doc['created_at'])):
        errors.append('contract.created_at: expected an RFC 3339 timestamp')
    _field(doc, 'title', 'str?', 'contract', errors, optional=True)

    # Identity (section 3.1): content-addressed; drift is a new revision.
    stamped = doc.get('contract_id')
    if stamped is not None:
        if not HEX64.match(str(stamped)):
            errors.append('contract.contract_id: expected a 64-character '
                          'lowercase sha256 hex digest')
        elif stamped != compute_contract_id(doc):
            errors.append(
                'contract.contract_id: stamped identity does not match the '
                'canonical bytes - a changed contract is a NEW revision '
                'citing parent_contract_id, never an in-place edit '
                '(section 3.1)')
    parent = doc.get('parent_contract_id')
    revision = doc['revision'] if _is_int(doc['revision']) else 1
    if revision > 1 and parent is None:
        errors.append('contract.parent_contract_id: required for revision '
                      '%d - a revision must cite the contract it replaces'
                      % revision)
    if revision == 1 and parent is not None:
        errors.append('contract.parent_contract_id: a first revision has no '
                      'parent - drop the field or correct revision')
    if parent is not None and parents is not None:
        if not HEX64.match(str(parent)):
            errors.append('contract.parent_contract_id: expected a sha256 '
                          'hex digest')
        elif parent not in parents:
            errors.append('contract.parent_contract_id: parent %s was not '
                          'supplied for chain checking - pass the earlier '
                          'revision as --parent FILE' % parent[:12])
        else:
            pdoc = parents[parent]
            if pdoc.get('revision') != revision - 1:
                errors.append('contract.parent_contract_id: parent declares '
                              'revision %r, expected %d (chain must be '
                              'contiguous)' % (pdoc.get('revision'),
                                               revision - 1))
            if revision_content_bytes(pdoc) == revision_content_bytes(doc):
                errors.append('contract: revision content is identical to '
                              'the parent once chain metadata is stripped - '
                              'a revision must change something substantive '
                              '(section 3.4)')

    _outcome_errors(doc, errors)
    criteria = _acceptance_errors(doc, errors)
    _invariants_errors(doc, errors)
    _scope_errors(doc, errors)
    _authorization_errors(doc, errors)
    _permissions_errors(doc, errors)
    _dependencies_errors(doc, errors)
    _envelope_errors(doc, errors)
    _scheduling_errors(doc, errors)
    _tasks_errors(doc, criteria, errors,
                  v7=CONTRACT_GENERATIONS[declared] == 'v7')
    return errors


def closure_errors(doc, warnings=None):
    """Criteria that no evidence can ever close (field report F-11).

    Checked when a draft is validated or materialized, never when an
    existing plan is loaded (a recorded contract keeps loading; the
    verifier reports it). What mints each accepted class for a criterion
    some task's gate_intent declares:

      observed  the gate executor (the run is bound to that intent, M5)
      asserted  ``ledger.py signoff`` - a human sign-off bound to it
      imported  migration only (shared/migrate_v6.py), never a live plan

    A regression/discrimination control closes through an executed control
    pair. A criterion no task declares has no evidence path at all: it
    closes only by reconciliation with amendment authority, so it is a
    warning (appended to ``warnings`` when given), not an error.
    """
    errors = []
    if not isinstance(doc, dict):
        return errors
    owned = set()
    for task in doc.get('tasks') or []:
        if isinstance(task, dict):
            for intent in task.get('gate_intent') or []:
                if isinstance(intent, dict):
                    owned.add(intent.get('criterion'))
    for crit in (doc.get('acceptance') or {}).get('criteria') or []:
        if not isinstance(crit, dict):
            continue
        control = crit.get('control') if isinstance(crit.get('control'), dict) else {}
        if control.get('kind') in ('regression', 'discrimination'):
            continue
        accepted = set(crit.get('accepted_evidence') or [])
        if crit.get('id') not in owned:
            if warnings is not None:
                warnings.append(
                    'contract.acceptance: %s is declared by no task '
                    'gate_intent - no gate or sign-off can close it; it '
                    'closes only by reconciliation with amendment authority '
                    '(declare it in the gate_intent of the task that proves '
                    'it)' % crit.get('id'))
            continue
        if not accepted & {'observed', 'asserted'}:
            errors.append(
                'contract.acceptance: %s accepts only %s and nothing can '
                'ever close it: imported evidence comes only from a '
                'migration - accept observed (a gate) or asserted (ledger.py '
                'signoff)' % (crit.get('id'), '/'.join(sorted(accepted))))
    return errors


def gate_command_errors(doc):
    """Gate checks the runner would refuse (field report F-02).

    ``ledger.py gate`` runs a check only when its first token (basename) is
    one of ``scope.allowed_command_classes``; checked at validate and
    materialize so a draft fails before approval, not at its first gate.
    A check whose criterion accepts no ``observed`` evidence is never
    executed (it describes the human check a sign-off records) and is
    skipped. Recorded contracts keep loading.
    """
    errors = []
    if not isinstance(doc, dict):
        return errors
    declared = (doc.get('scope') or {}).get('allowed_command_classes') or []
    if not isinstance(declared, list) or not declared:
        return errors
    accepted = {c.get('id'): c.get('accepted_evidence') or []
                for c in (doc.get('acceptance') or {}).get('criteria') or []
                if isinstance(c, dict)}
    for task in doc.get('tasks') or []:
        if not isinstance(task, dict):
            continue
        for intent in task.get('gate_intent') or []:
            if not isinstance(intent, dict) or \
                    'observed' not in accepted.get(intent.get('criterion'), []):
                continue
            check = intent.get('check')
            words = check.split() if isinstance(check, str) else []
            head = words[0].rsplit('/', 1)[-1] if words else ''
            if head not in declared:
                errors.append(
                    'contract.tasks: %s %s check %r starts with %r, outside '
                    'scope.allowed_command_classes %s - the gate runner '
                    'would refuse it. Declare the command, or wrap shell '
                    'builtins, VAR=value prefixes and compound commands as '
                    "bash -c '...' with bash declared"
                    % (task.get('id'), intent.get('criterion'),
                       (check or '')[:60], head, sorted(declared)))
    return errors


def _outcome_errors(doc, errors):
    outcome = doc.get('outcome')
    if not isinstance(outcome, dict):
        errors.append('contract.outcome: expected an object')
        return
    _closed(outcome, {'statement', 'success_definition', 'out_of_scope'},
            'contract.outcome', errors)
    _field(outcome, 'statement', 'str', 'contract.outcome', errors)
    _field(outcome, 'success_definition', 'str', 'contract.outcome', errors)
    if 'out_of_scope' not in outcome:
        errors.append('contract.outcome: missing required field '
                      "'out_of_scope' (the exclusion list is content)")
    else:
        _str_list(outcome['out_of_scope'], 'contract.outcome.out_of_scope',
                  errors)


def _acceptance_errors(doc, errors):
    acceptance = doc.get('acceptance')
    if not isinstance(acceptance, dict):
        errors.append('contract.acceptance: expected an object')
        return None
    _closed(acceptance, {'criteria'}, 'contract.acceptance', errors)
    criteria = acceptance.get('criteria')
    if not isinstance(criteria, list) or not criteria:
        errors.append('contract.acceptance.criteria: expected a non-empty '
                      'list')
        return None
    seen = set()
    ids = set()
    for i, crit in enumerate(criteria):
        path = 'contract.acceptance.criteria[%d]' % i
        if not isinstance(crit, dict):
            errors.append('%s: expected an object' % path)
            continue
        _closed(crit, {'id', 'statement', 'observable_check',
                       'accepted_evidence', 'control'}, path, errors)
        cid = _field(crit, 'id', 'str?', path, errors)
        if cid is not None:
            if not ID_CRITERION.match(cid):
                errors.append("%s.id: expected an 'AC-<slug>' stable id" %
                              path)
            elif cid in seen:
                errors.append('%s.id: duplicate criterion id %r - ids are '
                              'stable and unique' % (path, cid))
            else:
                seen.add(cid)
                ids.add(cid)
        _field(crit, 'statement', 'str', path, errors)
        _field(crit, 'observable_check', 'str', path, errors)
        accepted = crit.get('accepted_evidence')
        if not isinstance(accepted, list) or not accepted:
            errors.append('%s.accepted_evidence: expected a non-empty list '
                          'of trust labels - every criterion declares which '
                          'section-4.5 classes may close it' % path)
        else:
            for label in accepted:
                if label not in TRUST_LABELS:
                    errors.append('%s.accepted_evidence: unknown trust label '
                                  '%r (closed set: %s)' %
                                  (path, label, '/'.join(TRUST_LABELS)))
            if len(set(map(str, accepted))) != len(accepted):
                errors.append('%s.accepted_evidence: duplicate labels' % path)
        if 'control' in crit:
            control = crit['control']
            cpath = path + '.control'
            if not isinstance(control, dict):
                errors.append('%s: expected an object' % cpath)
            else:
                _closed(control, {'kind', 'rationale'}, cpath, errors)
                kind = _field(control, 'kind', 'str?', cpath, errors)
                if kind is not None and kind not in ('regression',
                                                     'discrimination',
                                                     'exempt'):
                    errors.append('%s.kind: expected regression/discrimination'
                                  '/exempt' % cpath)
                _field(control, 'rationale', 'str', cpath, errors)
    return ids


def _invariants_errors(doc, errors):
    invariants = doc.get('invariants')
    if not isinstance(invariants, list):
        errors.append('contract.invariants: expected a list')
        return
    seen = set()
    for i, inv in enumerate(invariants):
        path = 'contract.invariants[%d]' % i
        if not isinstance(inv, dict):
            errors.append('%s: expected an object' % path)
            continue
        _closed(inv, {'id', 'statement'}, path, errors)
        iid = _field(inv, 'id', 'str?', path, errors)
        if iid is not None:
            if not ID_INVARIANT.match(iid):
                errors.append("%s.id: expected an 'INV-<slug>' stable id" %
                              path)
            elif iid in seen:
                errors.append('%s.id: duplicate invariant id %r' %
                              (path, iid))
            else:
                seen.add(iid)
        _field(inv, 'statement', 'str', path, errors)


def _scope_errors(doc, errors):
    scope = doc.get('scope')
    if not isinstance(scope, dict):
        errors.append('contract.scope: expected an object')
        return
    _closed(scope, {'allowed_paths', 'allowed_command_classes',
                    'forbidden_operations'}, 'contract.scope', errors)
    if 'allowed_paths' not in scope or not scope['allowed_paths']:
        errors.append('contract.scope.allowed_paths: expected a non-empty '
                      'list - a plan that may touch nothing cannot run')
    else:
        _str_list(scope['allowed_paths'], 'contract.scope.allowed_paths',
                  errors)
    if 'allowed_command_classes' not in scope or not scope['allowed_command_classes']:
        errors.append('contract.scope.allowed_command_classes: expected a '
                      'non-empty list - an empty allowlist is undeclared, '
                      'not unrestricted')
    else:
        if _str_list(scope['allowed_command_classes'],
                     'contract.scope.allowed_command_classes', errors):
            if len(set(scope['allowed_command_classes'])) != \
                    len(scope['allowed_command_classes']):
                errors.append('contract.scope.allowed_command_classes: '
                              'duplicate entries')
    if 'forbidden_operations' not in scope or not scope['forbidden_operations']:
        errors.append('contract.scope.forbidden_operations: expected a '
                      'non-empty list - destructive and outward-facing '
                      'operations are named explicitly, never implied')
    else:
        _str_list(scope['forbidden_operations'],
                  'contract.scope.forbidden_operations', errors)


def _authorization_errors(doc, errors):
    auth = doc.get('authorization')
    if not isinstance(auth, dict):
        errors.append('contract.authorization: expected an object')
        return
    _closed(auth, {'mechanism', 'authority', 'timestamp', 'boundaries',
                   'consent_checkpoints'}, 'contract.authorization', errors)
    # D3-1: the Authorization row names the MECHANISM only - the citing
    # record is the section-3.1 journal approval event, never contract
    # content. D3-2: migration re-uses pre_authorization; no third value.
    mechanism = _field(auth, 'mechanism', 'str?', 'contract.authorization',
                       errors)
    if mechanism is not None and mechanism not in MECHANISMS:
        errors.append('contract.authorization.mechanism: unknown value %r - '
                      'exactly %s exist and migration re-uses %r (D3-2)' %
                      (mechanism, ' and '.join(MECHANISMS),
                       'pre_authorization'))
    _field(auth, 'authority', 'str', 'contract.authorization', errors)
    _field(auth, 'timestamp', 'datetime', 'contract.authorization', errors)
    _field(auth, 'boundaries', 'str', 'contract.authorization', errors)
    if 'consent_checkpoints' not in auth:
        errors.append('contract.authorization: missing required field '
                      "'consent_checkpoints' (carried verbatim, even when "
                      'empty)')
    else:
        _str_list(auth['consent_checkpoints'],
                  'contract.authorization.consent_checkpoints', errors)


def _permissions_errors(doc, errors):
    perms = doc.get('permissions')
    if not isinstance(perms, dict):
        errors.append('contract.permissions: expected an object')
        return
    _closed(perms, {'granted', 'not_granted'}, 'contract.permissions',
            errors)
    granted = perms.get('granted')
    denied = perms.get('not_granted')
    if not isinstance(granted, list):
        errors.append('contract.permissions.granted: expected a list')
        granted = []
    if not isinstance(denied, list):
        errors.append('contract.permissions.not_granted: expected a list')
        denied = []
    for name, path in ((granted, 'granted'), (denied, 'not_granted')):
        for cap in name:
            if cap not in CAPABILITIES:
                errors.append('contract.permissions.%s: unsupported '
                              'capability %r - the closed set is: %s' %
                              (path, cap, ', '.join(CAPABILITIES)))
        if len(set(map(str, name))) != len(name):
            errors.append('contract.permissions.%s: duplicate entries' % path)
    overlap = sorted(set(granted) & set(denied))
    if overlap:
        errors.append('contract.permissions: %s appear%s in BOTH granted and '
                      'not_granted - the lists must be disjoint' %
                      (', '.join(map(repr, overlap)),
                       's' if len(overlap) > 1 else ''))


def _dependencies_errors(doc, errors):
    deps = doc.get('dependencies')
    if not isinstance(deps, list):
        errors.append('contract.dependencies: expected a list')
        return
    for i, dep in enumerate(deps):
        path = 'contract.dependencies[%d]' % i
        if not isinstance(dep, dict):
            errors.append('%s: expected an object' % path)
            continue
        _closed(dep, {'name', 'kind', 'detail'}, path, errors)
        _field(dep, 'name', 'str', path, errors)
        kind = _field(dep, 'kind', 'str?', path, errors)
        if kind is not None and kind not in ('external_system', 'credential',
                                             'pinned_input'):
            errors.append('%s.kind: expected external_system/credential/'
                          'pinned_input' % path)
        _field(dep, 'detail', 'str', path, errors)


def _envelope_errors(doc, errors):
    envelope = doc.get('resource_envelope')
    if not isinstance(envelope, dict):
        errors.append('contract.resource_envelope: expected an object')
        return
    _closed(envelope, {'limits'}, 'contract.resource_envelope', errors)
    limits = envelope.get('limits')
    if not isinstance(limits, list) or not limits:
        errors.append('contract.resource_envelope.limits: expected a '
                      'non-empty list')
        return
    seen = set()
    for i, limit in enumerate(limits):
        path = 'contract.resource_envelope.limits[%d]' % i
        if not isinstance(limit, dict):
            errors.append('%s: expected an object' % path)
            continue
        _closed(limit, {'id', 'limit', 'unit', 'enforcement',
                        'metering_source', 'reserve'}, path, errors)
        lid = _field(limit, 'id', 'str?', path, errors)
        if lid is not None:
            if not LIMIT_ID.match(lid):
                errors.append('%s.id: expected a lowercase snake_case id' %
                              path)
            elif lid in seen:
                errors.append('%s.id: duplicate limit id %r' % (path, lid))
            else:
                seen.add(lid)
        # Malformed resource values are refused with the id named (A5).
        value = limit.get('limit')
        if not _is_num(value) or value < 0:
            errors.append('%s.limit (id %r): expected a number >= 0 (got '
                          '%r)' % (path, lid, value))
        _field(limit, 'unit', 'str', path, errors)
        if 'reserve' in limit:
            reserve = limit['reserve']
            if not _is_num(reserve) or reserve < 0:
                errors.append('%s.reserve (id %r): expected a number >= 0 '
                              '(got %r)' % (path, lid, reserve))
            elif _is_num(value) and reserve > value:
                errors.append('%s.reserve (id %r): reserve %s exceeds the '
                              'limit %s - a reserve larger than its limit '
                              'can never dispatch and is refused at '
                              'declaration (section 8)' %
                              (path, lid, reserve, value))
        enforcement = _field(limit, 'enforcement', 'str?', path, errors)
        if enforcement is not None and enforcement not in ('enforced',
                                                           'advisory'):
            errors.append('%s.enforcement: expected enforced/advisory' %
                          path)
        if enforcement == 'enforced' and not limit.get('metering_source'):
            errors.append('%s: an ENFORCED limit must name its metering '
                          'source - a host adapter reading real spend '
                          '(A5); asserted samples are advisory-only' % path)


def _scheduling_errors(doc, errors):
    """RFC section 5: caps and handoff conditions are CONTRACT-declared.

    The whole block is optional: an absent field means the deterministic
    core runs its shipped finite default (never unlimited), and a plan can
    declare tighter or looser bounds per plan. All fields are advisory to
    the model, binding on :mod:`scheduler` (the authorization core).
    """
    if 'scheduling' not in doc:
        return
    sched = doc.get('scheduling')
    if not isinstance(sched, dict):
        errors.append('contract.scheduling: expected an object')
        return
    path = 'contract.scheduling'
    _closed(sched, {'starvation_threshold_events',
                    'max_adaptations_per_task', 'max_retries_per_gate',
                    'handoff'}, path, errors)
    thresholds = (('starvation_threshold_events', 1),
                  ('max_adaptations_per_task', 0),
                  ('max_retries_per_gate', 0))
    for key, floor in thresholds:
        if key in sched:
            value = sched[key]
            if not _is_int(value) or value < floor:
                errors.append('%s.%s: expected an integer >= %d (got %r)'
                              % (path, key, floor, value))
    if 'handoff' in sched:
        handoff = sched['handoff']
        hpath = path + '.handoff'
        if not isinstance(handoff, dict):
            errors.append('%s: expected an object' % hpath)
        else:
            _closed(handoff, {'fresh_context', 'cross_host_resume'}, hpath,
                    errors)
            for key in ('fresh_context', 'cross_host_resume'):
                if key in handoff and (not isinstance(handoff[key], str) or
                                       not handoff[key].strip()):
                    errors.append('%s.%s: expected a non-empty condition '
                                  'string' % (hpath, key))


def _tasks_errors(doc, criteria_ids, errors, v7=False):
    tasks = doc.get('tasks')
    if not isinstance(tasks, list) or not tasks:
        errors.append('contract.tasks: expected a non-empty list')
        return
    by_id = {}
    for i, task in enumerate(tasks):
        path = 'contract.tasks[%d]' % i
        if not isinstance(task, dict):
            errors.append('%s: expected an object' % path)
            continue
        known = {'id', 'title', 'prerequisites', 'touched_surface',
                 'gate_intent'}
        if v7:
            # V7_CONTRACT.md section 2: the create-time marker that makes a
            # task eligible for delegation (never inferred at execution).
            known = known | {'parallel_safe'}
            if 'parallel_safe' in task and \
                    not isinstance(task['parallel_safe'], bool):
                errors.append('%s.parallel_safe: expected a boolean' % path)
        _closed(task, known, path, errors)
        tid = _field(task, 'id', 'str?', path, errors)
        if tid is not None:
            if not ID_TASK.match(tid):
                errors.append("%s.id: expected a 'T-<slug>' stable id" % path)
            elif tid in by_id:
                errors.append('%s.id: duplicate task id %r - ids are stable '
                              'and survive splits/reorders' % (path, tid))
            else:
                by_id[tid] = task
        _field(task, 'title', 'str', path, errors)
        prereqs = task.get('prerequisites')
        if not isinstance(prereqs, list):
            errors.append('%s.prerequisites: expected a list' % path)
        else:
            for ref in prereqs:
                if not isinstance(ref, str) or not ID_TASK.match(ref):
                    errors.append('%s.prerequisites: expected T-* ids, got '
                                  '%r' % (path, ref))
            if len(set(map(str, prereqs))) != len(prereqs):
                errors.append('%s.prerequisites: duplicate entries' % path)
        if 'touched_surface' not in task or not task['touched_surface']:
            errors.append('%s.touched_surface: expected a non-empty list - '
                          'every task declares the surface it touches' % path)
        else:
            _str_list(task['touched_surface'], path + '.touched_surface',
                      errors)
        intent = task.get('gate_intent')
        if not isinstance(intent, list):
            errors.append('%s.gate_intent: expected a list' % path)
        else:
            for j, gi in enumerate(intent):
                gpath = '%s.gate_intent[%d]' % (path, j)
                if not isinstance(gi, dict):
                    errors.append('%s: expected an object' % gpath)
                    continue
                _closed(gi, {'criterion', 'check'}, gpath, errors)
                ref = _field(gi, 'criterion', 'str?', gpath, errors)
                if ref is not None:
                    if not ID_CRITERION.match(ref):
                        errors.append('%s.criterion: expected an AC-* id' %
                                      gpath)
                    elif criteria_ids is not None and ref not in criteria_ids:
                        errors.append('%s.criterion: references unknown '
                                      'criterion %r (dangling gate intent)' %
                                      (gpath, ref))
                _field(gi, 'check', 'str', gpath, errors)
    # Graph integrity: dangling references and cycles are invalid graphs.
    for tid, task in by_id.items():
        for ref in task.get('prerequisites', []) or []:
            if isinstance(ref, str) and ID_TASK.match(ref) and \
                    ref not in by_id:
                errors.append('contract.tasks: task %s lists prerequisite %s '
                              'which does not exist (dangling reference)' %
                              (tid, ref))
    for cycle in _find_cycles(by_id):
        errors.append('contract.tasks: prerequisite cycle detected: %s - '
                      'the task graph must be a DAG' % ' -> '.join(cycle))


def _find_cycles(by_id):
    """Return one cycle path per strongly-connected culprit (iterative DFS)."""
    cycles = []
    state = {}  # tid -> 1 visiting, 2 done
    for root in by_id:
        if state.get(root):
            continue
        stack = [(root, iter([p for p in (by_id[root].get('prerequisites')
                                          or []) if p in by_id]))]
        state[root] = 1
        path = [root]
        while stack:
            node, children = stack[-1]
            advanced = False
            for child in children:
                if state.get(child) == 1:
                    idx = path.index(child)
                    cycles.append(path[idx:] + [child])
                elif not state.get(child):
                    state[child] = 1
                    path.append(child)
                    stack.append((child, iter(
                        [p for p in (by_id[child].get('prerequisites') or [])
                         if p in by_id])))
                    advanced = True
                    break
            if not advanced:
                state[node] = 2
                stack.pop()
                path.pop()
    return cycles


# ----------------------------------------------------------------- journal

def journal_event_errors(event, contract=None):
    """All validation errors for one journal event object."""
    errors = []
    if not isinstance(event, dict):
        return ['journal event: expected a JSON object']
    event_url = event.get('schema')
    expected = journal_url_for(contract) if contract is not None else None
    if event_url not in JOURNAL_GENERATIONS or \
            (expected is not None and event_url != expected):
        errors.append("event.schema: expected %r, found %r - mixed-era "
                      'records are refused; older plans keep their own '
                      'tooling (section 9.1)' %
                      (expected or JOURNAL_SCHEMA_URL, event_url))
        return errors
    etype = event.get('type')
    catalog = JOURNAL_EVENT_TYPES_V7 if \
        JOURNAL_GENERATIONS[event_url] == 'v7' else JOURNAL_EVENT_TYPES
    if etype not in catalog:
        errors.append('event.type: unknown event type %r (closed catalog: '
                      '%s)' % (etype, ', '.join(catalog)))
        return errors
    seq = event.get('seq')
    if not _is_int(seq) or seq < 1:
        errors.append('event.seq: expected an integer >= 1')
    if not isinstance(event.get('ts'), str) or \
            not DATETIME.match(event['ts']):
        errors.append('event.ts: expected an RFC 3339 timestamp (the '
                      "scheduler's clock, A11)")
    if not ID_PLAN.match(str(event.get('plan'))):
        errors.append('event.plan: expected a PLAN_* identifier')
    _field(event, 'contract_id', 'hex64', 'event', errors)
    actor = event.get('actor')
    if not isinstance(actor, dict):
        errors.append('event.actor: expected an object')
        actor = {}
    else:
        _closed(actor, {'kind', 'identity'}, 'event.actor', errors)
        if actor.get('kind') not in ('helper', 'agent', 'host_adapter',
                                     'human'):
            errors.append('event.actor.kind: expected helper/agent/'
                          'host_adapter/human')
        ident = actor.get('identity')
        if not isinstance(ident, str) or not ident.strip() or \
                len(ident) > 100:
            errors.append('event.actor.identity: expected a non-empty '
                          'string (<= 100 chars)')
    if 'note' in event and (not isinstance(event['note'], str) or
                            len(event['note']) > 500):
        errors.append('event.note: expected a string <= 500 chars')
    if errors:
        return errors
    if contract is not None:
        if event.get('plan') != contract.get('plan'):
            errors.append('event.plan: %s does not match the contract plan '
                          '%s - a journal belongs to one plan' %
                          (event.get('plan'), contract.get('plan')))
    handler = _EVENT_VALIDATORS[etype]
    if handler is _v_gate_run:
        handler(event, errors, contract)
    else:
        handler(event, errors)
    _trust_rules(event, errors)
    return errors


def _trust_rules(event, errors):
    """Section 4.5 / A1: observed requires a shipped executor; pointers."""
    if event.get('type') not in EVIDENCE_TYPES:
        if 'trust' in event:
            errors.append('event: trust labels exist only on evidence types '
                          '(%s), not on %r' % (', '.join(EVIDENCE_TYPES),
                                               event.get('type')))
        return
    trust = event.get('trust')
    if trust not in TRUST_LABELS:
        errors.append('event.trust: expected one of %s' %
                      '/'.join(TRUST_LABELS))
        return
    if trust in ('observed', 'imported') and not event.get('evidence_path'):
        errors.append('event.evidence_path: required for trust=%s - '
                      'evidence must cite a recoverable pointer' % trust)
    if trust == 'observed' and \
            event.get('actor', {}).get('kind') not in EXECUTING_ACTORS:
        errors.append(
            'event.trust: observed requires a shipped helper or host '
            'adapter to have EXECUTED the check, but actor.kind=%r only '
            'mediates a write - record it as asserted with the mediation '
            'named (A1)' % event.get('actor', {}).get('kind'))


def _v_task_start(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'task', 'fingerprint'}, 'event', errors)
    tid = _field(event, 'task', 'str?', 'event', errors)
    if tid is not None and not ID_TASK.match(tid):
        errors.append('event.task: expected a T-* id')
    # D2-6: the starting fingerprint captured at task start - the state a
    # control pair's old leg materializes. Optional: a raw append records
    # none, and a control on a fingerprint-less attempt is honestly
    # unavailable, never guessed.
    if 'fingerprint' in event:
        fp = event['fingerprint']
        fpath = 'event.fingerprint'
        if not isinstance(fp, dict):
            errors.append('%s: expected an object' % fpath)
        else:
            _closed(fp, {'revision', 'dirty'}, fpath, errors)
            _field(fp, 'revision', 'str', fpath, errors)
            if not isinstance(fp.get('dirty'), str):
                errors.append('%s.dirty: expected a string (empty means '
                              'clean)' % fpath)


def _v_approval(event, errors):
    # D3-7: the materialization-time approval record the guarded writer's
    # first-task-start refusal scans for by type.
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'authority', 'mechanism',
                    'plan_digest'}, 'event', errors)
    _field(event, 'authority', 'str', 'event', errors)
    mechanism = _field(event, 'mechanism', 'str?', 'event', errors)
    if mechanism is not None and mechanism not in MECHANISMS:
        errors.append('event.mechanism: unknown value %r - exactly %s exist '
                      '(D3-2)' % (mechanism, ' and '.join(MECHANISMS)))
    _field(event, 'plan_digest', 'hex64', 'event', errors)


def _v_gate_run(event, errors, contract=None):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'command', 'cwd', 'env',
                    'timeout_seconds', 'exit_code', 'trust',
                    'evidence_path', 'criterion', 'task'}, 'event', errors)
    _field(event, 'command', 'str', 'event', errors)
    _field(event, 'cwd', 'str', 'event', errors)
    if 'env' in event and not isinstance(event['env'], dict):
        errors.append('event.env: expected an object of declared variables')
    timeout = event.get('timeout_seconds')
    if not _is_num(timeout) or timeout <= 0:
        errors.append('event.timeout_seconds: expected a number > 0')
    if not _is_int(event.get('exit_code')):
        errors.append('event.exit_code: expected an integer')
    ref = event.get('criterion')
    if not isinstance(ref, str) or not ID_CRITERION.match(ref):
        errors.append('event.criterion: expected an AC-* id')
    tid = _field(event, 'task', 'str?', 'event', errors)
    if tid is not None and not ID_TASK.match(tid):
        errors.append('event.task: expected a T-* id')
    # M5: the record must land inside the contract's declared intent —
    # task and criterion are bound at execution, never chosen after
    if contract is not None and tid is not None and ref is not None:
        intents = None
        for task in contract.get('tasks', []):
            if task.get('id') == tid:
                intents = {i.get('criterion')
                           for i in task.get('gate_intent', [])}
                break
        if intents is None:
            errors.append('event.task: %r is not a task of this contract' % tid)
        elif ref not in intents:
            errors.append(
                'event.criterion: %r is not declared in task %s '
                'gate_intent - a gate run is bound to the declared '
                'intent, not linked after the fact' % (ref, tid))


def _v_observation(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'statement', 'trust',
                    'evidence_path'}, 'event', errors)
    _field(event, 'statement', 'str', 'event', errors)


def _v_adaptation(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'kind', 'trigger_observation',
                    'evidence_artifact', 'hypothesis', 'action', 'rationale',
                    'affected_tasks', 'affected_criteria', 'authority',
                    'evidence_invalidated', 'evidence_preserved',
                    'resource_impact', 'decision', 'reason'}, 'event',
            errors)
    kind = event.get('kind')
    if kind not in ADAPTATION_KINDS:
        errors.append('event.kind: %r is outside the closed section-3.3 '
                      'enumeration (%s) - the authorization core refuses it'
                      % (kind, ', '.join(ADAPTATION_KINDS)))
    trigger = event.get('trigger_observation')
    if not _is_int(trigger) or trigger < 1:
        errors.append('event.trigger_observation: expected a journal seq '
                      '>= 1')
    for key in ('evidence_artifact', 'hypothesis', 'action', 'rationale',
                'authority'):
        _field(event, key, 'str', 'event', errors)
    for key in ('affected_tasks', 'affected_criteria', 'evidence_invalidated',
                'evidence_preserved'):
        if not isinstance(event.get(key), list):
            errors.append('event.%s: expected a list' % key)
    for ref in event.get('affected_tasks') or []:
        if not isinstance(ref, str) or not ID_TASK.match(ref):
            errors.append('event.affected_tasks: expected T-* ids, got %r' %
                          ref)
    for ref in event.get('affected_criteria') or []:
        if not isinstance(ref, str) or not ID_CRITERION.match(ref):
            errors.append('event.affected_criteria: expected AC-* ids, got '
                          '%r' % ref)
    if 'resource_impact' in event:
        impact = event['resource_impact']
        ipath = 'event.resource_impact'
        if not isinstance(impact, dict):
            errors.append('%s: expected an object' % ipath)
        else:
            _closed(impact, {'declared', 'unit'}, ipath, errors)
            declared = impact.get('declared')
            if not _is_num(declared) or declared < 0:
                errors.append('%s.declared: expected a number >= 0 (the '
                              'D2-9a pending contribution)' % ipath)
            _field(impact, 'unit', 'str', ipath, errors)
    decision = event.get('decision')
    if decision not in ('authorized', 'refused'):
        errors.append('event.decision: expected authorized/refused')
    elif decision == 'refused' and not event.get('reason'):
        errors.append('event.reason: required when decision=refused - every '
                      'refusal carries its reason (section 5)')


def _v_amendment(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'original_criterion', 'observed_finding',
                    'disposition', 'revised_criterion', 'reason',
                    'authority', 'affected_tasks', 'evidence_invalidated',
                    'evidence_preserved'}, 'event', errors)
    for key in ('original_criterion', 'observed_finding', 'disposition',
                'revised_criterion', 'reason', 'authority'):
        _field(event, key, 'str', 'event', errors)
    for key in ('affected_tasks', 'evidence_invalidated',
                'evidence_preserved'):
        if not isinstance(event.get(key), list):
            errors.append('event.%s: expected a list' % key)
    for ref in event.get('affected_tasks') or []:
        if not isinstance(ref, str) or not ID_TASK.match(ref):
            errors.append('event.affected_tasks: expected T-* ids, got %r' %
                          ref)


def _v_intervention(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'category', 'description', 'question',
                    'resolution'}, 'event', errors)
    category = event.get('category')
    if category not in INTERVENTION_CATEGORIES:
        errors.append('event.category: %r is outside the closed taxonomy '
                      '(%s; TELEMETRY.md is the source of record, D3-11)' %
                      (category, ', '.join(INTERVENTION_CATEGORIES)))
    _field(event, 'description', 'str', 'event', errors)
    _field(event, 'question', 'str', 'event', errors)
    _field(event, 'resolution', 'str', 'event', errors, optional=True)


def _v_resource_sample(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'source', 'limit_id', 'value', 'unit',
                    'trust', 'evidence_path'}, 'event', errors)
    _field(event, 'source', 'str', 'event', errors)
    lid = event.get('limit_id')
    if lid is not None and (not isinstance(lid, str) or
                            not LIMIT_ID.match(lid)):
        errors.append('event.limit_id: expected a lowercase snake_case id')
    value = event.get('value')
    if not _is_num(value) or value < 0:
        errors.append('event.value: expected a number >= 0 (missing data is '
                      'exposed as missing, never imputed or zero-filled)')
    _field(event, 'unit', 'str', 'event', errors)


def _v_control_pair(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'criterion', 'check_artifacts',
                    'starting_fingerprint', 'old_leg', 'new_leg', 'verdict',
                    'trust', 'evidence_path'}, 'event', errors)
    ref = event.get('criterion')
    if not isinstance(ref, str) or not ID_CRITERION.match(ref):
        errors.append('event.criterion: expected an AC-* id')
    # D3-4: the declaration is the whitelist - exactly these files travel.
    if not _str_list(event.get('check_artifacts'), 'event.check_artifacts',
                     errors, minimum=1):
        errors.append('event.check_artifacts: a control pair must declare '
                      'its check artifact paths (D3-4)')
    fp = event.get('starting_fingerprint')
    dirty = None
    if not isinstance(fp, dict):
        errors.append('event.starting_fingerprint: expected an object')
    else:
        _closed(fp, {'revision', 'dirty'}, 'event.starting_fingerprint',
                errors)
        _field(fp, 'revision', 'str', 'event.starting_fingerprint', errors)
        if not isinstance(fp.get('dirty'), str):
            errors.append('event.starting_fingerprint.dirty: expected a '
                          'string (empty means clean)')
        else:
            dirty = fp['dirty']
    old = event.get('old_leg')
    old_available = None
    old_outcome = None
    if not isinstance(old, dict):
        errors.append('event.old_leg: expected an object')
    else:
        _closed(old, {'available', 'outcome', 'log'},
                'event.old_leg', errors)
        if type(old.get('available')) is not bool:
            errors.append('event.old_leg.available: expected a boolean')
        else:
            old_available = old['available']
            if old_available:
                if old.get('outcome') not in ('PASS', 'FAIL'):
                    errors.append('event.old_leg.outcome: required and must '
                                  'be PASS/FAIL when available=true')
                else:
                    old_outcome = old['outcome']
            elif 'outcome' in old:
                errors.append('event.old_leg.outcome: an unavailable leg '
                              'carries NO outcome - never a synthesized '
                              'old-tree result')
    new = event.get('new_leg')
    new_outcome = None
    if not isinstance(new, dict):
        errors.append('event.new_leg: expected an object')
    else:
        _closed(new, {'outcome', 'log'}, 'event.new_leg', errors)
        if new.get('outcome') not in ('PASS', 'FAIL'):
            errors.append('event.new_leg.outcome: expected PASS/FAIL')
        else:
            new_outcome = new['outcome']
        _field(new, 'log', 'str', 'event.new_leg', errors)
    verdict = event.get('verdict')
    if verdict not in ('discriminating', 'non_discriminating',
                       'control_unavailable'):
        errors.append('event.verdict: expected discriminating/'
                      'non_discriminating/control_unavailable')
    elif old_available is not None and new_outcome is not None:
        if dirty:
            expected = 'control_unavailable'
            why = ('a non-empty dirty component means the old leg cannot be '
                   'faithfully materialized (D3-3)')
        elif not old_available:
            expected = 'control_unavailable'
            why = 'the old leg is unavailable'
        elif old_outcome == 'FAIL' and new_outcome == 'PASS':
            expected = 'discriminating'
            why = '(old FAIL, new PASS) is the only discriminating pair'
        else:
            expected = 'non_discriminating'
            why = ('only (old FAIL, new PASS) discriminates; this pair is '
                   'recorded non-discriminating and never rounded up '
                   '(A6/U2)')
        if verdict != expected:
            errors.append('event.verdict: %r contradicts the legs (%s old / '
                          '%s new, dirty=%r) - expected %r: %s' %
                          (verdict, old_outcome, new_outcome, bool(dirty),
                           expected, why))


def _v_selection(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'task', 'priority_boost', 'aging'},
            'event', errors)
    tid = _field(event, 'task', 'str?', 'event', errors)
    if tid is not None and not ID_TASK.match(tid):
        errors.append('event.task: expected a T-* id')
    if type(event.get('priority_boost')) is not bool:
        errors.append('event.priority_boost: expected a boolean')
    elif event['priority_boost'] and 'aging' not in event:
        errors.append('event.aging: required when priority_boost=true - the '
                      'recorded boost names waiting_since_seq and the '
                      'threshold that fired (A11)')
    if 'aging' in event:
        aging = event['aging']
        apath = 'event.aging'
        if not isinstance(aging, dict):
            errors.append('%s: expected an object' % apath)
        else:
            _closed(aging, {'waiting_since_seq', 'threshold'}, apath,
                    errors)
            since = aging.get('waiting_since_seq')
            if not _is_int(since) or since < 1:
                errors.append('%s.waiting_since_seq: expected a journal seq '
                              '>= 1' % apath)
            _field(aging, 'threshold', 'str', apath, errors)


def _v_refusal(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'subject', 'stage', 'reason',
                    'proposal'}, 'event', errors)
    _field(event, 'subject', 'str', 'event', errors)
    stage = event.get('stage')
    if stage not in ('task_start', 'authorize', 'dispatch', 'gate'):
        errors.append('event.stage: expected task_start/authorize/dispatch/'
                      'gate')
    _field(event, 'reason', 'str', 'event', errors)
    if 'proposal' in event and (not _is_int(event['proposal']) or
                                event['proposal'] < 1):
        errors.append('event.proposal: expected a journal seq >= 1')


def _v_view_render(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'view', 'snapshot_digest', 'digests'},
            'event', errors)
    _field(event, 'view', 'str', 'event', errors)
    _field(event, 'snapshot_digest', 'hex64', 'event', errors)
    # N3: the rendered-bytes digests let a later render detect a human
    # edit that carried no marker — shape-checked, content-verified by
    # the renderer against its own recomputation
    digests = event.get('digests')
    if 'digests' in event:
        if not isinstance(digests, dict) or not digests:
            errors.append('event.digests: expected a non-empty object of '
                          'view name -> sha256')
        else:
            for name, digest in digests.items():
                if not isinstance(name, str) or not name.strip():
                    errors.append('event.digests: view names must be '
                                  'non-empty strings')
                if not isinstance(digest, str) or not HEX64.match(digest):
                    errors.append('event.digests[%r]: expected a sha256 '
                                  'hex digest' % name)


def _v_reconciliation(event, errors):
    # D2-4: the authority is section-3.2 content, not a mechanism label.
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'trigger', 'editor', 'authority'},
            'event', errors)
    for key in ('trigger', 'editor', 'authority'):
        _field(event, key, 'str', 'event', errors)


def _v_journal_repair(event, errors):
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'byte_offset', 'cause'}, 'event',
            errors)
    offset = event.get('byte_offset')
    if not _is_int(offset) or offset < 0:
        errors.append('event.byte_offset: expected an integer >= 0')
    _field(event, 'cause', 'str', 'event', errors)


def _v_delegation(event, errors):
    """V7_CONTRACT.md section 3: one delegation state transition.

    Not an evidence type: it records what a delegate was asked and what it
    claims, never a check that ran. A delegate's result is `asserted` until
    the parent's runner observes it with a gate (the event carries no trust
    label and no closure ever reads it).
    """
    _closed(event, {'schema', 'type', 'seq', 'ts', 'plan', 'contract_id',
                    'actor', 'note', 'task', 'delegation_id', 'transport',
                    'via', 'kind', 'profile', 'target', 'worktree',
                    'prompt_digest', 'state', 'result_path',
                    'result_digest'}, 'event', errors)
    tid = _field(event, 'task', 'str?', 'event', errors)
    if tid is not None and not ID_TASK.match(tid):
        errors.append('event.task: expected a T-* id')
    did = _field(event, 'delegation_id', 'str?', 'event', errors)
    if did is not None and not ID_DELEGATION.match(did):
        errors.append('event.delegation_id: expected 1-64 of [A-Za-z0-9._-]')
    if event.get('transport') not in DELEGATION_TRANSPORTS:
        errors.append('event.transport: expected headless/interactive')
    via = _field(event, 'via', 'str?', 'event', errors)
    if via is not None and not ID_ADDON.match(via):
        errors.append('event.via: expected an addon key')
    state = event.get('state')
    if state not in DELEGATION_STATES:
        errors.append('event.state: expected one of %s' %
                      '/'.join(DELEGATION_STATES))
    for key in ('kind', 'profile', 'target'):
        if key in event:
            if not isinstance(event[key], str) or not event[key] or \
                    len(event[key]) > 200:
                errors.append('event.%s: expected a non-empty string '
                              '(<= 200 chars)' % key)
    if 'worktree' in event and event['worktree'] is not None and \
            (not isinstance(event['worktree'], str) or
             not event['worktree'] or len(event['worktree']) > 300):
        errors.append('event.worktree: expected a path string or null '
                      '(read-only delegate)')
    if state == 'launched' and 'prompt_digest' not in event:
        errors.append('event.prompt_digest: required on launch (the prompt '
                      'is recorded by digest before it is relied on)')
    for key in ('prompt_digest', 'result_digest'):
        if key in event and (not isinstance(event[key], str) or
                             not DIGEST.match(event[key])):
            errors.append('event.%s: expected sha256:<64 hex>' % key)
    if 'result_path' in event:
        rp = event['result_path']
        if not isinstance(rp, str) or not rp or rp.startswith('/') or \
                '..' in rp.split('/'):
            errors.append('event.result_path: expected a relative path '
                          'inside the plan or repository')
        if state not in ('completed', 'failed'):
            errors.append('event.result_path: only a completed or failed '
                          'delegation carries a result')
    if 'trust' in event or 'evidence_path' in event:
        errors.append('event: a delegation is not evidence - it carries no '
                      'trust label and no evidence_path (its result stays '
                      'asserted until the parent runner observes it)')


_EVENT_VALIDATORS = {
    'delegation': _v_delegation,
    'task_start': _v_task_start,
    'approval': _v_approval,
    'gate_run': _v_gate_run,
    'observation': _v_observation,
    'adaptation': _v_adaptation,
    'amendment': _v_amendment,
    'intervention': _v_intervention,
    'resource_sample': _v_resource_sample,
    'control_pair': _v_control_pair,
    'selection': _v_selection,
    'refusal': _v_refusal,
    'view_render': _v_view_render,
    'reconciliation': _v_reconciliation,
    'journal_repair': _v_journal_repair,
}


def journal_errors(events, contract=None):
    """Validate a parsed event sequence: per-event errors plus ordering.

    Ordering rule: ``seq`` strictly increases down the file. Contiguity is
    NOT required - rolls may retire events above snapshot-cited positions
    (A12), so gaps are legal history while regressions are corruption.
    """
    errors = []
    previous = 0
    for i, event in enumerate(events):
        for err in journal_event_errors(event, contract=contract):
            errors.append('journal line %d: %s' % (i + 1, err))
        seq = event.get('seq') if isinstance(event, dict) else None
        if isinstance(seq, int) and type(seq) is int:
            if seq <= previous:
                errors.append('journal line %d: seq %d follows %d - the '
                              'journal is append-only; positions never go '
                              'backwards' % (i + 1, seq, previous))
            previous = seq
    return errors


# ------------------------------------------------------------------ selftest

def _selftest_contract():
    return {
        'schema': CONTRACT_SCHEMA_URL,
        'spec_version': '6.0.0',
        'plan': 'PLAN_selftest_v6',
        'revision': 1,
        'created_at': '2026-09-26T00:00:00Z',
        'outcome': {
            'statement': 'Ship the bounded v6 core.',
            'success_definition': 'All criteria closed on accepted evidence.',
            'out_of_scope': ['v7 roadmap items'],
        },
        'acceptance': {'criteria': [{
            'id': 'AC-one',
            'statement': 'Contract validates.',
            'observable_check': 'validator exits 0 on the fixture',
            'accepted_evidence': ['observed'],
            'control': {'kind': 'regression',
                        'rationale': 'the pre-v6 failure mode'},
        }]},
        'invariants': [{'id': 'INV-closed-objects',
                        'statement': 'Records stay closed objects.'}],
        'scope': {
            'allowed_paths': ['skills/deepworkplan/'],
            'allowed_command_classes': ['true'],
            'forbidden_operations': ['force-push', 'publish'],
        },
        'authorization': {
            'mechanism': 'plan_authorship',
            'authority': 'session user sergio',
            'timestamp': '2026-09-26T00:00:00Z',
            'boundaries': 'this plan only; no publication',
            'consent_checkpoints': ['GO required before release'],
        },
        'permissions': {
            'granted': ['gate_command_exec', 'fs_write_repo_scope'],
            'not_granted': ['network_access', 'agent_delegation'],
        },
        'dependencies': [{'name': 'python3', 'kind': 'pinned_input',
                          'detail': '>= 3.9 stdlib only'}],
        'resource_envelope': {'limits': [
            {'id': 'spend_usd', 'limit': 4000, 'unit': 'USD',
             'enforcement': 'enforced',
             'metering_source': 'claude-adapter: usage.total_cost_usd'},
            {'id': 'wall_clock_h', 'limit': 12, 'unit': 'hours',
             'enforcement': 'advisory'},
        ]},
        'tasks': [{
            'id': 'T-implement',
            'title': 'Implement the validator',
            'prerequisites': [],
            'touched_surface': ['skills/deepworkplan/shared/'],
            'gate_intent': [{'criterion': 'AC-one',
                             'check': 'true'}],
        }],
    }


def _selftest_events(contract_id):
    base = {'schema': JOURNAL_SCHEMA_URL, 'seq': 1,
            'ts': '2026-09-26T00:00:01Z', 'plan': 'PLAN_selftest_v6',
            'contract_id': contract_id,
            'actor': {'kind': 'helper', 'identity': 'contract_v6 selftest'}}
    events = [
        dict(base, type='task_start', task='T-implement'),
        dict(base, type='approval', authority='session user sergio',
             mechanism='plan_authorship',
             plan_digest='a' * 64),
        dict(base, type='gate_run', command='bats v6-contract.bats',
             cwd='.', timeout_seconds=600, exit_code=0, trust='observed',
             evidence_path='analysis_results/gates/task11.log',
             task='T-implement', criterion='AC-one'),
        dict(base, type='observation', statement='suite green',
             trust='asserted'),
        dict(base, type='adaptation', kind='retry',
             trigger_observation=3, evidence_artifact='gates/x.log',
             hypothesis='flaky timing', action='rerun with fixed seed',
             rationale='deterministic re-run', affected_tasks=['T-implement'],
             affected_criteria=['AC-one'], authority='session user sergio',
             evidence_invalidated=[], evidence_preserved=['gates/x.log'],
             decision='refused', reason='retry cap reached'),
        dict(base, type='amendment',
             original_criterion='AC-one: validator exits 0',
             observed_finding='fixture drifted', disposition='revised',
             revised_criterion='AC-one: validator exits 0 on v6 fixture',
             reason='schema generation changed', authority='developer',
             affected_tasks=['T-implement'], evidence_invalidated=[],
             evidence_preserved=[]),
        dict(base, type='intervention', category='new_authority',
             description='spend above advisory line',
             question='authorize the overage?'),
        dict(base, type='resource_sample',
             source='claude-adapter: usage.total_cost_usd',
             limit_id='spend_usd', value=1.25, unit='USD',
             trust='observed', evidence_path='meters/r3.json'),
        dict(base, type='control_pair', criterion='AC-one',
             check_artifacts=['fixtures/v6/contract-minimal.json'],
             starting_fingerprint={'revision': 'HEAD', 'dirty': ''},
             old_leg={'available': True, 'outcome': 'FAIL',
                      'log': 'legs/old.log'},
             new_leg={'outcome': 'PASS', 'log': 'legs/new.log'},
             verdict='discriminating', trust='observed',
             evidence_path='legs/'),
        dict(base, type='selection', task='T-implement',
             priority_boost=True,
             aging={'waiting_since_seq': 2, 'threshold': '12h default'}),
        dict(base, type='refusal', subject='T-implement',
             stage='task_start',
             reason='no approval event cites the live contract_id'),
        dict(base, type='view_render', view='refusals-and-interventions',
             snapshot_digest='b' * 64),
        dict(base, type='reconciliation', trigger='human edit won',
             editor='PROGRESS.md by developer', authority='developer'),
        dict(base, type='journal_repair', byte_offset=0,
             cause='torn tail from crash'),
    ]
    for i, event in enumerate(events):
        event['seq'] = i + 1
    return events


def self_test():
    """In-memory positive/negative suite; returns (ok, details)."""
    failures = []
    contract = _selftest_contract()
    if contract_errors(contract):
        failures.append('baseline contract should be valid: %s' %
                        contract_errors(contract))
    cid = compute_contract_id(contract)
    stamped = dict(contract, contract_id=cid)
    if contract_errors(stamped):
        failures.append('identity-stamped contract should be valid: %s' %
                        contract_errors(stamped))
    bad_stamp = dict(stamped)
    bad_stamp['contract_id'] = 'c' * 64
    if not contract_errors(bad_stamp):
        failures.append('a mismatched contract_id must fail identity')
    sched = json.loads(json.dumps(contract))
    sched['scheduling'] = {
        'starvation_threshold_events': 25, 'max_adaptations_per_task': 2,
        'max_retries_per_gate': 1,
        'handoff': {'fresh_context': 'context corruption is observed',
                    'cross_host_resume': 'a handoff carries a contract'}}
    if contract_errors(sched):
        failures.append('a well-formed scheduling block should be valid: %s'
                        % contract_errors(sched))
    stamped_start = json.loads(json.dumps(_selftest_events(cid)))
    stamped_start[0]['fingerprint'] = {'revision': 'r0', 'dirty': ''}
    if journal_errors(stamped_start, contract=stamped):
        failures.append('task_start carrying a starting fingerprint should '
                        'be valid: %s' %
                        journal_errors(stamped_start, contract=stamped)[:2])
    events = _selftest_events(cid)
    journal = journal_errors(events, contract=stamped)
    if journal:
        failures.append('baseline event catalog should be valid: %s' %
                        journal[:3])
    # Every catalog type must have been exercised.
    seen_types = sorted(e['type'] for e in events)
    if seen_types != sorted(JOURNAL_EVENT_TYPES):
        failures.append('selftest must cover the full catalog')
    # Negative probes: each mutant must produce at least one error.
    probes = [0]

    def probe(label, mutate_contract=None, mutate_event=None):
        probes[0] += 1
        c = json.loads(json.dumps(stamped))
        if mutate_contract:
            mutate_contract(c)
            errs = contract_errors(c)
        else:
            es = json.loads(json.dumps(events))
            mutate_event(es)
            errs = journal_errors(es, contract=c)
        if not errs:
            failures.append('mutant %r should fail' % label)

    probe('extra top-level field',
          lambda c: c.update({'efficiency': {'tokens': 1}}))
    probe('wrong schema era',
          lambda c: c.update({'schema':
                              'https://deepworkplan.com/schema/plan-state/v5.json'}))
    probe('duplicate criterion id',
          lambda c: c['acceptance']['criteria'].append(
              dict(c['acceptance']['criteria'][0])))
    probe('dangling prerequisite',
          lambda c: c['tasks'][0]['prerequisites'].append('T-missing'))
    probe('prerequisite cycle',
          lambda c: (c['tasks'].append(dict(c['tasks'][0], id='T-second',
                                            prerequisites=['T-implement'])),
                     c['tasks'][0].update(prerequisites=['T-second'])))
    probe('dangling gate intent',
          lambda c: c['tasks'][0]['gate_intent'].append(
              {'criterion': 'AC-nope', 'check': 'x'}))
    probe('unsupported capability',
          lambda c: c['permissions']['granted'].append('time_travel'))
    probe('permission overlap',
          lambda c: c['permissions']['not_granted'].append(
              c['permissions']['granted'][0]))
    probe('third mechanism',
          lambda c: c['authorization'].update(mechanism='migration'))
    probe('malformed resource value',
          lambda c: c['resource_envelope']['limits'][0].update(limit=-1))
    probe('enforced limit without metering source',
          lambda c: c['resource_envelope']['limits'][0].pop(
              'metering_source'))
    probe('empty accepted evidence',
          lambda c: c['acceptance']['criteria'][0].update(
              accepted_evidence=[]))
    probe('journal: unknown event type',
          None, lambda es: es[0].update(type='time_travel'))
    probe('journal: task_start fingerprint with a non-string dirty',
          None, lambda es: es[0].update(
              fingerprint={'revision': 'r0', 'dirty': 7}))
    probe('journal: task_start fingerprint with an extra key',
          None, lambda es: es[0].update(
              fingerprint={'revision': 'r0', 'dirty': '',
                           'staged': 'yes'}))
    probe('journal: observed on a mediating agent actor',
          None, lambda es: es[2].update(
              actor={'kind': 'agent', 'identity': 'model'}))
    probe('journal: approval with third mechanism',
          None, lambda es: es[1].update(mechanism='migration'))
    probe('journal: intervention with open taxonomy',
          None, lambda es: es[6].update(category='vibes'))
    probe('journal: (PASS, PASS) rounded up to discriminating',
          None, lambda es: (es[8]['old_leg'].update(outcome='PASS'),
                            es[8].update(verdict='discriminating')))
    probe('journal: dirty fingerprint presented as available control',
          None, lambda es: es[8]['starting_fingerprint'].update(
              dirty='M src/x.py'))
    probe('journal: control pair without the artifact declaration',
          None, lambda es: es[8].pop('check_artifacts'))
    probe('zero starvation threshold',
          lambda c: c.update(scheduling={'starvation_threshold_events': 0}))
    probe('negative adaptation cap',
          lambda c: c.update(scheduling={'max_adaptations_per_task': -1}))
    probe('scheduling with an unknown field',
          lambda c: c.update(scheduling={'aggressiveness': 11}))
    probe('empty handoff condition',
          lambda c: c.update(scheduling={'handoff': {
              'fresh_context': '  '}}))
    probe('empty allowed_command_classes',
          lambda c: c['scope'].update(allowed_command_classes=[]))
    probe('journal: refused adaptation without a reason',
          None, lambda es: es[4].pop('reason'))
    probe('journal: adaptation carrying criterion content',
          None, lambda es: es[4].update(revised_criterion='AC-one: easier'))
    probe('journal: seq regression',
          None, lambda es: es[5].update(seq=2))
    # v7 generation (V7_CONTRACT.md): the superset validates; its additions
    # are refused under the v6 URLs; generations never mix.
    v7 = json.loads(json.dumps(contract))
    v7['schema'] = CONTRACT_SCHEMA_URL_V7
    v7['tasks'][0]['parallel_safe'] = True
    probes[0] += 1
    if contract_errors(v7):
        failures.append('a v7 contract with parallel_safe should be valid: %s'
                        % contract_errors(v7)[:1])
    probes[0] += 1
    v6_marked = json.loads(json.dumps(contract))
    v6_marked['tasks'][0]['parallel_safe'] = True
    if not contract_errors(v6_marked):
        failures.append('parallel_safe under the v6 URL must fail')
    v7_stamped = dict(v7, contract_id=compute_contract_id(v7))
    delegation = {'schema': JOURNAL_SCHEMA_URL_V7, 'type': 'delegation',
                  'seq': 1, 'ts': '2026-10-09T00:00:00Z',
                  'plan': v7['plan'], 'contract_id': v7_stamped['contract_id'],
                  'actor': {'kind': 'agent', 'identity': 'selftest'},
                  'task': v7['tasks'][0]['id'], 'delegation_id': 'd1',
                  'transport': 'headless', 'via': 'agentkit',
                  'state': 'launched', 'prompt_digest': 'sha256:' + 'a' * 64}
    probes[0] += 1
    if journal_event_errors(delegation, v7_stamped):
        failures.append('a v7 delegation event should be valid: %s'
                        % journal_event_errors(delegation, v7_stamped)[:1])
    for label, mutate, against in (
            ('delegation under the v6 journal URL',
             lambda e: e.update(schema=JOURNAL_SCHEMA_URL), None),
            ('v7 event under a v6 contract', lambda e: None, stamped),
            ('delegation claims trust', lambda e: e.update(trust='observed'),
             v7_stamped),
            ('launch without prompt digest',
             lambda e: e.pop('prompt_digest'), v7_stamped)):
        probes[0] += 1
        ev = dict(delegation)
        mutate(ev)
        if not journal_event_errors(ev, against):
            failures.append('mutant %r should fail' % label)
    return (not failures, failures, probes[0])


# ---------------------------------------------------------------------- CLI

def _read_json(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def _read_ndjson(path):
    events = []
    with open(path, encoding='utf-8') as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit('journal line %d does not parse: %s' %
                                 (lineno, exc))
    return events


def main(argv):
    usage = ('usage: contract_v6.py validate-contract FILE [--parent FILE] '
             '[--recorded] '
             '| validate-journal FILE [--contract FILE] | compute-id FILE | '
             'self-test')
    if any(arg in ('-h', '--help') for arg in argv):
        print(usage)
        print('  validate-contract: a revision > 1 needs every earlier revision '
              'as --parent FILE (e.g. contracts/contract.r1.json); WARN lines '
              'are advisories; --recorded reports the draft-only checks '
              '(closability, gate command classes) as WARN for a contract '
              'already materialized')
        return 0
    if not argv:
        print(usage)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == 'compute-id':
        if len(rest) != 1:
            print(usage)
            return 2
        print(compute_contract_id(_read_json(rest[0])))
        return 0
    if cmd == 'self-test':
        ok, failures, probes = self_test()
        for failure in failures:
            print('FAIL', failure)
        print('self-test: %s (%d mutant probes)' %
              ('OK' if ok else 'FAILED', probes))
        return 0 if ok else 1
    if cmd == 'validate-contract':
        if not rest:
            print(usage)
            return 2
        doc = _read_json(rest[0])
        parents = {}
        recorded = False
        i = 1
        while i < len(rest):
            if rest[i] == '--parent' and i + 1 < len(rest):
                parent = _read_json(rest[i + 1])
                parents[compute_contract_id(parent)] = parent
                i += 2
            elif rest[i] == '--recorded':
                recorded = True
                i += 1
            else:
                print(usage)
                return 2
        errors = contract_errors(doc, parents=parents)
        warnings = []
        if not errors:
            draft = closure_errors(doc, warnings) + gate_command_errors(doc)
            if recorded:
                # an already-materialized contract (e.g. a migration's
                # records-only synthesis): draft checks are advisories
                warnings += draft
            else:
                errors = draft
        for warning in warnings:
            print('WARN', warning)
        for err in errors:
            print('FAIL', err)
        if errors:
            return 1
        print('OK: %s contract valid (plan %s, revision %d, %d criteria, '
              '%d tasks, contract_id %s)' %
              (contract_generation(doc) or 'v6', doc.get('plan'),
               doc.get('revision'),
               len(doc.get('acceptance', {}).get('criteria', [])),
               len(doc.get('tasks', [])),
               doc.get('contract_id') or compute_contract_id(doc)))
        return 0
    if cmd == 'validate-journal':
        if not rest:
            print(usage)
            return 2
        events = _read_ndjson(rest[0])
        contract = None
        i = 1
        while i < len(rest):
            if rest[i] == '--contract' and i + 1 < len(rest):
                contract = _read_json(rest[i + 1])
                i += 2
            else:
                print(usage)
                return 2
        errors = journal_errors(events, contract=contract)
        for err in errors:
            print('FAIL', err)
        if errors:
            return 1
        counts = {}
        for event in events:
            counts[event.get('type') if isinstance(event, dict) else '?'] = \
                counts.get(event.get('type') if isinstance(event, dict)
                           else '?', 0) + 1
        print('OK: %d journal events valid (%s)' %
              (len(events), ', '.join('%s x%d' % (k, v) for k, v in
                                      sorted(counts.items()))))
        return 0
    print(usage)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
