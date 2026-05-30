#!/usr/bin/env python3
"""Validate the YAML frontmatter on every SKILL.md in this repo.

Run from the repo root:

    python3 scripts/validate-frontmatter.py

CI fails if any SKILL.md violates the conventions documented in AGENTS.md.

Rules enforced:
  - Every SKILL.md under skills/ has frontmatter delimited by --- markers
  - The frontmatter parses as valid YAML
  - `name` is present, kebab-case, starts with "deepworkplan"
  - `description` is present and non-empty
  - `version` is present, a quoted string, and SemVer-shaped
  - `documentation_url` is present (legacy `homepage` is rejected)
  - `user-invocable` is present and is a boolean
  - `allowed-tools` is present
  - `name: deepworkplan_*` (snake_case) is rejected explicitly with a hint
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is required. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(2)

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[\w.-]+)?(?:\+[\w.-]+)?$")
KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = REPO_ROOT / "skills"


def parse_frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ValueError(f"frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return data


def validate(path: Path, data: dict) -> list[str]:
    errors: list[str] = []

    name = data.get("name")
    if not name:
        errors.append("missing required field: name")
    elif not isinstance(name, str):
        errors.append(f"name must be a string, got {type(name).__name__}")
    elif "_" in name:
        errors.append(
            f"name '{name}' uses snake_case — must be kebab-case "
            f"(e.g. 'deepworkplan-{name.split('_', 1)[-1].replace('_', '-')}')"
        )
    elif not KEBAB_RE.match(name):
        errors.append(
            f"name '{name}' must be kebab-case "
            f"(lowercase letters, digits, hyphens; start with a letter)"
        )
    elif not name.startswith("deepworkplan"):
        errors.append(
            f"name '{name}' must start with 'deepworkplan' "
            f"so skills.sh registry entries are namespaced consistently"
        )

    description = data.get("description")
    if not description or not isinstance(description, str) or not description.strip():
        errors.append("missing or empty required field: description")

    version = data.get("version")
    if not version:
        errors.append("missing required field: version")
    elif not isinstance(version, str):
        errors.append(
            f"version must be a quoted string (got {type(version).__name__}); "
            f"add quotes: version: \"{version}\""
        )
    elif not SEMVER_RE.match(version):
        errors.append(f"version '{version}' is not SemVer-shaped (X.Y.Z)")

    if "homepage" in data:
        errors.append(
            "field 'homepage' is forbidden (some agent harnesses treat it as "
            "a re-fetch source). Rename to 'documentation_url'."
        )

    if "documentation_url" not in data:
        errors.append(
            "missing required field: documentation_url (replaces legacy 'homepage')"
        )

    if "user-invocable" not in data:
        errors.append("missing required field: user-invocable (true/false)")
    elif not isinstance(data.get("user-invocable"), bool):
        errors.append("user-invocable must be a boolean (true/false), not a string")

    if "allowed-tools" not in data:
        errors.append("missing required field: allowed-tools")

    return errors


def main() -> int:
    if not SKILLS_ROOT.is_dir():
        print(f"ERROR: skills/ directory not found at {SKILLS_ROOT}", file=sys.stderr)
        return 2

    skill_files = sorted(SKILLS_ROOT.rglob("SKILL.md"))
    if not skill_files:
        print(f"ERROR: no SKILL.md files found under {SKILLS_ROOT}", file=sys.stderr)
        return 2

    total_errors = 0
    for path in skill_files:
        rel = path.relative_to(REPO_ROOT)
        try:
            data = parse_frontmatter(path)
        except ValueError as exc:
            print(f"✗ {rel}: {exc}")
            total_errors += 1
            continue

        if data is None:
            print(f"✗ {rel}: missing or malformed frontmatter (no --- delimiters)")
            total_errors += 1
            continue

        errors = validate(path, data)
        if errors:
            print(f"✗ {rel}:")
            for err in errors:
                print(f"    - {err}")
            total_errors += len(errors)
        else:
            print(f"✓ {rel}")

    print()
    if total_errors:
        print(f"FAIL: {total_errors} frontmatter issue(s) across {len(skill_files)} SKILL.md file(s)")
        return 1

    print(f"OK: all {len(skill_files)} SKILL.md file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
