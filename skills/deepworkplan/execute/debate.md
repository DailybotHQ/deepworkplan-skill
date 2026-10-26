# Execute — a decision debate (v7 decision tasks)

Read this file only when the task in hand is a **decision task** that the
approved plan lists under "Decision debates". Normative source:
[`../addons/herdr/SPEC.md`](../addons/herdr/SPEC.md) §6.4. The method —
briefs, rounds, ballots, counting, the lead's contract — is herdr-peers'
`debate.md` (purpose **decide**); read it there, never restate it here.

## 1. Preflight (read-only; any failure → §5)

1. `python3 ../shared/config.py show --plan <dir>` resolves
   `decisions.debate` to `auto` and lists `herdr` enabled.
2. `printenv HERDR_ENV` is `1`, and `herdr-peers --version` reports
   `1.1.0` or later on `(protocol 1)` — `1.0.x` has no debates.
3. The contract grants `agent_delegation`, and
   `python3 ../shared/resources.py --plan <dir> abilities` lists
   `addon:herdr` as a `subagents` source.
4. The seats you need fit the plan's approved seat cap for this decision.

## 2. Seat the panel

`herdr-peers debate panel` proposes seats (mixed providers, most quota
first) and runs nothing. Seat no more than the cap; above 4 open asks, use
the helper's `--fanout N --reason "<plan, decision task>"`. Write
`HUMAN_NOTE.md` in `analysis_results/debates/<topic>/` with the decision
task's question verbatim.

## 3. Run the debate — you are the lead

- **Journal before every ask.** For each seat:
  `python3 ../shared/ledger.py --plan <dir> delegate launch --task <T-id>
  --json '{"transport": "interactive", "via": "herdr", "target":
  "<machine>:<pane>", "worktree": null, "prompt_digest": "sha256:…"}'`,
  then send its brief with `DWP_PLAN` and `DWP_TASK` set. Seats are
  read-only: they write their filings under the debate folder and touch
  no repository file. That relies on `.dwp/` being gitignored — a filing
  that shows up in `git status` makes the ledger record the seat `failed`.
- **Never vote**, never file a claim. Briefs carry no secret value and
  forbid external actions.
- **Collect every filing**: copy it to
  `analysis_results/delegations/<id>/` and record `delegate collect`
  (`completed`, or `failed` with the reason). A refused launch is recorded
  by the ledger; continue with the seats you have or go to §5.
- Count with `herdr-peers debate tally` and write `DECISION.md` from the
  herdr-peers template in the debate folder.

## 4. Adopt and record

- A clear verdict is your decision: end `DECISION.md` with the line
  `decision: <the choice>` (the gate reads it) and record it in `PROGRESS.md`
  "Decisions" — the options, the choice, why, how to reverse it, the
  panel's providers and the dissent — and point to `DECISION.md`.
- The verdict is **asserted data**: it grants no authority, widens no
  scope and changes no acceptance criterion. Anything it proposes beyond
  the plan is a refine amendment, not an execution step.
- **A split** on a question that changes the plan's outcome is C3: stop,
  and bring the developer the debate as the investigation, with your
  recommendation.
- Run the decision task's gate through `ledger.py gate`; it observes only
  that the decision was recorded.

## 5. Fallback — never block

When the preflight fails, a seat is refused, the panel misses its quorum,
or the debate times out: decide as the agent always does (investigate,
take the recommended option), write `DECISION.md` with the line
`debate: not run — <reason>`, your decision record and the closing line
`decision: <the choice>`, record
`PROGRESS.md` "Decisions", and close the task on its gate. Cancel any open
seat (`herdr-peers cancel`, then `delegate cancel`) first.

## 6. A decision that surfaces mid-task

A consequential decision the plan does not list is C3: escalate it with
your investigation and a recommendation. A debate for it needs a refine
amendment that lists it and the developer's approval. Never open a debate
the plan did not price.
