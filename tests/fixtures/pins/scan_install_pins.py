#!/usr/bin/env python3
"""Every `skills add <source>` in the pack, workflows and scripts must be a
tag-pinned tree URL (https://github.com/OWNER/REPO/tree/vX.Y.Z, or a
placeholder/variable tag in templated lines). The skills CLI ignores the ref
of the OWNER/REPO@ref shorthand. Usage: scan_install_pins.py ROOT [TARGET...]
"""
import os, re, sys
root = sys.argv[1]
targets = sys.argv[2:] or ['skills', '.github/workflows', 'scripts']
ok = re.compile(r'^"?https://github\.com/([^ "/]+/[^ "/]+|\$\{?[A-Za-z_]+\}?|<[^>]+>)/tree/(v\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?|<[^>]+>|vX\.Y\.Z|\$\{?[A-Za-z_]+\}?)"?$')
explain = ('OWNER/REPO@', '<repo>@<tag>` printed')
bad = []
for t in targets:
    p = os.path.join(root, t)
    files = [p] if os.path.isfile(p) else [os.path.join(d, f) for d, _, fs in os.walk(p) for f in fs]
    for f in files:
        if f.endswith(('.png', '.svg')):
            continue
        try:
            text = open(f, encoding='utf-8').read()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if any(e in line for e in explain) or f.endswith('TRUST.md'):
                continue
            for m in re.finditer(r'skills add\s+("?[^\s`]+)', line):
                src = m.group(1)
                if src.startswith('-') or src in ('...', '…', 'calls', 'call', 'install', 'installs') or '/' not in src and '@' not in src:
                    continue
                if src.startswith('"') and not src.endswith('"'):
                    src = src.rstrip(')')
                if not ok.match(src.rstrip('`.,;)')):
                    bad.append('%s:%d: %s' % (os.path.relpath(f, root), n, src))
print('\n'.join(bad))
sys.exit(1 if bad else 0)
