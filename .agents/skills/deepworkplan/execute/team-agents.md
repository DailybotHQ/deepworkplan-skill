# DeepWorkPlan — Execute: team-agents branch (read only when Step 2.2 found a Team Agents Configuration and team mode was selected)

Verbatim from the main procedure. The sequential path is always preserved; every task also works sequentially, and the Final Review (or a legacy plan's three final tasks) is always sequential under the lead.

## Team-Agents Parallel Groups

> **CRITICAL: use REAL team agents, NOT subagents.** When the plan has a "Team
> Agents Configuration" section and team-agents mode was selected, you MUST use
> `TeamCreate` + `Agent` with `team_name` + `TaskCreate` + `SendMessage` +
> `TeamDelete`. Do NOT call `Agent` alone (no `team_name`) — that creates
> subagents, which only report back to the caller. Team agents share a task list
> and communicate with each other.

At a parallel-group boundary:
1. Announce the parallel group.
2. `TeamCreate` with `team_name: "dwp-{plan_name}-group-{letter}"`.
3. Spawn teammates with `Agent` + `team_name` + `subagent_type:
   "general-purpose"`, passing each its task file content + the plan README's
   Goal/Context/Guidelines + commit instructions.
4. `TaskCreate` one shared task per parallel task; assign each to its teammate via
   `TaskUpdate` (`owner`).
5. Monitor: receive teammate messages, `SendMessage` as needed; when all parallel
   tasks complete, verify each is `[x]` in the README. If a teammate fails, log
   and recover or fall back to sequential.
6. Clean up: `SendMessage` a `shutdown_request` to each teammate, wait for
   confirmation, then `TeamDelete`. Continue with the next sequential task/group.
7. Each teammate commits its own task; the lead verifies commits afterward.

**Verify real team agents:** the status bar shows `Team: dwp-...-group-X · N
teammates`, NOT `N local agents`.

**Sequential fallback:** if team-agents execution fails at any point, log the
reason and execute the remaining group tasks sequentially (standard single-task
rules) — no special handling needed.

- **Team agents:** detect, offer, fall back to sequential on failure, and always
  clean up the team after each parallel group.
