#!/usr/bin/env python3
"""Verify that a frozen evaluation baseline snapshot has not changed.

Reads ``latest-v5.json`` next to this script, re-hashes every file in the
recorded snapshot directory, and compares the result against the snapshot's
``SHA256SUMS`` manifest and the recorded snapshot digest. Any missing, added,
modified, or symlinked file fails with a nonzero exit -- the comparator must
be byte-stable for the whole duration of a campaign.

Usage::

    python3 tests/evaluation/v6/baselines/verify_snapshot.py          # verify
    python3 tests/evaluation/v6/baselines/verify_snapshot.py --write  # re-freeze

``--baseline PATH`` points the checker at an alternative baseline record
(used by the regression suite to exercise synthetic snapshots without ever
touching the real frozen comparator).

``--write`` regenerates the manifest and prints the new digest; it is only for
a deliberate re-freeze (for example when the confirmation freeze resolves a
newer v5), never as a way to silence a mismatch.

Python 3.9+ stdlib only. Contributor/evaluation infrastructure; not part of
the shipped skill.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MANIFEST_NAME = "SHA256SUMS"


def repo_root() -> Path:
    """Locate the repository root (the directory owning the shipped pack and
    tests/) by walking up from this file, independent of its depth."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "skills" / "deepworkplan" / "SKILL.md").is_file() and (
            candidate / "tests"
        ).is_dir():
            return candidate
    print("FAIL cannot locate the repository root from this script", file=sys.stderr)
    raise SystemExit(2)


def load_baseline(baseline_path: Path) -> dict:
    try:
        return json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"FAIL cannot read baseline JSON {baseline_path}: {exc}", file=sys.stderr)
        raise SystemExit(2)


def collect_manifest_lines(snapshot: Path) -> list[str]:
    """Reproduce the freeze manifest: coreutils sha256sum output over every
    regular file except the manifest itself, LC_ALL=C (byte) sorted paths."""
    entries = []
    for path in sorted(snapshot.rglob("*")):
        if not path.is_symlink() and path.is_file():
            rel = path.relative_to(snapshot)
            if rel.as_posix() == MANIFEST_NAME:
                continue
            entries.append(rel.as_posix())
    # Byte-sort the "./"-prefixed paths exactly as `LC_ALL=C sort` did at freeze time.
    entries.sort(key=lambda p: ("./" + p).encode("utf-8"))
    lines = []
    for rel in entries:
        data = (snapshot / rel).read_bytes()
        lines.append(f"{hashlib.sha256(data).hexdigest()}  ./{rel}")
    return lines


def find_symlinks(snapshot: Path) -> list[str]:
    return [
        p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*") if p.is_symlink()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="regenerate SHA256SUMS and print the new digest (deliberate re-freeze only)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="alternative baseline JSON record (default: latest-v5.json next to this script)",
    )
    args = parser.parse_args()

    baseline_path = args.baseline or (
        Path(__file__).resolve().parent / "latest-v5.json"
    )
    baseline = load_baseline(baseline_path)

    snapshot_path = Path(baseline["snapshot"]["path"])
    snapshot = snapshot_path if snapshot_path.is_absolute() else repo_root() / snapshot_path
    if not snapshot.is_dir():
        print(f"FAIL snapshot directory missing: {snapshot}", file=sys.stderr)
        return 1

    links = find_symlinks(snapshot)
    if links:
        print(
            "FAIL live symlinks inside snapshot are prohibited: "
            + ", ".join(links),
            file=sys.stderr,
        )
        return 1

    lines = collect_manifest_lines(snapshot)
    manifest = snapshot / MANIFEST_NAME

    if args.write:
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    try:
        recorded = manifest.read_bytes()
    except OSError as exc:
        print(f"FAIL cannot read {MANIFEST_NAME}: {exc}", file=sys.stderr)
        return 1

    regenerated = ("\n".join(lines) + "\n").encode("utf-8")
    if regenerated != recorded:
        recorded_lines = set(recorded.decode("utf-8", "replace").splitlines())
        current_lines = set(regenerated.decode("utf-8", "replace").splitlines())
        changed = sorted(recorded_lines ^ current_lines)
        print(
            f"FAIL snapshot changed: {len(changed)} manifest line(s) differ "
            f"(+added/-missing):",
            file=sys.stderr,
        )
        for line in changed[:20]:
            print(f"  {line}", file=sys.stderr)
        return 1

    digest = hashlib.sha256(recorded).hexdigest()
    expected = baseline["snapshot"]["digest"]
    if digest != expected:
        print(
            f"FAIL snapshot digest {digest} does not match recorded {expected}",
            file=sys.stderr,
        )
        return 1

    # Semantic spot-check: the frozen pack must still be the recorded version.
    pack_skill = snapshot / baseline["pack"]["path"] / "SKILL.md"
    version = None
    for line in pack_skill.read_text(encoding="utf-8", errors="replace").splitlines()[:20]:
        if line.startswith("version:"):
            version = line.split(":", 1)[1].strip().strip('"')
            break
    if version != baseline["pack"]["version"]:
        print(
            f"FAIL frozen pack version {version!r} does not match recorded "
            f"{baseline['pack']['version']!r}",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK {baseline['comparator']} frozen: {baseline['tag']} @ "
        f"{baseline['peeled_commit'][:12]}, {len(lines)} files, digest "
        f"{digest[:16]}..."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
