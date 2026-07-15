# Hook Enforcement — Deterministic Report Reminders

Prompt instructions (the [`triggers.md`](triggers.md) blocks) are
**probabilistic** — in long sessions the model can forget them. Lifecycle
hooks are **deterministic**: the agent harness itself runs a Dailybot CLI
command at session start, after tool use, and at the end of every turn, and
that command decides — from local state only — whether the model should be
reminded to send a progress report.

With hooks installed, reporting becomes fully autonomous: the developer logs
in once, and from then on the harness re-arms the reminders in every future
session, container, and repo. No human reminders, no reliance on the model's
memory.

> **Requires `dailybot-cli >= 3.7.0`** (the skill-pack baseline). The `dailybot hook` command group
> is available at this floor.
> Check with `dailybot --version`; if older, ask the developer to run
> `dailybot upgrade` once. Hooks installed against an older CLI fail
> gracefully (the harness ignores a missing command), but install-time is
> the right moment to get the version right.

## How it works

| Hook event (harness) | CLI command | Effect |
|----------------------|-------------|--------|
| Session start | `dailybot hook session-start --format <fmt>` | Injects context: login nudge (max once / 24 h) + unreported work left over from earlier sessions |
| After file-writing tools | `dailybot hook activity` | Records a soft work signal — catches research, analysis, and documents that never get committed |
| After a `git commit` | `dailybot hook post-commit` | Records a strong work signal |
| End of turn / stop | `dailybot hook stop --format <fmt>` | The decision point: emits a report reminder when unreported work exists, otherwise stays silent |

All commands are local-only (git + a per-repo ledger in
`~/.config/dailybot/ledger/`), never call the network, and always exit `0` —
a failure can never break the developer's session. Anti-noise gates
(30-minute minimum interval, 15-minute cooldown, snooze, per-repo opt-out)
are built into the CLI. Full reference:
[CLI docs — AGENT_HOOKS.md](https://github.com/DailybotHQ/cli/blob/main/docs/AGENT_HOOKS.md).

## Responding to a reminder (every agent, every session)

When a Dailybot reminder is injected into your context by one of these
hooks:

1. **If a meaningful unit of work is complete** — including non-commit work
   such as research, analysis, architecture decisions, written documents, or
   plans — send a report now via
   the [`dailybot-report` skill](SKILL.md). The successful
   `dailybot agent update` resets the ledger and the reminders stop.
2. **If nothing significant happened** (or the work is still mid-stream and
   you expect to keep going) — run `dailybot hook dismiss` to snooze
   reminders for an hour. Never ignore the reminder silently; either report
   or dismiss so the ledger reflects your judgment.
3. **Never block the developer's primary work** on either path.

## Installation (consent required — same rules as triggers)

Hook configs are written to the developer's harness config files. Exactly
like the auto-activation triggers in [`triggers.md`](triggers.md), this is
**opt-in**: show the file path and the exact content, explain the uninstall
path, and write only after the developer confirms. `DAILYBOT_AUTO_YES=1`
counts as consent. Merge — never overwrite — existing config files, and show
the merged result before saving.

There is no HTML-comment marker inside JSON configs; the uninstall marker is
the command string itself — every entry contains `dailybot hook`, so
removing all hook entries whose command starts with `dailybot hook` (or
deleting the dedicated file) fully uninstalls.

### Claude Code

**Path:** `~/.claude/settings.json` (user-wide) or `<repo>/.claude/settings.json`
(commit it so the whole team gets autonomous reporting).

Merge this into the existing JSON (create the file if missing):

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command", "command": "dailybot hook session-start --format claude"}]}
    ],
    "PostToolUse": [
      {"matcher": "Write|Edit|NotebookEdit",
       "hooks": [{"type": "command", "command": "dailybot hook activity"}]}
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "dailybot hook stop --format claude"}]}
    ]
  }
}
```

**Verify:** `grep -q "dailybot hook" ~/.claude/settings.json` (or the repo
file). **Uninstall:** remove the three entries.

### Cursor

**Path:** `~/.cursor/hooks.json` (user-wide) or `<repo>/.cursor/hooks.json`.

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [{"command": "dailybot hook session-start --format cursor"}],
    "afterFileEdit": [{"command": "dailybot hook activity"}],
    "stop": [{"command": "dailybot hook stop --format cursor"}]
  }
}
```

The `stop` output uses Cursor's `followup_message`, which auto-submits the
reminder as the next prompt. **Uninstall:** remove the entries or delete the
file.

### Other harnesses (Codex, Copilot, Gemini CLI, OpenCode, Windsurf)

The CLI side is identical — only the wrapper syntax differs. Use
`--format generic` (plain text on stdout) unless the harness documents a
context-injection JSON shape, and consult the harness's own hooks reference
for the exact config schema **at install time** (schemas evolve; do not
guess):

| Harness | Config location | End-of-turn event | Docs |
|---------|-----------------|-------------------|------|
| OpenAI Codex | `~/.codex/hooks.json` (user-level avoids the repo-trust prompt) | `Stop` | [developers.openai.com/codex/hooks](https://developers.openai.com/codex/hooks) |
| GitHub Copilot | `.github/hooks/dailybot.json` (repo) | `agentStop` | [docs.github.com — hooks reference](https://docs.github.com/en/copilot/reference/hooks-configuration) |
| Gemini CLI | `.gemini/settings.json` or `~/.gemini/settings.json` | `AfterAgent` | [geminicli.com/docs/hooks](https://geminicli.com/docs/hooks/) |
| OpenCode | plugin in `~/.config/opencode/plugins/` | `session.idle` | [opencode.ai/docs/plugins](https://opencode.ai/docs/plugins/) |
| Windsurf | `.windsurf/hooks.json` | `post_cascade_response` (cannot inject context — run-only) | [docs.devin.ai — hooks](https://docs.devin.ai/desktop/cascade/hooks) |

Cline has no end-of-turn hook as of this writing — rely on the
[`triggers.md`](triggers.md) prompt block there.

### Team rollout (zero per-developer setup)

Commit the repo-level config (`.claude/settings.json`,
`.cursor/hooks.json`, `.github/hooks/dailybot.json`, …) to the repository.
Every contributor — and every fresh container — gets the hooks on clone;
the only remaining per-person step is `dailybot login`, and the
`session-start` hook itself asks for that when missing.

## Per-repo controls

- `.dailybot/disabled` — silences hooks (and all skill telemetry) for a repo.
- `.dailybot/profile.json` → the `"report"` block is committed team policy.
  All keys are optional; absent keys keep the defaults:

  ```json
  {
    "report": {
      "min_interval_minutes": 30,
      "nudge": true,
      "mode": "balanced",
      "soft_turn_threshold": 8
    }
  }
  ```

  | Key | Default | Effect |
  |-----|---------|--------|
  | `min_interval_minutes` | `30` (`20` in `continuous` mode when omitted) | Minimum time between reports before reminders resume |
  | `nudge` | `true` | `false` turns reminders off for the repo while keeping manual reporting available |
  | `mode` | `"balanced"` | `"continuous"` lowers the soft-nudge thresholds for research-heavy repos so non-commit work (research, docs, analysis, plans) gets reminded sooner |
  | `soft_turn_threshold` | `8` (`5` in `continuous` mode when omitted) | Agent turns without a report before a soft nudge is eligible |

  Invalid `mode` values fall back to `"balanced"`; invalid `soft_turn_threshold`
  values fall back to the mode default. (Part of the `dailybot-cli >= 3.7.0`
  baseline; much older CLIs ignore `mode`/`soft_turn_threshold` and stay on the balanced
  defaults.

  **Continuous mode** — for repos where a lot of valuable work never lands as a
  commit (research, design docs, analysis):

  ```json
  {
    "report": {
      "mode": "continuous"
    }
  }
  ```

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Reminders never fire | Run `dailybot hook stop` manually after a commit — any output? Then check `dailybot --version` (>= 3.7.0), `.dailybot/disabled`, and the harness config actually contains the `dailybot hook` entries |
| Reminder fires but mentions old history | Delete the repo's file under `~/.config/dailybot/ledger/` — the baseline re-anchors silently |
| Too noisy | Raise `min_interval_minutes` in `.dailybot/profile.json`, or use `dailybot hook dismiss --minutes <n>` |
| Not reminded often enough (research-heavy repo) | Set `"mode": "continuous"` (or lower `soft_turn_threshold` / `min_interval_minutes`) in `.dailybot/profile.json` |
| Harness errors on hook output | Wrong `--format` — `claude`/`cursor` emit JSON, `generic` is plain text |
