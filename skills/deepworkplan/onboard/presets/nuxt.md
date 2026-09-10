# Preset — Nuxt (Vue)

> Reasoning aid, not a template. Verify against the live repo; detected reality
> wins. Capture the **real** validation command, not the example below.

## Signals that identify this stack

- `nuxt` in `package.json` `dependencies` and a `nuxt.config.ts` at the repo
  root (Nuxt 3+; Vue 3 + Vite + the **Nitro** server engine under the hood).
- An `app.vue` entrypoint; file-based routing under `pages/` (with `[id].vue`
  dynamic segments and `[...slug].vue` catch-alls) and `layouts/`.
- Server layer under `server/`: `server/api/*` (Nitro route handlers, e.g.
  `server/api/users.get.ts`), `server/routes/`, `server/middleware/`,
  `server/utils/`.
- Auto-imported `composables/`, `components/`, `utils/`, and `stores/` (Pinia
  via `@pinia/nuxt`); `plugins/`, `middleware/` (route middleware),
  `assets/`/`public/`.
- Package manager from the lockfile: `pnpm-lock.yaml` → pnpm, `yarn.lock` →
  yarn, `package-lock.json` → npm. **Infer from the lockfile present.**

## What to look for in recon

- The **real** `package.json` scripts: `dev`, `build` (`nuxt build`),
  `generate` (`nuxt generate`, for static), `preview`, `typecheck`
  (`nuxi typecheck` / `nuxt typecheck`), `lint` (`eslint`, often via
  `@nuxt/eslint`), and the test command. Capture them verbatim.
- Test convention: **Vitest** with **`@nuxt/test-utils`** (the official Nuxt
  test harness — `defineVitestConfig`, `mountSuspended`, `setup` for e2e). Note
  `*.test.ts`/`*.spec.ts` naming, and whether component vs Nuxt-runtime tests
  are split.
- Rendering mode in `nuxt.config.ts`: universal SSR (default), SSG
  (`nuxt generate` / `nitro.prerender`), SPA (`ssr: false`), or hybrid
  per-route `routeRules` — this shapes `PERFORMANCE.md` and the deploy target.
- Data fetching (`useFetch`, `useAsyncData`, `$fetch`), `runtimeConfig` and
  where **secrets** live (server-only `runtimeConfig` vs `public`, `.env`,
  `NUXT_*` env vars — the boundary matters).
- Modules enabled in `nuxt.config.ts` (`@nuxt/content`, `@pinia/nuxt`,
  `@nuxtjs/i18n`, etc.) — they add conventions and directories.

## Stack-specific skills/agents/commands to generate

- Skills: `page`/`route` (`pages/*.vue` + `definePageMeta` + data fetching),
  `server-route` (`server/api/*` Nitro handler + test), `composable`
  (auto-imported composition fn), `component` (auto-imported SFC + test),
  optionally `store-module` (Pinia) and `route-middleware`.
- Agents: baseline + a `frontend-reviewer` persona aware of auto-imports, the
  server-vs-client boundary, and the `runtimeConfig` public/private split.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — pages/layouts routing, the Nitro `server/api` layer,
  composables and auto-imports, data fetching, rendering mode and `routeRules`.
- `STANDARDS.md` — SFC + Composition API conventions, auto-import expectations,
  composable naming (`useX`), props/events typing.
- `TESTING_GUIDE.md` — Vitest + `@nuxt/test-utils` patterns (`mountSuspended`,
  runtime vs e2e setup), the real `*.test.ts`/`*.spec.ts` pattern, coverage
  target.
- `PERFORMANCE.md` — SSR vs SSG vs hybrid, payload/hydration cost, the deploy
  preset/target, asset budgets.

## Typical validation command (FIND the real one)

Commonly `pnpm run lint && pnpm run typecheck && pnpm test && pnpm run build`
(or npm/yarn), where typecheck is `nuxi typecheck` and build is `nuxt build`.
**Do not assume the package manager or script names** — read `package.json`,
`nuxt.config.ts`, and CI, and capture the exact commands.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; the target repo's version may differ, so re-verify.

### 1. Full commands
- Tests: `pnpm vitest run` (or `pnpm test`) with `@nuxt/test-utils` (`defineVitestConfig`); e2e via `@nuxt/test-utils/e2e` `setup()` or Playwright.
- Static: `pnpm lint` (`eslint`, often `@nuxt/eslint`), `pnpm nuxi typecheck` (or `nuxt typecheck`), `pnpm nuxt build`.

### 2. Scoped invocation
**Vitest** (reference run — vitest 5.0.0, contributor environment):
`vitest run <file>` selects exactly that file (`Test Files 1 passed`); `vitest run <dir>` selects the directory; `vitest run -t "<name>"` filters by test name; `vitest run --project <name>` selects a workspace project. **Evidence of a correct run:** the `Test Files N passed (N)` line — check `N` is what you expected.
**Zero-selection behavior (verified):** a path filter that matches nothing prints `No test files found` and exits **1** (detectable); a `-t` name filter that matches nothing exits **0** with every test *skipped* (`Test Files 8 skipped`) — a silent empty run. Never accept `-t` without confirming a non-zero passed count.

**Playwright** (flags verified against `@playwright/test@1.63 test --help`): `playwright test <file>`, `-g "<title>"`, `--project <name>`, `--only-changed [ref]` (impact via git). `No tests found` is reported when a filter matches nothing — confirm the exit code in the target repo before trusting it in a gate.

`@nuxt/test-utils` e2e suites boot a Nuxt server per `describe` block — scope them by file, and expect them to be slower than unit files.

### 3. Scoped static checks
- **ESLint** (example): `eslint <path>` scopes natively.
- **`nuxi typecheck`**: project-wide (generates types, then `vue-tsc --noEmit`). Type-check is **project-wide by design**: `tsc --noEmit` reads `tsconfig.json`; `tsc <file>` ignores the project config and is *not* a sound scoped check. Do not fabricate a per-file variant — a single project-wide run is the real (and usually cheap) option.

### 4. Source-to-test mapping
Co-located `*.spec.ts` / `*.test.ts` next to components/composables, or `tests/` (`tests/unit/`, `tests/e2e/`) mirroring `components/`, `composables/`, `server/api/`. `server/api/*` handlers are unit-testable with `h3` utilities or covered by e2e.

### 5. Affected consumers
`vitest run --changed <ref>`. **Blind spots:** Nuxt auto-imports (a composable can be used with no import statement — the import graph misses consumers), `nuxt.config.*` modules/runtimeConfig, `server/middleware/`, layouts, `app.vue`, `.env*`. For auto-imported composables, grep usages by name to find consumers or run the full suite.

### 6. Escalation and fallback
Shared/core: `composables/`, `utils/`, `stores/`, `layouts/`, `server/utils/`, `server/middleware/`, plugins. Always full run: `nuxt.config.*`, `vitest.config.*`, `tsconfig.json`, `package.json`/lockfile, ESLint config, `.env*`. **Fallback:** `pnpm lint && pnpm nuxi typecheck && pnpm vitest run && pnpm nuxt build`.

### 7. Layers and posture
Unit (Vitest) for composables/utils/server utils — fast base; component tests (`mountSuspended`) for behavior; integration via `@nuxt/test-utils/e2e` for pages + API routes together; a few Playwright flows. Unit-first; no ratio quota.

### 8. Zero-selection behavior
See §2 (Vitest path miss → exit 1; `-t` miss → exit 0 skipped).
