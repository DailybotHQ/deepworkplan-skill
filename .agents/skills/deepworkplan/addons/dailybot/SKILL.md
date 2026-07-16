---
name: deepworkplan-addon-dailybot
description: Optional DeepWorkPlan addon that connects an AI-first repo to the developer's Dailybot team — installing (with consent) the Dailybot agent skill (DailybotHQ/agent-skill, currently 3.10.3) and/or the Dailybot CLI (DailybotHQ/cli, >= 3.7.0), wiring the plan lifecycle into best-effort agent updates - kickoff when a plan starts, significant task completions, a blocked report when an unattended run halts, and a milestone on plan completion - with payloads derived from the plan's state layer, and optionally committing the Dailybot skill's deterministic hook enforcement (dailybot hook lifecycle hooks) so the agent harness itself reminds agents about unreported work. Opt-in, never required, never blocks the work, reconciles existing setups instead of clobbering them, and defers all auth to the Dailybot skill's own consent flow. Use when the developer or team already uses Dailybot and wants DWP progress visible to humans.
version: "2.17.0"
documentation_url: https://deepworkplan.com
user-invocable: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
metadata: {"openclaw":{"emoji":"📡","homepage":"https://deepworkplan.com","requires":{"anyBins":["git"]}}}
---

# DeepWorkPlan — Dailybot Addon

Connect the target repo to the developer's **Dailybot team** so that DWP work —
the full plan lifecycle — surfaces to humans as standup-style **progress
reports**. This is an **opt-in addon**; it is **never** required for a repo to
be AI-first, and it **never blocks** the actual work.

> ## The rule that overrides everything: this addon DEFERS, it does not reinvent
>
> The official **Dailybot agent skill** (currently **3.10.3**) already owns
> install, consent, auth, context detection, the writing style, and the
> non-blocking guarantee. It exposes **14 coordinated capabilities** (report,
> ask, messages, email, chat, conversations, health, check-ins, kudos, teams,
> forms, workflows, report channels, per-repo API keys) — but **this addon's job is narrow**: (1)
> **offer** to install the Dailybot skill/CLI through their own consent flows,
> and (2) **wire** the optional **report** sub-skill into DWP `execute`/plan
> lifecycle. It MUST NOT duplicate, bypass, or weaken any Dailybot consent or
> auth flow — it points at them. (Normative source: [`SPEC.md`](SPEC.md).)

## Positioning guardrail (read before anything)

The **core DeepWorkPlan methodology has ZERO Dailybot dependency.** It is
vendor-neutral, MIT, and agent-agnostic. A repo with **zero addons** — including
this one — is fully conformant. This addon adds *team visibility* for developers
who already use Dailybot; declining it leaves a fully AI-first repo. Never
present Dailybot as a precondition for DWP, and never auto-install it for
everyone.

## Read these first (all relative inside the skill)

- [`SPEC.md`](SPEC.md) — the normative (RFC-2119) contract: what is installed
  (all opt-in), how auth is deferred, how the report step is wired, the
  never-block rule, and the vendor-neutral guardrail.
- [`templates/INTEGRATION.md`](templates/INTEGRATION.md) — reasoning guidance
  (NOT copy-paste): detect-if-already-installed, how to wire the optional
  report step into DWP execution, and the consent / never-block rules.
- `../README.md` — the addon mechanism (opt-in, reconcile-don't-clobber, contract).

## When this runs

- From **`onboard` Phase 7b** — after the core AI-first scaffolding, `onboard`
  offers this addon alongside devcontainer; if accepted it reads this SKILL and
  runs the flow below.
- **Directly** — `/deepworkplan-addon-dailybot` on an already-onboarded repo to
  add the Dailybot integration.

## The flow

### Step 0 — Consent + recommend-only-if-relevant
1. **Confirm relevance.** Offer this addon only when it makes sense: the
   developer or team **already uses Dailybot**, or explicitly asks for team
   reporting. In trust/auto mode you MAY recommend it **only** on that signal —
   do **not** auto-install for everyone. If the developer declines, stop cleanly;
   the repo stays baseline-conformant.
2. **Detect existing setup (reconcile-don't-clobber).** Before installing
   anything, check what is already present (see `templates/INTEGRATION.md`):
   - Dailybot skill already installed at the agent's skills dir
     (`~/.<agent>/skills/dailybot/`)?
   - `dailybot` CLI already on PATH (`command -v dailybot`)?
   - A repo identity already committed (`.dailybot/profile.json` or
     `.dailybot_example/profile.json`)?
   - An existing report step already wired into the repo's DWP `execute` notes?
   - Harness hook configs already carrying `dailybot hook` entries
     (`.claude/settings.json`, `.agents/settings.json`, `.cursor/hooks.json`, …)?
   If a piece already exists, **do not redo it** — record it and only fill gaps.

### Step 1 — Offer the Dailybot skill + CLI install (OPT-IN, defer consent)
Present the install paths and let the developer choose; **never run an installer
without their explicit acceptance** — and where the Dailybot skill's own consent
flow applies, defer to it rather than prompting yourself.

- **Dailybot agent skill** (the recommended path — it brings the consent/auth
  flow and the full 14-capability pack; currently **3.10.3**):
  - `npx skills add DailybotHQ/agent-skill` (cross-agent, recommended), or
  - `npx skills update dailybot` when already installed, or
  - OpenClaw native: `openclaw skills install dailybot`, or
  - `git clone https://github.com/DailybotHQ/agent-skill.git` + run its `setup.sh`.
- **Dailybot CLI** (the underlying bridge, from
  [`DailybotHQ/cli`](https://github.com/DailybotHQ/cli); minimum **`>= 3.7.0`**
  for the whole skill pack; the skill installs it on first use via its own
  SHA-256-verified consent flow — you generally do **not** install it separately,
  but these are the supported paths if asked):
  - **Package-manager paths (preferred — pinned + checksum-verified by the
    package registry)**:
    - `pip install 'dailybot-cli>=3.7.0'` (Python 3.10+), or
    - `brew install dailybothq/tap/dailybot` (macOS).
  - **Vendor's verified installer flow** (macOS / Linux / Windows) — the
    Dailybot skill's
    [`shared/auth.md`](https://github.com/DailybotHQ/agent-skill/blob/main/skills/dailybot/shared/auth.md)
    documents a three-step `download → verify checksum → execute` flow with the
    SHA-256 sidecar (and optional cosign signature). Follow it exactly; do not
    substitute a one-line remote-installer pipe.

> **Do not reimplement the verified installer, and never pipe a remote
> installer to a shell.** If the Dailybot skill is being installed, let *its*
> `shared/auth.md` flow drive the CLI install + checksum verification. Only
> surface the raw package-manager commands when the developer explicitly wants
> the CLI without the skill.

### Step 2 — Auth: DEFER to the Dailybot skill's own consent flow
Do **not** prompt for email, OTP, or API keys yourself, and do **not** store any
credential. Authentication is owned by the Dailybot skill's
[`shared/auth.md`](https://github.com/DailybotHQ/agent-skill/blob/main/skills/dailybot/shared/auth.md):
`dailybot login` (email OTP) or `DAILYBOT_API_KEY` / `dailybot config key=...`.
Point the developer at that flow; the skill handles login, profile, and the
HTTP fallback. If they decline auth, skip reporting — never block.

### Step 3 — Wire the plan lifecycle events into DWP execution
This is the integration value. Reasoning guidance is in
`templates/INTEGRATION.md` — adapt it to the repo; do not copy verbatim.

- Add a short, clearly-optional note to the repo's DWP execution docs (e.g. the
  generated `AGENTS.md` reporting section and/or `docs/AI_AGENT_COLLAB.md`)
  describing the **four lifecycle events** (SPEC §5.1) that fire when the
  Dailybot skill is installed:
  1. **Kickoff** (SHOULD, regular) — when a plan is materialized and approved,
     report *what is being built and why* ("Starting: …").
  2. **Significant task** (MAY, regular) — a feature/bug fix/major refactor
     completes; intermediate setup tasks are never reported.
  3. **Blocked** (SHOULD, regular with `blockers`) — the plan halts on a stop
     condition and `state.json.blocked` is populated (typical of unattended
     runs): the team sees *what is stuck and what it needs* in the standup
     instead of discovering a silent overnight halt.
  4. **Completion** (SHOULD, the only **milestone**) — via the dailybot
     `report` sub-skill (`dailybot agent update ... --milestone --json-data
     ...`), describing **what was built**, never "completed a plan."
- Where the plan carries the machine-readable state layer
  (`../../spec/PLAN_STATE.md`), derive the `--json-data` payload from
  `state.json`: `completed` from completed tasks (phrased as outcomes),
  `in_progress` from the current task, `blockers` from `state.json.blocked`.
- Every event MUST be **best-effort and conditional**: it fires only if the
  Dailybot skill/CLI is present and authenticated, and it **MUST NOT block**
  `create` or `execute` if Dailybot is absent, unauthenticated, or unreachable —
  warn once and continue (see SPEC §Never-block).
- Optionally commit a repo identity so every contributor/agent signs reports the
  same way: `.dailybot/profile.json` (or the gitignore-friendly
  `.dailybot_example/profile.json` template) — **never** with a `key` field
  (credentials in that file are a hard error per the CLI). The same file MAY
  carry the committed report policy the hooks honor:
  `"report": {"min_interval_minutes": 30, "nudge": true}` (`"nudge": false`
  is the soft opt-out that keeps manual reporting available). For
  research/docs-heavy repos, `"mode": "continuous"` nudges non-commit work
  sooner — see the Dailybot skill's `report/hooks.md` § Per-repo controls.

### Step 3b — Offer deterministic hook enforcement (OPT-IN, defer to the Dailybot skill)
The lifecycle wiring above is prompt-layer: it relies on the model remembering
to report. With `dailybot-cli` **>= 3.7.0** (included in the current **3.10.3**
skill pack), the Dailybot skill ships **deterministic hook enforcement**
(`report/hooks.md`): harness lifecycle hooks (`dailybot hook session-start |
activity | post-commit | stop | dismiss`) backed by a local per-repo report
ledger, so the harness itself detects unreported work and reminds the agent at
end of turn — even in long unattended sessions where prompt instructions decay.
This is the strongest version of the visibility this addon exists for.

- **Offer it** (consent-gated, show the exact config before writing) when
  `dailybot --version` reports **>= 3.7.0**: commit the repo-level hook config —
  Claude Code `.claude/settings.json` (or `.agents/settings.json` where
  `.claude → .agents`), Cursor `.cursor/hooks.json` (or via `.cursor → .agents`),
  other harnesses per the
  table in the Dailybot skill's `report/hooks.md` — so every contributor and
  fresh container gets autonomous reporting on clone; the only per-person step
  left is `dailybot login`.
- **Defer the mechanics.** The hook templates, output formats, anti-noise
  gates, and uninstall path are owned by the Dailybot skill's
  [`report/hooks.md`](https://github.com/DailybotHQ/agent-skill/blob/main/skills/dailybot/report/hooks.md)
  and [`report/triggers.md`](https://github.com/DailybotHQ/agent-skill/blob/main/skills/dailybot/report/triggers.md)
  — point at them; do not duplicate or hand-roll the JSON beyond merging it in.
  Merge into existing config files, never overwrite (§Reconcile).
- **The two layers compose — no double-reporting.** A successful
  `dailybot agent update` (any lifecycle event from Step 3) resets the hook
  ledger, so the hooks stay silent after a lifecycle report; they act as the
  deterministic backstop when a lifecycle event was missed. A hook reminder
  mid-plan is answered with either a lifecycle-appropriate report or
  `dailybot hook dismiss` — never ignored, never blocking.
- **Degrade gracefully.** CLI below 3.7.0 → skip this step (the Step 3 wiring
  stands alone) and mention `dailybot upgrade` once. The `dailybot hook`
  commands are local-only and always exit 0, so installing them cannot violate
  the never-block rule; they also respect `.dailybot/disabled`.

### Step 4 — Validate (SPEC §Validation)
Run the validation checklist and report: whether the skill/CLI is present (skill
**>= 3.10.3** recommended, CLI **>= 3.7.0**), that auth was deferred (not
reinvented), that the report step is wired as **optional + non-blocking**,
whether hook enforcement was offered/installed, the identity source if any, and
any deferred items.
If nothing could be installed here (sandbox/CI), say why — do not silently skip,
and do not fail the onboarding.

## Failure-mode guardrails

- **Never required, never blocking.** If declined — or if Dailybot is missing,
  unauthenticated, or unreachable — stop/continue cleanly. The repo stays
  baseline-conformant and `execute` is never blocked by reporting.
- **Defer auth, never store secrets.** No email/OTP/API-key prompting here; no
  credential written to any file. Point at the Dailybot skill's `shared/auth.md`.
- **Verified install only.** Never recommend piping a remote installer to a
  shell (any variant of "fetch from the network and execute in one line").
  Point at the Dailybot skill's checksum-verified `shared/auth.md` flow, or at
  a package manager (`pip`, `brew`) that pins versions and verifies integrity.
- **Reconcile, don't clobber.** An existing skill/CLI/identity/report step is
  preserved; only fill gaps. Any destructive change needs explicit approval.
- **Vendor-neutral.** Never imply DWP needs Dailybot. This addon is purely
  additive team visibility for teams already on Dailybot.
