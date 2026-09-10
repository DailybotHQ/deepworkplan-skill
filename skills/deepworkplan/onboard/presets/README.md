# onboard/presets — Per-Stack Reasoning Guides

These guides help the `onboard` flow reason about a target repo. There is one
guide per common stack, plus a `generic` fallback for anything unrecognized.

> ## The golden rule
>
> **Presets are reasoning aids, NOT templates.** No file in this folder is a
> thing to copy into the target repo. Each guide lists *signals* that identify a
> stack, *what to generate* (stack-specific skills/agents/commands and doc
> emphases), and the *typical* validation command — and every guide reminds you
> to **verify against the live repo** and prefer **detected reality over preset
> assumptions**. If the preset says one thing and the repo says another, **the
> repo wins**. An empty or generic doc, or a command copied from a preset without
> confirming it exists in the repo, is a **failure**.

## How `onboard/SKILL.md` uses these

- **Phase 1 (recon):** after detecting the stack, load the matching guide and
  use its "signals" + "what to look for" as a checklist, verifying each against
  the real repo.
- **Phases 3–6 (generate):** use the guide's "skills/agents/commands to
  generate" and "doc emphases" as a starting point, then trim/extend based on the
  repo's real needs. Capture the **real** validation command (not the preset's
  example) into `AGENTS.md` and `docs/DEVELOPMENT_COMMANDS.md`.

## Index

| Guide | Stack | Identify by |
|-------|-------|-------------|
| [`django.md`](django.md) | Django / DRF (Python) | `manage.py`, `settings.py`, `poetry`/`pip` |
| [`fastapi.md`](fastapi.md) | FastAPI (Python) | `fastapi`/`uvicorn` in deps, async routes, `APIRouter` |
| [`python-package-cli.md`](python-package-cli.md) | Python package / CLI | `[project.scripts]` / `console_scripts`, Click/Typer |
| [`node-ts-service.md`](node-ts-service.md) | Node/TypeScript service (Express/Fastify/Lambda) | server framework imports, `serverless.yml`/handlers |
| [`nestjs.md`](nestjs.md) | NestJS (TypeScript) | `nest-cli.json`, `@Module`/`@Controller` decorators |
| [`ts-lambda.md`](ts-lambda.md) | TypeScript Lambda (Serverless) | `serverless.yml` / SAM `template.yaml` / CDK, handlers |
| [`spring-boot.md`](spring-boot.md) | Spring Boot (Java/Kotlin) | `pom.xml`/`build.gradle`, `@SpringBootApplication` |
| [`rails.md`](rails.md) | Ruby on Rails | `Gemfile`, `bin/rails`, `app/{models,controllers}` |
| [`laravel.md`](laravel.md) | Laravel (PHP) | `composer.json`, `artisan`, `app/Http/Controllers` |
| [`vue-vite.md`](vue-vite.md) | Vue + Vite (TypeScript) | `vite.config.*`, `vue` in deps |
| [`nuxt.md`](nuxt.md) | Nuxt (Vue) | `nuxt.config.*`, `server/api`, Nitro |
| [`nextjs.md`](nextjs.md) | Next.js (React) | `next.config.*`, `app/` or `pages/` router |
| [`sveltekit.md`](sveltekit.md) | SvelteKit | `svelte.config.js`, `src/routes/+page.svelte` |
| [`angular.md`](angular.md) | Angular | `angular.json`, `@Component`/`@NgModule` |
| [`astro-svelte.md`](astro-svelte.md) | Astro (+ Svelte) static/SSR site | `astro.config.*`, `.astro`/`.svelte` files |
| [`react-native.md`](react-native.md) | React Native (Expo) | `app.json`/`app.config.*`, `expo`/`react-native` deps |
| [`flutter.md`](flutter.md) | Flutter (Dart) | `pubspec.yaml`, `lib/main.dart` |
| [`swift-ios.md`](swift-ios.md) | Swift / iOS | `*.xcodeproj`/`*.xcworkspace`, `Package.swift`, XCTest |
| [`go.md`](go.md) | Go (modules) | `go.mod`, `package main`, `cmd/`/`internal/` |
| [`rust.md`](rust.md) | Rust (Cargo) | `Cargo.toml`, `src/main.rs`/`lib.rs` |
| [`terraform.md`](terraform.md) | Terraform / IaC | `*.tf`, `main.tf`/`variables.tf`/`outputs.tf` |
| [`generic.md`](generic.md) | **Fallback** — any unrecognized stack | none of the above match |

## The testing section every preset carries

Each preset ends with a **Testing and validation (verified vs example)** section
that Phase 1 and Phase 4 read to produce the testing map of
`DOCUMENTATION_STANDARD.md` §3.4. Every preset uses the same sub-headings so the
onboarding flow can rely on them:

1. **Full commands** — the stack's idiomatic full test, lint, format and
   type-check commands, with the working directory they run from.
2. **Scoped invocation** — by file, directory/module, package (workspaces) and
   marker/name filter, each with a runnable example, the tool version where
   flag behavior depends on it, and the expected evidence of a correct run
   (how the runner reports the selected count). Path filtering, name filtering
   and impact selection are **different guarantees** — say which one each is.
3. **Scoped static checks** — lint/format/type-check by path where the tool
   supports it; an explicit "not supported / project-wide is the real option"
   where it does not. Never fabricate a single-file variant.
4. **Source-to-test mapping** — the stack's conventional mapping rule
   (co-located, mirrored tree, naming, markers, package boundary).
5. **Affected consumers** — the stack's affected-tests tooling (`--changed`,
   `--findRelatedTests`, `testmon`, task graphs …), how to use it, and its
   blind spots (dynamic loading, templates, fixtures, generated inputs, config).
6. **Escalation and fallback** — what counts as shared/core in this stack, which
   configuration/schema/dependency/toolchain changes always trigger the full
   run, and the explicit fallback command.
7. **Layers and posture** — where unit / integration / e2e tests conventionally
   live, how each layer runs, and the stack's idiomatic unit-vs-integration
   split (unit-first behavioral coverage; integration at real seams; few e2e).
8. **Zero-selection behavior** — what the runner does when a filter matches
   nothing (exit code, message) so an agent can recognize an empty run.

**Marking rule.** A command in a preset is an **illustrative example** until it
is verified against the target repository in Phase 1; the flow labels it
verified only after a real run with a non-empty selection. A preset must not
label a known supported feature unavailable to avoid research, nor present a
documentation example as a live repository command.

## Archetype note (orchestrator hub)

Presets describe **individual-repo** stacks (the 99% case). If Phase 2 classifies
the target as an **orchestrator hub** (a coordination repo over multiple
sub-repos — `repositories/` folder, mostly-markdown root, sub-repos tracked
separately, root `AGENTS.md` indexing other repos' `AGENTS.md`), do **not** apply
a stack preset to the hub itself. Instead:

- Treat the hub's own content (mostly docs/coordination) with the `generic`
  guide's first-principles reasoning.
- Layer the **hub-only** structure on top of the baseline: a sub-project
  navigation index (e.g. `repositories/README.md`), `ECOSYSTEM_CONTEXT.md` + a
  cross-project standards guide, repository-boundary rules in `AGENTS.md` (commit
  inside each sub-repo, never from the hub root), and the orchestrator/child-DWP
  capability (see `../../guide/orchestrator.md`).
- Each **sub-repo** is onboarded independently with its own matching preset; the
  hub does not document sub-repo internals.

See `ARCHETYPES.md` (Task 2 spec) for the full classification heuristic and the
onboarding-difference matrix.
