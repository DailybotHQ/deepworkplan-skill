# DeepWorkPlan Guide — Execution Rules, Commits and Completion Tracking

> Part of the DeepWorkPlan methodology guide. The routing index is
> [`GUIDE.md`](GUIDE.md); read only the guide files your flow names.

## 6. Agent Execution Rules (Critical Behavior)

When an agent is instructed to use this system, it must obey:

1. **Single-task focus**
   - Only work on **one task file** at a time.
   - Ignore other tasks until the current one is fully completed or blocked.

2. **Strict order**
   - Always process the **first unchecked** task in the plan README (`[ ]`).
   - Once completed, mark it `[x]` and move to the next.

3. **Validation required**
   - Never mark a task as completed without running and considering the validations defined in the task file.
   - For behavior-changing tasks, the validations **must** include the repo's tests and its lint/type-check/format checks **selected from the task's Touched Surface** (falling back to the full suite when the change is shared/core or no scoped invocation is documented), and the task must have added/updated tests for the new behavior (`authoring.md` §5.3). The complete suite runs on the final state in the Final Review.

4. **Logging & commits**
   - Always update the task's log.
   - Always commit work before moving on.
   - **Commit message format** — Include a reference to the plan and task:
     ```
     type(scope): description - Task N of PLAN_{plan_name}
     ```
     Examples:
     ```
     feat(api): add notification endpoint - Task 2 of PLAN_notification_system
     docs(technical): update architecture guide - Task 3 of PLAN_docs_reorganization
     fix(chatbot): resolve timeout in handler - Task 1 of PLAN_bug_fixes
     ```

5. **Stop on failure**
   - If a validation fails or something is unclear, stop and log.
   - Do not continue blindly.

6. **Progress reporting** — handled by the optional Dailybot addon at [`addons/dailybot/`](../addons/dailybot/SKILL.md). Trigger by intent ("report this to Dailybot") or via `/dailybot_report` on Claude Code. The addon defers auth to the Dailybot skill and is opt-in and never-blocking.

   **Per-task reports (only for individually significant tasks):**
   - After a task that ships a feature, fixes a bug, or completes a major refactor, trigger the skill with a standup-style message — e.g., *"Implemented JWT middleware for the API gateway — all protected routes now validate tokens."*
   - **Skip** intermediate/setup tasks (scaffolding, base classes, config changes) — they'll be covered by the plan completion report.
   - **NEVER use** internal references: *"Completed Task N: {title} - PLAN_{name}"* — this is tracking, not a standup update.

   **🔔 Plan completion report (MANDATORY — golden rule):**
   - When ALL tasks in a plan are complete, you MUST send a Dailybot report as a **milestone** with **structured data** (completed/in-progress/blockers) and **metadata** (plan name, repo). The skill prompts for these fields when reporting plan completions.
   - **The message MUST describe what was BUILT, not that a plan ran.** This is the #1 anti-pattern — never send vague reports.
   - **If an Executive Report is requested:** generate it from durable evidence (task logs, PROGRESS.md, `analysis_results/`, the state layer, PR summaries) without replaying the plan. Do not generate it unrequested.

     Examples (the message itself; the skill builds the payload):
     - ✅ GOLD STANDARD: *"Built a full-text search feature for the agents dashboard — users can now search across report content, structured data, metadata, and agent names with real-time highlighted results."* (with structured data listing each deliverable and metadata `{"plan": "PLAN_dashboard_search", "repo": "web-app"}`)
     - ❌ NEVER (vague, no detail): *"Completed a deep work plan with multiple tasks executed and validated"*
     - ❌ NEVER (process-focused): *"Plan completed: PLAN_auth_refactor - 8 tasks completed successfully"*

   See [`addons/dailybot/templates/INTEGRATION.md`](../addons/dailybot/templates/INTEGRATION.md) for the full pattern.

   **General rules:**
   - ALWAYS in English, regardless of conversation language
   - If the reporting script fails or times out, **continue without blocking** — progress reporting is secondary to the actual work.
   - See `AGENTS.md` "Agent Progress Reporting" section and the progress report skill for the complete standard.

7. **Multi-repository commits** (for plans spanning multiple projects)
   - Commit changes in **each affected repository separately**
   - Push commits immediately after each task completion
   - Never accumulate changes across multiple tasks
   - See section below for detailed multi-project workflow

---

## 6.1. Final Review, Task-Local Skills and the Optional Report

Every DWP plan created under spec 2.3.0 ends with **one** mandatory task, the **Final Review**, automatically added by `/dwp-create`. Two responsibilities that older plans placed in separate closing tasks now live elsewhere: skills decisions happen **inside the task that produced the pattern**, and the Executive Report is **optional**. Plans created under earlier versions still carry three closing tasks (Security Review → Skills & Agents Discovery → Executive Report) and are executed under their own shape — never retrofitted mid-flight (`spec/DWP_SPECIFICATION.md` §6.5).

### Final Review (Last Task)

This task closes the plan, in this order:

**(a) Security pass** — over everything the plan changed, before the plan can complete:

- Reviews the plan's full accumulated diff for hardcoded secrets, injection risks, unsafe input handling, new attack surface, and auth/permission changes
- Audits dependencies the plan introduced or upgraded (best-effort, using the ecosystem's audit tooling where available)
- Verifies `docs/SECURITY.md` still reflects reality and updates it when the plan changed secrets handling, the auth model, or data boundaries
- Writes `analysis_results/SECURITY_REVIEW.md`, even when the conclusion is "no findings"
- A critical finding (e.g. a committed secret) blocks plan completion until fixed or explicitly accepted by the user
- Where an installed addon augments the pass (for example the AI Diff Reviewer local review, `authoring.md` §5.4), it runs here under the addon's never-block rule

Security is not a separate workstream bolted on at the end of a project — every plan leaves the repository's security documentation current and its own changes audited.

**(b) Final-state validation** — the repository's complete applicable test, lint, type-check and format suites run and pass on the **final** state (`spec/DWP_SPECIFICATION.md` §5.1.3). Fixes made during the review invalidate affected results, which are rerun: review → fixes and mirror refresh → final gates → closure. Nothing ships after its last applicable validation.

**(c) Skills reconciliation** — checks that every task's log carries a skills disposition and that every entry in `analysis_results/SKILLS_CANDIDATES.md` has one; finishes any warranted authoring still open (and validates it before (b) is final). It does **not** re-read the whole plan to rediscover patterns and writes **no** second discovery report — the ledger is the record.

**(d) Completion** — reports deliverables, validation evidence, limitations and PR links; offers the Executive Report **once**; sends the completion report through the configured channel (e.g. the Dailybot milestone) regardless of the answer. The plan is complete at this point.

### Task-Local Skills Decisions (Every Task)

The question "did this work create a reusable pattern worth a skill or agent?" is answered **inside each task, while the evidence is in context**:

- Every task's Completion & Log carries a **skills disposition**: `none`, `update <existing>`, `create <name>`, or `defer — <reason and owner>`. `none` needs no ledger row.
- A real candidate is appended to `analysis_results/SKILLS_CANDIDATES.md` with a stable ID (`T{task}-{seq}`), an evidence pointer and the disposition; on resume an existing ID is updated, never duplicated.
- Warranted, in-scope authoring (a new or updated skill/agent plus its catalog entry) happens **in that task, before its validation gate and commit**, after checking the existing `.agents/` catalog for duplicates. Prefer updating an existing capability; a single routine change does not justify a new skill.
- This keeps the virtuous cycle — plans → skills → better plans → better skills — without an end-of-plan re-read (`skills-integration.md` §11).

### Executive Report (Optional, On Request)

`analysis_results/EXECUTIVE_REPORT.md` is generated **only** when the developer asks — at the completion offer, earlier in the plan's guidelines, or at any later time (from durable evidence, without replaying the plan). No answer, a declined offer, or an unattended run leaves the plan complete with no report. When produced it is a comprehensive report written for cross-functional consumption:

- **Executive Summary** — Non-technical overview of what was accomplished
- **Product Impact** — User-facing changes, business value delivered
- **Technical Details** — Architecture decisions, code quality, files changed
- **QA Verification Guide** — Step-by-step guide for verifying changes
- **FAQs** — Common questions about the changes
- **Next Steps** — Recommended follow-up actions

The report adapts its emphasis based on plan type (code, docs, research, refactoring).

---

## 🔄 Multi-Project Commit Workflow

> **CRITICAL for plans that span multiple repositories (repositories/api-services, repositories/chatbot-functions, repositories/web-app, repositories/discord-gateway, etc.)**
>
> **For complex multi-repo features**, consider using an **Orchestrator Plan** instead of a direct multi-project plan. Orchestrator plans create child DWP plans in each sub-repository, leveraging each repo's own AGENTS.md and validation commands. See **section 13**.

### When Does This Apply?

This workflow applies when a Deep Work Plan involves changes to **multiple sub-projects** within the Dailybot ecosystem. Each sub-project is its own independent git repository.

### Per-Task Commit Protocol

**After completing EACH task in a multi-project plan:**

1. **Identify affected repositories:**
   ```bash
   # Check which repos have changes (from workspace root)
   cd repositories/api-services && git status
   cd ../chatbot-functions && git status
   cd ../web-app && git status
   cd ../discord-gateway && git status
   ```

2. **Run validations in each affected repository:**
   ```bash
   # API Services (from workspace root)
   cd repositories/api-services && codecheck

   # Chatbot Functions
   cd ../chatbot-functions && npm run test && npm run eslint:check

   # Web App
   cd ../web-app && npm run test && npm run lint

   # Discord Gateway
   cd ../discord-gateway && npm run test && npm run eslint:check
   ```

3. **Commit and push in each repository:**
   ```bash
   # Template for each repository
   cd {repository}
   git add -A
   git commit -m "type(scope): description - Task N of PLAN_{name}"
   git push
   ```

4. **Update the plan README** in the core-hub:
   - Mark the task as `[x]` completed
   - Update the Plan Status section
   - Commit plan tracking changes if needed

### Commit Message Format

For multi-project plans, use this format to maintain traceability:

```
type(scope): description - Task N of PLAN_{plan_name}

[Optional details]

Refs: Related commits in other repos (if applicable)
```

**Examples:**
```
feat(api): add notification preferences endpoint - Task 2 of PLAN_notification_system
feat(chatbot): implement notification dispatcher - Task 2 of PLAN_notification_system
feat(web): add notification settings UI - Task 3 of PLAN_notification_system
```

### Why Commit After Each Task?

| Benefit | Description |
|---------|-------------|
| **Recoverability** | If session is interrupted, all completed work is safely committed |
| **Traceability** | Each task has its own commit, easy to track or rollback |
| **Resume capability** | Plan can be resumed from any point with clear git history |
| **Multi-agent support** | Different agents can work on different tasks safely |
| **Progress visibility** | User can see exactly what was completed |

### Agent Behavior Checklist

When executing multi-project plans, the agent **MUST**:

- [ ] ✅ Complete all work for a single task before any commits
- [ ] ✅ Run validations in **each** affected repository
- [ ] ✅ Commit in each repository **separately** (not from root)
- [ ] ✅ Push to remote immediately (don't leave local-only commits)
- [ ] ✅ Update plan README and task log
- [ ] ✅ Report commit status to user after each task

**The agent MUST NOT:**

- ❌ Accumulate changes across multiple tasks
- ❌ Commit sub-project code from the root repository
- ❌ Skip pushing commits (risky for long-running plans)
- ❌ Continue without confirming commits succeeded
- ❌ Forget to commit in any affected repository

### Example: Complete Task Workflow

**Scenario:** Task 3 of PLAN_user_preferences modifies `repositories/api-services` and `repositories/web-app`

```bash
# 1. Work on the task (implementation)
# ... agent makes changes ...

# 2. Run validations (from workspace root)
cd repositories/api-services && codecheck
cd ../web-app && npm run test && npm run lint

# 3. Commit in api-services
cd ../api-services
git add -A
git commit -m "feat(api): add user preferences model and endpoints - Task 3 of PLAN_user_preferences"
git push

# 4. Commit in web-app
cd ../web-app
git add -A
git commit -m "feat(ui): add user preferences settings page - Task 3 of PLAN_user_preferences"
git push

# 5. Update plan tracking
cd ..
# Edit plan README.md: [ ] → [x] for Task 3
# Update Plan Status section

# 6. Report to user
# "Task 3 complete. Committed and pushed:
#  - api-services: feat(api): add user preferences model and endpoints
#  - web-app: feat(ui): add user preferences settings page"
```

---

## ⚠️ CRITICAL: Task Completion Tracking (MANDATORY)

> **THIS IS THE MOST IMPORTANT RULE OF THE ENTIRE SYSTEM**

### Why This Matters

The plan README's task list (`[ ]` / `[x]`) is the **SINGLE SOURCE OF TRUTH** for plan progress. Without proper task marking:
- Interrupted sessions cannot resume correctly
- Progress is lost and tasks may be repeated
- Plan status becomes unreliable
- Multi-day executions become impossible to track

### MANDATORY Actions After Each Task

**IMMEDIATELY after completing EACH task, the agent MUST:**

1. **Update the plan README.md** - Change `[ ]` to `[x]` for the completed task
2. **Update the Plan Status table** - Update the phase status and completed count
3. **Update the task file's Completion & Log section** - Record status, timestamp, and summary
4. **Update PROGRESS.md** - Add a short task summary (a few lines), key decisions, important values — the full narrative stays in the task file's Completion & Log; keep PROGRESS.md a bounded working index

### Example: Before and After

**BEFORE completing Task 3:**
```markdown
## Task List
- [x] Task 1: Setup
- [x] Task 2: Implementation
- [ ] Task 3: Testing        ← Currently working on
- [ ] Task 4: Documentation

## Plan Status
**Completed**: 2/4
```

**AFTER completing Task 3:**
```markdown
## Task List
- [x] Task 1: Setup
- [x] Task 2: Implementation
- [x] Task 3: Testing        ← Just completed, MUST mark!
- [ ] Task 4: Documentation

## Plan Status
**Completed**: 3/4
```

### Verification Checklist (Run After Each Task)

Before moving to the next task, verify:

- [ ] ✅ Plan README task is marked `[x]`
- [ ] ✅ Plan Status count is updated (e.g., "3/25")
- [ ] ✅ Task file Completion & Log section is filled
- [ ] ✅ PROGRESS.md is updated with task summary
- [ ] ✅ Changes are committed
- [ ] ✅ Dailybot progress report sent if task is independently significant (non-blocking — continue if fails)

### Consequences of Not Marking Tasks

❌ **If tasks are NOT marked as completed:**
- Resume operations will REDO already-completed work
- Time and resources will be wasted
- The plan becomes unreliable and confusing
- Long-running plans become impossible to manage

✅ **If tasks ARE properly marked:**
- Seamless resume after interruptions
- Clear progress visibility at all times
- Reliable multi-day/multi-session execution
- Accurate status reporting

---

---
