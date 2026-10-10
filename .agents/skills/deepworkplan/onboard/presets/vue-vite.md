# Preset — Vue + Vite (TypeScript)

> Reasoning aid, not a template. Verify against the live repo; detected reality
> wins. Capture the **real** validation command, not the example below.

## Signals that identify this stack

- `vite.config.ts`/`vite.config.js` and `vue` in `package.json` `dependencies`
  (Vue 3 → `vue@^3`, Composition API, `<script setup>`).
- `@vitejs/plugin-vue`, `vue-tsc`, `vue-router`, `pinia` (stores) in deps.
- Package manager from the lockfile: `pnpm-lock.yaml` → pnpm, `yarn.lock` →
  yarn, `package-lock.json` → npm. **Infer from the lockfile present.**
- Layout: `src/` with `components/`, `views/`/`pages/`, `stores/`,
  `composables/`, `router/`; possibly Storybook (`.storybook/`, `*.stories.ts`).

> If `react` is in deps instead of `vue`, this is a React+Vite repo — reuse the
> same reasoning but generate React-shaped skills (`component`, `hook`, `route`).

## What to look for in recon

- The **real** `package.json` scripts: the lint script (often `eslint:check`),
  the type-check (`vue-tsc --noEmit` / a `type:check` script), the test command
  (`vitest` / `jest`), and `build`. Capture them verbatim.
- Test convention: `*.test.ts` or `*.spec.ts`; vitest vs jest; component testing
  via `@vue/test-utils` / Testing Library.
- Whether Storybook is used (drives a `storybook-story` skill and a component-doc
  emphasis).
- Where API clients / env config live; the auth/token handling on the client.

## Stack-specific skills/agents/commands to generate

- Skills: `component` (SFC + test + optional story), `store-module` (Pinia
  store), `composable` (reusable composition fn), `view`/`route` (page + router
  entry), `storybook-story` if Storybook is present.
- Agents: baseline + a `component-author` / `frontend-reviewer` persona aware of
  the UI-vs-business component split and accessibility.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — views/components/stores/composables structure, router,
  state management, API layer.
- `STANDARDS.md` — SFC conventions, props/events typing, component boundaries,
  the UI-vs-business split.
- `TESTING_GUIDE.md` — vitest/jest patterns, `@vue/test-utils` mounting/mocking,
  the real `*.spec.ts`/`*.test.ts` pattern, coverage target.
- Per-module docs: per feature folder under `src/` (and a component-library doc
  if Storybook is used).

## Typical validation command (FIND the real one)

Commonly `pnpm run eslint:check && pnpm run type:check && pnpm test` or a
combined script. **Do not assume the package manager or script names** — read
`package.json` and CI and capture the exact commands.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; the target repo's version may differ, so re-verify.

### 1. Full commands
- Tests: `pnpm vitest run` (or `pnpm test`; Jest projects: `pnpm jest`), from the repo root; component tests via `@vue/test-utils`; e2e: `pnpm playwright test` / `pnpm cypress run`.
- Static: `pnpm eslint .` (or `pnpm run eslint:check`; Biome if adopted), `pnpm vue-tsc --noEmit` (or `pnpm run type:check`), `pnpm build` (`vite build`).

### 2. Scoped invocation
**Vitest** (reference run — vitest 5.0.0, contributor environment):
`vitest run <file>` selects exactly that file (`Test Files 1 passed`); `vitest run <dir>` selects the directory; `vitest run -t "<name>"` filters by test name; `vitest run --project <name>` selects a workspace project. **Evidence of a correct run:** the `Test Files N passed (N)` line — check `N` is what you expected.
**Zero-selection behavior (verified):** a path filter that matches nothing prints `No test files found` and exits **1** (detectable); a `-t` name filter that matches nothing exits **0** with every test *skipped* (`Test Files 8 skipped`) — a silent empty run. Never accept `-t` without confirming a non-zero passed count.

**Jest** (flags verified against `jest@29 --help`): `jest <pathPattern>` or `--testPathPattern <regex>` (path filter), `-t "<name>"` (name filter), `--findRelatedTests <src files…>` (impact selection: tests that import the changed sources), `--changedSince <ref>` (impact via git). **Evidence:** the `Tests: N passed` summary. **Zero-selection behavior:** `No tests found` exits **1** by default — `--passWithNoTests` turns that into a silent pass and is forbidden in a gate.

**Playwright** (flags verified against `@playwright/test@1.63 test --help`): `playwright test <file>`, `-g "<title>"`, `--project <name>`, `--only-changed [ref]` (impact via git). `No tests found` is reported when a filter matches nothing — confirm the exit code in the target repo before trusting it in a gate.

### 3. Scoped static checks
- **ESLint** (example): `eslint src/components/Foo.vue` — path scoping is native. **Biome** (reference run 2.5.12): `biome check <path>`.
- **`vue-tsc --noEmit`**: project-wide (reads `tsconfig.json`). Type-check is **project-wide by design**: `tsc --noEmit` reads `tsconfig.json`; `tsc <file>` ignores the project config and is *not* a sound scoped check. Do not fabricate a per-file variant — a single project-wide run is the real (and usually cheap) option.

### 4. Source-to-test mapping
Co-located `Foo.spec.ts` / `Foo.test.ts` next to `Foo.vue`, or `tests/unit/` mirroring `src/`. Pinia stores under `src/stores/` typically have `*.spec.ts` siblings.

### 5. Affected consumers
`vitest run --changed <ref>` (or `jest --findRelatedTests <files>`). **Blind spots:** router config, Pinia plugins, global components registered in `main.ts`, `vite.config.*` aliases, `.env*`, i18n message files — changes there need the affected feature's component tests or the full run.

### 6. Escalation and fallback
Shared/core: `src/stores/`, `src/composables/`, `src/router/`, `src/components/ui/` (design-system primitives), API client modules. Always full run: `vite.config.*`, `vitest.config.*`, `tsconfig*.json`, `package.json`/lockfile, ESLint/Biome config, `.env*`. **Fallback:** `pnpm eslint . && pnpm vue-tsc --noEmit && pnpm vitest run`.

### 7. Layers and posture
Unit (Vitest) for composables, stores, utils — fast base; component tests (`@vue/test-utils`) for behavior visible through props/events; integration for router + store wiring; e2e (Playwright/Cypress) for a few flows. Unit-first; no ratio quota.

### 8. Zero-selection behavior
See §2 (Vitest: path miss exits 1, `-t` miss exits 0 skipped; Jest: exits 1 unless `--passWithNoTests`).
