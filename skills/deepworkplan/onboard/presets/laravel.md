# Preset — Laravel (PHP)

> Reasoning aid, not a template. Verify every assumption against the live repo;
> detected reality wins. Capture the **real** validation command, not the
> example below.

## Signals that identify this stack

- `composer.json` with `laravel/framework` in `require`, and an `artisan`
  console entrypoint at the repo root.
- App layout under `app/`: `Models/`, `Http/Controllers/`, `Http/Middleware/`,
  `Providers/`, plus `config/`, `database/migrations/`, `database/seeders/`,
  `resources/`, and `routes/`.
- Routing in `routes/web.php` (session/web) and `routes/api.php` (stateless
  API); console routes in `routes/console.php`.
- Eloquent ORM models, migrations as timestamped classes under
  `database/migrations/`, factories/seeders for test data.
- Frequently containerized via **Laravel Sail**: look for `docker-compose.yml`,
  a `vendor/bin/sail` wrapper, and MySQL/Postgres/Redis services.
- Config and **secrets** in `.env` (driven by `config/*.php` reading `env()`);
  `.env.example` documents the expected keys.

## What to look for in recon

- The **real** test runner: `php artisan test` (wraps PHPUnit/Pest), bare
  `vendor/bin/phpunit`, or `vendor/bin/pest`. Check `phpunit.xml` and whether
  `pestphp/pest` is in `composer.json`. Test layout is commonly
  `tests/Feature/` and `tests/Unit/`.
- The **real** lint/format/static-analysis gate: `vendor/bin/pint` (Laravel
  Pint), PHP-CS-Fixer, and `vendor/bin/phpstan` / Larastan. Confirm which are
  wired and whether a composer script (`composer test`, `composer lint`) wraps
  them.
- Migration workflow (`php artisan migrate`, `migrate:fresh --seed`) and whether
  it runs inside Sail/Docker.
- Whether queues/jobs (`app/Jobs/`), events/listeners, scheduled tasks
  (`app/Console/Kernel.php` schedule), or Livewire/Inertia front-ends are present.

## Stack-specific skills/agents/commands to generate

- Skills: `model` (Eloquent model + migration + factory), `migration`
  (make/apply migrations safely), `controller` (controller + route + request
  validation), `artisan-command` (console command), optionally `job`/`queue`
  and `eloquent-relation` if those patterns are present.
- Agents: baseline roles + a `migration-author` / `db-reviewer` persona aware
  of migration reversibility and mass-assignment/`$fillable` safety.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — request → route → middleware → controller → Eloquent flow,
  service/repository layering, queues/events, caching/Redis, the DB.
- `TESTING_GUIDE.md` — PHPUnit vs Pest, feature vs unit tests, factories and
  database refresh strategy (`RefreshDatabase`), how to scope a single test.
- `SECURITY.md` — `.env`/config secrets handling, auth model (sessions,
  Sanctum, Passport), mass-assignment and validation boundaries, CSRF.
- Per-module docs: one per bounded area (its models, controllers, routes, jobs,
  policies).

## Typical validation command (FIND the real one)

Often `php artisan test` plus `vendor/bin/pint --test` and/or
`vendor/bin/phpstan analyse`, sometimes wrapped in a composer script and run
**inside Sail** (`./vendor/bin/sail test`). **Do not assume** — read
`composer.json` scripts, `phpunit.xml`, and CI, and capture the exact command,
flagging if it runs inside Docker.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; the target repo's version may differ, so re-verify. Items marked
*documented example* were **not** run here — confirm the exit code and the
selection count in the target repo before trusting them in a gate.

### 1. Full commands
- Tests: `php artisan test` (wraps PHPUnit or Pest per `phpunit.xml`/`pestphp/pest`), or `vendor/bin/phpunit` / `vendor/bin/pest`, from the app root; `--parallel` where configured.
- Static: `vendor/bin/pint --test` (format), `vendor/bin/phpstan analyse` (Larastan), optionally `php artisan route:list` / `config:cache` smoke.

### 2. Scoped invocation
**PHPUnit / `artisan test`** (documented example — PHP is not available in the contributor environment): `php artisan test tests/Unit/OrderTest.php` (file), `php artisan test --filter=OrderTest` (class or method name regex; `--filter='OrderTest::test_total'`), `php artisan test --group=orders` (`@group`), `php artisan test tests/Feature` (directory / suite: `--testsuite=Feature`). **Pest:** `vendor/bin/pest tests/Unit/OrderTest.php`, `--filter=total`, `--group=orders`. **Evidence:** `Tests: N passed` — `N` non-zero.

### 3. Scoped static checks
- `vendor/bin/pint --test app/Models` and `vendor/bin/phpstan analyse app/Models` (documented examples) scope natively to paths; phpstan on a subset can miss cross-file errors — prefer the configured paths in `phpstan.neon` as the real check.

### 4. Source-to-test mapping
`tests/Unit/` ↔ classes/services (no framework boot), `tests/Feature/` ↔ routes/controllers/jobs through the HTTP kernel (`$this->get(...)`), mirrored by namespace (`tests/Feature/Orders/…` ↔ `app/Http/Controllers/Orders/…`); factories in `database/factories/`.

### 5. Affected consumers
No native impact selector; reason from the container bindings and the model graph. **Blind spots:** service providers (`app/Providers/*`) binding implementations, middleware groups in `bootstrap/app.php`/`Kernel`, `routes/*.php`, `config/*.php` + `.env*`, migrations, events/listeners and observers registered by convention, Blade views/components, queued jobs. A provider, middleware, routing or migration change ⇒ the Feature suite or the full run.

### 6. Escalation and fallback
Shared/core: `app/Providers/`, `app/Http/Middleware/`, base models/traits, `app/Services/` shared, `tests/TestCase.php`. Always full run: `composer.json`/`composer.lock`, `config/**`, `routes/**`, `database/migrations/`, `phpunit.xml`/`pest` config, `.env*`. **Fallback:** `vendor/bin/pint --test && vendor/bin/phpstan analyse && php artisan test`.

### 7. Layers and posture
Unit (`tests/Unit`, no app kernel, no DB) for services, actions, value objects — fast base; Feature tests (HTTP kernel + test DB via `RefreshDatabase`) as the integration layer for routes/controllers/jobs; a few Dusk browser tests at most. Unit-first; keep Dusk few.

### 8. Zero-selection behavior
PHPUnit prints `No tests executed!` and exits **0** by default when a `--filter` matches nothing (documented; PHPUnit ≥ 10 offers `--fail-on-empty-test-suite`) — a silent empty run; check the `Tests: N` count. Pest behaves the same by default. A wrong file path fails loudly.
