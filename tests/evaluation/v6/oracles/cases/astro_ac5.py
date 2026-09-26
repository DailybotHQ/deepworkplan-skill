#!/usr/bin/env python3
"""Outcome oracle for Astro pilot case AC-5 (seo-compat): canonical URLs,
RSS/sitemap integrity, and a permanent redirect from /posts/<slug>/ to
/blog/<slug>/.

Arm-blind by construction: score() receives a workspace directory (a copy of
the seed with whatever the actor did to it) and judges only the built
artifact — never arm labels, agent narration, or DWP files.

Contract reading (from tests/evaluation/v6/fixtures/astro/CASES.md, AC-5),
scored against the output of a disposable-copy build (`pnpm install
--frozen-lockfile --ignore-scripts`, `pnpm run build`, `pnpm run check` —
all three must succeed before any AC-5 assertion is evaluated):

1. Canonical URLs. Every built content page must carry at least one
   <link rel="canonical"> whose href resolves to the page's final route
   (site origin parsed from astro.config.mjs `site:`, plus the dist-derived
   path), compared modulo one trailing slash: Astro's default
   `trailingSlash: 'ignore'` makes both spellings the same route, so the
   oracle polices wrong-route canonicals, not slash pedantry. Pages that
   are themselves redirect stubs (contain <meta http-equiv="refresh">) are
   exempt: a stub's canonical belongs to its destination, matching Astro's
   own redirect-page template.
2. RSS integrity. dist/rss.xml must enumerate every built post
   (dist/blog/<slug>/index.html) and every RSS item link must be an
   absolute, same-origin URL that resolves to a built page — checked in
   both directions.
3. Sitemap integrity. dist/sitemap-index.xml must exist; the <loc> entries
   of the sitemap files it indexes must cover every built post, and every
   <loc> must resolve to a built file.
4. Redirect compatibility. For every post slug (seed slugs ∪ built slugs,
   so content deletion cannot fake a pass), /posts/<slug>/ must serve a
   redirect to /blog/<slug>/, evidenced in the built output by either:
     (a) a page at dist/posts/<slug>/index.html whose
         <meta http-equiv="refresh"> target resolves to /blog/<slug>/, or
     (b) a static-host redirect manifest shipped into dist (`_redirects`,
         `netlify.toml`, `vercel.json`) with an explicit permanent rule
         (301/308) mapping /posts/<slug>/ to /blog/<slug>/.
   A /posts/<slug>/ page that serves real content instead of a redirect
   fails. "Permanent" reading: a static build cannot evidence a wire-level
   301, so the meta-refresh page is accepted on destination match alone
   (it is Astro's documented static encoding of its `redirects` config,
   which carries 301 semantics wherever the output is served through that
   config), while a manifest rule must state the 301/308 status explicitly
   (the _redirects default differs between hosts, so an unqualified rule
   is not evidence of permanence). The CASES.md acceptance sentence itself
   tests only "serves a redirect to /blog/first-post/".

First audit (2026-09-26, seed at astro@7.3.5): the pristine seed ALREADY
satisfies clauses 1-3 — src/components/BaseHead.astro renders a canonical
link on every page and both feeds enumerate all five posts with resolving
URLs — so the genuinely-missing AC-5 work is clause 4 (no /posts/ routes
exist). Pristine therefore FAILs on the redirect alone and no substitute
case variant is needed. Consequence for the reference fix: the Astro-native
`redirects: {'/posts/[...slug]': '/blog/[...slug]'}` config is NOT a valid
solution here, because Astro's generated stub pages (see
node_modules/astro/dist/core/routing/3xx.js) ship without <html lang>, a
viewport meta, a meta description, or an h1 and would regress the standing
fixture-check contract. The reference below hand-authors compliant redirect
pages instead.

Self-calibration (python3 tests/evaluation/v6/oracles/cases/astro_ac5.py):
pristine seed -> FAIL, seed + apply() -> PASS, seed + sabotage() -> FAIL,
then prints CALIBRATION OK and exits 0 iff the matrix holds. The sabotage
variant is the plausible wrong repair of canonicalizing pages to the
retired /posts/ route.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlsplit

PASS, FAIL = "PASS", "FAIL"

SEED = Path(__file__).resolve().parents[5] / "tests/evaluation/v6/fixtures/astro/seed"

SITE_RE = re.compile(r"""site:\s*['"]([^'"]+)['"]""")
META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.I)
LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.I)
ATTR_RE = re.compile(r"""([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""")
REFRESH_URL_RE = re.compile(r"url\s*=\s*(.+?)\s*$", re.I)

# The reference redirect page: one dynamic route covering every post. It
# must satisfy the standing fixture-check contract (html lang, viewport,
# title, meta description, exactly one h1, resolving internal links) while
# carrying the meta refresh that evidence clause 4a reads.
REDIRECT_PAGE = """---
import { getCollection } from 'astro:content';

// AC-5: permanent redirect from the retired /posts/<slug>/ route to /blog/<slug>/.
export async function getStaticPaths() {
\tconst posts = await getCollection('blog');
\treturn posts.map((post) => ({
\t\tparams: { slug: post.id },
\t\tprops: { destination: `/blog/${post.id}/` },
\t}));
}

const { destination } = Astro.props;
---

<!doctype html>
<html lang="en">
\t<head>
\t\t<meta charset="utf-8" />
\t\t<meta name="viewport" content="width=device-width,initial-scale=1" />
\t\t<meta name="robots" content="noindex" />
\t\t<title>Redirecting to the new address</title>
\t\t<meta name="description" content={`This post has moved; redirecting to ${destination}.`} />
\t\t<meta http-equiv="refresh" content={`0;url=${destination}`} />
\t\t<link rel="canonical" href={destination} />
\t</head>
\t<body>
\t\t<main>
\t\t\t<h1>This post has moved</h1>
\t\t\t<p>
\t\t\t\tThe post now lives at <a href={destination}>{destination}</a>. You will be
\t\t\t\tredirected shortly.
\t\t\t</p>
\t\t</main>
\t</body>
</html>
"""

CANONICAL_SNIPPET = 'rel="canonical"'
CANONICAL_TEMPLATE_LINE = "const canonicalURL = new URL(Astro.url.pathname, Astro.site);"
CANONICAL_SABOTAGE_LINE = (
    "const canonicalURL = new URL(Astro.url.pathname.replace(/^\\/blog\\//, '/posts/'), Astro.site);"
)


# --------------------------------------------------------------- scoring


def score(root, seed_root):
    """Judge AC-5 on the workspace at `root`, rebuilding it in a disposable
    copy. `seed_root` is the immutable seed, used only to enumerate the post
    slugs the workspace is required to keep building."""
    reasons = []
    with tempfile.TemporaryDirectory(prefix="oracle-astro-ac5-") as td:
        work = Path(td) / "ws"
        # Fresh install/build from source: stale node_modules/.astro/dist in
        # the workspace can neither speed a fake pass nor leak into the score.
        shutil.copytree(root, work, symlinks=False,
                        ignore=shutil.ignore_patterns("node_modules", ".astro", "dist"))
        _build(work, reasons)
        if not reasons:
            dist = work / "dist"
            site = _site_origin(work, reasons)
            if site:
                pages, _stubs = _scan_html(dist)
                posts = _post_slugs(dist)
                _assert_seed_posts_built(seed_root, posts, reasons)
                _assert_canonicals(pages, site, reasons)
                _assert_rss(dist, site, posts, reasons)
                _assert_sitemap(dist, site, posts, reasons)
                _assert_redirects(dist, site, sorted(set(_seed_slugs(seed_root)) | set(posts)), reasons)
    return {"verdict": PASS if not reasons else FAIL, "reasons": reasons}


def _build(work, reasons):
    """Run the standing install/build/check contract in the disposable copy."""
    commands = (
        ("install", "pnpm install --frozen-lockfile --ignore-scripts", 1200),
        ("build", "pnpm run build", 1200),
        ("check", "pnpm run check", 300),
    )
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name, cmd, timeout in commands:
        try:
            proc = subprocess.run(cmd, shell=True, cwd=str(work), capture_output=True,
                                  text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            reasons.append(f"{name} timed out")
            return
        if proc.returncode != 0:
            reasons.append(f"{name} failed: {(proc.stdout + proc.stderr)[-400:]}")
            return


def _site_origin(work, reasons):
    config = work / "astro.config.mjs"
    match = SITE_RE.search(config.read_text(encoding="utf-8", errors="replace")) if config.is_file() else None
    if not match:
        reasons.append("cannot determine the site origin from astro.config.mjs")
        return None
    return match.group(1).rstrip("/")


def _attrs(tag_text):
    out = {}
    for m in ATTR_RE.finditer(tag_text):
        value = next(g for g in m.groups()[1:] if g is not None)
        out[m.group(1).lower()] = value
    return out


def _route_for(path, dist):
    rel = path.relative_to(dist).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel[: -len(".html")]


def _is_redirect_stub(html):
    for tag in META_TAG_RE.findall(html):
        attrs = _attrs(tag)
        if attrs.get("http-equiv", "").strip().lower() == "refresh":
            return True
    return False


def _refresh_target(html):
    for tag in META_TAG_RE.findall(html):
        attrs = _attrs(tag)
        if attrs.get("http-equiv", "").strip().lower() == "refresh":
            match = REFRESH_URL_RE.search(attrs.get("content", ""))
            if match:
                return match.group(1)
    return None


def _scan_html(dist):
    """Split built HTML into content pages and redirect stubs, keyed by route."""
    pages, stubs = {}, {}
    for path in sorted(dist.rglob("*.html")):
        route = _route_for(path, dist)
        html = path.read_text(encoding="utf-8", errors="replace")
        (stubs if _is_redirect_stub(html) else pages)[route] = html
    return pages, stubs


def _post_slugs(dist):
    blog = dist / "blog"
    if not blog.is_dir():
        return []
    return sorted(child.name for child in blog.iterdir()
                  if child.is_dir() and (child / "index.html").is_file())


def _seed_slugs(seed_root):
    blog = Path(seed_root) / "src" / "content" / "blog"
    if not blog.is_dir():
        return []
    return sorted(p.stem for p in blog.iterdir() if p.suffix in {".md", ".mdx"})


def _resolves(dist, path):
    clean = (path or "").rstrip("/")
    if not clean:
        return (dist / "index.html").is_file()
    base = dist / clean.lstrip("/")
    return base.is_file() or (base / "index.html").is_file() or base.with_name(base.name + ".html").is_file()


def _same_route(href, site, route):
    parts = urlsplit(urljoin(site + "/", href.strip()))
    want = urlsplit(urljoin(site + "/", route))
    if parts.scheme not in ("http", "https") or parts.query or parts.fragment:
        return False
    return (parts.netloc.lower() == want.netloc.lower()
            and parts.path.rstrip("/") == want.path.rstrip("/"))


def _assert_seed_posts_built(seed_root, posts, reasons):
    if not posts:
        reasons.append("no built post pages under dist/blog/")
    missing = set(_seed_slugs(seed_root)) - set(posts)
    for slug in missing:
        reasons.append(f"seed post no longer built: /blog/{slug}/")


def _assert_canonicals(pages, site, reasons):
    for route, html in pages.items():
        tags = [t for t in LINK_TAG_RE.findall(html)
                if _attrs(t).get("rel", "").strip().lower() == "canonical"]
        hrefs = [_attrs(t).get("href", "") for t in tags]
        if not hrefs:
            reasons.append(f"{route}: no canonical link")
            continue
        for href in hrefs:
            if not href or not _same_route(href, site, route):
                reasons.append(f"{route}: canonical {href or '(empty)'} does not match the final route")


def _local_elements(root, name):
    for element in root.iter():
        if isinstance(element.tag, str) and element.tag.rsplit("}", 1)[-1] == name:
            yield element


def _assert_rss(dist, site, posts, reasons):
    rss = dist / "rss.xml"
    if not rss.is_file():
        reasons.append("rss.xml missing")
        return
    try:
        root = ET.parse(rss).getroot()
    except ET.ParseError as exc:
        reasons.append(f"rss.xml unparseable: {exc}")
        return
    site_host = urlsplit(site).netloc.lower()
    feed_paths = set()
    links = [(item.findtext("{*}link") or "").strip() for item in _local_elements(root, "item")]
    if not links:
        reasons.append("rss.xml enumerates no items")
    for link in links:
        parts = urlsplit(link)
        if parts.scheme not in ("http", "https") or parts.netloc.lower() != site_host:
            reasons.append(f"rss item link is not a same-origin absolute URL: {link or '(empty)'}")
            continue
        if not _resolves(dist, parts.path):
            reasons.append(f"rss item link does not resolve in dist/: {link}")
        feed_paths.add(parts.path.rstrip("/"))
    for slug in posts:
        if f"/blog/{slug}".rstrip("/") not in feed_paths:
            reasons.append(f"built post missing from rss.xml: /blog/{slug}/")


def _assert_sitemap(dist, site, posts, reasons):
    if not (dist / "sitemap-index.xml").is_file():
        reasons.append("sitemap-index.xml missing")
    site_host = urlsplit(site).netloc.lower()
    locs = set()
    found = False
    for path in sorted(dist.glob("sitemap-*.xml")):
        if path.name == "sitemap-index.xml":
            continue
        found = True
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            reasons.append(f"{path.name} unparseable: {exc}")
            continue
        for element in _local_elements(root, "loc"):
            parts = urlsplit((element.text or "").strip())
            if parts.scheme not in ("http", "https") or parts.netloc.lower() != site_host:
                reasons.append(f"sitemap <loc> is not a same-origin absolute URL: {parts.path}")
            elif not _resolves(dist, parts.path):
                reasons.append(f"sitemap <loc> does not resolve in dist/: {parts.path}")
            locs.add(parts.path.rstrip("/"))
    if not found:
        reasons.append("no sitemap files with <loc> entries beside sitemap-index.xml")
    for slug in posts:
        if f"/blog/{slug}" not in locs:
            reasons.append(f"built post missing from the sitemap: /blog/{slug}/")


def _manifest_rules(dist, reasons):
    """Collect permanent-redirect rules from static-host manifests in dist.
    Returns a list of (source_pattern, destination_template, status)."""
    rules = []
    redirects_file = dist / "_redirects"
    if redirects_file.is_file():
        for raw in redirects_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) == 2:
                rules.append((parts[0], parts[1], None))
            elif len(parts) >= 3:
                rules.append((parts[0], parts[1], parts[2]))
    netlify_file = dist / "netlify.toml"
    if netlify_file.is_file():
        try:
            data = tomllib.loads(netlify_file.read_text(encoding="utf-8", errors="replace"))
            rules.extend((r.get("from", ""), r.get("to", ""), str(r.get("status", "")))
                         for r in data.get("redirects", []))
        except tomllib.TOMLDecodeError as exc:
            reasons.append(f"netlify.toml unparseable: {exc}")
    vercel_file = dist / "vercel.json"
    if vercel_file.is_file():
        try:
            data = json.loads(vercel_file.read_text(encoding="utf-8", errors="replace"))
            for r in data.get("redirects", []):
                status = r.get("statusCode") or (308 if r.get("permanent") else "")
                rules.append((r.get("source", ""), r.get("destination", ""), str(status)))
        except json.JSONDecodeError as exc:
            reasons.append(f"vercel.json unparseable: {exc}")
    return rules


def _manifest_redirect(rules, slug):
    """The destination of a permanent (301/308) rule covering /posts/<slug>/,
    or None. Unqualified rules are rejected: the _redirects default status
    differs per host, so only an explicit 301/308 evidences permanence."""
    sources = {f"/posts/{slug}", f"/posts/{slug}/", "/posts/:slug", "/posts/*"}
    for source, destination, status in rules:
        if source not in sources or not status:
            continue
        try:
            if int(status) not in (301, 308):
                continue
        except ValueError:
            continue
        return destination.replace(":splat", slug).replace(":slug", slug).replace("*", slug)
    return None


def _assert_redirects(dist, site, slugs, reasons):
    rules = _manifest_rules(dist, reasons)
    for slug in slugs:
        matched = False
        stub = dist / "posts" / slug / "index.html"
        if stub.is_file():
            target = _refresh_target(stub.read_text(encoding="utf-8", errors="replace"))
            if target and _same_route(target, site, f"/blog/{slug}/"):
                matched = True
        if not matched:
            destination = _manifest_redirect(rules, slug)
            if destination and _same_route(destination, site, f"/blog/{slug}/"):
                matched = True
        if not matched:
            detail = "serves a page without a redirect" if stub.is_file() else "serves no redirect"
            reasons.append(f"/posts/{slug}/ {detail} to /blog/{slug}/")


# ------------------------------------------------- reference + sabotage


def apply(workspace_root):
    """Minimal AC-5 reference fix. The seed already canonicalizes every page
    (BaseHead) and ships intact RSS/sitemap, so the missing clause is the
    /posts/<slug>/ -> /blog/<slug>/ redirect: one dynamic page per post that
    meta-refreshes to the new route while still satisfying the standing
    fixture-check contract."""
    base_head = workspace_root / "src" / "components" / "BaseHead.astro"
    text = base_head.read_text(encoding="utf-8")
    assert CANONICAL_SNIPPET in text, "AC-5 reference: seed lost its canonical head component"
    page = workspace_root / "src" / "pages" / "posts" / "[slug].astro"
    assert not page.exists(), "AC-5 reference: redirect page already present"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(REDIRECT_PAGE, encoding="utf-8")


def sabotage(workspace_root):
    """Plausible broken variant: the redirect lands, but canonicals are
    pointed at the retired /posts/ route — looks implemented, fails the
    canonical-matches-final-route contract."""
    apply(workspace_root)
    base_head = workspace_root / "src" / "components" / "BaseHead.astro"
    text = base_head.read_text(encoding="utf-8")
    assert CANONICAL_TEMPLATE_LINE in text, "AC-5 sabotage: canonical template line not found"
    base_head.write_text(text.replace(CANONICAL_TEMPLATE_LINE, CANONICAL_SABOTAGE_LINE, 1),
                         encoding="utf-8")


# -------------------------------------------------------- self-calibration


def _main():
    if not SEED.is_dir():
        print(f"seed fixture not found: {SEED}", file=sys.stderr)
        return 2
    matrix = {}
    with tempfile.TemporaryDirectory(prefix="calib-astro-ac5-") as td:
        base = Path(td)
        variants = (("pristine", None), ("known_good", apply), ("broken", sabotage))
        for name, operation in variants:
            work = base / name
            shutil.copytree(SEED, work, symlinks=False)
            if operation is not None:
                operation(work)
            matrix[name] = score(work, SEED)
    expected = {"pristine": FAIL, "known_good": PASS, "broken": FAIL}
    ok = True
    for name, want in expected.items():
        got = matrix[name]["verdict"]
        ok = ok and got == want
        print(f"{'OK  ' if got == want else 'FAIL'} astro-AC5 {name}: {got} (expected {want})")
        for reason in matrix[name]["reasons"]:
            print(f"       {name}: {reason}")
    print("CALIBRATION " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_main())
