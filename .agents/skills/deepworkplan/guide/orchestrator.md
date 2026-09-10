# DeepWorkPlan Guide — Orchestrator Plans (Core Hub Only)

> Part of the DeepWorkPlan methodology guide. The routing index is
> [`GUIDE.md`](GUIDE.md); read only the guide files your flow names.

## 13. Orchestrator Plans (Core Hub Only)

> **This section applies exclusively to the Core Hub repository**, which orchestrates work across multiple sub-repositories in `repositories/`.

### 13.0. Hand-Off Rule (MANDATORY — read before anything else in this section)

> [!IMPORTANT]
> **An orchestrator agent must NEVER execute a child DWP itself.** Child DWPs must always be executed by a **separate agent session running inside the target repository**. The orchestrator's job is to *create* child DWPs, *verify readiness*, *emit hand-off prompts (one at a time or combined when children can run concurrently — see §13.6)*, and *register outputs after the user confirms execution* — not to run the children's tasks inline.

> [!TIP]
> **Parallelize whenever the dependency shape allows it.** Most multi-repo features with a frozen design contract (envelope spec, API contract, prompt architecture, …) qualify for **Contract-Parallel** mode (§13.6.2): children run concurrently against the shared spec, cutting wall-clock time ~50% without loss of safety. The hand-off rule applies to every child equally; what changes is whether hand-offs fire in batch (parallel) or one-at-a-time (runtime-dependent).

**Why hand-off (not inline execution):**

1. **Context boundary.** Each sub-repo has its own `AGENTS.md`, validation toolchain (Docker, `codecheck`, `npm run test`, etc.), test patterns (`*_test.py` vs `*.spec.ts`), and commit format. Executing a child from the Core Hub session silently mixes these contexts.
2. **Git hygiene.** Each sub-repo is its own independent git repository. Commits belong in each repo's git log with that repo's conventional format. Inline execution from Core Hub invites wrong-repo commits, stray `git status` noise, and broken audit trails.
3. **Autonomy.** Child DWPs are designed to be runnable independently by whichever agent (or human) is assigned to that repo — possibly in parallel with other children. Inline execution forces everything through one context window and blocks that parallelism.
4. **Safety.** If the orchestrator session is interrupted mid-child, the child DWP's progress/commits are easier to recover when they live entirely inside the target repo.

**What the orchestrator agent MUST do for every `execute_child_dwp` task:**

1. Verify predecessors are `[x] Executed` and their declared output artifacts exist on disk.
2. Emit a **ready-to-use hand-off prompt** to the user (or to a separate automated agent session running inside `repositories/{repo_name}/`). The prompt is a single copy-pasteable block that tells the target agent what plan to execute and what predecessor reports to read.
3. **Stop.** Do not `cd` into the target repo with write or execution intent. Do not edit target-repo files. Do not run the child DWP's tasks inline. Do not commit in the target repo.
4. **Wait** for the user to confirm the child DWP is complete (`DONE: ...` naming the declared artifact paths).
5. Verify from Core Hub (read-only) that the child plan reports `completed` and its declared artifacts exist, then register outputs in the orchestrator manifest and mark this task `[x]`.

**What the orchestrator agent MUST NOT do:**

- Navigate into `repositories/{repo_name}/` and iterate through the child DWP's tasks inline.
- Invoke subagents to execute the child's tasks as a proxy for the target repo's agent.
- Write the child DWP's analysis reports from the orchestrator session.
- Commit child DWP task work into the target repo's git history.

> **Exception (very narrow).** The `create_child_dwp` tasks DO require the orchestrator to navigate into the target repo to author the plan files. This is read-AGENTS.md-and-write-plan-files only — NOT executing the child plan's own tasks. Once the plan files are in place, the orchestrator returns to `/workspace` and never re-enters the target repo except to *verify* that the child completed and its declared artifacts exist. Integration checkpoint tasks (read-only cross-references across plan READMEs) are also fine from Core Hub.

See also the hand-off task template: `example_prompts/ORCHESTRATOR_TASK_TEMPLATE_execute_child_dwp.md`.

### 13.1. What Are Orchestrator Plans?

Orchestrator plans are a special type of Core Hub DWP plan whose tasks **create child DWP plans inside sub-repositories** rather than (or in addition to) directly executing code changes.

Instead of a single Core Hub plan that tries to implement everything across repos, an orchestrator plan:

1. **Creates independent DWP plans** inside each affected sub-repository (e.g., `repositories/api-services/`, `repositories/web-app/`)
2. **Reads each repo's AGENTS.md and DWP guide** to generate contextually-correct child plans that follow that repo's own rules, validation commands, and conventions
3. **Tracks child plan creation and execution status** from the orchestrator README
4. **Supports independent execution** — each repo's agent can execute its child DWP autonomously

**When to use orchestrator plans:**
- Feature spans 2+ repositories with independent implementation work per repo
- Each repo needs 3+ tasks with repo-specific validation
- Sub-repos have their own DWP systems (`.dwp/`) and `AGENTS.md`
- You want per-repo autonomous execution or independent resume capability
- Different agents might work on different repos

**When NOT to use orchestrator plans:**
- Single-repo plans
- Simple multi-repo changes (config replication, infra updates) — use direct multi-project plans instead
- Total tasks < 5 across all repos
- Changes are tightly coupled and can't be split into independent repo work

### 13.2. Orchestrator Plan vs Direct Multi-Project Plan

| Aspect | Direct Multi-Project Plan | Orchestrator Plan |
|--------|--------------------------|-------------------|
| **Complexity** | Simple cross-repo changes | Complex features spanning repos |
| **Execution** | Core Hub agent does everything | Orchestrator hands off each child DWP to a separate agent session running inside the target sub-repo; those agents execute independently (§13.0) |
| **Rules** | Core Hub plan must encode each repo's rules | Each child DWP uses its own repo's rules |
| **Validation** | Must inline each repo's validation commands | Child DWP inherits repo's validation automatically |
| **Resume** | Resume from single plan | Resume per-repo independently |
| **Scale** | Works well for < 5 tasks total | Designed for large multi-repo features |
| **Best for** | Config changes, infra updates, replication tasks | New features, major refactors, API+UI work |

### 13.3. Orchestrator Plan Structure

An orchestrator plan's README includes a **Child DWP Plans** section that tracks all child plans:

```markdown
## Child DWP Plans

| # | Repository | Child Plan | Status | Depends On |
|---|-----------|-----------|--------|-----------|
| 1 | api-services | PLAN_{feature}_api | [ ] Created / [ ] Executed | — |
| 2 | web-app | PLAN_{feature}_web | [ ] Created / [ ] Executed | Child #1 |
| 3 | chatbot-functions | PLAN_{feature}_chatbot | [ ] Created / [ ] Executed | Child #1 |

### Execution Mode (pick one — see §13.6 for the selection algorithm)
- [ ] **Contract-Parallel** (recommended default): children share a frozen design contract (from orchestrator design tasks) but don't need each other's runtime code; hand off concurrently, register `DONE`s as they arrive.
- [ ] **Fully Parallel / Distributed**: children are fully independent; hand off concurrently.
- [ ] **Sequential Runtime-Dependent**: one child's runtime code is required at BUILD time by another; hand off one at a time in dependency order (formerly labeled "Sequential with Output Handoff" — keep this label only for plans that truly need the predecessor's produced artifacts during implementation).

### Dependency Rules
- Child #2 (web-app) depends on Child #1 (api-services) — API endpoints must exist before web views
- Child #3 (chatbot-functions) depends on Child #1 (api-services) — API must be ready
```

**Status tracking:**
- `[ ] Created` → child DWP plan has been generated in the sub-repo
- `[ ] Executed` → child DWP plan has been executed (all its internal tasks completed)
- When marking as created: `[x] Created / [ ] Executed`
- When marking as completed: `[x] Created / [x] Executed`

### 13.4. Orchestrator Task Types

Orchestrator plans use three special task types:

#### `create_child_dwp` — Child DWP Creation Task

**Naming:** `N.task_create_child_dwp_{repo_name}.md`

This task instructs the agent to navigate to a sub-repository, read its documentation, and create a complete DWP plan there. See section 13.5 for the full protocol.

#### `execute_child_dwp` — Child DWP Execution HAND-OFF Task

**Naming:** `N.task_execute_child_dwp_{repo_name}.md`

> **This task is a hand-off, not an inline execution.** See §13.0 (Hand-Off Rule).

This task verifies execution readiness (predecessor outputs available), emits a ready-to-use hand-off prompt for a separate agent session running inside the target sub-repository, pauses, and — after the user confirms the child DWP is complete — registers the child's outputs in the orchestrator manifest. The orchestrator agent itself **never** runs the child DWP's own tasks. See sections 13.9 and 13.10 for predecessor-output protocols, and `example_prompts/ORCHESTRATOR_TASK_TEMPLATE_execute_child_dwp.md` for the full task template.

#### `integration_checkpoint` — Integration Verification Task

**Naming:** `N.task_integration_checkpoint.md`

This task verifies that child DWP plans are compatible — API contracts match, data models are consistent, naming conventions align, and output contracts are satisfied. Place these between dependency groups.

#### Hybrid Plans

An orchestrator plan can mix task types:
- **Direct tasks** — normal task files for design docs, API contracts, shared configuration
- **`create_child_dwp` tasks** — create child DWPs in sub-repos
- **`integration_checkpoint` tasks** — verify compatibility between child plans
- **`execute_child_dwp` tasks** — **hand-off** tasks that emit an execution prompt for a separate agent session running in the target sub-repo and pause for user confirmation (Sequential with Output Handoff mode). The orchestrator never runs the child inline — see §13.0.

**Typical task order:**
1. Direct tasks (design, API contract definition)
2. `create_child_dwp` tasks in dependency order
3. `integration_checkpoint` tasks between dependency groups
4. `execute_child_dwp` tasks in dependency order (Sequential with Output Handoff mode only)
5. The single mandatory **Final Review** (`{N}.task_final_review.md`)

### 13.5. Child DWP Creation Protocol

When the agent executes a `create_child_dwp` task, it must follow this protocol:

#### Step 1: Navigate to target repository

```bash
cd repositories/{repo_name}
```

Verify the repository exists and is accessible.

#### Step 2: Read the target repo's documentation

**Read these files in order:**

1. **`AGENTS.md`** — Extract:
   - Validation commands (e.g., `codecheck -f`, `npm run test && npm run eslint:check`)
   - Test file naming convention (e.g., `*_test.py`, `*.spec.ts`)
   - Commit format and scope conventions
   - Tech stack specifics (framework, language, package manager)
   - Docker requirements (e.g., API Services must validate inside Docker)
   - Import order rules, code style rules

2. **`guide/GUIDE.md`** — Understand:
   - Repo-specific DWP conventions (if any differences from Core Hub)
   - Available templates and examples

#### Step 3: Handle missing DWP infrastructure

If the target repo does NOT have the DeepWorkPlan skill installed:

1. Install the DeepWorkPlan skill in that repo (it ships its own `guide/GUIDE.md`
   and `examples/`), then ensure the gitignored output root exists:
   ```
   .dwp/
   ├── drafts/
   └── plans/
   ```
2. Reason about the target repo's tech stack (validation commands, test patterns,
   etc.) per `shared/adaptation.md` — never copy a fixed validation set.
3. Add `.dwp/` to the repo's `.gitignore`.

#### Step 4: Create the child DWP plan

Create the plan at:
```
repositories/{repo_name}/.dwp/plans/PLAN_{feature}_{repo_short}/
```

Create all required files:

- **README.md** — Following the target repo's DWP guide format:
  - Goal (referencing the parent orchestrator plan)
  - Context (tech stack from the repo's AGENTS.md)
  - Global Guidelines (from the repo's AGENTS.md)
  - Task List with `[ ]` checkboxes
  - Execution Rules
  - Parent plan reference: `> This is a child DWP created by orchestrator plan PLAN_{parent_name} in the Core Hub.`

- **Task files** — `N.task_{title}.md` for each task, using:
  - The target repo's validation commands (NOT the Core Hub's)
  - The target repo's test naming patterns
  - The target repo's commit format and scope
  - The target repo's linting and formatting rules

- **PROMPTS.md** — Using the target repo's template if available, or Core Hub's
- **PROGRESS.md** — Initial template
- **analysis_results/** — Empty folder
- **Mandatory final task** — the single **Final Review**, last
  (`{N}.task_final_review.md`). It covers the security pass, final-state
  validation and skills reconciliation in one task.

#### Step 5: Return to Core Hub and update tracking

```bash
cd /workspace  # Return to Core Hub root
```

Update the orchestrator plan's README:
- Mark the child DWP as `[x] Created` in the Child DWP Plans table
- Note the child plan's full path for reference

#### Step 6: Commit

Commit in the Core Hub repository (orchestrator tracking files only — the child DWP plan files are in the sub-repo's git-ignored `results/` folder).

### 13.6. Execution Modes

> **All modes obey §13.0 — the orchestrator agent NEVER runs a child DWP's own tasks.** What changes between modes is the **dependency shape** between children, which determines whether children can execute concurrently or must wait on each other.

> [!IMPORTANT]
> **Default to the most parallel mode that your dependency analysis supports.** Up-front contract design (Tasks 1–2 of the orchestrator: envelope spec, API contract, prompt architecture, etc.) is cheap and unlocks parallel child execution. An orchestrator agent that creates good design docs BEFORE the `create_child_dwp` tasks almost always unlocks Contract-Parallel mode below — saving ~50% wall-clock time without losing safety.

#### Mode selection algorithm (apply during plan creation)

When designing an orchestrator plan with 2+ child DWPs, answer these questions **in order**:

1. **Do any children need runtime code from another child?** (e.g., child B imports a library child A ships, or child B depends on child A's deployed endpoint at BUILD time, not deploy time)
   - Yes → **Sequential Runtime-Dependent** (§13.6.1). One child must execute before another.
   - No → go to question 2.

2. **Do children share a design contract (envelope, API schema, prompt spec, data model)?**
   - Yes → **Contract-Parallel** (§13.6.2). Children run in parallel against a frozen contract produced by the orchestrator's own design tasks.
   - No → **Fully Parallel / Distributed** (§13.6.3). Children are independent; no contract alignment needed.

> **Practical rule of thumb:** once an orchestrator has `integration_checkpoint` output and/or design-doc output (envelope spec, API contract, etc.) that BOTH children reference, the children usually qualify for **Contract-Parallel** — even if the product owner originally thought the dependency was runtime. Most "sequential with output handoff" cases are actually contract dependencies, not runtime dependencies.

#### 13.6.1 Sequential Runtime-Dependent (rare — only when truly needed)

One child must fully execute before another starts because the successor's code literally imports or calls the predecessor's code/endpoints at build / test time.

Flow:

1. Orchestrator creates all child DWPs (concurrent).
2. Orchestrator runs integration checkpoint.
3. **Hand off** Child #1 → separate agent session executes it → user confirms `DONE`.
4. Orchestrator verifies + registers outputs.
5. **Hand off** Child #2 (with explicit reference to Child #1's declared artifacts in the hand-off prompt) → ...
6. Continue until all children executed.

**Best for:**
- Library/package authored in one child and consumed in another (e.g., a shared SDK).
- Critical schema migration in child A that child B's tests depend on.

**Cost:** wall-clock time is sum of each child's duration.

#### 13.6.2 Contract-Parallel (recommended default when children share a spec)

Children share a design contract frozen up-front (envelope spec, API contract, prompt spec, data model, etc.) but don't need each other's runtime code during implementation. Children execute concurrently against the spec, and only re-sync at the end for integration testing.

Flow:

1. Orchestrator produces **design doc(s)** as direct tasks (typically Tasks 1–2) — envelope schema, API contract, prompt architecture, etc.
2. Orchestrator creates all child DWPs (they reference the frozen design docs).
3. Orchestrator runs integration checkpoint verifying both children's READMEs align with the design docs.
4. Orchestrator emits a **combined hand-off block** listing both children's prompts at once, with a note: *"these children can be executed concurrently in separate agent sessions. They share the frozen design contract at `analysis_results/<SPEC>.md`. Neither child needs the other's runtime code or produced artifacts during implementation."*
5. User runs both children in parallel (two sessions, possibly two humans / agents).
6. As each child reports `DONE`, orchestrator verifies + registers.
7. When **both** children are `[x] Executed`, orchestrator runs E2E validation + synthesis.

**Best for:**
- API ↔ client (after the contract spec is frozen).
- Emitter ↔ receiver (after the envelope schema is frozen).
- Multiple repos implementing to a shared design.

**Cost:** wall-clock time ≈ max(child durations) — roughly half of Sequential.

**Prerequisites:**
- Design docs MUST be frozen before children start.
- Children's READMEs explicitly reference the design docs as hard dependencies.
- E2E validation is deferred to a post-children task (orchestrator Task 8 or similar).

**Precondition check for parallel start:** the api-side (or any successor-in-spirit) child README's Task 1 precondition should require **the sibling child's README + frozen design docs**, not the sibling's finished output. The sibling's produced artifacts matter later (at integration-validation time), not at implementation-start time.

#### 13.6.3 Fully Parallel / Distributed (when children are fully independent)

Children have no cross-repo dependencies — neither runtime nor contract.

Flow:

1. Orchestrator creates all child DWPs.
2. Emits hand-off block for all at once.
3. Children execute concurrently, totally independently.
4. Each `DONE` registered as it arrives.
5. Final synthesis runs after all done.

**Best for:**
- Overnight autonomous execution across repos.
- Different teams own different repos.
- Config-replication or similar mechanical work.

**Cost:** wall-clock time ≈ max(child durations).

---

> [!TIP]
> **How to choose during plan design:**
>
> - If you have design tasks (Tasks 1–2 producing specs/docs) in Phase 0 BEFORE `create_child_dwp`, you're almost certainly on **Contract-Parallel**. Express this explicitly in the orchestrator plan's README (§4.2 Execution mode).
> - If you find yourself writing "child B needs child A's finished output at runtime" — re-examine. Usually child B needs the CONTRACT (already in the spec doc) plus a fixture/example payload (also derivable from the spec). The predecessor's full output is usually only needed at E2E validation time.
> - Keep `Sequential Runtime-Dependent` as a **fallback** for genuinely linked code (shared library extraction, breaking-schema migrations).

### 13.7. Inter-Plan Dependencies

Dependencies between child plans follow data flow order:

```
Typical dependency order:
  Data Layer (API/DB) → Service Layer (Chatbot/Gateway) → Presentation (Web App)

Example:
  api-services (models, endpoints) → web-app (views consuming endpoints)
  api-services (models, endpoints) → chatbot-functions (handlers calling API)
  api-services (models, endpoints) → discord-gateway (commands using API)
```

**Declaring dependencies:**
- Use the `Depends On` column in the Child DWP Plans table
- Reference by child plan number (e.g., "Child #1")
- Multiple dependencies: "Child #1, Child #2"

**Integration checkpoints:**
- Place `integration_checkpoint` tasks between dependency groups
- These verify that child plans are compatible before execution continues
- Check: API contract alignment, data model consistency, naming conventions

### 13.8. Orchestrator Context Manifest

The **Orchestrator Context Manifest** (`ORCHESTRATOR_MANIFEST.md`) is an optional but recommended file in the parent plan folder that provides cross-repo context to all child DWPs.

#### Why Use a Manifest?

When a child DWP executes inside a sub-repository, the executing agent has no visibility of:
- The parent plan's shared design decisions and constraints
- What other child DWPs exist and what they're responsible for
- What outputs predecessor child DWPs have produced
- Whether prerequisite work has been completed

The manifest solves this by providing a single file that child DWPs reference for global context.

#### Manifest Structure

Create `ORCHESTRATOR_MANIFEST.md` in the parent plan folder:

```text
PLAN_{feature}/
├── README.md
├── ORCHESTRATOR_MANIFEST.md   ← Cross-repo context manifest
├── PROMPTS.md
├── PROGRESS.md
├── analysis_results/
└── N.task_*.md
```

#### Manifest Template

```markdown
# Orchestrator Context Manifest: PLAN_{feature}

> This manifest provides cross-repo context for all child DWP plans.
> It is created during orchestrator plan generation and updated during execution.

## 1. Shared Context

### Design Decisions
- {Decision 1}: {rationale}
- {Decision 2}: {rationale}

### API Contracts
- {Contract file or inline specification}

### Global Constraints
- {Constraint 1}
- {Constraint 2}

## 2. Child DWP Registry

| # | Repository | Child Plan | Role | Status |
|---|-----------|-----------|------|--------|
| 1 | {repo1} | PLAN_{feature}_{repo1_short} | {role} | pending |
| 2 | {repo2} | PLAN_{feature}_{repo2_short} | {role} | pending |

## 3. Dependency Graph

{repo1} ──→ {repo2}    (repo2 depends on repo1's outputs)

### Dependency Details

| Consumer | Depends On | Required Outputs | Reason |
|----------|-----------|-----------------|--------|
| {repo2} | {repo1} | API contract in `analysis_results/`, endpoint list | Web needs to know API contract |

## 4. Output Contracts

### What Each Child DWP Produces

| Child Plan | Expected Outputs | Description |
|-----------|-----------------|-------------|
| PLAN_{feature}_{repo1_short} | `analysis_results/*` (name the exact files) | API endpoints, data models |
| PLAN_{feature}_{repo2_short} | `analysis_results/*` (name the exact files) | UI components, integration |

> **Name real files, not a report.** The Executive Report is **optional** under
> DWP 2.3.0 — it is offered once at completion and generated only on request, so
> a successor must never be made to depend on one existing. Declare the concrete
> artifacts the child will write (a contract document, a schema, an endpoint
> list). If an orchestrator genuinely wants a report as a downstream input, it
> **MUST** say so in the `create_child_dwp` task, so the child plan records the
> request up front and the report becomes a real declared output.

### What Each Child DWP Consumes

| Child Plan | Required Inputs | Source |
|-----------|----------------|--------|
| PLAN_{feature}_{repo1_short} | (none — first in chain) | — |
| PLAN_{feature}_{repo2_short} | Predecessor's declared output artifacts | PLAN_{feature}_{repo1_short} |

## 5. Execution State (Updated During Execution)

| # | Child Plan | Created | Executed | Declared Outputs Present | Key Outputs |
|---|-----------|---------|----------|--------------------------|-------------|
| 1 | PLAN_{feature}_{repo1_short} | [ ] | [ ] | — | — |
| 2 | PLAN_{feature}_{repo2_short} | [ ] | [ ] | — | — |

### Completed Output References
<!-- Updated after each child DWP completes execution -->
```

#### When to Create a Manifest

- **Always recommended** for orchestrator plans with dependencies between child DWPs
- **Required** when using "Sequential with Output Handoff" execution mode
- **Optional** for fully parallel execution with no inter-child-DWP dependencies
- **Backward compatible** — orchestrator plans without a manifest continue to work as before

### 13.9. Inter-Child-DWP Output Passing Protocol

When child DWPs have data dependencies (e.g., Web needs to know what API endpoints exist), this protocol ensures outputs from predecessor child DWPs are available to dependent successors.

#### How Output Passing Works

```text
Phase 1: Orchestrator creates child DWPs (with manifest context injected)
  ↓
Phase 2: Orchestrator HANDS OFF Child #1 (predecessor) to a separate agent
         running inside the target sub-repo → that agent executes Child #1
  ↓ Child #1 completes → user replies DONE → orchestrator verifies the
    child completion + declared artifacts on disk, registers outputs in manifest
  ↓
Phase 3: Orchestrator HANDS OFF Child #2 (dependent) with a prompt
         that instructs the target agent to read Child #1's executive
         report before Task 1
  ↓ Target agent loads predecessor outputs and executes Child #2
  ↓
Phase 4: Child #2 completes → user replies DONE → orchestrator verifies
         and registers outputs in manifest
```

> The orchestrator agent itself never moves from Phase 2 to Phase 3 by running Child #1's own tasks. It creates, hands off, waits, registers — then creates, hands off, waits, registers.

#### Output Registration

After a child DWP completes execution, its outputs are registered in the manifest's "Execution State" section:

```markdown
## 5. Execution State (Updated During Execution)

| # | Child Plan | Created | Executed | Declared Outputs Present | Key Outputs |
|---|-----------|---------|----------|--------------------------|-------------|
| 1 | PLAN_feature_api | [x] | [x] | Available | API endpoints, data models |
| 2 | PLAN_feature_web | [x] | [ ] | — | — |

### Completed Output References

#### Child #1: PLAN_feature_api (api-services)
- **Declared outputs:** `repositories/api-services/.dwp/plans/PLAN_feature_api/analysis_results/API_CONTRACT.md`
- **Completion evidence:** that plan's `state.json` (`status: completed`) and its
  Final Review task log.
- **Key outputs:**
  - API endpoints: GET/PUT/PATCH /api/v1/preferences/
  - Data model: UserPreferences (fields, types, constraints)
  - Test coverage: 95%+ on all new code
- **Summary:** CRUD API for user preferences fully implemented.
```

#### Predecessor Output Consumption

This section describes the **target repo's agent** (the one actually executing the child DWP after the orchestrator hands off — not the orchestrator itself). When that agent starts executing a dependent child DWP, it must:

1. **Read the manifest** — Check the "Execution State" section.
2. **Verify prerequisites** — Ensure all required predecessor child DWPs are marked as `[x] Executed`.
3. **Load predecessor outputs** — Read the declared output artifacts and key outputs listed in "Completed Output References".
4. **Inject predecessor context** — Use predecessor outputs as additional context when executing the child DWP's tasks.

The orchestrator's hand-off prompt should explicitly name which predecessor artifacts to read before Task 1. Name the concrete files the predecessor declared — never assume an Executive Report exists, because it is generated only on request.

#### What to Pass as Predecessor Context

| Output Type | How to Use |
|-------------|-----------|
| **Declared output artifacts** | Read for the contract the successor must honor (endpoints, schemas, decisions) |
| **Final Review task log** | Read for what was validated, what was deferred, and any accepted risk |
| **Executive Report** (only when the orchestrator requested one) | Read for the overall summary |
| **API Endpoints** | Use as input for API client/service layer tasks |
| **Data Models** | Use as reference for type definitions and validation rules |
| **Key Decisions** | Apply constraints and conventions established by predecessor |

#### Fallback When Manifest Is Missing

If no manifest exists (backward compatibility):
- Check the parent plan README's "Child DWP Plans" table for status
- Look for the declared output artifacts in predecessor child DWP plan folders
- If no predecessor outputs are available, proceed with the information in the child DWP's own README (which includes the parent plan reference from section 13.5)

#### Child DWP Dependency Blocking

When a child DWP has predecessors, its README must include a clear blocking notice:

```markdown
## Input Dependencies

> ⚠️ **EXECUTION BLOCKED** until all inputs are available.

| Predecessor | Status | Declared Output Path |
|-------------|--------|----------------------|
| PLAN_{feature}_{predecessor_short} | [ ] Ready | `repositories/{repo}/.dwp/plans/PLAN_{feature}_{predecessor_short}/analysis_results/{declared_artifact}` |

**Before starting execution:**
1. Verify the predecessor plan is complete — its `state.json` reads `status: completed` — and that each declared output artifact above exists
2. Read those artifacts — extract API endpoints, data models, key decisions
3. If a declared artifact is missing, STOP and report: "Cannot start — waiting for {predecessor} to complete"
4. Use predecessor context throughout execution, especially for integration-related tasks
```

This blocking notice ensures that **any agent** — whether executing from Core Hub or from the sub-repo directly — knows to check for prerequisites before starting.

### 13.10. Dependency-Aware Execution Modes

Building on the basic Sequential and Distributed modes (section 13.6), orchestrator plans can use enhanced execution modes that handle output passing automatically.

#### Mode Comparison (aligned with §13.6 taxonomy)

| Mode (new name) | Legacy name | Output Passing | When to Use |
|-----------------|-------------|---------------|-------------|
| **Contract-Parallel** | (was a subset of "Sequential with Output Handoff") | Via frozen design contract at plan level | **Recommended default** when children share a spec produced by orchestrator's design tasks. Children run concurrently. |
| **Fully Parallel / Distributed** | "Parallel" / "Distributed" | None | Children are fully independent. |
| **Sequential Runtime-Dependent** | "Sequential with Output Handoff" | Automatic — the predecessor's declared artifacts are referenced in the successor's hand-off prompt | Only when child B's code literally imports/needs child A's code at build/test time. |
| **Mixed** | "Mixed" | Per-group | Dependency graph has both parallel and sequential sub-groups. |

#### Sequential with Output Handoff

This is the recommended mode when child DWPs have data dependencies. **Remember §13.0: the orchestrator agent never executes the children itself** — it hands off and waits. The flow is:

```text
1. Create ALL child DWPs (with manifest context)
2. Hand off Child #1 (no predecessors) → separate agent session executes it
   → User confirms DONE → orchestrator registers outputs in manifest
3. Hand off Child #2 with Child #1's declared artifacts referenced in the prompt
   → separate agent session executes it
   → User confirms DONE → orchestrator registers outputs in manifest
4. Continue until all children are executed
5. Orchestrator runs synthesis / skills / executive tasks in Core Hub
```

**Orchestrator plan uses `execute_child_dwp` hand-off tasks** in addition to `create_child_dwp` tasks:

```markdown
## Task List
- [ ] Task 1: Design API contract (direct task)
- [ ] Task 2: Create child DWP for api-services (create_child_dwp)
- [ ] Task 3: Create child DWP for web-app (create_child_dwp)
- [ ] Task 4: Integration checkpoint
- [ ] Task 5: Execute child DWP for api-services (execute_child_dwp)
- [ ] Task 6: Execute child DWP for web-app (execute_child_dwp)
- [ ] Task 7: Final Review
```

#### Mixed Mode

For complex dependency graphs where some children can run in parallel:

```text
Dependency graph:
  api-services ──→ web-app
  api-services ──→ chatbot-functions
  (web-app and chatbot-functions are independent of each other)

Execution:
1. Create ALL child DWPs
2. Execute api-services child DWP → register outputs
3. Execute web-app AND chatbot-functions (both depend only on api-services)
4. Register all outputs
```

> **Note:** When a single agent executes a plan, "parallel" tasks within a group are still executed sequentially, but they do NOT pass outputs to each other — they only consume outputs from previous groups.

#### Hand-Off Readiness Gate

Before **handing off** a child DWP, the orchestrator agent must verify — but **what counts as readiness depends on the execution mode** (§13.6):

**Contract-Parallel (§13.6.2) or Fully Parallel / Distributed (§13.6.3) — lenient gate:**

1. **Design docs exist** — referenced contract / spec files are on disk.
2. **Integration checkpoint passed** — PROCEED decision is documented.
3. **All sibling child DWP folders exist** — `test -d <path>` for each.

A predecessor's *finished outputs* are **NOT required** at hand-off time — they matter later, at E2E-validation time.

**Sequential Runtime-Dependent (§13.6.1) — strict gate:**

1. **All predecessors executed** — manifest Execution State shows `[x] Executed` for each predecessor.
2. **Outputs available** — "Completed Output References" has entries for all predecessors.
3. **Declared artifacts exist** — the predecessor's declared output files on disk.

If any required check fails, orchestrator STOPS:

```
BLOCKED: Cannot hand off Child #{N} — prerequisite not met:
- Mode: Sequential Runtime-Dependent | Contract-Parallel | Fully Parallel
- Missing: {design doc path | sibling folder | predecessor declared artifact}
- Action: {what to do next}
```

> Reminder (§13.0): the orchestrator never executes Child #{M} itself to unblock Child #{N}. It emits the Child #{M} hand-off prompt and waits — **unless** this is a Contract-Parallel or Fully Parallel plan, in which case children can be handed off in a single batch without waiting on each other.

#### When a plan is Contract-Parallel, emit a COMBINED hand-off block

For Contract-Parallel plans (the default for well-designed multi-repo features), the orchestrator can emit all children's hand-off prompts at once in a single message, noting they can run concurrently:

```
The following child DWPs can be executed CONCURRENTLY in separate agent sessions. They share the frozen design contract at `<path-to-spec>` and do NOT depend on each other's runtime code.

Session A — inside `repositories/{repo1}/`:
  {prompt for child 1}

Session B — inside `repositories/{repo2}/`:
  {prompt for child 2}

When each child reports DONE, paste its DONE reply here. I will continue once BOTH are complete.
```

This cuts wall-clock time ~50% vs sequential without sacrificing correctness, assuming the design contract (Task 1–2 output) is frozen and the integration checkpoint passed.

---
