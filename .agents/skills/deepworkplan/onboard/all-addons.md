# DeepWorkPlan — Onboard: detect every addon, upgrade the ones in use, offer the ones that fit (read only when triggered)

Read this file in Phase 7b when the developer asks to set up or update the
repository's addons ("which addons fit here?", "bring my addons up to date"),
or on a **harness upgrade** (Phase 0) of a repository that already has addons.
A single-addon offer stays in [`addons.md`](addons.md). Nothing here weakens
an addon's own rules: each addon's `SKILL.md` still owns its consent, its
install and its validation.

**What goes where.** The pack and the required AI Diff Reviewer local review
go into **every** repository. Every other addon goes only where it fits: an
installed one the repository still uses is upgraded in place to the pack's
pin, one that fits is offered, and nothing is added just to complete the set.

## 1. Plan (read-only)

```bash
python3 ../shared/addon_sync.py plan --repo <repo>          # table
python3 ../shared/addon_sync.py plan --repo <repo> --json   # same plan, schema dwp-addon-sync/v1
```

For every addon the pack ships, the planner reads its detection (the
descriptor's command or path), the vendored skill (`.agents/skills/<name>/`
and `skills-lock.json`), the repository registry (`.dwp/config.json`) and, for
the dev container, the repository layout. It prints one row per addon with
the installed version, the pack's pin and one action:

| Action | Meaning | What you do |
|--------|---------|-------------|
| `install` | absent | offer it; on acceptance run the addon's flow |
| `upgrade` | older than the pin (or an old release without its surface) | offer the upgrade; on acceptance run the addon's flow at the pin |
| `record` | at the pin (or newer), registry missing or stale | run the row's `record` command — only for an addon the developer uses |
| `current` | at the pin and recorded | nothing |
| `newer` | newer than the pin | keep it — **never downgrade** |
| `reconcile` | hand-written work present (a docker setup without dck) | the addon's diff-and-consent flow (§3) |
| `verify` | detected, version unreadable | re-run its detection by hand; report |
| `declined` | the registry records a decline | do not re-offer |
| `evaluate` | applicability is the addon's call (design-system) | run that addon's detection |
| `not-applicable` | nothing to install for | nothing |

The planner writes nothing and runs no installer. Running it twice on an
unchanged repository prints the same plan.

## 2. Offer once, then work row by row

Show the table and make **one** consolidated offer: per row, its action and
what it costs (machine-level installs, Docker, accounts). The developer may
accept all, some or none; a decline writes nothing, and only an explicit
"turn it off" is `config.py disable <key>`. Trust mode may recommend rows; it
accepts none of the signal-gated ones by itself (`addons.md`).

Work the accepted rows in this order, because later addons consume earlier
ones: **ai-diff-reviewer** (Phase 7a, required) → **dependency-upgrade** →
**design-system** → **dailybot** → **agentkit** → **herdr** → **vim** →
**devcontainer** (its layers use the others, §3).

For each accepted row:

1. Read the addon's `SKILL.md` and run its flow for the row's action.
   - **Repository skills** (ai-diff-reviewer, dailybot): an upgrade is the
     same tree-URL-pinned `skills add` line the addon documents, which
     replaces only the vendored copy; `.review/extension.md` and every other
     hand-written file stay. Verify the installed `version:` equals the pin
     (`../shared/install-verification.md`).
   - **In-pack addons** (dependency-upgrade, design-system): an existing
     `/lib-upgrade` delegator or `DESIGN.md` is the repository's own work —
     reconcile on request, never regenerate.
   - **Machine-level products** (agentkit, herdr, vim, the dck kit): §4.
2. On success, run the row's `record` command (the planner prints it with
   the pin). It reconciles `.dwp/config.json`: other keys stay.
3. Re-run the planner. The row must now read `current` (or `newer`); if not,
   report what it says — never mark it done on your own word.

**Idempotency:** a second pass over a finished repository finds every row
`current`, `newer`, `declined`, `evaluate` or `not-applicable`, runs nothing
and writes nothing.

## 3. The dev container: the full working stack

When the developer wants the repository to run in a container, finish with
the whole stack, not a bare Dockerfile. The reference is a repository where
one `bash dev.sh up` brings up the app, the editor, the agents and the
Herdr workspace.

1. **Render** with the kit (`../addons/devcontainer/SKILL.md`). An existing
   layout (`reconcile`) goes through `dck init --dry-run` first: every
   `replace` is shown as a diff, nothing changes without consent, and each
   changed file is backed up first.

   ```bash
   dck init --dry-run --agents --clis "<the CLIs the developer chose>" \
     <--editor|--no-editor> <--herdr|--no-herdr> --port <name>=<port>
   dck init …the same flags…   # after the diff was accepted
   ```

   `--editor` only when the vim addon was accepted, `--herdr` only when the
   herdr addon was; otherwise pass `--no-editor` / `--no-herdr`.

   - `[agents] clis`: **only** the CLIs the developer names; none by default.
   - `[layers] editor = true` when the vim addon is on; `[layers] dailybot = true`
     when the dailybot addon is on (set in `.devcontainer/dck.toml`, then
     `dck init` again).
   - `[herdr] machine = true`, `layout = "standard"` (App · Editor ·
     Development · Agents, every pane opening in the workspace, `/app` by
     default) and `mesh = true` (Docker Desktop; it widens trust between
     containers — say so).
2. **Start hook** where the stack needs one: `docker/local/dev-setup-hook.sh`,
   run by the container at every start as the dev user from the workspace
   (build caches off the bind mount, generated files). It is the repository's
   own code: write it only for a real need the stack shows.
3. **Host accounts** (optional; `../addons/devcontainer/SKILL.md`, host
   accounts): to let agents inside use the developer's own accounts, the
   developer sets `[agents] host_profiles = true` (optionally
   `host_profile_names` and exact `host_env_keys`) in
   their **host** profile `~/.config/dck/profile.toml` — never the repository.
   Claude then authenticates through the profile's token
   (`CLAUDE_CODE_OAUTH_TOKEN[_<SUFFIX>]` in the `ak` env file), Codex through
   its auth file; one active writer per Codex account. Describe it; never
   set it.
4. **Bring it up:** `bash dev.sh up` (builds, starts, registers the Herdr
   machine and opens the layout). A failed build is a failed run.
5. **Verify** and record each result:

   | Check | Expect |
   |-------|--------|
   | `dck doctor --json` | `interface` 2, repo config valid, no drift, the layers you chose |
   | `bash dev.sh exec ak doctor --json` | the chosen CLIs; `permissions` `auto` (or `ask` when opted out — expected, not a failure) |
   | `bash dev.sh exec ak usage --json` | each shared account answers (only with host profiles on) |
   | `herdr workspace list` | the container's workspace with the four panes |
   | `bash dev.sh exec ssh -T git@github.com` | the greeting through the host agent (exit 1 with a greeting is success) |
   | `bash dev.sh exec gh auth status` | logged in, when the repository uses `gh` |
   | the repository's real test command, inside | passes, or the failure is recorded |

Then `config.py enable devcontainer --version <pin> --repo <repo>`.

## 4. Machine-level pieces: point, don't run

`ak`, `dck`, the herdr-peers host install and the editor change the developer's
machine, not the repository. Show the commands; run them only when the
developer accepts, in an interactive session.

The exact, verified install and upgrade sequence for each machine-level
product — tagged clone, tag check, the release's `SHA256SUMS` checked against
the tree, then the product's own installer — is
[`../addons/machine-installs.md`](../addons/machine-installs.md). Re-detect
afterwards; the interface must match the descriptor.

Never pipe a download into a shell, never install a coding-agent CLI the
developer did not choose, and never set an autonomy flag: the kit's default
and its opt-out (`AGENTKIT_PERMISSIONS=ask`) decide.

## 5. Report

One line per addon: action taken, version before → after, the record
written, and anything left for the developer (a declined row, a machine
install shown but not run, a failed check). Re-run the planner and include
its `pending:` line — `nothing` is the only "addons done".
