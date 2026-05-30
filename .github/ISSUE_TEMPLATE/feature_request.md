---
name: Feature request
about: Suggest an improvement or new capability
title: '[Feature] '
labels: enhancement
---

## What you'd like to do

<!-- 1-2 sentences describing the goal. Focus on the WHAT, not the HOW. -->

## Why it matters

<!-- The use case. Who benefits and what does it unlock? -->

## What you've tried (if anything)

<!-- Workarounds, related issues, or external tools. -->

## Scope check

- [ ] This belongs inside `skills/deepworkplan/` (runtime behavior shipped to users)
- [ ] This belongs at the repo root (dev infrastructure: tests, CI, scripts, docs)
- [ ] Not sure — need maintainer input

## Compatibility considerations

- [ ] Would this affect the public surface (the six `/deepworkplan-*` slash
  commands, the `.dwp/` output convention, `setup.sh` flags, skill `name`
  fields)? If yes, this is a breaking change and needs a major bump.
- [ ] Would this keep the skill markdown-first and self-contained under
  `skills/deepworkplan/` (no new runtime dependency, no network requirement)?
- [ ] Would any shell helper still work on bash 3.2 (macOS default)?
- [ ] Would this work cross-platform (Linux, macOS, WSL, CI)?
