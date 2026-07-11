# Reasoning template — the "Agent Prompt Guide" block

Every `DESIGN.md` ends with a short **Agent Prompt Guide**: a "how to use this file"
block that tells a downstream coding agent to follow the design system. Adapt the
wording to the repo, keep it to a few lines, and reference the repo's real token
names.

---

## Drop-in block (adapt the bracketed parts)

```markdown
## Agent prompt guide

**For coding agents working in this repo:** this `DESIGN.md` is the source of truth
for every interface surface it covers (visual UI, CLI output, outbound messages).
Before generating or editing any user-facing output:

1. **Use the named tokens** in this file (colors, type, spacing, radius — or
   semantic CLI styles and message conventions) — do not introduce ad-hoc values
   outside it.
2. **Respect roles** — pick a color/style by its *role* (e.g. `color.accent` for
   primary actions, the `success` style for completed operations), not by
   eyeballing a value.
3. **Keep integrity** — text pairings must meet the contrast targets in Do's &
   Don'ts; CLI output must stay legible when piped or colorless; rich messages
   keep their plain-text fallback.
4. **Match the documented patterns** — reuse the Button/Input/Card patterns, the
   display helpers (`print_success`, panels, spinners), or the message envelopes
   and voice rules, with their states.
5. **When something isn't covered**, choose the option most consistent with the
   conventions here and note the gap rather than inventing an unrelated style.

Suggested instruction to paste into an agent prompt:
> "Follow `DESIGN.md` strictly. Build [the output] using its tokens, roles, and
>  documented patterns; keep the integrity rules (contrast / degradation /
>  fallbacks) intact."
```

---

## Notes

- Reference the repo's **actual** token/helper names (e.g. `color.accent`,
  `--color-ink`, `oxblood`, `print_success`, `mrkdwn`) so the guidance is
  concrete, not generic — covering every profile present in the file.
- If the repo installed a `/design-system` delegator, you MAY mention it here
  ("run `/design-system` to refresh this file after design changes").
- Keep this block short — its job is to point agents at the rest of the file, not to
  repeat it.
