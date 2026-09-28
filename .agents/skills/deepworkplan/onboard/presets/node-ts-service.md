# Preset — Node / TypeScript service (Express / Fastify / Lambda)

> Reasoning aid, not a template. Verify against the live repo; detected reality
> wins. Capture the **real** validation command, not the example below.

## Signals that identify this stack

- `tsconfig.json` + a server framework in deps: `express`, `fastify`, `koa`,
  `@nestjs/*`, or serverless handlers.
- Serverless shape: `serverless.yml`, `template.yaml` (SAM), `aws-lambda` types,
  handler files exporting `handler`, or a `functions/` directory.
- Long-running service shape: a `start`/`serve` script, a `Dockerfile`, a
  `src/index.ts`/`src/server.ts` entrypoint.
- Package manager from the lockfile (pnpm/yarn/npm) — infer from what's present.
- Layout: `src/` with `routes`/`controllers`/`handlers`, `services`,
  `models`/`schemas`, `middleware`, `lib`.

## What to look for in recon

- The **real** scripts: lint (`eslint:check` / Biome), type-check (`tsc
  --noEmit` / a `type:check` script), test (`jest`/`vitest`), `build`.
- Test convention: usually `*.spec.ts` or `*.test.ts`; where tests live.
- Whether it's **serverless** (per-function handlers, deploy via serverless/SAM)
  or a **long-running service** (HTTP server, container) — this strongly shapes
  `ARCHITECTURE.md`, `PERFORMANCE.md`, and the skills to generate.
- Integrations / external APIs the service talks to; where secrets/config live.
- **Interface surface for the design-system addon:** an ops CLI styled with
  `chalk`/`ink`/`ora` behind a shared output helper is a `cli-output` signal,
  and a chat-platform SDK (Slack Bolt, `discord.js`, `botbuilder`) with a
  message-composition layer is a `conversational` signal — in Phase 7b,
  recommend the matching design-system profile (ask, never auto-apply).

## Stack-specific skills/agents/commands to generate

- Skills: for a service → `endpoint`/`handler` (route + controller + test),
  `service` (business-logic module), `middleware`, `integration` (external API
  client); for serverless → `lambda-fn` (handler + event types + test + deploy
  wiring).
- Agents: baseline + an `api-reviewer` / `integration-author` persona aware of
  contract/versioning and error handling.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — request lifecycle (or event lifecycle for Lambda), service
  boundaries, integration points, error-handling/retry strategy.
- `SECURITY.md` — auth/authz, secrets handling, input validation, the
  sensitive-data boundary.
- `PERFORMANCE.md` — cold starts (serverless), connection pooling, timeouts,
  throughput budgets.
- Per-module docs: per service/handler group and per external integration.

## Typical validation command (FIND the real one)

Commonly `npm run eslint:check && npm test` (or pnpm), plus `tsc --noEmit`.
**Do not assume the package manager or script names** — read `package.json`/CI
and capture the exact commands.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; the target repo's version may differ, so re-verify.

### 1. Full commands
- Tests: `npm test` (`jest` or `vitest run`; check `package.json`), from the repo root; HTTP integration tests often use supertest against the app instance.
- Static: `npm run eslint:check` (or `eslint .`; Biome if adopted), `tsc --noEmit` (or `type:check`), `npm run build`.

### 2. Scoped invocation
**Jest** (flags verified against `jest@29 --help`): `jest <pathPattern>` or `--testPathPattern <regex>` (path filter), `-t "<name>"` (name filter), `--findRelatedTests <src files…>` (impact selection: tests that import the changed sources), `--changedSince <ref>` (impact via git). **Evidence:** the `Tests: N passed` summary. **Zero-selection behavior:** `No tests found` exits **1** by default — `--passWithNoTests` turns that into a silent pass and is forbidden in a gate.

**Vitest** (reference run — vitest 5.0.0, contributor environment):
`vitest run <file>` selects exactly that file (`Test Files 1 passed`); `vitest run <dir>` selects the directory; `vitest run -t "<name>"` filters by test name; `vitest run --project <name>` selects a workspace project. **Evidence of a correct run:** the `Test Files N passed (N)` line — check `N` is what you expected.
**Zero-selection behavior (verified):** a path filter that matches nothing prints `No test files found` and exits **1** (detectable); a `-t` name filter that matches nothing exits **0** with every test *skipped* (`Test Files 8 skipped`) — a silent empty run. Never accept `-t` without confirming a non-zero passed count.

### 3. Scoped static checks
- **ESLint** (example) `eslint src/handlers` / **Biome** (reference run 2.5.12) `biome check <path>` scope natively.
- **`tsc --noEmit`**: project-wide. Type-check is **project-wide by design**: `tsc --noEmit` reads `tsconfig.json`; `tsc <file>` ignores the project config and is *not* a sound scoped check. Do not fabricate a per-file variant — a single project-wide run is the real (and usually cheap) option.

### 4. Source-to-test mapping
Co-located `*.test.ts` / `*.spec.ts` next to modules, or `tests/` (`tests/unit/`, `tests/integration/`) mirroring `src/`. Route/handler files map to their handler tests plus the app-level integration test that mounts them.

### 5. Affected consumers
`jest --findRelatedTests <files>` / `vitest run --changed <ref>`. **Blind spots:** middleware registered in the app factory, route tables, config loaders reading `.env*`, DB migrations/schemas, queue/cron registrations, OpenAPI specs. A change to app-level middleware or config affects every route ⇒ integration suite or full run.

### 6. Escalation and fallback
Shared/core: `src/common/`, `src/lib/`, `src/middleware/`, `src/config/`, the app factory (`app.ts`), shared clients (DB/HTTP). Always full run: `tsconfig*.json`, `jest`/`vitest` config, `package.json`/lockfile, ESLint/Biome config, migrations, `.env*`, `Dockerfile`/compose when tests run in containers. **Fallback:** `npm run eslint:check && tsc --noEmit && npm test`.

### 7. Layers and posture
Unit (Jest/Vitest) for pure modules and handlers with mocked I/O — fast base; integration with supertest against the real app (and a test DB) for the HTTP/persistence seams; contract tests where the service publishes an API; few e2e. Unit-first; no ratio quota.

### 8. Zero-selection behavior
See §2. Jest exits 1 on `No tests found` (unless `--passWithNoTests`); Vitest path miss exits 1, `-t` miss exits 0 skipped.
