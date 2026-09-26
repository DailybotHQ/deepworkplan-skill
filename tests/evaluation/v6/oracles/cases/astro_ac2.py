#!/usr/bin/env python3
"""Calibrated outcome oracle for Astro pilot case AC-2 (routing-urls).

AC-2 (tests/evaluation/v6/fixtures/astro/CASES.md): add tag archives at
/tags/<tag>/ with stable URLs linked from every post's tags, plus pagination
on /blog/ at 3 posts per page preserving post URLs. External acceptance
contract: built archive pages exist for existing tags; pagination pages link
both directions; no existing post URL changes; the fixture check contract
passes.

score(root, seed_root) is arm-blind by construction: it judges ONLY the
workspace artifact — it never sees arm labels, agent narration, or any .dwp
file. It copies the workspace into a disposable directory, runs the manifest
commands there (pnpm install --frozen-lockfile --ignore-scripts && pnpm run
build && pnpm run check), then asserts the AC-2 contract against the built
dist/:

  * every seed post URL /blog/<slug>/ still exists (URLs preserved);
  * every tag declared in the workspace's post frontmatter has a built
    /tags/<tag>/ archive that links back to its member posts;
  * every post page links to the archive of each of its own tags;
  * /blog/ shows exactly 3 of the seed's posts (3 per page), links a second
    pagination page under /blog/ that carries the remaining posts, and the
    pagination pages link back to /blog/ (both directions).

First audit (2026-09-26): the pristine seed does NOT satisfy AC-2 — the
blog schema has no `tags` field, no post carries tags, /blog/ lists all five
posts on a single page, and there is no src/pages/tags/ route — so the
public case stands unchanged; no substitute variant was needed. The
pristine=FAIL leg of the calibration matrix evidences this empirically.

reference.apply(workspace): the minimal real feature — a `tags` schema field
(z.array(z.string()).default([])), tags on all five seed posts, a new
src/pages/tags/[tag].astro archive route, BlogPost.astro rendering each
post's tags as /tags/<tag>/ links, and blog pagination via a new
src/pages/blog/[...page].astro (Astro paginate, pageSize 3; page 1 stays at
/blog/). The post route narrows [...slug].astro to [slug].astro so it does
not collide with the new rest route; post URLs are unchanged.

reference.sabotage(workspace): a plausible variant that LOOKS finished — it
moves the post route to src/pages/blog/post/[slug].astro and repoints every
internal link, so the site still builds and fixture-check still passes, but
every existing post URL changed (/blog/<slug>/ -> /blog/post/<slug>/),
which AC-2 explicitly forbids.

Calibration matrix (run `python3 tests/evaluation/v6/oracles/cases/astro_ac2.py`,
or a single leg with `... astro_ac2.py pristine|known_good|broken`):

    pristine seed        -> FAIL (the feature is absent)
    seed + apply()       -> PASS (the documented behavior holds)
    seed + sabotage()    -> FAIL (the URL regression is caught)

Prints "CALIBRATION OK" and exits 0 iff the whole matrix holds.
Self-contained: stdlib only, no imports from the shipped pack.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PASS, FAIL = "PASS", "FAIL"

# Tag assignments the reference implementation writes into the seed posts.
# Keys are file names under src/content/blog/.
REFERENCE_TAGS = {
    "first-post.md": ["astro", "beginners"],
    "second-post.md": ["astro", "tutorial"],
    "third-post.md": ["astro", "tutorial"],
    "markdown-style-guide.md": ["markdown", "tutorial"],
    "using-mdx.mdx": ["mdx", "tutorial"],
}

# Replacement for src/pages/blog/index.astro: the paginated blog index.
# The rest parameter keeps page 1 at /blog/ and emits /blog/2/ for page 2.
BLOG_PAGE_ASTRO = """---
import { Image } from 'astro:assets';
import { getCollection } from 'astro:content';
import BaseHead from '../../components/BaseHead.astro';
import Footer from '../../components/Footer.astro';
import FormattedDate from '../../components/FormattedDate.astro';
import Header from '../../components/Header.astro';
import { SITE_DESCRIPTION, SITE_TITLE } from '../../consts';

export async function getStaticPaths({ paginate }) {
	const posts = (await getCollection('blog')).sort(
		(a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf(),
	);
	// AC-2: paginate the blog index at 3 posts per page. The rest parameter
	// keeps page 1 at /blog/ and emits /blog/2/ for the following page.
	return paginate(posts, { pageSize: 3 });
}

const { page } = Astro.props;
---

<!doctype html>
<html lang="en">
	<head>
		<BaseHead title={SITE_TITLE} description={SITE_DESCRIPTION} />
		<style>
			main {
				width: 960px;
			}
			ul {
				display: flex;
				flex-wrap: wrap;
				gap: 2rem;
				list-style-type: none;
				margin: 0;
				padding: 0;
			}
			ul li {
				width: calc(50% - 1rem);
			}
			ul li * {
				text-decoration: none;
				transition: 0.2s ease;
			}
			ul li:first-child {
				width: 100%;
				margin-bottom: 1rem;
				text-align: center;
			}
			ul li:first-child img {
				width: 100%;
			}
			ul li:first-child .title {
				font-size: 2.369rem;
			}
			ul li img {
				margin-bottom: 0.5rem;
				border-radius: 12px;
			}
			ul li a {
				display: block;
			}
			.title {
				margin: 0;
				color: rgb(var(--black));
				line-height: 1;
			}
			.date {
				margin: 0;
				color: rgb(var(--gray));
			}
			ul li a:hover h4,
			ul li a:hover .title,
			ul li a:hover .date {
				color: rgb(var(--accent));
			}
			ul a:hover img {
				box-shadow: var(--box-shadow);
			}
			.pagination {
				display: flex;
				align-items: center;
				justify-content: space-between;
				margin-top: 2rem;
			}
			.pagination a {
				color: rgb(var(--black));
			}
			@media (max-width: 720px) {
				ul {
					gap: 0.5em;
				}
				ul li {
					width: 100%;
					text-align: center;
				}
				ul li:first-child {
					margin-bottom: 0;
				}
				ul li:first-child .title {
					font-size: 1.563em;
				}
			}
		</style>
	</head>
	<body>
		<Header />
		<main>
			<h1>All posts</h1>
			<section>
				<ul>
					{
						page.data.map((post) => (
							<li>
								<a href={`/blog/${post.id}/`}>
									{post.data.heroImage && (
										<Image width={720} height={360} src={post.data.heroImage} alt="" />
									)}
									<h2 class="title">{post.data.title}</h2>
									<p class="date">
										<FormattedDate date={post.data.pubDate} />
									</p>
								</a>
							</li>
						))
					}
				</ul>
			</section>
			<nav class="pagination" aria-label="Blog pages">
				{
					page.url.prev && (
						<a rel="prev" href={page.url.prev}>
							&laquo; Newer
						</a>
					)
				}
				<span>
					Page {page.currentPage} of {page.lastPage}
				</span>
				{
					page.url.next && (
						<a rel="next" href={page.url.next}>
							Older &raquo;
						</a>
					)
				}
			</nav>
		</main>
		<Footer />
	</body>
</html>
"""

# New archive route: one stable /tags/<tag>/ page per distinct tag.
TAG_PAGE_ASTRO = """---
import { getCollection } from 'astro:content';
import BaseHead from '../../components/BaseHead.astro';
import Footer from '../../components/Footer.astro';
import FormattedDate from '../../components/FormattedDate.astro';
import Header from '../../components/Header.astro';
import { SITE_TITLE } from '../../consts';

export async function getStaticPaths() {
	const posts = (await getCollection('blog')).sort(
		(a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf(),
	);
	// AC-2: one stable /tags/<tag>/ archive per distinct tag, listing the
	// posts that carry it.
	const tags = [...new Set(posts.flatMap((post) => post.data.tags))];
	return tags.map((tag) => ({
		params: { tag },
		props: {
			tag,
			posts: posts.filter((post) => post.data.tags.includes(tag)),
		},
	}));
}

const { tag, posts } = Astro.props;
---

<html lang="en">
	<head>
		<BaseHead
			title={`Posts tagged "${tag}" | ${SITE_TITLE}`}
			description={`All ${SITE_TITLE} posts tagged ${tag}, collected on one archive page.`}
		/>
		<style>
			main {
				width: 720px;
				max-width: calc(100% - 2em);
				margin: 0 auto;
			}
			ul {
				list-style-type: none;
				margin: 0;
				padding: 0;
			}
			ul li {
				margin-bottom: 1rem;
			}
			ul li a {
				text-decoration: none;
			}
			.title {
				margin: 0;
				color: rgb(var(--black));
			}
			.date {
				margin: 0;
				color: rgb(var(--gray));
			}
		</style>
	</head>
	<body>
		<Header />
		<main>
			<h1>Posts tagged &ldquo;{tag}&rdquo;</h1>
			<ul>
				{
					posts.map((post) => (
						<li>
							<a href={`/blog/${post.id}/`}>
								<h2 class="title">{post.data.title}</h2>
								<p class="date">
									<FormattedDate date={post.data.pubDate} />
								</p>
							</a>
						</li>
					))
				}
			</ul>
			<p>
				<a href="/blog/">All posts</a>
			</p>
		</main>
		<Footer />
	</body>
</html>
"""

# Rendered inside each post (BlogPost.astro), right after the title h1.
POST_TAGS_BLOCK = """{
							tags && tags.length > 0 && (
								<ul class="post-tags">
									{tags.map((t) => (
										<li>
											<a href={`/tags/${t}/`}>
												#{t}
											</a>
										</li>
									))}
								</ul>
							)
						}"""


def _result(verdict, reasons):
    return {"verdict": verdict, "reasons": reasons}


def _run(cmd, cwd, env=None, timeout=1200):
    return subprocess.run(cmd, shell=True, cwd=str(cwd), capture_output=True,
                          text=True, timeout=timeout)


def _frontmatter(path: Path) -> str:
    """Return the raw YAML frontmatter block body of a text file ('' if none)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def _parse_tags(fm: str):
    """Parse a `tags:` frontmatter key. Returns a list, or None when the key
    is absent. Accepts inline arrays (tags: [a, b]) and block lists."""
    inline = re.search(r"^tags:\s*\[(.*)\]\s*$", fm, re.M)
    if inline:
        items = [t.strip().strip("'\"") for t in inline.group(1).split(",")]
        return [t for t in items if t]
    if not re.search(r"^tags:\s*$", fm, re.M):
        return None
    tags = []
    in_block = False
    for line in fm.splitlines():
        if re.match(r"^tags:\s*$", line):
            in_block = True
            continue
        if in_block:
            item = re.match(r"^\s+-\s*(.+?)\s*$", line)
            if item:
                tags.append(item.group(1).strip("'\""))
            elif not line.strip():
                continue
            else:
                break
    return tags


def _post_files(root: Path) -> list:
    """(slug, path) pairs of a workspace's posts, derived from its content
    files. The slug is the route id under /blog/."""
    blog = root / "src" / "content" / "blog"
    out = []
    for path in sorted(blog.rglob("*")):
        if path.is_file() and path.suffix in (".md", ".mdx"):
            out.append((path.relative_to(blog).with_suffix("").as_posix(), path))
    return out


def _post_slugs(root: Path) -> list:
    return [slug for slug, _ in _post_files(root)]


def _hrefs(html: str) -> list:
    return re.findall(r'href="([^"]+)"', html)


def _resolve(dist: Path, href: str):
    """Map an absolute href to a built file under dist/, or None. The leading
    slash is stripped before joining: pathlib resets to an absolute path when
    a joined segment starts with '/', which would silently escape dist/."""
    rel = href.split("#")[0].split("?")[0]
    if not rel.startswith("/"):
        return None
    parts = rel.lstrip("/")
    direct = dist / parts
    if direct.is_file():
        return direct
    clean = parts.rstrip("/")
    if not clean:
        index = dist / "index.html"
        return index if index.is_file() else None
    as_index = dist / clean / "index.html"
    if as_index.is_file():
        return as_index
    as_file = dist / (clean + ".html")
    if as_file.is_file():
        return as_file
    return None


def _build_workspace(root: Path, work: Path, reasons: list, env_path=None):
    """Copy the workspace to a disposable directory and run the manifest
    commands (install/build/check) there. Returns the copy path, or None
    after recording a reason."""
    commands = [
        ("install", "pnpm install --frozen-lockfile --ignore-scripts"),
        ("build", "pnpm run build"),
        ("check", "pnpm run check"),
    ]
    env = dict(os.environ)
    if env_path:
        env["PATH"] = env_path
    shutil.copytree(root, work, symlinks=False)
    for name, cmd in commands:
        try:
            proc = _run(cmd, work, env=env)
        except subprocess.TimeoutExpired:
            reasons.append(f"{name} timed out")
            return None
        if proc.returncode != 0:
            reasons.append(f"{name} failed: {(proc.stdout + proc.stderr)[-400:]}")
            return None
    return work


def score(root: Path, seed_root: Path, env_path=None) -> dict:
    """Judge a workspace against the AC-2 acceptance contract (arm-blind)."""
    reasons = []
    with tempfile.TemporaryDirectory(prefix="oracle-astro-ac2-") as td:
        work = _build_workspace(root, Path(td) / "ws", reasons, env_path)
        if work is None:
            return _result(FAIL, reasons)
        dist = work / "dist"

        # No existing post URL changes: every seed post route still builds.
        seed_slugs = _post_slugs(seed_root)
        expected_paths = {f"/blog/{slug}" for slug in seed_slugs}
        for slug in seed_slugs:
            if not (dist / "blog" / slug / "index.html").is_file():
                reasons.append(f"existing post URL changed or missing: /blog/{slug}/")

        # Tag inventory of the workspace, parsed from its own frontmatter.
        post_tags = {}
        for slug, post_path in _post_files(root):
            tags = _parse_tags(_frontmatter(post_path))
            post_tags[slug] = tags if tags else []
        all_tags = sorted({t for tags in post_tags.values() for t in tags})
        if not all_tags:
            reasons.append("no post declares tags in its frontmatter; the tag-archive feature is absent")

        # Built archive pages exist for existing tags and list their posts.
        for tag in all_tags:
            archive = dist / "tags" / tag / "index.html"
            if not archive.is_file():
                reasons.append(f"tag archive page missing: /tags/{tag}/")
                continue
            archive_hrefs = _hrefs(archive.read_text(encoding="utf-8", errors="replace"))
            archive_targets = {h.rstrip("/") for h in archive_hrefs}
            for slug, tags in post_tags.items():
                if tag in tags and f"/blog/{slug}" not in archive_targets:
                    reasons.append(f"/tags/{tag}/ does not link to its post /blog/{slug}/")

        # Every post links to the archive of each of its own tags.
        for slug, tags in post_tags.items():
            page = dist / "blog" / slug / "index.html"
            if not page.is_file():
                continue  # already reported as a changed/missing post URL
            targets = {h.rstrip("/") for h in _hrefs(page.read_text(encoding="utf-8", errors="replace"))}
            for tag in tags:
                if f"/tags/{tag}" not in targets:
                    reasons.append(f"/blog/{slug}/ does not link to its tag archive /tags/{tag}/")

        # Pagination on /blog/ at 3 posts per page, linked both directions.
        blog_index = dist / "blog" / "index.html"
        if not blog_index.is_file():
            reasons.append("built /blog/ index missing")
        else:
            index_hrefs = _hrefs(blog_index.read_text(encoding="utf-8", errors="replace"))
            first_page = {h.rstrip("/") for h in index_hrefs} & expected_paths
            if len(first_page) != 3:
                reasons.append(
                    f"expected exactly 3 seed posts on the first /blog/ page (3 posts per page), found {len(first_page)}")
            # Follow the pagination pages linked from /blog/ (links under
            # /blog/ that are neither the index nor a seed post page).
            pagination_pages = []
            for href in index_hrefs:
                if not href.startswith("/blog"):
                    continue
                clean = href.rstrip("/")
                if clean == "/blog" or clean in expected_paths:
                    continue
                target = _resolve(dist, href)
                if target is None or target == blog_index:
                    continue
                try:
                    target.relative_to(dist / "blog")
                except ValueError:
                    continue
                pagination_pages.append(target)
            covered = set(first_page)
            back_link = False
            if not pagination_pages:
                reasons.append("no second pagination page is linked from /blog/ "
                               "(5 posts at 3 per page need one)")
            for target in pagination_pages:
                target_hrefs = _hrefs(target.read_text(encoding="utf-8", errors="replace"))
                covered |= {h.rstrip("/") for h in target_hrefs} & expected_paths
                if any(h.rstrip("/") == "/blog" for h in target_hrefs):
                    back_link = True
            missing = expected_paths - covered
            if missing:
                reasons.append(f"posts not reachable across /blog/ pagination pages: {sorted(missing)}")
            if pagination_pages and not back_link:
                reasons.append("pagination pages do not link back to /blog/ (both directions required)")

    return _result(PASS if not reasons else FAIL, reasons)


# ------------------------------------------------------- reference variants

def apply(workspace_root: Path) -> None:
    """Minimal real AC-2 implementation on a workspace copy: tags schema
    field, tags on the posts, /tags/<tag>/ archives, per-post tag links, and
    /blog/ pagination at 3 posts per page — post URLs unchanged."""
    # 1. Schema: optional tags list, defaulting to empty.
    schema = workspace_root / "src" / "content.config.ts"
    text = schema.read_text(encoding="utf-8")
    if "tags:" not in text:
        anchor = "\t\t\theroImage: z.optional(image()),"
        assert anchor in text, "schema anchor not found"
        text = text.replace(
            anchor, anchor + "\n\t\t\t// AC-2: post tags, used to build /tags/<tag>/ archives."
                    + "\n\t\t\ttags: z.array(z.string()).default([]),", 1)
        schema.write_text(text, encoding="utf-8")

    # 2. Frontmatter: tags on every seed post.
    blog = workspace_root / "src" / "content" / "blog"
    for name, tags in REFERENCE_TAGS.items():
        post = blog / name
        assert post.is_file(), f"expected seed post missing: {name}"
        text = post.read_text(encoding="utf-8")
        if "\ntags:" in text:
            continue
        fm_end = text.find("\n---", 3)
        assert fm_end != -1, f"no frontmatter fence in {name}"
        block = "".join(f"  - {t}\n" for t in tags)
        text = text[:fm_end] + "\ntags:\n" + block + text[fm_end:]
        post.write_text(text, encoding="utf-8")

    # 3. Blog pagination: index.astro becomes [...page].astro (page 1 stays
    #    at /blog/), and the post route narrows [...slug] to [slug] so the
    #    two rest routes cannot collide and post URLs stay identical.
    pages = workspace_root / "src" / "pages" / "blog"
    if not (pages / "[...page].astro").is_file():
        assert (pages / "index.astro").is_file(), "seed blog index missing"
        (pages / "[...page].astro").write_text(BLOG_PAGE_ASTRO, encoding="utf-8")
        (pages / "index.astro").unlink()
        slug_route = pages / "[...slug].astro"
        if slug_route.is_file():
            (pages / "[slug].astro").write_text(slug_route.read_text(encoding="utf-8"), encoding="utf-8")
            slug_route.unlink()

    # 4. Tag archive route.
    tags_dir = workspace_root / "src" / "pages" / "tags"
    tags_dir.mkdir(exist_ok=True)
    (tags_dir / "[tag].astro").write_text(TAG_PAGE_ASTRO, encoding="utf-8")

    # 5. Post pages render each post's tags as links to its archives.
    layout = workspace_root / "src" / "layouts" / "BlogPost.astro"
    text = layout.read_text(encoding="utf-8")
    if 'class="post-tags"' not in text:
        old_props = "const { title, description, pubDate, updatedDate, heroImage } = Astro.props;"
        new_props = "const { title, description, pubDate, updatedDate, heroImage, tags } = Astro.props;"
        assert old_props in text, "layout props anchor not found"
        text = text.replace(old_props, new_props, 1)
        anchor = "<h1>{title}</h1>"
        assert anchor in text, "layout title anchor not found"
        text = text.replace(anchor, anchor + "\n\t\t\t\t\t\t" + POST_TAGS_BLOCK, 1)
        style_anchor = "\t\t\t.last-updated-on {"
        assert style_anchor in text, "layout style anchor not found"
        style_block = ("\t\t\t.post-tags {\n"
                       "\t\t\t\tdisplay: flex;\n"
                       "\t\t\t\tgap: 0.75rem;\n"
                       "\t\t\t\tlist-style-type: none;\n"
                       "\t\t\t\tmargin: 1em 0;\n"
                       "\t\t\t\tpadding: 0;\n"
                       "\t\t\t}\n")
        text = text.replace(style_anchor, style_block + style_anchor, 1)
        layout.write_text(text, encoding="utf-8")


def sabotage(workspace_root: Path) -> None:
    """Broken variant that still builds and passes fixture-check: a plausible
    route refactor moves every post to /blog/post/<slug>/ and repoints all
    internal links — but the existing post URLs changed, which AC-2 forbids."""
    apply(workspace_root)
    blog = workspace_root / "src" / "pages" / "blog"
    post_dir = blog / "post"
    post_dir.mkdir(exist_ok=True)
    if not (post_dir / "[slug].astro").is_file():
        slug_route = blog / "[slug].astro"
        assert slug_route.is_file(), "sabotage expects the [slug] post route from apply()"
        text = slug_route.read_text(encoding="utf-8")
        text = text.replace("'../../layouts/BlogPost.astro'", "'../../../layouts/BlogPost.astro'", 1)
        (post_dir / "[slug].astro").write_text(text, encoding="utf-8")
        slug_route.unlink()
    for rel in ("[...page].astro",):
        page_path = blog / rel
        page_path.write_text(
            page_path.read_text(encoding="utf-8").replace("/blog/${post.id}/", "/blog/post/${post.id}/"),
            encoding="utf-8")
    tag_page = workspace_root / "src" / "pages" / "tags" / "[tag].astro"
    tag_page.write_text(
        tag_page.read_text(encoding="utf-8").replace("/blog/${post.id}/", "/blog/post/${post.id}/"),
        encoding="utf-8")


# ------------------------------------------------------------- calibration

def _seed_dir() -> Path:
    return Path(__file__).resolve().parents[5] / "tests" / "evaluation" / "v6" / "fixtures" / "astro" / "seed"


def run_variant(seed: Path, variant: str, base: Path) -> dict:
    """Materialize one calibration variant and score it."""
    work = base / variant
    shutil.copytree(seed, work, symlinks=False)
    if variant == "known_good":
        apply(work)
    elif variant == "broken":
        sabotage(work)
    return score(work, seed)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    seed = _seed_dir()
    if not seed.is_dir():
        print(f"seed fixture not found: {seed}", file=sys.stderr)
        return 2
    expected = {"pristine": "FAIL", "known_good": "PASS", "broken": "FAIL"}
    variants = [v for v in expected if not argv or v in argv]
    results = {}
    with tempfile.TemporaryDirectory(prefix="calib-astro-ac2-") as td:
        for variant in variants:
            result = run_variant(seed, variant, Path(td))
            results[variant] = result
            print(f"{variant}: {result['verdict']}", flush=True)
            for reason in result["reasons"]:
                print(f"  - {reason}", flush=True)
    ok = all(results[v]["verdict"] == expected[v] for v in variants)
    print("CALIBRATION " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
