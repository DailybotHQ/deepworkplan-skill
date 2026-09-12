# Troubleshooting — decision path

Read this only when something is already wrong. Each symptom has one first
check, then a decision. Do not run a generic "repair everything" pass: fix the
specific cause, then continue the flow you were in.

## 1. The skill is installed but the agent cannot find it

**Symptom:** the developer says the skill is installed, but no `deepworkplan`
routing is available, or a sub-skill path does not resolve.

1. Look for the pack directory your harness actually reads — commonly
   `.agents/skills/deepworkplan/`, `~/.claude/skills/deepworkplan/`, or the
   equivalent for the host in use.
2. If the directory is missing, installation did not reach this host. Say so;
   do not improvise a pack. Point at the install routes and stop.
3. If the directory exists but `SKILL.md` is absent inside it, the install is
   partial — reinstall rather than patching files by hand.

> An installer exiting `0` is not proof every target succeeded. Some install
> tools report overall success while individual per-agent targets fail. Verify
> the directory your harness reads, not the installer's exit code.

## 2. A skills-CLI install delivered the wrong tag or no content

**Symptom:** `npx … skills add <repo>@<tag>` printed the requested tag (or
"Done!") and exited 0, but the installed `SKILL.md` `version:` is not the
requested tag, or the target directory is empty / missing its `SKILL.md`.

Two upstream CLI defects, both reproduced in the v2/v5 round-1 benchmark
install ledgers: the `@tag` pin can be display-only (the requested tag
printed while the latest bytes are delivered), and a parallel-mkdir race can
report success while placing no content.

1. **Empty or partial target (false success):** remove the empty attempt,
   pre-create the target directory (`mkdir -p .agents/skills/<name>/`), and
   retry the identical command once — this alone fixed every round-1
   occurrence.
2. **Wrong tag delivered:** do not trust the printed source line. Reinstall
   byte-exact from the tag itself:
   `git archive <tag> skills/<name> | tar -x --strip-components=1 -C .agents/skills`,
   then `diff -rq` the result against a `git archive` export of the same
   tag — it must be identical.
3. **Prevent both:** pre-create the target directory *before* every
   `skills add` call, and verify every install afterwards — installed
   `version:` equals the requested tag, directory non-empty. `onboard`
   Phase 7 / Phase 7a and `upgrade` Phase 3 run this verification as a
   mandatory step.

## 3. The installation is stale

**Symptom:** behavior does not match the documented flow, or the specification
version referenced in the pack disagrees with what a plan declares.

1. Read `version:` in the pack's router `SKILL.md`.
2. Compare it with the version the developer expects.
3. If it is older, reinstall through the route they originally used. Do not
   hand-edit `version:` fields and do not mix files from two installs.
4. A repository that vendors a deliberately adapted copy is a different case:
   changing it is an intentional, reviewed act, never a silent refresh.

## 4. No test or validation command exists

**Symptom:** a task needs a validation gate, but the repository documents none.

1. Look for the real command in this order: the repository's own agent
   instructions, its package/build manifest scripts, then CI configuration.
2. If you find one, use it verbatim and record where it came from.
3. If none exists, **do not invent a command and do not claim a gate passed.**
   State plainly that the repository has no validation command, propose one
   appropriate to the stack, and get it confirmed before relying on it.
4. Until a real gate exists, a task that changes behavior cannot be marked
   complete on the strength of "it builds" or "the file exists".

## 5. The host cannot do something the flow assumes

**Symptom:** slash commands, hooks, subagents or a proprietary task API are
unavailable.

1. Those are conveniences. Fall back to the portable sequential path: read the
   plan, do one task, run its gate, record it, commit, move on.
2. What cannot be substituted is tool execution and repository read/write
   access. If the agent genuinely cannot run commands or edit files, stop and
   say so — installation cannot compensate for that.
3. Never silently downgrade a required gate because the host made it awkward.

## 6. The plan's state is inconsistent

**Symptom:** README checkboxes, task logs, `PROGRESS.md` and `state.json`
disagree, or a task looks half-done.

1. Treat the markdown plan as the human-readable source of truth and
   `state.json` as a projection of it.
2. Establish what actually happened from evidence, not from the most optimistic
   record: git history, the task's own Completion & Log, and whether the work is
   present in the files.
3. Reconcile the projection to that evidence. If a task is recorded complete but
   its gate output is missing or its change is absent, it is **not** complete —
   reopen it.
4. Record the reconciliation in the task log. Do not rewrite history to look
   tidy; a failed gate that was later fixed is part of the evidence.

## 7. Resuming a plan another agent started

1. Read, in order: the plan README's task list, `state.json`'s checkpoint, the
   last completed task's log, then the git log.
2. Resume at the first unchecked task. Do not redo completed work.
3. If the checkpoint and the checkboxes disagree, apply §5 before continuing.
4. Record your own identity in what you write; the artifact should show who did
   which part.

## 8. An in-flight plan predates the current specification

A plan created under an earlier lifecycle keeps that lifecycle. Do not migrate
it silently to look current. Either finish it as recorded, or migrate it
explicitly — and when you migrate, invalidate the evidence the change affects
rather than carrying stale gate results forward.
