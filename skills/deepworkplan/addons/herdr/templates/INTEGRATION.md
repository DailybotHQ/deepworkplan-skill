# Template — one interactive delegate through herdr-peers (reason, don't copy-paste)

Fill every `<placeholder>` from the plan and the live Herdr listing; never
guess an address. Preconditions: `../../../execute/delegation.md` (v7
contract with `agent_delegation`, `parallel_safe` task or read-only
delegate, `addon:herdr` in the effective `subagents` sources) and
`HERDR_ENV=1` in this session.

## 1. Choose the peer

`herdr-peers list` (the helper's live listing). Prefer an idle agent; a
peer is `<machine_id>:<pane_id>` exactly as the listing prints it — labels
and row numbers are never addresses.

## 2. Compose the brief (data the peer reads)

- The task objective and its `AC-*` criteria, verbatim.
- For a writing peer: "work only in `<worktree>`" (pass `--worktree`).
- What to send back: a short summary of what changed and why.
- No secret values; no wider scope than the task.

`prompt_digest` = `sha256:` + the SHA-256 of exactly that brief.

## 3. Record, then ask

```bash
python3 <pack>/shared/ledger.py --plan <dir> delegate launch --task <T-id> \
  --json '{"delegation_id": "<id>", "transport": "interactive", "via": "herdr",
           "kind": "<kind>", "target": "<machine_id>:<pane_id>",
           "worktree": "<path or null>", "prompt_digest": "sha256:<hex>"}'
DWP_PLAN=<dir> DWP_TASK=<T-id> herdr-peers ask [--worktree <path>] <machine_id>:<pane_id> "<brief>"
```

Keep the ask id the helper prints; note it next to `<id>`.

## 4. Observe and collect

- `ledger.py … delegate observe`; `herdr-peers check <ask-id>`.
- `herdr-peers wait <ask-id>` (or the reply lands in this pane). Save it to
  `<dir>/analysis_results/delegations/<id>/reply.txt`.
- `ledger.py … delegate collect --task <T-id> --json '{"delegation_id":
  "<id>", "state": "completed", "result_path":
  "analysis_results/delegations/<id>/reply.txt"}'` (`failed` on a refusal
  or timeout).
- Integrate the peer's worktree branch like any contribution, then run the
  task's gates here through `ledger.py gate`.

## 5. Cancel

`herdr-peers cancel <ask-id> --reason "<why>"`, then `ledger.py …
delegate cancel --task <T-id> --json '{"delegation_id": "<id>"}'`.

Never answer the reply; never delegate from the peer; close only panes you
created.
