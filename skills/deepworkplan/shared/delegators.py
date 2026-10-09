#!/usr/bin/env python3
"""Delegator drift report (field report F-23); read-only, stdlib only.

Onboarding writes thin command delegators (``.agents/commands/dwp-*.md`` and
friends) from the pack's ``onboard/command-templates/``. A repository may
adapt them on purpose, and an upgrade may ship new templates; neither is
visible unless someone compares. This helper compares, never writes:

    delegators.py check --repo DIR [--commands REL] [--skill-path REL] [--strict]

For every template it prints one line: ``OK <name>`` (byte-identical after
``<skill-path>`` is resolved), ``DRIFT <name>`` (differs: a deliberate
adaptation to keep, or a stale copy to refresh from the template — the
developer decides) or ``MISSING <name>`` (no delegator; onboarding offers
it). Exit 0, or 1 with ``--strict`` when anything drifted or is missing.
"""

import argparse
import os
import sys

sys.dont_write_bytecode = True

_HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.normpath(os.path.join(_HERE, '..', 'onboard',
                                          'command-templates'))


def check(repo, commands='.agents/commands', skill_path='.agents/skills',
          templates=TEMPLATES):
    """[(state, name)] for every template, in name order."""
    results = []
    for name in sorted(os.listdir(templates)):
        if not name.endswith('.md'):
            continue
        with open(os.path.join(templates, name), encoding='utf-8') as fh:
            expected = fh.read().replace('<skill-path>', skill_path)
        target = os.path.join(repo, commands, name)
        if not os.path.isfile(target):
            results.append(('MISSING', name))
            continue
        with open(target, encoding='utf-8', errors='replace') as fh:
            actual = fh.read()
        results.append(('OK' if actual == expected else 'DRIFT', name))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(prog='delegators.py',
                                     description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command')
    p = sub.add_parser('check')
    p.add_argument('--repo', required=True)
    p.add_argument('--commands', default='.agents/commands')
    p.add_argument('--skill-path', default='.agents/skills')
    p.add_argument('--strict', action='store_true')
    args = parser.parse_args(argv)
    if args.command != 'check':
        parser.print_help()
        return 2
    results = check(args.repo, args.commands, args.skill_path)
    for state, name in results:
        print('%-7s %s' % (state, name))
    flagged = [r for r in results if r[0] != 'OK']
    print('%d template(s): %d ok, %d drift, %d missing — a drift is an '
          'adaptation to keep or a stale copy to refresh; this report never '
          'writes' % (len(results), len(results) - len(flagged),
                      sum(r[0] == 'DRIFT' for r in results),
                      sum(r[0] == 'MISSING' for r in results)))
    return 1 if (args.strict and flagged) else 0


if __name__ == '__main__':
    sys.exit(main())
