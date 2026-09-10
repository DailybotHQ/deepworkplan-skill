# DeepWorkPlan Guide — Skills & Agents Integration

> Part of the DeepWorkPlan methodology guide. The routing index is
> [`GUIDE.md`](GUIDE.md); read only the guide files your flow names.

## 11. Skills & Agents Integration (MANDATORY)

When creating deep work plans, the plan generator **MUST** consult the project's available Skills and Agents to produce higher-quality, more consistent plans.

### Why This Matters

- Skills contain battle-tested, step-by-step procedures for common tasks
- Agents provide specialized validation checklists and review expertise
- Skills now have **`model` routing** (haiku/sonnet/opus) for cost-efficient execution
- Skills have **`allowed-tools`** restrictions for safer execution
- Agents have **`tools`/`permissionMode`** for controlled access
- Using skill invocation (`/skill-name`) leverages these features automatically

### Where to Find Skills & Agents

Before creating any plan, the generator **MUST** read:

1. **Skills catalog:** `.agents/docs/skills_agents_catalog.md`
   - Lists all available skills with names, tiers, models, file paths, and descriptions
2. **Individual skill files:** `.agents/skills/{skill-name}/SKILL.md`
   - Contains detailed step-by-step procedures, guardrails, and validation
   - Frontmatter includes `model`, `allowed-tools`, and other routing metadata
3. **Agent files:** `.agents/agents/{agent-name}.md`
   - Contains specialized checklists, workflows, and validation criteria
   - Frontmatter includes `tools`, `model`, and `permissionMode`

> `.claude/` and `.cursor/` are symlinks to `.agents/` — all three paths work.

### How to Integrate Skills into Task Files

When writing a task file (`N.task_*.md`), the plan generator **MUST**:

1. **Check if a relevant skill exists** for the task's objective
   - Example: Task is "Update project documentation" → use `/doc-update` skill
   - Example: Task is "Summarize research findings" → use `/research-summary` skill
   - Example: Task is "Create a cross-project plan" → use `/multi-project-plan` skill

2. **If a matching skill exists, instruct invocation in the task instructions:**

   ```markdown
   ## 1. Context

   **Complexity:** Tier {N} ({Light|Standard|Heavy})
   **Primary Skill:** `/{skill-name}` (model: {haiku|sonnet|opus})

   ## 3. Instructions

   **Invoke the skill:** `/{skill-name}`

   This skill will:
   - Use the model configured in its frontmatter (e.g., `model: sonnet`)
   - Restrict tools to only what it needs (e.g., `allowed-tools: Read, Write, Edit, Glob, Grep`)
   - Follow its built-in procedure automatically

   **Additional context for this specific task:**
   - [task-specific additions or overrides]
   - [plan-specific constraints]
   ```

3. **If no matching skill exists**, write instructions normally (as before)

4. **For validation steps, delegate to agents:**
   - Example: Task involves documentation → delegate to `doc-writer` agent
   - Example: Task involves research analysis → delegate to `researcher` agent
   - Example: Task involves multi-project coordination → delegate to `planner` agent

   ```markdown
   ## 5. Validation

   Standard validations:
   - [project-specific commands]

   Agent-based validation (delegated):
   - Delegate to `{agent-name}` agent for {specific concern}
     - The agent will use its configured `tools` (e.g., read-only) and `model`
     - It will follow its built-in checklist and report findings
   ```

5. **Always prefer skill invocation over ad-hoc instructions** when a skill covers
   the task's objective, even partially. The skill has been tested and refined;
   ad-hoc instructions have not.

### How to Reference Skills & Agents in Plan README

The plan's `README.md` should include a section listing which skills and agents are relevant, **including the model column** for execution cost visibility:

```markdown
## Skills & Agents Used in This Plan

| Task | Skill/Agent | Model | Purpose |
|------|-------------|-------|---------|
| Task 1 | `/doc-update` skill | haiku | Documentation update procedure |
| Task 3 | `/research-summary` skill | sonnet | Research summarization |
| Task 5 | `doc-writer` agent | sonnet | Documentation quality validation |
| Task 8 | `planner` agent | opus | Multi-project coordination review |
```

This gives the executor (and the user) visibility into:
- Which tasks will be fast/cheap (haiku) vs. expensive (opus)
- Total model usage across the plan
- Where optimization is possible

If no skills or agents are relevant to the plan, include the section with a note:

```markdown
## Skills & Agents Used in This Plan

No existing skills or agents are directly applicable to this plan's tasks.
Consider creating new skills if patterns emerge during execution.
```

### Execution Checklist Updates

Task files should reference skill invocation in their execution checklists:

```markdown
* [ ] 1. Read this task file fully and understand the goal and constraints
* [ ] 2. Invoke `/{skill-name}` skill (auto-routes to correct model and tools)
* [ ] 3. Apply task-specific additions listed in Instructions section
* [ ] 4. Run standard validations
* [ ] 5. Delegate to `{agent-name}` agent for quality check (if applicable)
* [ ] 6. Commit changes with conventional format
```

### Task-Local Skills Decisions (Output Direction)

Every task decides, **as it completes and while its evidence is in context**, whether its work produced:
- New patterns created → potential new skills/agents
- Changes to existing patterns → potential updates to existing skills/agents
- Skills generator system improvements needed

The disposition (`none` / `update` / `create` / `defer`) is recorded in the task's Completion & Log; real candidates go to `analysis_results/SKILLS_CANDIDATES.md` by stable ID, and warranted in-scope authoring happens inside that task before its gate (`execution.md` §6.1). The Final Review reconciles the ledger — it does not rediscover the plan.

This complements the existing input direction (using existing skills in plans).
The full cycle: Catalog → Plan (input) → Execution (task-local decisions) → Final Review (reconciliation) → Catalog (output)

### Keeping the Registry Updated

**CRITICAL:** The skills/agents catalog **MUST** be kept up to date.

- When a plan creates new skills or agents, update the catalog immediately
- When a skill or agent is deprecated, remove it from the catalog
- The catalog (`.agents/docs/skills_agents_catalog.md`) is the **SINGLE SOURCE OF TRUTH** for what's available
- Also update `.agents/README.md`'s quick reference tables when the catalog changes
- If the catalog is outdated, plans will reference non-existent procedures or miss available ones

---
