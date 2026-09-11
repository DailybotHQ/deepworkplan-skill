# Installation and agent compatibility matrix

What is actually proven about installing this pack and running it on a given
agent — and, just as importantly, what is not.

## Evidence levels

Every cell below carries one of three levels. They are not interchangeable.

| Level | Means |
| --- | --- |
| **Documented** | A route or agent is described in our docs. No test asserts it. |
| **Install-tested** | An automated fixture or a recorded run proves the files land correctly. Proves installation only. |
| **Behavior-tested** | An agent actually ran the create → execute → interrupt → resume workflow using the installed pack, and the result was inspected. |

A smoke install is never evidence of behavior. We do not publish a blanket
"works with any coding agent" guarantee, because we have not run every agent.

## Installation routes

| Route | Level | Evidence |
| --- | --- | --- |
| `npx skills add DailybotHQ/deepworkplan-skill` | **Install-tested** | Local run into an isolated project (see caveat below); release workflow also smoke-installs each published tag into a temp dir and asserts the version |
| `git clone` + `./setup.sh --host <agent>` | **Install-tested** | `tests/setup-sh.bats` exercises **every** advertised host route in an isolated `HOME` |
| `./setup.sh` (auto-detect) | **Install-tested** | `tests/setup-sh.bats`; the "no agents detected" branch skips on machines where an agent is on `PATH` |
| Manual per-agent copy/clone | **Documented** | `docs/INSTALLATION.md` method 4; same directory map `setup.sh` uses |
| OpenClaw native (`openclaw skills install`) | **Documented** | `docs/OPENCLAW.md`; no OpenClaw runtime available in our test environments |

### Caveat found while install-testing the skills CLI

Installing into a project that the CLI maps to many agent targets, **32 of those
targets failed** with `ENOENT … mkdir …/.agents/skills/deepworkplan` while the
CLI still exited `0` and printed `Done!`. The canonical
`.agents/skills/deepworkplan` directory *was* created and the per-agent
symlinks that matter (for example `.claude/skills/deepworkplan`) resolve to it,
so the install is usable — but the exit status of `npx skills add` is not a
reliable signal that every requested target succeeded. Check the printed
per-target lines, or verify the specific directory your agent reads.

This is upstream CLI behavior, not a property of this pack.

## `setup.sh` host routes

All nine advertised routes are asserted in `tests/setup-sh.bats`: the pack
symlink plus all six sub-skill symlinks must appear in the documented directory.

| `--host` | Skills directory | Level |
| --- | --- | --- |
| `claude` | `~/.claude/skills` | Install-tested |
| `cursor` | `~/.cursor/skills` | Install-tested |
| `codex` | `~/.codex/skills` | Install-tested |
| `windsurf` | `~/.codeium/windsurf/skills` | Install-tested |
| `copilot` | `~/.copilot/skills` | Install-tested |
| `cline` | `~/.cline/skills` | Install-tested |
| `gemini` | `~/.gemini/skills` | Install-tested |
| `opencode` | `~/.config/opencode/skills` | Install-tested |
| `antigravity` | `~/.antigravity/skills` | Install-tested |

Guarantees also covered by fixtures:

- **Idempotent** — a second run produces the same links without error.
- **Non-clobbering** — a real file already sitting at a skill path is left
  untouched, and the remaining routes still link.
- **No preexisting agent directory required** — `setup.sh` creates the tree.
- **No network required.**

## Runtime self-containment

The installed directory must work without this repository's `tests/`,
`scripts/`, `docs/` or `.github/`, and without the website.

- A fixture asserts that **no runtime Markdown file under
  `skills/deepworkplan/` links to repo-only infrastructure**.
- Link resolution was checked against a freshly installed pack and against the
  candidate tree: **260 local links checked in the candidate, zero broken.**
  Eight unresolved targets exist and are all *illustrative* — sample task
  filenames inside a documented example plan (`1.task_add_discord_message_handler.md`)
  and `{N}` template placeholders in the orchestrator templates. They are
  prose, not navigation.
- Bash 3.2 compatibility is preserved (no `mapfile`, associative arrays, or
  `${var^^}` in shipped scripts); CI runs the installer on macOS and Linux.

## Agent behavior

Installation says nothing about whether an agent can *run* the workflow. An
agent needs tool execution and repository permissions; no installer can supply
those.

| Agent | Level | Evidence |
| --- | --- | --- |
| Claude Code (Anthropic) | **Behavior-tested** | Behavioral evaluation scenarios; authored and resumed plans in the bidirectional handoff (both directions passed) |
| OpenAI Codex (`codex-cli` 0.153.4, reported model GPT-6) | **Behavior-tested** | Authored and resumed plans in the bidirectional handoff (both directions passed); also the truncated instrumented arms, which produce no efficiency claim |
| Cursor, Windsurf, Copilot, Cline, Gemini, OpenCode, Antigravity | **Install-tested only** | Directory routes asserted; no workflow run recorded |

### Portable sequential path

The methodology's required path is plain file reads, edits and shell commands.
Slash commands, hooks, subagents and proprietary task APIs are conveniences: when
they are absent the sequential path still works. What an agent cannot do without
is executing tools and reading/writing the repository.

## Lite and Full plans

The Lite/Full lifecycle is **structurally tested** by `tests/lite-plans.bats` and
the schema-contract checker: a ready Lite plan with inline task locators passes
conformance, unsafe locators fail, and legacy v1 plans retain their v1 schema
path. This is not a claim that every listed agent has behavior-tested Lite
creation. The portable contract is Markdown plus JSON and shell validation, so
agents that can read and write their workspace can follow it; behavior evidence
continues to be recorded per harness above.

## Cross-agent handoff

See [the handoff record](evaluations/cross-agent-handoff.md) for the
bidirectional (A→B and B→A) interrupted-plan experiment, its results, and its
limits.
