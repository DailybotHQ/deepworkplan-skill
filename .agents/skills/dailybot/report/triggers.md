# Auto-Activation Triggers

This file contains the exact trigger templates for each supported agent. A
trigger is a small always-on instruction that tells the agent to invoke
Dailybot skills after completing tasks or making broad edits — primarily the
`dailybot-report` skill, but also to check messages at session start and send
periodic health checks.

> **Prefer hooks where available.** Trigger blocks are prompt instructions —
> advisory, and forgettable in long sessions. With `dailybot-cli`
> the harness can enforce reporting deterministically via lifecycle hooks;
> see [`hooks.md`](hooks.md). Install both when possible: the trigger block
> teaches the behavior, the hooks guarantee it. On harnesses without hook
> support (e.g. Cline), the trigger block is the only mechanism.

Step 0 in [SKILL.md](SKILL.md) uses these templates **only after the developer
explicitly confirms** the skill should write to a global agent config file.
Each template is wrapped in a marker so the block can be located and removed
later:

```
<!-- dailybot-auto-activation: BEGIN -->
...content...
<!-- dailybot-auto-activation: END   (delete this block to disable) -->
```

To uninstall on any agent, search for `dailybot-auto-activation` in the file
listed below and delete from BEGIN to END (inclusive).

---

## Cursor

Cursor uses `.mdc` rule files with YAML frontmatter.

**Path**: `~/.cursor/rules/dailybot.mdc`

**Create this file** with the following content (the file existing IS the
opt-in marker — to uninstall, delete the file):

```
---
description: Invoke Dailybot skills for progress reporting, message checking, and team coordination
alwaysApply: true
---
<!-- dailybot-auto-activation: BEGIN — delete this file to disable -->
Send a progress report to Dailybot after each of the following: (a) completing a discrete task or subtask, or (b) after any batch of edits that modifies 3 or more files. Compose a standup-style update describing what changed and why. Use the `dailybot-report` skill to send the report.

At the start of a work session, check for pending messages from the team using the `dailybot-messages` skill.

During long sessions (15+ minutes), send periodic health checks using the `dailybot-health` skill.
<!-- dailybot-auto-activation: END -->
```

**Verify**: `test -f ~/.cursor/rules/dailybot.mdc`

---

## Claude Code

Claude Code reads `CLAUDE.md` files for persistent instructions.

**Path**: `~/.claude/CLAUDE.md`

**Append** the following block to the end of the file (create the file if it
doesn't exist):

```
<!-- dailybot-auto-activation: BEGIN -->
## Dailybot

Send a progress report to Dailybot after each of the following: (a) completing a discrete task or subtask, or (b) after any batch of edits that modifies 3 or more files. Compose a standup-style update describing what changed and why. Use the dailybot-report skill to send the report.

At the start of a work session, check for pending messages using the dailybot-messages skill. During long sessions, send periodic health checks using the dailybot-health skill.

User command: /dailybot_report. Agent-only skills: dailybot-messages, dailybot-email, dailybot-health.
<!-- dailybot-auto-activation: END   (delete this block to disable) -->
```

**Verify**: `grep -q "dailybot-auto-activation" ~/.claude/CLAUDE.md 2>/dev/null`

---

## OpenAI Codex

Codex reads `AGENTS.md` files for persistent instructions.

**Path**: `~/.codex/AGENTS.md`

**Append** the following block to the end of the file (create the file if it
doesn't exist):

```
<!-- dailybot-auto-activation: BEGIN -->
## Dailybot

Send a progress report to Dailybot after each of the following: (a) completing a discrete task or subtask, or (b) after any batch of edits that modifies 3 or more files. Compose a standup-style update describing what changed and why. Use the dailybot-report skill to send the report.

At the start of a work session, check for pending messages using the dailybot-messages skill. During long sessions, send periodic health checks using the dailybot-health skill.

User-invocable: dailybot-report. Agent-only: dailybot-messages, dailybot-email, dailybot-health.
<!-- dailybot-auto-activation: END   (delete this block to disable) -->
```

**Verify**: `grep -q "dailybot-auto-activation" ~/.codex/AGENTS.md 2>/dev/null`

---

## Windsurf

Windsurf uses global rules managed through Settings, or files in
`.windsurf/rules/`.

**Preferred**: Ask the developer to add a global rule through
**Settings > Cascade > Rules** with activation mode **Always On** and the
content below.

**Alternative** — if the developer prefers a file, create a workspace rule
(deleting the file disables the trigger):

**Path**: `.windsurf/rules/dailybot.md`

```
---
trigger: always_on
---
<!-- dailybot-auto-activation: BEGIN — delete this file to disable -->
Send a progress report to Dailybot after each of the following: (a) completing a discrete task or subtask, or (b) after any batch of edits that modifies 3 or more files. Compose a standup-style update describing what changed and why. Use the `dailybot-report` skill to send the report.

At the start of a work session, check for pending messages using the `dailybot-messages` skill. During long sessions, send periodic health checks using the `dailybot-health` skill.
<!-- dailybot-auto-activation: END -->
```

**Verify**: Ask the developer if Dailybot appears in their Windsurf rules, or
check `test -f .windsurf/rules/dailybot.md`

---

## GitHub Copilot

Copilot reads `AGENTS.md` files for agent instructions.

**Path**: `~/.agents/AGENTS.md`

**Append** the following block to the end of the file (create the file if it
doesn't exist):

```
<!-- dailybot-auto-activation: BEGIN -->
## Dailybot

Send a progress report to Dailybot after each of the following: (a) completing a discrete task or subtask, or (b) after any batch of edits that modifies 3 or more files. Compose a standup-style update describing what changed and why. Use the dailybot-report skill to send the report.

At the start of a work session, check for pending messages using the dailybot-messages skill. During long sessions, send periodic health checks using the dailybot-health skill.

User-invocable: dailybot-report. Agent-only: dailybot-messages, dailybot-email, dailybot-health.
<!-- dailybot-auto-activation: END   (delete this block to disable) -->
```

**Verify**: `grep -q "dailybot-auto-activation" ~/.agents/AGENTS.md 2>/dev/null`

---

## Cline

Cline reads `.clinerules` files for persistent instructions.

**Path**: `~/.cline/.clinerules`

**Append** the following block to the end of the file (create the file if it
doesn't exist):

```
<!-- dailybot-auto-activation: BEGIN -->
## Dailybot

Send a progress report to Dailybot after each of the following: (a) completing a discrete task or subtask, or (b) after any batch of edits that modifies 3 or more files. Compose a standup-style update describing what changed and why. Use the dailybot-report skill to send the report.

At the start of a work session, check for pending messages using the dailybot-messages skill. During long sessions, send periodic health checks using the dailybot-health skill.
<!-- dailybot-auto-activation: END   (delete this block to disable) -->
```

**Verify**: `grep -q "dailybot-auto-activation" ~/.cline/.clinerules 2>/dev/null`

---

## OpenClaw

OpenClaw uses the AgentSkills-compatible `SKILL.md` format natively.
**No trigger file is needed** — OpenClaw loads skills automatically on every
eligible session based on gating rules in the frontmatter `metadata` field.

**Install via ClawHub (recommended):**

```bash
openclaw skills install dailybot
```

**Install manually:**

```bash
git clone https://github.com/DailybotHQ/agent-skill.git <workspace>/skills/dailybot
```

**Configure API key** in `~/.openclaw/openclaw.json`:

```json
{
  "skills": {
    "entries": {
      "dailybot": {
        "enabled": true,
        "apiKey": { "source": "env", "provider": "default", "id": "DAILYBOT_API_KEY" }
      }
    }
  }
}
```

The `/dailybot` router and `/dailybot_report` register as slash commands. The
messages, email, and health skills are agent-only (not user-invocable) and
activate autonomously. No trigger setup required.

---

## Gemini CLI

Gemini CLI reads `GEMINI.md` for persistent instructions.

**Path**: `~/.gemini/GEMINI.md`

**Append** the following block to the end of the file (create if it doesn't
exist):

```
<!-- dailybot-auto-activation: BEGIN -->
## Dailybot

Send a progress report to Dailybot after each of the following: (a) completing a discrete task or subtask, or (b) after any batch of edits that modifies 3 or more files. Compose a standup-style update describing what changed and why. Use the dailybot-report skill to send the report.

At the start of a work session, check for pending messages using the dailybot-messages skill. During long sessions, send periodic health checks using the dailybot-health skill.

User-invocable: dailybot-report. Agent-only: dailybot-messages, dailybot-email, dailybot-health.
<!-- dailybot-auto-activation: END   (delete this block to disable) -->
```

**Verify**: `grep -q "dailybot-auto-activation" ~/.gemini/GEMINI.md 2>/dev/null`

---

## Skill installation paths

After running `./setup.sh`, symlinks are created for each sub-skill:

| Agent | Pack path | Symlinked sub-skills |
|-------|-----------|---------------------|
| Cursor | `~/.cursor/skills/dailybot/` | `~/.cursor/skills/dailybot-report/`, `-messages/`, `-email/`, `-health/` |
| Claude Code | `~/.claude/skills/dailybot/` | `~/.claude/skills/dailybot-report/`, `-messages/`, `-email/`, `-health/` |
| OpenAI Codex | `~/.codex/skills/dailybot/` | `~/.codex/skills/dailybot-report/`, `-messages/`, `-email/`, `-health/` |
| Windsurf | `~/.codeium/windsurf/skills/dailybot/` | same pattern |
| GitHub Copilot | `~/.copilot/skills/dailybot/` | same pattern |
| Cline | `~/.cline/skills/dailybot/` | same pattern |
| Gemini CLI | `~/.gemini/skills/dailybot/` | same pattern |
| OpenClaw | `<workspace>/skills/dailybot/` | native discovery, no symlinks needed |

Cursor also reads from `~/.claude/skills/` and `~/.codex/skills/` for
compatibility. Windsurf also reads from `~/.agents/skills/` for compatibility.
Copilot also reads from `~/.claude/skills/` and `~/.agents/skills/` for
compatibility.
