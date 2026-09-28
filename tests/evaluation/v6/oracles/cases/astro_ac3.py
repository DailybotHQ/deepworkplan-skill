#!/usr/bin/env python3
"""Arm-blind outcome oracle for Astro pilot case AC-3 (client-side search).

AC-3 public acceptance contract (tests/evaluation/v6/fixtures/astro/CASES.md):
"Built page contains the search control and data; filtering behavior is
verifiable in the served DOM; empty query and no-match states render
human-readable text."

Like the shared oracles module, this oracle judges ONLY the artifact: it
receives a workspace directory (a copy of the seed with whatever the actor
did to it) plus the pristine seed root (used solely to know which post titles
the fixture ships), and never sees arm labels, agent narration, or .dwp
files. Adding a `.dwp/` directory cannot change a score.

The module is self-contained and stdlib-only: the build helper mirrors
`oracles.py::_astro_build_and_check` because oracles.py is a shared pilot
file this module must not import (and must not edit).

First-audit result (2026-09-26, documented per pilot protocol): the pristine
seed does NOT already satisfy AC-3 — no page in the seed contains an <input>
element, and no src file contains `addEventListener`; the only "input" hit in
the seed is a CSS rule in `src/styles/global.css`. The seed therefore stands
as the baseline and no re-authored missing variant was needed.

Contract interpretation (static analysis of the built DOM; no headless
browser is available to the oracle, so behavior is verified by construction
of the served page):

1. `pnpm install --frozen-lockfile --ignore-scripts`, `pnpm run build` and
   `pnpm run check` pass on a disposable copy of the workspace (the seed's
   manifest.json command contract).
2. The built `/blog/index.html` exists.
3. Search control: the page contains an `<input>` whose type is search,
   text, or unset.
4. Data embedded: every seed post title appears in the built page (as
   rendered text, a data-* attribute, or an embedded data island) AND
   outside `<script>` bodies — the server-rendered listing doubles as the
   human-readable empty-query state, which also keeps the page useful
   without JavaScript.
5. Filtering verifiable in the served DOM: the page's script corpus (inline
   scripts, locally bundled JS files referenced by the page, and inline
   `on*=` handler values) must (a) reference the search input by one of its
   identifying tokens (id/name/class/data-*) or select `<input>` elements
   generically, (b) attach an event listener (input/change/keyup/... or an
   `oninput=`-style attribute), and (c) combine a query-matching primitive
   (includes/indexOf/test/...) with a result-visibility primitive
   (hidden/display/classList/...).
6. No-match state: a human-readable no-match message is present in the
   served HTML or in the script corpus (the string the client renders when
   zero posts match), or the page carries a no-results/empty-state element
   whose content is human-readable text.

Known limits (documented honestly): this is presence-based static analysis
of the built DOM, not a live interaction test; a page could theoretically
satisfy the shape assertions while a runtime bug escapes them. The matrix
below (pristine FAIL / reference PASS / sabotage FAIL) is the calibration
evidence for how discriminating the shape is in practice.

Usage:
    python3 tests/evaluation/v6/oracles/cases/astro_ac3.py

    Runs the calibration matrix pristine=FAIL / apply=PASS / sabotage=FAIL,
    prints CALIBRATION OK, and exits 0 iff the matrix holds.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

PASS, FAIL = "PASS", "FAIL"

# --------------------------------------------------------------- build step


def _astro_build_and_check(root: Path, work: Path, reasons: list, env_path=None) -> bool:
    """Build `root` into the caller-provided empty directory `work`.

    The caller owns `work`'s lifetime (a TemporaryDirectory held open for the
    whole scoring pass) so dist/ stays readable after this function returns —
    returning a path out of a TemporaryDirectory context would hand back an
    already-deleted tree. Commands come from the seed's manifest.json.
    """
    commands = {
        "install": "pnpm install --frozen-lockfile --ignore-scripts",
        "build": "pnpm run build",
        "check": "pnpm run check",
    }
    env = dict(os.environ)
    if env_path:
        env["PATH"] = env_path
    shutil.copytree(root, work, symlinks=False)
    for name, cmd in commands.items():
        try:
            proc = subprocess.run(cmd, shell=True, cwd=str(work), capture_output=True,
                                  text=True, timeout=1200, env=env)
        except subprocess.TimeoutExpired:
            reasons.append(f"{name} timed out")
            return False
        if proc.returncode != 0:
            reasons.append(f"{name} failed: {(proc.stdout + proc.stderr)[-400:]}")
            return False
    return True


# ------------------------------------------------------- fixture inspection


def _seed_titles(seed_root: Path) -> list:
    """Post titles the immutable seed ships (the data the search must cover)."""
    titles = []
    content = seed_root / "src" / "content" / "blog"
    for path in sorted(content.iterdir()):
        if path.suffix not in (".md", ".mdx"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        front = re.match(r"^---\s*\n(.*?)\n---", text, flags=re.S)
        block = front.group(1) if front else text
        hit = re.search(r"^title:\s*(.+?)\s*$", block, flags=re.M)
        if hit:
            value = hit.group(1).strip().strip("\"'")
            if value:
                titles.append(value)
    return titles


# ------------------------------------------------------------ page analysis


def _strip_comments(html: str) -> str:
    return re.sub(r"<!--.*?-->", " ", html, flags=re.S)


def _strip_scripts(html: str) -> str:
    return re.sub(r"<script\b.*?</script>", " ", html, flags=re.S | re.I)


def _search_inputs(html: str) -> list:
    """<input> tags that can plausibly act as a text search control."""
    controls = []
    for tag in re.findall(r"<input\b[^>]*>", html, flags=re.I):
        hit = re.search(r'\btype\s*=\s*["\']([^"\']*)["\']', tag, flags=re.I)
        itype = (hit.group(1) if hit else "text").lower()
        if itype in ("", "text", "search"):
            controls.append(tag)
    return controls


def _input_tokens(tag: str) -> set:
    """Identifying tokens a script would use to reach this input."""
    tokens = set()
    for attr in ("id", "name", "class"):
        hit = re.search(rf'\b{attr}\s*=\s*["\']([^"\']*)["\']', tag, flags=re.I)
        if hit:
            tokens.update(w for w in re.split(r"\s+", hit.group(1)) if len(w) >= 3)
    for hit in re.finditer(r'\b(data-[a-z0-9-]+)\s*=\s*["\']?([^"\'\s>]*)', tag, flags=re.I):
        tokens.add(hit.group(1))
        if len(hit.group(2)) >= 3:
            tokens.add(hit.group(2))
    return tokens


def _collect_script_corpus(html: str, dist: Path, page: Path) -> str:
    """Everything a client could execute from this page: inline scripts,
    locally bundled JS files referenced via src, and inline on*= handlers."""
    parts = []
    for hit in re.finditer(r"<script\b([^>]*)>(.*?)</script>", html, flags=re.S | re.I):
        parts.append(hit.group(2))
        src = re.search(r'\bsrc\s*=\s*["\']([^"\']+)["\']', hit.group(1))
        if src and not re.match(r"^[a-z]+://", src.group(1)):
            target = src.group(1)
            for cand in (dist / target.lstrip("/"), page.parent / target):
                if cand.is_file():
                    parts.append(cand.read_text(encoding="utf-8", errors="replace"))
                    break
    for hit in re.finditer(r'\son[a-z]+\s*=\s*"([^"]*)"', html, flags=re.I):
        parts.append(hit.group(1))
    return "\n".join(parts)


# A script that never mentions the input by an identifying token may still
# reach it generically (querySelector('input[type="search"]'), ...).
_GENERIC_INPUT_SELECT = re.compile(r"""["'`][^"'`]*\binput\b[^"'`]*["'`]""", re.I)

_WIRING = (
    re.compile(
        r"""addEventListener\s*\(\s*["'`](input|change|keyup|keydown|search|submit|click|paste)["'`]""",
        re.I,
    ),
    re.compile(r"""\bon(?:input|change|keyup|keydown|search|submit)\s*[:=]""", re.I),
    re.compile(r"""\.on(?:input|change|keyup|search)\s*=""", re.I),
)

_MATCH_PRIMITIVE = re.compile(
    r"""\.(?:includes|indexOf|match|test|search|filter|some|every)\s*\(|startsWith|endsWith|\.toLowerCase\(\)|\.normalize\(""",
    re.I,
)

_VISIBILITY_PRIMITIVE = re.compile(
    r"""\bhidden\b|\.display\b|\.visibility\b|classList|setProperty|removeAttribute|toggleAttribute|\.remove\(\)|aria-hidden|\.style\.""",
    re.I,
)

_NO_MATCH_MESSAGE = (
    re.compile(r"\bno\s+(?:posts|results|matches|articles|entries)\b", re.I),
    re.compile(r"\bnothing\s+(?:found|matched|here)\b", re.I),
    re.compile(r"\b0\s+(?:results|matches|posts)\b", re.I),
    re.compile(r"\bno\s+posts\s+match\b", re.I),
)


def _no_match_state(html: str, corpus: str) -> bool:
    """A human-readable no-match message in the HTML or the script corpus,
    or a no-results element whose content is human-readable text."""
    hay = html + "\n" + corpus
    if any(p.search(hay) for p in _NO_MATCH_MESSAGE):
        return True
    for hit in re.finditer(
        r"<([a-z]+)\b[^>]*(?:id|class)\s*=\s*[\"'][^\"']*no[-_]?(?:results?|match)[^\"']*['\"][^>]*>(.*?)</\1\s*>",
        html,
        flags=re.S | re.I,
    ):
        inner = _strip_scripts(hit.group(2))
        if re.search(r"[a-zA-Z]{3}.*\s.*[a-zA-Z]{3}", _strip_comments(inner)):
            return True
    return False


# ------------------------------------------------------------------ scoring


def score(root: Path, seed_root: Path, env_path=None) -> dict:
    """AC-3: the built /blog/ page carries a search control over embedded
    post-title data, verifiable filtering wiring, and human-readable
    empty-query and no-match states."""
    reasons: list = []
    build_dir = tempfile.TemporaryDirectory(prefix="oracle-astro-ac3-")
    try:
        work = Path(build_dir.name) / "ws"
        if not _astro_build_and_check(root, work, reasons, env_path):
            return {"verdict": FAIL, "reasons": reasons}

        dist = work / "dist"
        page = dist / "blog" / "index.html"
        if not page.is_file():
            reasons.append("built /blog/ page missing (dist/blog/index.html)")
            return {"verdict": FAIL, "reasons": reasons}

        html = _strip_comments(page.read_text(encoding="utf-8", errors="replace"))
        html_no_scripts = _strip_scripts(html)

        # 1. The search control exists on /blog/.
        controls = _search_inputs(html)
        if not controls:
            reasons.append("no search control: /blog/ has no <input> of type search/text")
        tokens: set = set()
        for tag in controls:
            tokens |= _input_tokens(tag)

        # 2. The data: every seed post title is embedded in the page, and
        #    rendered outside scripts (the human-readable empty-query state).
        titles = _seed_titles(seed_root)
        if not titles:
            reasons.append("seed fixture ships no posts (oracle misconfiguration)")
        for title in titles:
            if title.lower() not in html.lower():
                reasons.append(f"post title not present anywhere in built /blog/: {title!r}")
            elif title.lower() not in html_no_scripts.lower():
                reasons.append(
                    f"post title only present inside scripts, empty-query state "
                    f"would not render human-readable text: {title!r}"
                )

        # 3. Filtering verifiable in the served DOM: a script corpus that
        #    binds the input, listens for queries, matches, and toggles results.
        corpus = _collect_script_corpus(html, dist, page)
        if controls:
            bound = any(token in corpus for token in tokens) or bool(
                _GENERIC_INPUT_SELECT.search(corpus)
            )
            if not bound:
                reasons.append(
                    "no script references the search input (by id/name/class/data-* "
                    "or a generic input selector)"
                )
        if not any(pattern.search(corpus) for pattern in _WIRING):
            reasons.append("no event listener wires the search input to filtering behavior")
        if not _MATCH_PRIMITIVE.search(corpus):
            reasons.append("no query-matching logic (includes/indexOf/test/...) in the page scripts")
        if not _VISIBILITY_PRIMITIVE.search(corpus):
            reasons.append("no show/hide logic for filter results in the page scripts")

        # 4. The no-match state carries human-readable text.
        if not _no_match_state(html, corpus):
            reasons.append(
                "no human-readable no-match state (message or no-results element with text)"
            )
    finally:
        build_dir.cleanup()

    return {"verdict": PASS if not reasons else FAIL, "reasons": reasons}


# ------------------------------------------------- calibration reference/sab


def apply(workspace: Path) -> None:
    """Minimal reference implementation of AC-3 on the seed: a search input,
    per-item title data, a no-match status line, and a small inline script
    that filters the rendered list as the user types."""
    page = workspace / "src" / "pages" / "blog" / "index.astro"
    if not page.is_file():
        raise AssertionError("AC-3 reference: blog index not found in workspace")
    text = page.read_text(encoding="utf-8")
    if "post-search" in text:
        return  # already implemented; keep the reference idempotent

    # Machine-readable data: each list item carries its post title.
    text = text.replace(
        "<li>",
        '<li data-title={post.data.title}>',
        1,
    )
    # Search control + no-match status line ahead of the list.
    text = text.replace(
        "<section>",
        '<section>\n\t\t\t\t<label for="post-search">Filter posts</label>\n'
        '\t\t\t\t<input id="post-search" type="search" placeholder="Filter posts by title" />\n'
        '\t\t\t\t<p id="no-results" role="status" hidden>No posts match your search.</p>',
        1,
    )
    # The list the filter operates on.
    text = text.replace("<ul>", '<ul id="post-list">', 1)

    script = """<script is:inline>
			// AC-3 reference: client-side filter over the rendered post list.
			const searchInput = document.getElementById('post-search');
			const postItems = Array.from(document.querySelectorAll('#post-list li'));
			const noResults = document.getElementById('no-results');
			function filterPosts() {
				const query = searchInput.value.trim().toLowerCase();
				let shown = 0;
				for (const item of postItems) {
					const title = (item.dataset.title || item.textContent || '').toLowerCase();
					const matches = query === '' || title.includes(query);
					item.hidden = !matches;
					if (matches) shown += 1;
				}
				noResults.hidden = shown > 0;
			}
			searchInput.addEventListener('input', filterPosts);
		</script>
"""
    text = text.replace("</body>", f"{script}\t</body>", 1)
    page.write_text(text, encoding="utf-8")


def sabotage(workspace: Path) -> None:
    """Plausible broken variant: the control, the data, and the filter logic
    all ship, but the listener is never attached, so typing does nothing."""
    apply(workspace)
    page = workspace / "src" / "pages" / "blog" / "index.astro"
    text = page.read_text(encoding="utf-8")
    line = "\t\t\tsearchInput.addEventListener('input', filterPosts);\n"
    if line not in text:
        raise AssertionError("AC-3 sabotage: listener line not found after apply()")
    text = text.replace(
        line,
        "\t\t\t// NOTE: filter logic ships, but no event is attached yet.\n",
        1,
    )
    page.write_text(text, encoding="utf-8")


# ------------------------------------------------------------- matrix entry


def main() -> int:
    here = Path(__file__).resolve()
    seed = here.parents[2] / "fixtures" / "astro" / "seed"
    if not seed.is_dir():
        print(f"seed fixture not found: {seed}", flush=True)
        return 2

    expected = {"pristine": FAIL, "known_good": PASS, "broken": FAIL}
    matrix_ok = True
    for name, op in (("pristine", None), ("known_good", apply), ("broken", sabotage)):
        with tempfile.TemporaryDirectory(prefix=f"calib-astro-AC3-{name}-") as td:
            work = Path(td) / name
            shutil.copytree(seed, work, symlinks=False)
            if op is not None:
                op(work)
            result = score(work, seed)
        verdict = result["verdict"]
        ok = verdict == expected[name]
        matrix_ok = matrix_ok and ok
        print(f"{'OK  ' if ok else 'FAIL'} astro-AC3 {name}: {verdict}", flush=True)
        for reason in result["reasons"]:
            print(f"       {name}: {reason}", flush=True)
    print("CALIBRATION " + ("OK" if matrix_ok else "FAILED"))
    return 0 if matrix_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
