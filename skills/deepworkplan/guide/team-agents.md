# DeepWorkPlan Guide — Team Agents Execution Mode (Claude Code Only)

> Part of the DeepWorkPlan methodology guide. The routing index is
> [`GUIDE.md`](GUIDE.md); read only the guide files your flow names.

## 14. Team Agents Execution Mode (Claude Code Only)

> **Progressive Enhancement:** Team agents features are optional metadata in DWP plans.
> Non-Claude agents (Cursor, Codex, Gemini) safely ignore these sections and execute tasks sequentially.
> All plans remain fully functional without team agents.
>
> **Reference:** For the team-agents task template, see [`examples/TEAM_AGENTS_TASK_TEMPLATE.md`](../examples/TEAM_AGENTS_TASK_TEMPLATE.md).

### 14.1. Overview

Team agents allow multiple Claude Code instances to work on plan tasks **in parallel**. One session acts as team lead, coordinating work and synthesizing results. Teammates work independently, each in its own context window, communicating via a shared task list and direct messaging.

**When to use team agents in DWP plans:**
- Plan has 3+ tasks that can execute in parallel (no dependencies between them)
- Tasks involve independent modules, files, or research areas
- Combined effort benefits from parallel exploration (review, debugging, research)

**When NOT to use:**
- Tasks are strictly sequential (each depends on previous)
- Tasks modify the same files (risk of overwrites)
- Simple plans with 2-3 tasks (coordination overhead exceeds benefit)

**Execution modes comparison:**

| Mode | Agent Support | Description |
|------|--------------|-------------|
| **Sequential** (default) | All agents | Tasks executed one at a time, in order |
| **Subagents** | Claude Code | Spawn helper agents within same session for focused sub-tasks |
| **Team Agents** | Claude Code only | Multiple Claude instances work parallel tasks with shared coordination |
| **Orchestrator** | All agents | Parent plan creates child DWPs in sub-repos |

### 14.2. Parallel Task Groups

Plans can define **parallel task groups** — sets of tasks that can execute simultaneously by different teammates.

**In the plan README.md, add a "Team Agents Configuration" section AFTER all standard sections:**

```markdown
## Team Agents Configuration (Claude Code Only)

> **Note:** This section is used by Claude Code team agents for parallel execution.
> Other AI agents should ignore this section and execute all tasks sequentially.

### Parallel Task Groups

| Group | Tasks | Teammates | Description |
|-------|-------|-----------|-------------|
| Sequential | 1-2 | Lead only | Setup and prerequisites |
| Parallel A | 3, 4, 5 | 3 teammates | Independent module work |
| Sequential | 6 | Lead only | Integration checkpoint |
| Parallel B | 7, 8 | 2 teammates | Testing and documentation |
| Sequential | 9-11 | Lead only | Final tasks (mandatory) |

### Teammate Roles

| Role | Assigned Tasks | Model | Spawn Prompt |
|------|---------------|-------|-------------|
| API Specialist | 3 | sonnet | "Focus on API endpoint changes in src/api/..." |
| Frontend Dev | 4 | sonnet | "Focus on web UI components in src/components/..." |
| Test Engineer | 5 | sonnet | "Focus on test coverage across all modules..." |
```

**Key rules for parallel task groups:**
- Tasks within a parallel group must have **no file dependencies** between them
- Each teammate must own a distinct set of files (no overlap)
- The mandatory Final Review is **always sequential** (legacy plans: their three closing tasks likewise)
- Integration checkpoints between parallel groups are recommended

### 14.3. Task File Additions for Team Agents

Each task file can optionally include team agent metadata **AFTER all standard sections**:

```markdown
## Team Agents Metadata (Claude Code Only)

- **Parallel Group:** A
- **Teammate Role:** API Specialist
- **Can Run With:** Tasks 4, 5 (no file conflicts)
- **Blocks:** Task 6 (integration checkpoint)
- **Files Owned:** src/api/, tests/api/
- **Spawn Prompt:** "You are an API specialist. Focus on endpoint changes in src/api/. Follow the patterns in AGENTS.md for this repo. Report findings when complete."
```

> Non-Claude agents ignore this section entirely. It doesn't affect sequential execution.

### 14.4. Progressive Enhancement Pattern

The progressive enhancement pattern ensures team agent metadata is **additive only**:

1. **Plan README:** Add optional "Team Agents Configuration" section AFTER standard sections
2. **Task files:** Add optional "Team Agents Metadata" section AFTER standard sections
3. **Execution:** Claude Code reads metadata for parallel execution; other agents skip it
4. **Validation:** Same validation commands for all agents — no team-agent-specific validations

**Rules:**
- NEVER put required information inside team agent sections
- NEVER make task execution depend on team agent communication
- All tasks MUST be independently executable in sequential order
- Team agents sections are optimization hints, not execution requirements
- Task numbering remains sequential (1, 2, 3...) — parallel groups overlay the numbering

### 14.5. Execution Flow with Team Agents

> **IMPORTANT: Use REAL team agents, NOT subagents.**
> Real team agents use `TeamCreate` + `Agent` with `team_name` + `SendMessage` + `TeamDelete`.
> Subagents (Agent tool alone, without `team_name`) are NOT team agents — they lack shared task lists and inter-agent messaging.

When a DWP plan with team agent metadata is executed in Claude Code:

1. **Lead reads plan README** and detects "Team Agents Configuration" section
2. **Asks user** whether to use team agents or sequential execution
3. **Sequential tasks execute normally** (lead handles them)
4. **At parallel group boundary**, lead uses this exact sequence:
   - `TeamCreate` → creates team `"dwp-{plan_name}-group-{letter}"`
   - `Agent` with `team_name` → spawns each teammate by role name (from Teammate Roles table)
   - `TaskCreate` → creates shared task entries for each parallel task
   - `TaskUpdate` with `owner` → assigns each task to its designated teammate
5. **Teammates work independently:**
   - Read their assigned task file
   - Follow standard execution rules (validation, commit, logging)
   - Report completion to lead via automatic messaging
   - Can message each other if coordination is needed
6. **Lead waits for all parallel tasks** to complete
7. **Lead shuts down teammates** via `SendMessage` with `type: "shutdown_request"`
8. **Lead cleans up** with `TeamDelete`
9. **Integration checkpoint** (if defined) runs as sequential task
10. **Next group** proceeds (sequential or another parallel group)
11. **Mandatory final tasks** always run sequentially under the lead

**How to verify real team agents are active (not subagents):**
- Status bar shows: `Team: dwp-{plan_name}-group-{letter} · {N} teammates`
- NOT: `{N} local agents` (that means subagents were used — incorrect)
- Pressing Enter shows "Teammates" with named roles, not "Background tasks > Local agents"

**Fallback:** If team agents are disabled, unavailable, or execution fails at any point, **all remaining tasks execute sequentially** (standard behavior). No special handling needed — tasks are designed to work sequentially.

### 14.6. Integration with Orchestrator Plans

Team agents can be used WITHIN orchestrator plans at two levels:

1. **Orchestrator level:** Team agents can execute `create_child_dwp` tasks in parallel (when child DWPs have no dependencies between them)
2. **Child DWP level:** Individual child DWPs can define their own parallel task groups in their README

These are independent — orchestrator parallelism and child DWP parallelism don't interfere with each other.

**Example:** An orchestrator plan creates child DWPs for api-services and web-app. The `create_child_dwp` tasks can run in parallel (team agents). Then each child DWP, when executed, may use team agents internally for its own parallel task groups.

### 14.7. Quality Gate Hooks for Team Agents

Claude Code hooks can enforce quality during team execution:

- **`TeammateIdle`**: Runs when a teammate is about to go idle. Exit code 2 sends feedback and keeps the teammate working.
- **`TaskCompleted`**: Runs when a task is being marked complete. Exit code 2 prevents completion and sends feedback.

Example hook in `.agents/settings.json` (Claude Code reads via the `.claude → .agents` symlink; Cursor reads `.cursor/hooks.json` via the `.cursor → .agents` symlink):
```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash .agents/hooks/validate-task-completion.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

These hooks apply to ALL tasks (sequential and parallel). They're a general Claude Code feature, not team-agent-specific.

### 14.8. Accelerating Plan Creation with Team Agents

Team agents can speed up the **plan creation process itself** (not just execution) in two phases:

#### Phase 1: Parallel Research (before materialization)

When a plan involves multiple repositories or complex areas, teammates can research different areas simultaneously before the plan is materialized.

**When to activate (automatic):**
- Plan involves 2+ repositories (need to read AGENTS.md, understand architecture)
- Plan requires analyzing multiple independent modules or codebases
- Research would take significant time if done sequentially

**How it works:**
1. Lead spawns research teammates (1 per repo or major area)
2. Each teammate reads AGENTS.md, explores relevant code, identifies patterns and constraints
3. Teammates return structured findings to the lead
4. Lead synthesizes research into enriched context for the plan

**Result:** The plan is significantly more accurate because it is based on real codebase research rather than assumptions.

#### Phase 2: Parallel Task File Generation (after the Full format is chosen)

When generating a plan with 5+ user-defined task files, teammates can write task files simultaneously.

**How it works:**
1. Lead creates the plan skeleton: README.md, PROMPTS.md, PROGRESS.md, analysis_results/, and the single Final Review task file (`{N}.task_final_review.md`)
2. Lead spawns teammates (1 per 2-3 task files) to generate user-defined task files in parallel
3. Each teammate receives the plan context, and writes their assigned task files
4. Lead verifies all files, ensures consistency, and cleans up the team

**What the lead handles (always sequential):**
- README.md (must be created first — it's the plan index)
- PROMPTS.md, PROGRESS.md
- The mandatory Final Review task — it follows a fixed template
- Team agents metadata sections (depend on knowing all tasks)
- Final quality verification

**What teammates handle (in parallel):**
- Phase 1: Research of different repos/modules
- Phase 2: User-defined task files (N.task_*.md), 2-3 per teammate with no file overlap

**Fallback:** If team agents are unavailable, both phases execute sequentially as before. No impact on the final plan quality.

> **Note:** These optimizations are transparent to the user. They run `/dwp-create` as usual and the plan is created faster with richer context. The resulting plan is identical regardless of whether team agents were used during creation.

---
