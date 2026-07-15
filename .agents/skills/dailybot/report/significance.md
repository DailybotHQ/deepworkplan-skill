# When to Report — Trigger Rules

This guide defines when to send a Dailybot progress report. The system uses objective, binary conditions — no subjective judgment required.

## Report Triggers

Send a progress report when **either** condition is met:

### 1. Task completed

You finished a discrete task or subtask — a todo item, a user-requested change, a bug fix, a feature, a refactor, a test suite, a deployment.

The key test is structural: is the unit of work done? If you checked off a task or delivered what was asked, report it.

### 2. Broad edit

You modified 3 or more files in a single batch of edits. This catches meaningful cross-cutting changes even when no explicit "task" was defined.

### User override

If the developer explicitly says "report this to Dailybot" or "send an update", always report regardless of the conditions above.

## Milestone Rule

Mark a report as a **milestone** only when the **top-level task is fully completed** — all subtasks are done and the entire requested piece of work is wrapped up.

Individual subtask completions are regular reports, not milestones. If the developer explicitly asks for a milestone, always honor it.

## Aggregation Rule

If you completed multiple related changes, combine them into one report. Don't send 3 reports for parts of one feature.

**Instead of:**
- "Updated the user model"
- "Added the preferences endpoint"
- "Wrote tests for preferences"

**Send one:**
- "Built the user preferences system — new data model, API endpoint, and full test coverage."

## Edge Cases

### "I completed a task AND answered some questions"

Report the task completion. Ignore the Q&A — only the trigger-meeting part matters.

### "I did many small edits across files"

If 3+ files were modified, report regardless of how small each individual edit was. The report content should describe the aggregate outcome.

### "The developer asked me to report"

Always honor explicit requests, even if neither trigger condition is met.

### "I already reported recently"

If you sent a report less than 30 minutes ago for the same logical task, consider aggregating with the next one rather than sending back-to-back reports.

### "I'm mid-task, not done yet"

Do not report incomplete work just because you edited 3+ files as part of an ongoing task. The broad-edit trigger applies to a completed batch of edits, not work-in-progress mid-stream. Wait until the subtask or edit batch is done.
