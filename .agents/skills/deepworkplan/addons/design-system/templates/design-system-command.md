# Template — `/design-system` delegator command (reasoning aid)

This is the **delegator command** the design-system addon **MAY** install into the
target repo's `.agents/commands/design-system.md` **only when the addon is
accepted** during `onboard` Phase 7b (or when the addon is run directly) **and** the
developer wants a one-command way to refresh `DESIGN.md` later. It is a **thin
delegator**: it carries no logic of its own — it routes to the
`deepworkplan-addon-design-system` addon, which holds the real flow.

Installing this command is **optional** (`SPEC.md` §9). Fill the placeholders by
reasoning about the target repo (its real design source and accessibility rules);
do not copy verbatim. Decline the addon → do **not** install this command.

```markdown
---
name: design-system
description: Create or refresh this repo's DESIGN.md (design tokens + rules for AI agents; at docs/DESIGN.md, indexed from AGENTS.md) via the DeepWorkPlan design-system addon.
---

# /design-system

Create or refresh this repository's `DESIGN.md` (at `docs/DESIGN.md`, indexed from
`AGENTS.md`) so coding agents generate interface output — visual UI, terminal
output, or outbound messages — consistent with this repo's **own** conventions.
This command is a **thin delegator** to the DeepWorkPlan
`deepworkplan-addon-design-system` addon — it does not contain the logic itself.

## Steps

1. Invoke the `deepworkplan-addon-design-system` addon (via
   `/deepworkplan-addon-design-system` or by reading the addon's `SKILL.md`).
2. Follow the addon's flow: locate this repo's real design source per profile
   (<e.g. CSS custom properties in `src/styles/global.css` + a Tailwind `@theme`
   block; or the CLI display module; or the message-composition helpers>), reason
   out each accepted profile's canonical sections of `DESIGN.md` from that
   source, and write or **reconcile** `DESIGN.md` at its location
   (`docs/DESIGN.md` for a repo with a `docs/` tree; root otherwise), ensuring
   `AGENTS.md` references it.
3. Run the addon's validation step (sections present per accepted profile, values
   traceable to the real source, per-profile integrity — WCAG AA contrast /
   degradation rules / plain-text fallbacks — and token references resolve).

## Notes

- Profiles in this repo: <fill in — e.g. visual-ui / cli-output / conversational>.
- Design source for this repo: <fill in — e.g. Tailwind config / CSS vars / token file / CLI display module / message helpers>.
- Integrity rules to enforce: <fill in — e.g. WCAG AA + approved/forbidden text colors; NO_COLOR degradation; plain-text fallbacks>.
- Reason about the real tokens — never paste a third-party brand's `DESIGN.md`.
- Reconcile an existing `DESIGN.md`; ask before any destructive change.
```
