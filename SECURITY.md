# Security Policy

This is the **official DeepWorkPlan agent skill pack**, maintained by the team
at [Dailybot](https://www.dailybot.com). Source of truth:
<https://github.com/dailybotops/deepworkplan-skill>. Reports against this repo
reach the Dailybot security team directly.

## Reporting a Vulnerability

If you believe you have found a security vulnerability in the DeepWorkPlan skill
pack, please report it privately rather than opening a public issue.

**Email:** security@dailybot.com

Include in your report:

- A description of the issue and the impact you observed
- Steps to reproduce (a minimal proof of concept is ideal)
- The version of the skill pack (`version` field in `skills/deepworkplan/SKILL.md`)
- Your name or handle if you would like credit in the release notes

We acknowledge reports within **3 business days** and aim to issue a fix or a
mitigation within **30 days** for valid findings, depending on severity.

## Supported Versions

The skill auto-releases from `main`; the latest tagged `vX.Y.Z` release is the
only supported version. Security fixes ship as a new release rather than
backports.

| Version | Supported |
|---------|-----------|
| Latest `2.x` release | ✅ |
| Anything older | ❌ — upgrade to the latest release |

## In Scope

- Code in this repository under `skills/`, `setup.sh`, and `scripts/`
- The behavior of the bundled `skills/deepworkplan/shared/context.sh`
- The repo-mutation behavior of `deepworkplan-onboard` (the files it writes)
- Any silent file write or persistent change made by the skill

## Out of Scope

- Third-party agent harnesses (Claude Code, Cursor, Codex, etc.) — report upstream
- Issues caused by user-modified copies of the skill that drift from this repo
- The skills.sh / OpenClaw distribution platforms themselves — report to those projects

## Threat Model (Markdown-first skill)

DeepWorkPlan is a **Markdown-first** skill. It has **no CLI, no HTTP API, no
auth flow, and makes no network calls** — `shared/context.sh` reads local git
metadata and environment variables only and emits a single-line JSON blob; no
telemetry leaves the machine. The skill's only security-relevant action is that
it **mutates the user's repository**:

- `deepworkplan-onboard` generates or reconciles `AGENTS.md`, `docs/`,
  per-module docs, `.agents/`, and the `.claude → .agents` symlink.
- The plan flows (`create`, `execute`, `refine`, `resume`) write plan
  artifacts under the gitignored `.dwp/` directory.
- The opt-in devcontainer addon writes devcontainer/compose files when
  explicitly invoked.

### Consent and dry-run posture

The onboarding and addon flows are designed to **propose before they write**:

- **Consent before mutation.** The `onboard` flow surfaces the planned files
  and changes for the developer to review before writing, and **reconciles**
  existing setups (it does not clobber an existing `AGENTS.md`, devcontainer,
  or `docs/` layout — it merges/extends).
- **Opt-in addons.** Addons (e.g. the devcontainer addon) are never applied
  automatically; they are layered only when the developer requests them.
- **Bounded output.** Plan artifacts are confined to `.dwp/` (gitignored by
  default), so running a plan does not pollute committed source.
- **No network, no secrets.** The skill never reads secrets, environment
  variables beyond the documented agent-detection / `DWP_*` overrides, or
  source file contents for transmission — there is nowhere to transmit to.

### Non-blocking failure mode

When a control or detection step is uncertain (e.g. `context.sh` cannot find a
git root), the skill falls back to a safe default ($PWD as repo root, `.dwp/`
under it) and continues with the developer's primary task. It never blocks work
to satisfy a check.

## Discovery Boundary (defense in depth)

Anything outside `skills/deepworkplan/` — this file, `README.md`, `.github/`,
`scripts/`, `tests/`, `docs/`, and the contributor `AGENTS.md` / `CLAUDE.md` —
is repo-development infrastructure that is **never installed** on a user's
machine. The runtime artifact's surface is bounded to one directory, which keeps
the auditable footprint small.

## Coordinated Disclosure

We follow standard coordinated disclosure: please give us a reasonable window to
ship a fix before publishing details. We will credit reporters in the
[CHANGELOG](CHANGELOG.md) and the GitHub release notes once a fix is shipped,
unless you ask to remain anonymous.
