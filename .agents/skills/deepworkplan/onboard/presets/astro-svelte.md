# Preset — Astro (+ Svelte) site

> Reasoning aid, not a template. Verify against the live repo; detected reality
> wins. Capture the **real** validation command, not the example below.

## Signals that identify this stack

- `astro.config.mjs`/`astro.config.ts` and `astro` in `package.json` deps.
- UI integration islands: `@astrojs/svelte` + `.svelte` files (or
  `@astrojs/react`/`@astrojs/vue` — adapt the island-component skill to whichever
  is present). Tailwind via `@astrojs/tailwind`.
- Content collections: a `src/content/` folder with a `config.ts` defining
  collections (blog, docs); MDX via `@astrojs/mdx`.
- Layout: `src/pages/` (file-based routing), `src/components/`, `src/layouts/`,
  `src/content/`, `public/`.
- Package manager from the lockfile (pnpm/yarn/npm) — infer from what's present.

## What to look for in recon

- The **real** scripts: `astro check` (type/diagnostics), the lint/format gate
  (frequently **Biome** — `biome:check` — rather than ESLint+Prettier; confirm),
  `build` (`astro build`), `dev`/`preview`.
- Whether tests exist at all (static sites often have few/none — note it and
  treat `astro check` + `build` as the validation gate). Playwright for E2E if
  present.
- Content collections + their schemas (drives `content`/`blog` skills and a
  content-collection-aware doc emphasis).
- Deployment: static output vs SSR adapter (Vercel/Netlify/node) — informs
  `ARCHITECTURE.md` and `PERFORMANCE.md`.

## Stack-specific skills/agents/commands to generate

- Skills: `content`/`blog` (add a content-collection entry per its schema),
  `component` (Astro or island component), `collection` (define a new content
  collection), `page`/`route`.
- Agents: baseline + a `content-author` / `frontend-reviewer` persona aware of
  content-collection schemas and SEO/performance.
- Commands: the five DWP commands + `code-review`, `pr`, `commit`.

## Doc emphases

- `ARCHITECTURE.md` — file-based routing, content collections + schemas, island
  architecture, static-vs-SSR output, the asset pipeline.
- `PERFORMANCE.md` — important for a marketing/static site: bundle size, image
  optimization, Lighthouse/Core Web Vitals budgets.
- `STANDARDS.md` — content frontmatter conventions, component boundaries,
  Tailwind usage.
- Per-module docs: per content collection and per major component area.

## Typical validation command (FIND the real one)

Often `pnpm run astro check && pnpm run build`, sometimes preceded by a Biome
gate `pnpm run biome:check`. **Do not assume** — read `package.json`/CI and
capture the exact commands.

## Testing and validation (verified vs example)

The uniform section every preset carries (`README.md` → "The testing section
every preset carries"). Everything below is an **illustrative example until it
is verified against the target repository** in Phase 1 — run the scoped example
on a real path and record the selected/executed count. Items marked *reference
run* were verified once in this skill's contributor environment with the tool
version stated; the target repo's version may differ, so re-verify.

### 1. Full commands
- Tests (when present): `pnpm vitest run` (or `pnpm test`) from the repo root; e2e: `pnpm playwright test`.
- Static: `pnpm exec biome check .` (or `pnpm run biome:check`; if ESLint+Prettier instead, `pnpm eslint .` and `pnpm prettier --check .`), `pnpm astro check`, `pnpm astro build`.
- Static sites often have few unit tests; then `astro check` + `build` (+ Biome) is the full gate — say so in `TESTING_GUIDE.md` rather than pretending a suite exists.

### 2. Scoped invocation
**Vitest** (reference run — vitest 5.0.0, contributor environment):
`vitest run <file>` selects exactly that file (`Test Files 1 passed`); `vitest run <dir>` selects the directory; `vitest run -t "<name>"` filters by test name; `vitest run --project <name>` selects a workspace project. **Evidence of a correct run:** the `Test Files N passed (N)` line — check `N` is what you expected.
**Zero-selection behavior (verified):** a path filter that matches nothing prints `No test files found` and exits **1** (detectable); a `-t` name filter that matches nothing exits **0** with every test *skipped* (`Test Files 8 skipped`) — a silent empty run. Never accept `-t` without confirming a non-zero passed count.

**Playwright** (flags verified against `@playwright/test@1.63 test --help`): `playwright test <file>`, `-g "<title>"`, `--project <name>`, `--only-changed [ref]` (impact via git). `No tests found` is reported when a filter matches nothing — confirm the exit code in the target repo before trusting it in a gate.

### 3. Scoped static checks
- **Biome** (reference run — biome 2.5.12): `biome check <path>` scopes to files/directories (`Checked 1 file`); a nonexistent path exits **1**. Verified.
- **ESLint/Prettier** (example): `eslint <path>`, `prettier --check <path>`.
- **`astro check`** (verified help: only `--root` / `--tsconfig`): project-wide, no path filter. Type-check is **project-wide by design**: `tsc --noEmit` reads `tsconfig.json`; `tsc <file>` ignores the project config and is *not* a sound scoped check. Do not fabricate a per-file variant — a single project-wide run is the real (and usually cheap) option.

### 4. Source-to-test mapping
Co-located `*.test.ts` next to source, or a mirrored `tests/unit/<area>/` tree (this skill's own website uses `tests/unit/lib/` mirroring `src/lib/`). Content collections and `.astro` templates are usually covered by `astro check` + `build`, not unit tests — record which.

### 5. Affected consumers
`vitest run --changed <ref>` selects tests whose import graph touches changed files (git-based). **Blind spots:** `.astro`/`.svelte` islands rendered by the build, content-collection schemas (`src/content.config.ts`), MDX, `astro.config.*`, Tailwind config, `public/` assets and env files — none are visible to the import graph. For these, `astro check` + `astro build` is the affected check.

### 6. Escalation and fallback
Shared/core: `src/layouts/`, `src/lib/`, shared components, i18n/translation modules, the content-collection schema. Always full run: `astro.config.*`, `src/content.config.ts`, `tsconfig.json`, `package.json`/lockfile, `biome.json`/ESLint config, Tailwind config, `.env*`. **Fallback:** `pnpm vitest run && pnpm astro check && pnpm astro build` (plus Biome).

### 7. Layers and posture
Unit (Vitest) for `src/lib/` and pure helpers — the fast base; component tests where islands carry logic; `astro check` + `build` as the integration seam for templates/collections; Playwright for a few high-value pages (navigation, forms, i18n switch). Unit-first; no ratio quota.

### 8. Zero-selection behavior
See the Vitest and Playwright notes in §2. `astro check` and `astro build` have no selection and therefore no empty run.
