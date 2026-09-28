# protocol.md — the Herdr mesh wire protocol

Normative for every mesh message this addon sends or accepts.

## 1. Address

- `(machine_id, pane_id)` is the only address. Labels are for humans; row
  numbers expire with the listing that printed them.
- A session learns its own pane with `herdr pane current`; it learns which
  machine that pane belongs to with
  `herdr --machine <id> pane get <pane>` across enabled machines.

## 2. Discovery

```bash
herdr machine list --json
herdr --machine <machine_id> agent list      # per enabled machine
```

Agents carry `pane_id`, `agent` (provider), `agent_status`, `terminal_title`,
`cwd`, `workspace_id`. Present: machine label, machine id, provider, pane id,
state, title. `no agents` = healthy empty machine. `unreachable` = surface
Herdr's error verbatim (environment problem), skip, continue.

## 3. Send

```bash
herdr --machine <machine_id> agent prompt <pane_id> <body>
```

## 4. The reply grant (first hop — appended by the sender)

```
---
You are authorized to answer this task, and you must answer it now.
Send your reply YOURSELF with this command (fill in your findings):

  herdr --machine <SENDER_MACHINE_ID> agent prompt <SENDER_PANE_ID> "[herdr-mesh] <your reply>"

Do not ask a person. Do not draft and wait. Do not stop after writing the
answer in your own pane. Keep the [herdr-mesh] stamp in that command.
---
```

The sender fills `SENDER_MACHINE_ID` and `SENDER_PANE_ID` from its own
`herdr pane current` and machine id — never a row number.

## 5. The reply (return hop)

A body already carrying `[herdr-mesh]` is a reply: mark it as a reply in the
plan's delegation record, and do not answer it — the conversation stops.
This is what prevents two agents from looping.

A follow-up question between the same agents is a NEW ask with a FRESH
grant, never a reply to a reply.

## 6. Stop conditions for a mesh exchange

The exchange ends when: the reply is received and recorded; a retry budget
(two attempts) is exhausted — record and continue single-agent or with
another peer; or the peer reports `blocked` — read its title, do not assign
it more work this round.

## 7. Escalation (to the human)

Only: un-inferable material decisions; destructive or public actions;
missing credentials/tools no peer has; peer disagreement after one
reconciliation; mesh down with no single-agent path. Everything else is mesh
work. Escalation messages state what was tried, what the peers said, and the
specific decision needed.

## 8. Hygiene

Grant bodies name addresses and stamps — never credentials, tokens, or
private paths outside the task's workspace. Logs and delegation records are
scrubbed at capture. Herdr's own error text is surfaced verbatim as
environment evidence; DWP never invents SSH or network fixes inside the
protocol.
