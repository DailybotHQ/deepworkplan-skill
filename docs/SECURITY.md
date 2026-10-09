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
POSIX shell helpers (`setup.sh`, `scripts/`, and, inside the pack,
`skills/deepworkplan/shared/context.sh` and `skills/deepworkplan/verify/conformance.sh`),
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
- `verify/conformance.sh` is **read-only**: it reads plan files, `AGENTS.md`,
  `docs/` and `.gitignore` to produce a verdict, and writes nothing. It makes no
  network call.
- `shared/benchmark.py` (opt-in via `.dwp/config.json`) reads the plan's own
  records (`journal.ndjson`, `manifest.json`, `contract.json`, `state.json`),
  read-only `git` queries via an argv subprocess call, and the two documented
  config files. Its only writes land inside the measured plan's
  `analysis_results/`. Records carry the repository **basename**, branch and
  counts — never full paths, file contents, or environment values. With the
  nested `learnings` flag on, it also writes `learnings.json` there: the
  derived half copies friction reasons the journal already recorded, and the
  curated half is written once and then preserved byte-for-byte by reruns —
  never merged or rewritten. Curated entries carry a closed-vocabulary
  category, an anchor naming only a journal event seq and/or a short section
  id (never a path), and finding/proposal text — no file contents, no user
  paths, no secrets. It makes no network call and there is nothing to
  transmit to.
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
  `.dwp/plans/*` or analysis output, and do not relocate sensitive
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

## skills.sh audit posture (user-trust invariant)

The public [skills.sh listing](https://www.skills.sh/dailybothq/deepworkplan-skill/deepworkplan)
continuously shows Gen Agent Trust Hub / Socket / Snyk audits for the shipped
pack. The audits are largely **lexical** — they pattern-match strings in
`skills/deepworkplan/**` regardless of surrounding guardrail prose — so the pack
maintains these hard invariants (enforced in review by
[`.review/extension.md`](../.review/extension.md) and self-auditable via
[`skills/deepworkplan/TRUST.md`](../skills/deepworkplan/TRUST.md)):

1. **No remote-installer pipes** (Snyk E005 / Socket W012): no literal
   `curl … | bash`, `wget … | sh`, `irm … | iex`, or any single-line
   fetch-and-execute — anywhere in the pack, opt-in addons and "don't do this"
   illustrations included. Installs are described as package-manager commands
   or a verified multi-step flow (download → verify SHA-256 → execute).
   Precedent: `6a05ed9` flipped Snyk to FAIL before this rule existed.
2. **No permission-bypass literals, no silent credential relocation**
   (Snyk E006): AI-CLI wrappers documented in the pack are **pass-through**
   (no injected bypass flags — elevated modes are the developer's own choice),
   and any host-credential seeding (e.g. SSH keys into a devcontainer) ships
   behind an explicit, visible opt-in gate (read-only mount +
   `SEED_SSH_KEYS=1`), default off.
3. **No unpinned clone-and-run installs** (Snyk/Socket W012): every documented
   cross-repo install is tag-pinned (`@vX.Y.Z`, or `git clone --branch
   vX.Y.Z` for the ecosystem kits, followed by their own `install.sh`) or
   package-manager installed; `skills-lock.json` content hashes are the
   verification story.
4. **Trust boundaries everywhere**: every `SKILL.md` with write-capable
   `allowed-tools` carries a human-readable "Trust boundary (write scope)"
   section — the contract Trust Hub audits against the frontmatter.

Dashboard lag after a merge is normal (skills.sh re-scans on a delay); a known
bad string in the tree is not. History: E005/W012 pipes were eliminated in
`6a05ed9` (Jul 2026); the `fix/security-audits-e006-w012-trust` round (Sep 2026)
eliminated the E006 vectors (devcontainer bypass-flag wrappers, silent SSH
seeding — now opt-in-gated), swept **every** cross-repo install in the pack to
tag-pinned form (dailybot addon, ai-diff-reviewer addon + SPEC/INTEGRATION,
`onboard` Phase 7 + addon summaries, `spec/ADDONS.md`), narrowed `status` to
read-only tools, and rolled trust boundaries out to every write-capable
`SKILL.md`. Self-audit grep #5 enforces the pin rule mechanically: no `git
clone` without an exact `--branch vX.Y.Z` tag and no un-tagged `skills add`
anywhere under the pack.

## v7 attack surface and its controls

| Surface | Control |
|---|---|
| Addon detect commands (`shared/resources.py`) | Only for addons **you enabled**; the command comes from the in-pack `addon.json` (schema forbids shell metacharacters), runs as argv without a shell, stdin closed, 10 s timeout, binary resolved to an absolute path (a relative `PATH` entry is refused); output only parsed for an interface integer; `file-json:` interfaces read machine-level `~/` files only. |
| Addon registry writer (`shared/config.py`) | Atomic replace; refuses unknown keys, malformed versions, unparseable files and a symlinked `.dwp/` or `config.json`. |
| Delegation (`ledger.py delegate`) | Recorded gate (v7 contract, `agent_delegation` grant, `parallel_safe` marker or a read-only delegate, an enabled and detected transport addon); a raw append cannot write a delegation; a read-only delegate's tree fingerprint is checked at collect and cancel (changed tree → recorded failed), and a read-only delegate on an unmarked task needs a git work tree; a task cannot complete while one of its delegations is open; `result_path` validated and contained before it is read; delegate output is data and `asserted` until this plan's gates observe it. |
| Gate fingerprints | Touched-surface entries outside the repository are never read (glob matches are contained file by file); links are named, never followed. |
| Release workflows | Inputs and commit messages reach shell only through `env:`; multi-line step outputs use a random delimiter; versions are re-validated where used; pre-releases only from `main`, above the last stable release, never moving a tag, never `latest`; third-party installers (the ecosystem pin smoke) run in a separate job with read-only permissions and no persisted credentials, before any job that can push. |
| Public hygiene (ecosystem amendment A3) | `scripts/check-public-hygiene.sh` runs in CI over tracked files: no personal paths, private organization/repository/tooling names, non-public `@dailybot.com` addresses or secret-shaped strings (fixtures must be obviously fake and listed in `.public-hygiene-allow` with a reason). History is not rewritten for non-secret names. |

## Repository settings (ecosystem amendment A3, S2)

Secret scanning with push protection, private vulnerability reporting and
Dependabot alerts are on; `main` is protected (required CI checks —
frontmatter, shellcheck, bats, public hygiene, schema/contract, Python
floor — one approving review, no force pushes or deletions; administrators
and the release automation may bypass). Wiki and Discussions are off; head
branches are deleted on merge. `bash scripts/check-github-settings.sh
DailybotHQ/deepworkplan-skill` verifies these read-only; it checks that CI
checks are required, not their names, and does not inspect the bypass list.

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
