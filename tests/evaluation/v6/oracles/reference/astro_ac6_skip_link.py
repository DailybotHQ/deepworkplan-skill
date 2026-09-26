#!/usr/bin/env python3
"""Reference solution for Astro case AC-6 (skip link + keyboard focus), used
only for oracle calibration: adds a visible skip-to-content link as the first
body element of every page, anchors it to an id="main" target, and adds a
visible :focus style. The sabotage variant points the link at a missing
target (looks implemented; fails the journey).
"""

SKIP_CSS = """
/* AC-6: visible skip link, keyboard-reachable */
.skip-link {
	position: absolute;
	left: -9999px;
	top: 0;
	background: white;
	color: var(--black);
	padding: 0.5rem 1rem;
	z-index: 99;
}
.skip-link:focus {
	left: 1rem;
	top: 1rem;
	outline: 2px solid var(--accent);
}
"""


def apply(workspace_root):
    changed = False
    for astro in sorted(workspace_root.rglob("*.astro")):
        text = astro.read_text(encoding="utf-8")
        if "skip-link" in text:
            continue
        if "<body>" in text:
            text = text.replace(
                "<body>",
                '<body>\n\t\t<a class="skip-link" href="#main">Skip to content</a>',
                1,
            )
            changed = True
        text = text.replace("<main>", '<main id="main">', 1)
        astro.write_text(text, encoding="utf-8")
    css = workspace_root / "src" / "styles" / "global.css"
    if css.is_file() and ".skip-link" not in css.read_text(encoding="utf-8"):
        css.write_text(css.read_text(encoding="utf-8") + SKIP_CSS, encoding="utf-8")
        changed = True
    assert changed, "AC-6 reference found nothing to patch"


def sabotage(workspace_root):
    """Broken variant: the skip link exists but targets a missing anchor."""
    apply(workspace_root)
    for astro in sorted(workspace_root.rglob("*.astro")):
        text = astro.read_text(encoding="utf-8")
        if 'class="skip-link"' in text:
            text = text.replace('href="#main"', 'href="#contenido"', 1)
            astro.write_text(text, encoding="utf-8")
            return
