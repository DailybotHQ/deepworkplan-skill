# Preset — Spring Boot (Java / Kotlin)

> Reasoning aid, not a template. Verify every assumption against the live repo;
> detected reality wins. Capture the **real** validation command, not the
> example below.

## Signals that identify this stack

- Build manifest: `pom.xml` (Maven) **or** `build.gradle`/`build.gradle.kts`
  (Gradle), declaring `spring-boot-starter-parent` / the Spring Boot plugin and
  `spring-boot-starter-*` dependencies. **Infer the build tool from which file
  is present.**
- A wrapper: `./mvnw` (`.mvn/wrapper/`) or `./gradlew` (`gradle/wrapper/`) — use
  it, not a global Maven/Gradle.
- Source layout `src/main/java` (or `src/main/kotlin`) + `src/test/java`, and a
  `@SpringBootApplication`-annotated entrypoint with `SpringApplication.run(...)`.
- The layered stereotype model: `@RestController`/`@Controller`, `@Service`,
  `@Repository` (often Spring Data `JpaRepository`), `@Configuration`,
  `@Component`, with constructor injection.
- Config in `src/main/resources/application.yml` / `application.properties`,
  often with profile variants (`application-<profile>.yml`).

## What to look for in recon

- The **real** test command: `./mvnw test` (Maven Surefire/Failsafe) or
  `./gradlew test`, running JUnit 5 with Spring Boot Test
  (`@SpringBootTest`, `@WebMvcTest`, `@DataJpaTest`, `MockMvc`, Testcontainers).
  Capture the exact wrapper invocation.
- The **real** lint/format gate: Checkstyle, Spotless, PMD, SpotBugs, or
  ktlint/detekt (Kotlin) — and how it's invoked (`./mvnw verify`,
  `./gradlew check`, `spotlessApply`).
- Build tool specifics: Maven phases/profiles vs Gradle tasks; the full build
  command (`./mvnw verify` vs `./gradlew build`).
- Persistence layer: Spring Data JPA/JDBC, Hibernate, and the migration tool
  (Flyway `db/migration/V*.sql` or Liquibase changelogs).
- Configuration and secrets: active profiles (`SPRING_PROFILES_ACTIVE`),
  externalized config, and where secrets resolve from (env vars, Vault, config
  server).

## Stack-specific skills/agents/commands to generate

- Skills: `controller-add` (`@RestController` + request mapping + test),
  `service` (`@Service` business-logic bean + test), `repository` (Spring Data
  repository + entity), `entity` (`@Entity` + migration), optionally `migration`
  (Flyway/Liquibase) and `config-properties` (`@ConfigurationProperties`).
- Agents: baseline roles + an `api-reviewer` / `persistence-author` persona
  aware of transaction boundaries, layering, and migration safety.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — layering (controller → service → repository → entity),
  Spring context/bean wiring, transaction boundaries, REST surface.
- `TESTING_GUIDE.md` — JUnit 5 + Spring Boot Test slices (`@WebMvcTest` /
  `@DataJpaTest`), `MockMvc`, Testcontainers, how to scope a single test class
  with `-Dtest=` (Maven) or `--tests` (Gradle).
- `SECURITY.md` — Spring Security config, auth (JWT/OAuth2/sessions),
  externalized secrets, profile-based config.
- Per-module docs: one per domain/feature package (its controllers, services,
  repositories, entities).

## Typical validation command (FIND the real one)

Often `./mvnw verify` (Maven) or `./gradlew check` (Gradle) — which run tests
plus the lint/format/static-analysis gates. **Do not assume** the build tool or
goals — read `pom.xml`/`build.gradle`/CI and capture the exact wrapper command.

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
- Tests: `./mvnw test` (Surefire; `./mvnw verify` adds Failsafe integration tests) **or** `./gradlew test` (`./gradlew check` adds static checks) — always the wrapper, from the root or the module.
- Static: Checkstyle/Spotless/PMD/ktlint/detekt per the build file (`./mvnw checkstyle:check`, `./gradlew spotlessCheck`, `./gradlew ktlintCheck`), `./mvnw -q compile` / `./gradlew compileJava` as the compile gate.

### 2. Scoped invocation
**Maven** (documented example — not run in the contributor environment): `./mvnw -pl orders-service -am test -Dtest='OrderServiceTest'` (one module and what it needs; `-Dtest` accepts class names, `Class#method`, and patterns like `'Order*Test'`); `-Dit.test=` for Failsafe. **Gradle** (documented example): `./gradlew :orders-service:test --tests 'com.acme.orders.OrderServiceTest'` (or `--tests '*OrderService*'`; `--tests` accepts class/method patterns); `./gradlew :orders-service:test` for a module. **Evidence:** Surefire's `Tests run: N, Failures: 0` / Gradle's test report summary — `N` must be non-zero.

### 3. Scoped static checks
- Maven: `./mvnw -pl <module> checkstyle:check` / `spotless:check`; Gradle: `./gradlew :<module>:checkstyleMain`, `:<module>:spotlessCheck` (documented examples) — scoping is per **module**, not per file. Compilation is per module too (`-pl <module> -am`).

### 4. Source-to-test mapping
`src/test/java` mirrors `src/main/java` package by package (`OrderService` ↔ `OrderServiceTest`); `src/test/resources` holds test configs; integration tests named `*IT` (Failsafe convention) or under a Gradle `integrationTest` source set; multi-module builds keep tests inside each module.

### 5. Affected consumers
Module dependency graph from the build file (`./mvnw dependency:tree`, `./gradlew :<module>:dependencies`); run the changed module and its dependents (`-pl <mod> -amd` runs dependents with Maven). **Blind spots:** Spring auto-configuration and component scanning (a bean change affects consumers with no compile-time edge), `application*.yml`/profiles, `@ConfigurationProperties`, JPA entities/migrations (Flyway/Liquibase), AOP aspects, security filter chains, test slices' `@Import`s. A shared bean, security config or entity change ⇒ the module's `@SpringBootTest`s or the full run.

### 6. Escalation and fallback
Shared/core: `common`/`core` modules, security config, shared entities, base test classes. Always full run: `pom.xml`/`build.gradle*`, dependency BOMs/lockfiles, `application*.yml`, migrations, `checkstyle.xml`/spotless config, `Dockerfile`/testcontainers config. **Fallback:** `./mvnw verify` or `./gradlew check`.

### 7. Layers and posture
Unit (JUnit 5 + Mockito, no Spring context) for services and domain logic — fast base; slice tests (`@WebMvcTest`, `@DataJpaTest`) for one layer's wiring; `@SpringBootTest` (full context, often with Testcontainers) only for real seams — they are the slow, high-value integration layer; few e2e. Unit-first; keep the context-loading tests few.

### 8. Zero-selection behavior
Maven Surefire fails the build with `No tests were executed!` when `-Dtest` matches nothing (unless `-Dsurefire.failIfNoSpecifiedTests=false`) — detectable; a module with zero tests passes silently. Gradle fails with `No tests found for given includes` when `--tests` matches nothing — detectable. (Both documented; confirm on the target's plugin versions.)
