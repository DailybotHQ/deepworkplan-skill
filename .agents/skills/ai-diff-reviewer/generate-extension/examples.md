# Examples — condensed reference for `generate-extension`

Three condensed samples adapted from the shipped worked examples in
[`examples/prompts/`](https://github.com/DailybotHQ/ai-diff-reviewer/tree/main/examples/prompts).
Use these as **inspiration for the SHAPE and TONE** of an override
section — do NOT copy-paste the content verbatim into a real repo's
extension. The goal of `generate-extension` is to produce overrides
tied to the CURRENT repo's actual files and patterns, not to reuse
generic ones.

Full versions with usage instructions are in the linked source files.

---

## Sample A — Python / SQLAlchemy / FastAPI extension

Adapted from
[`examples/prompts/python-strict.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/examples/prompts/python-strict.md).

```markdown
## Severity overrides for this codebase

- **Always `critical`:**
  - `pickle.loads`, `yaml.load` without `SafeLoader`, or `subprocess`
    with `shell=True` on any input traced back to a request (see
    `src/api/**` handlers).
  - Bare `except:` in `src/services/` — silently swallows
    `KeyboardInterrupt`/`SystemExit` and hides real bugs.
  - Change to `src/auth/` or `src/crypto/` without a matching test in
    the same PR.
  - Money/currency computation using `float`. All amounts in
    `src/billing/` must use `decimal.Decimal`.

- **Escalate to `warning`:**
  - Missing type hints on public functions exported from `src/api/`
    or `src/services/`.
  - Mutable default arguments (`def f(x=[]):`).
  - Sync blocking call inside an `async def` (`requests.get`, `time.sleep`).

- **De-escalate to `info`:**
  - Style choices already caught by `ruff` + `black` (their CI job
    fails first — the reviewer shouldn't duplicate).

## Don't comment on

- Missing docstrings — the codebase is intentionally undocstringed.
- Formatting inside migrations in `alembic/versions/` — auto-generated.

## Repo-specific conventions

- All DB access goes through `src/db/session.py` — inline
  `create_engine` calls are `warning`.
- All external HTTP calls use `src/http/client.py` with the shared
  retry policy — raw `httpx.get` is `warning`.
```

---

## Sample B — Security-focused extension (OWASP-anchored)

Adapted from
[`examples/prompts/security-focused.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/examples/prompts/security-focused.md).

```markdown
## Severity overrides for this codebase (security focus)

Anchor every finding to the OWASP Top-10 category it belongs to.

- **Always `critical`:**
  - **A01 Broken Access Control** — handler in `src/api/**` reading or
    writing user data without an explicit `require_role()` / tenant
    check.
  - **A02 Cryptographic Failures** — `md5`/`sha1` used for password
    hashing (must be `argon2`/`bcrypt` per RFC-007), missing
    HTTPS enforcement in `src/config/prod.py`, raw AES without
    GCM/HMAC.
  - **A03 Injection** — SQL/NoSQL/LDAP/OS-command built via string
    concatenation with user input. Parameterized queries only.
  - **A05 Security Misconfiguration** — `debug=True` in a deploy
    config file, `CORS *` on a non-public API.

- **Escalate to `warning`:**
  - Auth token stored in `localStorage`/`sessionStorage`.
  - Missing rate-limit decorator on any endpoint under
    `src/api/public/`.

## Don't comment on

- Third-party vendor snippets in `src/vendor/` — locked, updated only
  via dependency bumps.

## Repo-specific conventions

- Every request handler ends with an audit-log emission via
  `src/audit/log.py`. Missing emission on a data-mutating handler is
  `critical`.
- All secrets are loaded via `src/config/secrets.py::load()`. Direct
  `os.environ["…"]` reads outside that module are `warning`.
```

---

## Sample C — TypeScript / React extension

Adapted from
[`examples/prompts/typescript-strict.md`](https://github.com/DailybotHQ/ai-diff-reviewer/blob/main/examples/prompts/typescript-strict.md).

```markdown
## Severity overrides for this codebase (TS + React)

- **Always `critical`:**
  - `any` on a public API boundary (props, return types, exported
    function signatures). `unknown` is fine; `any` silently opts out
    of type checking.
  - `dangerouslySetInnerHTML` fed by anything other than a static
    string constant.
  - `useEffect` with a missing or intentionally-elided dependency
    array (unless commented AND justified in the diff description).
  - `localStorage`/`sessionStorage` for auth tokens or secrets — use
    `apps/frontend/src/auth/tokenStore.ts` (HttpOnly cookie).
  - Direct DOM mutation inside a React component
    (`document.getElement…` for write, not read).

- **Escalate to `warning`:**
  - Non-null assertion `!` on values that could legitimately be
    `null` (favor optional chaining `?.` or an explicit guard).
  - Missing `AbortController` on `fetch()` inside a React component
    (per RFC-014 on Suspense boundaries).
  - `React.memo` around a component that has zero measurable
    render-cost overhead (memoization is not free).

## Don't comment on

- Formatting — `prettier` runs on save + in CI.
- Import ordering — `eslint-plugin-import` enforces it.

## Repo-specific conventions

- All API calls go through `apps/frontend/src/api/client.ts` — raw
  `fetch()` in a component is `warning`.
- All forms use `apps/frontend/src/forms/useForm.ts`. Hand-rolled
  `useState` for form state is `warning`.
```

---

## Anti-patterns — what NOT to produce

These outputs would fail the Step 4 quality gate. If your generated
extension resembles any of them, go back to Discovery.

### ❌ Generic (could belong to any repo)

```markdown
- Avoid magic numbers.
- Use meaningful variable names.
- Follow SOLID principles.
- Prefer composition over inheritance.
```

Every one of these could apply to any codebase. There's no signal in
the file — the reviewer already has these general priors from the
base prompt.

### ❌ Category-only (no code anchor)

```markdown
- OWASP A01 findings are critical.
- OWASP A03 findings are critical.
- OWASP A05 findings are critical.
```

Naming the category without pointing at WHERE the pattern lives in
this repo forces the reviewer to guess. Cite files.

### ❌ Prohibits things the linter already catches

```markdown
- No `console.log` in production code.
- No unused imports.
- Prefer const over let.
```

If ESLint/ruff/etc. already catches these on `main`, the reviewer
duplicating the check is noise. De-escalate them to `info` or omit.
