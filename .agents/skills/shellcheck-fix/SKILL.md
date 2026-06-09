---
name: shellcheck-fix
description: Run shellcheck on the shipped/installer shell scripts and fix findings while preserving bash 3.2 compatibility. Use after editing any .sh file.
version: "1.0.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit
---

# Shellcheck Fix

## Goal

Keep `setup.sh`, `skills/deepworkplan/shared/context.sh`, and `scripts/*.sh`
shellcheck-clean and runnable on macOS's default bash 3.2.

## When to use

After editing any shell script, or when CI's shellcheck step fails.

## Steps

1. Run `shellcheck setup.sh skills/deepworkplan/shared/context.sh scripts/*.sh`.
2. Fix each finding. When resolving, keep the script **bash 3.2-safe**:
   - replace `mapfile`/`readarray` with `while IFS= read -r line; do …; done < <(cmd)`
   - replace `declare -A` with a restructured approach
   - replace `${var^^}`/`${var,,}` with `tr '[:lower:]' '[:upper:]'`
3. Confirm each script starts with `#!/usr/bin/env bash` then `set -euo pipefail`.
4. Re-run shellcheck until clean.
5. If `setup.sh` changed, smoke-test it: `HOME="$(mktemp -d)" ./setup.sh --host claude`.

## Validation

`shellcheck setup.sh skills/deepworkplan/shared/context.sh scripts/*.sh` exits 0,
and the installer smoke test still creates the expected symlinks.

## Notes

Do not change `setup.sh` public flags (`--host`, `--help`) or symlink names
without flagging a MAJOR bump. CI runs the smoke job on Ubuntu **and** macOS.
