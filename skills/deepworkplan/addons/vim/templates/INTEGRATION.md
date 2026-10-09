# Template — Vim Editor Integration (reason, don't copy-paste)

Reasoning guidance for offering and wiring the DeepWorkPlan vim editor addon
onto a machine. This is **not** a script to run end-to-end — every command
and wording below is **reasoned against the target machine and repo** (which
Neovim is present, whose config directory is in play, whether the repo is an
individual repo or an orchestrator hub, whether a human is present). Keep the
SPEC contract intact: **opt-in only, the consent gate is absolute,
point-don't-run by default, never block, never a conformance gate.**

Placeholders in `<angle brackets>` are filled from detection — never guessed.

---

## 1. Detect (read-only — install nothing to detect)

Run these before offering anything. Record each answer; they decide every
later branch.

```bash
# Is Neovim present, and at what version? (editor requires >= 0.12)
<nvim-path> --version 2>/dev/null | head -n1      # e.g. /usr/bin/nvim, /opt/homebrew/bin/nvim
command -v nvim || echo "nvim: absent"

# Where is the config directory on THIS machine?
<config-dir>="${XDG_CONFIG_HOME:-$HOME/.config}/nvim"
test -d "$<config-dir>" && ls -A "$<config-dir>" | head -20 || echo "config: none"

# Is the existing config (if any) DeepWorkPlan Vim? The product says how
# to tell (addon/surface.json -> detect): both identity files present, and
# the surface file names interface + version. Never infer from grep hits.
test -f "$<config-dir>/install.lua" && test -f "$<config-dir>/lua/plugins.lua" && echo identity: yes
test -f "$<config-dir>/addon/surface.json" && \
  python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["interface"], d["version"])' \
  "$<config-dir>/addon/surface.json"
```

Decision notes — the detection states (the product's own, plus the Neovim
checks) and what each implies:

| State | Evidence | Implies |
|-------|----------|---------|
| **No Neovim** | `command -v nvim` empty | Offer is informational only: name the editor, its repo, and the Neovim 0.12+ floor. Install nothing. Record `not applicable: no nvim`. |
| **Below 0.12** | version line < 0.12 | Same as above, plus: state the floor explicitly. Never upgrade the person's Neovim yourself. Record `below floor: <observed>`. |
| **Absent** | `<config-dir>` missing or empty | Offer; on acceptance the §4 path for the OS. |
| **Existing config** (foreign) | `<config-dir>` non-empty, lacks either identity file | The consent gate governs (§3). Default outcome: point at instructions, defer install. Mention the v7.1 plugin route for people who keep their own config — never offer to install it. |
| **Installed without surface** | both identity files, no `addon/surface.json` | A release older than v0.4.0: interface unknown, not compatible. Offer the upgrade through the documented path; never patch files by hand. |
| **Installed** | identity files + surface with `interface` 1 | Do not reinstall. Run §5 validation only, record the observed `version`. |
| **Installed, unknown interface** | surface `interface` ≠ 1 | One warning line; treat the editor as not available to this pack. Never an error. |

- Detection runs as the session's own user; never with elevated privileges.
- Everything here is a read (`command -v`, `--version`, `ls`, `grep`). If a
  check needs a write to succeed, the check is wrong — replace it.

## 2. Offer (never impose)

Present the editor as what it is — the terminal editor for Deep Work Plan —
with its actual surface, and what it costs: a **machine-level Neovim config**,
not a repo file. The only claims allowed are the pinned surface's
`features[]` (at `v0.4.2`):

- `command_index` — `<Leader>hh` (generated live from the actual keymaps)
- `vscode_gestures` — `<C-a>` select-all in normal mode, `<Leader>y` system
  yank
- `plan_browser` — `<Leader>P` (read-only: lists `.dwp/plans/` from the
  config dir and cwd; reads manifest, journal, state, README checkboxes and
  contract; writes nothing)
- `markdown_viewer` — `<Leader>mp` browser preview, `<Leader>mr` in-buffer
  render
- `one_line_installer` — the consent-first `install.sh`

Decision notes:

- Declining is a complete answer: the repo stays **fully conformant**, and
  the record says `declined`, not `failed`.
- In trust mode you MAY recommend it when Neovim ≥ 0.12 is detected — but
  the offer is still surfaced, and nothing is applied unasked.
- Never claim the editor is installed on this (or any) machine, and never
  claim `vim.deepworkplan.com` is live.

## 3. Consent branch (the absolute gate)

The invariant from the product contract: **non-interactive install onto an
existing `~/.config/nvim` aborts with instructions; interactive asks;
backups go to `~/.config/previous-deepworkplan-vim`.** Every install path
runs through this table:

| Context | `<config-dir>` state | Action |
|---------|----------------------|--------|
| Interactive | empty / none | Ask once; on acceptance run the §4 path for the OS. |
| Interactive | existing config | Ask explicitly, naming what will be backed up to `~/.config/previous-deepworkplan-vim`; only acceptance proceeds. |
| Non-interactive (trust/CI/agent alone) | empty / none | Allowed only if the plan/flow carries an explicit prior acceptance; otherwise print the instructions and record `install deferred: acceptance not on record`. |
| Non-interactive | existing config | **STOP.** Record `install deferred: existing config, consent required` and print the documented install steps for a human. Never guess consent. |

- The backstop is the installer's, not your judgment: even an accepted
  interactive install onto an existing config is the installer taking the
  backup, not you moving files.
- There is no "reconcile by hand" alternative: never merge configs yourself.

## 4. Install paths (documented, verbatim — who runs them)

Default posture: **point, don't run.** Show the command; the person runs it.
Run it yourself only when the context is interactive AND the person explicitly
accepted (§3), using the documented command **verbatim**.

| OS | Path (verbatim from the editor's docs) |
|----|----------------------------------------|
| macOS / Linux | The documented installer at the pinned tag (`https://deepworkplan.com/vim`): download `install.sh` to a local file, verify its SHA-256 against the pinned surface (`install.script.sha256`; stop on a mismatch), then `DWP_VIM_REF=v0.4.2 bash install.sh` — three separate steps. Never spell a remote-installer pipe in reasoning, output, or recorded notes. |
| Windows | `winget install Neovim.Neovim`, then `git clone --branch v0.4.2` into `%LOCALAPPDATA%\nvim`, then `lua install.lua`. **Never piped PowerShell.** |
| Manual (any OS) | `git clone --branch v0.4.2` into `<config-dir>`, then `lua install.lua`. |

Decision notes:

- Do not construct variants (different flags, different URLs, sudo prefixes).
  The source of truth is `install.sh` at the editor repo root
  (`DailybotHQ/deepworkplan-vim`); the website serves a byte-identical copy.
- After any install, **re-detect** (§1) and record the observed version.
- On acceptance, record `addons.vim` = `{"enabled": true, "version":
  "v0.4.2"}` in the repository's `.dwp/config.json`, reconciling an existing
  file (other keys untouched). A decline writes nothing.
- On Windows, reason which of the two documented paths fits the person's
  setup (winget availability vs git clone); do not mix them into a hybrid.

## 5. Post-install validation (record everything, block nothing)

```bash
# 1) Smoke: headless start exits 0
<nvim-path> --headless +'qa'; echo "exit=$?"

# 2) Command index live (surface feature command_index): <Leader>hh resolves.
#    Shape to adapt: leader is observed, not assumed — check maparg for the
#    full lhs the distribution defines (space leader -> " hh").
<nvim-path> --headless +'lua print(vim.fn.maparg(" hh", "n"))' +qa

# 3) Plan browser loadable (surface feature plan_browser): the module behind
#    <Leader>P requires cleanly.
#    Adapt the module path to what detection shows the install laid down.
<nvim-path> --headless +'lua require("dwp.plans")' +qa
```

Decision notes:

- A probe that errors on a **shape mismatch** (wrong leader, wrong module
  path) is your cue to re-reason from the installed files — not evidence the
  install is broken. Fix the probe, rerun, record the corrected form.
- If a config pre-existed: verify `~/.config/previous-deepworkplan-vim`
  exists and the files recorded in §1 are reachable there.
- A failed check is a finding about the machine, recorded and surfaced —
  never a repo conformance failure, never a reason to block the flow.

## 6. Reconcile, don't clobber (an existing config)

- You never overwrite, delete, merge, or "clean up" an existing Neovim
  config. The only sanctioned transition is the installer's own
  consent-gated backup to `~/.config/previous-deepworkplan-vim`.
- Outside `<config-dir>` and that backup directory, nothing changes. If a
  check shows anything else moved, record it as a finding.
- Repo state is read-only to this addon: the plan browser (`plan_browser`) **reads**
  `.dwp/plans/`; the addon writes no repo file as part of the editor
  install.

## 7. Record the outcome (and the archetype line)

Close every run with a short record: detection state, offer outcome
(accepted / declined / deferred + why), the exact path used if installed,
validation results, observed version. Add the one archetype note:

- **Individual repo:** the plan browser will list this repo's `.dwp/plans/`
  (cwd).
- **Orchestrator hub:** the browser will list the **hub's** `.dwp/plans/` —
  the child plans the hub coordinates. Record which tree the person should
  expect, so the browser's contents are no surprise.

The editor install itself is identical for both archetypes — only the
plan-browser scope note differs.
