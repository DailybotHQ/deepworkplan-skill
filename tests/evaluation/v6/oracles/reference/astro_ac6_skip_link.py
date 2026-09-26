#!/usr/bin/env python3
"""Reference solution for Astro case AC-6 (skip link + keyboard focus), used
only for oracle calibration: adds a visible skip-to-content link as the first
body element of every page, anchors it to an id="main" target, and adds a
visible :focus style. The sabotage variant points the link at a missing
target (looks implemented; fails the journey). The stub_ variants are
cosmetic compliances an actor might ship to game a substring check: an
empty :focus rule, a cosmetic-only :focus rule, tabindex=-1, and a
display:none base that focus never undoes.
"""

import re

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

def _rewrite_focus_block(workspace_root, new_body):
    css = workspace_root / "src" / "styles" / "global.css"
    text = css.read_text(encoding="utf-8")
    text, n = re.subn(r"\.skip-link:focus\s*\{[^}]*\}",
                      ".skip-link:focus {" + new_body + "}", text)
    assert n == 1, "focus block not found for stub rewrite"
    css.write_text(text, encoding="utf-8")


def stub_empty_focus(workspace_root):
    """Stub: the :focus rule exists but is empty — pure shape compliance."""
    apply(workspace_root)
    _rewrite_focus_block(workspace_root, "")


def stub_cosmetic_focus(workspace_root):
    """Stub: :focus only recolors — the link stays offscreen and unfocusable
    visually, but '.skip-link' and ':focus' both appear in the CSS."""
    apply(workspace_root)
    _rewrite_focus_block(workspace_root, "\n\tcolor: rebeccapurple;\n\tfont-weight: bold;\n")


def stub_tabindex(workspace_root):
    """Stub: the anchor is first and styled, but tabindex=-1 removes it from
    the tab order, so it is never the first focusable element."""
    apply(workspace_root)
    for astro in sorted(workspace_root.rglob("*.astro")):
        text = astro.read_text(encoding="utf-8")
        if 'class="skip-link"' in text:
            text = text.replace(
                '<a class="skip-link" href="#main"',
                '<a class="skip-link" href="#main" tabindex="-1"', 1)
            astro.write_text(text, encoding="utf-8")
            return
    raise AssertionError("skip link anchor not found for stub_tabindex")


def stub_display_none(workspace_root):
    """Stub: base rule hard-hides the link with display:none and the :focus
    rule never restores display — the link can never receive focus."""
    apply(workspace_root)
    css = workspace_root / "src" / "styles" / "global.css"
    text = css.read_text(encoding="utf-8")
    text, n = re.subn(r"\.skip-link\s*\{", ".skip-link {\n\tdisplay: none;\n",
                      text, count=1)
    assert n == 1, "skip-link base rule not found for stub_display_none"
    css.write_text(text, encoding="utf-8")
