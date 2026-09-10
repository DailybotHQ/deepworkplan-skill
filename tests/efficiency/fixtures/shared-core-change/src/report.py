from src.core import normalize

def key(value: str) -> str:
    # consumers rely on normalize() collapsing inner whitespace? No — they rely on it NOT doing so.
    return normalize(value).replace(" ", "-")
