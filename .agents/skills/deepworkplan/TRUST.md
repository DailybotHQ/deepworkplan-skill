# Trust & guarantees — DeepWorkPlan skill

This file ships **inside** the skill so you can read exactly what DeepWorkPlan
will and will not do on your machine before you let it run. It restates, in one
place, the guarantees enforced by the skill's design. The authoritative security
policy and threat model live in the repo's [`SECURITY.md`](https://github.com/DailybotHQ/deepworkplan-skill/blob/main/SECURITY.md);
this is the install-time companion to it.

Source of truth: <https://deepworkplan.com> · License: MIT.

## What this skill is

A **Markdown-first** agent skill: the "code" is the `SKILL.md` prompt files an
agent reads at runtime, plus three small Bash helpers: `setup.sh` (symlinking,
at the repository root, not inside the pack), and two inside the pack —
`shared/context.sh` for repo/branch/`.dwp/` detection and
`verify/conformance.sh` for the read-only conformance check. The **core
methodology makes no CLI calls, no HTTP API calls, no authentication flow, and no
network calls**, and emits **no telemetry** of any kind.

> **One honest caveat — opt-in addons.** The shipped tree includes opt-in addons
> (`addons/dailybot`, `addons/devcontainer`, `addons/dependency-upgrade`,
> `addons/ai-diff-reviewer`, `addons/design-system`) that, if you explicitly
> choose to install them, may install third-party artifacts — **always behind
> your consent, always pinned** (a published tag or a package-manager version),
> and always through a verifiable path: a package manager, the checksummed
> `skills` CLI, or a documented download → verify SHA-256 → execute flow. No
> addon ever pipes a remote installer into a shell, copies host credentials
> anywhere without an explicit visible opt-in, or documents permission-bypass
> shortcuts. **A repository is fully conformant with zero addons**, and the
> baseline methodology never touches the network. The self-audit below scopes
> the no-network check to the core and lists the addons separately so you can
> see exactly where any network reference lives.

## Permissions it requests (`allowed-tools`)

`Bash, Read, Grep, Glob, Edit, Write` — and why each is needed:

- **Read, Grep, Glob** — analyze your repository (stack, commands, structure) to
  reason about it rather than copy a template.
- **Edit, Write** — generate and reconcile `AGENTS.md`, `docs/`, per-module docs,
  the `.agents/` kit, and write plan artifacts under `.dwp/`.
- **Bash** — run `shared/context.sh` (reads local git + environment metadata
  only), `verify/conformance.sh` (reads plan and repository files; writes
  nothing), and the repo's own validation commands during plan execution.

## What it does to your machine

The only security-relevant action is **mutating your repository**, and it is
non-destructive by design:

- **Reconciles, never clobbers.** It detects existing `AGENTS.md`, `docs/`,
  `.agents/`, `CLAUDE.md`, and `.gitignore`, and merges/improves in place — asking
  before replacing or deleting anything you already have.
- **Proposes before large changes.** Onboarding presents a plan and waits for your
  confirmation before big or destructive edits.
- **Keeps working state out of version control.** Plans and drafts land in a
  gitignored `.dwp/` directory; onboarding **appends** to `.gitignore` rather than
  rewriting it.
- **Touches no secrets.** It never reads or commits credentials, and keeps changes
  to small, reviewable diffs.

## What it does NOT do

- No telemetry, no analytics, no "phone home" — ever, including the addons.
- No network requests in the **core** methodology or any of its Bash helpers. (Opt-in
  addons may install third-party tools via their official installers, only with
  your consent — see the caveat above.)
- No background daemon, no persistent external state.
- No silent file writes outside the documented surfaces (`AGENTS.md`, `docs/`,
  per-module docs, `.agents/`, `.dwp/`, and `.gitignore` appends).

## Provenance — verify before you run

Every release publishes a `SHA256SUMS` over the shipped skill
(`skills/deepworkplan/**`). Confirm your copy matches the release before trusting
it:

```bash
# From the repo root, with SHA256SUMS downloaded from the matching release:
./setup.sh --verify        # or: ./scripts/verify-integrity.sh
```

Releases are **checksummed, not signed** — cryptographic signing (cosign or
maintainer GPG) is a documented next step, not a current claim. Everything is open
source, so you can also diff any shipped file against the repository at its tag.

## Self-audit (don't take our word for it)

Run these from the repo root to confirm the claims above:

```bash
# 1. No network calls in the CORE methodology (excludes opt-in addons; expect none):
grep -RInE 'curl|wget|fetch\(|urllib|requests\.|XMLHttpRequest' \
  skills/deepworkplan --exclude-dir=addons --exclude=TRUST.md \
  || echo 'OK: no network calls in the core skill'

# 2. See every network reference that DOES exist — all inside opt-in addons:
grep -RIlE 'curl|wget' skills/deepworkplan/addons || echo 'none'

# 3. Two scripts ship inside the pack; confirm neither makes a network call:
find skills/deepworkplan -name '*.sh'
grep -nE 'curl|wget|https?://' \
  skills/deepworkplan/shared/context.sh skills/deepworkplan/verify/conformance.sh \
  || echo 'OK: both read local files, git and env only'

# 4. No remote-installer pipes or bypass-flag literals anywhere in the pack
#    (the lexical shapes Snyk E005/E006 and Socket W012 audit for). The
#    bracketed letters keep this grep from matching its own pattern:
grep -RInE --exclude=TRUST.md -- '--dangerous[l]y|--full-permissio[n]|c[u]rl[^|]*\|[[:space:]]*(ba)?sh|w[g]et[^|]*\|[[:space:]]*(ba)?sh|\|[[:space:]]*(ie[x]|pws[h])[[:space:]]*$|ir[m][[:space:]]+https?://[^ ]*[[:space:]]+\|[[:space:]]*ie[x]' \
  skills/deepworkplan \
  || echo 'OK: no installer pipes, no bypass flags'

# 5. No unpinned installs of any kind: no clone-and-run (installing by
#    cloning whatever a remote default branch currently holds), no un-tagged
#    `skills add`, and no moving refs — a pin is an immutable version tag
#    (@vX.Y.Z), never @main/@master/@latest/@head:
grep -RInE --exclude=TRUST.md 'git clone |skills add [A-Za-z0-9_./-]+([[:space:]]|$)|skills add [^`]*@(main|master|latest|head)([[:space:]\`]|$)' skills/deepworkplan \
  || echo 'OK: every install path is tag-pinned or package-managed'
```

## Reporting a vulnerability

Privately, through **GitHub's private vulnerability reporting** on this repo —
<https://github.com/DailybotHQ/deepworkplan-skill/security> — not a public issue.
See [`SECURITY.md`](https://github.com/DailybotHQ/deepworkplan-skill/blob/main/SECURITY.md).
The public trust page is <https://deepworkplan.com/trust>.
