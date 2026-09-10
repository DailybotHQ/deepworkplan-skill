# Preset — React Native / Expo (TypeScript)

> Reasoning aid, not a template. Verify against the live repo; detected reality
> wins. Capture the **real** validation command, not the example below.

## Signals that identify this stack

- `react-native` in `package.json` `dependencies`, with `react` alongside it.
- **Expo managed**: `expo` in deps, an `app.json` or `app.config.ts`/`app.config.js`,
  an `expo` key, and often no committed `ios/`/`android/` folders.
- **Bare React Native**: committed `ios/` (with a `*.xcodeproj`/`Podfile`) and
  `android/` (with `build.gradle`) folders, a `react-native.config.js`. **Detect
  managed vs bare early — it changes nearly every command.**
- `metro.config.js`/`metro.config.cjs` (the bundler), `babel.config.js` with
  `babel-preset-expo` or `metro-react-native-babel-preset`.
- Navigation: React Navigation (`@react-navigation/*`) or **expo-router** (an
  `app/` directory with file-based routes, `expo-router` in deps).
- Package manager from the lockfile: `pnpm-lock.yaml` → pnpm, `yarn.lock` →
  yarn, `package-lock.json` → npm; Expo projects often pin via `expo install`.
  **Infer from the lockfile present.**
- Layout: `src/`/`app/` with `screens/`/`components/`, `navigation/`, `hooks/`,
  `services/`; `assets/` for fonts/images.

## What to look for in recon

- The **real** test setup: Jest (`jest.config.*` or a `jest` key,
  `jest-expo`/`react-native` preset) with `@testing-library/react-native`. Test
  files `*.test.tsx`/`*.test.ts` or under `__tests__/`. **Confirm the preset.**
- The **real** lint/type-check: `eslint` (`.eslintrc`/`eslint.config.js`,
  often `eslint-config-expo` or `@react-native`), `tsc --noEmit`/a `type-check`
  script, Prettier. Capture verbatim.
- The **real** run/build path, which depends on managed vs bare:
  - Expo managed: `expo start`, `expo prebuild`, and **EAS** (`eas build`,
    `eas.json`) for store builds.
  - Bare RN: `npx react-native run-ios`/`run-android`, `pod install`,
    `xcodebuild`/Gradle for release builds.
- Native modules / config plugins (Expo `plugins`), and where secrets/env live
  (`.env`, `app.config.ts` `extra`, EAS secrets).

## Stack-specific skills/agents/commands to generate

- Skills: `screen` (screen + navigation entry + test), `component` (RN component +
  test), `hook` (custom hook), `navigator`/`route` (React Navigation stack or an
  expo-router file), `native-module` only if bare RN with custom native code.
- Agents: baseline + a `mobile-author` / `frontend-reviewer` persona aware of
  the managed-vs-bare split, platform branches (iOS/Android), and list/perf
  pitfalls (FlatList, memoization).
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — screen/navigation structure (React Navigation vs
  expo-router), state, the native config (managed vs bare), EAS pipeline.
- `STANDARDS.md` — component/screen conventions, styling approach
  (`StyleSheet`/styled), platform-specific files (`*.ios.tsx`/`*.android.tsx`).
- `TESTING_GUIDE.md` — Jest + `@testing-library/react-native`, the preset,
  the real `*.test.tsx` pattern, mocking native modules.
- Per-module docs: per feature folder (its screens, navigators, hooks, services).

## Typical validation command (FIND the real one)

Commonly `npm run lint && npm run type-check && npm test` (or the
pnpm/yarn equivalent). The **build/run** command is managed-vs-bare specific
(`expo start`/`eas build` vs `npx react-native run-ios`/Gradle). **Do not
assume** the package manager, the preset, or whether it's managed or bare —
read `package.json`, `app.json`/`app.config.*`, check for `ios/`/`android/`,
and capture the exact commands.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; items marked *documented example* were **not** run here —
confirm the exit code and the selection count in the target repo before trusting
them in a gate.

### 1. Full commands
- Tests: `npm test` (Jest with `jest-expo` / `react-native` preset and `@testing-library/react-native`), from the app root; e2e: `detox test -c <config>` or `maestro test flows/`.
- Static: `npm run lint` (ESLint), `npm run type-check` (`tsc --noEmit`), `npx expo-doctor` (Expo projects), `npx expo export`/`eas build` as build gates where applicable.

### 2. Scoped invocation
**Jest** (flags verified against `jest@29 --help` in the contributor environment): `jest src/screens/Orders` (path pattern), `--testPathPattern <regex>`, `-t "<name>"`, `--findRelatedTests <src files…>` (import-graph impact), `--changedSince <ref>`. **Evidence:** `Tests: N passed`. **Zero-selection:** `No tests found` exits **1** unless `--passWithNoTests` (never in a gate).

**Detox / Maestro** (documented example): `detox test -c ios.sim.debug e2e/orders.test.js` (one suite), `maestro test flows/orders.yaml` (one flow). Both need a built app and a simulator/emulator — mark them CI/device-only if they cannot run locally.

### 3. Scoped static checks
- **ESLint** (documented example): `eslint src/screens/Orders` scopes natively.
- **`tsc --noEmit`**: project-wide (reads `tsconfig.json`); `tsc <file>` ignores the project config and is not a sound scoped check — say so rather than fabricate a per-file variant.

### 4. Source-to-test mapping
Co-located `__tests__/` folders or `*.test.tsx` next to screens/components/hooks; `src/screens/Orders/__tests__/OrdersScreen.test.tsx` ↔ `OrdersScreen.tsx`; native-module mocks in `jest.setup.js`.

### 5. Affected consumers
`jest --findRelatedTests <changed files>` (verified flag) follows imports. **Blind spots:** native module mocks in `jest.setup.js`, `app.json`/`app.config.*` (Expo config and plugins), `metro.config.js`/`babel.config.js`, navigation stacks (a route registered by name), assets/fonts, `.env*`/`expo-constants`, platform folders (`ios/`, `android/`) — none are import edges. A navigator, theme/provider, or config-plugin change ⇒ the full Jest run (and a build for config plugins).

### 6. Escalation and fallback
Shared/core: `src/components/ui/`, `src/hooks/`, `src/navigation/`, providers/context, API clients, `App.tsx`. Always full run: `app.json`/`app.config.*`, `jest.config.*`/`jest.setup.*`, `babel.config.js`, `metro.config.js`, `tsconfig.json`, `package.json`/lockfile, ESLint config, `.env*`, native project files. **Fallback:** `npm run lint && npm run type-check && npm test`.

### 7. Layers and posture
Unit (Jest) for hooks, reducers/stores, utils — fast base; component/screen tests with `@testing-library/react-native` for behavior; integration for navigation + store wiring; Detox/Maestro for a few critical flows on a device. Unit-first; keep e2e few.

### 8. Zero-selection behavior
Jest exits **1** on `No tests found` unless `--passWithNoTests` (verified flag semantics). Detox/Maestro with a wrong file/flow path fail loudly; a flow that matches no screens still "passes" its steps — review the report, not just the exit code.
