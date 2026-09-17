# Working-principles authoring trial

Date: 2026-09-17. Baseline: `7f692b0` (v5.4.0), with this PR's onboarding,
specification, and working-principles changes applied. This is an authoring
and reconciliation observation, not a benchmark of agent quality.

## Method

One independent agent in the current Codex harness received the modified
onboarding skill path and two isolated write scopes. It did not receive the
parent conversation or a reference output. The task was:

> Add the working principles this onboarding teaches to each repository
> AGENTS.md. Keep local preferences and everything unrelated intact; only
> reconcile agent working principles, not the rest of onboarding.

The agent was asked to perform that request twice, report edits and second-pass
differences, and interpret three later requests without executing them. No
network, publishing, or writes outside the fixtures were allowed. A follow-up
clarified that this was principles-only and did not require padding files to
the full onboarding minimum. That intervention limits the independence of the
scope judgment; it is not hidden as an unaided success.

Fixtures were constructed under the gitignored `tmp/` directory:

- **Beacon:** a README describing a small Python CLI with standard-library-only
  dependencies and no `AGENTS.md`.
- **Atlas:** a README, a trivial unittest file, and an `AGENTS.md` with the
  heading `Engineering agreement`. Existing rules covered investigation before
  questions, authorized completion and validation, routine decisions, precise
  reporting, truthful checks, analysis-only scope, and mandatory maintainer
  approval before adding dependencies. A Quick Commands table named
  `python3 -m unittest discover -s tests`. Local preferences required preserving
  the existing heading and section.

## Observed results

| Case | First pass | Second pass |
|---|---|---|
| Beacon | Created a 34-line, 266-word `AGENTS.md` with ten inline principles, adapted to the small Python CLI | No edits; content and modification time unchanged |
| Atlas | Added five bullets (15 lines) for missing behaviors under `Engineering agreement`; original content otherwise byte-identical | No edits; content and modification time unchanged |

Both READMEs and the test file remained unchanged. Atlas retained its dependency
approval rule, heading, local preferences, and command table. The agent needed
no user clarification for the authorized edits. The parent agent inspected both
outputs and confirmed preservation and coverage. The trial exposed an ambiguity
between the full onboarding minimum and a principles-only request; the shipped
reference now explicitly forbids padding or unrelated scaffolding for that case.

Observed output fingerprints (SHA-256), retained for comparison with the
recorded fixture artifacts; a new agent may choose equivalent wording:

| Fixture | AGENTS.md SHA-256 |
|---|---|
| fresh | `0b5d7f25691d1d4b62d1d814c14a95b21cda5f3de47b7af788ead5b5622be649` |
| existing | `84d2436f2306bd7b5841aa45768f322192596d5739cea22dc9a6dd61c100b36a` |

## Interpretation exercises, not execution evidence

The agent interpreted "analyze this bug before changing anything" as read-only;
"fix the failing unit test" as authorized investigation, repair and validation;
and "add a new dependency" as subject to Atlas's approval rule or Beacon's
standard-library constraint. Those answers were not followed by actual tasks
and cannot establish that an agent obeys the instructions during execution.

## Limits and reproduction

Repeat the two fixture setups above with the shipped `onboard/SKILL.md` and
its conditional `shared/working-principles.md` resource. Record the entire
attempt, preserve before/after files, compare a second reconciliation, and
separate authoring observations from later task execution. For a full onboarding
trial, use standalone repositories: in this narrow exercise `context.sh`
resolved the enclosing development repository, so the agent relied on the
explicit write scopes. No full repository-conformance claim was made.

This was one agent session and two constructed fixtures, with a scope
clarification. It does not establish cross-model reliability, autonomous task
completion, token savings, or measured improvement over the prior release.
Automated packaging tests separately check that the referenced resource ships
and resolves from an exported pack, and that the contributor entry point stays
within its line budget with valid local file links. They do not check model
compliance.
