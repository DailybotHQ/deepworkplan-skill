# Install verification — the skills-CLI defense contract

Two CLI defects are known from round-1 benchmark evidence
(`troubleshooting.md` §2): an `@tag` pin can be display-only (the requested
tag printed while the latest bytes are delivered), and a parallel-mkdir race
can report "Done!"/exit 0 while placing no content. Until both are fixed
upstream, every install site in this pack (`onboard` Phase 7 and Phase 7a,
`upgrade` Phase 3) defends its own users. **Read this when — and only when —
a phase below performs or verifies a `skills add` install.**

Around every `skills add` call:

- **Pre-create the target** `.agents/skills/<name>/` first, and remove any
  empty earlier attempt (documented race workaround — the upstream defect is
  cited in `troubleshooting.md` §2).
- **Verify what landed:** the installed `SKILL.md` frontmatter `version:`
  equals the requested tag, and the installed directory is non-empty
  (`SKILL.md` present — not just the CLI's exit 0).
- **On mismatch, empty, or false success:** retry the identical command once
  after pre-creating the directory; if it still fails, fall back to the
  byte-exact manual install
  `git archive <tag> skills/deepworkplan | tar -x --strip-components=1 -C .agents/skills`
  and byte-check with `diff -rq` against a `git archive` export of the tag.
  Record the event and the fallback in the phase's report — never proceed
  silently on a mismatched or empty install.
