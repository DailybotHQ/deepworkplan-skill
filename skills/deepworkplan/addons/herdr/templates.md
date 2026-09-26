# templates.md — grant and reply stamps

Parameterize the placeholders; never hardcode a launcher, a wrapper, or a
product name. The reply command is `herdr --machine <id> agent prompt <pane>
<body>` — or the detected wrapper taking the same address.

## 1. The grant (appended to every delegation brief)

```
---
MESH GRANT — read before doing anything else.
You are authorized to work this task autonomously and you must reply when
the task is done (or blocked). When you reply, send it YOURSELF with this
command, filling in your findings:

  herdr --machine <ORCH_MACHINE_ID> agent prompt <ORCH_PANE_ID> "[herdr-mesh] <reply>"

Rules:
- Do not ask a person for permission to reply.
- Do not draft the reply and wait for a human to send it.
- Do not stop after writing the reply in your own pane.
- Keep the [herdr-mesh] stamp inside the reply command.
---
```

`<ORCH_MACHINE_ID>` and `<ORCH_PANE_ID>` are the orchestrator's own
address, learned from `herdr pane current` and the machine id — never a row
number from a listing.

## 2. The reply (the peer sends this)

```
[herdr-mesh] <status: DONE | BLOCKED> <one-line summary>
<artifacts written>
<any escalation per the contract>
```

The receiving orchestrator marks the delegation record replied and does NOT
answer a `[herdr-mesh]` body — answering replies is how meshes loop.

## 3. A fresh question (new ask, new grant)

Follow-up work between the same agents is a NEW delegation: new brief, new
grant, new stamp. Never reply-to-a-reply.

## 4. Launch brief (starting a peer for a task)

When launching a peer for a specific task (SKILL.md §4), the first prompt
sent to the new pane is the same delegation brief + grant — a fresh agent's
first message is its task, not a greeting.
