# Template — `docker/custom_commands.sh` (reason, don't copy)

Reasoning template. The **agent-CLI wrappers**, **git-aware prompt**, and
**`check_devcontainer` helper** are stable; the **validation commands**
(`codecheck`/`check`/`fix`/`test`) are reasoned from the repo's **real** lint /
typecheck / test commands.

Sourced from the dev user's `.bashrc` (the Dockerfile appends
`source {workspaceFolder}/docker/custom_commands.sh`).

## The stable parts (keep)

- **AI-CLI wrappers** — `claudex` / `codexx` / `cursorx`: **pass-through**,
  resume-aware wrappers around `claude` / `codex` / `agent` (Cursor). They give
  agents one-word entry points with `-c/-r/-l` resume shortcuts, and forward
  every other flag **verbatim** to the wrapped CLI.
  **The wrapper never injects a permission-bypass flag.** If the developer wants
  an elevated-permission session, they pass the host CLI's own documented
  permission-mode flag (or set its permission-mode setting) themselves — the
  wrapper stays transparent so the command that actually runs is always the
  command that was typed. Wrappers that silently escalate privileges are a
  backdoor shape security scanners flag (Snyk E006), and for good reason:
  approval prompts are a safety boundary, not friction.
- **`check_devcontainer`** — detects `/.dockerenv` / `REMOTE_CONTAINERS` /
  `CODESPACES` and prints whether you're inside the container (and how to get in
  if not).
- **Git-aware prompt** (`PROMPT_COMMAND` showing branch + dirty marker) + git
  aliases (`gs`, `ga`, `gc`, `gp`, `gl`, `gd`, `gco`, `gcob`, ...).
- **Welcome message** (`show_welcome`) for interactive shells.

## The reasoned parts (fill from the repo's real commands)

Define `codecheck` / `check`, `fix`, and `test` as the repo's **verbatim** real
commands. **Never** ship `<your test command here>`.

| Alias | Maps to (examples — pick the repo's REAL command) |
|-------|---------------------------------------------------|
| `codecheck` / `check` | Python: `ruff check . && mypy .`; Django (api-services): the in-container `codecheck` (black + mypy [+ pytest]); Node: `pnpm run eslint:check && pnpm run type:check`; Astro: `astro check`. |
| `fix` | `ruff check --fix . && black .` / `pnpm run eslint:fix` / `prettier --write .`. |
| `test` | `pytest` / `pnpm test` / `vitest run` / `playwright test` — the repo's real runner + naming convention. |

```bash
#!/bin/bash
# {Project} dev container — custom commands (sourced in .bashrc)

# --- reasoned: real validation commands ---
alias check='{REAL lint+typecheck command}'
alias codecheck='{REAL validation — for api-services this runs INSIDE the container}'
alias fix='{REAL autofix command}'
alias test='{REAL test command}'

# --- stable: agent CLI wrappers (claudex / codexx / cursorx), check_devcontainer,
#     git-aware prompt, git aliases, show_welcome ---
# (copy the reference implementations near-verbatim; wrappers are PASS-THROUGH:
#  they forward flags verbatim and add only the -c/-r/-l resume shortcuts —
#  never a permission-bypass flag)
```

## Decision notes

- **Validation-in-container repos** (api-services): make clear in the welcome
  message and in the generated `AGENTS.md` that `codecheck` MUST run **inside**
  the container (DB/native deps required). The alias is the in-container entry
  point.
- **Match the repo's package manager** in `fix`/`test` (pnpm vs npm vs poetry vs
  uv) — infer from the lockfile, never habit.
- **Reconcile mode**: if `custom_commands.sh` exists, keep its wrappers/prompt
  and only correct the validation aliases to the real commands if they're wrong
  or missing.
```
