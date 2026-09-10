# Preset — SvelteKit

> Reasoning aid, not a template. Verify against the live repo; detected reality
> wins. Capture the **real** validation command, not the example below.

## Signals that identify this stack

- `@sveltejs/kit` and `svelte` in `package.json`, a `svelte.config.js`, and a
  `vite.config.js`/`vite.config.ts` (SvelteKit is Vite-based).
- File-based routing under `src/routes/`: `+page.svelte` (UI), `+page.ts`
  (universal `load`), `+page.server.ts` (server `load` + form `actions`),
  `+layout.svelte`/`+layout.ts`, and `+server.ts` (standalone API endpoints with
  `GET`/`POST`/… handlers).
- `src/lib/` (the `$lib` alias), `src/app.html`, `src/hooks.server.ts` /
  `src/hooks.client.ts`, and `src/app.d.ts` (the `App` namespace types).
- The configured **adapter** in `svelte.config.js`: `adapter-auto`,
  `adapter-node`, `adapter-static`, `adapter-cloudflare`, `adapter-vercel` —
  it decides SSR vs prerender and the deploy target.
- Package manager from the lockfile: `pnpm-lock.yaml` → pnpm, `yarn.lock` →
  yarn, `package-lock.json` → npm. **Infer from the lockfile present.**

## What to look for in recon

- The **real** `package.json` scripts: `dev`, `build` (`vite build`),
  `preview`, `check` (`svelte-kit sync && svelte-check`), `lint` (`eslint` +
  often `prettier --check`), and the test command. Capture them verbatim.
- Type-checking is `svelte-check` (not bare `tsc`) — it understands `.svelte`
  files; the script is usually `check` / `check:watch`.
- Test convention: unit/component via **Vitest** (`vitest.config` /
  `vite.config` test block) with `@testing-library/svelte`; end-to-end via
  **Playwright** (`playwright.config.ts`, `tests/`). Note `*.test.ts` /
  `*.spec.ts` naming.
- The `load`/`actions` model: which routes use server vs universal loads, form
  actions, and `+server.ts` endpoints; where env/secrets live (`$env/static/*`,
  `$env/dynamic/*`, `.env`).
- Svelte version (4 vs 5 runes) — it changes component/reactivity conventions.

## Stack-specific skills/agents/commands to generate

- Skills: `route` (`+page.svelte` + `load` + optional `+page.server.ts`
  actions), `endpoint` (`+server.ts` with typed request handlers + test),
  `component` (`$lib` component + test), `load-function` (server/universal load
  + invalidation), optionally `form-action`.
- Agents: baseline + a `frontend-reviewer` persona aware of the server-vs-
  universal `load` boundary, progressive enhancement, and the adapter's SSR/
  prerender constraints.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — routing tree, `load` model (server vs universal), form
  actions, `+server.ts` endpoints, hooks, the adapter and SSR/prerender story.
- `STANDARDS.md` — component conventions, `$lib` boundaries, Svelte 4 vs 5
  (runes) idioms, props/typing.
- `TESTING_GUIDE.md` — Vitest + `@testing-library/svelte` patterns, Playwright
  e2e flow, the real `*.test.ts`/`*.spec.ts` pattern, plus `svelte-check` as a
  gate.
- `PERFORMANCE.md` — prerender vs SSR per route, the adapter target, asset/
  bundle budgets.

## Typical validation command (FIND the real one)

Commonly `pnpm run lint && pnpm run check && pnpm test && pnpm run build`
(or npm/yarn), where `check` is `svelte-check` and `build` is `vite build`.
**Do not assume the package manager or script names** — read `package.json`,
`svelte.config.js`, and CI, and capture the exact commands.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; the target repo's version may differ, so re-verify.

### 1. Full commands
- Tests: `pnpm vitest run` (or `pnpm test`; some repos split `test:unit` / `test:e2e`), from the repo root; e2e: `pnpm playwright test`.
- Static: `pnpm lint` (`eslint` + often `prettier --check`), `pnpm check` (`svelte-kit sync && svelte-check`), `pnpm build` (`vite build`).

### 2. Scoped invocation
**Vitest** (reference run — vitest 5.0.0, contributor environment):
`vitest run <file>` selects exactly that file (`Test Files 1 passed`); `vitest run <dir>` selects the directory; `vitest run -t "<name>"` filters by test name; `vitest run --project <name>` selects a workspace project. **Evidence of a correct run:** the `Test Files N passed (N)` line — check `N` is what you expected.
**Zero-selection behavior (verified):** a path filter that matches nothing prints `No test files found` and exits **1** (detectable); a `-t` name filter that matches nothing exits **0** with every test *skipped* (`Test Files 8 skipped`) — a silent empty run. Never accept `-t` without confirming a non-zero passed count.

**Playwright** (flags verified against `@playwright/test@1.63 test --help`): `playwright test <file>`, `-g "<title>"`, `--project <name>`, `--only-changed [ref]` (impact via git). `No tests found` is reported when a filter matches nothing — confirm the exit code in the target repo before trusting it in a gate.

### 3. Scoped static checks
- **ESLint / Prettier** (example): `eslint <path>`, `prettier --check <path>` scope natively.
- **`svelte-check`**: project-wide (it understands `.svelte` and reads the project config); `svelte-check --threshold error` narrows severity, not paths. Type-check is **project-wide by design**: `tsc --noEmit` reads `tsconfig.json`; `tsc <file>` ignores the project config and is *not* a sound scoped check. Do not fabricate a per-file variant — a single project-wide run is the real (and usually cheap) option.

### 4. Source-to-test mapping
Co-located `*.test.ts` next to `+page.svelte` / `+server.ts` / components, or `src/**/__tests__/`; `src/lib/` utilities with sibling tests; e2e under `tests/` (`*.spec.ts`, Playwright).

### 5. Affected consumers
`vitest run --changed <ref>`. **Blind spots:** `+layout.svelte` / `+layout.server.ts` (affects every child route with no import edge), `hooks.server.ts`, `svelte.config.js`, `vite.config.*`, `$env` usage, `.env*`. A change under `src/routes/(group)/+layout*` affects the whole group — run that group's tests or the full suite.

### 6. Escalation and fallback
Shared/core: `src/lib/` (`$lib`), `src/hooks.*`, top-level layouts, `src/params/`. Always full run: `svelte.config.js`, `vite.config.*`, `vitest.config.*`, `tsconfig.json`, `package.json`/lockfile, ESLint/Prettier config, `.env*`. **Fallback:** `pnpm lint && pnpm check && pnpm vitest run` (+ `pnpm build`).

### 7. Layers and posture
Unit (Vitest) for `$lib` and load functions — fast base; component tests (`@testing-library/svelte`); integration for `+server.ts` endpoints with real load/form actions; Playwright for a few flows. Unit-first; no ratio quota.

### 8. Zero-selection behavior
See §2 (Vitest path miss → exit 1; `-t` miss → exit 0 skipped).
