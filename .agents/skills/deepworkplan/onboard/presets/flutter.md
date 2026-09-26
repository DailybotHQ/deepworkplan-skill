# Preset — Flutter (Dart)

> Reasoning aid, not a template. Verify against the live repo; detected reality
> wins. Capture the **real** validation command, not the example below.

## Signals that identify this stack

- `pubspec.yaml` at the repo root with `flutter:` under `dependencies` and an
  `sdk: flutter` line; `pubspec.lock` pins the resolved versions.
- `lib/main.dart` with a `void main() => runApp(...)` entry and a root widget
  (`MaterialApp`/`CupertinoApp`).
- Widgets extending `StatelessWidget`/`StatefulWidget`; `BuildContext`,
  `build()` methods.
- `analysis_options.yaml` (often `include: package:flutter_lints/flutter.yaml`
  or `package:lints/recommended.yaml`) — the analyzer/lint config.
- `test/` with `*_test.dart` files using `flutter_test` (`testWidgets`,
  `WidgetTester`); possibly `integration_test/` and `test/golden/` golden files.
- Platform folders: `android/`, `ios/`, and optionally `web/`, `macos/`,
  `linux/`, `windows/` (multi-platform target).

## What to look for in recon

- The **real** test command: `flutter test` (unit/widget) and any
  `flutter test integration_test/` or golden-test step. Test naming is
  `*_test.dart`. Capture verbatim.
- The **real** static-analysis gate: `flutter analyze` (or `dart analyze`)
  driven by `analysis_options.yaml`, plus `dart format --set-exit-if-changed .`.
- The **real** build target(s): `flutter build apk`/`appbundle`/`ipa`/`web` —
  which platforms ship, and any flavor/`--dart-define` config.
- **State management** if present: Provider (`provider`), Riverpod
  (`flutter_riverpod`, `@riverpod`), or Bloc (`flutter_bloc`, `Cubit`/`Bloc`).
  **Confirm which — it shapes the generated skills.**
- **Code generation** if present: `build_runner` with `json_serializable`,
  `freezed`, `riverpod_generator`, or `*.g.dart`/`*.freezed.dart` files →
  a `dart run build_runner build --delete-conflicting-outputs` step.

## Stack-specific skills/agents/commands to generate

- Skills: `widget` (widget + widget test), `screen`/`page` (route + screen),
  `model` (data class + `fromJson`/`toJson`, with codegen if `json_serializable`),
  and a state-shaped skill matching the library — `provider`/`riverpod-provider`/
  `bloc-feature`.
- Agents: baseline + a `widget-author` / `frontend-reviewer` persona aware of
  the widget tree, rebuild/`const` performance, and the chosen state pattern.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — widget/screen structure under `lib/`, the state-management
  approach, the data/repository layer, navigation, platform targets.
- `STANDARDS.md` — widget conventions (`const` constructors, composition over
  inheritance), file/feature layout, the analyzer ruleset.
- `TESTING_GUIDE.md` — `flutter_test` unit/widget tests, `WidgetTester` pumping,
  golden tests if used, the real `*_test.dart` pattern, mocking.
- Per-module docs: per feature folder under `lib/` (its widgets, screens,
  models, providers/blocs).

## Typical validation command (FIND the real one)

Commonly `flutter analyze && dart format --set-exit-if-changed . && flutter
test`, plus a `dart run build_runner build` step before tests if code
generation is used. **Do not assume** the state library, whether codegen runs,
or which platforms build — read `pubspec.yaml`, `analysis_options.yaml`, and CI
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
- Tests: `flutter test` (unit + widget, `test/**/*_test.dart`) from the package root; `flutter test integration_test/` on a device/emulator; `dart test` for pure-Dart packages; `dart run build_runner build --delete-conflicting-outputs` first when code generation is used.
- Static: `flutter analyze` (or `dart analyze`), `dart format --output=none --set-exit-if-changed .`.

### 2. Scoped invocation
**`flutter test` / `dart test`** (documented example — Flutter is not available in the contributor environment): `flutter test test/widgets/order_card_test.dart` (file), `flutter test test/widgets/` (directory), `flutter test --name 'computes total'` (regex on test names; `--plain-name` for a substring), `flutter test --tags golden` / `-x slow` (tags from `dart_test.yaml`), `flutter test integration_test/orders_test.dart -d <device>`; pure Dart: `dart test test/orders_test.dart`, `-N <name>`, `-t <tag>`. **Evidence:** the `+N` counter in the summary (`00:03 +12: All tests passed!`) — `N` non-zero.

### 3. Scoped static checks
- `dart analyze lib/widgets` and `dart format --output=none --set-exit-if-changed lib/widgets` (documented example) scope by path; `flutter analyze` runs the whole project (cheap). Generated code (`*.g.dart`, `*.freezed.dart`) must exist before analysis.

### 4. Source-to-test mapping
`test/` mirrors `lib/` (`lib/widgets/order_card.dart` ↔ `test/widgets/order_card_test.dart`); goldens under `test/golden/` (`matchesGoldenFile`); integration tests under `integration_test/`; packages in a melos/workspace monorepo keep their own `test/`.

### 5. Affected consumers
No native impact selector; reason from imports (`dart pub deps` for packages) and from provider/bloc consumers. **Blind spots:** code generation (`build_runner`, freezed, json_serializable, riverpod generators), assets and fonts in `pubspec.yaml`, localization (`l10n/*.arb`), platform channels (`android/`, `ios/` native code), theme/`MaterialApp` configuration, golden baselines (a rendering change fails goldens far from the edit). A theme, router, or shared provider change ⇒ the widget suite or the full run.

### 6. Escalation and fallback
Shared/core: `lib/core/`, `lib/theme/`, shared widgets, providers/blocs used app-wide, `lib/main.dart`, generated sources. Always full run: `pubspec.yaml`/`pubspec.lock`, `analysis_options.yaml`, `dart_test.yaml`, `build.yaml`, `l10n.yaml`, native platform config. **Fallback:** `flutter analyze && flutter test` (+ `flutter test integration_test/` where a device is available).

### 7. Layers and posture
Unit (pure Dart `test()` — no widgets) for models, services, blocs/notifiers — fast base; widget tests (`testWidgets`, `WidgetTester`) for behavior visible through the tree; golden tests deliberately (they are brittle); integration tests on a device for a few flows. Unit-first; keep goldens and integration few.

### 8. Zero-selection behavior
`package:test` (which `flutter test` and `dart test` use) reports `No tests ran.` and exits with a **non-zero** code (documented: exit code 79, `noTestsRan`) when a `--name`/`--tags` filter matches nothing — detectable; confirm on the target's SDK. A nonexistent path fails loudly. `flutter test integration_test/` with no device fails to start — not a pass.
