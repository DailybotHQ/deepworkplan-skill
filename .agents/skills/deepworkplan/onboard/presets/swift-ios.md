# Preset — Swift / iOS

> Reasoning aid, not a template. Verify against the live repo; detected reality
> wins. Capture the **real** validation command, not the example below.

## Signals that identify this stack

- An `*.xcodeproj` and/or `*.xcworkspace` at the repo root (a workspace usually
  means CocoaPods or multiple projects), and `*.swift` source files.
- **Dependency manager** — detect which:
  - `Package.swift` → **SwiftPM** (and `Sources/`, `Tests/` per the SPM layout).
  - `Podfile` + `Podfile.lock` → **CocoaPods** (open the `.xcworkspace`, run
    `pod install`).
  - `Cartfile` → **Carthage** (rarer).
  **Infer from the files present.**
- `*.xcodeproj/project.pbxproj` (targets, schemes), `Info.plist`, `*.entitlements`,
  and an `xcschemes` set under `*.xcodeproj/xcshareddata/`.
- **UI layer** — detect which:
  - SwiftUI: types conforming to `View`, a `body: some View`, `@State`/
    `@StateObject`/`@Observable`, an `App` struct with `@main`.
  - UIKit: `UIViewController`/`UIView` subclasses, `*.storyboard`/`*.xib`,
    `AppDelegate`/`SceneDelegate`.
  **Confirm SwiftUI vs UIKit — it changes nearly every screen-level skill.**
- Layout: `Sources/`/an app target folder with feature groups, `Models/`,
  `Views/`, `ViewModels/` (MVVM is common), `Resources/`, `Tests/`/`*Tests/`.

## What to look for in recon

- The **real** test command: `xcodebuild test -scheme <Scheme> -destination
  'platform=iOS Simulator,name=...'` (app projects) vs `swift test` (an SPM
  library). Tests use **XCTest** (`XCTestCase`, `func test...`) and possibly
  the newer **Swift Testing** (`import Testing`, `@Test`). **Confirm which.**
- The **real** lint/format gate: **SwiftLint** (`.swiftlint.yml`, `swiftlint`)
  and/or **swift-format** (`.swift-format`, `swift format lint`). Capture
  verbatim, and note if it runs as an Xcode build phase.
- The **real** build: `xcodebuild -scheme <Scheme> build` / `swift build`, the
  scheme and destination, and any `fastlane` lanes (`fastlane/Fastfile`) wrapping
  build/test/release.
- The dependency manager — it changes setup (`pod install` /
  `swift package resolve`) and whether you open the project or the workspace.
- Where signing/secrets live (provisioning profiles, `*.entitlements`, fastlane
  match, CI secrets) — flag, don't touch.

## Stack-specific skills/agents/commands to generate

- Skills: a UI-shaped skill matching the layer — `swiftui-view` (View +
  preview + test) or `uikit-screen` (view controller + test); `viewmodel`
  (if MVVM), `model` (Codable type + test), `service`/`networking-client`.
- Agents: baseline + a `swift-author` / `ios-reviewer` persona aware of the
  SwiftUI-vs-UIKit split, value-vs-reference types, optional handling, and
  concurrency (`async`/`await`, actors, `@MainActor`).
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — SwiftUI vs UIKit, the app/scene lifecycle, the
  architecture pattern (MVVM/TCA/MVC), navigation, the networking/data layer,
  the dependency manager.
- `STANDARDS.md` — Swift conventions (value types, optionals, access control,
  `async`/`await`), file/feature layout, the SwiftLint/swift-format ruleset.
- `TESTING_GUIDE.md` — XCTest (or Swift Testing), the scheme/destination to run,
  the real `*Tests.swift` pattern, mocking via protocols, UI tests if present.
- Per-module docs: per feature group (its views/view controllers, view models,
  models, services).

## Typical validation command (FIND the real one)

For an app project, commonly `swiftlint && xcodebuild test -scheme <Scheme>
-destination 'platform=iOS Simulator,name=iPhone 15'` (often wrapped in a
fastlane lane or a `Makefile`); for an SPM library, `swift build && swift
test`. **Do not assume** the dependency manager, the UI layer, the scheme, or
whether fastlane wraps it — read `Package.swift`/`Podfile`, the `*.xcodeproj`
schemes, any `Fastfile`, and CI, and capture the exact commands.

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
- Tests (app project): `xcodebuild test -scheme <Scheme> -destination 'platform=iOS Simulator,name=<device>'` from the project root (`-workspace`/`-project` as needed; `-resultBundlePath` for reports). Tests (SwiftPM library): `swift test`.
- Static: `swiftlint lint` (or `swiftlint --strict`), `swift-format lint -r Sources Tests` where adopted; `xcodebuild build` / `swift build` as the compile gate.

### 2. Scoped invocation
**`xcodebuild test`** (documented example — Xcode is not available in the contributor environment): `-only-testing:AppTests/OrderTests` (one class), `-only-testing:AppTests/OrderTests/testTotal` (one method), `-only-testing:AppTests` (one target), `-skip-testing:AppUITests` (exclude UI tests), `-testPlan <plan>` for configured subsets. **`swift test`** (documented example): `swift test --filter OrderTests` (regex on `Target.Class/method`, works for XCTest and Swift Testing), `--skip <regex>`, `swift test --parallel`. **Evidence:** `Executed N tests, with 0 failures` — `N` non-zero for the intended target.

### 3. Scoped static checks
- `swiftlint lint --path Sources/Orders` (or `swiftlint lint Sources/Orders` on newer versions) and `swift-format lint -r Sources/Orders` (documented examples) scope by path. Compilation is per target/scheme, not per file.

### 4. Source-to-test mapping
SwiftPM: `Tests/<Target>Tests/` mirrors `Sources/<Target>/` (`OrderService.swift` ↔ `OrderServiceTests.swift`); app projects: `<App>Tests/` grouped by feature, `<App>UITests/` for XCUITest. Test targets declare their dependencies explicitly in `Package.swift` / the project.

### 5. Affected consumers
SwiftPM: `swift package show-dependencies` and the `targets` graph in `Package.swift` — run the changed target's tests and the tests of targets that depend on it. **Blind spots:** storyboards/XIBs and asset catalogs, `Info.plist`, build settings and `.xcconfig`, schemes/test plans, SwiftUI previews, DI containers/environment values, localization (`.strings`/`.xcstrings`), `@testable import` visibility. A shared framework/package, xcconfig or scheme change ⇒ the full scheme's tests.

### 6. Escalation and fallback
Shared/core: shared packages/frameworks (`Core`, `Networking`, `DesignSystem`), app entry (`App.swift`/`AppDelegate`), DI setup. Always full run: `Package.swift`/`Package.resolved`, `project.pbxproj`, `.xcconfig`, schemes and test plans, `.swiftlint.yml`, `Podfile`/`Podfile.lock` where CocoaPods is used. **Fallback:** the full `xcodebuild test -scheme <Scheme> …` (or `swift test`) plus `swiftlint lint`.

### 7. Layers and posture
Unit (XCTest / Swift Testing on plain types, no simulator UI) for models, services, view models — fast base; integration for networking/persistence seams with protocol-based fakes; XCUITest for a few flows (slow; needs a simulator). Unit-first; keep UI tests few.

### 8. Zero-selection behavior
`swift test --filter <no-match>` reports `Executed 0 tests` and exits **0** (documented) — a silent empty run; check the count. `xcodebuild test -only-testing:` with an identifier that does not exist reports an error for that identifier — confirm the exit code on the target's Xcode version before relying on it.
