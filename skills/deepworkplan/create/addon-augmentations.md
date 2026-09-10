# DeepWorkPlan — Create: the Final Review's local review step and addon augmentations (read when composing the Final Review)

This file is read when composing the Final Review task (`SKILL.md` Step 4.4 item 3): the AI Diff Reviewer local review is a required part of the security pass since standard 2.3.0, and other installed addons may augment it. Detection rules and the exact augmentation text are verbatim from the main procedure; the never-block rule of `../addons/README.md` applies.

## `ai-diff-reviewer`

**Required local review — `ai-diff-reviewer` (baseline since 2.3.0).**
The Final Review's security pass includes a post-existing-checks local-review
step defined by the [`ai-diff-reviewer` addon](../addons/ai-diff-reviewer/SKILL.md).
Detection: `.agents/skills/ai-diff-reviewer/` present + an extension file at
one of the three recognized paths (in precedence order): `.review/extension.md`,
`.github/ai-diff-reviewer/extension.md`, or the back-compat
`.github/ai-pr-reviewer/extension.md`. When both are present: invoke the upstream skill's parent
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
findings are appended and reported but do not block. Degradation is honest,
never silent (addon SPEC §6.1, §7): when the vendored skill or the extension
file is absent, record a `local reviewer not installed` finding in
`SECURITY_REVIEW.md`, install the missing piece when the run is authorized to
write to the harness (`../onboard/addons.md` Phase 7a — pinned skill,
`generate-extension`) and then review, otherwise carry the finding into the
completion report; when a review that could start errors at invocation, warn
once, record it and continue — NEVER fail the task for either. Flow A needs
**no** CI provider secret — do NOT
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
