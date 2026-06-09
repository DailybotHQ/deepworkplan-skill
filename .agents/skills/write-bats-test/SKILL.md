---
name: write-bats-test
description: Add or extend a bats-core test for the shell scripts, following the tests/ convention. Use when changing setup.sh or context.sh behavior.
version: "1.0.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
---

# Write Bats Test

## Goal

Cover new or changed shell behavior with a bats-core test that matches the
existing convention in `tests/`.

## When to use

When `setup.sh` or `skills/deepworkplan/shared/context.sh` gains or changes
behavior (a new flag, a new detection branch, a new output field).

## Steps

1. Read the existing tests to match style and helpers:
   `tests/setup-sh.bats`, `tests/context-sh.bats`.
2. Add `@test` cases for the new behavior. Use a throwaway `HOME`/temp dir for
   any filesystem effect so the suite never touches the developer's `~/.claude`.
3. Keep assertions on observable contract: emitted JSON fields from
   `context.sh`, created symlink names from `setup.sh`, exit codes.
4. Run `bats tests/` and iterate until green.

## Validation

`bats tests/` passes, including the new cases, and the suite leaves no artifacts
outside its temp dirs.

## Notes

Tests must run on bash 3.2. Prefer testing the **public contract** (flags,
symlink names, JSON keys) over internal implementation so refactors don't churn
the suite.
