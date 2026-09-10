# Preset — Ruby on Rails (Ruby)

> Reasoning aid, not a template. Verify every assumption against the live repo;
> detected reality wins. Capture the **real** validation command, not the
> example below.

## Signals that identify this stack

- A `Gemfile` declaring `rails` (and `Gemfile.lock` pinning it), `bin/rails` and
  `bin/rake` executables, and `config/application.rb` requiring `rails/all`.
- The MVC layout under `app/`: `app/models`, `app/controllers`, `app/views`,
  plus `app/helpers`, `app/jobs`, `app/mailers`, and (modern) `app/javascript`.
- Routing in `config/routes.rb`; the database layer in `db/migrate/*` migrations
  and `db/schema.rb` (or `db/structure.sql`).
- Configuration under `config/` (`environments/{development,test,production}.rb`),
  and encrypted secrets in `config/credentials.yml.enc` + `config/master.key`.
- Test framework from what's present: **RSpec** (`spec/`, `.rspec`,
  `rspec-rails` in the Gemfile) **or** Minitest (`test/`, the Rails default).
  **Infer from what exists.**

## What to look for in recon

- The **real** test command: `bundle exec rspec` (RSpec) or `bin/rails test`
  (Minitest), plus system/integration variants (`bin/rails test:system`).
  Confirm the directory (`spec/` vs `test/`) and any factories
  (`factory_bot`) vs fixtures.
- The **real** lint/format gate: `rubocop` (often `bundle exec rubocop`,
  `.rubocop.yml`), Standard, or `erb_lint`/`brakeman` — capture how it's
  invoked.
- The migration workflow (`bin/rails db:migrate`, `db:rollback`,
  `db:schema:load`) and whether the schema is `schema.rb` or `structure.sql`.
- Background jobs (Active Job adapter: Sidekiq/Resque/GoodJob), and the
  front-end approach (Hotwire/Turbo + Stimulus, importmaps/jsbundling,
  ViewComponent).
- Where secrets/config live: `config/credentials*`, `Rails.application.config`,
  `ENV`, and the multi-environment layout.

## Stack-specific skills/agents/commands to generate

- Skills: `model-add` (model + migration + spec), `migration` (write/apply a
  migration safely), `controller` (controller + routes + request spec),
  `endpoint`/`resource` (resourceful route + controller + view/JSON),
  optionally `job` (Active Job) and `mailer` if present.
- Agents: baseline roles + a `migration-author` / `db-reviewer` persona aware of
  reversible migrations and zero-downtime concerns.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — request → route → controller → model → view/serializer
  flow, Active Record associations, jobs/mailers, Hotwire/Turbo if present.
- `TESTING_GUIDE.md` — RSpec vs Minitest, model/request/system specs, factories
  vs fixtures, how to run a single spec/test file.
- `SECURITY.md` — `config/credentials` + `master.key` handling, strong
  parameters, CSRF, auth (Devise/has_secure_password), Brakeman.
- Per-module docs: per domain area (its models, controllers, jobs, mailers).

## Typical validation command (FIND the real one)

Often `bundle exec rubocop && bundle exec rspec`, or `bin/rails test` for a
Minitest app. **Do not assume** the test framework or lint setup — read the
`Gemfile`, `.rubocop.yml`, `bin/`, and CI, and capture the exact command.

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
- Tests: `bundle exec rspec` (RSpec) **or** `bin/rails test` (+ `bin/rails test:system`) (Minitest) from the app root; `bin/rails db:test:prepare` first when the schema changed.
- Static: `bundle exec rubocop`, `bundle exec brakeman -q` (security scan), `bundle exec erb_lint --lint-all` where present; `bin/rails zeitwerk:check` as the autoload sanity check.

### 2. Scoped invocation
**RSpec** (documented example — Ruby is not available in the contributor environment): `bundle exec rspec spec/models/order_spec.rb` (file), `spec/models/order_spec.rb:42` (one example by line), `-e 'computes the total'` (by description), `--tag focus` / `--tag ~slow` (by metadata), `spec/models/` (directory). **Minitest**: `bin/rails test test/models/order_test.rb`, `test/models/order_test.rb:42`, `-n /total/` (name regex), `bin/rails test test/models` (directory). **Evidence:** RSpec's `N examples, 0 failures` / Minitest's `N runs, M assertions` — `N` non-zero.

### 3. Scoped static checks
- `bundle exec rubocop app/models/order.rb` (documented example) scopes natively to files/directories. `brakeman` and `zeitwerk:check` are app-wide by nature.

### 4. Source-to-test mapping
`spec/models/order_spec.rb` ↔ `app/models/order.rb`; `spec/requests/orders_spec.rb` ↔ `app/controllers/orders_controller.rb` + routes; `spec/services/…` ↔ `app/services/…`; system specs under `spec/system/`; Minitest mirrors under `test/`. Factories in `spec/factories/` (FactoryBot) or `test/fixtures/`.

### 5. Affected consumers
No native impact selector; reason from the model graph (associations, concerns, callbacks) and controllers/jobs that touch the model. **Blind spots:** callbacks and concerns (`include`) with no explicit call site, `config/routes.rb`, initializers, `config/*.yml`, migrations/`db/schema.rb`, views/partials/helpers, ActiveJob/Sidekiq jobs, `.env*`. A concern, initializer, routing or schema change affects many specs ⇒ the full run.

### 6. Escalation and fallback
Shared/core: `app/models/concerns/`, `app/controllers/concerns/`, `ApplicationRecord`/`ApplicationController`, `lib/`, shared services, `spec/support/`. Always full run: `Gemfile`/`Gemfile.lock`, `config/**`, `db/schema.rb`/migrations, `.rspec`/`spec_helper.rb`/`rails_helper.rb`, `.rubocop.yml`. **Fallback:** `bundle exec rubocop && bundle exec rspec` (or `bin/rails test`).

### 7. Layers and posture
Unit (model/service specs with minimal DB touch, PORO specs) — fast base; request specs as the integration layer for routing + controller + view; a few system specs (browser) for critical flows. Unit-first; keep system specs few.

### 8. Zero-selection behavior
RSpec prints `0 examples, 0 failures` and exits **0** when a filter matches nothing (documented) — a silent empty run; set `config.fail_if_no_examples = true` (RSpec ≥ 3.7) in `spec_helper.rb` or check the count. Minitest prints `0 runs` and exits **0** likewise — check the count. A wrong file path fails loudly (`cannot load such file`).
