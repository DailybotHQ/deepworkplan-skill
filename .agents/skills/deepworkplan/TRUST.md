# Trust & guarantees — DeepWorkPlan skill

This file ships **inside** the skill so you can read exactly what DeepWorkPlan
will and will not do on your machine before you let it run. It restates, in one
place, the guarantees enforced by the skill's design. The authoritative security
policy and threat model live in the repo's [`SECURITY.md`](https://github.com/DailybotHQ/deepworkplan-skill/blob/main/SECURITY.md);
this is the install-time companion to it.

Source of truth: <https://deepworkplan.com> · License: MIT.

## What this skill is

A **Markdown-first** agent skill: the "code" is the `SKILL.md` prompt files an
agent reads at runtime, plus a small set of local helpers. Two Bash: `setup.sh`
(symlinking, at the repository root, not inside the pack) and, inside the pack,
`shared/context.sh` for repo/branch/`.dwp/` detection. Sixteen Python (stdlib
only, Python 3.9+), all inside the pack: `verify/conformance.sh` and its
`verify/plan_contract.py` for the read-only conformance check,
`shared/plan_paths.py` for monotonic plan IDs and plan selection,
`shared/update-state.py`, `shared/state_contract.py` and
`shared/finalize_plan.py` for the guarded state, evidence and completion
transactions, `shared/contract_v6.py` validating the v6 outcome
contract and journal records (identity, graph and verdict semantics; it
never executes gates), and — for v6 plans — `shared/ledger.py`, the single
journal writer and gate executor (the only place `observed` gate evidence
is produced, by actually running the declared command; evidence replay
from its cache is bound to the same task and criterion the cached result
was recorded under, so an identical command for another linkage runs
fresh instead of silently minting nothing; its `materialize` command is
the guarded creator of a v6 plan — manifest contract pointer, stamped
content-addressed contract, then the materialization-time approval event,
each step atomic and resumable, never rewriting a different contract or
another generation's manifest; it also captures
each task's starting fingerprint at `task_start` and executes both legs of
a declared control pair, materializing the old leg as a detached worktree
at that recorded revision; for v7 plans its `delegate` command records
delegation launches and results behind a gate — v7 contract,
`agent_delegation` grant, `parallel_safe` task or read-only delegate, an
enabled and detected transport addon — and **never runs a delegate
itself**: the transport addon does, and a delegate's result stays
`asserted` until this ledger's own gate observes it), `shared/views.py`
rendering the deterministic generated views under the human-edit rule,
`shared/scheduler.py` — the read-only authorization core that turns journal
records into dispatch/refusal decisions (it never writes and never executes
anything; every refusal it returns is a decision, not a side effect) — and
`shared/outcomes.py`, the v6 outcome-verification helper: closure decisions
and receipts are pure recomputations over the records (a receipt is written
only to the `--out` path you name), review states are recorded as ordinary
`asserted` observations through the ledger writer, and a declared control
executes through the ledger's control executor — never on its own — and
`shared/context_manifest.py`, the v6 context-selection helper: a read-only
derivation of the per-task context manifest, dead-end digest, freshness
verdict and four-quantity accounting from the plan's own records (it takes
no lock and writes nothing unless you pass `--out`); and
`shared/resources.py`, the v6 resource helper: it composes the
scheduler's envelope accounting and the ledger's record discipline to
negotiate host abilities, apply reserves, record exhaustion and settle
cancellations — the only events it writes are journal observations
through the ledger writer, and it never mints observed trust. From 7.0.0
it also computes addon-provided abilities (`spec/V7_ABILITIES.md`): for an
addon **you enabled** in `.dwp/config.json` it runs that addon's declared
detect command — a plain argv line from the addon's `addon.json` (no shell
metacharacters allowed by schema), executed without a shell, stdin closed,
10-second timeout, output only parsed for an interface number — or checks
the declared file paths; a disabled addon is never consulted and nothing
it learns is written to a plan; and
`shared/migrate_v6.py`, the explicit v5 → v6 migration helper — preview,
guarded resumable migrate, verified rollback. It never executes anything:
a v5 gate record is imported through the ledger writer as `imported`
evidence with the v5 source digest as provenance (or `asserted` history
when the v5 state kept no resolvable pointer), and `observed` is refused
there exactly as everywhere else. The only v5 byte it ever rewrites is the
manifest, swapped to the v6 pointer after the verified backup exists. And
`shared/benchmark.py`, the opt-in benchmark helper: **disabled unless you turn
it on** (`.dwp/config.json` or `~/.dwp/config.json`); it derives a per-plan
metrics record from the plan's own records — journal, contract, state — and
writes it inside that plan's `analysis_results/`. Unmetered quantities are
null, never estimated; the record never leaves your repositories (no network,
no upload — it is local field data you asked for, not telemetry); and an
emission failure degrades to a warning and can never block plan completion.
With the nested `learnings` flag on, the same helper additionally writes
`learnings.json` beside the record, still only inside that `analysis_results/`
directory: its derived half copies friction reasons the journal already
recorded, verbatim, and its curated half — agent judgment, written once —
carries a closed-vocabulary category, an anchor naming only a journal event
seq and/or a short section id, and the finding/proposal text; never file
contents, paths or secrets. Reruns preserve curated entries byte-for-byte.
`shared/config.py` is the one reader of `.dwp/config.json` /
`~/.dwp/config.json` (benchmark switch and addon registry): reading is
fail-closed and never aborts a flow, it lists the `addons/` directory names
without opening any addon file (only `descriptors` and `backfill`, on
request, read the descriptors and run their read-only detection), and its
writers (`enable` / `disable` / `host`, run by onboarding after you accept,
and `backfill --write`, run by an accepted upgrade) reconcile the repository
file atomically and refuse rather than overwrite a file they cannot parse. It
makes no network call and stores no secret. `shared/delegators.py` compares
the repository's command delegators with the pack's templates and prints a
drift report; it never writes.
They
read and write only your repository and its `.dwp/`
directory — with one honest exception that is CPython's behavior rather than
ours: importing a Python helper can leave a `__pycache__/` bytecode cache
beside it inside the installed pack. The shipped flows set
`sys.dont_write_bytecode` to avoid it, but a direct `python3 -c 'import …'`
against a helper (a diagnosis step, say) will still create one. It is a cache
of our own files, contains nothing of yours, and is safe to delete. The **core
methodology makes no HTTP API calls, no authentication flow, and no network
calls**, and emits **no telemetry** of any kind. Its only external process
calls are `git` and — from 7.0.0, and only for an addon **you enabled** — that
addon's declared read-only detect command (for example `ak doctor --json`),
run without a shell under a timeout (see `shared/resources.py` above).

> **One honest caveat — addons.** The shipped tree includes eight addons
> (`addons/dailybot`, `addons/devcontainer`, `addons/dependency-upgrade`,
> `addons/ai-diff-reviewer`, `addons/design-system`, `addons/agentkit`,
> `addons/herdr`, `addons/vim`). Seven are opt-in: if you explicitly choose to
> install them, they may install third-party artifacts — **always behind
> your consent, always pinned** (a published tag or a package-manager
> version), and always through a verifiable path: a package manager, the
> checksummed `skills` CLI, a clone of an exact tag followed by that
> product's own `install.sh`, or a documented download → verify SHA-256 →
> execute flow. Three of them (`agentkit`, `herdr`, `vim`) and `devcontainer`
> are thin integrators of separate products (coding-agents-kit, herdr-peers,
> deepworkplan-vim, devcontainer-kit); each has its own repository and
> license, and the pack carries only detection, the offer, the pinned install
> and — for the two delegation transports — the mapping onto the plan's
> recorded `delegate` operations. Enabling an addon is recorded in
> `.dwp/config.json` and authorizes nothing by itself. The eighth, the
> **AI Diff Reviewer local review**, is
> part of the baseline since standard 2.3.0: `onboard` installs one MIT-licensed, tag-pinned
> skill (`DailybotHQ/ai-diff-reviewer`) through the checksummed `skills` CLI,
> and the Final Review's security pass runs it through your own coding agent —
> no service, no provider secret, no telemetry; its CI Action stays opt-in and
> a decline is recorded, never hidden. No addon ever pipes a remote installer
> into a shell, copies host credentials anywhere without an explicit visible
> opt-in, or documents permission-bypass shortcuts. (The agentkit addon's
> delegates run under coding-agents-kit's own posture — autonomy by default,
> with an opt-out, `--ask` or `AGENTKIT_PERMISSIONS=ask`, that always wins;
> the pack spells no autonomy flag and passes only `--ask`, when a plan
> records the opt-out.) **A repository is fully
> conformant with zero optional addons**. Core runtime helpers never touch the
> network; consent-gated onboarding Phase 7a is the sole baseline exception and
> may run the pinned AI Diff Reviewer install plus extension bootstrap. The
> self-audit below checks that exception explicitly and lists other addons
> separately.

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
- **Keeps working state out of version control.** Plans land in a
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
# 1. No network calls in the CORE methodology (excludes addons; expect none):
grep -RInE 'curl|wget|fetch\(|urllib|requests\.|XMLHttpRequest' \
  skills/deepworkplan --exclude-dir=addons --exclude=TRUST.md \
  || echo 'OK: no network calls in the core skill'

# 2. See every network reference that DOES exist — all inside addons:
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

# 5. No unpinned installs of any kind: no clone-and-run of whatever a remote
#    default branch currently holds (a clone must name an exact tag,
#    `git clone --branch vX.Y.Z`), no un-tagged `skills add`, and no
#    `OWNER/REPO@ref` shorthand — the skills CLI ignores that ref and installs
#    the default branch; a pin is the tree-URL form
#    `skills add https://github.com/OWNER/REPO/tree/vX.Y.Z`:
grep -RInE --exclude=TRUST.md --exclude=install-verification.md --exclude=troubleshooting.md 'git clone |skills add [A-Za-z0-9_./-]+([[:space:]]|$)|skills add "?[^ "]*[A-Za-z0-9_>-]@|skills add "?https://[^ "]*' skills/deepworkplan \
  | grep -vE 'skills add "?https://github\.com/[^ "]+/tree/(v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?|vX\.Y\.Z|<[^>]+>|\$\{?[A-Za-z_]+\}?)("|[[:space:]`]|$)' \
  | grep -vE 'git clone --branch v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?([[:space:]`]|$)' \
  || echo 'OK: every install path is tag-pinned or package-managed'
```

## Reporting a vulnerability

Privately, through **GitHub's private vulnerability reporting** on this repo —
<https://github.com/DailybotHQ/deepworkplan-skill/security> — not a public issue.
See [`SECURITY.md`](https://github.com/DailybotHQ/deepworkplan-skill/blob/main/SECURITY.md).
The public trust page is <https://deepworkplan.com/trust>.
