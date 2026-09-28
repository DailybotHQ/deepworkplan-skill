# listing.md — listing the live mesh

Proposed v7 flow; the v6 onboarding and execution paths do not invoke it.

## The user-facing rule

When a person says any of these — "list the Herdr agents", "who is
available", "show the mesh", "list agents" — **list them
now**. Do not describe the command. Do not answer from a table seen
earlier. Do not say "you can run herdr machine list". Run the list and
print the table. The list is live: agents appear and disappear, a rebuild
does not refresh an old table, and an old table is not a directory.

If `herdr` is not on PATH, say so and show the install paths from SKILL.md
§0. Do not invent a list.

## How to build the list

Use `herdr` only — no product launcher. Run as the session user, never as
root: the catalog and `known_hosts` are per-user, and a root shell often
sees an empty mesh while the real user sees the fleet.

1. `herdr pane current` — this session's pane id and terminal id. Timeout
   8 seconds. If it fails, this session is not a row; say so, and still
   list everyone else.
2. `herdr machine list --json` — timeout 12 seconds. Keep objects that are
   enabled and have an id. Disabled machines are not part of the live mesh.
3. For each enabled machine: `herdr --machine <id> agent list` — timeout 12
   seconds. Agents live at `result.agents`; each can carry `pane_id`,
   `agent`, `agent_status`, `terminal_id`, `terminal_title`,
   `terminal_title_stripped`, `cwd`, `workspace_id`, `focused`.
4. Classify that machine:
   - Non-zero exit, timeout, empty stdout, or JSON without a
     `result.agents` array → one row, state `unreachable`. Keep the last
     line of stderr: that line is the diagnosis. Do not drop the machine.
   - Exit 0 and an empty agents array → one row, state `no agents`. The
     machine answered; nobody is running there.
   - One or more agents → one row per agent. Five agents on a machine are
     five rows, not one.
5. Mark the current session: a row is "you" when its machine id owns this
   pane and its `pane_id` equals `herdr pane current` (match `terminal_id`
   too when both sides have one). Print `you are #N` and mark that row
   `<- you`. If this session is not in the list, print that it is not a
   row.
6. Number only rows that have a pane — those are the messagable agents. A
   `no agents` or `unreachable` row gets `#` = `-`. The number is valid
   only for this printing; the next listing renumbers. Never store it;
   never use it as a reply address. The stable address is machine id plus
   pane id.

## The table

Columns, in order:

| Column | Meaning |
| --- | --- |
| # | Short number for this printing only. `-` when there is no pane. |
| MACHINE | Human label — enough to recognize the machine, not an address. Strip a leading `N - ` ordinal if present. |
| ID | Herdr machine id (hex) — the machine half of the stable address. |
| AGENT | Provider in that pane (`claude`, `codex`, `grok`, `cursor`, …). `-` if none. |
| PANE | Pane id (`w5:p2`) — the stable half of the address. `-` if none. |
| STATE | `idle`, `working`, `blocked`, `done`, `no agents`, `unreachable`. |
| TITLE | `terminal_title_stripped`, one line, truncated around 36 characters. |

Footer, always: `#` is the short id from this list; PANE is the stable
address. To message one, use the machine id and the pane from that row and
append the reply grant (SKILL.md §8 / templates.md §1). If the person wants
the short form, it is valid only until the next listing.

Print the table even when some machines are unreachable. **A partial mesh
is still the mesh.**

## What the states mean

- `idle` — free. Prefer this peer for new work.
- `working` — busy. Read the title before asking; do not hand it a second
  task that writes the same files.
- `done` — the last turn finished. Free.
- `blocked` — read the title; it may already be waiting on the thing you
  were about to ask.
- `no agents` — SSH and Herdr answered; no coding agent is open. Not a
  failure. Do not start an agent unless the plan asked for a worker pane.
- `unreachable` — the client call did not complete. The agents may still
  exist. Do not delete the machine. Do not start containers just to make
  the row appear.

## Unreachable is a diagnosis, not a dead machine

Surface the stderr, then interpret it. Do not invent a product-specific
peer file. Diagnoses seen in the wild:

- `No ED25519 host key is known for [host]:<port> and you have requested
  strict checking.` — Herdr wants the ED25519 host key with strict
  checking; a normal SSH client with `accept-new` can succeed on the same
  alias while Herdr fails, because the first SSH often stored an RSA key
  and Debian hashes `known_hosts` (a plaintext grep for `ssh-ed25519` sees
  nothing, and `ssh-keygen -F` succeeding only means SOME key exists). The
  typed check is
  `ssh-keygen -F "[host]:<port>" -f ~/.ssh/known_hosts` — look for
  `ssh-ed25519` in that output. `ssh-keyscan -T 4 -t ed25519 -p <port>
  <host>` returns the key Herdr wants. Compare its fingerprint with a trusted
  source and ask for explicit developer approval before adding it to
  `known_hosts`. Only after approval may you retry that machine once. Without
  approval, report it as unreachable and continue with the machines that
  answered. Do not loop.
- `Connection closed` / `Connection refused` on a port that `nc` says is
  open → the process behind the port is not sshd (stale image; sshd did not
  start). Report it. Do not install sshd from this skill.
- Timeout or empty answer → the machine is off, the catalog is stale, or
  the call ran as the wrong user. Say which of those the error supports; do
  not guess the others.
- An alias resolving to `127.0.0.1` from inside a container points at the
  container itself, not the peer — the peer address from inside a container
  is `host.docker.internal` plus the published port. Report it. Do not
  rewrite a product peers file from this addon.

A second listing often succeeds once the missing ED25519 key is stored: the
first `unreachable` was the missing key, not a missing agent.

## After the table

If the person only asked for the list: stop after the table and the footer.
Do not send messages.

If the person asked to talk to one of them: re-read the row you just
printed, address by machine id + pane id, and append the reply grant
(SKILL.md §8 / templates.md §1) verbatim. The short number may be used as a
convenience for the list just printed, only by resolving it again against
that same listing before sending — never from memory.
