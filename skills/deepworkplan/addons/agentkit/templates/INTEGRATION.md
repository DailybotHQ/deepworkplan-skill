# Template — one headless delegate through `ak` (reason, don't copy-paste)

Reasoning guidance for running ONE delegate of a v7 plan through
coding-agents-kit. Fill every `<placeholder>` from the plan and the
machine; never guess. Preconditions are in `../../../execute/delegation.md`
(grant, `parallel_safe` or read-only, `addon:agentkit` in the effective
`subagents` sources). If any fails, do not delegate.

## 1. Prepare the worktree (writing delegate)

```bash
git worktree add ../<repo>-<delegation_id> -b dwp/<plan>/<delegation_id>
```

A read-only delegate gets no worktree: `--cwd` is the repository and the
prompt says "do not modify files"; record `"worktree": null`.

## 2. Compose the prompt (data the delegate reads)

- The task objective and its `AC-*` criteria, verbatim.
- "Work only inside `<worktree>`; commit nothing outside it."
- What to return: a short summary of what changed and why.
- Never a secret value, never a broader scope than the task.

`prompt_digest` = `sha256:` + the SHA-256 of exactly that prompt text.

## 3. Record, then launch

```bash
python3 <pack>/shared/ledger.py --plan <dir> delegate launch --task <T-id> \
  --json '{"delegation_id": "<id>", "transport": "headless", "via": "agentkit",
           "kind": "<kind>", "profile": "<@profile or omit>", "target": "<worktree>",
           "worktree": "<worktree>", "prompt_digest": "sha256:<hex>"}'
mkdir -p <dir>/analysis_results/delegations/<id>
ak run <kind> [@profile] --cwd <worktree> --timeout <seconds> --output-format json [--ask] \
  -- "<prompt>" > <dir>/analysis_results/delegations/<id>/result.json &
```

The kit launches the agent in autonomy by default. Add `--ask` when the
plan records the developer's opt-out; an inherited
`AGENTKIT_PERMISSIONS=ask` already wins without it, so never unset it.
Never add `--auto` or spell a CLI permission flag.

## 4. Observe

`ledger.py … delegate observe` and the background job's state. Check at the
pace the work changes; a timeout is already bounded by `--timeout`.

## 5. Collect and verify here

1. Read `result.json` — one object; `exit` 0 → `completed`, else `failed`
   (3 = CLI missing / not logged in; 4 = timeout; 5 = cancelled).
2. `ledger.py … delegate collect --task <T-id> --json '{"delegation_id":
   "<id>", "state": "<completed|failed>", "result_path":
   "analysis_results/delegations/<id>/result.json"}'`.
3. Review the worktree diff like any contribution; merge what is right.
4. Run the task's gates here through `ledger.py gate` — only that is
   `observed` evidence. Then `complete` as usual.
5. `git worktree remove ../<repo>-<delegation_id>` once merged or abandoned.

## 6. Cancel

Send SIGTERM to the `ak run` job (the kit kills the process tree, exit 5),
then `ledger.py … delegate cancel --task <T-id> --json '{"delegation_id":
"<id>"}'`.
