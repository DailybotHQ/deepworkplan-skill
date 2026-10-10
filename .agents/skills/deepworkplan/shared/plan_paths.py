#!/usr/bin/env python3
"""Allocate and resolve flat Deep Work Plan directories.

The counter is local to one .dwp/plans directory. Existing unnumbered plans
remain in place and can still be selected by their exact names.
"""

import argparse
import fcntl
import os
import re


SLUG = re.compile(r'^[a-z0-9]+(?:_[a-z0-9]+){1,4}$')
NUMBERED = re.compile(r'^PLAN_([0-9]{3,})_([a-z0-9]+(?:_[a-z0-9]+){1,4})$')


class PlanPathError(Exception):
    pass


def plans(root):
    if not os.path.isdir(root):
        return []
    return [name for name in os.listdir(root)
            if name.startswith('PLAN_') and
            os.path.isdir(os.path.join(root, name))]


def number(name):
    match = NUMBERED.fullmatch(name)
    return int(match.group(1)) if match else None


def allocate(root, slug, max_words=5):
    """Claim a new folder and persist the next number under an exclusive lock."""
    if not SLUG.fullmatch(slug) or len(slug.split('_')) > max_words:
        raise PlanPathError('name must be 2-%d lowercase snake_case words' %
                            max_words)
    os.makedirs(root, exist_ok=True)
    lock_path = os.path.join(root, '.plan-id.lock')
    with open(lock_path, 'a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        counter_path = os.path.join(root, '.next-plan-id')
        try:
            with open(counter_path, encoding='ascii') as counter:
                stored = int(counter.read().strip())
            if stored < 1:
                raise ValueError('counter must be positive')
        except FileNotFoundError:
            stored = 1
        except ValueError as exc:
            raise PlanPathError('invalid .next-plan-id: %s' % exc)
        next_id = max([stored] + [number(name) + 1 for name in plans(root)
                                  if number(name) is not None])
        while True:
            name = 'PLAN_%03d_%s' % (next_id, slug)
            path = os.path.join(root, name)
            try:
                os.mkdir(path)
                break
            except FileExistsError:
                next_id += 1
        pending = counter_path + '.tmp.%d' % os.getpid()
        with open(pending, 'w', encoding='ascii') as counter:
            counter.write('%d\n' % (next_id + 1))
            counter.flush()
            os.fsync(counter.fileno())
        os.replace(pending, counter_path)
        return path


def resolve(root, selector):
    """Resolve an exact name, numeric id, unique slug, or latest plan."""
    names = plans(root)
    if not names:
        raise PlanPathError('no plans found in %s' % root)
    if selector in names:
        return os.path.join(root, selector)
    if selector.startswith('PLAN_'):
        selector = selector[5:]
    if selector == 'latest':
        numbered = [name for name in names if number(name) is not None]
        if numbered:
            highest = max(number(name) for name in numbered)
            matches = [name for name in numbered if number(name) == highest]
            if len(matches) != 1:
                raise PlanPathError('duplicate plan ID %d: %s' %
                                    (highest, ', '.join(sorted(matches))))
            winner = matches[0]
        else:
            winner = max(names, key=lambda name: os.path.getmtime(
                os.path.join(root, name)))
        return os.path.join(root, winner)
    if selector.isdecimal():
        matches = [name for name in names if number(name) == int(selector)]
    else:
        matches = [name for name in names if name == 'PLAN_' + selector or
                   (NUMBERED.fullmatch(name) and
                    NUMBERED.fullmatch(name).group(2) == selector)]
    if len(matches) == 1:
        return os.path.join(root, matches[0])
    if matches:
        raise PlanPathError('ambiguous plan %r: %s' %
                            (selector, ', '.join(sorted(matches))))
    raise PlanPathError('plan %r not found in %s' % (selector, root))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plans-dir', required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    allocation = sub.add_parser('allocate')
    allocation.add_argument('slug')
    allocation.add_argument('--max-words', type=int, choices=(4, 5), default=5)
    sub.add_parser('resolve').add_argument('selector')
    sub.add_parser('list')
    args = parser.parse_args()
    root = os.path.abspath(args.plans_dir)
    try:
        if args.command == 'allocate':
            print(allocate(root, args.slug, args.max_words))
        elif args.command == 'resolve':
            print(resolve(root, args.selector))
        else:
            for name in sorted(plans(root), key=lambda n: (number(n) is None,
                                                            number(n) or 0, n)):
                print(name)
    except PlanPathError as exc:
        parser.exit(2, '%s\n' % exc)


if __name__ == '__main__':
    main()
