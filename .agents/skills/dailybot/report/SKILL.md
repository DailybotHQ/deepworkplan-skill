---
name: dailybot-report
description: Report work progress to Dailybot. Activate after completing a discrete task or subtask, or after any batch of edits that modifies 3 or more files. Compose a standup-style update describing what changed and why.
version: "3.10.3"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: true
metadata: {"openclaw":{"emoji":"📡","homepage":"https://dailybot.com","requires":{"anyBins":["dailybot","curl"]},"primaryEnv":"DAILYBOT_API_KEY","install":[{"id":"cli-install-script","kind":"download","url":"https://cli.dailybot.com/install.sh","label":"Install Dailybot CLI (official script — preferred on Linux/macOS)"},{"id":"pip","kind":"pip","package":"dailybot-cli","bins":["dailybot"],"label":"Install Dailybot CLI via pip (fallback if binary fails)"}]}}
allowed-tools: Bash, Read, Grep, Glob
---

# Dailybot Progress Report

You help developers keep their team informed. After completing tasks or making broad edits, you send a short progress update to Dailybot. The update reads like a human giving their daily standup — no one should be able to tell it came from an agent.

---

## Agent Compatibility

This skill works across all major AI coding agents. Execution paths differ slightly but the logic is identical.

| Agent | Skill path | Activation |
|-------|-----------|-----------|
| Claude Code | `~/.claude/skills/dailybot/report/` | `/dailybot_report` slash command |
| OpenClaw | `<workspace>/skills/dailybot_report/` or `~/.openclaw/skills/` | `/dailybot_report` slash command |
| Cursor | `~/.cursor/skills/dailybot/report/` | Natural language trigger |
| OpenAI Codex | `~/.codex/skills/dailybot/report/` | Natural language trigger |
| Windsurf | `~/.codeium/windsurf/skills/dailybot/report/` | Natural language trigger |
| GitHub Copilot | `~/.copilot/skills/dailybot/report/` | Natural language trigger |
| Cline | `~/.cline/skills/dailybot/report/` | Natural language trigger |
| Gemini CLI | `~/.gemini/skills/dailybot/report/` | Natural language trigger |

When natural language triggers apply, the skill activates on phrases like: "report this to Dailybot", "send a Dailybot update", "let my team know what we built".

---

## Step 0 — Optional Auto-Activation Setup (First Run Only)

Auto-activation makes Dailybot reporting fire automatically in future sessions
without the developer invoking the skill each time. **It is opt-in.** Writing
to a global agent config file (`CLAUDE.md`, `AGENTS.md`, etc.) affects every
future session in every repository, including unrelated work — so the
developer must explicitly approve it the first time.

There are **two independent opt-ins**, and you should consider both every
first run:

- **Step 0a — Prompt trigger** (works on every agent): a standing
  instruction in the global config file.
- **Step 0b — Hook enforcement** (harnesses with a hook
  system): deterministic, harness-driven reminders.

Check each one separately. **Having the trigger installed does NOT mean
hooks are installed** — a returning developer who accepted the trigger in
an older version still needs the hook offer. Never skip Step 0b just because
Step 0a is already done; only skip an opt-in whose own check shows it is
present.

### Step 0a — Check if the prompt trigger is already installed

Identify which agent you are and run the corresponding check:

| Agent | Check |
|-------|-------|
| Claude Code | `grep -q "dailybot-auto-activation" ~/.claude/CLAUDE.md 2>/dev/null && echo "installed"` |
| OpenClaw | *(skip — OpenClaw loads this skill natively on every eligible session)* |
| Cursor | `test -f ~/.cursor/rules/dailybot.mdc && echo "installed"` |
| Codex | `grep -q "dailybot-auto-activation" ~/.codex/AGENTS.md 2>/dev/null && echo "installed"` |
| Windsurf | `test -f .windsurf/rules/dailybot.md && echo "installed"` |
| Copilot | `grep -q "dailybot-auto-activation" ~/.agents/AGENTS.md 2>/dev/null && echo "installed"` |
| Cline | `grep -q "dailybot-auto-activation" ~/.cline/.clinerules 2>/dev/null && echo "installed"` |
| Gemini CLI | `grep -q "dailybot-auto-activation" ~/.gemini/GEMINI.md 2>/dev/null && echo "installed"` |

If output says "installed" — the prompt trigger is set; **skip the rest of
Step 0a and go to Step 0b** (do not skip to Step 1).

#### If missing — ask before creating

Read [`triggers.md`](triggers.md) for the exact file path and content for the
current agent.

If `DAILYBOT_AUTO_YES=1` is set in the environment, treat consent as already
given — write the trigger block straight away and skip the prompt below.
Otherwise, show the developer this prompt **before writing anything**:

> "Dailybot reporting can run automatically after every task or broad edit,
> across all your future sessions. To set that up, I'd add the block below to
> **`<file path>`**:
>
> ```
> <exact content from triggers.md, including the
> dailybot-auto-activation markers>
> ```
>
> This affects **every repository** you open with this agent. To uninstall
> later, delete the marked block — see the `Uninstall` section in the README.
>
> **Should I add it now?** (yes / no / not now)"

- **Yes** — write the trigger block exactly as shown, including the
  `dailybot-auto-activation` opening and closing markers from `triggers.md`,
  then continue to Step 0b.
- **No / not now** — skip the trigger for this session and continue to
  Step 0b (hooks are a separate opt-in worth offering even if the trigger
  was declined). Do not re-ask about the trigger in the same session.

If the developer accepts, briefly confirm:

> "Added. From your next session onward, Dailybot reporting fires
> automatically. Remove the marked block in `<file path>` to disable."

Then continue to **Step 0b** (do not skip to Step 1 — hooks are a separate
opt-in).

### Step 0b — Hook enforcement (recommended)

Trigger blocks are advisory — the model can forget them in long sessions.
The CLI ships a `dailybot hook` command
group that the harness itself invokes at session start, after file edits,
and at the end of every turn, making the reminders **deterministic**. This
is what makes reporting truly autonomous, so offer it whenever it is
available — including to developers who already accepted the Step 0a
trigger in a previous session.

#### Check whether hooks apply, and whether they are already installed

1. **CLI version.** Run `dailybot --version`. If it reports below `3.7.0`
   (or the CLI is absent), the `dailybot hook` group does not exist — skip
   Step 0b silently and continue to Step 1. The Step 0a trigger alone still
   works.
2. **Harness support.** If the current harness has no lifecycle-hook system
   (e.g. Cline today), skip Step 0b silently — Step 0a covers it.
3. **Already installed?** Check whether the hook config already references
   `dailybot hook`, and skip to Step 1 if so:

   | Agent | Check |
   |-------|-------|
   | Claude Code | `grep -rq "dailybot hook" ~/.claude/settings.json .claude/settings.json 2>/dev/null && echo "installed"` |
   | Cursor | `grep -rq "dailybot hook" ~/.cursor/hooks.json .cursor/hooks.json 2>/dev/null && echo "installed"` |
   | Codex | `grep -rq "dailybot hook" ~/.codex/hooks.json .codex/hooks.json 2>/dev/null && echo "installed"` |
   | Copilot | `grep -rq "dailybot hook" .github/hooks/ 2>/dev/null && echo "installed"` |
   | Gemini CLI | `grep -rq "dailybot hook" ~/.gemini/settings.json .gemini/settings.json 2>/dev/null && echo "installed"` |

   If output says "installed" — hooks are already set; continue to Step 1.

#### If missing — ask before creating

Read [`hooks.md`](hooks.md) for the current harness's exact config file path,
content, merge rules, and uninstall path. The **same consent rules as Step
0a apply**: show the file path and exact content before writing, merge
(never overwrite) existing config, and `DAILYBOT_AUTO_YES=1` counts as
consent. A repo-level config (`.claude/settings.json`, `.cursor/hooks.json`,
…) committed to the repository gives the whole team autonomous reporting on
clone — offer that when the developer is in a shared project.

Once hooks are wired, consider the repo's **report cadence**. For research- or
docs-heavy repos where much of the valuable work never lands as a commit, add
`"report": {"mode": "continuous"}` to the committed `.dailybot/profile.json` so
non-commit work (research, analysis, design docs, plans) is nudged sooner (a
lower interval and turn threshold). See [`hooks.md`](hooks.md) § Per-repo controls.

If the developer declines, continue to Step 1 and do not re-ask in the same
session. The Step 0a trigger still provides (probabilistic) coverage.

### Responding to injected Dailybot reminders

When a hook injects a reminder ("commits have landed since the last
report…" / "sustained work without a progress report…") into your context:

- **Meaningful unit complete** (including non-commit work — research,
  analysis, documents) → compose and send the report now (Steps 3–7).
- **Nothing significant / still mid-stream** → run `dailybot hook dismiss`
  to snooze for an hour. Either report or dismiss — never ignore the
  reminder silently.

---

## Step 1 — Verify Setup

Read and follow the authentication steps in [`../shared/auth.md`](../shared/auth.md). That file covers CLI installation, login, API key setup, and agent profile configuration.

If auth fails or the developer declines, skip reporting entirely and continue with your primary task.

---

## Step 2 — Choose Execution Path

```bash
command -v dailybot
```

- **CLI found** → Step 4A
- **CLI not found** → Step 4B (see [`../shared/http-fallback.md`](../shared/http-fallback.md) for the base curl patterns)

Both paths produce identical results. Prefer CLI — it handles auth and retries automatically. Fall back to HTTP in sandboxed environments, CI, or containers where the CLI cannot be installed.

---

## Step 3 — Detect Context

### 3a. Run the bundled script

Find `context.sh` in the `shared/` directory of the Dailybot skill pack and run it:

```bash
bash ~/.cursor/skills/dailybot/shared/context.sh
```

Adjust the base path to match your agent's skill directory (e.g., `~/.claude/skills/dailybot/`, `~/.codex/skills/dailybot/`).

Outputs JSON: `{"repo":"...","branch":"...","agent_tool":"...","agent_name":"..."}`. Capture it.

### 3b. Manual fallback (any agent)

See the header comments in [`../shared/context.sh`](../shared/context.sh) for the manual fallback commands:

```bash
# repo name
git remote get-url origin 2>/dev/null | sed 's|.*/||;s|\.git$||'

# branch
git branch --show-current 2>/dev/null
```

If git commands fail, use the current folder name for repo and `"unknown"` for branch.

Assemble metadata — include your model identifier:

```json
{
  "repo": "<repo_name>",
  "branch": "<branch_name>",
  "agent_tool": "<your_tool>",
  "agent_name": "<your_name_or_profile_name>",
  "model": "<your_model>"
}
```

Model identifier examples: `"claude-sonnet-4-6"`, `"o3"`, `"gemini-2.5-pro"`, `"gpt-4o"`.

---

## Step 4A — Send Report via CLI

> Use this path when `command -v dailybot` succeeds.
>
> **Timeout**: Allow at least 30 seconds for CLI commands to complete. Do not use a shorter timeout.

> ### Pre-flight (mandatory) — respect the repo profile
>
> **Before constructing the command, do the repo-profile pre-flight from the router:** [`../SKILL.md` § Mandatory pre-flight](../SKILL.md#mandatory-pre-flight-respect-the-repo-profile). Full procedure in [`../shared/repo-profile.md`](../shared/repo-profile.md). One-liner detection:
>
> ```bash
> ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
> [ -f "$ROOT/.dailybot/profile.json" ] && cat "$ROOT/.dailybot/profile.json"
> ```
>
> The examples below show `--name` and `--metadata` **for the case where the repo has no `.dailybot/profile.json`** (no repo profile, no pinned identity). **If a repo profile exists, omit the flags it already provides** — see the per-key table in the router. The `Plain report (with repo profile)` block at the end shows what each example collapses to in that case.

### Flag reference

| Flag | Short | Description | Omit if `.dailybot/profile.json` sets |
|------|-------|-------------|---------------------------------------|
| `--name` | `-n` | Agent worker name | `name` |
| `--profile` | `-p` | Named auth profile slug (from `agents.json`) | `profile` |
| `--metadata` | `-d` | JSON metadata (repo, branch, model, etc.) | each `default_metadata.<key>` (omit those keys from the JSON; pass only what the profile does NOT set) |
| `--json-data` | `-j` | Structured JSON data | (always pass — not affected by repo profile) |
| `--milestone` | `-m` | Mark as a milestone accomplishment | (always pass when relevant — not affected by repo profile) |
| `--co-authors` | `-c` | Co-author email or UUID (repeatable, or comma-separated) | (always pass when relevant — not affected by repo profile) |

### Plain report — no repo profile

```bash
dailybot agent update "<message>" \
  --name "<agent_name>" \
  --metadata '<metadata_json>'
```

### Rich report (multiple deliverables) — no repo profile

```bash
dailybot agent update "<message>" \
  --name "<agent_name>" \
  --json-data '<structured_json>' \
  --metadata '<metadata_json>'
```

### Milestone report — no repo profile

```bash
dailybot agent update "<message>" \
  --name "<agent_name>" \
  --milestone \
  --json-data '<structured_json>' \
  --metadata '<metadata_json>'
```

### With repo profile (the common case)

When `.dailybot/profile.json` sets `name` (and optionally `default_metadata`), the same three patterns collapse to:

```bash
# Plain
dailybot agent update "<message>" \
  --metadata '<metadata_json_minus_profile_keys>'

# Rich
dailybot agent update "<message>" \
  --json-data '<structured_json>' \
  --metadata '<metadata_json_minus_profile_keys>'

# Milestone
dailybot agent update "<message>" \
  --milestone \
  --json-data '<structured_json>' \
  --metadata '<metadata_json_minus_profile_keys>'
```

Where `<metadata_json_minus_profile_keys>` is your inline metadata **with every key already set by `default_metadata` removed** (the CLI shallow-merges them server-side; passing them inline is at best redundant, at worst overrides them silently).

Worked example — given `{"name":"CLI","default_metadata":{"repo":"cli"}}` at repo root, a plain report becomes:

```bash
dailybot agent update "Implemented X to fix Y." \
  --metadata '{"model":"claude-opus-4-7"}'
```

(no `--name`, no `repo` in `--metadata` — both come from the profile).

### Using a named profile (no repo profile)

If a non-default global profile was configured during auth setup AND there is no repo profile pinning it:

```bash
dailybot agent --profile <profile_name> update "<message>" ...
```

If a repo profile sets `profile`, omit `--profile` from the command line.

---

## Step 4B — Send Report via HTTP API

> Use this path when the CLI is unavailable. Requires `curl`. See [`../shared/http-fallback.md`](../shared/http-fallback.md) for the base patterns.

**Base URL:** `https://api.dailybot.com`
**Auth header:** `X-API-KEY: $DAILYBOT_API_KEY`

### Plain report

```bash
curl -s -X POST https://api.dailybot.com/v1/agent-reports/ \
  -H "X-API-KEY: $DAILYBOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "<agent_name>",
    "content": "<message>",
    "metadata": <metadata_json>
  }'
```

### Rich report

```bash
curl -s -X POST https://api.dailybot.com/v1/agent-reports/ \
  -H "X-API-KEY: $DAILYBOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "<agent_name>",
    "content": "<message>",
    "structured": {
      "completed": ["Deliverable 1", "Deliverable 2"],
      "in_progress": ["Item still being worked on"],
      "blockers": []
    },
    "metadata": <metadata_json>
  }'
```

### Milestone report

```bash
curl -s -X POST https://api.dailybot.com/v1/agent-reports/ \
  -H "X-API-KEY: $DAILYBOT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "<agent_name>",
    "content": "<message>",
    "is_milestone": true,
    "structured": {
      "completed": ["..."],
      "in_progress": [],
      "blockers": []
    },
    "metadata": <metadata_json>
  }'
```

### Response

A successful request returns `201` with the created report, including a
`url` field that points to where the report landed in Dailybot:

```json
{
  "id": "<uuid>",
  "url": "https://app.dailybot.com/agents/report/<uuid>",
  "...": "..."
}
```

Capture that `url` and surface it when you confirm (see Step 7). The CLI
prints the same link automatically as a `View:` line; the HTTP
`201` body above always carries the `url` too — read it from there.

---

## Step 5 — Trigger Check

Send a progress report after each of the following:

1. **Task completed** — You finished a discrete task or subtask (e.g., a todo item, a user-requested change, a bug fix, a feature).
2. **Broad edit** — You modified 3 or more files in a single batch of edits.

Once auth is set up and (if applicable) the auto-activation trigger is in
place, you do not need to re-confirm each individual report — the developer
already opted in. Don't second-guess whether the work is "significant
enough"; if either condition above is met, send the report.

If the developer explicitly asks you to report, always report regardless of these conditions.

### What to include

Every report must answer two questions:
- **What changed** — concrete outcomes, not file paths
- **Why** — the purpose or motivation behind the change

### Aggregate related work

If you completed multiple related changes, combine them into one report. Don't send 3 reports for parts of one feature — send one report covering the whole thing.

For detailed guidelines, see [`significance.md`](significance.md).

---

## Step 6 — Compose the Report

### The Human-First Principle

The developer directed the effort, made the decisions, and is accountable for the result. Your report reflects **their accomplishment**.

**Golden rule:** The reader should never be able to tell whether a human or an agent wrote the report.

- Never say "Agent completed...", "Claude did...", "I implemented...", "The AI built..."
- Focus on outcomes: what was accomplished and why it matters
- Always write in **English**, regardless of conversation language
- 1–3 sentences maximum, past tense

### Report type

**Plain report** — single bug fix, small feature, one-off task. Message + metadata only.

**Rich report** — multi-deliverable feature, major refactor, complex task. Message + structured data + optional milestone flag.

### Structured data format

```json
{
  "completed": ["Deliverable 1", "Deliverable 2"],
  "in_progress": ["Item still being worked on"],
  "blockers": ["Issue preventing progress"]
}
```

Each item: concise, human-readable string. Empty arrays are fine.

### Milestone flag

Mark a report as a milestone only when the **top-level task is fully completed** — all subtasks are done and the entire requested piece of work is wrapped up. Individual subtask completions are regular reports, not milestones. If the developer explicitly asks for a milestone, always honor it.

### Co-authors

Do not add `--co-authors` by default — Dailybot automatically credits the authenticated developer. Only add if the developer explicitly asks to credit someone else. Never guess email addresses.

### Forbidden in report messages

| Forbidden | Why |
|-----------|-----|
| File paths (`app/auth.py`) | Nobody reads paths in a standup |
| Git statistics (`+127 -12`) | Meaningless without context |
| Raw commit messages (`feat(scope): ...`) | Commit syntax is for git, not humans |
| Branch names (`pushed to dev`) | Internal workflow detail |
| Agent attribution (`Agent completed...`) | Violates the Human-First Principle |
| Plan or task IDs (`PLAN_auth`, `task-3`) | Internal identifiers |
| Non-English text | All reports must be in English |
| Vague fallbacks (`Updated code`, `Made changes`) | If you can't be specific, don't report |

For writing templates by work type, see [`writing-guide.md`](writing-guide.md).
For side-by-side examples, see [`examples.md`](examples.md).

---

## Step 7 — Confirm

After the command runs:

- **Success** — briefly confirm what was reported, and include the placement link the response returns (the `url` field, printed by the CLI as `View:`, and always present in the HTTP `201` body) so the developer can jump straight to where it landed. Example: *"Reported to Dailybot: Built the notification preferences system with full test coverage — view it at https://app.dailybot.com/agents/report/<uuid>."* If no `url` is surfaced (an older backend), just confirm the report without a link.
- **Failure** — warn briefly. Do not retry in a loop. Suggest `dailybot status --auth` for auth issues, or `dailybot logout` + `dailybot login` if the session seems stale.
- **Skipped** — say nothing. Complete silence is the correct response.

---

## Non-Blocking Rule

Reporting must **never block your primary work**. If the CLI is missing, auth fails, the network is down, or the command errors:

1. Warn the developer briefly
2. Continue with the primary task
3. Do not retry automatically
4. Do not enter a diagnostic loop

---

## Additional Resources

- [`triggers.md`](triggers.md) — auto-activation trigger templates for each supported agent
- [`hooks.md`](hooks.md) — deterministic hook enforcement: per-harness configs, reminder handling, `dismiss`
- [`significance.md`](significance.md) — when to report and when to stay silent, with edge cases
- [`writing-guide.md`](writing-guide.md) — writing templates by work type, action verbs, rate limiting
- [`examples.md`](examples.md) — 15 side-by-side good vs bad comparisons
- [`../shared/auth.md`](../shared/auth.md) — authentication setup (CLI login, API key, agent register)
- [`../shared/context.sh`](../shared/context.sh) — automated context detection
- [`../shared/http-fallback.md`](../shared/http-fallback.md) — HTTP API fallback patterns
- [`../shared/dashboard-urls.md`](../shared/dashboard-urls.md) — dashboard URL catalog (report detail pages, agent analytics, etc.)
- **Live API spec:** `https://api.dailybot.com/api/swagger/`
- **Full agent API skill:** `https://www.dailybot.com/skill.md`
