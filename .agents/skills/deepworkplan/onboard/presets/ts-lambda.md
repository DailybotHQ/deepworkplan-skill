# Preset — TS Lambda (Serverless) (Serverless Framework / SAM / CDK)

> Reasoning aid, not a template. Verify every assumption against the live repo;
> detected reality wins. Capture the **real** validation command, not the
> example below.

## Signals that identify this stack

- A deploy descriptor — exactly which one shapes the whole flow:
  - `serverless.yml` → **Serverless Framework** (`functions:` map, `provider:`,
    plugins like `serverless-esbuild`).
  - `template.yaml`/`template.yml` with `Transform: AWS::Serverless-2016-10-31`
    → **AWS SAM**.
  - `cdk.json` + a `bin/`/`lib/` stack tree → **AWS CDK** (functions defined in
    TypeScript constructs).
- `tsconfig.json` plus `aws-lambda` types; handler files exporting `handler`
  (e.g. `export const handler = async (event) => ...`).
- Per-function layout under `src/functions/` or `src/handlers/`, often one
  directory per function. Bundler config: `esbuild`/`esbuild.config`, or `tsc`.
- Package manager from the lockfile (pnpm/yarn/npm). **Infer the toolchain
  (Serverless vs SAM vs CDK) from the descriptor that's present** — do not assume.

## What to look for in recon

- The **real** scripts: lint (`eslint`), type-check (`tsc --noEmit` /
  `type:check`), test (`jest`/`vitest`), and the bundle step (esbuild vs tsc).
  Test convention is usually `*.test.ts`/`*.spec.ts` colocated or under `tests/`.
- The **real** package/synth command — the safe, read-only gate:
  `sls package` (Serverless), `sam build` (+ `sam validate`), or `cdk synth`.
  **`sls deploy` / `sam deploy` / `cdk deploy` mutate the AWS account — never run
  them as a validation gate.**
- Event sources per function (API Gateway/HTTP, SQS, SNS, EventBridge, S3,
  DynamoDB streams) — this shapes the handler skill and the event types.
- **IAM scope per function** (least privilege), cold-start/bundle-size budget,
  and where secrets/config live (SSM Parameter Store, Secrets Manager, env vars).

## Stack-specific skills/agents/commands to generate

- Skills: `lambda-fn` (new handler + typed event + unit test + descriptor
  wiring), `event-source` (wire a trigger to a function), `iam-policy` (scope a
  least-privilege role), optionally `layer` (shared Lambda layer) and
  `local-invoke` (run a function locally via `sls invoke local`/`sam local`).
- Agents: baseline roles + a `security-reviewer` / `iam-auditor` persona focused
  on least-privilege IAM, and an `api-reviewer` for contract/error handling.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — event lifecycle per function, the toolchain (Serverless /
  SAM / CDK), function topology and their triggers, shared layers/utilities.
- `SECURITY.md` — **least-privilege IAM per function** (call this out
  explicitly), secrets handling (SSM/Secrets Manager, never hard-coded),
  input validation at the event boundary, the sensitive-data boundary.
- `PERFORMANCE.md` — cold starts, bundle size (tree-shaking via esbuild),
  memory/timeout tuning, provisioned concurrency, connection reuse.
- Per-module docs: one per function (its event source, IAM role, dependencies).

## Typical validation command (FIND the real one)

Often `npm run lint && tsc --noEmit && npm test && sls package` (or
`sam build && sam validate`, or `cdk synth`). **Do not assume** the toolchain,
package manager, or script names — read `package.json`/the descriptor/CI and
capture the exact commands, treating synth/package (not deploy) as the gate.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; the target repo's version may differ, so re-verify.

### 1. Full commands
- Tests: `npm test` (`jest` or `vitest run`), from the repo root (or the function package in a monorepo).
- Static: `npm run lint` (ESLint), `tsc --noEmit`, the bundle step (`esbuild` script / `sls package` / `sam build` / `cdk synth`) as the build gate.

### 2. Scoped invocation
**Jest** (flags verified against `jest@29 --help`): `jest <pathPattern>` or `--testPathPattern <regex>` (path filter), `-t "<name>"` (name filter), `--findRelatedTests <src files…>` (impact selection: tests that import the changed sources), `--changedSince <ref>` (impact via git). **Evidence:** the `Tests: N passed` summary. **Zero-selection behavior:** `No tests found` exits **1** by default — `--passWithNoTests` turns that into a silent pass and is forbidden in a gate.

**Vitest** (reference run — vitest 5.0.0, contributor environment):
`vitest run <file>` selects exactly that file (`Test Files 1 passed`); `vitest run <dir>` selects the directory; `vitest run -t "<name>"` filters by test name; `vitest run --project <name>` selects a workspace project. **Evidence of a correct run:** the `Test Files N passed (N)` line — check `N` is what you expected.
**Zero-selection behavior (verified):** a path filter that matches nothing prints `No test files found` and exits **1** (detectable); a `-t` name filter that matches nothing exits **0** with every test *skipped* (`Test Files 8 skipped`) — a silent empty run. Never accept `-t` without confirming a non-zero passed count.

Monorepo of functions: run from the function's package (`npm test --workspace packages/orders`) or with `vitest run --project orders`; note the cwd in `TESTING_GUIDE.md`.

### 3. Scoped static checks
- **ESLint** (example) `eslint src/handlers/orders` scopes natively.
- **`tsc --noEmit`**: project-wide; `cdk synth` / `sam build` / `sls package`: whole stack. Type-check is **project-wide by design**: `tsc --noEmit` reads `tsconfig.json`; `tsc <file>` ignores the project config and is *not* a sound scoped check. Do not fabricate a per-file variant — a single project-wide run is the real (and usually cheap) option.

### 4. Source-to-test mapping
Co-located `handler.test.ts` next to `handler.ts`, or `tests/` mirroring `src/handlers/` / `src/lib/`. Infrastructure definitions (`serverless.yml`, `template.yaml`, CDK stacks) are covered by synth/package + any infra unit tests (CDK assertions), not by handler tests.

### 5. Affected consumers
`jest --findRelatedTests <files>` / `vitest run --changed <ref>`. **Blind spots:** event mappings and env vars in `serverless.yml`/`template.yaml`/CDK (a handler's trigger or permissions change with no code import), shared layers, `.env*`, IAM policies, bundler config (esbuild externals). Infra file change ⇒ synth/package gate + the affected function's tests, or the full run.

### 6. Escalation and fallback
Shared/core: `src/lib/`, shared middleware (middy), common clients (DynamoDB/S3 wrappers), Lambda layers. Always full run: `serverless.yml`/`template.yaml`/CDK stacks, `esbuild`/bundler config, `tsconfig*.json`, `jest`/`vitest` config, `package.json`/lockfile, `.env*`. **Fallback:** `npm run lint && tsc --noEmit && npm test && <package/synth step>`.

### 7. Layers and posture
Unit (Jest/Vitest) for handler logic with mocked AWS SDK clients — fast base; integration against LocalStack/emulators or a dev stage only for real service seams (DynamoDB queries, SQS wiring); contract tests for event shapes; few e2e. Unit-first; no ratio quota.

### 8. Zero-selection behavior
See §2. Jest exits 1 on `No tests found` (unless `--passWithNoTests`); Vitest path miss exits 1, `-t` miss exits 0 skipped.
