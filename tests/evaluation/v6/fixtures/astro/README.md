# Astro fixture (v6 evaluation lab)

Immutable initial seed for the Astro workload family: the official Astro blog
starter (`withastro/astro` `examples/blog` at tag `astro@7.3.5`, commit
`c2e01642af5f3919e4951b277a01d2de0ba1322f`, MIT) with a generic product
landing page overlaid and a zero-dependency check script added. Provenance,
overlays and commands: [`seed/manifest.json`](seed/manifest.json). Public
development cases and the mechanism taxonomy: [`CASES.md`](CASES.md).

This directory is fixture-local on purpose: the service and legacy fixtures
(Tasks 6, 7) carry their own local docs, and shared integration (Task 8) owns
anything cross-family. No shared index is edited here.

## What every arm gets

The same seed files, the same lockfile, the same commands (pnpm is this
host's package manager; recorded in `seed/manifest.json`):

```bash
pnpm install --frozen-lockfile --ignore-scripts   # clean, lockfile-pinned install
pnpm run build                                    # astro build -> dist/
pnpm run check                                    # fixture-check over dist/
```

`npm run check` must pass on the pristine seed. It is the public acceptance
instrument for this family; hidden scoring variants change the task instance,
never this contract.

## Isolation of this fixture

- The seed contains no hidden solution, no treatment hint, and no DWP
  artifacts (preregistration rule).
- The lab driver (`scripts/evaluation/v6/lab.py`) stages this seed into the
  lab with pinned hashes; arms work in disposable copies.
- Sealed variants of the cases in `CASES.md` are custodian-authored outside
  implementer access; nothing sealed is stored in this tree.
