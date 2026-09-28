# Astro fixture — public development cases and mechanism taxonomy

Public material, visible to every arm and to the v6 implementer. Sealed
confirmation variants are authored by the restricted custodian from this
taxonomy; the implementer neither authors nor inspects them (preregistration,
`isolation`). Repeated copies of one mechanism are repeats, not new cases.

## Mechanism taxonomy (the axis sealed variants vary along)

| Mechanism | What it exercises |
| --- | --- |
| content-schema | typed content collection changes and their blast radius |
| routing-urls | route generation, pagination, stable URLs, redirects |
| search-client | client-side behavior over static content, empty/error states |
| i18n-locale | locale-aware routes, links, dates, fallbacks |
| seo-compat | canonical, RSS/sitemap integrity, redirect compatibility |
| a11y-keyboard | focus order, keyboard operability, semantic contracts |
| responsive-perf | layout adaptation, image/loading behavior under constraints |
| regression-detect | a defect whose user consequence the check contract must catch |

## Public development cases

| ID | Mechanism | Size | Objective (human-readable) | External acceptance contract (what an independent scorer verifies) |
| --- | --- | --- | --- | --- |
| AC-1 | content-schema | small | Add an optional `readingTime` field to the blog schema and render it on post pages without breaking any existing post's build. | `npm run build` and `npm run check` pass; every existing post page renders; a post with the field shows it, posts without it render cleanly. |
| AC-2 | routing-urls | medium | Add tag archives at `/tags/<tag>/` with stable URLs linked from every post's tags, plus pagination on `/blog/` at 3 posts per page preserving post URLs. | Built archive pages exist for existing tags; pagination pages link both directions; no existing post URL changes; `npm run check` passes. |
| AC-3 | search-client | medium | Add a small client-side search box on `/blog/` filtering post titles, with a useful empty state. | Built page contains the search control and data; filtering behavior is verifiable in the served DOM; empty query and no-match states render human-readable text. |
| AC-4 | i18n-locale | large | Add an `/es/` locale tree: landing and blog index translated, locale switcher in the nav, English fallbacks for untranslated routes. | `/es/` and `/es/blog/` render Spanish pages; switcher links resolve both directions; untranslated content falls back without broken links; `npm run check` passes on both locales. |
| AC-5 | seo-compat | medium | Give every page a canonical URL and preserve RSS/sitemap integrity; add a permanent redirect from `/posts/<slug>/` to `/blog/<slug>/`. | Canonicals match final routes; RSS and sitemap enumerate built posts with resolving URLs; `/posts/first-post/` serves a redirect to `/blog/first-post/`. |
| AC-6 | a11y-keyboard | medium | Add a visible skip-to-content link and make the nav fully keyboard-operable with a visible focus style. | Skip link is the first focusable element and moves focus to main; every nav item is reachable and operable by keyboard; focus style is visible in built CSS. |
| AC-7 | responsive-perf | medium | Make the landing hero stack cleanly at 360px width and size the largest image lazily without layout shift. | Built CSS contains the narrow-viewport rules; below-fold images carry lazy loading and explicit dimensions; `npm run check` passes. |
| AC-8 | regression-detect | small | (Dev-only discriminating case, pre-seeded defect variant) A broken internal link is introduced on the About page. | The standard check contract must FAIL on the seeded defect — proving the checks discriminate; the repair restores a pass. |

## Fairness notes

- The acceptance intent above is public; hidden scoring variants change the
  specific mechanism instance, never the public contract (preregistration
  rule: hidden checks test public acceptance intent, not surprise
  requirements).
- Every arm receives the same seed, the same `manifest.json` commands and the
  same check contract. No arm gets fixture-specific hints.
