# SECURITY.md — security posture (this repo)

> **Scope.** This is the repo's **security posture** for agents and contributors —
> the conformance-floor security document required of every DeepWorkPlan repo
> (`spec/DOCUMENTATION_STANDARD.md` §3, category 5). It is **not** the
> vulnerability-reporting policy: report vulnerabilities through
> [`SECURITY.md`](../SECURITY.md) at the repo root (GitHub private vulnerability
> reporting). This repo **dogfoods** the methodology it ships, so it holds itself
> to the same conformance floor it asks of every onboarded repo.

## What this repository is

A **Markdown-first agent skill pack**: Markdown procedures (`skills/`), a few
POSIX shell helpers (`setup.sh`, `scripts/`, `skills/deepworkplan/shared/context.sh`),
and Bats tests. There is **no runtime service, no HTTP API, no auth flow, and no
network egress.** The only security-relevant action the skill performs is that it
**mutates the user's repository** (onboarding writes/reconciles `AGENTS.md`,
`docs/`, `.agents/`, the `.claude → .agents` / `.cursor → .agents` symlinks; plan flows write under the
gitignored `.dwp/`). The full threat model, consent/dry-run posture, and
in-scope/out-of-scope boundaries live in the root [`SECURITY.md`](../SECURITY.md);
this document covers the **handling rules** agents must follow when working in
this repo.

## Secrets handling

- **There are no secrets in this repository, and none should ever be added.** No
  API keys, tokens, credentials, `.env` files, or private endpoints are required
  to develop, test, or release the skill.
- `shared/context.sh` reads **local git metadata and a documented allowlist of
  environment variables only** (agent-detection and `DWP_*` overrides). It never
  reads source contents or arbitrary environment for transmission — there is
  nowhere to transmit to.
- Releases publish from `main` via CI; publishing credentials live **only** in
  GitHub Actions secrets, never in the tree. Do not echo, log, or commit them.
- **A secret in a pushed commit MUST be treated as leaked and rotated**, not
  merely removed in a follow-up commit. This includes test fixtures and
  documentation examples — fabricated-looking strings still trip secret
  scanners and teach bad habits.

## Sensitive-data boundaries

- The skill operates on the **developer's local repository**; it must not copy
  repository contents, plan artifacts, or git metadata off the machine.
- Plan working state (`.dwp/`) is **gitignored by default**. Do not commit
  `.dwp/plans/*`, drafts, or analysis output, and do not relocate sensitive
  working state into committed source.
- Generated docs describe **conventions and locations**, never live secret
  values. When onboarding documents a repo's secret-handling convention, it
  records *where* secrets live and *how* they are loaded — never the secrets
  themselves.

## What agents MUST NOT write into docs or commits

- Real credentials, tokens, private URLs, internal hostnames, or customer data —
  in any file, including `tests/` fixtures and Markdown examples.
- Placeholder-but-plausible secrets (e.g. `sk-...`, `AKIA...`) that scanners flag.
- The contents of a user's environment captured during a run.

## Security review (dogfooding the spec)

Every Deep Work Plan in this repo ends with the mandatory **Security Review**
final task (`spec/DWP_SPECIFICATION.md` §6), and any task touching the shell
helpers, `setup.sh`, the onboarding mutation surface, or dependency/tooling
metadata carries the **per-task security discipline** (§5.1.2) in its acceptance
criteria. Because the skill's only sensitive action is mutating a repository, the
review focuses on:

- **Write surface.** Onboarding/addon flows propose before they write and
  **reconcile** instead of clobbering existing `AGENTS.md` / `docs/` / devcontainer
  setups; addons are opt-in.
- **Discovery boundary.** Anything outside `skills/deepworkplan/` — this file,
  the root `SECURITY.md`, `.github/`, `scripts/`, `tests/`, `docs/` — is
  repo-development infrastructure that is **never installed** on a user's machine.
- **No-secrets gate.** Every commit is checked to be free of secrets before push.
- **Non-blocking failure.** Uncertain control steps fall back to a safe default
  (`$PWD` as repo root, `.dwp/` under it) and continue; security checks never
  block the developer's primary task.

## Reporting a vulnerability

See the root [`SECURITY.md`](../SECURITY.md): use GitHub private vulnerability
reporting at <https://github.com/DailybotHQ/deepworkplan-skill/security>. Do not
open a public issue with exploit details before a fix exists.
