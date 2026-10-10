# Preset — NestJS (TypeScript)

> Reasoning aid, not a template. Verify every assumption against the live repo;
> detected reality wins. Capture the **real** validation command, not the
> example below.

## Signals that identify this stack

- `nest-cli.json` at the repo root and `@nestjs/core`, `@nestjs/common` in
  `package.json` deps; usually `reflect-metadata` and `rxjs`.
- A bootstrap `main.ts` calling `NestFactory.create(AppModule)`; a root
  `app.module.ts`.
- The decorator + DI model: `@Module`, `@Controller`, `@Injectable`, plus
  `@Get/@Post/...` route decorators and constructor injection.
- Feature folders, each with `*.module.ts`, `*.controller.ts`, `*.service.ts`,
  and `dto/` (request/response DTOs, often `class-validator`/`class-transformer`).
- Cross-cutting providers: guards, pipes (`ValidationPipe`), interceptors,
  filters, and `@nestjs/config` for configuration.
- Package manager from the lockfile (`pnpm-lock.yaml` → pnpm, `yarn.lock` →
  yarn, `package-lock.json` → npm). **Infer from what's present.**
- Common companions: TypeORM/Prisma/Mongoose, `@nestjs/swagger`, microservices
  (`@nestjs/microservices`), or GraphQL (`@nestjs/graphql`).

## What to look for in recon

- The **real** scripts in `package.json`: `test` (Jest unit), `test:e2e` (Jest
  via `test/jest-e2e.json`), `test:cov`, `lint` (ESLint), `build` (`nest build`
  / `tsc`), and `start:dev`. Capture them verbatim.
- Test convention: unit tests are `*.spec.ts` co-located with sources; e2e tests
  are `*.e2e-spec.ts` under `test/`, using `@nestjs/testing`'s
  `Test.createTestingModule(...)` and supertest.
- Module graph: how feature modules import/export providers and are wired into
  `AppModule`; which providers are global.
- Validation/serialization strategy: a global `ValidationPipe`, DTOs with
  `class-validator` decorators, and any interceptors/serializers.
- The ORM/data layer and migration workflow (TypeORM migrations vs Prisma
  `migrate`), and where config/secrets live (`@nestjs/config`, `.env`).

## Stack-specific skills/agents/commands to generate

- Skills: `module-add` (feature module scaffold + wiring into `AppModule`),
  `controller` (controller + route handlers + spec), `provider`/`service`
  (injectable service + spec), `dto` (request/response DTO with validation),
  optionally `guard`/`pipe`/`interceptor` and `migration` if an ORM is present.
- Agents: baseline roles + an `api-reviewer` / `module-author` persona aware of
  DI scope, DTO validation, and module boundaries.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — module graph and DI, request → guard → pipe → controller →
  service → repository flow, interceptors/filters, transport (HTTP/microservice/
  GraphQL).
- `TESTING_GUIDE.md` — Jest unit `*.spec.ts` with `Test.createTestingModule` and
  provider mocking, e2e `*.e2e-spec.ts` with supertest, how to scope one
  module's tests.
- `SECURITY.md` — auth guards/strategies (`@nestjs/passport`, JWT), global
  `ValidationPipe`, secrets via `@nestjs/config`.
- Per-module docs: one per feature module (its controllers, providers, DTOs).

## Typical validation command (FIND the real one)

Commonly `<pm> run lint && <pm> test && <pm> run build` (e.g. `pnpm`/`npm`),
sometimes with `test:e2e`. **Do not assume the package manager or script
names** — read `package.json`/CI and capture the exact commands.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; the target repo's version may differ, so re-verify.

### 1. Full commands
- Tests: `pnpm test` (Jest unit, `*.spec.ts`), `pnpm test:e2e` (Jest via `test/jest-e2e.json`, `*.e2e-spec.ts` with supertest), `pnpm test:cov`, from the repo root.
- Static: `pnpm lint` (ESLint), `pnpm build` (`nest build` / `tsc`), optionally `pnpm tsc --noEmit`.

### 2. Scoped invocation
**Jest** (flags verified against `jest@29 --help`): `jest <pathPattern>` or `--testPathPattern <regex>` (path filter), `-t "<name>"` (name filter), `--findRelatedTests <src files…>` (impact selection: tests that import the changed sources), `--changedSince <ref>` (impact via git). **Evidence:** the `Tests: N passed` summary. **Zero-selection behavior:** `No tests found` exits **1** by default — `--passWithNoTests` turns that into a silent pass and is forbidden in a gate.

Nest specifics: `pnpm test -- src/users/users.service.spec.ts` (unit, path filter), `pnpm test:e2e -- test/users.e2e-spec.ts` (one e2e file — it boots the Nest app once per file), `pnpm test -- -t "UsersService"` (name filter). Remember the `--` separator when the script wraps `jest`.

### 3. Scoped static checks
- **ESLint** (example): `eslint src/users` scopes natively.
- **`tsc --noEmit`** / `nest build`: project-wide. Type-check is **project-wide by design**: `tsc --noEmit` reads `tsconfig.json`; `tsc <file>` ignores the project config and is *not* a sound scoped check. Do not fabricate a per-file variant — a single project-wide run is the real (and usually cheap) option.

### 4. Source-to-test mapping
Co-located `foo.service.spec.ts` / `foo.controller.spec.ts` next to the unit; e2e under `test/*.e2e-spec.ts` per feature module. A module's DI graph (`@Module` providers/imports) is the real dependency structure — tests of a provider's consumers are the affected set.

### 5. Affected consumers
`jest --findRelatedTests <changed files>` follows imports, which in Nest largely mirror the DI graph. **Blind spots:** providers injected by token (`@Inject(TOKEN)`), dynamic modules (`forRoot`/`forRootAsync`), global modules and guards/interceptors/pipes registered in `main.ts` or via `APP_GUARD`, config from `.env*`/`ConfigModule`, ORM entities/migrations. A change to a global guard/interceptor or an entity affects every request path ⇒ the e2e suite or the full run.

### 6. Escalation and fallback
Shared/core: `src/common/` (guards, interceptors, pipes, filters), `src/config/`, shared modules imported by many features, entities/schemas, `main.ts`. Always full run: `nest-cli.json`, `tsconfig*.json`, `jest` config, `package.json`/lockfile, ORM config/migrations, `.env*`. **Fallback:** `pnpm lint && pnpm test && pnpm test:e2e`.

### 7. Layers and posture
Unit (Jest with `Test.createTestingModule` and mocked providers) for services/controllers — fast base; integration = e2e-spec files with supertest against a real Nest app and a test database where the module truly wires persistence/HTTP; keep e2e to the real seams. Unit-first; no ratio quota.

### 8. Zero-selection behavior
Jest: `No tests found` exits 1 unless `--passWithNoTests`. A `--testPathPattern` regex that matches nothing is the common mistake — check the `Tests:` summary count.
