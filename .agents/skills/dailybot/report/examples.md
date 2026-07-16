# Report Examples

Side-by-side comparisons of weak and strong reports. Use these as a calibration reference.

> **About `--name` and `--metadata` in the rich examples below:** every example assumes the repo does **not** ship a `.dailybot/profile.json` — i.e. there is no pinned identity, so each call must pass `--name` explicitly and put `repo` / `agent_tool` / `agent_name` inline in `--metadata`. **If the repo does ship a `.dailybot/profile.json`, omit every flag the profile already sets** (see [`SKILL.md` § Step 4A "Pre-flight"](SKILL.md#step-4a--send-report-via-cli) and [`../shared/repo-profile.md`](../shared/repo-profile.md) for the full procedure). Don't ever copy these example flag lists wholesale into a repo with a pinned profile — it silently overrides the developer's pin.

---

## Plain Reports

### 1. Feature implementation

**Weak:** "3 files modified in app/followups/ — updated serializers and tasks"

**Strong:** "Refactored followup notifications — managers now receive their full platform profile (avatar, contact info) instead of just a name string, improving how manager data appears in reminders."

Why: Describes the change AND its user-facing impact. No file paths.

---

### 2. Bug fix

**Weak:** "fix: handle null timezone in user profile"

**Strong:** "Fixed a bug where users without a timezone set would see errors on their profile page."

Why: Describes the problem users experienced, not the code change.

---

### 3. Frontend change

**Weak:** "feat: add copy icon and click feedback to hero CLI pill — pushed to dev"

**Strong:** "Added copy-to-clipboard functionality to the homepage CLI demo with visual feedback when users click."

Why: No branch names. Describes what the user experiences.

---

### 4. Multiple commits

**Weak:** "2 commits — latest: fix: handle null timezone in user profile"

**Strong:** "Fixed a bug where users without a timezone set would see errors on their profile page."

Why: One sentence about the outcome. Commit count is irrelevant to the team.

---

### 5. Documentation

**Weak:** "1 file modified: docs/technical/ARCHITECTURE_OVERVIEW.md"

**Strong:** "Updated the architecture documentation to reflect the new notification service integration."

Why: Describes what changed and why, not which file was edited.

---

### 6. Testing

**Weak:** "Completed testing work"

**Strong:** "Added test coverage for the manager profile serializer — 15 cases covering edge cases and platform variations."

Why: Specific about what was tested and the scope of coverage.

---

### 7. Refactoring

**Weak:** "refactor: clean up auth middleware"

**Strong:** "Refactored the authentication middleware to centralize token validation — eliminates duplicated checks across 4 endpoints."

Why: Explains the purpose and impact of the refactor.

---

### 8. Dependency update

**Weak:** "3 commits — latest: chore: update dependencies"

**Strong:** "Updated project dependencies to latest stable versions, including security patches for the HTTP client."

Why: Mentions the reason the update matters.

---

### 9. Performance fix

**Weak:** "perf: optimize dashboard query"

**Strong:** "Optimized the dashboard loading query — page now loads in under 500ms instead of 3 seconds for large teams."

Why: Quantifies the improvement.

---

### 10. CI/CD configuration

**Weak:** "ci: add e2e test step to pipeline"

**Strong:** "Configured the CI pipeline for automated browser tests — PRs now get E2E test results before merge."

Why: Explains what the team gets out of it.

---

## Rich Reports (with structured data)

### 11. Major feature (milestone)

**Weak:**
```bash
dailybot agent update "Completed development work and all tests pass" \
  --name "cursor"
```

**Strong:**
```bash
dailybot agent update \
  "Built the notification preferences system — users can now configure which alerts they receive and through which channels (email, in-app, Slack)." \
  --name "cursor" \
  --milestone \
  --json-data '{"completed":["Preferences data model","REST API endpoints (CRUD)","Email channel integration","Slack channel integration","User settings UI","Test suite (32 cases)"],"in_progress":[],"blockers":[]}' \
  --metadata '{"repo":"my-web","branch":"feature/notifications","agent_tool":"cursor","agent_name":"cursor","model":"claude-sonnet-4-20250514"}'
```

Why: Describes what users get, lists all deliverables, marks as milestone.

---

### 12. Multi-step task (milestone)

**Weak:**
```bash
dailybot agent update "Completed a deep work plan with multiple tasks" \
  --name "codex" \
  --milestone
```

**Strong:**
```bash
dailybot agent update \
  "Completed the auth refactor — JWT tokens now work across all services with centralized middleware validation, eliminating per-service token handling." \
  --name "codex" \
  --milestone \
  --json-data '{"completed":["JWT middleware implementation","Token validation service","Session migration script","Integration tests (24 cases)","API documentation update"],"in_progress":[],"blockers":[]}' \
  --metadata '{"repo":"my-api","branch":"feature/auth","agent_tool":"codex","agent_name":"codex","model":"o3"}'
```

Why: Describes the outcome and lists specific deliverables. No plan names or task IDs.

---

### 13. Feature with blockers

**Weak:**
```bash
dailybot agent update "Working on deployment, having some issues" \
  --name "cursor"
```

**Strong:**
```bash
dailybot agent update \
  "Implemented the staging deployment pipeline — builds and tests are automated, but the final deploy step is blocked by a Docker image issue." \
  --name "cursor" \
  --json-data '{"completed":["Build automation","Test runner integration","Environment configuration"],"in_progress":["Deploy step automation"],"blockers":["Docker base image missing libpq-dev — needs infrastructure team to update"]}' \
  --metadata '{"repo":"my-api","branch":"feature/deploy","agent_tool":"cursor","agent_name":"cursor","model":"claude-sonnet-4-20250514"}'
```

Why: Clear about what's done, what's pending, and exactly what's blocking.

---

### 14. Deployment (milestone)

**Weak:**
```bash
dailybot agent update "Deployed to production" \
  --name "windsurf" \
  --milestone
```

**Strong:**
```bash
dailybot agent update \
  "Deployed the new billing system to production — subscription management is now fully automated with Stripe webhook handling." \
  --name "windsurf" \
  --milestone \
  --metadata '{"repo":"billing-service","branch":"main","agent_tool":"windsurf","agent_name":"windsurf","model":"claude-sonnet-4-20250514"}'
```

Why: Says what was deployed and what it means for the product.

---

### 15. Analysis (no milestone)

**Weak:**
```bash
dailybot agent update "Completed analysis" \
  --name "copilot"
```

**Strong:**
```bash
dailybot agent update \
  "Completed the API performance audit — identified 3 N+1 query issues and a missing database index that account for 80% of p95 latency. Documented findings with fix recommendations." \
  --name "copilot" \
  --json-data '{"completed":["Query analysis across 12 endpoints","N+1 detection and documentation","Missing index identification","Fix recommendation document"],"in_progress":[],"blockers":[]}' \
  --metadata '{"repo":"my-api","branch":"main","agent_tool":"copilot","agent_name":"copilot","model":"gpt-4o"}'
```

Why: Specific findings, quantified impact, clear deliverables — even though no code was written.

---

## The Standup Test — Quick Calibration

Before sending any report, ask: "Would this be worth saying in a real standup?"

| Report | Worth saying? |
|--------|:---:|
| "Implemented the notification preferences system" | Yes |
| "Fixed a typo in a test file" | No |
| "Deployed the new auth middleware to staging" | Yes |
| "Updated a lockfile" | No |
| "Built the user preferences API with full test coverage" | Yes |
| "Read some code and explored the codebase" | No |
| "Completed the 8-task auth refactor with JWT across all services" | Yes |
| "3 files modified" | No |
| "Drafted the Q3 product roadmap with prioritized initiatives" | Yes |
| "Had a conversation with no conclusions" | No |
