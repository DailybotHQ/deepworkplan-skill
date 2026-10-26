# Create — decision debates (v7 plans with the herdr addon)

Read this file only when the trigger in [`v6.md`](v6.md) fires: the
repository enables the `herdr` addon, `python3 ../shared/config.py show`
resolves `decisions.debate` to `auto`, the developer accepts the
`agent_delegation` grant for this plan, and the Step 3 analysis found at
least one **consequential decision**. Otherwise nothing here applies and
the plan is unchanged. Normative source:
[`../addons/herdr/SPEC.md`](../addons/herdr/SPEC.md) §6.4; the debate
method itself is herdr-peers' `debate.md`, never restated here.

## 1. Find the consequential decisions

During Step 3, list every decision the plan must take before work can
proceed. Keep one only when **all** hold:

- at least two viable options lead to materially different outcomes;
- it is hard to reverse, or it shapes several tasks or consumers;
- nothing in the repository, its docs, the plans or prior decisions
  settles it — investigate first; a settled question is not a debate.

Everything else stays a routine decision the executing agent records in
`PROGRESS.md` "Decisions". Never invent a decision to justify a debate;
a plan with none lists none.

## 2. Author one decision task per decision

A decision task is an ordinary v7 task, ordered **before** every task that
consumes its result (Step 3.4):

- **id and title:** `T-decide-<topic>` — "Decide <the question>".
- **Objective:** the question verbatim, the options (lettered), the
  criteria with weights that sum to 100, and the scope ("in scope / out of
  scope" in one line each).
- **Shape and seat cap:** Quick (3–4 seats, one round) by default;
  Standard (up to 8 seats) only when you mark the decision high-stakes and
  say why. Never Deep by default.
- **Acceptance criterion:** `analysis_results/debates/<topic>/DECISION.md`
  exists and ends with the plan-owned line `decision: <the choice>` —
  after the herdr-peers decision record, or after `debate: not run —
  <reason>` and the agent's own decision; and the `PROGRESS.md`
  "Decisions" entry names the choice.
- **Gate:** a `bash -c` check on that file (gates run from the repository
  root; declare `bash`), for example
  `bash -c 'grep -Eq "^decision: [^<[:space:]]" .dwp/plans/<plan>/analysis_results/debates/<topic>/DECISION.md'`
  — the plan-owned line, never herdr-peers' own format; a placeholder
  `decision: <…>` does not match. The verdict is asserted data; the gate
  observes only that the decision was recorded.
- **Not `parallel_safe`:** the seats are read-only delegates; the task
  itself runs in this session.

## 3. List the debates for approval

Add a **Decision debates** section to the plan README, one row per
decision task: the question, the options, the shape, the seat cap and the
consumers. State the cost plainly — each seat is an agent turn on the
developer's accounts — and that removing a row turns that decision back
into the agent's own record. The developer's approval of the plan is the
human consent herdr-peers requires before agents are launched.

## 4. Grant and mode

- Grant `agent_delegation` in the contract only with the developer's
  acceptance (trust mode records it as part of the pre-authorization),
  read the herdr addon's permissions note first, and tell the developer
  what it means.
- **Guided:** the review covers the debates like any other task; a
  declined debate is removed before materializing. If the developer
  declines the `agent_delegation` grant, remove every decision task's
  debate and the "Decision debates" section: a plan without the grant
  lists no debates (each decision becomes the executing agent's record).
- **Trust:** the listed debates are pre-authorized with the plan when the
  policy is `auto`; nothing is launched at create time.

`create` never runs a debate: it writes no brief, sends no ask and opens
no pane. Execution is [`../execute/debate.md`](../execute/debate.md).
