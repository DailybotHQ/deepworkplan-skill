# DeepWorkPlan Guide — Prompting Create, Execute and Resume

> Part of the DeepWorkPlan methodology guide. The routing index is
> [`GUIDE.md`](GUIDE.md); read only the guide files your flow names.

## 7. How to Instruct an Agent to Generate a New Plan

When you want Cursor, Claude, or another agent to **generate a new deep-work plan**, you can say:

> **Prompt to the agent:**
>
> - Ensure the gitignored output root exists (the skill creates it on demand):
>   - `.dwp/plans/` and `.dwp/drafts/` (git-ignored)
>   - The methodology guide ships in the skill at `guide/GUIDE.md`
> - Then, create a new plan folder:
>   - `.dwp/plans/PLAN_{plan_title}/`
> - Inside that plan folder:
>   - **BEFORE creating any files**, read the skills/agents catalog at `.agents/docs/skills_agents_catalog.md` (also reachable via `.claude/` or `.cursor/` symlinks) to identify relevant skills and agents for the plan's tasks
>   - Create `README.md` describing:
>     - The overall goal
>     - Context
>     - Global guidelines
>     - A Task List with `[ ]` items and links to each `N.task_*.md` file
>     - Execution rules for the agent
>     - A "Skills & Agents Used in This Plan" section mapping tasks to relevant skills/agents (see section 11)
>     - Reference to PROMPTS.md for ready-to-use prompts
>   - Create `PROMPTS.md` with ready-to-use prompts for this plan:
>     - Use the template at `examples/PROMPTS_TEMPLATE.md`
>     - Replace `{PLAN_NAME}` with the actual plan name
>     - Include prompts for: execute, resume, resume with status, check status, modify
>   - For each task in the Task List:
>     - Create a `N.task_{task_title}.md` file following the task template defined in this guide (`guide/GUIDE.md`, §5).
>     - Ensure each task file has:
>       - Context
>       - Goal
>       - Instructions (referencing relevant skill procedures when available)
>       - Acceptance Criteria
>       - Validation commands (including agent-based validation when applicable)
>       - Execution checklist
>       - Completion & Log section
> - Make sure all tasks are:
>   - Atomic (one clear objective)
>   - Ordered
>   - Written so an agent can complete each one independently and with high quality.

---

## 8. How to Instruct an Agent to Execute a Plan

When a plan is ready and you want an agent to **run it**, say:

> **Execution prompt to the agent:**
>
> - Use `.dwp/plans/PLAN_{plan_title}/README.md` as your source of truth.
> - Follow these rules:
>   - Work on **one task at a time**.
>   - Always pick the **first unchecked `[ ]` task** in the Task List.
>   - Open the corresponding `N.task_*.md` file and follow its instructions in full.
>   - Run all validation commands specified in the task file.
>   - Only when the task meets all acceptance criteria:
>     - Mark it as `[x]` in the plan README Task List.
>     - Update the task file's Completion & Log section.
>     - Commit the changes.
>   - Then move to the next `[ ]` task and repeat.
>   - If a validation fails or something is unclear, stop, log in the task file, and do not mark the task as completed.

---

## 9. How to Resume an Interrupted Plan (CRITICAL)

### 9.1. When to Resume

Plans may be interrupted due to:

- **Internet connection loss** during execution
- **IDE/editor crashes** (Cursor, VS Code, etc.)
- **Agent hitting token/context limits** mid-execution
- **Intentional breaks** (overnight pauses, scheduled stops)
- **System shutdowns** or unexpected errors

The resume functionality ensures work can continue **exactly where it left off** without duplicating completed tasks.

### 9.2. Resume Prompt Template

When a plan is interrupted and you want to resume execution, use this prompt:

> **Resume prompt to the agent:**
>
> RESUME the deep work plan at: `.dwp/plans/PLAN_{plan_title}/README.md`
>
> **Resume Instructions:**
>
> 1. **Read the plan README** to understand the overall objective
> 2. **Check the task list** - identify which tasks are marked `[x]` (completed) and which are `[ ]` (pending)
> 3. **Find the FIRST unchecked `[ ]` task** - this is your resumption point
> 4. **BEFORE starting work on that task:**
>    - Review the task file completely (`N.task_{task_title}.md`)
>    - Check if any work was already started:
>      - Run: `git status` (are there uncommitted changes?)
>      - Run: `git diff` (what was changed since last commit?)
>      - Run: `git log --oneline -10` (what are recent commits?)
>    - Review the task's **Completion & Log** section for any notes from the previous session
>    - If work was partially done, assess what remains to complete it
> 5. **Continue execution** from that task following normal execution rules:
>    - Complete the current task
>    - Run all validation commands
>    - Update the task's Completion & Log section
>    - Mark as `[x]` in the plan README
>    - Commit changes
>    - Move to next `[ ]` task
> 6. **NEVER redo completed `[x]` tasks**
> 7. **NEVER skip `[ ]` tasks**
>
> **Context awareness:**
>
> - Review recent git commits to understand what was accomplished
> - Check for uncommitted changes that indicate partial work
> - Read task completion logs for any notes or blockers from previous session
>
> Begin resuming now. First report:
>
> - Which tasks are already completed `[x]`
> - Which task you're resuming from `[ ]`
> - Any uncommitted work or partial progress found
> - Your plan for completing the current task

### 9.3. Critical Resume Rules

**The agent MUST follow these rules when resuming:**

1. **Verify completion status**
   - Trust the plan README's task list (`[x]` vs `[ ]`)
   - Cross-check with git commits for confirmation
   - Never assume - always verify current state
   - **Enhanced verification:** After identifying the resumption point, verify the last completed task:
     1. Check git log confirms a commit for that task
     2. Check the task's Completion & Log has a timestamp and status
     3. Check if PROGRESS.md is up to date
   - If any check fails, flag it to the user before continuing

2. **Assess partial work**
   - If `git status` shows uncommitted changes, review them carefully
   - If changes align with current task, incorporate and complete
   - If changes are unrelated or unclear, seek clarification

3. **Read completion logs**
   - Previous session may have left notes in task's Completion & Log section
   - Look for blockers, issues, or follow-up items
   - Use this context to inform current work

4. **Never duplicate work**
   - If a task is marked `[x]`, it's done - move on
   - Don't re-implement completed functionality
   - Trust the previous session's work unless validation fails

5. **Continue strict order**
   - Resume from first `[ ]` task
   - Complete it fully before moving to next
   - Maintain sequential execution

### 9.4. Example Resume Scenarios

**Scenario A: Clean interruption (all work committed)**

```text
Plan status:
- Task 1: [x] Completed, committed
- Task 2: [x] Completed, committed
- Task 3: [ ] Not started
- Task 4: [ ] Not started

Resume action:
→ Start work on Task 3
→ Follow task 3's instructions completely
→ No partial work to review
```

**Scenario B: Interruption mid-task (uncommitted changes)**

```text
Plan status:
- Task 1: [x] Completed, committed
- Task 2: [x] Completed, committed
- Task 3: [ ] In progress (git diff shows changes)
- Task 4: [ ] Not started

Resume action:
→ Review uncommitted changes (git diff)
→ Assess if changes are valid partial progress
→ Continue completing Task 3
→ Run validations, update logs, commit
→ Move to Task 4
```

**Scenario C: Interruption with blocker logged**

```text
Plan status:
- Task 1: [x] Completed, committed
- Task 2: [ ] Blocked (log says: "validation failed - coverage at 45%, need 50%")
- Task 3: [ ] Not started

Resume action:
→ Read Task 2's Completion & Log
→ Understand the blocker (coverage issue)
→ Fix the validation failure
→ Re-run validations
→ If pass: mark [x], commit, move to Task 3
→ If still fail: log again, stop, request help
```

### 9.5. Resume Checklist for Agents

When resuming a plan, the agent should:

- [ ] 1. Read plan README completely
- [ ] 2. Identify completed `[x]` vs pending `[ ]` tasks
- [ ] 3. Find first `[ ]` task (resumption point)
- [ ] 4. Run `git status` to check for uncommitted work
- [ ] 5. Run `git log --oneline -10` to see recent commits
- [ ] 6. Read current task's Completion & Log for notes
- [ ] 7. Assess partial work if any
- [ ] 8. Report resumption status to user
- [ ] 9. Continue execution following normal rules
- [ ] 10. Never skip or duplicate tasks

---
