#!/usr/bin/env python3
"""Reference solution for Astro case AC-1 (reading-time field), used only
for oracle calibration: adds an optional `readingTime` schema field, renders
it on post pages, and populates it on one post — without breaking existing
posts. The sabotage variant keeps schema+data but drops the render.
"""


def apply(workspace_root):
    schema = workspace_root / "src" / "content.config.ts"
    text = schema.read_text(encoding="utf-8")
    if "readingTime" in text:
        pass
    else:
        anchor = "\t\t\tupdatedDate: z.coerce.date().optional(),"
        assert anchor in text, "schema anchor not found"
        text = text.replace(anchor, anchor + "\n\t\t\treadingTime: z.string().optional(),", 1)
        schema.write_text(text, encoding="utf-8")

    layout = workspace_root / "src" / "layouts" / "BlogPost.astro"
    text = layout.read_text(encoding="utf-8")
    if "readingTime" not in text:
        old_props = "const { title, description, pubDate, updatedDate, heroImage } = Astro.props;"
        new_props = "const { title, description, pubDate, updatedDate, heroImage, readingTime } = Astro.props;"
        assert old_props in text, "props anchor not found"
        text = text.replace(old_props, new_props, 1)
        old_date = "<FormattedDate date={pubDate} />"
        new_date = old_date + "\n\t\t\t\t\t\t\t{readingTime && <span class=\"reading-time\"> · {readingTime}</span>}"
        assert old_date in text, "date anchor not found"
        text = text.replace(old_date, new_date, 1)
        layout.write_text(text, encoding="utf-8")

    post = workspace_root / "src" / "content" / "blog" / "first-post.md"
    text = post.read_text(encoding="utf-8")
    if "readingTime" not in text:
        anchor = "heroImage: '../../assets/blog-placeholder-3.jpg'"
        assert anchor in text, "frontmatter anchor not found"
        text = text.replace(anchor, anchor + "\nreadingTime: '3 min read'", 1)
        post.write_text(text, encoding="utf-8")


def sabotage(workspace_root):
    """Broken variant: schema and data exist (build passes) but the render is
    missing — the user-visible behavior is absent."""
    apply(workspace_root)
    layout = workspace_root / "src" / "layouts" / "BlogPost.astro"
    text = layout.read_text(encoding="utf-8")
    line = "\n\t\t\t\t\t\t\t{readingTime && <span class=\"reading-time\"> · {readingTime}</span>}"
    assert line in text, "sabotage anchor not found"
    layout.write_text(text.replace(line, "", 1), encoding="utf-8")
