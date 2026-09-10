#!/usr/bin/env python3
"""Dev-only validator for the split methodology guide (skills/deepworkplan/guide/).

Checks (exit 1 on any failure):
  1. every markdown link to guide/*.md anywhere in the installed pack resolves;
  2. GUIDE.md's section map lists every top-level section present in the guide files
     (fence-aware: '## ' inside code blocks is ignored);
  3. every non-index guide file carries the pointer header back to GUIDE.md;
  4. (optional) --baseline FILE: every non-blank line of FILE (a pre-split guide)
     still exists somewhere in the guide files — a line-level preservation gate.
Runtime files never depend on this script.
"""
import argparse, collections, pathlib, re, sys

def top_sections(text):
    out, fence = [], None
    for line in text.split("\n"):
        m = re.match(r"^(`{3,}|~{3,})", line)
        if m:
            fence = None if fence and line.startswith(fence) else (fence or m.group(1))
        elif fence is None and line.startswith("## "):
            out.append(line.strip())
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", default="skills/deepworkplan")
    ap.add_argument("--baseline")
    a = ap.parse_args()
    pack = pathlib.Path(a.pack); guide = pack / "guide"; problems = []

    # 1. links
    for md in pack.rglob("*.md"):
        for rel in re.findall(r"\]\(((?:\.\./)*(?:\./)?guide/[A-Za-z0-9_.-]+\.md)(?:#[^)]*)?\)", md.read_text()):
            if not (md.parent / rel).resolve().is_file():
                problems.append(f"broken link: {md} -> {rel}")

    # 2. section map coverage
    index = (guide / "GUIDE.md").read_text()
    listed = set(re.findall(r"^\| (## [^|]+?) \|", index, re.M))
    for f in sorted(guide.glob("*.md")):
        if f.name == "GUIDE.md":
            continue
        for h in top_sections(f.read_text()):
            if h.startswith("## ") and h not in listed and not any(h == l.strip() for l in listed):
                problems.append(f"section not in GUIDE.md map: {f.name}: {h}")
        # 3. pointer header
        if "[`GUIDE.md`](GUIDE.md)" not in f.read_text():
            problems.append(f"missing index pointer header: {f.name}")

    # 4. preservation
    if a.baseline:
        before = collections.Counter(l for l in pathlib.Path(a.baseline).read_text().split("\n") if l.strip())
        after = collections.Counter(l for f in guide.glob("*.md") for l in f.read_text().split("\n") if l.strip())
        for l, n in before.items():
            if after.get(l, 0) < n:
                problems.append(f"line lost from guide ({n - after.get(l, 0)}x): {l[:90]}")

    for p in problems:
        print("FAIL", p)
    print(f"{'OK' if not problems else 'FAILED'}: guide migration check ({len(problems)} problem(s))")
    return 1 if problems else 0

if __name__ == "__main__":
    sys.exit(main())
