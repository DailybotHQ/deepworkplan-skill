# DeepWorkPlan — Create: addon augmentations of the Final Review (read only when an addon is installed)

This file is read **only** when the target repository has an installed addon that augments the Final Review's security pass (`SKILL.md` Step 4.4 item 3). Detection rules and the exact augmentation text are verbatim from the main procedure; the never-block rule of `../addons/README.md` applies.

## `ai-diff-reviewer`

**Addon augmentation — `ai-diff-reviewer` (opt-in, only when installed).**
When the target repo has installed the [`ai-diff-reviewer` addon](../addons/ai-diff-reviewer/SKILL.md) — detected via
`.agents/skills/ai-diff-reviewer/` present + an extension file at one of the
three recognized paths (in precedence order): `.review/extension.md`,
`.github/ai-diff-reviewer/extension.md`, or the back-compat
`.github/ai-pr-reviewer/extension.md` — the Final Review's security pass gains
an ADDITIONAL post-existing-checks step: invoke the upstream skill's parent
default flow ("Review my current branch" / `/ai-diff-reviewer`), capture the
verdict, findings table, per-finding bodies, notes, and recommendation, and
append them to `analysis_results/SECURITY_REVIEW.md` under a dedicated
`## AI Diff Reviewer local review` heading.   The upstream skill's `prompt.md`
is byte-identical to the CI Action's `prompts/default.md` at the same tag, so
when the same repo also runs the CI Action (Flow B), the local review shares
the same methodology and severity model via that prompt plus the extension
file; CI round 2+ may surface a shorter finding set under Iteration-Aware
Review (local stays a full pass — see addon SPEC §4.3). A `critical` finding
follows the existing security-pass contract
(blocks completion until fixed or explicitly accepted); `warning` / `info`
findings are appended and reported but do not block. The augmentation is
best-effort and conditional per the addon SPEC §7 (never-block rule): skip
the **local** review pass (warn once, NEVER fail the task) only when the
vendored skill is absent, detection fails (no extension file), or the local
review invocation errors. Flow A needs **no** CI provider secret — do NOT
treat an unset `CURSOR_API_KEY` (or other provider secret) as a reason to
skip the local security pass; that secret is Flow B CI / gate
messaging only. **Flow B optional companion (not a plan task):**
when the plan's PR has been pushed and CI has posted its review, the developer
MAY invoke the upstream `apply-review` sub-skill from within the same
`execute` session to walk through CI findings per-finding (apply / defer /
skip) with explicit consent — read-only by default, edits require per-finding
yes, never commits or pushes. This is surfaced as an available option during
`execute`; the addon MUST NOT insert an `apply-review` task file into any
plan (would violate the single-Final-Review rule).
