from src.core import normalize

def label(value: str) -> str:
    return normalize(value).upper()
