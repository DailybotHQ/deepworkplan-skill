---
name: dailybot-custom-form-template
description: STARTER TEMPLATE — do not consume this file in place. Copy it to .agents/skills/dailybot-custom/<your-skill-name>/SKILL.md in your own repo, then customize. This is the bootstrap skeleton for authoring a per-form custom skill that the universal dailybot-forms resolver will load from .dailybot/profile.json.
version: "3.10.3"
documentation_url: https://www.dailybot.com/skill.md
user-invocable: false
allowed-tools: Bash, Read, Grep, Glob
---

# Custom Form Skill — Starter Template

> [!IMPORTANT]
> **Do not use this file in place.** It lives inside the universal Dailybot skill pack (`.agents/skills/dailybot/`) only as a reference. **Copy it** to your own repo as:
>
> ```text
> .agents/skills/dailybot-custom/<your-skill-name>/SKILL.md
> ```
>
> The universal Dailybot skill pack is **managed by `skills-lock.json`** and rewritten on every upgrade. Anything you place inside `.agents/skills/dailybot/` will be overwritten. Anything under `.agents/skills/dailybot-custom/` is **customer-owned** and the installer never touches it. That separation is the entire point — keep the line clean.

---

## When the universal skill loads this custom file

The universal `dailybot-forms` skill resolves a per-form custom skill by reading `.dailybot/profile.json` in the repo root and looking up the current form under `vars.custom_form_skills`:

```json
{
  "vars": {
    "custom_form_skills": {
      "by_uuid": {
        "<form-uuid-in-this-environment>": ".agents/skills/dailybot-custom/<your-skill-name>"
      },
      "by_slug": {
        "<form-slug-stable-across-environments>": ".agents/skills/dailybot-custom/<your-skill-name>"
      }
    }
  }
}
```

When either lookup matches, the universal skill stops and loads this file. Everything below this point is your custom workflow logic — write it for the specific form this skill targets.

---

## 1 — Auth

User-scoped Bearer token (`dailybot login`). This is identical to the universal forms skill — see [`../../shared/auth.md`](../../shared/auth.md). If the developer doesn't have a session, fall back to the universal skill's auth steps; don't reinvent them here.

---

## 2 — State machine reference (fill in)

Document the workflow this form uses. Read it from `dailybot form get <form_uuid> --json` once and pin the canonical version here so future-you doesn't have to re-derive it.

```
draft  → review     "Send for review"
review → released   "Mark released"
review → draft      "Back to draft"
released → (final, sticky unless allow_reopen_from_final_state=true)
```

Keep this in sync with the server-side workflow. The server is the source of truth for `allowed_transitions`; this section is documentation only.

---

## 3 — Per-state required fields

Some forms expect specific questions to be answered before moving forward. Document the contract per state:

| State | Required answers before transitioning out |
|-------|-------------------------------------------|
| `draft`    | service name, release notes |
| `review`   | reviewer list, regression-test status |
| `released` | release URL, channel-routing target |

The custom skill should validate these locally **before** invoking the CLI's `transition` command, so the developer sees a clear "you need to fill X first" instead of a server-side audience error.

---

## 4 — Default values & autofill

If the form has fields the agent can fill from session context, document the source mapping:

| Form question | Source |
|---------------|--------|
| `service_name` | repo name from `.dailybot/profile.json` → `default_metadata.repo` |
| `released_by`  | logged-in user from `dailybot status --auth --json` |
| `branch`       | `git rev-parse --abbrev-ref HEAD` |

Always confirm the autofilled values with the developer before submitting.

---

## 5 — Channel routing reminders

If a transition triggers a side-effect (post to Slack, page on-call, email stakeholders), document it here so the agent surfaces the side-effect during the confirmation prompt:

> "Moving this response to `released` will notify `#releases` in Slack and email the stakeholders list. Confirm? (yes / cancel)"

The server owns the actual notifications — this section is about what to tell the developer in the confirmation prompt.

---

## 6 — Recovery flows

What does the agent do when:

- The latest response is in a final state but the developer says "I need to re-open" → guide them to a new response (or, if they own the form, suggest `allow_reopen_from_final_state=true`).
- The developer's audience does not include the requested transition (`form_response_change_state_forbidden`) → tell them who can do it; do not retry.
- A required field is missing → list the gaps, ask the developer to fill them, then re-attempt the transition.

---

## 7 — Reference implementation

A complete reference implementation of this template lives as a custom skill at `.agents/skills/dailybot-custom/<form-slug>/SKILL.md` in the consuming repo (a customer- or team-owned namespace, separate from this skill pack). Such a skill demonstrates per-state validation, autofill from repo metadata, and channel-routing reminders end-to-end.

---

## 8 — Keep customizations under `dailybot-custom/`

| OK | Not OK |
|----|--------|
| `.agents/skills/dailybot-custom/coderelease-form/SKILL.md` | `.agents/skills/dailybot/forms/coderelease-form/SKILL.md` |
| `.agents/skills/dailybot-custom/onboarding-survey/SKILL.md` | Editing the universal `.agents/skills/dailybot/forms/SKILL.md` directly |
| Registering your skill in `.dailybot/profile.json` → `vars.custom_form_skills` | Hardcoding form UUIDs into the universal skill |

If you find yourself wanting to edit the universal `dailybot-forms` skill to handle one specific form, stop and author a custom skill here instead. That's the contract the resolver exists to make safe.
