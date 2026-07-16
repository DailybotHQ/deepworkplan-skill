# Writing Guide — How to Compose Reports Teams Value

Every report you send appears in Dailybot alongside updates from human team members. Your report should be indistinguishable from a human's standup update.

## The Human-First Principle

The developer who works with you directed the effort, made the decisions, and is accountable for the result. Your report reflects their accomplishment, not yours.

**Golden rule:** The reader should never be able to tell whether a human or an agent wrote the report.

## Report Structure

Every report follows the same pattern:

```
[What was accomplished] — [why it matters or what it enables].
```

Lead with the outcome, then connect it to impact. One to three sentences maximum.

## Sentence Construction

### Action verbs by work type

| Work type | Strong verbs |
|-----------|-------------|
| New feature | Built, Implemented, Added, Shipped, Created |
| Bug fix | Fixed, Resolved, Corrected, Patched |
| Refactor | Refactored, Redesigned, Restructured, Simplified, Migrated |
| Tests | Added test coverage for, Tested, Validated |
| Documentation | Documented, Wrote documentation for |
| Performance | Optimized, Improved, Reduced latency for, Accelerated |
| Configuration | Configured, Set up, Enabled, Integrated |
| Analysis | Analyzed, Investigated, Identified, Mapped out |
| Deployment | Deployed, Released, Shipped, Launched |

### What to emphasize

**Emphasize:**
- User-facing outcomes ("users can now...")
- Business value ("prevents duplicate charges...")
- Scope of the work ("12 endpoints", "full test suite with 32 cases")
- What changed from the user's perspective

**Do not emphasize:**
- Number of files changed
- Lines of code added or removed
- Internal implementation details
- Which libraries or tools were used (unless that IS the deliverable)

## Templates by Work Type

### Feature

```
Built/Implemented [what] — [what it enables for users or the team].
```

"Implemented notification preferences — users can now choose which alerts they receive via email vs. in-app."

### Bug fix

```
Fixed [user-facing problem] — [brief cause or what was going wrong].
```

"Fixed an issue where team members in different timezones saw incorrect standup deadlines."

### Refactor

```
Refactored [what] to [improvement] — [benefit or what this enables].
```

"Refactored the authentication flow to use JWT tokens — improves session management and enables cross-service auth."

### Test coverage

```
Added test coverage for [what] — [scope or what scenarios are now covered].
```

"Added test coverage for the webhook retry system — 12 cases covering timeout, auth failure, and payload validation."

### Documentation

```
Documented [topic] — [what readers can now find or understand].
```

"Documented the API rate limiting system — configuration options, default limits, and troubleshooting steps."

### Performance

```
Optimized [what] — [measurable improvement or user-facing benefit].
```

"Optimized the dashboard query — page now loads in under 500ms instead of 3 seconds for large teams."

### Deployment

```
Deployed [what] to [where] — [what is now live or available].
```

"Deployed the new billing system to production — subscription management is now fully automated."

### Analysis or research

```
Completed [what] — [key findings or what decisions it enables].
```

"Completed the API performance audit — identified 3 N+1 queries and a missing index that account for 80% of latency."

### Multiple related changes

```
[Summary of the overall effort]: [most important item]. Also [secondary items].
```

"Made several improvements to the standup flow: added timezone-aware scheduling and improved reminder formatting. Also fixed a layout issue on mobile."

## Forbidden Patterns

Never include these in a report message:

| Pattern | Example | Why it's wrong |
|---------|---------|----------------|
| File paths | `app/services/auth.py` | Nobody reads file paths in a standup |
| Git statistics | `3 files changed, +127 -12` | Meaningless without context |
| Raw commit messages | `feat(scope): description` | Commit syntax is for git, not humans |
| Branch names | `pushed to dev`, `merged to main` | Internal workflow details |
| Agent attribution | `Agent completed...`, `I implemented...` | Violates the human-first principle |
| Deferring to git | `see git log for details` | Reports must be self-contained |
| Jargon without context | `resolved hydration mismatch` | Most team members won't understand |
| Plan or task IDs | `PLAN_auth_refactor`, `task-3` | Internal identifiers, not outcomes |
| Non-English text | `Se corrigió un error` | All reports must be in English |
| Vague fallbacks | `Updated code`, `Made changes` | If you can't be specific, don't report |

## Structured Data Guidelines

Use `--json-data` when a report covers three or more distinct deliverables.

### Writing good items

**Good** — concise, outcome-oriented:
- "JWT authentication endpoint"
- "Token refresh with expiry handling"
- "Integration tests (24 cases)"
- "API documentation update"

**Bad** — vague or overly technical:
- "Updated files"
- "Refactored code"
- "app/auth/middleware/jwt_validator.py"
- "Fixed the thing"

### When structured data helps

- Multi-deliverable features (3+ distinct pieces)
- Task or plan completions with multiple outputs
- When the individual items add clarity beyond the message alone

### When to skip structured data

- Single bug fix (the message says everything)
- One-item reports (structured data adds noise)
- When every item would just repeat the message differently

## Rate Limiting

Quality over quantity. One rich, specific report is worth more than ten shallow ones.

- If you completed related changes, aggregate into one report
- Aim for roughly 10 meaningful reports per day at most, not 100
- If the last report was less than 30 minutes ago, consider waiting and combining
- Back-to-back reports about the same feature should always be merged

## Co-Authors

Do not add co-authors on your own initiative. The Dailybot backend automatically credits the authenticated developer.

Only use `--co-authors` when the developer explicitly says to credit someone else. The flag accepts email addresses or user UUIDs. Never guess email addresses.

For multiple co-authors, either repeat the flag or use a comma-separated list:

```bash
--co-authors alice@co.com --co-authors bob@co.com
--co-authors "alice@co.com,bob@co.com"
```
