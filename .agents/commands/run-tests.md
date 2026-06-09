---
description: Run the full local CI gate — frontmatter, shellcheck, bats, and the setup smoke test
---

# /run-tests

Reproduce locally what `.github/workflows/ci.yml` runs on every PR, in order.
Stop at the first failure and fix before moving on.

## What to do

1. **Frontmatter** — `python3 scripts/validate-frontmatter.py`
2. **Shell lint** — `shellcheck setup.sh skills/deepworkplan/shared/context.sh scripts/*.sh`
3. **Unit tests (bats-core)** — `bats tests/` (covers `context-sh.bats`, `setup-sh.bats`)
4. **Installer smoke test** against a throwaway HOME (never touches `~/.claude`):

   ```bash
   HOME="$(mktemp -d)" ./setup.sh --host claude
   ```

5. **context.sh smoke** — `bash skills/deepworkplan/shared/context.sh` (must emit single-line JSON)

All shell scripts must run on **bash 3.2** (macOS default): no `mapfile`,
no `declare -A`, no `${var^^}`. CI runs the smoke job on both `ubuntu-latest`
and `macos-latest` to enforce this — keep new shell code 3.2-safe.
