# Preset — Next.js (React)

> Reasoning aid, not a template. Verify against the live repo; detected reality
> wins. Capture the **real** validation command, not the example below.

## Signals that identify this stack

- `next` and `react` in `package.json` `dependencies`, plus a
  `next.config.js` / `next.config.mjs` / `next.config.ts` at the repo root.
- **Router detection (decisive):** an `app/` directory → **App Router**
  (Server Components by default, `'use client'` for Client Components, nested
  `layout.tsx`/`page.tsx`, `route.ts` route handlers, server actions); a
  `pages/` directory → **Pages Router** (`pages/_app`, `getServerSideProps`/
  `getStaticProps`, `pages/api/*` API routes). Some repos run **both** during a
  migration — note it.
- Package manager from the lockfile: `pnpm-lock.yaml` → pnpm, `yarn.lock` →
  yarn, `package-lock.json` → npm. **Infer from the lockfile present.**
- Layout: `src/` or root-level `app/`/`pages/`, `components/`, `lib/`,
  `public/`; TypeScript via `tsconfig.json`; styling via Tailwind, CSS Modules,
  or styled-components.

## What to look for in recon

- The **real** `package.json` scripts: `dev`, `build` (`next build`),
  `start`, `lint` (`next lint` / `eslint`), and the test command. Capture them
  verbatim.
- Lint config: `eslint-config-next` with `next/core-web-vitals` (the canonical
  Next ESLint preset). Confirm whether it's `next lint` or a direct `eslint`
  invocation, and whether Biome is used instead.
- Test convention: unit/component via **Jest** (`jest.config`) or **Vitest**
  (`vitest.config`) with Testing Library; end-to-end via **Playwright**
  (`playwright.config.ts`) or **Cypress** (`cypress/`). Note `*.test.tsx` /
  `*.spec.tsx` naming and where tests live.
- Data layer: server actions, route handlers (`app/**/route.ts`), or
  `pages/api/*`; where env/config and secrets live (`.env.local`,
  `NEXT_PUBLIC_*` vs server-only vars — the boundary matters).
- Rendering strategy (static/SSG, SSR, ISR, streaming) — it shapes
  `PERFORMANCE.md`.

## Stack-specific skills/agents/commands to generate

- Skills (App Router): `page`/`route` (segment `page.tsx` + `layout.tsx`),
  `server-component`, `client-component`, `route-handler` (`route.ts` +
  test), `server-action`. Skills (Pages Router): `page` (`pages/*` +
  data-fetching fn), `api-route` (`pages/api/*` + test), `component`.
- Agents: baseline + a `frontend-reviewer` persona aware of the Server vs
  Client Component boundary, the `NEXT_PUBLIC_*` env boundary, and Core Web
  Vitals.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — router model (App vs Pages), Server/Client Component
  split, data fetching (server actions / route handlers / `getServerSideProps`),
  rendering/caching strategy.
- `STANDARDS.md` — component conventions, the `'use client'` boundary,
  props/typing, file-colocation rules.
- `TESTING_GUIDE.md` — Jest/Vitest + Testing Library patterns, Playwright/
  Cypress e2e flow, the real `*.test.tsx`/`*.spec.tsx` pattern, coverage target.
- `PERFORMANCE.md` — rendering strategy, bundle/Core Web Vitals budgets,
  `next/image` and font optimization.

## Typical validation command (FIND the real one)

Commonly `pnpm run lint && pnpm test && pnpm run build` (or npm/yarn), with
`next build` as the build gate and a separate e2e job. **Do not assume the
package manager, the router, or script names** — read `package.json`, the
config files, and CI, and capture the exact commands.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; the target repo's version may differ, so re-verify.

### 1. Full commands
- Tests: `pnpm jest` or `pnpm vitest run` (whichever `package.json` wires as `test`), from the repo root; e2e: `pnpm playwright test` or `pnpm cypress run`.
- Static: `pnpm next lint` (or `pnpm eslint .`; Biome if adopted), `pnpm tsc --noEmit` (or `type-check`), `pnpm next build` (also type-checks).

### 2. Scoped invocation
**Jest** (flags verified against `jest@29 --help`): `jest <pathPattern>` or `--testPathPattern <regex>` (path filter), `-t "<name>"` (name filter), `--findRelatedTests <src files…>` (impact selection: tests that import the changed sources), `--changedSince <ref>` (impact via git). **Evidence:** the `Tests: N passed` summary. **Zero-selection behavior:** `No tests found` exits **1** by default — `--passWithNoTests` turns that into a silent pass and is forbidden in a gate.

**Vitest** (reference run — vitest 5.0.0, contributor environment):
`vitest run <file>` selects exactly that file (`Test Files 1 passed`); `vitest run <dir>` selects the directory; `vitest run -t "<name>"` filters by test name; `vitest run --project <name>` selects a workspace project. **Evidence of a correct run:** the `Test Files N passed (N)` line — check `N` is what you expected.
**Zero-selection behavior (verified):** a path filter that matches nothing prints `No test files found` and exits **1** (detectable); a `-t` name filter that matches nothing exits **0** with every test *skipped* (`Test Files 8 skipped`) — a silent empty run. Never accept `-t` without confirming a non-zero passed count.

**Playwright** (flags verified against `@playwright/test@1.63 test --help`): `playwright test <file>`, `-g "<title>"`, `--project <name>`, `--only-changed [ref]` (impact via git). `No tests found` is reported when a filter matches nothing — confirm the exit code in the target repo before trusting it in a gate.

### 3. Scoped static checks
- **`next lint --dir <dir>`** (documented example) and **`eslint <path>`** scope natively; **Biome** `biome check <path>` (reference run 2.5.12).
- **`tsc --noEmit`** / `next build`: project-wide. Type-check is **project-wide by design**: `tsc --noEmit` reads `tsconfig.json`; `tsc <file>` ignores the project config and is *not* a sound scoped check. Do not fabricate a per-file variant — a single project-wide run is the real (and usually cheap) option.

### 4. Source-to-test mapping
Co-located `*.test.tsx` / `*.spec.tsx` next to components, `__tests__/` folders, or `tests/` mirroring `app/` / `pages/` / `components/` / `lib/`. Route handlers (`app/**/route.ts`) and server actions get unit tests next to them or integration tests under `tests/`.

### 5. Affected consumers
`jest --findRelatedTests <changed src files>` (import-graph impact) or `vitest run --changed <ref>`. **Blind spots:** `app/layout.tsx` and nested layouts (affect every child route), `middleware.ts`, `next.config.*`, route segment config exports, `.env*`, `public/`, MDX/content files, CSS modules — none are import edges that tests follow. Layout/middleware changes ⇒ the affected route group's tests or the full run.

### 6. Escalation and fallback
Shared/core: `lib/`, `components/ui/`, `app/layout.tsx`, `middleware.ts`, shared hooks/providers, API clients. Always full run: `next.config.*`, `jest.config.*`/`vitest.config.*`, `tsconfig.json`, `package.json`/lockfile, ESLint/Biome config, `.env*`. **Fallback:** `pnpm next lint && pnpm tsc --noEmit && pnpm test` (+ `pnpm next build`).

### 7. Layers and posture
Unit (Jest/Vitest) for `lib/`, hooks, pure components — fast base; component tests with Testing Library for behavior; integration for route handlers / server actions with real modules; Playwright/Cypress for a few flows. Unit-first; no ratio quota.

### 8. Zero-selection behavior
See §2. Jest: `No tests found` exits 1 unless `--passWithNoTests` (never in a gate). Vitest: path miss exits 1, `-t` miss exits 0 skipped.
