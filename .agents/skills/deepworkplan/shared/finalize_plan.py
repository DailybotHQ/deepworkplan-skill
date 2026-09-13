#!/usr/bin/env python3
"""Validate and publish a completed projection without inventing gate evidence.

Usage: python3 shared/finalize_plan.py PLAN --candidate STATE.json
The candidate contains only previously earned source/acceptance evidence.
Markdown is authored first; this helper never edits it or runs recorded commands.
An interrupted publication leaves .finalizing.json and requires explicit recovery.
"""
import argparse
import hashlib
import json
import re
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'verify'))
from plan_contract import check, field_content, unfenced
from state_contract import state_errors


def atomic(path, data):
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.'+path.name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def validate(plan, candidate):
    errors = state_errors(candidate, strict=True, plan_dir=plan)
    if candidate.get('status') != 'completed':
        errors.append('candidate is not completed')
    if errors:
        raise ValueError('; '.join(errors))
    result = check(plan, state_override=candidate, allow_finalizing=True)
    if result.failed:
        raise ValueError('; '.join(x for x in result.lines if not x.startswith(('+ ', '~ '))))
    readme = (plan/'README.md').read_text()
    for task in candidate['tasks']:
        loc = task.get('locator')
        if loc and loc['kind'] == 'inline':
            # Read only this inline record; a later task's disposition cannot mask it.
            # `re` is imported at module scope. A function-local `import re`
            # here once bound `re` as a local for the WHOLE function, so a
            # Full plan — every locator `kind: file`, this branch never taken —
            # hit an UnboundLocalError at the first `re` use further down, and
            # guarded publication was unreachable for Full plans entirely.
            match = re.search(r'(?m)^#{2,6} .*\{'+re.escape(loc['value'])+r'\}.*$', readme)
            if not match:
                raise ValueError('missing inline task record')
            tail = readme[match.end():]
            end = re.search(r'(?m)^## ', tail)
            body = tail[:end.start()] if end else tail
        else:
            body = (plan/(loc['value'] if loc else task['file'])).read_text()
        log = field_content(unfenced(body), 'Completion & Log') or field_content(unfenced(body), 'Completion log')
        # field_content stops at sublabels; dispositions are searched only in the task.
        # Name which condition failed: "requires a completed log" sent a reader
        # hunting through a log that was already complete when the real fault
        # was an unparseable heading.
        missing = []
        if not log:
            missing.append('no readable "Completion & Log" section — check the heading '
                           'is "## Completion & Log", optionally numbered and with a '
                           'parenthetical suffix, and nothing else on the line')
        elif re.search(r'(?im)^\s*(?:\*\*)?status(?:\*\*)?\s*:?\s*(?:\*\*)?\s*pending\b', log):
            # Match the STATUS LINE, not the word anywhere in the log. A
            # substring test refused a completed plan whose log said
            # "before appending either leg" — "appending" contains "pending" —
            # and reported that the log said pending, which was false. The
            # read-only checker already used a status-line rule
            # (plan_contract.log_status_mismatch); the finalizer now matches it.
            missing.append('its log\'s status line still says pending')
        if 'Skills disposition:' not in body:
            missing.append('no "Skills disposition:" line')
        if 'Documentation decision:' not in body:
            missing.append('no "Documentation decision:" line')
        if missing:
            raise ValueError(f'task {task["id"]} cannot be published: ' + '; '.join(missing))


def fingerprint(plan, candidate):
    """Relevant plan artifacts only; receipts do not fingerprint themselves."""
    files = {'README.md','PROGRESS.md','PROMPTS.md','manifest.json',
             'analysis_results/SECURITY_REVIEW.md','analysis_results/SKILLS_CANDIDATES.md'}
    for task in candidate['tasks']:
        loc = task.get('locator')
        if loc and loc['kind']=='file':
            files.add(loc['value'])
        elif not loc:
            files.add(task['file'])
    digest = hashlib.sha256()
    for name in sorted(files):
        path = plan/name
        digest.update(name.encode()+b'\0'+(path.read_bytes() if path.exists() else b'<absent>'))
    return digest.hexdigest()


def publish(plan, candidate, expected=None, recover=False, fault=None):
    """fault is an internal test callback, never a CLI/environment bypass."""
    plan = Path(plan)
    state_path = plan/'state.json'
    original = state_path.read_bytes()
    if expected and hashlib.sha256(original).hexdigest()!=expected:
        raise ValueError('stale state snapshot')
    marker = plan/'.finalizing.json'
    lock = plan/'state.json.lock'
    if marker.exists() and not recover:
        raise ValueError('interrupted finalization: inspect evidence and use --recover')
    lock.mkdir()  # Cooperating writers use the same lock as update-state.py.
    try:
        validate(plan, candidate)
        before = fingerprint(plan, candidate)
        payload = (json.dumps(candidate, indent=2, ensure_ascii=False)+'\n').encode()
        digest = hashlib.sha256(payload).hexdigest()
        atomic(marker, json.dumps({'candidate_sha256':digest,'artifacts_sha256':before}).encode())
        if fault:
            fault('before_publish')
        if state_path.read_bytes()!=original or fingerprint(plan,candidate)!=before:
            raise ValueError('plan changed during validation')
        atomic(state_path, payload)
        if fault:
            fault('after_publish')
        actual = json.loads(state_path.read_text())
        validate(plan, actual)
        if fingerprint(plan,actual)!=before or state_path.read_bytes()!=payload:
            raise ValueError('plan changed after publication')
        receipt = plan/'analysis_results/FINALIZATION.json'
        atomic(receipt, (json.dumps({'state_sha256':digest,'artifacts_sha256':before,
                                    'result':'verified'},indent=2)+'\n').encode())
        marker.unlink()
    finally:
        lock.rmdir()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--expected-sha256')
    parser.add_argument('--recover',action='store_true')
    args=parser.parse_args()
    try:
        publish(args.plan,json.loads(args.candidate.read_text()),args.expected_sha256,args.recover)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'finalize-plan: NOT COMPLETED: {exc}',file=sys.stderr)
        return 1
    print('Final artifacts verified; no recorded commands were executed.')
    return 0


if __name__=='__main__':
    sys.exit(main())
