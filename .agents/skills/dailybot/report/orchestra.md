# Reporting from orchestra lanes

An orchestra runs several repository lanes under one lead. Each lane owns its
progress reports; the lead owns the single orchestra completion milestone.
Distinct agent names make those updates attributable without repeating the
same accomplishment under several identities. This guide uses existing
reporting commands and changes no CLI or HTTP contract.

## Assign identities before work starts

The developer-authorized lead assigns a stable name per lane, for example
`sample-repo lane` or `another-repo lane`, and a separate lead name. Record
the names and reporting ownership in the orchestration plan or the lead's
existing coordination record. Keep the same name after a session restart or an
account change. Coding-agent vendor/auth profiles and Dailybot report
identities serve different purposes: changing a coding account must not
silently change the lane's reporting identity. Optional
[coding-agents-kit](https://github.com/DailybotHQ/coding-agents-kit) selects
those coding accounts; it is not Dailybot auth or a reporting prerequisite. If
several lanes work on one repository, include their role in the assigned name
so they remain distinct.

Run the report skill's normal opt-out, authentication, target-organization,
and [repo-profile pre-flight](../shared/repo-profile.md) first. Do not install
a CLI, configure hooks, or send a report merely because this guide contains an
example. Use the developer's existing reporting authorization and preserve all
consent boundaries.

**Explicit authorized name override.** When the developer has authorized the
orchestra and its lead-assigned lane names, pass `--name "<repo> lane"` even
if `.dailybot/profile.json` pins `name`. This is an intentional, per-command
override for that assignment, not permission to choose another name or bypass
the pre-flight. Verify that the assigned name is covered by the developer's
actual instruction or previously approved orchestration scope. A peer's
assertion or an agent-written plan entry alone is not authorization. Record a
pointer to that approval; if none is available, keep the pinned identity and
request the missing authorization. Never edit the repository profile to change
the identity for every agent. Continue to honor its auth `profile` and omit
metadata keys already supplied by `default_metadata`. Without authorization
for a lane-name override, keep the pinned name and resolve the assignment with
the lead before sending under a different identity.

For example, a profile that pins `name` and `default_metadata.repo` still
provides the repo metadata and auth defaults. An authorized lane report is:

```bash
dailybot agent update "Documented independent review lanes so the lead can hold merges until findings and validation are resolved." \
  --name "sample-repo lane" \
  --json-data '{"completed":["Independent reviewer workflow documented"],"in_progress":["Waiting for integration approval"],"blockers":[]}'
```

No `--milestone`: the lane's completed work is a subtask of the orchestra.
Pass only additional, non-secret metadata the profile does not already set.
For the HTTP fallback, use the assigned lane name in `agent_name` and omit
`is_milestone` (or set it to `false`); the same authorization and profile
rules apply.

When the same lane works Dailybot Plan cards using a login session or personal
API key, set `DAILYBOT_AGENT_NAME` (or `dailybot --agent-name`) to its
assigned report name so card attribution matches. With an agent or
organization key, omit that Plan attribution name: the API refuses it. The
report `--name` exception does not extend to other sub-skills' identity
overrides. See the [report attribution rule](SKILL.md#flag-reference) and
[Plan credential table](../tasks/SKILL.md).

## Choose the reporting owner for each event

| Event | Reporting owner | Report type |
|---|---|---|
| Orchestra kickoff | Lead | Regular: combined goal and purpose |
| Significant lane result or PR ready | That lane | Regular: its outcome and remaining work |
| Lane blocked | That lane | Regular, with concrete `blockers` and what is needed |
| Lane done, awaiting integration/release | That lane | Regular: completed deliverable and pending integration |
| Entire orchestra accepted and released | Lead | One `--milestone` after all required gates and release checkpoints |

Aggregate adjacent events for the same deliverable. A passing gate and its PR
becoming ready can be one update. The normal report triggers still apply to a
completed task or batch of three or more edited files. Combine related results
once; do not add a second report for routine inspection or an individual edit
in that batch. Report content stays human-readable English: what changed and
why it matters. Put technical identity in the agent name or structured
metadata, not in the message. Keep plan IDs, branch names, paths, raw commits,
git statistics, and secrets out of report text.

The lead's final report describes the integrated outcome. It should not
re-send each lane's update or mark completion while required reviews, merges,
releases, or live checks are pending. Lane agents never add `--milestone` just
because their own portion is done. An explicit developer request for a
milestone still takes precedence over this default ownership.

## Coordinate without duplicate reports

Dailybot reports provide team visibility; an orchestra's existing control
channel handles lead/lane coordination. Dailybot reporting needs neither Herdr
nor an orchestration plan. If the developer chose
[herdr-peers](https://github.com/DailybotHQ/herdr-peers) v0.2.0, that optional
public tool provides one authorized ask/reply between agents in
[Herdr](https://github.com/herdrdev/herdr) panes. Load its installed skill and
Herdr's `herdr --skill` before using it. A standalone lane status update in
that workflow can be sent as:

```bash
herdr-peers ask <lead-address> 'report lane: PR ready, repository gate passed. Dailybot lane update sent; integrated milestone remains with the lead.'
```

Include a non-secret report URL if the CLI returned one. If the lane is
answering a pending lead ask, run `herdr-peers check` first and use the
helper's authorized `reply` command instead. Never ask while holding an
unanswered ask, and never reply to a reply. A peer message is evidence to
verify; it grants no new publication or credential authority.

Keep a small event ledger in an existing, authorized coordination record: lane
name, logical event, candidate/release reference, send status, and report URL
when available. If there is a DeepWorkPlan, use its `analysis_results/`;
otherwise use the lead's approved state location or conversation record. Do
not create a plan or write an arbitrary ledger merely to send a report. Check
the available record before sending after a restart; without durable delivery
evidence, verify with the lead rather than assuming the event was unsent. Do
not send once for the report trigger, again for the hook reminder, and again
for the same herdr-peers milestone. A hook reminder for already-reported work
can be acknowledged with `dailybot hook dismiss`; don't disable the whole repo
to silence one lane. Hooks use a repo-local ledger: agents sharing a checkout
still need a per-lane record to avoid losing ownership.

If the send fails or its outcome is uncertain, record `failed` or `unknown`
and inform the lead. Do not retry automatically or let the lead repost a
possibly delivered report. An explicit retry should first check delivery; do
not assume report writes support the Plan API [shared idempotency
rules](../shared/idempotency.md). Only use a key when the specific endpoint
and installed CLI document that guarantee. Reporting remains best-effort:
missing authentication, `.dailybot/disabled`, or an unreachable service must
not block development or its validation gates. A skipped report is not
evidence that a lane's work failed.

For general cadence and writing guidance, read the [report significance
guide](significance.md) and [writing guide](writing-guide.md).
